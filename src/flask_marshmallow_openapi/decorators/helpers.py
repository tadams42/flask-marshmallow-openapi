import textwrap
from typing import Type

import marshmallow as ma
from openapi_pydantic_models import (
    OperationObject,
    ParameterObject,
    ResponseObject,
    ResponsesObject,
)


def _update_errors(open_api_data: OperationObject, errors: dict[int, str] | None):
    open_api_data.responses = open_api_data.responses or ResponsesObject()

    for code, description in (errors or {}).items():
        open_api_data.responses[code] = ResponseObject(
            **{
                # Following definition breaks ReDoc completely and is temporarily disabled
                # Bugs in ReDoc prevent rendering of `schema` objects defined by remote
                # schemas:
                #   - https://github.com/Redocly/redoc/issues/740
                #   - https://github.com/Redocly/redoc/issues/1128
                #
                # "content": {
                #     "application/json": {
                #         "type": "object",
                #         "schema": {
                #             "$ref": "https://jsonapi.org/schema#/definitions/failure"
                #         },
                #     }
                # },
                "description": textwrap.dedent(str(description)),
            }
        )


def _parameters_from_schema(
    schema_cls: Type[ma.Schema],
    requires_id_in_path: bool,
    open_api_data: OperationObject,
):
    open_api_data.parameters = []
    open_api_data.responses = ResponsesObject()

    id_parameter: ParameterObject | None = None
    for param in getattr(schema_cls.opts, "url_parameters", None) or []:
        if isinstance(param, dict):
            param = ParameterObject(**param)
        if param.name == "id":
            id_parameter = param
        else:
            open_api_data.parameters.append(param)

    url_id_field_name: str | None = getattr(schema_cls.opts, "url_id_field", None)
    if id_parameter and url_id_field_name:
        id_parameter.name = url_id_field_name

    if requires_id_in_path:
        if id_parameter:
            open_api_data.parameters.append(id_parameter)
        else:
            id_field = getattr(schema_cls, "_declared_fields", dict()).get("id", None)
            id_field_type = "integer"
            if id_field and "String" in str(id_field):
                id_field_type = "string"

            open_api_data.parameters.append(
                ParameterObject(
                    **{
                        "name": url_id_field_name or "id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": id_field_type},
                    }
                )
            )
