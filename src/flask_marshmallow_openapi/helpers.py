import importlib
import inspect
from typing import Optional, Set, Tuple, Type, Union

import marshmallow


def schema_ref(schema: Union[str, Type[marshmallow.Schema]]) -> str:
    return f"#/components/schemas/{schema_name(schema)}"


def schema_name(schema: Union[str, Type[marshmallow.Schema]]) -> Optional[str]:
    if schema:
        return (schema if isinstance(schema, str) else schema.__name__).replace(
            "Schema", ""
        )
    else:
        return None


_KNOWN_SCHEMAS: Set[Tuple[str, Type[marshmallow.Schema]]] = set()


def all_schemas() -> Set[Tuple[str, Type[marshmallow.Schema]]]:
    return _KNOWN_SCHEMAS


def main_schema_cls(
    other_schema: Union[str, marshmallow.Schema]
) -> Type[marshmallow.Schema]:
    """
    Given ie. class FooCreateSchema or name "FooCreateSchema", returns class FooSchema.
    """
    try:
        other_schema = other_schema.__name__
    except AttributeError:
        pass

    other_schema = other_schema.replace("Create", "").replace("Update", "")

    retv = next((_[1] for _ in all_schemas() if _[1].__name__ == other_schema), None)

    if not retv:
        raise RuntimeError(f"Couldn't find main schema for {other_schema}!")

    return retv


def find_all_schemas(
    app_package_name: str,
) -> Set[Tuple[str, Type[marshmallow.Schema]]]:
    global _KNOWN_SCHEMAS

    if _KNOWN_SCHEMAS:
        return _KNOWN_SCHEMAS

    modules = [
        _[1]
        for _ in inspect.getmembers(
            importlib.import_module(".", app_package_name), inspect.ismodule
        )
    ]

    clss = {
        _[1]
        for _ in inspect.getmembers(
            importlib.import_module(".", app_package_name), inspect.isclass
        )
    }

    for klass in {
        _
        for module_ in modules
        for name, _ in inspect.getmembers(module_, inspect.isclass)
    }.union(clss):
        if (
            issubclass(klass, marshmallow.Schema)
            and klass.__name__ != "Schema"
            and klass.__name__ != "JsonApiSchema"
        ):
            _KNOWN_SCHEMAS.add(
                (
                    schema_name(klass),
                    klass,
                )
            )

    return _KNOWN_SCHEMAS
