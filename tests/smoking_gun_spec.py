# Some basic, common sense tests that don't deal with more speciffic logic

import importlib


def test_package_can_be_imported():
    # avoid blunders with Python typing

    for module_name in [
        "decorators",
        "flask_paths",
        "middleware",
        "schemas_registry",
        "securities",
        "static_collector",
    ]:
        importlib.import_module(f".{module_name}", "flask_marshmallow_openapi")
