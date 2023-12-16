import os
import json
import yaml
import shutil
import htmlmin
import argparse
from datetime import datetime
from markdown import Markdown
from flask import Flask, Response
from jinja2 import Environment, FileSystemLoader


def extension_base_url(base: str, filename: str) -> str:
    if base.endswith("/"):
        base = base[:-1]
    return f"{base}/{filename}"


def extension_site_icon_effects(site: dict) -> str:
    effects = []
    if site.get("icon_effects") is not None:
        effects = [e.strip() for e in site["icon_effects"] if e.strip() != ""]
    if site.get("icon") is None:
        effects.append("hidden")
    effects = [f"site-icon-effect-{e}" for e in effects]
    effects.append("site-icon")
    return " ".join(effects)


def extension_site_tag_colors(tags: list[dict[str, str]], tag: str) -> str:
    tag_style = next(filter(lambda t: t["name"] == tag, tags), None)
    if tag_style is None:
        return ""
    css = ""
    if tag_style.get("color") is not None:
        css += f"background: {tag_style['color'].strip()};"
    if tag_style.get("text") is not None:
        css += f"color: {tag_style['text'].strip()};"
    return f"style=\"{css}\""


def render_homepage(_args: argparse.Namespace, manifest: dict, render: Environment) -> str:
    template = render.get_template("index.html")
    return template.render(manifest)


def render_markdown(args: argparse.Namespace, manifest: dict, render: Environment, slug: str) -> str:
    source = os.path.join(args.home, "articles", f"{slug}.md")
    if not os.path.exists(source):
        return None
    markdown = Markdown(extensions=["meta", "fenced_code", "codehilite", "toc"])
    with open(source, "r", encoding="utf-8") as f:
        content = markdown.convert(f.read())
        metadata = markdown.Meta
    template = render.get_template("markdown.html")
    return template.render(manifest, markdown=content, metadata=metadata)


def initialization(args: argparse.Namespace) -> tuple[dict, Environment]:
    manifest = os.path.join(args.home, "manifest.yml")
    with open(manifest, "r", encoding="utf-8") as f:
        manifest = yaml.load(f, Loader=yaml.FullLoader)
    
    extensions = {
        "datetime": datetime,
        "args": args,
        "base_url": extension_base_url,
        "site_icon_effects": extension_site_icon_effects,
        "site_tag_colors": extension_site_tag_colors,
    }
    templates = os.path.join(args.root, "templates")
    render = Environment(loader=FileSystemLoader(templates))
    for k, v in extensions.items():
        render.globals[k] = v
    
    return manifest, render


