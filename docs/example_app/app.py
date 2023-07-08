from flask_marshmallow_openapi import OpenAPISettings, OpenAPI

import flask
import yaml

from my_api import api, UlidField

app = flask.Flask(__name__)
app.register_blueprint(api, url_prefix="/v1")


tmplt = """
title: "{{ api_name }}"
openapi_version: 3.0.2

servers:
  - url: http://127.0.0.1:5000
    description: |
      Flask dev server running locally on developer machine

  - url: https://foo.example.com
    description: Live API server

info:
  description: |
    Flask API for demonstrating capabilities of `flask-marshmallow-openapi`

    [See CHANGELOG here](/v1/docs/changelog)

tags:
  - name: Books
    description: |
      Docs for Books tag

      Look I can Markdown!

      | foo | bar | baz |
      | --- | --- | --- |
      | 1   | 2   | 3   |
      | 4   | 5   | 6   |
"""


def load_swagger_json_template(api_name: str, api_version: str):
    text = flask.render_template_string(tmplt, api_name=api_name)
    data = yaml.full_load(text)
    data["version"] = api_version
    return data


chnglg = """
# CHANGELOG

## 0.9.0 (unreleased)

- fix: foo
- feat: bar
- ...

## 0.8.0 (2023-06-23)

- feat: one
- feat: two
- fix: ten
"""


def load_changelog_md():
    return chnglg


conf = OpenAPISettings(
    api_version="v1",
    api_name="My API",
    app_package_name="my_api",
    mounted_at="/v1",
    swagger_json_template_loader=load_swagger_json_template,
    swagger_json_template_loader_kwargs={"api_name": "Foobar API", "api_version": "v1"},
    changelog_md_loader=load_changelog_md,
)
docs = OpenAPI(config=conf)


def ULID_field2properties(self, field, **kwargs):
    if isinstance(field, UlidField):
        return UlidField.OPENAPI_SCHEMA_ATTRS.items()
    return dict()


docs.add_attribute_function(ULID_field2properties)


docs.init_app(app)
