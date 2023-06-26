import functools
import textwrap
from typing import Optional

import inflection
import wrapt

from ..schemas_registry import SchemasRegistry
from ..flask_paths import FlaskPathsManager


def _generate_operation_id(method, many, response_schema):
    for_schema = inflection.underscore(
        SchemasRegistry.schema_name(response_schema)
        .replace("Schema", "")
        .replace("Update", "")
        .replace("Create", "")
    )

    if method == "get":
        return for_schema + "_" + ("list" if many else "detail")

    if method == "post":
        return for_schema + "_" + "create"

    if method == "patch":
        return for_schema + "_" + "update"

    if method == "delete":
        return for_schema + "_" + "delete"


def hide_doc():
    return functools.partial(
        _decorate, open_api_data={"post": {"operationId": "hidden"}}
    )


def _update_errors(open_api_data: dict, errors: Optional[dict]):
    for code, description in (errors or {}).items():
        code, body = _error_response(code, description)
        open_api_data["responses"][code] = body


def _error_response(code, description):
    return (
        str(code),
        {
            # "content": {
            #     "application/json": {
            #         # "type": "object"
            #         # TODO: Current version of ReDoc fails to parse JSON:Schema
            #         #       referenced in below links. For that reason, we'd removed
            #         #       them from docs. If/when ReDoc is fixed, we should add them
            #         #       back in.
            #         # "schema": {
            #         #     "$ref": "https://jsonapi.org/schema#/definitions/failure"
            #         # }
            #     }
            # },
            "description": textwrap.dedent(str(description)),
        },
    )


def _decorate(wrapped, open_api_data):
    @wrapt.decorator
    def wrapper(wrapped, instance, args, kwargs):
        return wrapped(*args, **kwargs)

    if not hasattr(wrapped, FlaskPathsManager.ATTRIBUTE_NAME):
        setattr(wrapped, FlaskPathsManager.ATTRIBUTE_NAME, dict())
    getattr(wrapped, FlaskPathsManager.ATTRIBUTE_NAME).update(open_api_data)

    return wrapper(wrapped)


def _initial_docs(schema_cls):
    id_field = getattr(schema_cls, "_declared_fields", dict()).get("id", None)
    id_field_type = "integer"
    if id_field and "String" in str(id_field):
        id_field_type = "string"

    retv = {
        "operationId": None,
        "responses": {
            # code: description
            # for code, description in [
            #     _error_response("4XX", "Client side errors"),
            #     _error_response("5XX", "Server side errors"),
            # ]
        },
        "parameters": [
            {
                "name": "id",
                "in": "path",
                "required": True,
                "schema": {"type": id_field_type},
            }
        ],
    }

    return retv
