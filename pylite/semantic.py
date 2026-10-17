"""Conservative declaration analysis of the parser's helper-based Python AST.

No runtime helper or user expression is executed. Binding sets represent all
possible states at a program point; uncertainty is a warning, not a proof.
"""
import ast
from dataclasses import dataclass

from .diagnostics import SourceError, resource_error
from .builtin_names import BUILTIN_NAMES
from .binding_checks import SemanticAnalyzer

ABSENT = frozenset({'absent'})
UNKNOWN = object()


class SemanticError(SourceError):
    category = 'SemanticError'


class SemanticWarning(SourceError):
    category = 'SemanticWarning'


@dataclass
class Analysis:
    tree: ast.Module
    errors: list
    warnings: list


class Analyzer:
    def __init__(self, source):
        self.source = source
        self.issues = {}
        self.position = (1, 1)

    def issue(self, message, call, warning=False):
        line, column = (arg.value for arg in call.args[-2:])
        cls = SemanticWarning if warning else SemanticError
        diagnostic = cls(message, line, column, self.source)
        self.issues[(cls, line, column, message)] = diagnostic

    @staticmethod
    def merge(left, right):
        return {name: left.get(name, ABSENT) | right.get(name, ABSENT)
                for name in left.keys() | right.keys()}

    @staticmethod
    def literal(node):
        # Deliberately small: no folding calls, arithmetic, comparisons or variables.
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.Call) and node.func.id == '_lite_unary':
            value = Analyzer.literal(node.args[1])
            if type(value) in (int, float):
                return value if node.args[0].value == 'PLUS' else -value
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            value = Analyzer.literal(node.operand.args[0])
            if type(value) is bool:
                return not value
        if isinstance(node, ast.Call) and node.func.id == '_lite_condition':
            return Analyzer.literal(node.args[0])
        return UNKNOWN

    def expression(self, node, state):
        if isinstance(node, ast.Call):
            kind = node.func.id.removeprefix('_lite_')
            self.position = tuple(arg.value for arg in node.args[-2:])
            # Arguments are evaluated before the helper's binding check.
            for arg in node.args[:-2]:
                self.expression(arg, state)
            name = node.args[0].value if kind in ('get', 'assign', 'declare', 'call') else None
            binding = state.get(name, ABSENT)
            if kind in ('get', 'assign'):
                if name in BUILTIN_NAMES or (name and name.startswith("__pylite_")):
                    self.issue(f"Name '{name}' is reserved for a built-in function, not a variable.", node)
                elif binding == ABSENT:
                    self.issue(f"Variable '{name}' is not declared. Use 'let {name} = ...' first.", node)
                elif 'absent' in binding:
                    self.issue(f"Variable '{name}' may not be declared; its declaration might not execute.", node, True)
                if kind == 'assign' and 'const' in binding:
                    self.issue(f"Cannot change constant '{name}'." if binding == frozenset({'const'})
                               else f"Variable '{name}' may be a constant and cannot safely be reassigned.",
                               node, binding != frozenset({'const'}))
            elif kind == 'declare':
                if name in BUILTIN_NAMES or (name and name.startswith("__pylite_")):
                    self.issue(f"Name '{name}' is reserved for a built-in function.", node)
                elif 'absent' not in binding:
                    self.issue(f"Name '{name}' is already declared.", node)
                elif binding != ABSENT:
                    self.issue(f"Name '{name}' may already be declared on another path or loop iteration.", node, True)
                # A failed redeclaration cannot replace the original binding.
                new = frozenset({'const' if node.args[2].value else 'mutable'})
                state[name] = (binding - {'absent'}) | new
            elif kind == 'call' and name not in BUILTIN_NAMES:
                self.issue(f"Unknown function '{name}'.", node)
        elif isinstance(node, ast.List):
            for element in node.elts:
                self.expression(element, state)

    def block(self, body, state):
        for node in body:
            if isinstance(node, ast.Expr):
                self.expression(node.value, state)
            elif isinstance(node, ast.If):
                test = node.test.operand if isinstance(node.test, ast.UnaryOp) else node.test
                self.expression(test, state)
                value = self.literal(node.test)
                if value is True:
                    state = self.block(node.body, state)
                elif value is not False:
                    state = self.merge(state, self.block(node.body, state.copy()))
            elif isinstance(node, ast.For):
                self.expression(node.iter, state)
                count = self.literal(node.iter.args[0])
                if type(count) is int and count == 0:
                    continue
                if type(count) is int and count > 0:
                    entry = state.copy()
                    state = self.block(node.body, state)
                    if count > 1 and state != entry:
                        # Binding kinds never change after a successful declaration.
                        # A second pass detects repeat declarations without unrolling.
                        # Stable bindings need no second pass; nested stable loops
                        # must not cause exponential work in a non-executing check.
                        state = self.block(node.body, state)
                elif count is UNKNOWN:
                    entry = state.copy()
                    # Join the back edge to a fixed point. Including the zero path
                    # ensures a possible second iteration is not a definite error.
                    while True:
                        joined = self.merge(entry, self.block(node.body, state.copy()))
                        if joined == state:
                            break
                        state = joined
                # Invalid literal counts never execute their body; runtime diagnoses them.
        return state

    def analyze(self, tree):
        try:
            self.block(tree.body, {})
        except (RecursionError, MemoryError) as error:
            raise resource_error(error, self.source, *self.position) from None
        issues = sorted(self.issues.values(), key=lambda item: (item.line, item.column, item.message))
        return Analysis(tree, [item for item in issues if isinstance(item, SemanticError)],
                        [item for item in issues if isinstance(item, SemanticWarning)])


def check(source):
    """Parse and analyze without execution; return errors and uncertainty warnings."""
    from .compiler import Parser
    return Analyzer(source).analyze(Parser(source).parse())
