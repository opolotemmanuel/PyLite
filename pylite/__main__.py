"""Command-line interface for PyLite."""

import argparse
import json
import sys
from dataclasses import fields, is_dataclass
from pathlib import Path

from .lexer import Lexer, LexError
from .parser import Parser, ParseError
from .runtime import run, PyLiteRuntimeError
from .semantic import SemanticAnalyzer
from .symbols import SemanticError


def node_to_dict(value):
    if is_dataclass(value):
        return {
            "type": type(value).__name__,
            **{
                field.name: node_to_dict(getattr(value, field.name))
                for field in fields(value)
            },
        }

    if isinstance(value, list):
        return [node_to_dict(item) for item in value]

    return value


def main():
    parser = argparse.ArgumentParser(description="PyLite language tools")
    commands = parser.add_subparsers(dest="command", required=True)

    lex = commands.add_parser("lex", help="Inspect a .lite token stream")
    lex.add_argument("file", type=Path)
    lex.add_argument("--json", action="store_true")

    parse = commands.add_parser("parse", help="Inspect a .lite syntax tree")
    parse.add_argument("file", type=Path)

    check = commands.add_parser(
        "check", help="Check syntax and variable binding rules"
    )
    check.add_argument("file", type=Path)

    execute = commands.add_parser("run", help="Execute a .lite program")
    execute.add_argument("file", type=Path)

    args = parser.parse_args()

    try:
        source = args.file.read_bytes().decode("utf-8-sig")

        if args.command == "run":
            run(source, filename=str(args.file))

        elif args.command == "check":
            program = Parser(source).parse()
            SemanticAnalyzer().analyze(program)
            print(f"{args.file}: semantic checks passed")

        elif args.command == "parse":
            program = Parser(source).parse()
            print(json.dumps(node_to_dict(program), indent=2))

        else:
            tokens = Lexer(source).tokenize()

            if args.json:
                print(json.dumps(
                    [token.to_dict() for token in tokens],
                    indent=2,
                ))
            else:
                for token in tokens:
                    print(
                        f"{token.line}:{token.column}\t"
                        f"{token.kind:<12}\t{token.lexeme!r}"
                    )

    except (
        LexError,
        ParseError,
        SemanticError,
        PyLiteRuntimeError,
        OSError,
        UnicodeError,
        ValueError,
    ) as error:
        print(error, file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())