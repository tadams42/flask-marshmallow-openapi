from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

import apispec
import flask
import requests
from apispec.exceptions import DuplicateComponentNameError
from apispec.ext.marshmallow import MarshmallowPlugin

from . import decorators, helpers
from .static_collector import StaticResourcesCollector

_MINIMAL_SPEC = {"title": "Some API", "openapi_version": "3.0.2", "version": "v1"}


@dataclass
class OpenAPISettings:
    #: Name string displayed in various places in of API docs
    api_name: str

    #: Version string displayed in various places in of API docs
    api_version: str

    #: Top level python package in which to search for marshmalow.Schema classes
    app_package_name: str

    #: Where to mount OpenAPI blueprint? Giving ie. "/v1" will create following docs
    #: routes: "/v1/re_doc", "/v1/swagger_ui", "/v1/docs/static", ...
    mounted_at: str = "/"

    #: Optional function that loads minimal OpenAPI specification and returns it as
    #: dict. For example, client app could maintain following yaml file with document
    #: extensive documentation of OpenAPI tags. This file can be used as swagger.json
    #: seed file onto which other parts of docs (schemas and routes) will be added.
    #:
    #:   dict.
    #:   ---
    #:   title: {{ api_name }}
    #:   openapi_version: 3.0.2
    #:
    #:   servers:
    #:     - url: http://127.0.0.1:5000
    #:       description: |
    #:         Flask dev server running locally on developer machine
    #:
    #:     - url: https://foo.example.com
    #:       description: Live API server
    #:
    #:   components:
    #:     securitySchemes:
    #:       access_token:
    #:         scheme: bearer
    #:         type: http
    #:         bearerFormat: JWT
    #:         description: |
    #:           This endpoint requires [JWT](https://jwt.io/) access token.
    #:       refresh_token:
    #:         scheme: bearer
    #:         type: http
    #:         bearerFormat: JWT
    #:         description: |
    #:           This endpoint requires [JWT](https://jwt.io/) refresh token.
    #:
    #:   tags:
    #:     - name: Books
    #:       description: |
    #:         Common documentation for all book related routes.
    #:
    #: If None, OpenAPI will use default minimal swagger.json spec.
    swagger_json_template_loader: Callable[..., dict] | None = None

    #: kwargs for swagger_json_template_loader
    swagger_json_template_loader_kwargs: dict | None = None

    #: similar to swagger_json_template_loader, this one loads CHANGELOG.md
    #: If None, OpenAPI will not integrate CHANGELOG.md into documentation.
    changelog_md_loader: Callable[[], str] | None = None


