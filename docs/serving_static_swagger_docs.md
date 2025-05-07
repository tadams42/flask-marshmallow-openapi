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

## About Nginx and HTTP cache

You might be changing API docs rapidly and as a consequence, `swagger.json` changes
rapidly too. There is a risk that other people will be looking at older version of
docs - unless they hard reload their browser.

To avoid this, we should configure nginx to inject correct `Cache-Control` header into
response for each served static files.

```nginx
server {
    # ...

    location ^~ /v1/static {
        alias /home/user/static;
        try_files $uri $uri.html =404;

        add_header Cache-Control "public, max-age=86400, must-revalidate";
    }

    location ^~ /v1/docs {
        alias /home/user/static/docs;
        try_files $uri $uri.html =404;

        add_header Cache-Control "no-cache";
    }

    # ...
}
```

Above configuration assumes following:

1. files under `/home/user/static/` change rarely

   Browser is instructed to cache them for 1 day. After one day, browser WILL check
   with server if file had been modified. If server returns `HTTP 304 Not Modified`,
   file will not be re-downloaded.


   (via `ETag` - Nginx injects that automatically for us) and download new
   version of file only if it had changed.

2. files under `/v1/docs` change more frequently

   Browser is instructed to cache these files, but to check with server if they had
   changed on every request. Again, this happens automatically via `Etag` that Nginx
   injects for us everywhere. If server returns `HTTP 304 Not Modified`, browser doesn't
   need to re-download file. Otherwise, it re-downloads it.

There are a few mechanisms of comparing file contents between browser and server. Modern
servers use `Etag` and Nginx injects that everywhere where it is needed. Details are usually
not important if you are running somewhat modern system with Nginx.

For other web servers check their docs in combination with:

- [MSDN HTTP Caching guide](https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/Caching)
- [MSDN Cache-Control header](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Cache-Control)
