import re
import textwrap
from collections.abc import Generator
from typing import Any, Callable, Final, Type

import flask
import inflection
import marshmallow as ma
import werkzeug
import werkzeug.routing
import wrapt
import yaml
from openapi_pydantic_models import OperationObject, PathItemObject

from .schemas_registry import SchemasRegistry


class FlaskPathsManager:
    _ENCOUNTERED_OPERATION_IDS: Final[set[str]] = set()
    _PATH_TEMPLATE_CONVERTER: Final[re.Pattern] = re.compile(r"<([a-z]*:)?([a-z_]*)>")
    ATTRIBUTE_NAME: Final[str] = "_open_api"

    @classmethod
    def generate_operation_id(
        cls, method: str, is_list: bool, response_schema: str | Type[ma.Schema]
    ):
        for_schema = inflection.underscore(
            SchemasRegistry.schema_name(response_schema)
            .replace("Schema", "")
            .replace("Update", "")
            .replace("Create", "")
        )

        if method.lower() == "get":
            return for_schema + "_" + ("list" if is_list else "detail")

        if method.lower() == "post":
            return for_schema + "_" + "create"

        if method.lower() == "patch":
            return for_schema + "_" + "update"

        if method.lower() == "delete":
            return for_schema + "_" + "delete"

        raise ValueError(f'Unsupported method "{method}"!')

    @classmethod
    def decorate(cls, wrapped, open_api_data):
        setattr(wrapped, cls.ATTRIBUTE_NAME, open_api_data)

        @wrapt.decorator
        def wrapper(wrapped, instance, args, kwargs):
            return wrapped(*args, **kwargs)

        return wrapper(wrapped)

    def __init__(
        self,
        app: flask.Flask,
        is_excluded_cb: Callable[[str, str], bool] | None = None,
        overrides: dict[tuple[str, str], OperationObject] | None = None,
    ) -> None:
        self.app = app
        self.is_excluded_cb = is_excluded_cb
        self.overrides: dict[tuple[str, str], OperationObject] = overrides or {}

    def collect_endpoints_docs(
        self,
    ) -> Generator[tuple[str, PathItemObject], None, None]:
        for rule in self.app.url_map.iter_rules():
            operations = self._operations_for_rule(rule)
            if operations:
                yield (
                    self._flask_path_template_to_open_api_path_template(rule.rule),
                    operations,
                )

    def _operations_for_rule(
        self, rule: werkzeug.routing.Rule
    ) -> PathItemObject | None:
        docs_for_methods = [
            _.lower() for _ in (rule.methods or []) if _ not in {"HEAD", "OPTIONS"}
        ]
        view = self.app.view_functions[rule.endpoint]
        retv = PathItemObject()
        any_found = False

        for method in docs_for_methods:
            view_func = self._view_func(view, method)
            method_attr = method.lower() if method.lower() != "delete" else "delete_"

            operation: OperationObject = getattr(
                view_func, self.ATTRIBUTE_NAME, OperationObject()
            )

            if operation.operationId == "hidden":
                # Support for legacy, deprecated behavior
                continue

            # Check for override first, and only then is_excluded_cb
            # If override exists, we don't want to skip docs

            override = self.overrides.get(
                (rule.rule, method.lower()), None
            ) or self.overrides.get((rule.endpoint, method.lower()), None)
            if override:
                setattr(retv, method_attr, override)
                any_found = True
                continue

            if self.is_excluded_cb and self.is_excluded_cb(rule.rule, method):
                setattr(retv, method_attr, None)
                continue

            if not operation.operationId:
                operation.operationId = f"{method}_{rule.endpoint}"

            docstring_data = self._docstring_data(view, method)
            if docstring_data:
                operation_data = operation.model_dump()
                operation_data.update(docstring_data)
                operation = OperationObject.model_validate(operation_data)

            self._register_operation_id(operation)

            setattr(retv, method_attr, operation)
            any_found = True

        return retv if any_found else None

    def _docstring_data(self, view, method: str) -> dict[str, Any] | None:
        f = self._view_func(view, method)

        data = yaml.full_load(textwrap.dedent(f.__doc__ or "")) or {}

        if isinstance(data, str):
            data = {"description": data}

        if data and "description" in data:
            with self.app.test_request_context():
                data["description"] = flask.render_template_string(data["description"])

        if method.lower() in data:
            data = data[method.lower()]

        return data or None

    def _register_operation_id(self, operation: OperationObject):
        if operation.operationId in self.__class__._ENCOUNTERED_OPERATION_IDS:
            operation.operationId = (
                operation.operationId
                + "_"
                + str(
                    len(
                        [
                            _
                            for _ in self.__class__._ENCOUNTERED_OPERATION_IDS
                            if re.match(operation.operationId + r"[_0-9]*$", _)
                        ]
                    )
                )
            )
        self.__class__._ENCOUNTERED_OPERATION_IDS.add(operation.operationId)

    def _view_func(self, view, method):
        if hasattr(view, "view_class"):
            f = getattr(view.view_class, method.lower())
        else:
            f = view
        return f

    @classmethod
    def _flask_path_template_to_open_api_path_template(cls, path: str):
        return cls._PATH_TEMPLATE_CONVERTER.sub(r"{\2}", path)
