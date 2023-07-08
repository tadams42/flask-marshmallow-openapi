import textwrap

import flask
import marshmallow as ma
from openapi_pydantic_models import Locations, ParameterObject

from flask_marshmallow_openapi import Securities, open_api

api = flask.Blueprint("my_api", __name__)


# class SchemaOpts(ma.SchemaOpts):
#     def __init__(self, meta, *args, **kwargs):
#         self.tags: list[str] | None = getattr(meta, "tags", None)
#         self.url_parameters: list[ParameterObject | dict] | None = getattr(
#             meta, "url_parameters", None
#         )
#         super().__init__(meta, *args, **kwargs)


# class BookSchema(ma.Schema):
#     OPTIONS_CLASS = SchemaOpts

#     class Meta:
#         tags = ["Books"]

#     id = ma.fields.Integer(as_string=True)
#     title = ma.fields.String(
#         allow_none=False,
#         metadata={
#             "description": textwrap.dedent(
#                 """
#                 Attributes with Markdown
#                 | foo | bar | baz |
#                 | --- | --- | --- |
#                 | 1   | 2   | 3   |
#                 | 4   | 5   | 6   |
#                 """
#             )
#         },
#     )
#     publisher = ma.fields.String(allow_none=False)
#     isbn = ma.fields.String(allow_none=False)


# @open_api.get_list(response_schema=BookSchema)
# @api.route("/books", methods=["GET"])
# def books_list():
#     """
#     description: |
#         Look I can Markdown!

#         | foo | bar | baz |
#         | --- | --- | --- |
#         | 1   | 2   | 3   |
#         | 4   | 5   | 6   |
#     """
#     return flask.jsonify(
#         BookSchema(many=True).dump(
#             [
#                 {"id": 24, "title": "title", "publisher": "publisher", "isbn": "isbn"},
#                 {"id": 42, "title": "title", "publisher": "publisher", "isbn": "isbn"},
#             ]
#         )
#     )


# @open_api.get_detail(response_schema=BookSchema)
# @api.route("/books/<int:book_id>", methods=["GET"])
# def books_details(book_id):
#     return flask.jsonify(
#         BookSchema(many=False).dump(
#             {"id": 42, "title": "title", "publisher": "publisher", "isbn": "isbn"}
#         )
#     )


# class ApiHealthCheckSchema(ma.Schema):
#     OPTIONS_CLASS = SchemaOpts

#     class Meta:
#         tags = ["System"]

#     api_version = ma.fields.String(allow_none=False)
#     component_version = ma.fields.String(allow_none=False)
#     status = ma.fields.Integer(as_string=True)


# @api.route("/health_check", methods=["GET"])
# @open_api.get(
#     response_schema=ApiHealthCheckSchema,
#     operation_id="health_check",
#     is_list=False,
#     has_id_in_path=False,
# )
# def health_check():
#     return ApiHealthCheckSchema(many=False).dump(
#         {"api_version": "v1", "component_version": "1.2.3", "status": 42}
#     )


# class BookCreateSchema(ma.Schema):
#     OPTIONS_CLASS = SchemaOpts

#     class Meta:
#         tags = ["Books"]

#     id = ma.fields.Integer(as_string=True)
#     title = ma.fields.String(allow_none=False, required=True)
#     publisher = ma.fields.String(allow_none=False)
#     isbn = ma.fields.String(allow_none=False)


# @api.route("/books", methods=["POST"])
# @open_api.post(request_schema=BookCreateSchema, response_schema=BookSchema)
# def books_create():
#     data = BookCreateSchema(many=False).load(flask.request.json)
#     # Create object from data...
#     return flask.jsonify(
#         BookSchema(many=False).dump(
#             {"id": 42, "title": "title", "publisher": "publisher", "isbn": "isbn"}
#         )
#     )


# class BookUpdateSchema(ma.Schema):
#     OPTIONS_CLASS = SchemaOpts

#     class Meta:
#         tags = ["Books"]

#     id = ma.fields.Integer(as_string=True, dump_only=True)
#     title = ma.fields.String(allow_none=False)
#     publisher = ma.fields.String(allow_none=False)
#     isbn = ma.fields.String(allow_none=False)


# @api.route("/books/<int:book_id>", methods=["PATCH"])
# @open_api.patch(request_schema=BookUpdateSchema, response_schema=BookSchema)
# def books_update(book_id):
#     data = BookUpdateSchema(many=False).load(flask.request.json)
#     # Update object from data...
#     return flask.jsonify(
#         BookSchema(many=False).dump(
#             {"id": 42, "title": "title", "publisher": "publisher", "isbn": "isbn"}
#         )
#     )


# class ApiHealthCheckUpdateSchema(ma.Schema):
#     OPTIONS_CLASS = SchemaOpts

#     class Meta:
#         tags = ["System"]

#     api_version = ma.fields.String(allow_none=False)
#     component_version = ma.fields.String(allow_none=False, dump_only=True)
#     status = ma.fields.Integer(as_string=True, dump_only=True)


# @api.route("/health_check", methods=["PATCH"])
# @open_api.patch(
#     request_schema=ApiHealthCheckUpdateSchema,
#     response_schema=ApiHealthCheckSchema,
#     operation_id="health_check_update",
#     has_id_in_path=False,
# )
# def health_check_update():
#     data = ApiHealthCheckUpdateSchema(many=False).load(flask.request.json)
#     # Update object from data...
#     return ApiHealthCheckSchema(many=False).dump(
#         {"api_version": "v1", "component_version": "1.2.3", "status": 42}
#     )


# @api.route("/books/<int:book_id>", methods=["DELETE"])
# @open_api.delete_(BookSchema)
# def books_delete(book_id):
#     return flask.jsonify({})


