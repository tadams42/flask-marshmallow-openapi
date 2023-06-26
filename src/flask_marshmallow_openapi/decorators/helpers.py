import textwrap

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


def _initial_docs(schema_cls, with_id_in_path: bool) -> OperationObject:
    retv = OperationObject()

    retv.responses = ResponsesObject()

    if with_id_in_path:
        id_field = getattr(schema_cls, "_declared_fields", dict()).get("id", None)
        id_field_type = "integer"
        if id_field and "String" in str(id_field):
            id_field_type = "string"

        retv.parameters = []
        retv.parameters.append(
            ParameterObject(
                **{
                    "name": "id",
                    "in": "path",
                    "required": True,
                    "schema": {"type": id_field_type},
                }
            )
        )

    return retv
