"""Command line: parses arguments and calls the modules. No logic of its own."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from rynz import __version__, log

# rynz 1.x command names that still work for one release
ALIASES = {"create": "new", "deploy": "build", "test": "check"}


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="rynz", description="Really Your Note Zenerator: Markdown in, plain HTML out.")
    p.add_argument("-v", "--version", action="version", version=f"rynz {__version__}")
    p.add_argument("-q", "--quiet", action="store_true", help="only print warnings and errors")
    p.add_argument("--verbose", action="store_true", help="print every step")
    p.add_argument("-C", "--dir", default=".", metavar="DIR", help="run as if started in DIR")
    # The same flags also work after the command (`rynz build -q`)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("-q", "--quiet", action="store_true", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    common.add_argument("--verbose", action="store_true", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    common.add_argument("-C", "--dir", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    sub = p.add_subparsers(dest="command", metavar="command")
    sub.required = True

    def command(name: str, help: str) -> argparse.ArgumentParser:
        return sub.add_parser(name, help=help, parents=[common])

    s = command("new", help="start a new site in a folder")
    s.add_argument("folder")
    s.add_argument("--title", help="site title (default: the folder name)")
    s.add_argument("--url", default="https://example.com", help="site address")

    s = command("add", help="add a new post (starts as a draft)")
    s.add_argument("title", help='post title, e.g. "My first post"')
    s.add_argument("--folder", help="subfolder of content/ (default: note)")

    s = command("build", help="build the site into the output folder")
    s.add_argument("--drafts", action="store_true", help="include pages marked draft: true")
    s.add_argument("--incremental", action="store_true", help="skip pages that haven't changed")
    s.add_argument("--out", metavar="DIR", help="output folder (default: paths.output in config.yml)")
    s.add_argument("--check", action="store_true", help="run `rynz check` after building")

    s = command("serve", help="preview locally; rebuilds when you save")
    s.add_argument("-p", "--port", type=int, default=5555)
    s.add_argument("--host", default="127.0.0.1")
    s.add_argument("--no-drafts", action="store_true", help="hide drafts in the preview")
    s.add_argument("--no-watch", action="store_true", help="don't rebuild on save")

    s = command("check", help="check the built site for broken links and missing text")
    s.add_argument("--strict", action="store_true", help="treat warnings as errors")

    command("config", help="show the full config with defaults, and validate it")

    s = command("migrate", help="rename rynz 1.x keys in config.yml")
    s.add_argument("--dry-run", action="store_true", help="show the changes without writing")

    s = command("init-ci", help="write a deploy file: gitlab, cloudflare or rsync")
    s.add_argument("target", choices=["gitlab", "cloudflare", "rsync"])
    s.add_argument("--force", action="store_true", help="overwrite an existing file")
    return p


def _run(args: argparse.Namespace) -> int:
    root = Path(args.dir)

    if args.command == "new":
        from rynz.scaffold import new_site

        target = new_site(root / args.folder, title=args.title, url=args.url)
        log.ok(f"created {target}")
        log.info(f"next: cd {args.folder} && rynz serve")
        return 0

    if args.command == "add":
        from rynz.scaffold import add_note

        path = add_note(args.title, root, args.folder)
        log.ok(f"created {path} (draft: true — remove that line to publish)")
        return 0

    if args.command == "build":
        from rynz.build import Builder, report
        from rynz.scaffold import ensure_gitignore

        result = Builder(root, drafts=args.drafts, incremental=args.incremental, output=args.out).build()
        report(result)
        ensure_gitignore(root.resolve())
        if args.check:
            return _check(root, strict=False)
        return 0

    if args.command == "serve":
        from rynz.server import serve

        serve(root, host=args.host, port=args.port, drafts=not args.no_drafts, watch=not args.no_watch)
        return 0

    if args.command == "check":
        return _check(root, strict=args.strict)

    if args.command == "config":
        import yaml

        from rynz import config as config_mod

        cfg = config_mod.load(root)
        log.info(yaml.safe_dump(config_mod.public_view(cfg), sort_keys=False, allow_unicode=True).rstrip())
        log.ok("config.yml is valid")
        return 0

    if args.command == "migrate":
        from rynz.scaffold import migrate

        changes = migrate(root, dry_run=args.dry_run)
        if not changes:
            log.ok("config.yml already uses rynz 2.0 names")
        else:
            verb = "would rename" if args.dry_run else "renamed"
            log.ok(f"{verb}: " + ", ".join(changes))
            if not args.dry_run:
                log.info("a backup was saved as config.yml.bak")
        return 0

    if args.command == "init-ci":
        from rynz.scaffold import init_ci

        for path in init_ci(args.target, root, force=args.force):
            log.ok(f"wrote {path}")
        return 0
    return 2


def _check(root: Path, strict: bool) -> int:
    from rynz import config as config_mod
    from rynz.checks import check_site

    cfg = config_mod.load(root, warn_legacy=False)
    out = root / cfg.paths["output"]
    if not out.is_dir():
        log.error(f"{out} not found — run `rynz build` first")
        return 1
    rep = check_site(out, cfg["url"])
    for issue in rep.issues:
        (log.error if issue.level == "error" else log.warn)(f"{issue.file}: {issue.message}")
    failed = bool(rep.errors) or (strict and bool(rep.warnings))
    summary = f"checked {rep.files} pages: {len(rep.errors)} errors, {len(rep.warnings)} warnings"
    (log.error if failed else log.ok)(summary)
    return 1 if failed else 0


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    i = 0
    while i < len(argv) and argv[i].startswith("-"):
        i += 2 if argv[i] in ("-C", "--dir") else 1
    if i < len(argv):
        command = argv[i]
        if command in ALIASES:
            log.warn(f"`rynz {command}` is now `rynz {ALIASES[command]}`; the old name goes away in rynz 2.1")
            argv[i] = ALIASES[command]
        elif command == "save":
            log.error("`rynz save` was removed in 2.0 — use git directly: git add -A && git commit")
            return 2
    args = _parser().parse_args(argv)
    log.set_level(quiet=args.quiet, verbose=args.verbose)

    from rynz.errors import BuildError, RynzError

    try:
        return _run(args)
    except BuildError as exc:
        for err in exc.errors:
            log.error(str(err))
        log.error(str(exc))
        return 1
    except RynzError as exc:
        log.error(str(exc))
        return 1
    except KeyboardInterrupt:
        return 130