def build(args):
    size_threshold = 1024 * 100  # 100 KB
    manifest, render = initialization(args)
    print(f"Building to directory: {args.dist}...")
    if args.clean and os.path.exists(args.dist):
        print(f"Cleaning: {args.dist}...")
        shutil.rmtree(args.dist)
    if not os.path.exists(args.dist):
        os.mkdir(args.dist)
    
    def size_readable(size: int):
        color = "white" if size < size_threshold else "yellow"
        if size < 1024:
            return color, f"{size:>8} B"
        if size < 1024 * 1024:
            return color, f"{size / 1024:>8.2f} KB"
        if size < 1024 * 1024 * 1024:
            return color, f"{size / 1024 / 1024:>8.2f} MB"
        return color, f"{size / 1024 / 1024 / 1024:>8.2f} GB"
    
    def color_print(color: str, text: str):
        colors = {
            "red": "31;1",
            "green": "32;1",
            "yellow": "33;1",
            "blue": "34;1",
            "magenta": "35;1",
            "cyan": "36;1",
            "white": "37",
        }
        print(f"\033[{colors[color]}m{text}\033[0m", flush=True, end="")
    
    def copy(src: str, dst: str):
        if not os.path.exists(src):
            return
        if os.path.isdir(src):
            for f in os.listdir(src):
                copy(os.path.join(src, f), os.path.join(dst, f))
            return
        dst_abspath = os.path.join(args.dist, dst)
        os.makedirs(os.path.dirname(dst_abspath), exist_ok=True)
        color_print("white", f"[")
        color_print("yellow", f"COPY")
        color_print("white", f"] {dst:<40}")
        shutil.copy(src, dst_abspath)
        size_color, size = size_readable(os.path.getsize(dst_abspath))
        color_print("green", f"OK ")
        color_print(size_color, f"{size}\n")
    
    def make(content: str, dst: str, minify: bool = False):
        dst_abspath = os.path.join(args.dist, dst)
        os.makedirs(os.path.dirname(dst_abspath), exist_ok=True)
        color_print("white", f"[")
        color_print("blue", f"MAKE")
        color_print("white", f"] {dst:<40}")
        if minify:
            content = htmlmin.minify(content, remove_comments=True, remove_empty_space=True)
        with open(dst_abspath, "w", encoding="utf-8") as f:
            f.write(content)
        size_color, size = size_readable(os.path.getsize(dst_abspath))
        color_print("green", f"OK ")
        color_print(size_color, f"{size}\n")
    
    make(render_homepage(args, manifest, render), "index.html", minify=True)
    for markdown in os.listdir(os.path.join(args.home, "articles")):
        if not markdown.endswith(".md") or markdown.startswith("."):
            continue
        slug = markdown[:-3]
        make(render_markdown(args, manifest, render, slug), f"{slug}.html", minify=True)
    if args.with_assets:
        copy(os.path.join(args.home, "assets"), "assets")
    if args.with_css:
        copy(os.path.join(args.root, "css"), "css")
    if args.with_manifest:
        make(json.dumps(manifest, ensure_ascii=False), "manifest.json")
    
    print("Done building portal.")


def serve(args):
    app = Flask(__name__)

    @app.route("/")
    def homepage():
        manifest, render = initialization(args)
        return render_homepage(args, manifest, render)
    
    @app.route("/<slug>")
    def markdown(slug: str):
        manifest, render = initialization(args)
        return render_markdown(args, manifest, render, slug)
    
    @app.route("/manifest.json")
    def manifest():
        manifest, _ = initialization(args)
        return manifest
    
    @app.route("/css/<filename>")
    def css(filename: str):
        if not filename.endswith(".css"):
            filename += ".css"
        physical_path = os.path.join(args.root, "css", filename)
        if not os.path.exists(physical_path):
            return "Not Found", 404
        with open(physical_path, "rb") as f:
            return Response(f.read(), mimetype="text/css")
    
    @app.route("/assets/<filename>")
    def assets(filename: str):
        physical_path = os.path.join(args.home, "assets", filename)
        if not os.path.exists(physical_path):
            return "Not Found", 404
        with open(physical_path, "rb") as f:
            return Response(f.read(), mimetype="application/octet-stream")

    app.run(host=args.host, port=args.port, debug=True)


def init_project(args):
    home = os.path.abspath(args.home)
    print(f"Initializing project at: {home}...")
    if os.path.exists(home):
        print("Please select a path that does not exist.")
        return
    template = os.path.join(args.root, "project_template")
    print(f"Copying: {template} -> {home}...")
    shutil.copytree(template, home)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--assets-cdn-url", type=str, default="/assets")
    parser.add_argument("--css-cdn-url", type=str, default="/css")
    parser.add_argument("--home", type=str, default="data")

    subparsers = parser.add_subparsers(dest="command", required=True)
    build_parser = subparsers.add_parser("build")
    build_parser.add_argument("--dist", type=str, default="dist")
    build_parser.add_argument("--clean", action="store_true")
    build_parser.add_argument("--with-assets", action="store_true")
    build_parser.add_argument("--with-css", action="store_true")
    build_parser.add_argument("--with-manifest", action="store_true")
    serve_parser = subparsers.add_parser("serve")
    serve_parser.add_argument("--port", type=int, default=8000)
    serve_parser.add_argument("--host", type=str, default="127.0.0.1")
    subparsers.add_parser("init")

    args = parser.parse_args()
    args.root = os.path.dirname(os.path.abspath(__file__))
    if args.command == "build":
        build(args)
    if args.command == "serve":
        serve(args)
    if args.command == "init":
        init_project(args)


if __name__ == "__main__":
    main()        
