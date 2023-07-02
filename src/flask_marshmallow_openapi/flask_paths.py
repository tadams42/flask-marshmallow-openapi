import re
import textwrap
from collections.abc import Generator
from typing import Any, Final, Type

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

    def __init__(self, app: flask.Flask) -> None:
        self.app = app

    def collect_endpoints_docs(
        self,
    ) -> Generator[tuple[str, PathItemObject], None, None]:
        for rule in self.app.url_map.iter_rules():
            if self._should_document_enpdpoint(rule.endpoint):
                path, operations = self._path_for(rule)
                if path and operations:
                    yield path, operations

    @classmethod
    def _should_document_enpdpoint(cls, name: str) -> bool:
        # Reduce spam in docs
        return (
            "_relationships_" not in name
            and ".docs." not in name
            and "static" not in name
        )

    def _operations_for_rule(
        self, rule: werkzeug.routing.Rule
    ) -> PathItemObject | None:
        supported_methods = [
            _.lower() for _ in rule.methods if _ not in ["HEAD", "OPTIONS"]
        ]
        view = self.app.view_functions[rule.endpoint]

        retv = PathItemObject()

        for method in supported_methods:
            view_func = self._view_func(view, method)

            operation: OperationObject = getattr(
                view_func, self.ATTRIBUTE_NAME, OperationObject()
            )

            if operation.operationId == "hidden":
                continue

            if not operation.operationId:
                operation.operationId = f"{method}_{rule.endpoint}"

            docstring_data = self._docstring_data(view, method)
            if docstring_data:
                operation_data = operation.model_dump()
                operation_data.update(docstring_data)
                operation = OperationObject.model_validate(operation_data)

            self._register_operation_id(operation)

            if method.lower() == "delete":
                setattr(retv, "delete_", operation)
            else:
                setattr(retv, method.lower(), operation)

        return retv

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

    def _path_for(
        self, rule: werkzeug.routing.Rule
    ) -> tuple[str | None, PathItemObject | None]:
        # Bug in apispec_webframeworks.flask.FlaskPlugin only adds single path for each
        # inspected view.
        # https://github.com/ma-code/apispec-webframeworks/issues/14
        #
        # Thus, we implement our own inspection
        operations = self._operations_for_rule(rule)
        if operations:
            return (
                self._flask_path_template_to_open_api_path_template(rule.rule),
                operations,
            )
        return None, None

    @classmethod
    def _flask_path_template_to_open_api_path_template(cls, path: str):
        return cls._PATH_TEMPLATE_CONVERTER.sub(r"{\2}", path)
