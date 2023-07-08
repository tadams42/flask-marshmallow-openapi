# Serving docs statically via nginx

Add `collect-static` command to your app:

```py
import shutil

import click
import flask

@app.cli.command("collect_static")
@click.argument(
    "destination_dir",
    nargs=1,
    type=click.Path(file_okay=False, dir_okay=True, writable=True, resolve_path=True),
    required=True,
)
def collect_static_command(destination_dir):
    docs.collect_static(destination_dir)
    shutil.copytree(
        flask.current_app.static_folder, destination_dir, dirs_exist_ok=True
    )
    click.echo(f"Static files collected into {destination_dir}.")
```

Configure `nginx`:

```nginx
server {
    # ...

    location ^~ /v1/static {
        alias /home/user/static;
        try_files $uri $uri.html =404;
    }

    location ^~ /v1/docs {
        alias /home/user/static/docs;
        try_files $uri $uri.html =404;
    }

    # ...
}
```

Whenever deploying the app, call:

```sh
flask --app foobar_api collect-static /home/user/static
```
