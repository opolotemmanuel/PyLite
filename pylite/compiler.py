"""Compile the shared, source-located syntax tree to guarded runtime helper AST.

The package-level Parser facade retains the completed project's AST API while
pylite.parser.Parser preserves the workspace's syntax-node API. Both use one grammar.
"""
import ast
from .nodes import (Assignment, Binary, Call, Conditional, Declaration,
                    ExpressionStatement, Literal, Name, Repeat, Unary)
from .parser import Parser as SyntaxParser
from .transpiler import Transpiler as NativeTranspiler
from .diagnostics import Span, resource_error
from .lexer import Lexer

OPS = {'+':'PLUS','-':'MINUS','*':'STAR','/':'SLASH','==':'EQ','!=':'NE',
       '<':'LT','>':'GT','<=':'LE','>=':'GE'}


class Compiler(NativeTranspiler):
    def transpile(self, program):
        self.source = program.source
        self.tokens = Lexer(self.source).tokenize()
        self.loop_id = 0
        try:
            tree = ast.Module(body=[self.statement(n) for n in program.statements], type_ignores=[])
            return ast.fix_missing_locations(tree)
        except (RecursionError, MemoryError) as error:
            raise resource_error(error, self.source) from None

    def helper(self, name, args, node, binding=False):
        span = (node.focus if binding else None) or node.span
        if isinstance(node, Binary):
            token = next((t for t in self.tokens if t.lexeme == node.operator
                          and node.left.span.end <= t.start < node.right.span.start), None)
            if token:
                span = Span.from_offsets(self.source, token.start, token.end)
        line, column = (span.line, span.column) if span else (1, 1)
        return ast.Call(func=ast.Name(id='_lite_' + name, ctx=ast.Load()),
                        args=[*args, ast.Constant(line), ast.Constant(column)], keywords=[])

    def _statement(self, node):
        if isinstance(node, Declaration):
            return ast.Expr(self.helper('declare', [ast.Constant(node.name), self.expression(node.value),
                                                   ast.Constant(not node.mutable)], node, True))
        if isinstance(node, Assignment):
            return ast.Expr(self.helper('assign', [ast.Constant(node.name), self.expression(node.value)], node, True))
        if isinstance(node, ExpressionStatement):
            return ast.Expr(self.expression(node.expression))
        if isinstance(node, Conditional):
            condition = self.helper('condition', [self.expression(node.condition)], node)
            if node.inverted:
                condition = ast.UnaryOp(op=ast.Not(), operand=condition)
            return ast.If(test=condition, body=self.body(node.body), orelse=[])
        if isinstance(node, Repeat):
            self.loop_id += 1
            return ast.For(target=ast.Name(id=f'_lite_loop_{self.loop_id}', ctx=ast.Store()),
                           iter=self.helper('repeat', [self.expression(node.count)], node),
                           body=self.body(node.body), orelse=[])
        raise TypeError(f'Unsupported statement: {type(node).__name__}')

    def _expression(self, node):
        if isinstance(node, Literal):
            return ast.Constant(node.value)
        if isinstance(node, Name):
            return self.helper('get', [ast.Constant(node.identifier)], node, True)
        if isinstance(node, Unary):
            return self.helper('unary', [ast.Constant(OPS[node.operator]), self.expression(node.operand)], node)
        if isinstance(node, Binary):
            return self.helper('binary', [ast.Constant(OPS[node.operator]), self.expression(node.left),
                                         self.expression(node.right)], node)
        if isinstance(node, Call):
            return self.helper('call', [ast.Constant(node.function),
                                       ast.List(elts=[self.expression(n) for n in node.arguments], ctx=ast.Load())], node, True)
        raise TypeError(f'Unsupported expression: {type(node).__name__}')


class Parser:
    def __init__(self, source, filename='<pylite>'):
        self.source, self.filename = source, filename

    def parse(self):
        return Compiler().transpile(SyntaxParser(self.source, self.filename).parse())
