import functools
from typing import Type

import marshmallow as ma
from flask.typing import ResponseReturnValue
from openapi_pydantic_models import (
    OperationObject,
    ResponsesObject,
    SecurityRequirementObject,
)

from ..flask_paths import FlaskPathsManager
from ..securities import Securities
from .helpers import _parameters_from_schema, _update_errors


def delete(
    resource_schema: Type[ma.Schema],
    *,
    operation_id: str | None = None,
    errors: dict | None = None,
    security: Securities = Securities.access_token,
) -> functools.partial[ResponseReturnValue]:
    """
    Decorator that will inject standard sets of our OpenAPI DELETE docs into decorated
    method.
    """
    open_api_data = OperationObject()

    open_api_data.operationId = operation_id or FlaskPathsManager.generate_operation_id(
        "delete", False, resource_schema
    )
    _parameters_from_schema(
        resource_schema, requires_id_in_path=True, open_api_data=open_api_data
    )

    open_api_data.responses = ResponsesObject()

    open_api_data.responses["204"] = {"description": "Resource was deleted"}

    if security != Securities.no_token:
        open_api_data.security = [SecurityRequirementObject({f"{security.name}": []})]

    open_api_data.tags = getattr(resource_schema.opts, "tags", None)
    open_api_data.tags = list(set(open_api_data.tags or []))

    _update_errors(open_api_data, errors)

    return functools.partial(FlaskPathsManager.decorate, open_api_data=open_api_data)
