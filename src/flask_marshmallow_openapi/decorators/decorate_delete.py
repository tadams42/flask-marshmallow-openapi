import functools
from typing import Optional

from ..securities import Securities
from .helpers import _decorate, _generate_operation_id, _initial_docs, _update_errors


def delete_(
    resource_schema,
    operation_id: Optional[str] = None,
    errors: Optional[dict] = None,
    security: Securities = Securities.access_token,
):
    """
    Decorator that will inject standard sets of our OpenAPI DELETE docs into decorated
    method.
    """

    if not operation_id:
        operation_id = _generate_operation_id("delete", False, resource_schema)

    open_api_data = _initial_docs(resource_schema)
    open_api_data["operationId"] = operation_id
    open_api_data["responses"]["204"] = {"description": "Resource was deleted"}
    open_api_data["parameters"][0]["name"] = resource_schema.opts.url_id_field
    if security != Securities.no_token:
        open_api_data["security"] = [{f"{security.name}": []}]

    tags = getattr(resource_schema.opts, "tags", None) or getattr(
        resource_schema.opts, "tags", None
    )
    if tags:
        open_api_data["tags"] = tags

    _update_errors(open_api_data, errors)

    return functools.partial(_decorate, open_api_data={"delete": open_api_data})
