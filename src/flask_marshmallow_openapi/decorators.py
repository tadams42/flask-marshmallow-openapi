"""
Module provides decorators for flask view functions that will add OpenAPI docs to those
functions. Once docs are added, apispec.APISpec can use them to generate swagger.json.
"""

import copy
import functools
import re
import textwrap
from typing import List, Optional, Type

import flask
import marshmallow
import werkzeug.routing
import wrapt
import yaml

from .helpers import schema_name, schema_ref
from .securities import Securities

ATTRIBUTE_NAME = "_open_api"
_ENCOUNTERED_OPERATION_IDS = set()


def _generate_operation_id(method, many, response_schema):
    for_schema = (
        schema_name(response_schema)
        .replace("Schema", "")
        .replace("Update", "")
        .replace("Create", "")
    )

    if method == "get":
        return ("list" if many else "detail") + for_schema

    if method == "post":
        return "create" + for_schema

    if method == "patch":
        return "update" + for_schema

    if method == "delete":
        return "delete" + for_schema


def hide_doc():
    return functools.partial(
        _decorate, open_api_data={"post": {"operationId": "hidden"}}
    )


def get(
    response_schema,
    operation_id: Optional[str] = None,
    summary: str = "",
    many: bool = False,
    errors: Optional[dict] = None,
    security: Securities = Securities.access_token,
    additional_content: Optional[dict] = None,
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
            "application/json": {"schema": {"$ref": schema_ref(response_schema)}}
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

    tags = getattr(response_schema.opts, "tags", None)
    if tags:
        open_api_data["tags"] = tags

    if summary:
        open_api_data["summary"] = summary

    _update_errors(open_api_data, errors)

    return functools.partial(_decorate, open_api_data={"get": open_api_data})


def post(
    request_schema: Type[marshmallow.Schema],
    response_schema: Type[marshmallow.Schema] | None = None,
    operation_id: Optional[str] = None,
    summary: Optional[str] = None,
    errors: Optional[dict] = None,
    headers: Optional[List[dict]] = None,
    security: Securities = Securities.access_token,
):
    """
    Decorator that will inject standard sets of our OpenAPI POST docs into decorated
    method.
    """

    if not response_schema:
        response_schema = request_schema

    if not operation_id:
        operation_id = _generate_operation_id("post", False, response_schema)

    open_api_data = _initial_docs(request_schema)
    open_api_data["operationId"] = operation_id
    if security != Securities.no_token:
        open_api_data["security"] = [{f"{security.name}": []}]

    # TODO: This convention of having "create" in schema name makes our code smelly,
    # come up with something more explicit
    if "deleted" in schema_name(response_schema).lower():
        open_api_data["responses"]["204"] = {"description": "Resource was deleted"}

    else:
        open_api_data["responses"]["201"] = {
            "content": {
                "application/json": {"schema": {"$ref": schema_ref(response_schema)}}
            },
            "description": "",
        }

    open_api_data["requestBody"] = {
        "content": {
            "application/json": {"schema": {"$ref": schema_ref(request_schema)}}
        }
    }
    if summary:
        open_api_data["summary"] = summary

    url_id_field = getattr(request_schema.opts, "url_id_field", None)
    # TODO: This convention of having "create" in schema name makes our code smelly,
    # come up with something more explicit
    if url_id_field and "create" not in schema_name(request_schema).lower():
        open_api_data["parameters"][0]["name"] = url_id_field
    else:
        del open_api_data["parameters"]

    tags = getattr(request_schema.opts, "tags", None) or getattr(
        response_schema.opts, "tags", None
    )
    if tags:
        open_api_data["tags"] = tags

    _update_errors(open_api_data, errors)

    if headers:
        if "parameters" not in open_api_data:
            open_api_data["parameters"] = []
        for header in headers:
            header["in"] = "header"
            open_api_data["parameters"].append(header)

    return functools.partial(_decorate, open_api_data={"post": open_api_data})


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


def patch(
    request_schema: Type[marshmallow.Schema],
    response_schema: Optional[Type[marshmallow.Schema]] = None,
    operation_id: Optional[str] = None,
    errors: Optional[dict] = None,
    additional_content: Optional[dict] = None,
    security: Securities = Securities.access_token,
):
    """
    Decorator that will inject standard sets of our OpenAPI PATCH docs into decorated
    method.
    """

    if not response_schema:
        response_schema = request_schema

    if not operation_id:
        operation_id = _generate_operation_id("patch", False, response_schema)

    open_api_data = _initial_docs(request_schema)
    open_api_data["operationId"] = operation_id
    if security != Securities.no_token:
        open_api_data["security"] = [{f"{security.name}": []}]
    open_api_data["responses"]["200"] = {
        "content": {
            "application/json": {"schema": {"$ref": schema_ref(response_schema)}}
        },
        "description": "",
    }
    open_api_data["requestBody"] = {
        "content": {
            "application/json": {"schema": {"$ref": schema_ref(request_schema)}}
        }
    }

    if additional_content:
        for content_type, schema in additional_content.items():
            open_api_data["requestBody"]["content"][content_type] = schema

    open_api_data["parameters"][0]["name"] = response_schema.opts.url_id_field

    tags = getattr(request_schema.opts, "tags", None) or getattr(
        response_schema.opts, "tags", None
    )
    if tags:
        open_api_data["tags"] = tags

    _update_errors(open_api_data, errors)

    return functools.partial(_decorate, open_api_data={"patch": open_api_data})


def _update_errors(open_api_data: dict, errors: Optional[dict]):
    for code, description in (errors or {}).items():
        code, body = _error_response(code, description)
        open_api_data["responses"][code] = body


def _error_response(code, description):
    return (
        str(code),
        {
            # "content": {
            #     "application/json": {
            #         # "type": "object"
            #         # TODO: Current version of ReDoc fails to parse JSON:Schema
            #         #       referenced in below links. For that reason, we'd removed
            #         #       them from docs. If/when ReDoc is fixed, we should add them
            #         #       back in.
            #         # "schema": {
            #         #     "$ref": "https://jsonapi.org/schema#/definitions/failure"
            #         # }
            #     }
            # },
            "description": textwrap.dedent(str(description)),
        },
    )


def _decorate(wrapped, open_api_data):
    @wrapt.decorator
    def wrapper(wrapped, instance, args, kwargs):
        return wrapped(*args, **kwargs)

    if not hasattr(wrapped, ATTRIBUTE_NAME):
        setattr(wrapped, ATTRIBUTE_NAME, dict())
    getattr(wrapped, ATTRIBUTE_NAME).update(open_api_data)

    return wrapper(wrapped)


_PATH_CONVERTER = re.compile(r"<([a-z]*:)?([a-z_]*)>")


def _initial_docs(schema_cls):
    id_field = getattr(schema_cls, "_declared_fields", dict()).get("id", None)
    id_field_type = "integer"
    if id_field and "String" in str(id_field):
        id_field_type = "string"

    retv = {
        "operationId": None,
        "responses": {
            # code: description
            # for code, description in [
            #     _error_response("4XX", "Client side errors"),
            #     _error_response("5XX", "Server side errors"),
            # ]
        },
        "parameters": [
            {
                "name": "id",
                "in": "path",
                "required": True,
                "schema": {"type": id_field_type},
            }
        ],
    }

    return retv


def _flask_path_to_open_api_path(path: str):
    return _PATH_CONVERTER.sub(r"{\2}", path)


def _yaml_from_docstring(app: "flask.Flask", docstring: str):
    retv = yaml.full_load(textwrap.dedent(docstring or "")) or {}

    if isinstance(retv, str):
        retv = {"description": retv}

    if retv and "description" in retv:
        with app.test_request_context():
            retv["description"] = flask.render_template_string(retv["description"])

    return retv


def _operations_for_rule(app: flask.Flask, rule: werkzeug.routing.Rule):
    supported_methods = [
        _.lower() for _ in rule.methods if _ not in ["HEAD", "OPTIONS"]
    ]
    view = app.view_functions[rule.endpoint]
    open_api_data = getattr(view, ATTRIBUTE_NAME, {})
    operations = dict()

    for method in supported_methods:
        if method in open_api_data:
            operations[method] = open_api_data[method]
        else:
            operations[method] = dict()

        if hasattr(view, "view_class"):
            f = getattr(view.view_class, method)
        else:
            f = view

        from_docstring = _yaml_from_docstring(app, f.__doc__)
        if method in from_docstring:
            from_docstring = from_docstring[method]
        operations[method].update(from_docstring)

        operations[method].update(getattr(f, ATTRIBUTE_NAME, {}).get(method, {}))

        operation_id = operations[method].get(
            "operationId", f"{method}_{rule.endpoint}"
        )

        if operation_id == "hidden":
            del operations[method]
            continue

        if operation_id in _ENCOUNTERED_OPERATION_IDS:
            operations[method]["operationId"] = (
                operation_id
                + "_"
                + str(
                    len(
                        [
                            _
                            for _ in _ENCOUNTERED_OPERATION_IDS
                            if re.match(operation_id + r"[_0-9]*$", _)
                        ]
                    )
                )
            )
        else:
            operations[method]["operationId"] = operation_id

        _ENCOUNTERED_OPERATION_IDS.add(operations[method]["operationId"])

    return copy.deepcopy(operations)


def path_for(app: flask.Flask, rule: werkzeug.routing.Rule):
    # Bug in apispec_webframeworks.flask.FlaskPlugin only adds single path for each
    # inspected view.
    # https://github.com/marshmallow-code/apispec-webframeworks/issues/14
    #
    # Thus, we implement our own inspection
    operations = _operations_for_rule(app, rule)
    if operations:
        return {
            "path": _flask_path_to_open_api_path(rule.rule),
            "operations": operations,
        }
