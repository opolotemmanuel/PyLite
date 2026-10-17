"""Keyword lookup table, identifier classification, and scope-aware symbol
pre-checks for PyLite 1.0.

The pre-check runs over the token stream before parsing, so a reserved word
used as a variable name gets a clear message instead of a generic parse error:

    let if = 1      ->  'if' is a reserved keyword and cannot be used as a
                        variable name.
"""
from dataclasses import dataclass

# The lexer owns the keyword lookup table, so both modules share one list.
# 'loop' is reserved too because blocks close with 'end loop'.
from .lexer import KEYWORDS, LexError

KEYWORD_KINDS = frozenset(KEYWORDS.values())
BLOCK_OPENERS = frozenset({"IF", "UNLESS", "REPEAT"})


class ReservedWordError(LexError):
    """A reserved keyword is used where a variable name is expected."""


class KeywordClassifier:
    """Distinguishes user variable names from reserved words."""

    def __init__(self, keywords=None):
        self.keywords = dict(KEYWORDS if keywords is None else keywords)

    def is_reserved(self, word):
        return word in self.keywords

    def classify(self, word):
        """Return the token kind for a word: its keyword kind or IDENTIFIER."""
        return self.keywords.get(word, "IDENTIFIER")

    def is_valid_identifier(self, word):
        """True if word could name a variable: ASCII letters, digits and '_',
        not starting with a digit, and not reserved."""
        return (bool(word)
                and word.isascii()
                and (word[0].isalpha() or word[0] == "_")
                and all(c.isalnum() or c == "_" for c in word)
                and not self.is_reserved(word))

    def reserved_name_message(self, word):
        if word in ("true", "false"):
            return (f"'{word}' is a boolean value and cannot be used as a "
                    f"variable name. Try a different name, such as 'is_{word}'.")
        return (f"'{word}' is a reserved keyword and cannot be used as a "
                f"variable name. Try a different name, such as '{word}_value'.")


@dataclass(frozen=True)
class ScopedSymbol:
    name: str
    mutable: bool
    line: int
    column: int
    depth: int  # 0 is the top level; each if/unless/repeat block adds one


class ScopedSymbolTable:
    """Records declarations per block scope. Lookups search the innermost
    scope first, then the enclosing ones."""

    def __init__(self):
        self.scopes = [{}]
        self.declarations = []

    @property
    def depth(self):
        return len(self.scopes) - 1

    def enter_scope(self):
        self.scopes.append({})

    def exit_scope(self):
        # An unmatched 'end' is reported by the parser, so never pop the top level.
        if len(self.scopes) > 1:
            self.scopes.pop()

    def declare(self, name, mutable, line, column):
        symbol = ScopedSymbol(name, mutable, line, column, self.depth)
        self.scopes[-1][name] = symbol
        self.declarations.append(symbol)
        return symbol

    def lookup(self, name):
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        return None

    def is_declared(self, name):
        return self.lookup(name) is not None


def precheck(tokens, source, classifier=None):
    """Scan a token stream for reserved words used as variable names.

    Returns the ScopedSymbolTable of declarations found; raises
    ReservedWordError at the first misuse.
    """
    classifier = classifier or KeywordClassifier()
    table = ScopedSymbolTable()
    at_statement_start = True

    def fail(token):
        raise ReservedWordError(classifier.reserved_name_message(token.lexeme),
                                source, token.line, token.column)

    for index, token in enumerate(tokens):
        following = tokens[index + 1] if index + 1 < len(tokens) else None

        if token.kind == "NEWLINE":
            at_statement_start = True
            continue
        if not at_statement_start:
            continue
        at_statement_start = False

        if token.kind in ("LET", "CONST") and following is not None:
            if following.kind in KEYWORD_KINDS:
                fail(following)
            if following.kind == "IDENTIFIER":
                table.declare(following.lexeme, token.kind == "LET",
                              following.line, following.column)
        elif token.kind in KEYWORD_KINDS and following is not None \
                and following.kind == "ASSIGN":
            # e.g. 'end = 3' or 'print = 1' at the start of a statement
            fail(token)
        elif token.kind in BLOCK_OPENERS:
            table.enter_scope()
        elif token.kind == "END":
            table.exit_scope()

    return table
