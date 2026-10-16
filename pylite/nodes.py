"""Syntax tree nodes produced by the PyLite parser."""

from dataclasses import dataclass


class Expression:
    """Base class for expressions."""


class Statement:
    """Base class for statements."""


@dataclass
class Literal(Expression):
    value: int | str | bool


@dataclass
class Name(Expression):
    identifier: str


@dataclass
class Unary(Expression):
    operator: str
    operand: Expression


@dataclass
class Binary(Expression):
    left: Expression
    operator: str
    right: Expression


@dataclass
class Call(Expression):
    function: str
    arguments: list[Expression]


@dataclass
class Declaration(Statement):
    name: str
    value: Expression
    mutable: bool


@dataclass
class Assignment(Statement):
    name: str
    value: Expression


@dataclass
class ExpressionStatement(Statement):
    expression: Expression


@dataclass
class Conditional(Statement):
    condition: Expression
    body: list[Statement]
    inverted: bool = False


@dataclass
class Repeat(Statement):
    count: Expression
    body: list[Statement]


@dataclass
class Program:
    statements: list[Statement]