# Overview

[![PyPI Status](https://badge.fury.io/py/flask-marshmallow-openapi.svg)](https://badge.fury.io/py/flask-marshmallow-openapi)
[![license](https://img.shields.io/pypi/l/flask-marshmallow-openapi.svg)](https://opensource.org/licenses/MIT)
[![python_versions](https://img.shields.io/pypi/pyversions/flask-marshmallow-openapi.svg)](https://pypi.org/project/flask-marshmallow-openapi/)
[![documentation](https://readthedocs.org/projects/flask-marshmallow-openapi/badge/?version=latest)](https://flask-marshmallow-openapi.readthedocs.io/en/latest/?badge=latest)


Provides OpenAPI documentation generated from code for
[Flask](https://flask.palletsprojects.com/en/latest/) APIs built around
[marshmallow](https://marshmallow.readthedocs.io/en/stable/) schemas.

This hackish and organically grown ™ package was created because no other similar
projects worked exactly the way I wanted them.

Similar projects:

- [flasgger](https://github.com/flasgger/flasgger)
- [flask-openapi3](https://github.com/luolingchun/flask-openapi3)

## Installation

~~~sh
pip install flask-marshmallow-openapi
~~~

## Documentation

[Read the Docs](https://flask-marshmallow-openapi.readthedocs.io/en/latest)

## What does it do?

Searches your codebase for [marshmallow](https://marshmallow.readthedocs.io/en/stable/)
schemas and 🎖️ decorated 🎖️ Flask routes.

It then produces `swagger.json` and injects it into self-hosted
[ReDoc](https://github.com/Redocly/redoc) and
[SwaggerUI](https://github.com/swagger-api/swagger-ui) documentation viewers.

```py
api = flask.Blueprint("my_api", __name__)


class BookSchema(ma.Schema):
    id = ma.fields.Integer(as_string=True)
    title = ma.fields.String(allow_none=False)
    publisher = ma.fields.String(allow_none=False)
    isbn = ma.fields.String(allow_none=False)


@open_api.get_list(BookSchema)
@api.route("/books", methods=["GET"])
def books_list():
    return "<p>Hello, World!</p>"


app = flask.Flask(__name__)
app.register_blueprint(api, url_prefix="/v1")


conf = OpenAPISettings(
    api_version="v1", api_name="My API", app_package_name="my_api", mounted_at="/v1"
)
docs = OpenAPI(config=conf)
docs.init_app(app)
```

New app routes:

```sh
$ flask routes

Endpoint               Methods  Rule
---------------------  -------  -------------------------------
# ...
open_api.re_doc        GET      /v1/docs/re_doc
open_api.static        GET      /v1/docs/static/<path:filename>
open_api.swagger_json  GET      /v1/docs/static/swagger.json
open_api.swagger_ui    GET      /v1/docs/swagger_ui
open_api.swagger_yaml  GET      /v1/docs/static/swagger.yaml
# ...
```
