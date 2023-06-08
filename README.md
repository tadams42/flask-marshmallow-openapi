# Overview

[![PyPI Status](https://badge.fury.io/py/flask-marshmallow-openapi.svg)](https://badge.fury.io/py/flask-marshmallow-openapi)
[![license](https://img.shields.io/pypi/l/flask-marshmallow-openapi.svg)](https://opensource.org/licenses/MIT)
[![python_versions](https://img.shields.io/pypi/pyversions/flask-marshmallow-openapi.svg)](https://pypi.org/project/flask-marshmallow-openapi/)


Provides OpenAPI documentation generated from code for
[Flask](https://flask.palletsprojects.com/en/latest/) APIs built around
[marshmallow](https://marshmallow.readthedocs.io/en/stable/) schemas.

This hackish and organically grown (TM) package was crated because no other similar
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

## Example

See [example application](./docs/examples/foobar_api/README.md). Following is incomplete
excerpt to demonstrate:


```py
import flask
import marshmallow as ma
from flask_marshmallow_openapi import OpenAPI, OpenAPISettings, open_api


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


conf = OpenAPISettings(
    api_version="v1",
    api_name="Foobar API",
    app_package_name="foobar_api",
    mounted_at="/v1",
)


docs = OpenAPI(config=conf)
docs.init_app(app)
```
