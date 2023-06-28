import importlib
import inspect
from typing import Type

import marshmallow as ma

_KNOWN_SCHEMAS: dict[str, Type[ma.Schema]] = dict()


class SchemasRegistry:
    @classmethod
    def schema_ref(cls, schema: str | Type[ma.Schema]) -> str:
        return f"#/components/schemas/{cls.schema_name(schema)}"

    @classmethod
    def schema_name(cls, schema: str | Type[ma.Schema]) -> str:
        return (schema if isinstance(schema, str) else schema.__name__).replace(
            "Schema", ""
        )

    @classmethod
    def all_schemas(cls) -> dict[str, Type[ma.Schema]]:
        return _KNOWN_SCHEMAS

    @classmethod
    def main_schema_cls(
        cls, other_schema: str | ma.Schema | Type[ma.Schema]
    ) -> Type[ma.Schema]:
        """
        Given ie. class FooCreateSchema or name "FooCreateSchema", returns class
        FooSchema.
        """
        name = None
        if isinstance(other_schema, ma.Schema):
            name = other_schema.__class__.__name__
        elif isinstance(other_schema, str):
            name = other_schema
        else:
            try:
                name = other_schema.__name__
            except AttributeError:
                pass

        if not name:
            raise TypeError(f"Couldn't find schema name for {other_schema}!")

        name = name.replace("Create", "").replace("Update", "").replace("Schema", "")
        retv = _KNOWN_SCHEMAS.get(name, None)
        if not retv:
            raise RuntimeError(f"Couldn't find main schema for {other_schema}!")

        return retv

    @classmethod
    def find_all_schemas(cls, app_package_name: str) -> dict[str, Type[ma.Schema]]:
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
                issubclass(klass, ma.Schema)
                and klass.__name__ != "Schema"
                and klass.__name__ != "JsonApiSchema"
            ):
                _KNOWN_SCHEMAS[cls.schema_name(klass)] = klass

        return _KNOWN_SCHEMAS


def main_schema_cls(other_schema: str | ma.Schema) -> Type[ma.Schema]:
    """
    Given ie. class FooCreateSchema or name "FooCreateSchema", returns class
    FooSchema.
    """
    return SchemasRegistry.main_schema_cls(other_schema)
