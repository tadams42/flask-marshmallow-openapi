import importlib.resources
from dataclasses import dataclass

import flask
import marshmallow as ma
import yaml
from flask_marshmallow_openapi import OpenAPI, OpenAPISettings, open_api

import resources as app_resources


@dataclass
class Book:
    id: int
    title: str
    publisher: str
    isbn: str


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
