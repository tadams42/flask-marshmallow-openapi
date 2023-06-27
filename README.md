# Overview

[![PyPI Status](https://badge.fury.io/py/flask-marshmallow-openapi.svg)](https://badge.fury.io/py/flask-marshmallow-openapi)
[![license](https://img.shields.io/pypi/l/flask-marshmallow-openapi.svg)](https://opensource.org/licenses/MIT)
[![python_versions](https://img.shields.io/pypi/pyversions/flask-marshmallow-openapi.svg)](https://pypi.org/project/flask-marshmallow-openapi/)

Provides OpenAPI documentation generated from code for
[Flask](https://flask.palletsprojects.com/en/latest/) APIs built around
[marshmallow](https://marshmallow.readthedocs.io/en/stable/) schemas.

This hackish and organically grown (TM) package was created because no other similar
projects worked exactly the way I wanted them.

You will probably be better served by some other, properly maintained project with
similar purpose:

- [flasgger](https://github.com/flasgger/flasgger)
- [flask-openapi3](https://github.com/luolingchun/flask-openapi3)

If you still want to use it, welcome aboard :-) and read on!

## Installation

~~~sh
pip install flask-marshmallow-openapi
~~~

## What it does?

Searches your codebase for [marshmallow](https://marshmallow.readthedocs.io/en/stable/)
schemas and :medal_military: decorated :medal_military: Flask routes. For example:

```py
from flask_marshmallow_openapi import Securities, open_api

from ..views import NewPasswordSchema, LoginResponseSchema


@blueprint.route("/reset_password/<token>", methods=["POST"])
@open_api.post(
    request_schema=NewPasswordSchema,
    response_schema=LoginResponseSchema,
    operation_id="reset_password_finalize",
    security=Securities.no_token,
    additional_parameters=[
        {
            "name": "token",
            "in": "path",
            "required": True,
            "allowEmptyValue": False,
            "schema": {"type": "string"},
        }
    ],
)
def reset_password_confirm(token):
    ...
```

Using these, it constructs OpenAPI `swagger.json` and serves it. It also includes and
serves `ReDoc` and `SwaggerUI` documentation viewers.

## Full example

First we need some data:

```py
from dataclasses import dataclass

@dataclass
class Book:
    id: int
    title: str
    publisher: str
    isbn: str
```

Then we need some [marshmallow](https://marshmallow.readthedocs.io/en/stable/) schemas:

```py
import marshmallow as ma


class SchemaOpts(ma.SchemaOpts):
    def __init__(self, meta, *args, **kwargs):
        self.tags = getattr(meta, "tags", [])
        self.url_id_field = getattr(meta, "url_id_field", None)
        super().__init__(meta, *args, **kwargs)


class BookSchema(ma.Schema):
    OPTIONS_CLASS = SchemaOpts

    class Meta:
        url_id_field = "id"
        tags = ["Books"]
        description = "Schema for Book model"

    id = ma.fields.Integer(as_string=True)
    title = ma.fields.String(
        allow_none=False, metadata={"description": "book.title description"}
    )
    publisher = ma.fields.String(allow_none=False)
    isbn = ma.fields.String(allow_none=False)


class BookCreateSchema(ma.Schema):
    OPTIONS_CLASS = SchemaOpts

    class Meta(BookSchema.Meta):
        pass

    title = ma.fields.String(allow_none=False, required=True)


class BookUpdateSchema(ma.Schema):
    OPTIONS_CLASS = SchemaOpts

    class Meta(BookSchema.Meta):
        pass

    id = ma.fields.Integer(as_string=True, dump_only=True)
    isbn = ma.fields.String(allow_none=False, dump_only=True)
```

Then an [Flask](https://flask.palletsprojects.com/en/2.3.x/) app and some
:medal_military: decorated :medal_military: routes:

```py
import flask
from flask_marshmallow_openapi import open_api

app = flask.Flask(__name__)


@app.route("/books", methods=["GET"])
@open_api.get(BookSchema, "bookList", many=True)
def books_list():
    return "<p>Hello, World!</p>"


@app.route("/books/<int:book_id>", methods=["GET"])
@open_api.get(BookSchema, "bookDetail", many=False)
def books_detail(book_id):
    """
    description: |
        Look I can Markdown!

        | foo | bar | baz |
        | --- | --- | --- |
        | 1   | 2   | 3   |
        | 4   | 5   | 6   |
    """
    return "<p>Hello, World!</p>"


@app.route("/books", methods=["POST"])
@open_api.post(BookCreateSchema, BookSchema, "bookCreate")
def books_create():
    return "<p>Hello, World!</p>"


@app.route("/books/<int:book_id>", methods=["PATCH"])
@open_api.patch(BookUpdateSchema, BookSchema, "bookUpdate")
def books_update(book_id):
    return "<p>Hello, World!</p>"
```

Finally, we need to initialize OpenAPI middleware for our app:


```py
import importlib.resources
import yaml

def load_swagger_json_template(api_name: str, api_version: str):
    text = flask.render_template_string(
        importlib.resources.files(app_resources)
        .joinpath("open_api.template.yaml")
        .read_text(),
        api_name=api_name,
    )

    data = yaml.full_load(text)
    data["info"] = dict()
    data["version"] = api_version
    return data


def load_changelog_md():
    return importlib.resources.files(app_resources).joinpath("CHANGELOG.md").read_text()


conf = OpenAPISettings(
    api_version="v1",
    api_name="Foobar API",
    app_package_name="foobar_api",
    mounted_at="/v1",
    swagger_json_template_loader=load_swagger_json_template,
    swagger_json_template_loader_kwargs={"api_name": "Foobar API", "api_version": "v1"},
    changelog_md_loader=load_changelog_md,
)

docs = OpenAPI(config=conf)
docs.init_app(app)
```

`app_package_name` must be importable Python package name. It will be searched for any
`marshmallow.Schema` subclasses. These will be added as OpenAPI `components.schemas`.

Installed middleware will add some routes to serve ReDoc, SwaggerUI and
`swagger.json`:

- [ReDoc](http://127.0.0.1:5000/v1/docs/re_doc)
- [SwaggerUI](http://127.0.0.1:5000/v1/docs/swagger_ui)
- [swagger.json](http://127.0.0.1:5000/v1/docs/static/swagger.json)
- [swagger.yaml](http://127.0.0.1:5000/v1/docs/static/swagger.yaml)

If you provide (optional) `changelog_md_loader`, API docs will include routes:

- `/v1/docs/changelog`
- `/v1/docs/static/changelog.md`

If you provide (optional) `load_swagger_json_template`, it will be used as basis for
constructing `swagger.json`. Template could look like this:

```yaml
---
title: {{ api_name }}
openapi_version: 3.0.2

servers:
  - url: http://127.0.0.1:5000
    description: |
      Flask dev server running locally on developer machine

  - url: https://foo.example.com
    description: Live API server

components:
  securitySchemes:
    access_token:
      scheme: bearer
      type: http
      bearerFormat: JWT
      description: |
        This endpoint requires [JWT](https://jwt.io/) access token.
    refresh_token:
      scheme: bearer
      type: http
      bearerFormat: JWT
      description: |
        This endpoint requires [JWT](https://jwt.io/) refresh token.

tags:
  - name: Books
    description: |
      Common documentation for all book related routes.
```

### Serving static docs via ngnix

Add `collect-static` command to your app:

```py
import shutil

import click
import flask

@app.cli.command("collect_static")
@click.argument(
    "destination_dir",
    nargs=1,
    type=click.Path(file_okay=False, dir_okay=True, writable=True, resolve_path=True),
    required=True,
)
def collect_static_command(destination_dir):
    docs.collect_static(destination_dir)
    shutil.copytree(
        flask.current_app.static_folder, destination_dir, dirs_exist_ok=True
    )
    click.echo(f"Static files collected into {destination_dir}.")
```

Configure `nginx`:

```nginx
server {
    # ...

    location ^~ /v1/static {
        alias /home/user/static;
        try_files $uri $uri.html =404;
    }

    location ^~ /v1/docs {
        alias /home/user/static/docs;
        try_files $uri $uri.html =404;
    }

    # ...
}
```

Whenever deploying the app, call:

```sh
flask --app foobar_api collect-static /home/user/static
```
