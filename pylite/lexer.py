"""Strict PyLite 1.0 lexer. Positions are one-based; offsets are zero-based."""
from dataclasses import dataclass, asdict

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

class LexError(Exception):
    def __init__(self, message, source, line, column):
        self.message, self.line, self.column = message, line, column
        lines = source.splitlines()
        snippet = lines[line - 1].expandtabs(4) if line <= len(lines) else ""
        prefix = f"{line} | "
        super().__init__(f"PyLite LexError [Line {line}, Col {column}]: {message}\n"
                         f"{prefix}{snippet}\n{' ' * (len(prefix) + column - 1)}^")

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
        stream = StreamReader(self.source)
        tokens = []
        while not stream.is_at_end():
            char = stream.peek()
            if char in " \t":
                stream.advance()
                continue
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
                if stream.peek() and (stream.peek().isalnum() or stream.peek() in "_."):
                    error("Invalid integer literal. PyLite 1.0 accepts digits only; separate numbers from names.")
                kind = "INTEGER"
                # Avoid Python's decimal-string conversion limit for long literals.
                value = 0
                for digit in self.source[start:stream.index]:
                    value = value * 10 + ord(digit) - ord("0")
            elif char == '"':
                stream.advance()
                decoded = []
                escapes = {"n": "\n", "t": "\t", "r": "\r", '"': '"', "\\": "\\"}
                while stream.peek() != '"':
                    if stream.is_at_end() or stream.peek() in "\r\n":
                        error('Unclosed string literal. Expected closing double quote before line end.')
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
                if operator not in OPERATORS:
                    error(f"Unexpected character {char!r}.")
                for _ in operator:
                    stream.advance()
                kind, value = OPERATORS[operator], operator
            tokens.append(Token(kind, self.source[start:stream.index], value, line, column, start, stream.index))
        tokens.append(Token("EOF", "", None, stream.line, stream.column, stream.index, stream.index))
        return tokens
