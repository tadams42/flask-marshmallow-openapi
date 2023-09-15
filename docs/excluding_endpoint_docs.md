# Excluding and overriding generated endpoint documentation

To exclude endpoint docs, configure skip predicate:

```python
def _should_skip(path: str, method: str):
    return "/docs" in path or "/static" in path or "/relationships/" in path

conf = OpenAPISettings(
    # ...
    is_excluded_cb=_should_skip,
)
docs = OpenAPI(config=conf)
docs.init_app(app)
```

To  override docs for endpoint:

```python
from openapi_pydantic_models import OperationObject


open_api.add_override(
    "/v1/users/<user_id>/relationships/tags",
    "GET",
    OperationObject(
        tags=["User tags"],
        description="ZOMG!",
        operationId="user_rel_tags_detail",
    ),
)
```

Note that overrides take precedence over exclusion: if endpoint docs are overridden,
that override will be included even if `is_excluded_cb` would had skipped it.
