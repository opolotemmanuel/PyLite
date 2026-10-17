"""Source-located diagnostics shared by each language stage."""


class SourceError(Exception):
    category = 'Error'

    def __init__(self, message, line, column, source=None):
        self.message, self.line, self.column = message, line, column
        text = f'PyLite {self.category} [Line {line}, Col {column}]: {message}'
        if source is not None:
            # str.splitlines also splits characters permitted inside string values.
            lines = source.replace('\r\n', '\n').replace('\r', '\n').split('\n')
            snippet = lines[line - 1].expandtabs(4) if 0 < line <= len(lines) else ''
            prefix = f'{line} | '
            text += f"\n{prefix}{snippet}\n{' ' * (len(prefix) + column - 1)}^"
        super().__init__(text)


class ResourceError(SourceError):
    category = 'ResourceError'


def resource_error(error, source=None, line=1, column=1):
    message = ('Program nesting or expression depth exceeds the host limit.'
               if isinstance(error, RecursionError) else 'Not enough memory to process this program.')
    return ResourceError(message, line, column, source)


"""Source spans and shared diagnostic rendering.

Offsets count Unicode characters; AST columns count UTF-8 bytes.
"""
import re
from dataclasses import dataclass


def source_lines(source):
    """Split physical lines without treating Unicode string content as newlines."""
    return re.split(r"(?<=\n)|(?<=\r)(?!\n)", source)


@dataclass(frozen=True)
class Span:
    start: int
    end: int
    line: int
    column: int
    end_line: int
    end_column: int

    @classmethod
    def from_offsets(cls, source, start, end):
        def position(offset):
            # split on physical newlines only, as the lexer does.
            parts = re.split(r'\r\n|\r|\n', source[:offset])
            return len(parts), len(parts[-1].expandtabs(4)) + 1
        return cls(start, end, *position(start), *position(end))


def render(kind, message, source, filename, span, *, line=None):
    if span is None:
        # Traceback line numbers remain available without instruction ranges.
        lines = source_lines(source)
        snippet = lines[line - 1].rstrip("\r\n").expandtabs(4)
        return (f'PyLite {kind} [{filename}, Line {line}]:\n'
                f'{message}\n{line} | {snippet}')
    lines = source_lines(source)
    snippet = lines[span.line - 1].rstrip("\r\n").expandtabs(4) if span.line <= len(lines) else ''
    prefix = f'{span.line} | '
    width = max(1, (span.end_column if span.end_line == span.line else len(snippet) + 1) - span.column)
    return (f'PyLite {kind} [{filename}, Line {span.line}, Col {span.column}]:\n'
            f'{message}\n{prefix}{snippet}\n'
            f'{" " * (len(prefix) + span.column - 1)}{"^" * width}')
