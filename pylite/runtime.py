"""Execute transpiled PyLite programs."""

from .parser import Parser
from .transpiler import Transpiler


class PyLiteRuntimeError(Exception):
    """A readable error raised during program execution."""


def repeat_values(count):
    if type(count) is not int or count < 0:
        raise PyLiteRuntimeError(
            "The repeat count must be a nonnegative integer, "
            "such as 0, 1, or 5."
        )

    return range(count)


def double_value(value):
    if type(value) not in (int, float):
        raise PyLiteRuntimeError(
            "double_value expects a number."
        )

    return value * 2


def run(source, filename="<pylite>"):
    program = Parser(source).parse()
    module = Transpiler().transpile(program)
    code = compile(module, filename, "exec")

    declared_names = set()

    def declare(name, value):
        if name in declared_names:
            raise PyLiteRuntimeError(
                f"Variable '{name}' was declared more than once "
                "during execution. Move its declaration before "
                "the loop."
            )

        declared_names.add(name)
        return value

    environment = {
        "__builtins__": {},
        "print": print,
        "double_value": double_value,
        "__pylite_repeat": repeat_values,
        "__pylite_declare": declare,
    }

    try:
        exec(code, environment, environment)

    except PyLiteRuntimeError:
        raise

    except ZeroDivisionError:
        raise PyLiteRuntimeError(
            "Cannot divide by zero. Check the value after '/'."
        ) from None

    except TypeError:
        raise PyLiteRuntimeError(
            "This operation received incompatible values. "
            "Check that the operands have suitable types."
        ) from None

    except NameError as error:
        raise PyLiteRuntimeError(
            f"A variable has no value at this point: {error.name}."
        ) from None

    return {
        name: value
        for name, value in environment.items()
        if name not in {"__builtins__", "print", "double_value"}
        and not name.startswith("__pylite_")
    }