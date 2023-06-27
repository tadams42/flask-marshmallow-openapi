import functools

from openapi_pydantic_models import (
    MediaTypeObject,
    ParameterObject,
    ResponsesObject,
    SecurityRequirementObject,
)

from ..flask_paths import FlaskPathsManager
from ..schemas_registry import SchemasRegistry
from ..securities import Securities
from .helpers import _initial_docs, _update_errors


def get(
    response_schema,
    operation_id: str | None = None,
    summary: str | None = None,
    many: bool = False,
    errors: dict[int, str] | None = None,
    security: Securities = Securities.access_token,
    additional_content: dict[str, dict | MediaTypeObject] | None = None,
    additional_parameters: list[ParameterObject | dict] | None = None,
    tags_override: list[str] | None = None,
):
    """
    Decorator that will inject standard sets of our OpenAPI GET docs into decorated
    method.
    """

    if not operation_id:
        operation_id = FlaskPathsManager.generate_operation_id(
            "get", many, response_schema
        )

    open_api_data = _initial_docs(response_schema, with_id_in_path=not many)
    open_api_data.parameters = open_api_data.parameters or []

    open_api_data.operationId = operation_id

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
                schema = MediaTypeObject(**media)
            open_api_data.responses["200"].content[content_type] = media

    if not many:
        try:
            open_api_data.parameters[0].name = response_schema.opts.url_id_field
        except AttributeError:
            # It is perfectly fine to use GET on URLs that don't have ID field and
            # are described by schemas that don't have that field either.
            pass

    for data in additional_parameters or []:
        if isinstance(data, dict):
            data = ParameterObject(**data)
        open_api_data.parameters.append(data)

    if open_api_data.parameters:
        open_api_data.parameters = [_ for _ in open_api_data.parameters if _.name]

    tags = tags_override or getattr(response_schema.opts, "tags", None)
    if tags:
        open_api_data.tags = tags

    open_api_data.tags = list(set(open_api_data.tags or []))

    open_api_data.summary = summary

    _update_errors(open_api_data, errors)

    return functools.partial(FlaskPathsManager.decorate, open_api_data=open_api_data)
