"""Convert PyLite syntax nodes into Python AST."""

import ast

from .nodes import (
    Assignment,
    Binary,
    Call,
    Conditional,
    Declaration,
    ExpressionStatement,
    Literal,
    Name,
    Repeat,
    Unary,
)
from .semantic import SemanticAnalyzer


class Transpiler:
    def transpile(self, program):
        SemanticAnalyzer().analyze(program)
        self.source = program.source

        module = ast.Module(
            body=[
                self.statement(node)
                for node in program.statements
            ],
            type_ignores=[],
        )

        return ast.fix_missing_locations(module)

    def statement(self, node):
        return self.locate(self._statement(node), node.span)

    def locate(self, result, span):
        if span is None:
            return result

        def byte_column(offset):
            start = max(self.source.rfind("\n", 0, offset),
                        self.source.rfind("\r", 0, offset)) + 1
            return len(self.source[start:offset].encode("utf-8"))

        # Synthetic helper nodes inherit their originating operation;
        # child expressions retain their more precise positions.
        def visit(tree):
            if isinstance(tree, (ast.expr, ast.stmt)) and not hasattr(tree, "lineno"):
                tree.lineno = span.line
                tree.col_offset = byte_column(span.start)
                tree.end_lineno = span.end_line
                tree.end_col_offset = byte_column(span.end)
            for child in ast.iter_child_nodes(tree):
                visit(child)

        visit(result)
        return result

    def _statement(self, node):
        if isinstance(node, Declaration):
            return ast.Assign(
                targets=[
                    ast.Name(id=node.name, ctx=ast.Store())
                ],
                value=ast.Call(
                    func=ast.Name(
                        id="__pylite_declare",
                        ctx=ast.Load(),
                    ),
                    args=[
                        ast.Constant(value=node.name),
                        self.expression(node.value),
                    ],
                    keywords=[],
                ),
            )

        if isinstance(node, Assignment):
            return ast.Assign(
                targets=[
                    ast.Name(id=node.name, ctx=ast.Store())
                ],
                value=self.expression(node.value),
            )

        if isinstance(node, ExpressionStatement):
            return ast.Expr(
                value=self.expression(node.expression)
            )

        if isinstance(node, Conditional):
            condition = self.expression(node.condition)

            if node.inverted:
                condition = ast.UnaryOp(
                    op=ast.Not(),
                    operand=condition,
                )

            return ast.If(
                test=condition,
                body=self.body(node.body),
                orelse=[],
            )

        if isinstance(node, Repeat):
            return ast.For(
                target=ast.Name(
                    id="__pylite_loop_index",
                    ctx=ast.Store(),
                ),
                iter=ast.Call(
                    func=ast.Name(
                        id="__pylite_repeat",
                        ctx=ast.Load(),
                    ),
                    args=[
                        self.expression(node.count)
                    ],
                    keywords=[],
                ),
                body=self.body(node.body),
                orelse=[],
            )

        raise TypeError(
            f"Unsupported statement: {type(node).__name__}"
        )

    def body(self, statements):
        # Python requires at least one statement in each block.
        return [
            self.statement(node)
            for node in statements
        ] or [ast.Pass()]

    def expression(self, node):
        return self.locate(self._expression(node), node.span)

    def _expression(self, node):
        if isinstance(node, Literal):
            return ast.Constant(value=node.value)

        if isinstance(node, Name):
            return ast.Name(
                id=node.identifier,
                ctx=ast.Load(),
            )

        if isinstance(node, Unary):
            operators = {
                "+": ast.UAdd,
                "-": ast.USub,
            }

            if node.operator not in operators:
                raise TypeError(
                    f"Unsupported unary operator: {node.operator}"
                )

            return ast.UnaryOp(
                op=operators[node.operator](),
                operand=self.expression(node.operand),
            )

        if isinstance(node, Binary):
            arithmetic = {
                "+": ast.Add,
                "-": ast.Sub,
                "*": ast.Mult,
                "/": ast.Div,
            }

            comparisons = {
                "==": ast.Eq,
                "!=": ast.NotEq,
                "<": ast.Lt,
                ">": ast.Gt,
                "<=": ast.LtE,
                ">=": ast.GtE,
            }

            left = self.expression(node.left)
            right = self.expression(node.right)

            if node.operator in arithmetic:
                return ast.BinOp(
                    left=left,
                    op=arithmetic[node.operator](),
                    right=right,
                )

            if node.operator in comparisons:
                return ast.Compare(
                    left=left,
                    ops=[comparisons[node.operator]()],
                    comparators=[right],
                )

            raise TypeError(
                f"Unsupported binary operator: {node.operator}"
            )

        if isinstance(node, Call):
            return ast.Call(
                func=ast.Name(
                    id=node.function,
                    ctx=ast.Load(),
                ),
                args=[
                    self.expression(argument)
                    for argument in node.arguments
                ],
                keywords=[],
            )

        raise TypeError(
            f"Unsupported expression: {type(node).__name__}"
        )
