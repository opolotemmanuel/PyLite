"""Variable binding records for PyLite semantic analysis."""

from dataclasses import dataclass


class SemanticError(Exception):
    """A program violates a variable binding rule."""


@dataclass(frozen=True)
class Symbol:
    name: str
    mutable: bool


class SymbolTable:
    def __init__(self):
        self._symbols: dict[str, Symbol] = {}

    def declare(self, name: str, mutable: bool) -> Symbol:
        if name in self._symbols:
            raise SemanticError(
                f"Variable '{name}' is already declared. "
                "Use assignment to update a mutable variable."
            )

        symbol = Symbol(name=name, mutable=mutable)
        self._symbols[name] = symbol
        return symbol

    def lookup(self, name: str) -> Symbol:
        if name not in self._symbols:
            raise SemanticError(
                f"Variable '{name}' has not been declared. "
                f"Declare it with 'let {name} = ...' "
                f"or 'const {name} = ...' before using it."
            )

        return self._symbols[name]

    def require_mutable(self, name: str) -> Symbol:
        symbol = self.lookup(name)

        if not symbol.mutable:
            raise SemanticError(
                f"Cannot reassign constant '{name}'. "
                "Use 'let' when declaring a variable "
                "whose value needs to change."
            )

        return symbol