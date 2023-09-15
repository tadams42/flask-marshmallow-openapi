import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import apispec
import flask
import requests
from apispec.exceptions import DuplicateComponentNameError
from apispec.ext.marshmallow import MarshmallowPlugin
from openapi_pydantic_models import OperationObject

from .flask_paths import FlaskPathsManager
from .schemas_registry import SchemasRegistry
from .static_collector import StaticResourcesCollector

_MINIMAL_SPEC = {"title": "Some API", "openapi_version": "3.0.2", "version": "v1"}

_DEFAULT_SECURITIES = {
    "components": {
        "securitySchemes": {
            "access_token": {
                "scheme": "bearer",
                "type": "http",
                "bearerFormat": "JWT",
                "description": "This endpoint requires [JWT](https://jwt.io/) access token.\n",
            },
            "refresh_token": {
                "scheme": "bearer",
                "type": "http",
                "bearerFormat": "JWT",
                "description": "This endpoint requires [JWT](https://jwt.io/) refresh token.\n",
            },
        }
    },
}


@dataclass
class OpenAPISettings:
    #: Name string displayed in various places in of API docs
    api_name: str

    #: Version string displayed in various places in of API docs
    api_version: str

    #: Top level python package in which to search for marshmallow.Schema classes
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

    # Set function that will blacklist some of the endpoints and methods from
    # being documented.
    #
    # Example:
    #
    #     def should_skip(path: str, method: str):
    #         return "/docs" in path or "/static" in path
    #
    #     OpenAPISettings(
    #         ...
    #         is_excluded_cb = should_skip
    #     )
    is_excluded_cb: Callable[[str, str], bool] | None = None


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

    def __init__(self, config: OpenAPISettings, app: flask.Flask | None = None):
        self._apispec = None
        self.blueprint = flask.Blueprint(
            name="open_api",
            import_name=__name__,
            url_prefix="/docs",
            template_folder="./templates",
            static_folder="./static",
        )
        self.config = config

        self._map_to_openapi_types = []
        self._attribute_functions = []
        self.docs_overrides: dict[tuple[str, str], OperationObject] = {}

        if app:
            self.init_app(app)

    def add_override(self, path: str, method: str, docs: OperationObject):
        """
        Specifies documentation override for given path and method.

        This will be used by OpenAPI middleware to override whatever docs would've been
        generated for that path and method.
        """
        self.docs_overrides[(path, method.lower())] = docs

    def add_map_to_openapi_types(self, data):
        """
        Call this as many times needed, but before calling `init_app()`.

        Example:
            class CustomInteger(Integer):
                pass

            open_api = OpenAPI(config=_open_api_conf)
            open_api.add_map_to_openapi_types((IntegerLike, Integer,))

            # ...

            open_api.init_app(app)

        See:
            https://apispec.readthedocs.io/en/latest/using_plugins.html#custom-fields
        """
        self._map_to_openapi_types.append(data)

    def add_attribute_function(self, f):
        """
        Call this as many times needed, but before calling `init_app()`.

        Example:
            def ULID_field2properties(self, field, **kwargs):
                ret = {}
                if isinstance(field, MyULIDField):
                    ret["format"] = "ULID"
                    ret["examples"] = [
                        "01H4QG7F1XB3MGW7GHB5PA4P89",
                        "01H4QG7FMQCE8DAPV6EQZREDX4",
                        "01H4QG7VE3BY903B5DNJ442RDN",
                        "01H4QG7XCPGCPB3BYN0QPFX61S",
                        "01H4QG80AHN36H1X1R2FEG61V4",
                        "01H4QG8294DFA2S9CZTBGEPCNE",
                        "01H4QG847Q1KVSQE6F8GXKRTJH",
                    ]
                return ret

            open_api = OpenAPI(config=_open_api_conf)
            open_api.add_attribute_function(ULID_field2properties)

            # ...

            open_api.init_app(app)

        See:
            https://apispec.readthedocs.io/en/latest/using_plugins.html#custom-fields
        """
        self._attribute_functions.append(f)

    def init_app(self, app: flask.Flask):
        self._add_own_endpoints()

        full_url_prefix = (
            Path(self.config.mounted_at or "/") / f"./{self.blueprint.url_prefix}"
        )

        with app.test_request_context():
            SchemasRegistry.find_all_schemas(self.config.app_package_name)
            self._init_apispec()
            self._collect_shema_docs()
            self._collect_endpoints_docs(app)

        app.register_blueprint(self.blueprint, url_prefix=str(full_url_prefix))

        if not hasattr(app, "extensions"):
            app.extensions = {}
        app.extensions["open_api"] = self

    def _collect_endpoints_docs(self, app):
        for converted_path, operations in FlaskPathsManager(
            app, self.config.is_excluded_cb, self.docs_overrides
        ).collect_endpoints_docs():
            self._apispec.path(path=converted_path, operations=operations.model_dump())

    def _init_apispec(self):
        initial_swagger_json = self._load_initial_spec()

        ma_plugin = MarshmallowPlugin()
        self._apispec = apispec.APISpec(plugins=[ma_plugin], **(initial_swagger_json))
        for _ in self._map_to_openapi_types:
            ma_plugin.map_to_openapi_type(*_)
        for _ in self._attribute_functions:
            ma_plugin.converter.add_attribute_function(_)

    def _collect_shema_docs(self):
        for name, klass in SchemasRegistry.all_schemas().items():
            # apispec automatically registers all nested schema so we must prevent
            # registering them ourselves because of DuplicateSchemaError
            x_tags = getattr(klass.opts, "x_tags", None)

            try:
                if x_tags:
                    self._apispec.components.schema(
                        name, component={"x-tags": x_tags}, schema=klass
                    )
                else:
                    self._apispec.components.schema(name, schema=klass)
            except DuplicateComponentNameError:
                pass

    def _load_initial_spec(self):
        initial_swagger_json: dict = _MINIMAL_SPEC
        if self.config.api_name:
            _MINIMAL_SPEC["title"] = self.config.api_name
        if self.config.api_version:
            _MINIMAL_SPEC["version"] = self.config.api_version

        if self.config.swagger_json_template_loader:
            if self.config.swagger_json_template_loader_kwargs:
                initial_swagger_json = self.config.swagger_json_template_loader(
                    **self.config.swagger_json_template_loader_kwargs
                )
            else:
                initial_swagger_json = self.config.swagger_json_template_loader()

        initial_swagger_json.update(_DEFAULT_SECURITIES)

        return initial_swagger_json

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

    def _add_own_endpoints(self):
        # How this stuff works?
        #
        # On development machines, these endpoints will be handled by supplied lambdas.
        # This is inefficient and slow, but it always serves latest data for "static"
        # content (ie. "swagger.json", "CHANGELOG.md") without the need to reload
        # development server.
        #
        # On deployed machines, we put reverse proxy in front of Flask app. We configure
        # reverse proxy to rewrite request static URLs and point them onto static files
        # that are generated once, during deployment.
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