# class LoginRequestSchema(ma.Schema):
#     OPTIONS_CLASS = SchemaOpts

#     class Meta:
#         tags = ["Authentication"]

#     username_or_email = ma.fields.String(allow_none=False, required=True)
#     password = ma.fields.String(allow_none=False, required=True)


# class LoginResponseSchema(ma.Schema):
#     OPTIONS_CLASS = SchemaOpts

#     class Meta:
#         tags = ["Authentication"]

#     access_token = ma.fields.String(allow_none=False, required=True)
#     refresh_token = ma.fields.String(allow_none=False, required=True)


# @api.route("/login", methods=["POST"])
# @open_api.post(
#     LoginRequestSchema,
#     LoginResponseSchema,
#     operation_id="login",
#     security=Securities.no_token,
# )
# def login():
#     data = LoginRequestSchema(many=False).load(flask.request.json)
#     # access_token, refresh_token = validate_login(data)
#     return flask.jsonify(
#         LoginResponseSchema(many=False).dump(
#             {"access_token": "foo", "refresh_token": "bar"}
#         )
#     )


# class RefreshTokenResponseSchema(ma.Schema):
#     OPTIONS_CLASS = SchemaOpts

#     class Meta:
#         tags = ["Authentication"]

#     access_token = ma.fields.String(allow_none=False, required=True)


# @api.route("/refresh", methods=["GET"])
# @open_api.get(
#     RefreshTokenResponseSchema,
#     operation_id="refresh",
#     is_list=False,
#     has_id_in_path=False,
#     security=Securities.refresh_token,
# )
# def refresh():
#     # access_token = generate_access_token_from_refresh_token(flask.request)
#     return flask.jsonify(
#         RefreshTokenResponseSchema(many=False).dump({"access_token": "foo"})
#     )


# class NewPasswordSchema(ma.Schema):
#     OPTIONS_CLASS = SchemaOpts

#     class Meta:
#         tags = ["Authentication"]
#         url_parameters = [
#             {
#                 "name": "token",
#                 "in": "path",
#                 "required": True,
#                 "allowEmptyValue": False,
#                 "schema": {"type": "string"},
#             }
#         ]

#     new_password = ma.fields.String(allow_none=False, required=True)


# @api.route("/reset_password/<token>", methods=["POST"])
# @open_api.post(
#     request_schema=NewPasswordSchema,
#     response_schema=LoginResponseSchema,
#     operation_id="reset_password_confirm",
#     security=Securities.no_token,
# )
# def reset_password_confirm(token):
#     data = NewPasswordSchema(many=False).load(flask.request.json)
#     # access_token, refresh_token = validate_reset_password(token)
#     return flask.jsonify(
#         LoginResponseSchema(many=False).dump(
#             {"access_token": "foo", "refresh_token": "bar"}
#         )
#     )


class UlidField(ma.fields.String):
    OPENAPI_SCHEMA_ATTRS = {
        "type": "string",
        "format": "ULID",
        "examples": [
            "01H4QG7EVN6J6HF5DAMS9TK53X",
            "01H4QG7F1XB3MGW7GHB5PA4P89",
            "01H4QG7F864HBXG63N8PBF1XBM",
            "01H4QG7FEEW0D463QJEREF81P3",
            "01H4QG7FMQCE8DAPV6EQZREDX4",
            "01H4QG7FTZYHYM92AG6TG5ZDFR",
            "01H4QG7G1898PRWKBAED26J0VE",
            "01H4QG7G7H3DWQ671CV4PF6D62",
            "01H4QG7GDSYJ0ZWF8J39XRAMR0",
            "01H4QG7GM2WWEYQPAGM57MYK4Y",
            "01H4QG7VE3BY903B5DNJ442RDN",
            "01H4QG7WDCAWS1DN52EWWYXTG9",
            "01H4QG7XCPGCPB3BYN0QPFX61R",
            "01H4QG7XCPGCPB3BYN0QPFX61S",
            "01H4QG7ZB859YDH4GXWY9V8V1H",
            "01H4QG80AHN36H1X1R2FEG61V4",
            "01H4QG819VCQFN67QXQCMRYD85",
            "01H4QG8294DFA2S9CZTBGEPCNE",
            "01H4QG838EMDFGRHN9AZW3SJGG",
            "01H4QG847Q1KVSQE6F8GXKRTJH",
        ],
    }

    @classmethod
    def is_valid_ulid_string(cls, value):
        return True

    def _serialize(self, value, attr, obj, **kwargs):
        if not value:
            return ""
        return value

    def _deserialize(self, value, attr, data, **kwargs):
        if self.is_valid_ulid_string(value):
            return value
        raise ma.ValidationError("must be valid ULID string!")


class SchemaOpts(ma.SchemaOpts):
    def __init__(self, meta, *args, **kwargs):
        self.url_parameters: list[ParameterObject | dict] | None = getattr(
            meta, "url_parameters", None
        )
        super().__init__(meta, *args, **kwargs)


class PublisherSchema(ma.Schema):
    OPTIONS_CLASS = SchemaOpts

    class Meta:
        url_parameters = [
            {
                "name": "id",
                "in": "path",
                "required": True,
                "allowEmptyValue": False,
                "schema": {
                    k: v
                    for k, v in UlidField.OPENAPI_SCHEMA_ATTRS.items()
                    # Not strictly necessary, but reduces spam in docs
                    if k != "examples"
                },
            }
        ]

    id = UlidField()
    name = ma.fields.String()
    address = ma.fields.String()


@open_api.get_list(response_schema=PublisherSchema)
@api.route("/publishers", methods=["GET"])
def publishers_list():
    ...


@open_api.get_detail(response_schema=PublisherSchema)
@api.route("/publishers/<publisher_id>", methods=["GET"])
def publishers_details(publisher_id):
    ...
