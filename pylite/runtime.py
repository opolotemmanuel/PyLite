"""Execution support for generated PyLite AST nodes."""
import ast
import operator
from .compiler import Parser, Compiler as Transpiler
from .parser import Parser as SyntaxParser
from .symbols import SemanticError
from .diagnostics import Span, render, source_lines
import dis
import sys
from .lexer import Lexer
from .diagnostics import SourceError, ResourceError, resource_error

from .builtin_names import BUILTIN_NAMES

class RuntimeError(SourceError):
    category = "RuntimeError"

class BindingError(RuntimeError, SemanticError):
    """Binding failures remain catchable through either project's error API."""


PyLiteRuntimeError = RuntimeError


class ExecutionResult(dict):
    @property
    def variables(self):
        return self


class Runtime:
    def __init__(self, output=None):
        output = print if output is None else output
        self.variables = {}
        self.constants = set()
        self.declaration_positions = {}
        def display(*values):
            output(" ".join(self.format_value(value) for value in values))
        self.functions = {"print": display, "double_value": double_value,
                          "abs": abs, "len": len, "str": self.format_value, "int": int}

    @staticmethod
    def format_value(value):
        if type(value) is bool:
            return "true" if value else "false"
        return str(value)

    @staticmethod
    def numeric_double(value):
        if type(value) not in (int, float):
            raise TypeError("double_value expects a number")
        return value * 2

    def declare(self, name, value, constant, line, column):
        if name in self.variables:
            error = RuntimeError if self.declaration_positions[name] == (line, column) else BindingError
            raise error(f"Name '{name}' is already declared. Variable '{name}' was declared more than once during execution.", line, column)
        if name in self.functions or name.startswith("__pylite_"):
            raise BindingError(f"Name '{name}' is already declared or reserved for a built-in function. Variable '{name}' was declared more than once during execution.", line, column)
        self.variables[name] = value
        self.declaration_positions[name] = (line, column)
        if constant:
            self.constants.add(name)

    def assign(self, name, value, line, column):
        if name not in self.variables:
            raise BindingError(f"Variable '{name}' is not declared. Use 'let {name} = ...' first.", line, column)
        if name in self.constants:
            raise BindingError(f"Cannot change constant '{name}'. Cannot reassign constant '{name}'. Use 'let' for a mutable variable.", line, column)
        self.variables[name] = value

    def get(self, name, line, column):
        if name not in self.variables:
            raise BindingError(f"Variable '{name}' is not declared.", line, column)
        return self.variables[name]

    def condition(self, value, line, column):
        if type(value) is not bool:
            raise RuntimeError("A condition must be true or false; use a comparison such as 'count > 0'.", line, column)
        return value

    def repeat(self, value, line, column):
        if type(value) is not int or value < 0:
            raise RuntimeError("A repeat count must be a non-negative integer (nonnegative integer, such as 0, 1, or 5).", line, column)
        return range(value)

    def call(self, name, args, line, column):
        if name not in self.functions:
            raise BindingError(f"Unknown function '{name}'.", line, column)
        if name == 'double_value':
            if len(args) != 1:
                raise BindingError("Function 'double_value' expects 1 argument.", line, column)
            # Explicit validation errors are translated; unexpected helper defects propagate.
            try:
                return self.functions[name](*args)
            except RuntimeError as error:
                raise RuntimeError(error.message, line, column) from None
        try:
            return self.functions[name](*args)
        except (TypeError, ValueError, OverflowError) as error:
            raise RuntimeError(f"Invalid arguments for '{name}': {error}", line, column) from None

    def unary(self, kind, value, line, column):
        if type(value) not in (int, float):
            raise RuntimeError("This operation received incompatible values. Unary '+' and '-' require a number.", line, column)
        return value if kind == "PLUS" else -value

    def binary(self, kind, left, right, line, column):
        operations = {"PLUS": operator.add, "MINUS": operator.sub, "STAR": operator.mul,
                      "SLASH": operator.truediv, "EQ": operator.eq, "NE": operator.ne,
                      "LT": operator.lt, "GT": operator.gt, "LE": operator.le, "GE": operator.ge}
        numeric = type(left) in (int, float) and type(right) in (int, float)
        if kind in ("PLUS", "MINUS", "STAR", "SLASH") and not numeric:
            if not (kind == "PLUS" and type(left) is str and type(right) is str):
                raise RuntimeError("This operation received incompatible values. Arithmetic requires numbers; '+' also joins two strings.", line, column)
        if kind in ("LT", "GT", "LE", "GE") and not numeric and not (type(left) is str and type(right) is str):
            raise RuntimeError("This operation received incompatible values. Compare two numbers or two strings.", line, column)
        if kind in ("EQ", "NE") and type(left) is not type(right) and not numeric:
            return kind == "NE"
        try:
            return operations[kind](left, right)
        except ZeroDivisionError:
            raise RuntimeError("Cannot divide by zero.", line, column) from None
        except (TypeError, ValueError, OverflowError) as error:
            raise RuntimeError(f"Cannot evaluate this expression: {error}", line, column) from None

    def environment(self):
        names = ("declare", "assign", "get", "condition", "repeat", "call", "unary", "binary")
        def guarded(method):
            def invoke(*args):
                try:
                    return method(*args)
                except (RecursionError, MemoryError) as error:
                    raise resource_error(error, line=args[-2], column=args[-1]) from None
            return invoke
        return {"__builtins__": {}, **{"_lite_" + name: guarded(getattr(self, name)) for name in names}}

