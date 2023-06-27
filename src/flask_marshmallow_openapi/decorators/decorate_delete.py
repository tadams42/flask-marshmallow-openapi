import functools
from typing import Type

import marshmallow as ma
from openapi_pydantic_models import ResponsesObject, SecurityRequirementObject

from ..flask_paths import FlaskPathsManager
from ..securities import Securities
from .helpers import _initial_docs, _update_errors


def delete_(
    resource_schema: Type[ma.Schema],
    operation_id: str | None = None,
    errors: dict | None = None,
    security: Securities = Securities.access_token,
):
    """
    Decorator that will inject standard sets of our OpenAPI DELETE docs into decorated
    method.
    """

    if not operation_id:
        operation_id = FlaskPathsManager.generate_operation_id(
            "delete", False, resource_schema
        )

    open_api_data = _initial_docs(resource_schema, with_id_in_path=True)

    open_api_data.operationId = operation_id

    open_api_data.responses = ResponsesObject()

    open_api_data.responses["204"] = {"description": "Resource was deleted"}

    open_api_data.parameters[0].name = resource_schema.opts.url_id_field

    if security != Securities.no_token:
        open_api_data.security = [SecurityRequirementObject({f"{security.name}": []})]

    open_api_data.tags = getattr(resource_schema.opts, "tags", None)
    open_api_data.tags = list(set(open_api_data.tags or []))

    _update_errors(open_api_data, errors)

    return functools.partial(FlaskPathsManager.decorate, open_api_data=open_api_data)
