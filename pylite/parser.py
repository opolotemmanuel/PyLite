"""Recursive-descent parser for PyLite 1.0."""

from .lexer import Lexer
from .nodes import (
    Assignment, Binary, Call, Conditional, Declaration,
    ExpressionStatement, Literal, Name, Program, Repeat, Unary,
)


class ParseError(Exception):
    def __init__(self, message, source, token):
        lines = source.splitlines()
        snippet = (
            lines[token.line - 1].expandtabs(4)
            if token.line <= len(lines)
            else ""
        )
        prefix = f"{token.line} | "
        super().__init__(
            f"PyLite ParseError [Line {token.line}, "
            f"Col {token.column}]: {message}\n"
            f"{prefix}{snippet}\n"
            f"{' ' * (len(prefix) + token.column - 1)}^"
        )


class Parser:
    def __init__(self, source):
        self.source = source
        self.tokens = Lexer(source).tokenize()
        self.position = 0
        self.parenthesis_depth = 0

    @property
    def current(self):
        return self.tokens[self.position]

    def advance(self):
        token = self.current
        if token.kind != "EOF":
            self.position += 1
        return token

    def match(self, *kinds):
        if self.current.kind in kinds:
            return self.advance()
        return None

    def expect(self, kind, message):
        if self.current.kind != kind:
            self.error(message)
        return self.advance()

    def error(self, message):
        raise ParseError(message, self.source, self.current)

    def skip_newlines(self):
        while self.match("NEWLINE"):
            pass

    def expression_space(self):
        if self.parenthesis_depth:
            self.skip_newlines()

    def statement_end(self):
        if self.match("NEWLINE"):
            self.skip_newlines()
        elif self.current.kind != "EOF":
            self.error("Expected a new line after this statement.")

    def parse(self):
        statements = []
        self.skip_newlines()
        while self.current.kind != "EOF":
            statements.append(self.statement())
        return Program(statements)

    def statement(self):
        kind = self.current.kind

        if kind in ("LET", "CONST"):
            mutable = self.advance().kind == "LET"
            name = self.expect(
                "IDENTIFIER",
                "Expected a variable name after let or const.",
            ).lexeme
            self.expect("ASSIGN", "Expected '=' after the variable name.")
            value = self.expression()
            self.statement_end()
            return Declaration(name, value, mutable)

        if kind in ("IF", "UNLESS", "REPEAT"):
            return self.block()

        if kind == "END":
            self.error("Unexpected 'end': there is no matching open block.")

        if (
            kind == "IDENTIFIER"
            and self.tokens[self.position + 1].kind == "ASSIGN"
        ):
            name = self.advance().lexeme
            self.advance()
            value = self.expression()
            self.statement_end()
            return Assignment(name, value)

        expression = self.expression()
        self.statement_end()
        return ExpressionStatement(expression)

    def block(self):
        opening = self.advance().kind
        expression = self.expression()

        if opening == "REPEAT":
            self.expect("TIMES", "Expected 'times' after the repeat count.")

        self.expect("COLON", "Expected ':' before the block body.")
        self.expect("NEWLINE", "Start the block body on a new line.")
        self.skip_newlines()

        body = []
        closing = "LOOP" if opening == "REPEAT" else opening

        while self.current.kind != "END":
            if self.current.kind == "EOF":
                self.error(f"Missing 'end {closing.lower()}'.")

            body.append(self.statement())

        self.advance()
        self.expect(
            closing,
            f"Expected 'end {closing.lower()}' to close this block.",
        )
        self.statement_end()

        if opening == "REPEAT":
            return Repeat(expression, body)

        return Conditional(expression, body, opening == "UNLESS")

    def expression(self):
        expression = self.comparison()
        self.expression_space()

        while self.match("PIPE"):
            self.expression_space()
            function = self.match("IDENTIFIER", "PRINT")
            if function is None:
                self.error("Expected a function name after '|>'.")

            expression = Call(function.lexeme, [expression])
            self.expression_space()

        return expression

    def comparison(self):
        expression = self.addition()
        self.expression_space()
        operator = self.match("EQ", "NE", "LT", "GT", "LE", "GE")

        if operator:
            right = self.addition()
            expression = Binary(expression, operator.lexeme, right)
            self.expression_space()

            if self.current.kind in ("EQ", "NE", "LT", "GT", "LE", "GE"):
                self.error(
                    "Chained comparisons are not supported yet. "
                    "Use one comparison per expression."
                )

        return expression

    def addition(self):
        expression = self.multiplication()
        self.expression_space()

        while self.current.kind in ("PLUS", "MINUS"):
            operator = self.advance().lexeme
            right = self.multiplication()
            expression = Binary(expression, operator, right)
            self.expression_space()

        return expression

    def multiplication(self):
        expression = self.unary()
        self.expression_space()

        while self.current.kind in ("STAR", "SLASH"):
            operator = self.advance().lexeme
            right = self.unary()
            expression = Binary(expression, operator, right)
            self.expression_space()

        return expression

    def unary(self):
        self.expression_space()
        operator = self.match("PLUS", "MINUS")
        if operator:
            return Unary(operator.lexeme, self.unary())
        return self.primary()

    def primary(self):
        self.expression_space()
        token = self.match("INTEGER", "STRING", "TRUE", "FALSE")
        if token:
            return Literal(token.value)

        token = self.match("IDENTIFIER", "PRINT")
        if token:
            self.expression_space()
            if self.match("LPAREN"):
                self.parenthesis_depth += 1
                arguments = []
                self.expression_space()

                if self.current.kind != "RPAREN":
                    arguments.append(self.expression())
                    while self.match("COMMA"):
                        arguments.append(self.expression())

                self.expect("RPAREN", "Expected ')' after function arguments.")
                self.parenthesis_depth -= 1
                return Call(token.lexeme, arguments)

            if token.kind == "PRINT":
                self.error("Use print(...) or pass a value through '|> print'.")

            return Name(token.lexeme)

        if self.match("LPAREN"):
            self.parenthesis_depth += 1
            expression = self.expression()
            self.expression_space()
            self.expect("RPAREN", "Expected ')' after the expression.")
            self.parenthesis_depth -= 1
            return expression

        self.error("Expected a value, variable name, or parenthesized expression.")