"""Execute transpiled PyLite programs."""

import dis
import sys

from .diagnostics import Span, render, source_lines
from .parser import Parser
from .transpiler import Transpiler


class PyLiteRuntimeError(Exception):
    """A readable error raised during program execution."""


def repeat_values(count):
    if type(count) is not int or count < 0:
        raise PyLiteRuntimeError(
            "The repeat count must be a nonnegative integer, "
            "such as 0, 1, or 5."
        )

    return range(count)


def double_value(value):
    if type(value) not in (int, float):
        raise PyLiteRuntimeError(
            "double_value expects a number."
        )

    return value * 2


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


def run(source, filename="<pylite>"):
    program = Parser(source, filename).parse()
    module = Transpiler().transpile(program)
    code = compile(module, filename, "exec")

    declared_names = set()

    def declare(name, value):
        if name in declared_names:
            raise PyLiteRuntimeError(
                f"Variable '{name}' was declared more than once "
                "during execution. Move its declaration before "
                "the loop."
            )

        declared_names.add(name)
        return value

    environment = {
        "__builtins__": {},
        "print": print,
        "double_value": double_value,
        "__pylite_repeat": repeat_values,
        "__pylite_declare": declare,
    }

    try:
        exec(code, environment, environment)

    except (PyLiteRuntimeError, ZeroDivisionError, TypeError, NameError) as error:
        tb = error.__traceback__
        origin = None
        while tb is not None:
            if tb.tb_frame.f_code is code:
                origin = tb
            last = tb
            tb = tb.tb_next

        # Only translate Python failures raised by generated user operations.
        # Helper validation raises PyLiteRuntimeError explicitly; helper defects
        # (including TypeError) must retain their original traceback.
        if origin is None or (not isinstance(error, PyLiteRuntimeError)
                              and last is not origin):
            raise
        span = runtime_span(code, origin.tb_lasti, source)
        if isinstance(error, ZeroDivisionError):
            message = "Cannot divide by zero. Check the value after '/'."
        elif isinstance(error, TypeError):
            message = ("This operation received incompatible values. "
                       "Check that the operands have suitable types.")
        elif isinstance(error, NameError):
            message = f"A variable has no value at this point: {error.name}."
        else:
            message = str(error)
        diagnostic = render("RuntimeError", message, source, filename, span,
                            line=origin.tb_lineno)
        raise PyLiteRuntimeError(diagnostic) from None

    return {
        name: value
        for name, value in environment.items()
        if name not in {"__builtins__", "print", "double_value"}
        and not name.startswith("__pylite_")
    }