def run(source, filename="<pylite>", output=None):
    """Run one fresh program and return its runtime for inspection."""
    tree = Transpiler().transpile(SyntaxParser(source, filename).parse())
    runtime = Runtime(output)
    environment = runtime.environment()
    try:
        code = compile(tree, filename, "exec")
        exec(code, environment, environment)
    except (RuntimeError, ResourceError) as error:
        if filename == '<pylite>' or isinstance(error, ResourceError):
            raise type(error)(error.message, error.line, error.column, source) from None
        tb, origin = error.__traceback__, None
        while tb is not None:
            if tb.tb_frame.f_code is code:
                origin = tb
            tb = tb.tb_next
        span = runtime_span(code, origin.tb_lasti, source) if origin else None
        kind = 'RuntimeError'
        if isinstance(error, BindingError):
            kind = 'SemanticError'
            token = next((t for t in Lexer(source).tokenize()
                          if (t.line, t.column) == (error.line, error.column)), None)
            if token:
                span = Span.from_offsets(source, token.start, token.end)
        error.args = (render(kind, error.message, source, filename, span,
                             line=origin.tb_lineno if origin else error.line),)
        raise error from None
    except (RecursionError, MemoryError) as error:
        raise resource_error(error, source) from None
    result = ExecutionResult(runtime.variables)
    result.constants = runtime.constants
    return result

def transpile(source):
    """Return Python code; its helper calls require a Runtime.environment()."""
    tree = Parser(source).parse()
    try:
        return ast.unparse(tree)
    except (RecursionError, MemoryError) as error:
        raise resource_error(error, source) from None
    except ValueError as error:
        raise ResourceError(f"Cannot render generated code: {error}", 1, 1, source) from None


def runtime_span(code, instruction_offset, source):
    """Return a precise span only when instruction debug ranges are available."""
    # Python 3.10 has neither show_caches nor Instruction.positions.
    if sys.version_info < (3, 11) or not hasattr(code, "co_positions"):
        return None
    position = next((getattr(instruction, "positions", None)
                     for instruction in dis.get_instructions(code, show_caches=True)
                     if instruction.offset == instruction_offset), None)
    if position is None or any(value is None for value in (
            position.lineno, position.end_lineno,
            position.col_offset, position.end_col_offset)):
        return None

    lines = source_lines(source)

    def offset(line, column):
        prefix = sum(len(text) for text in lines[:line - 1])
        return prefix + len(lines[line - 1].encode("utf-8")[:column].decode("utf-8"))

    return Span.from_offsets(source,
                             offset(position.lineno, position.col_offset),
                             offset(position.end_lineno, position.end_col_offset))


def double_value(value):
    if type(value) not in (int, float):
        raise RuntimeError("double_value expects a number.", 1, 1)
    return value * 2
