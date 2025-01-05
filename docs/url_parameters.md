# Documenting URL parameters

We can specify url parameters as part of request schema. To do that, we need to use
`marshmallow.SchemaOptions` like this:

```py
# Using Flask app from "Getting started", this is fully working example
from openapi_pydantic_models import ParameterObject


class SchemaOpts(ma.SchemaOpts):
    def __init__(self, meta, *args, **kwargs):
        self.url_parameters: list[ParameterObject | dict] | None = getattr(
            meta, "url_parameters", None
        )
        super().__init__(meta, *args, **kwargs)
```

## Path parameters

```py
# Using Flask app from "Getting started", this is fully working example
class NewPasswordSchema(ma.Schema):
    OPTIONS_CLASS = SchemaOpts

    class Meta:
        url_parameters = [
            {
                "name": "token",
                "in": "path",
                "required": True,
                "allowEmptyValue": False,
                "schema": {"type": "string"},
            }
        ]

    new_password = ma.fields.String(allow_none=False, required=True)


@api.route("/reset_password/<token>", methods=["POST"])
@open_api.post(
    request_schema=NewPasswordSchema,
    response_schema=LoginResponseSchema,
    operation_id="reset_password_confirm",
    security=Securities.no_token,
)
def reset_password_confirm(token):
    data = NewPasswordSchema(many=False).load(flask.request.json)
    # access_token, refresh_token = validate_reset_password(token)
    return flask.jsonify(
        LoginResponseSchema(many=False).dump(
            {"access_token": "foo", "refresh_token": "bar"}
        )
    )
```

which gets us:

![ReDoc](./img/url_parameters_01.png "ReDoc - URL parameters")

## Query parameters

```py
# Using Flask app from "Getting started", this is fully working example
class NewPasswordSchema(ma.Schema):
    OPTIONS_CLASS = SchemaOpts

    class Meta:
        url_parameters = [
            {
                "name": "token",
                "in": "query",
                "required": True,
                "allowEmptyValue": False,
                "schema": {"type": "string"},
            }
        ]

    new_password = ma.fields.String(allow_none=False, required=True)


@api.route("/reset_password?token=<token>", methods=["POST"])
@open_api.post(
    request_schema=NewPasswordSchema,
    response_schema=LoginResponseSchema,
    operation_id="reset_password_confirm",
    security=Securities.no_token,
)
def reset_password_confirm(token):
    data = NewPasswordSchema(many=False).load(flask.request.json)
    # access_token, refresh_token = validate_reset_password(token)
    return flask.jsonify(
        LoginResponseSchema(many=False).dump(
            {"access_token": "foo", "refresh_token": "bar"}
        )
    )
```

which gets us:

![ReDoc](./img/url_parameters_02.png "ReDoc - URL parameters")


## Special treatment of object identifiers in URL path

By default, `@get` and `@patch` route decorators assume integer URL path parameter named
`id`:

```
GET /books/<int:id>
PATCH /books/<int:id>
```

If for whatever reason this default is not enough, we can both rename and better describe
object identifier parameter using `Schema.Meta`.

Renaming it:

```py
class BookSchema(ma.Schema):
    OPTIONS_CLASS = SchemaOpts

    class Meta:
        url_id_field = "book_id"
```

Which will document it like this:

```
GET /books/<int:book_id>
PATCH /books/<int:book_id>
```

Adding more details to ID parameter docs:

```py
class BookSchema(ma.Schema):
    OPTIONS_CLASS = SchemaOpts

    class Meta:
        url_id_field = "book_id"
        url_parameters = [
            {
                "name": "book_id",
                "in": "query",
                "required": True,
                "allowEmptyValue": False,
                "schema": {"type": "string"},
            }
        ]

```
