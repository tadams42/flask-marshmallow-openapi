[![PyPI Status](https://badge.fury.io/py/flask-marshmallow-openapi.svg)](https://badge.fury.io/py/flask-marshmallow-openapi)
[![license](https://img.shields.io/pypi/l/flask-marshmallow-openapi.svg)](https://opensource.org/licenses/MIT)
[![python_versions](https://img.shields.io/pypi/pyversions/flask-marshmallow-openapi.svg)](https://pypi.org/project/flask-marshmallow-openapi/)

# Overview

# Installation

~~~sh
pip install flask-marshmallow-openapi
~~~

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

## Contents

```{toctree}
---
maxdepth: 2
---
getting_started
documenting_get_routes
documenting_post_routes
documenting_patch_routes
documenting_delete_routes
markdown_and_docstrings
security_schemes
url_parameters
openapi_tags
openapi_middleware
documenting_custom_field_types
serving_static_swagger_docs
license
```

* {ref}`genindex`
* {ref}`modindex`
* {ref}`search`
