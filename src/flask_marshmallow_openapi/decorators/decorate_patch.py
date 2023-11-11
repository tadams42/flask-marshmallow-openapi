import functools
from typing import Type

import marshmallow as ma
from flask.typing import ResponseReturnValue
from openapi_pydantic_models import (
    MediaTypeObject,
    OperationObject,
    RequestBodyObject,
    ResponsesObject,
    SecurityRequirementObject,
)

from ..flask_paths import FlaskPathsManager
from ..schemas_registry import SchemasRegistry
from ..securities import Securities
from .helpers import _parameters_from_schema, _update_errors


def patch(
    request_schema: Type[ma.Schema],
    response_schema: Type[ma.Schema] | None = None,
    *,
    operation_id: str | None = None,
    has_id_in_path: bool = True,
    errors: dict[int, str] | None = None,
    additional_content: dict[str, dict | MediaTypeObject] | None = None,
    security: Securities = Securities.access_token,
) -> functools.partial[ResponseReturnValue]:
    """
    Decorator that will inject standard sets of our OpenAPI PATCH docs into decorated
    method.

    Example:

        import marshmallow as ma
        from flask_marshmallow_openapi import Securities, open_api

        class SchemaOpts(ma.SchemaOpts):
        def __init__(self, meta, *args, **kwargs):
            self.tags = getattr(meta, "tags", [])
            self.url_id_field = getattr(meta, "url_id_field", None)
            super().__init__(meta, *args, **kwargs)

        class BookSchema(ma.Schema):
            OPTIONS_CLASS = SchemaOpts

            class Meta:
                url_id_field = "id"
                tags = ["Books"]
                description = "Schema for Book model"

            id = ma.fields.Integer(as_string=True)
            title = ma.fields.String(
                allow_none=False, metadata={"description": "book.title description"}
            )

        @open_api.patch(
            request_schema=BookSchema,
            security=Securities.no_token,
            errors={
                409: "title must be unique!",
                422: "title must be at least 1 character!"
            }
            additional_content={
                "application/octet-stream": {
                    "schema": {"type": "string", "format": "binary"}
                }
            }
        )
        def update_book():
            \"\"\"
            description: |
                Long description!
            \"\"\"
    """

    if not response_schema:
        response_schema = request_schema

    open_api_data = OperationObject()

    open_api_data.operationId = operation_id or FlaskPathsManager.generate_operation_id(
        "patch", False, response_schema
    )
    # has_id = bool(getattr(response_schema.opts, "url_id_field", None))
    _parameters_from_schema(
        response_schema, requires_id_in_path=has_id_in_path, open_api_data=open_api_data
    )

    if security != Securities.no_token:
        open_api_data.security = [SecurityRequirementObject({f"{security.name}": []})]

    open_api_data.responses = ResponsesObject()
    open_api_data.responses["200"] = {
        "content": {
            "application/json": {
                "schema": {"$ref": SchemasRegistry.schema_ref(response_schema)}
            }
        }
    }

    open_api_data.requestBody = RequestBodyObject(
        **{
            "content": {
                "application/json": {
                    "schema": {"$ref": SchemasRegistry.schema_ref(request_schema)}
                }
            }
        }
    )

    if additional_content:
        for content_type, media in additional_content.items():
            if not isinstance(media, MediaTypeObject):
                media = MediaTypeObject(**media)
            open_api_data.requestBody.content[content_type] = media

    open_api_data.tags = list(
        set(
            getattr(request_schema.opts, "tags", [])
            + getattr(response_schema.opts, "tags", [])
        )
    )

    _update_errors(open_api_data, errors)

    return functools.partial(FlaskPathsManager.decorate, open_api_data=open_api_data)
