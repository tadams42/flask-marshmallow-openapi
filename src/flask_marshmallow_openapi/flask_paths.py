import copy
import re
import textwrap
from typing import Final, Set

import flask
import werkzeug
import werkzeug.routing
import yaml


class FlaskPathsManager:
    _ENCOUNTERED_OPERATION_IDS: Final[Set[str]] = set()
    _PATH_CONVERTER: Final[re.Pattern] = re.compile(r"<([a-z]*:)?([a-z_]*)>")
    ATTRIBUTE_NAME: Final[str] = "_open_api"

    def __init__(self, app: flask.Flask) -> None:
        self.app = app

    def collect_endpoints_docs(self):
        for rule in self.app.url_map.iter_rules():
            if self._should_document_enpdpoint(rule.endpoint):
                open_api_path = self._path_for(rule)
                if open_api_path:
                    # data = {
                    #     "path": "/v1/healthcheck",
                    #     "operations": {
                    #         "get": {
                    #             "operationId": "healthcheck",
                    #             "responses": {
                    #                 "200": {
                    #                     "content": {
                    #                         "application/json": {
                    #                             "schema": {
                    #                                 "$ref": "#/components/schemas/ApiHealthCheck"
                    #                             }
                    #                         }
                    #                     },
                    #                     "description": "",
                    #                 }
                    #             },
                    #             "tags": ["System"],
                    #             "summary": "api_health_check",
                    #         }
                    #     },
                    # }

                    yield {
                        "path": open_api_path["path"],
                        "operations": open_api_path["operations"],
                    }

    @classmethod
    def _should_document_enpdpoint(cls, name: str):
        # Reduce spam in docs
        return (
            "_relationships_" not in name
            and ".docs." not in name
            and "static" not in name
        )

    def _operations_for_rule(self, rule: werkzeug.routing.Rule):
        supported_methods = [
            _.lower() for _ in rule.methods if _ not in ["HEAD", "OPTIONS"]
        ]
        view = self.app.view_functions[rule.endpoint]
        open_api_data = getattr(view, self.ATTRIBUTE_NAME, {})
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

            from_docstring = self._yaml_from_docstring(f.__doc__)
            if method in from_docstring:
                from_docstring = from_docstring[method]
            operations[method].update(from_docstring)

            operations[method].update(
                getattr(f, self.ATTRIBUTE_NAME, {}).get(method, {})
            )

            operation_id = operations[method].get(
                "operationId", f"{method}_{rule.endpoint}"
            )

            if operation_id == "hidden":
                del operations[method]
                continue

            if operation_id in self.__class__._ENCOUNTERED_OPERATION_IDS:
                operations[method]["operationId"] = (
                    operation_id
                    + "_"
                    + str(
                        len(
                            [
                                _
                                for _ in self.__class__._ENCOUNTERED_OPERATION_IDS
                                if re.match(operation_id + r"[_0-9]*$", _)
                            ]
                        )
                    )
                )
            else:
                operations[method]["operationId"] = operation_id

            self.__class__._ENCOUNTERED_OPERATION_IDS.add(
                operations[method]["operationId"]
            )

        return copy.deepcopy(operations)

    def _path_for(self, rule: werkzeug.routing.Rule):
        # Bug in apispec_webframeworks.flask.FlaskPlugin only adds single path for each
        # inspected view.
        # https://github.com/marshmallow-code/apispec-webframeworks/issues/14
        #
        # Thus, we implement our own inspection
        operations = self._operations_for_rule(rule)
        if operations:
            return {
                "path": self._flask_path_to_open_api_path(rule.rule),
                "operations": operations,
            }

    @classmethod
    def _flask_path_to_open_api_path(cls, path: str):
        return cls._PATH_CONVERTER.sub(r"{\2}", path)

    def _yaml_from_docstring(self, docstring: str):
        retv = yaml.full_load(textwrap.dedent(docstring or "")) or {}

        if isinstance(retv, str):
            retv = {"description": retv}

        if retv and "description" in retv:
            with self.app.test_request_context():
                retv["description"] = flask.render_template_string(retv["description"])

        return retv
