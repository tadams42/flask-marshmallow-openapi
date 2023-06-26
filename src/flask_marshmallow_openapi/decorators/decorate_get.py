import functools
from typing import Optional

from openapi_pydantic_models import ParameterObject

from ..schemas_registry import SchemasRegistry
from ..securities import Securities
from .helpers import _decorate, _generate_operation_id, _initial_docs, _update_errors


def get(
    response_schema,
    operation_id: Optional[str] = None,
    summary: str = "",
    many: bool = False,
    errors: dict | None = None,
    security: Securities = Securities.access_token,
    additional_content: dict | None = None,
    additional_parameters: list[ParameterObject] | None = None,
    tags_override: list[str] | None = None,
):
    """
    Decorator that will inject standard sets of our OpenAPI GET docs into decorated
    method.
    """

    if not operation_id:
        operation_id = _generate_operation_id("get", many, response_schema)

    open_api_data = _initial_docs(response_schema)
    open_api_data["operationId"] = operation_id
    open_api_data["responses"]["200"] = {
        "content": {
            "application/json": {
                "schema": {"$ref": SchemasRegistry.schema_ref(response_schema)}
            }
        },
        "description": "",
    }

    if security != Securities.no_token:
        open_api_data["security"] = [{f"{security.name}": []}]

    if additional_content:
        for k, v in additional_content.items():
            open_api_data["responses"]["200"]["content"][k] = v

    if many:
        del open_api_data["parameters"]
    else:
        try:
            open_api_data["parameters"][0]["name"] = response_schema.opts.url_id_field
        except AttributeError:
            # It is perfectly fine to use GET on URLs that don't have ID field and
            # are described by schemas that don't have that field either.
            pass

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

    tags = tags_override or getattr(response_schema.opts, "tags", None)
    if tags:
        open_api_data["tags"] = tags

    if summary:
        open_api_data["summary"] = summary

    _update_errors(open_api_data, errors)

    return functools.partial(_decorate, open_api_data={"get": open_api_data})
