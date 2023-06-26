import functools
from typing import List, Optional, Type

import marshmallow
from openapi_pydantic_models import ParameterObject

from ..schemas_registry import SchemasRegistry
from ..securities import Securities
from .helpers import _decorate, _generate_operation_id, _initial_docs, _update_errors


def post(
    request_schema: Type[marshmallow.Schema],
    response_schema: Type[marshmallow.Schema] | None = None,
    operation_id: Optional[str] = None,
    summary: Optional[str] = None,
    errors: Optional[dict] = None,
    headers: Optional[List[dict]] = None,
    security: Securities = Securities.access_token,
    additional_parameters: list[ParameterObject] | None = None,
):
    """
    Decorator that will inject standard sets of our OpenAPI POST docs into decorated
    method.
    """

    if not response_schema:
        response_schema = request_schema

    if not operation_id:
        operation_id = _generate_operation_id("post", False, response_schema)

    open_api_data = _initial_docs(request_schema)
    open_api_data["operationId"] = operation_id
    if security != Securities.no_token:
        open_api_data["security"] = [{f"{security.name}": []}]

    # TODO: This convention of having "create" in schema name makes our code smelly,
    # come up with something more explicit
    if "deleted" in SchemasRegistry.schema_name(response_schema).lower():
        open_api_data["responses"]["204"] = {"description": "Resource was deleted"}

    else:
        open_api_data["responses"]["201"] = {
            "content": {
                "application/json": {
                    "schema": {"$ref": SchemasRegistry.schema_ref(response_schema)}
                }
            },
            "description": "",
        }

    open_api_data["requestBody"] = {
        "content": {
            "application/json": {
                "schema": {"$ref": SchemasRegistry.schema_ref(request_schema)}
            }
        }
    }
    if summary:
        open_api_data["summary"] = summary

    url_id_field = getattr(request_schema.opts, "url_id_field", None)
    # TODO: This convention of having "create" in schema name makes our code smelly,
    # come up with something more explicit
    if (
        url_id_field
        and "create" not in SchemasRegistry.schema_name(request_schema).lower()
    ):
        open_api_data["parameters"][0]["name"] = url_id_field
    else:
        del open_api_data["parameters"]

    if additional_parameters:
        open_api_data["parameters"] = open_api_data.get("parameters", []) + [
            _.dict() for _ in additional_parameters
        ]

    if "parameters" in open_api_data:
        open_api_data["parameters"] = [
            _ for _ in open_api_data["parameters"] if (_["name"])
        ]
        if not open_api_data["parameters"]:
            del open_api_data["parameters"]

    tags = getattr(request_schema.opts, "tags", None) or getattr(
        response_schema.opts, "tags", None
    )
    if tags:
        open_api_data["tags"] = tags

    _update_errors(open_api_data, errors)

    if headers:
        if "parameters" not in open_api_data:
            open_api_data["parameters"] = []
        for header in headers:
            header["in"] = "header"
            open_api_data["parameters"].append(header)

    return functools.partial(_decorate, open_api_data={"post": open_api_data})
