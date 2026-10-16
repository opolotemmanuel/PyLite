import argparse
import json
import sys
from pathlib import Path
from .lexer import Lexer, LexError

def main():
    parser = argparse.ArgumentParser(description="PyLite 1.0 token inspector")
    commands = parser.add_subparsers(dest="command", required=True)
    lex = commands.add_parser("lex", help="Inspect a .lite source file")
    lex.add_argument("file", type=Path)
    lex.add_argument("--json", action="store_true", help="Export token objects as JSON")
    args = parser.parse_args()
    try:
        source = args.file.read_bytes().decode("utf-8-sig")
        tokens = Lexer(source).tokenize()
        if args.json:
            print(json.dumps([token.to_dict() for token in tokens], indent=2))
        else:
            for token in tokens:
                print(f"{token.line}:{token.column}\t{token.kind:<12}\t{token.lexeme!r}")
    except (LexError, OSError, UnicodeError, ValueError) as error:
        print(error, file=sys.stderr)
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
