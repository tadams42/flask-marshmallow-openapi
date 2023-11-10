import functools
from typing import Type

import marshmallow as ma
from flask.typing import ResponseReturnValue
from openapi_pydantic_models import (
    Locations,
    OperationObject,
    ParameterObject,
    RequestBodyObject,
    ResponsesObject,
    SecurityRequirementObject,
)

from ..flask_paths import FlaskPathsManager
from ..schemas_registry import SchemasRegistry
from ..securities import Securities
from .helpers import _parameters_from_schema, _update_errors


def post(
    request_schema: Type[ma.Schema],
    response_schema: Type[ma.Schema] | None = None,
    *,
    operation_id: str | None = None,
    summary: str | None = None,
    errors: dict[int, str] | None = None,
    headers: list[ParameterObject | dict] | None = None,
    security: Securities = Securities.access_token,
) -> functools.partial[ResponseReturnValue]:
    """
    Decorator that will inject standard sets of our OpenAPI POST docs into decorated
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

        @open_api.post(
            request_schema=BookSchema,
            security=Securities.no_token,
            errors={
                409: "title must be unique!",
                422: "title must be at least 1 character!"
            }
            additional_parameters=[
                {
                    "name": "zomg",
                    "in": "path",
                    "required": True,
                    "allowEmptyValue": False
                }
            ],
            headers=[
                {
                    "name": "X-Foo",
                    "allowEmptyValue": False
                }
            ]
        )
        def create_book(zomg):
            \"\"\"
            description: |
                Long description!
            \"\"\"
    """

    if not response_schema:
        response_schema = request_schema

    open_api_data = OperationObject()

    open_api_data.operationId = operation_id or FlaskPathsManager.generate_operation_id(
        "post", False, response_schema
    )

    _parameters_from_schema(
        request_schema, requires_id_in_path=False, open_api_data=open_api_data
    )

    if security != Securities.no_token:
        open_api_data.security = [SecurityRequirementObject({f"{security.name}": []})]

    open_api_data.responses = ResponsesObject()
    # TODO: This convention of having "create" in schema name makes our code smelly,
    # come up with something more explicit
    if "deleted" in SchemasRegistry.schema_name(response_schema).lower():
        open_api_data.responses["204"] = {"description": "Resource was deleted"}
    else:
        open_api_data.responses["201"] = {
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

    if summary:
        open_api_data.summary = summary

    open_api_data.tags = list(
        set(
            getattr(request_schema.opts, "tags", [])
            + getattr(response_schema.opts, "tags", [])
        )
    )

    _update_errors(open_api_data, errors)

    for header in headers or []:
        if isinstance(header, dict):
            header = ParameterObject(**header)
        header.in_ = Locations.header
        open_api_data.parameters.append(header)

    return functools.partial(FlaskPathsManager.decorate, open_api_data=open_api_data)
