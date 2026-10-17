import argparse
import json
import sys
from pathlib import Path
from dataclasses import fields, is_dataclass
from .parser import Parser as SyntaxParser

def node_to_dict(value):
    if is_dataclass(value):
        return {"type": type(value).__name__, **{field.name: node_to_dict(getattr(value, field.name)) for field in fields(value)}}
    if isinstance(value, list):
        return [node_to_dict(item) for item in value]
    return value

from .lexer import Lexer
from .runtime import run, transpile
from .semantic import check
from .diagnostics import SourceError, ResourceError, resource_error, Span, render

def main():
    parser = argparse.ArgumentParser(description="PyLite 1.1 language runner")
    commands = parser.add_subparsers(dest="command", required=True)
    lex = commands.add_parser("lex", help="Inspect a .lite source file")
    lex.add_argument("file", type=Path)
    lex.add_argument("--json", action="store_true", help="Export token objects as JSON")
    parse = commands.add_parser("parse", help="Inspect the source-located syntax tree")
    parse.add_argument("file", type=Path)
    for command, help_text in (("run", "Execute a PyLite program"), ("check", "Check syntax and declarations without execution"),
                               ("transpile", "Show the generated Python code")):
        subparser = commands.add_parser(command, help=help_text)
        if command == "run":
            input_group = subparser.add_mutually_exclusive_group(required=True)
            input_group.add_argument("file", type=Path, nargs="?")
            input_group.add_argument("-c", "--code", help="Execute PyLite source directly")
        else:
            subparser.add_argument("file", type=Path)
    args = parser.parse_args()
    source = None
    try:
        inline = args.command == "run" and args.code is not None
        source = args.code if inline else args.file.read_bytes().decode("utf-8-sig")
        if args.command == "parse":
            print(json.dumps(node_to_dict(SyntaxParser(source, str(args.file)).parse()), indent=2))
            return 0
        if args.command == "run":
            run(source, "<command>" if inline else str(args.file))
            return 0
        if args.command == "check":
            analysis = check(source)
            for diagnostic in [*analysis.errors, *analysis.warnings]:
                token = next((t for t in Lexer(source).tokenize()
                              if (t.line, t.column) == (diagnostic.line, diagnostic.column)), None)
                span = Span.from_offsets(source, token.start, token.end) if token else None
                print(render(diagnostic.category, diagnostic.message, source, str(args.file), span,
                             line=diagnostic.line), file=sys.stderr)
            if analysis.errors:
                return 1
            print("Syntax is valid. No definite semantic errors."
                  + (" Possible runtime binding errors were reported." if analysis.warnings else ""))
            return 0
        if args.command == "transpile":
            print(transpile(source))
            return 0
        tokens = Lexer(source).tokenize()
        if args.json:
            encoded = []
            for token in tokens:
                try:
                    encoded.append(json.dumps(token.to_dict()))
                except ValueError as error:
                    raise ResourceError(f"Cannot encode token: {error}", token.line, token.column, source) from None
            print("[\n  " + ",\n  ".join(encoded) + "\n]")
        else:
            for token in tokens:
                print(f"{token.line}:{token.column}\t{token.kind:<12}\t{token.lexeme!r}")
    except (RecursionError, MemoryError) as error:
        print(resource_error(error, source), file=sys.stderr)
        return 1
    except UnicodeError as error:
        print(f"PyLite: cannot decode source as UTF-8: {error}", file=sys.stderr)
        return 1
    except ValueError as error:
        print(ResourceError(f"Host conversion limit: {error}", 1, 1, source), file=sys.stderr)
        return 1
    except (SourceError, OSError) as error:
        print(error, file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("PyLite: execution interrupted.", file=sys.stderr)
        return 130
    return 0

if __name__ == "__main__":
    sys.exit(main())