class OpenAPI:
    """
    Sets up OpenAPI integration.

    - collects all endpoint docstrings into OpenAPI specification document.
    - Registers marshmallow schemas as OpenAPI component objects
    - Sets up serving of OpenAPI specification (swagger.json)
    - Sets up serving of SwaggerUI and ReDoc OpenAPI viewers

    Adds following routes to app:

    +--------------------------+--------+------------------------------------------------+
    |          endpoint        | method |                  path                          |
    +==========================+========+================================================+
    | open_api.swagger_json    | GET    | /{self.mounted_at}/docs/static/swagger.json    |
    +--------------------------+--------+------------------------------------------------+
    | open_api.swagger_yaml    | GET    | /{self.mounted_at}/docs/static/swagger.yaml    |
    +--------------------------+--------+------------------------------------------------+
    | open_api.re_doc          | GET    | /{self.mounted_at}/docs/re_doc                 |
    +--------------------------+--------+------------------------------------------------+
    | open_api.swagger_ui      | GET    | /{self.mounted_at}/docs/swagger_ui             |
    +--------------------------+--------+------------------------------------------------+
    | open_api.changelog.md    | GET    | /{self.mounted_at}/docs/static/changelog.md    |
    +--------------------------+--------+------------------------------------------------+
    | open_api.changelog       | GET    | /{self.mounted_at}/docs/changelog              |
    +--------------------------+--------+------------------------------------------------+
    | open_api.static          | GET    | /{self.mounted_at}/docs/static/<path:filename> |
    +--------------------------+--------+------------------------------------------------+
    """

    def __init__(self, config: OpenAPISettings, app: Optional[flask.Flask] = None):
        self._apispec = None
        self.blueprint = flask.Blueprint(
            name="open_api",
            import_name=__name__,
            url_prefix="/docs",
            template_folder="./templates",
            static_folder="./static",
        )
        self.config = config
        if app:
            self.init_app(app)

    def init_app(self, app: flask.Flask):
        self._add_own_endpoints(app)

        full_url_prefix = (
            Path(self.config.mounted_at or "/") / f"./{self.blueprint.url_prefix}"
        )

        with app.test_request_context():
            helpers.find_all_schemas(self.config.app_package_name)

            initial_swagger_json: dict = _MINIMAL_SPEC
            if self.config.swagger_json_template_loader:
                if self.config.swagger_json_template_loader_kwargs:
                    initial_swagger_json = self.config.swagger_json_template_loader(
                        **self.config.swagger_json_template_loader_kwargs
                    )
                else:
                    initial_swagger_json = self.config.swagger_json_template_loader()

            self._apispec = apispec.APISpec(
                plugins=[MarshmallowPlugin()], **(initial_swagger_json)
            )
            for name, klass in helpers.all_schemas():
                # apispec automatically registers all nested schema so we must prevent
                # registering them ourselves because of DuplicateSchemaError
                try:
                    self._apispec.components.schema(name, schema=klass)
                except DuplicateComponentNameError:
                    pass

            self._collect_endpoints_docs(app)

        app.register_blueprint(self.blueprint, url_prefix=str(full_url_prefix))

        if not hasattr(app, "extensions"):
            app.extensions = {}
        # app.extensions["open_api"] = self

    def collect_static(self, destination_dir: str | Path):
        StaticResourcesCollector(self, destination_dir).collect()

    def _swagger_ui_template_config(self, config_overrides=None, oauth_config=None):
        # Swagger UI config
        # see: https://github.com/swagger-api/swagger-ui
        config = {
            "dom_id": "#swagger-ui",
            "url": flask.url_for("open_api.swagger_json"),
            "layout": "StandaloneLayout",
            "deepLinking": True,
            "docExpansion": "none",
            "validatorUrl": "none",
            "tagSorter": "cmpr",
            "oauth2RedirectUrl": os.path.join(
                self.blueprint.static_url_path,
                "docs",
                "swagger_ui",
                "oauth2-redirect.html",
            ),
        }

        if config_overrides:
            config.update(config_overrides)

        fields = {"config_json": json.dumps(config)}

        if oauth_config:
            fields["oauth_config_json"] = json.dumps(oauth_config)

        fields["api_name"] = self.config.api_name

        return fields

    def _add_own_endpoints(self, app):
        # How this stuff works?
        #
        # On development machines, these endpoints will be handled by supplied lambdas.
        # This is inefficient and slow, but it always serves latest data for "static"
        # content (ie. "swagger.json", "CHANGELOG.md") without the need to reload
        # development server.
        #
        # On deployed machines, we put reverse proxy in front of Flask app.
        # We configure reverse proxy to rewrite request some URLs and point then onto
        # static files that are generated once, during deployment.
        #
        # For example, request `GET /v1/docs/re_doc` will:
        #
        #   - on development machine will hit one of lambdas below
        #   - on deployed server, we will have generated `/foo/bar/static/re_doc.html`
        #     and configured reverse proxy to rewrite original request into
        #     `GET /static/re_doc.html`.
        #
        # As a result, when app is deployed, our slow and inefficient lambdas here will
        # never be triggered.

        self.blueprint.add_url_rule(
            rule="/static/swagger.json",
            endpoint="swagger_json",
            view_func=lambda: flask.make_response(
                json.dumps(self._apispec.to_dict()),
                requests.codes["✓"],
                {"Content-Type": "application/json"},
            ),
            methods=["GET"],
        )
        self.blueprint.add_url_rule(
            rule="/static/swagger.yaml",
            endpoint="swagger_yaml",
            view_func=lambda: flask.Response(
                response=self._apispec.to_yaml(),
                status=requests.codes["✓"],
                mimetype="application/x-yaml",
            ),
        )
        self.blueprint.add_url_rule(
            rule="/swagger_ui",
            endpoint="swagger_ui",
            view_func=lambda: flask.render_template(
                "swagger_ui.jinja2", **self._swagger_ui_template_config()
            ),
            methods=["GET"],
        )
        self.blueprint.add_url_rule(
            rule="/re_doc",
            endpoint=f"re_doc",
            view_func=lambda: flask.render_template(
                "re_doc.jinja2", api_name=self.config.api_name
            ),
            methods=["GET"],
        )

        if self.config.changelog_md_loader:
            self.blueprint.add_url_rule(
                rule="/static/changelog.md",
                endpoint="changelog_md",
                view_func=lambda: flask.make_response(
                    self.config.changelog_md_loader(),
                    requests.codes["✓"],
                    {"Content-Type": "text/markdown"},
                ),
                methods=["GET"],
            )
            self.blueprint.add_url_rule(
                rule="/changelog",
                endpoint=f"changelog",
                view_func=lambda: flask.render_template(
                    "changelog.html.jinja2", api_name=self.config.api_name
                ),
                methods=["GET"],
            )

    @property
    def _to_dict(self):
        return self._apispec.to_dict()

    @property
    def _to_yaml(self):
        return self._apispec.to_yaml()

    def _should_document_enpdpoint(self, name: str):
        # Reduce spam in docs
        return (
            "_relationships_" not in name
            and ".docs." not in name
            and "static" not in name
        )

    def _collect_endpoints_docs(self, app):
        for rule in app.url_map.iter_rules():
            if self._should_document_enpdpoint(rule.endpoint):
                open_api_path = decorators.path_for(app, rule)
                if open_api_path:
                    self._apispec.path(
                        path=open_api_path["path"],
                        operations=open_api_path["operations"],
                    )
