"""Static binding checks for PyLite programs."""

from .nodes import (
    Assignment, Binary, Call, Conditional, Declaration,
    ExpressionStatement, Literal, Name, Program, Repeat, Unary,
)
from .symbols import SemanticError, SymbolTable


class SemanticAnalyzer:
    def __init__(self):
        # Functions supplied by the future PyLite runtime.
        self.builtins = {
            "print": None,       # Any number of arguments.
            "double_value": 1,   # Exactly one argument.
        }
        self.symbols = SymbolTable()
        self.initialized: set[str] = set()

    def analyze(self, program: Program) -> Program:
        # Reset state so the analyzer can check multiple programs.
        self.symbols = SymbolTable()
        self.initialized = set()

        for statement in program.statements:
            self.check_statement(statement)

        return program

    def check_statement(self, statement):
        if isinstance(statement, Declaration):
            if statement.name.startswith("__pylite_"):
                raise SemanticError(
                    "Names starting with '__pylite_' are reserved "
                    "for the compiler. Choose another variable name."
                )

            if statement.name in self.builtins:
                raise SemanticError(
                    f"'{statement.name}' is a built-in function name. "
                    "Choose another variable name."
                )

            # Check the initializer before making the new binding available.
            self.check_expression(statement.value)
            self.symbols.declare(statement.name, statement.mutable)
            self.initialized.add(statement.name)
            return
        if isinstance(statement, Assignment):
            self.symbols.require_mutable(statement.name)
            self.check_expression(statement.value)
            self.initialized.add(statement.name)
            return

        if isinstance(statement, ExpressionStatement):
            self.check_expression(statement.expression)
            return

        if isinstance(statement, Conditional):
            self.check_expression(statement.condition)
            self.check_optional_body(statement.body)
            return

        if isinstance(statement, Repeat):
            self.check_expression(statement.count)
            self.check_optional_body(statement.body)
            return

        raise TypeError(
            f"Unsupported statement node: {type(statement).__name__}"
        )

    def check_optional_body(self, statements):
        # The block may not execute. Analyze its contents, but do not
        # assume that assignments inside it happened after the block.
        previously_initialized = self.initialized.copy()

        try:
            for statement in statements:
                self.check_statement(statement)
        finally:
            self.initialized = previously_initialized

    def check_expression(self, expression):
        if isinstance(expression, Literal):
            return

        if isinstance(expression, Name):
            self.symbols.lookup(expression.identifier)

            if expression.identifier not in self.initialized:
                raise SemanticError(
                    f"Variable '{expression.identifier}' may not have "
                    "a value because its declaration is inside a block "
                    "that might not execute. Declare it before the block."
                )
            return

        if isinstance(expression, Unary):
            self.check_expression(expression.operand)
            return

        if isinstance(expression, Binary):
            self.check_expression(expression.left)
            self.check_expression(expression.right)
            return

        if isinstance(expression, Call):
            if expression.function not in self.builtins:
                raise SemanticError(
                    f"Unknown function '{expression.function}'. "
                    "Available functions: print, double_value."
                )

            expected = self.builtins[expression.function]
            actual = len(expression.arguments)

            if expected is not None and actual != expected:
                raise SemanticError(
                    f"Function '{expression.function}' expects "
                    f"{expected} argument(s), but received {actual}."
                )

            for argument in expression.arguments:
                self.check_expression(argument)
            return

        raise TypeError(
            f"Unsupported expression node: {type(expression).__name__}"
        )