import functools
from typing import Optional, Type

import marshmallow

from ..securities import Securities
from ..schemas_registry import SchemasRegistry
from .helpers import _decorate, _generate_operation_id, _initial_docs, _update_errors


def patch(
    request_schema: Type[marshmallow.Schema],
    response_schema: Optional[Type[marshmallow.Schema]] = None,
    operation_id: Optional[str] = None,
    errors: Optional[dict] = None,
    additional_content: Optional[dict] = None,
    security: Securities = Securities.access_token,
):
    """
    Decorator that will inject standard sets of our OpenAPI PATCH docs into decorated
    method.
    """

    if not response_schema:
        response_schema = request_schema

    if not operation_id:
        operation_id = _generate_operation_id("patch", False, response_schema)

    open_api_data = _initial_docs(request_schema)
    open_api_data["operationId"] = operation_id
    if security != Securities.no_token:
        open_api_data["security"] = [{f"{security.name}": []}]
    open_api_data["responses"]["200"] = {
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

    if additional_content:
        for content_type, schema in additional_content.items():
            open_api_data["requestBody"]["content"][content_type] = schema

    open_api_data["parameters"][0]["name"] = response_schema.opts.url_id_field

    tags = getattr(request_schema.opts, "tags", None) or getattr(
        response_schema.opts, "tags", None
    )
    if tags:
        open_api_data["tags"] = tags

    _update_errors(open_api_data, errors)

    return functools.partial(_decorate, open_api_data={"patch": open_api_data})
