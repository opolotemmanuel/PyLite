"""Core scanning engine: StreamReader (character stream + position tracking)
and LexerEngine (base frame: trivia skipping, token hooks, error reporting).

Comment syntax (assumption, change the two constants to suit your language):
    # ...            single-line comment, runs to end of line
    #[ ... ]#        multi-line comment, not nested; must be closed
"""

from dataclasses import dataclass
from typing import List, Optional

EOF = "\0"  # returned by peek()/advance() at end of input

LINE_COMMENT = "#"
BLOCK_OPEN = "#["
BLOCK_CLOSE = "]#"


@dataclass(frozen=True)
class Position:
    """A point in the source. line and column are 1-based; index is 0-based."""
    index: int
    line: int
    column: int

    def __str__(self) -> str:
        return f"{self.line}:{self.column}"


class LexError(Exception):
    def __init__(self, message: str, pos: Position):
        super().__init__(f"{pos}: {message}")
        self.message = message
        self.pos = pos


class StreamReader:
    """Character pointer over a source string.

    - peek(n) looks ahead without consuming; advance() consumes one character.
    - "\\r\\n", "\\r" and "\\n" each count as ONE newline (advance returns "\\n").
    - A tab moves the column to the next tab stop (tab_width), so columns match
      what an editor shows. The character index still counts the tab as 1.
    """

    def __init__(self, source: str, tab_width: int = 4):
        if tab_width < 1:
            raise ValueError("tab_width must be >= 1")
        self.source = source
        self.tab_width = tab_width
        self._index = 0
        self._line = 1
        self._column = 1

    # --- inspection ---------------------------------------------------
    def is_at_end(self) -> bool:
        return self._index >= len(self.source)

    def peek(self, offset: int = 0) -> str:
        i = self._index + offset
        if 0 <= i < len(self.source):
            return self.source[i]
        return EOF

    def startswith(self, text: str) -> bool:
        return self.source.startswith(text, self._index)

    @property
    def position(self) -> Position:
        return Position(self._index, self._line, self._column)

    # --- consumption --------------------------------------------------
    def advance(self) -> str:
        """Consume and return the next character (EOF if at end)."""
        if self.is_at_end():
            return EOF
        ch = self.source[self._index]
        self._index += 1
        if ch == "\r":
            if self.peek() == "\n":  # treat \r\n as a single newline
                self._index += 1
            ch = "\n"
        if ch == "\n":
            self._line += 1
            self._column = 1
        elif ch == "\t":
            self._column += self.tab_width - ((self._column - 1) % self.tab_width)
        else:
            self._column += 1
        return ch

    def advance_if(self, text: str) -> bool:
        """Consume `text` if it is next in the stream."""
        if not self.startswith(text):
            return False
        for _ in text:
            self.advance()
        return True

    def slice(self, start: Position, end: Optional[Position] = None) -> str:
        """Raw source text between two positions (end defaults to current)."""
        end = end or self.position
        return self.source[start.index:end.index]


class LexerEngine:
    """Base frame. Subclass and implement scan_token() to produce tokens."""

    def __init__(self, source: str, tab_width: int = 4):
        self.reader = StreamReader(source, tab_width)
        self.tokens: List[object] = []
        self.token_start: Position = self.reader.position

    # --- trivia: whitespace and comments ------------------------------
    def skip_trivia(self) -> None:
        """Consume whitespace and comments until the next real character."""
        r = self.reader
        while not r.is_at_end():
            ch = r.peek()
            if ch in " \t\n\r\f\v":
                r.advance()
            elif r.startswith(BLOCK_OPEN):
                self._skip_block_comment()
            elif ch == LINE_COMMENT:
                self._skip_line_comment()
            else:
                break

    def _skip_line_comment(self) -> None:
        r = self.reader
        while not r.is_at_end() and r.peek() != "\n":
            r.advance()  # newline itself is left for the whitespace loop

    def _skip_block_comment(self) -> None:
        r = self.reader
        start = r.position
        r.advance_if(BLOCK_OPEN)
        while not r.is_at_end():
            if r.advance_if(BLOCK_CLOSE):
                return
            r.advance()
        raise LexError("unterminated multi-line comment", start)

    # --- driver -------------------------------------------------------
    def tokenize(self) -> List[object]:
        while True:
            self.skip_trivia()
            if self.reader.is_at_end():
                break
            self.token_start = self.reader.position
            self.scan_token()
        self.tokens.append(self.make_eof())
        return self.tokens

    def scan_token(self) -> None:
        """Consume one token starting at self.token_start. Override me."""
        ch = self.reader.peek()
        raise LexError(f"unexpected character {ch!r}", self.token_start)

    def make_eof(self) -> object:
        return ("EOF", "", self.reader.position)

    def emit(self, kind: str, value: Optional[str] = None) -> None:
        """Append a token spanning token_start..current position."""
        text = self.reader.slice(self.token_start) if value is None else value
        self.tokens.append((kind, text, self.token_start))

    def error(self, message: str) -> LexError:
        return LexError(message, self.token_start)


if __name__ == "__main__":
    # Smoke tests
    r = StreamReader("a\tb\r\nc")
    out = []
    while not r.is_at_end():
        p = r.position
        out.append((r.advance(), p.line, p.column, p.index))
    assert out == [("a", 1, 1, 0), ("\t", 1, 2, 1), ("b", 1, 5, 2),
                   ("\n", 1, 6, 3), ("c", 2, 1, 5)], out
    assert r.peek() == EOF and r.advance() == EOF

    class Words(LexerEngine):
        def scan_token(self):
            while self.reader.peek().isalnum():
                self.reader.advance()
            if self.reader.position.index == self.token_start.index:
                raise self.error(f"unexpected {self.reader.peek()!r}")
            self.emit("WORD")

    toks = Words("foo # note\n  #[ multi\n line ]# bar\n\tbaz").tokenize()
    assert [(t[0], t[1], str(t[2])) for t in toks] == [
        ("WORD", "foo", "1:1"), ("WORD", "bar", "3:10"),
        ("WORD", "baz", "4:5"), ("EOF", "", "4:8")], toks

    try:
        Words("x #[ never closed").tokenize()
    except LexError as e:
        assert "unterminated" in str(e) and str(e.pos) == "1:3"
    else:
        raise AssertionError("expected LexError")
    print("all checks passed")
