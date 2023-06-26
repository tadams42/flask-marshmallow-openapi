"""
Module provides decorators for flask view functions that will add OpenAPI docs to those
functions. Once docs are added, apispec.APISpec can use them to generate swagger.json.
"""

from .decorate_delete import delete_
from .decorate_get import get
from .decorate_patch import patch
from .decorate_post import post