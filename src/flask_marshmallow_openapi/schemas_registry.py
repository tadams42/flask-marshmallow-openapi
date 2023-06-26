import importlib
import inspect
from typing import Optional, Set, Tuple, Type, Union

import marshmallow

_KNOWN_SCHEMAS: Set[Tuple[str, Type[marshmallow.Schema]]] = set()


class SchemasRegistry:
    @classmethod
    def schema_ref(cls, schema: Union[str, Type[marshmallow.Schema]]) -> str:
        return f"#/components/schemas/{cls.schema_name(schema)}"

    @classmethod
    def schema_name(cls, schema: Union[str, Type[marshmallow.Schema]]) -> Optional[str]:
        if schema:
            return (schema if isinstance(schema, str) else schema.__name__).replace(
                "Schema", ""
            )
        else:
            return None

    @classmethod
    def all_schemas(cls) -> Set[Tuple[str, Type[marshmallow.Schema]]]:
        return _KNOWN_SCHEMAS

    @classmethod
    def main_schema_cls(
        cls, other_schema: Union[str, marshmallow.Schema]
    ) -> Type[marshmallow.Schema]:
        """
        Given ie. class FooCreateSchema or name "FooCreateSchema", returns class FooSchema.
        """
        try:
            other_schema = other_schema.__name__
        except AttributeError:
            pass

        other_schema = other_schema.replace("Create", "").replace("Update", "")

        retv = next(
            (_[1] for _ in cls.all_schemas() if _[1].__name__ == other_schema), None
        )

        if not retv:
            raise RuntimeError(f"Couldn't find main schema for {other_schema}!")

        return retv

    @classmethod
    def find_all_schemas(
        cls,
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
                        cls.schema_name(klass),
                        klass,
                    )
                )

        return _KNOWN_SCHEMAS


def main_schema_cls(
    other_schema: Union[str, marshmallow.Schema]
) -> Type[marshmallow.Schema]:
    return SchemasRegistry.main_schema_cls(other_schema)
