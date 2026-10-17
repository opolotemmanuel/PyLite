"""PyLite lexer with the documented 1.1 literal and comment extensions. Positions are one-based; offsets are zero-based."""
from dataclasses import dataclass, asdict
import math
from .diagnostics import SourceError, resource_error

KEYWORDS = {word: word.upper() for word in
            "let const if unless repeat times end loop print true false".split()}
OPERATORS = {"|>": "PIPE", "==": "EQ", "!=": "NE", "<=": "LE", ">=": "GE",
             "=": "ASSIGN", "+": "PLUS", "-": "MINUS", "*": "STAR", "/": "SLASH",
             "<": "LT", ">": "GT", "(": "LPAREN", ")": "RPAREN",
             ":": "COLON", ",": "COMMA"}

@dataclass(frozen=True)
class Token:
    kind: str
    lexeme: str
    value: object
    line: int
    column: int
    start: int
    end: int

    def to_dict(self):
        return asdict(self)

class LexError(SourceError):
    category = "LexError"

    def __init__(self, message, source, line, column):
        super().__init__(message, line, column, source)

class StreamReader:
    """Tracks raw offsets and visual columns; CRLF is a single newline."""
    def __init__(self, source):
        self.source, self.index, self.line, self.column = source, 0, 1, 1

    def peek(self, distance=0):
        i = self.index + distance
        return self.source[i] if i < len(self.source) else ""

    def is_at_end(self):
        return self.index >= len(self.source)

    def advance(self):
        char = self.peek()
        if not char:
            return ""
        self.index += 1
        if char == "\r":
            if self.peek() == "\n":
                self.index += 1
            self.line += 1
            self.column = 1
        elif char == "\n":
            self.line += 1
            self.column = 1
        elif char == "\t":
            self.column += 4 - (self.column - 1) % 4
        else:
            self.column += 1
        return char

class Lexer:
    def __init__(self, source):
        self.source = source

    def tokenize(self):
        self.position = (1, 1)
        try:
            return self._tokenize()
        except (RecursionError, MemoryError) as error:
            raise resource_error(error, self.source, *self.position) from None

    def _tokenize(self):
        stream = StreamReader(self.source)
        tokens = []
        while not stream.is_at_end():
            char = stream.peek()
            if char in " \t":
                stream.advance()
                continue
            self.position = (stream.line, stream.column)
            if char == "#" and stream.peek(1) == "|":
                opening = (stream.line, stream.column)
                stream.advance()
                stream.advance()
                depth = 1
                while depth:
                    if stream.is_at_end():
                        raise LexError("Unclosed multiline comment. Expected '|#'.", self.source, *opening)
                    pair = stream.peek() + stream.peek(1)
                    if pair in ("#|", "|#"):
                        depth += 1 if pair == "#|" else -1
                        stream.advance()
                        stream.advance()
                    elif stream.peek() in "\r\n":
                        start, line, column = stream.index, stream.line, stream.column
                        stream.advance()
                        tokens.append(Token("NEWLINE", self.source[start:stream.index], None,
                                            line, column, start, stream.index))
                    else:
                        stream.advance()
                continue
            if char == "|" and stream.peek(1) == "#":
                raise LexError("Comment closing '|#' has no matching '#|'.", self.source,
                               stream.line, stream.column)
            if char == "#":
                while not stream.is_at_end() and stream.peek() not in "\r\n":
                    stream.advance()
                continue
            start, line, column = stream.index, stream.line, stream.column

            def error(message):
                raise LexError(message, self.source, line, column)

            if char in "\r\n":
                stream.advance()
                kind, value = "NEWLINE", None
            elif char.isascii() and (char.isalpha() or char == "_"):
                stream.advance()
                while stream.peek() and stream.peek().isascii() and (stream.peek().isalnum() or stream.peek() == "_"):
                    stream.advance()
                word = self.source[start:stream.index]
                kind = KEYWORDS.get(word, "IDENTIFIER")
                value = True if word == "true" else False if word == "false" else word
            elif char in "0123456789":
                while stream.peek() and stream.peek() in "0123456789":
                    stream.advance()
                floating = False
                if stream.peek() == ".":
                    floating = True
                    stream.advance()
                    if not stream.peek() or stream.peek() not in "0123456789":
                        error("Malformed number: expected digits after the decimal point (for example 3.14).")
                    while stream.peek() and stream.peek() in "0123456789":
                        stream.advance()
                if stream.peek() and stream.peek() in "eE":
                    floating = True
                    stream.advance()
                    if stream.peek() and stream.peek() in "+-":
                        stream.advance()
                    if not stream.peek() or stream.peek() not in "0123456789":
                        error("Malformed number: expected exponent digits (for example 2.5e-2).")
                    while stream.peek() and stream.peek() in "0123456789":
                        stream.advance()
                if stream.peek() and (stream.peek().isalnum() or stream.peek() in "_."):
                    error("Malformed number: separate numbers from names; underscores and extra decimal points are not allowed.")
                literal = self.source[start:stream.index]
                if floating:
                    kind, value = "FLOAT", float(literal)
                    if not math.isfinite(value):
                        error("Floating-point literal is outside the finite supported range.")
                else:
                    kind, value = "INTEGER", 0
                    # Avoid Python's decimal-string conversion limit for long literals.
                    for digit in literal:
                        value = value * 10 + ord(digit) - ord("0")
            elif char in ('"', "'"):
                quote = char
                stream.advance()
                decoded = []
                escapes = {"n": "\n", "t": "\t", "r": "\r", '"': '"', "'": "'", "\\": "\\"}
                while stream.peek() != quote:
                    if stream.is_at_end() or stream.peek() in "\r\n":
                        error(f"Unclosed string literal. Expected closing {quote!r} before line end.")
                    current = stream.advance()
                    if current == "\\":
                        if stream.is_at_end() or stream.peek() in "\r\n":
                            error("Unclosed string literal after escape character.")
                        escaped = stream.advance()
                        if escaped not in escapes:
                            error(f"Unknown string escape: {chr(92)}{escaped}.")
                        current = escapes[escaped]
                    decoded.append(current)
                stream.advance()
                kind, value = "STRING", "".join(decoded)
            else:
                operator = self.source[start:start + 2]
                if operator not in OPERATORS:
                    operator = char
                if char == "." and stream.peek(1) and stream.peek(1) in "0123456789":
                    error("Malformed number: include digits before the decimal point (for example 0.5).")
                if operator not in OPERATORS:
                    error(f"Unexpected character {char!r}.")
                for _ in operator:
                    stream.advance()
                kind, value = OPERATORS[operator], operator
            tokens.append(Token(kind, self.source[start:stream.index], value, line, column, start, stream.index))
        tokens.append(Token("EOF", "", None, stream.line, stream.column, stream.index, stream.index))
        return tokens
