import functools
from typing import Type

import marshmallow as ma
from flask.typing import ResponseReturnValue
from openapi_pydantic_models import (
    MediaTypeObject,
    OperationObject,
    ResponsesObject,
    SecurityRequirementObject,
)

from ..flask_paths import FlaskPathsManager
from ..schemas_registry import SchemasRegistry
from ..securities import Securities
from .helpers import _parameters_from_schema, _update_errors


def get(
    response_schema: Type[ma.Schema],
    *,
    operation_id: str | None = None,
    summary: str | None = None,
    is_list: bool = True,
    has_id_in_path: bool = False,
    errors: dict[int, str] | None = None,
    security: Securities = Securities.access_token,
    additional_content: dict[str, dict | MediaTypeObject] | None = None,
    tags_override: list[str] | None = None,
) -> functools.partial[ResponseReturnValue]:
    """
    Decorator that will inject standard sets of our OpenAPI GET docs into decorated
    method.
    """
    open_api_data = OperationObject()

    open_api_data.operationId = operation_id or FlaskPathsManager.generate_operation_id(
        "get", is_list, response_schema
    )
    _parameters_from_schema(
        response_schema,
        requires_id_in_path=has_id_in_path,
        open_api_data=open_api_data,
    )

    open_api_data.responses = ResponsesObject()
    open_api_data.responses["200"] = {
        "content": {
            "application/json": {
                "schema": {"$ref": SchemasRegistry.schema_ref(response_schema)}
            }
        }
    }

    if security != Securities.no_token:
        open_api_data.security = [SecurityRequirementObject({f"{security.name}": []})]

    if additional_content:
        for content_type, media in additional_content.items():
            if not isinstance(media, MediaTypeObject):
                media = MediaTypeObject(**media)
            open_api_data.responses["200"].content[content_type] = media

    tags = tags_override or getattr(response_schema.opts, "tags", None)
    if tags:
        open_api_data.tags = tags

    open_api_data.tags = list(set(open_api_data.tags or []))

    open_api_data.summary = summary

    _update_errors(open_api_data, errors)

    return functools.partial(FlaskPathsManager.decorate, open_api_data=open_api_data)


def get_list(
    response_schema: Type[ma.Schema],
    *,
    operation_id: str | None = None,
    summary: str | None = None,
    errors: dict[int, str] | None = None,
    security: Securities = Securities.access_token,
    additional_content: dict[str, dict | MediaTypeObject] | None = None,
    tags_override: list[str] | None = None,
) -> functools.partial[ResponseReturnValue]:
    return get(
        response_schema,
        operation_id=operation_id,
        summary=summary,
        errors=errors,
        security=security,
        additional_content=additional_content,
        tags_override=tags_override,
        is_list=True,
        has_id_in_path=False,
    )


def get_detail(
    response_schema: Type[ma.Schema],
    *,
    operation_id: str | None = None,
    summary: str | None = None,
    errors: dict[int, str] | None = None,
    security: Securities = Securities.access_token,
    additional_content: dict[str, dict | MediaTypeObject] | None = None,
    tags_override: list[str] | None = None,
) -> functools.partial[ResponseReturnValue]:
    return get(
        response_schema,
        operation_id=operation_id,
        summary=summary,
        errors=errors,
        security=security,
        additional_content=additional_content,
        tags_override=tags_override,
        is_list=False,
        has_id_in_path=True,
    )
