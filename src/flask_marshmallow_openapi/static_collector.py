from __future__ import annotations

import hashlib
import json
import os
import shutil
from pathlib import Path
from typing import TYPE_CHECKING, Union

import flask
from flask import current_app

if TYPE_CHECKING:
    from .open_api import OpenAPI

# TODO: This shouldn't be needed once we can fully rely on importlib.resources
_SELF_PATH = Path(os.path.abspath(os.path.dirname(__file__)))


class StaticResourcesCollector:
    def __init__(self, open_api: OpenAPI, destination_dir: str | Path):
        self.open_api = open_api
        self.destination_dir = Path(destination_dir) / "docs"
        self.docs_static = self.destination_dir / "static"

    def collect(self):
        os.makedirs(self.docs_static, exist_ok=True)
        with current_app.test_request_context():
            # Do this so url_for generates correct URLs
            swagger_json_url = self._write_swagger_json()
            self._write_redoc_html(swagger_json_url)
            self._write_swagger_ui_html(swagger_json_url)
            self._write_changelog_html()
        self._copy_src_static_folder()

    def _write_swagger_json(self):
        swagger_json_filename = None

        for ext in ["json", "yaml"]:
            with open(self.docs_static / "open_api_spec.tmp", "w") as f:
                if ext == "json":
                    json.dump(self.open_api._to_dict, f, indent=2)
                else:
                    f.write(self.open_api._to_yaml)

            digest = _file_checksum(
                self.docs_static / "open_api_spec.tmp", hashlib.sha256
            )

            if ext == "json":
                dest = swagger_json_filename = f"swagger_{digest}.{ext}"
            else:
                dest = f"swagger_{digest}.{ext}"

            os.rename(self.docs_static / "open_api_spec.tmp", self.docs_static / dest)

        new_swagger_json_path = flask.url_for(
            "open_api.static", filename=swagger_json_filename
        )

        return new_swagger_json_path

    def _write_redoc_html(self, swagger_json_url):
        page = flask.render_template(
            "re_doc.jinja2",
            swagger_json_path=swagger_json_url,
            api_name=self.open_api.config.api_name,
        )
        with open(self.destination_dir / "re_doc.html", "w") as f:
            f.write(page)

    def _write_swagger_ui_html(self, swagger_json_url):
        page = flask.render_template(
            "swagger_ui.jinja2",
            **self.open_api._swagger_ui_template_config(
                config_overrides={"url": swagger_json_url}
            ),
        )
        with open(self.destination_dir / "swagger_ui.html", "w") as f:
            f.write(page)

    def _write_changelog_html(self):
        with open(self.docs_static / "changelog.md", "w") as f:
            if self.open_api.config.changelog_md_loader:
                f.write(self.open_api.config.changelog_md_loader())

        page = flask.render_template(
            "changelog.html.jinja2", api_name=self.open_api.config.api_name
        )
        with open(self.destination_dir / "changelog.html", "w") as f:
            f.write(page)

    def _copy_src_static_folder(self):
        # TODO: "../static/" should really be handled by importlib.resources but that
        # doesn't support extracting directories from package, only individual files.
        shutil.copytree(_SELF_PATH / "static", self.docs_static, dirs_exist_ok=True)


def _file_checksum(file_path: Union[str, Path], hashlib_callable):
    """Given path of the file and hash function, calculates file digest"""
    if os.path.isfile(file_path) and callable(hashlib_callable):
        hash_obj = hashlib_callable()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_obj.update(chunk)
        return hash_obj.hexdigest()

    return None
