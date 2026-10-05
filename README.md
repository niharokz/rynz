# rynz

**rynz turns a folder of Markdown files into a plain, fast website.** No JavaScript, no tracking, no build chain: one command and you have HTML you can host anywhere.

It powers [nih.ar](https://nih.ar), a personal site that has been online since 2011.

- **Write in Markdown.** Tables, footnotes, task lists and highlighted code work out of the box.
- **Plain HTML out.** Zero JavaScript, and no CSS classes unless you add them.
- **Yours to change.** Every template and stylesheet is a normal file you can override.

---

## Contents

- [Quick start](#quick-start)
- [Writing a post](#writing-a-post)
- [Project layout](#project-layout)
- [Configuration](#configuration)
- [Commands](#commands)
- [Templates and themes](#templates-and-themes)
- [Plugins](#plugins)
- [Deploying](#deploying)
- [Upgrading from rynz 1.x](#upgrading-from-rynz-1x)
- [FAQ](#faq)

---

## Quick start

You need Python 3.10 or newer.

```bash
pip install rynz
rynz new my-site
cd my-site
rynz serve
```

Open http://127.0.0.1:5555. You'll see a working site with a sample post. Every time you save a file, rynz rebuilds the site; refresh the browser to see the change.

When you're ready to publish:

```bash
rynz build
```

The finished site is in `public/`. Upload that folder to any web host.

---

## Writing a post

```bash
rynz add "My first post"
```

This creates `content/note/my-first-post.md`:

```markdown
---
title: "My first post"
description: ""
date: 2026-10-05
tags: [note]
draft: true
---

Start writing here.
```

The part between the `---` lines is the **frontmatter**: settings for this page. Everything below it is your post, written in Markdown.

A new post starts as a **draft**: `rynz serve` shows it, `rynz build` leaves it out. Delete the `draft: true` line when you want to publish it.

**Posts and pages.** A file with the `note` tag is a *post*: it appears in the list on your home page and in the RSS feed. A file without it is a *page*, like an About page: it gets built, but isn't listed.

### Frontmatter fields

Only `title` is needed. Everything else is optional.

| Field | What it does | Example |
| --- | --- | --- |
| `title` | Page title | `title: "Hello"` |
| `description` | One line shown in search results, social previews and the feed | `description: "Why I self-host"` |
| `date` | When it was first published | `date: 2026-10-05` |
| `updated` | When you last changed it meaningfully | `updated: 2026-11-01` |
| `tags` | Tags; `note` makes it a post | `tags: [note, linux]` |
| `draft` | Leave it out of `rynz build` | `draft: true` |
| `slug` | Change the file name in the URL | `slug: hello` |
| `template` | Use a different template for this page | `template: wide.html` |
| `image` | Image for social previews | `image: /img/cover.png` |
| `aliases` | Old URLs that should redirect here | `aliases: [old-name]` |
| `noindex` | Ask search engines to skip it | `noindex: true` |
| `nofeed` | Keep a post out of the feed | `nofeed: true` |
| `toc` | Show a table of contents | `toc: true` |
| `head` | Extra HTML for this page's `<head>` | `head: '<meta name="x" content="y">'` |

Any other field you add is kept and available in templates as `page.extra.<name>`.

---

## Project layout

```text
my-site/
├── config.yml        site settings
├── content/          your writing
│   ├── home.md       text at the top of the home page
│   ├── about.md      a page  → about.html
│   └── note/         posts (any folder depth works)
│       └── hello-world.md
├── data/             YAML files available to templates as site.data
├── static/           files copied as-is: images, CSS, favicon
├── template/         your own templates (override the theme's)
└── public/           the built site — created by `rynz build`
```

---

## Configuration

`config.yml` needs just two lines:

```yaml
title: My site
url: https://example.com
```

Everything else has a sensible default. Here is a fuller example with the common options:

```yaml
title: My site
url: https://example.com
description: Notes on Linux, homelabs and banking software.
author: Your Name
language: en
image: /img/card.png        # default social preview image
theme: default

menu:                        # links in the header
  - name: about
    url: /about.html
footer_menu:                 # links in the footer
  - name: feed
    url: /rss.xml

urls: flat                   # flat: /about.html · clean: /about · pretty: /about/
tags: true                   # a page per tag at /tag/<name>.html
archive: true                # /archive.html with posts grouped by year
gemini: false                # also build a Gemini capsule

markdown:
  highlight:
    style: monokai           # any Pygments style name
```

### All options

| Option | Default | What it does |
| --- | --- | --- |
| `title`, `url` | — | Required |
| `description`, `author`, `email`, `language`, `image` | empty, `en` | Used in meta tags and the feed |
| `theme` | none | `default`, or a path to your own theme folder |
| `menu`, `footer_menu` | `[]` | Lists of `{name, url}` links |
| `urls` | `flat` | How pages are linked: `flat`, `clean` or `pretty` |
| `paths.content` / `templates` / `static` / `output` / `data` | `content`, `template`, `static`, `public`, `data` | Folder names |
| `partials.home` / `header` / `footer` | `content/home.md` … | Markdown snippets used by templates |
| `templates.home` / `note` / `list` | `home.html`, `note.html`, `list.html` | Which templates to use |
| `posts.tag` | `note` | The tag that makes a page a post |
| `markdown.extras` | tables, footnotes, fenced code… | [markdown2 extras](https://github.com/trentm/python-markdown2/wiki/Extras) to enable |
| `markdown.highlight` | on, `monokai` | Code highlighting; `highlight: false` turns it off |
| `markdown.strip_classes` | `true` | Remove the CSS classes Markdown adds |
| `markdown.lazy_images` | `true` | Add `loading="lazy"` and image sizes |
| `feed` | on, `rss.xml` | `output`, `limit`, `full_content`, `tag_feeds` |
| `sitemap`, `robots` | on | `sitemap.xml` and `robots.txt` |
| `tags`, `archive`, `opml`, `gemini` | off | Extra pages; set to `true` to turn on |
| `redirects` | on | Redirect pages for `aliases:` |
| `reading_speed` | `200` | Words per minute for reading time |
| `plugins` | `[]` | Your plugins (see [Plugins](#plugins)) |

Run `rynz config` to see every value your site is actually using.

---

## Commands

| Command | What it does |
| --- | --- |
| `rynz new my-site` | Start a new site in `my-site/` |
| `rynz add "Title"` | Create a new post (as a draft) |
| `rynz serve` | Preview at http://127.0.0.1:5555; rebuilds when you save. `-p 8080` for another port |
| `rynz build` | Build the site into `public/`. `--drafts`, `--incremental`, `--check` |
| `rynz check` | Find broken links, missing titles and images without alt text |
| `rynz config` | Show your full configuration and check it for mistakes |
| `rynz migrate` | Upgrade a rynz 1.x `config.yml` to the new key names |
| `rynz init-ci gitlab` | Write a deploy file: `gitlab`, `cloudflare` or `rsync` |

Add `-q` for quiet output or `--verbose` for every step. `rynz -C path/to/site build` runs in another folder.

---

## Templates and themes

rynz looks for each template in this order:

1. your `template/` folder
2. the theme named in `config.yml`
3. rynz's built-in templates

So to change one thing, copy just that file into `template/` and edit it. To change the look, put your own `nss.css` in `static/`.

The default theme's files are `base.html`, `home.html`, `note.html`, `list.html`, `partials/head.html`, `partials/nav.html`, `partials/footer.html`, `feed.xml`, `sitemap.xml` and `robots.txt`.

### What templates can use

| Variable | Contains |
| --- | --- |
| `page.title`, `page.description`, `page.date`, `page.updated`, `page.tags` | From frontmatter |
| `page.html` | The page's content as HTML |
| `page.url`, `page.permalink` | Link (`/about.html`) and full address |
| `page.toc`, `page.reading_time`, `page.words` | Table of contents, minutes, word count |
| `page.prev`, `page.next` | Older and newer post |
| `site.posts`, `site.pages` | Every post / every page, newest first |
| `site.tags`, `site.years` | Posts grouped by tag / by year |
| `site.data.<file>` | Contents of `data/<file>.yml` |
| `site.home`, `site.header`, `site.footer` | The Markdown snippets, as HTML |
| `config` | Everything in `config.yml` |

Filters: `date("%d %b %Y")`, `iso`, `rfc822`, `xml`, `absolute_url`.

---

## Plugins

A plugin is a Python file with a `register` function. List it in `config.yml`:

```yaml
title: My site
url: https://example.com
plugins:
  - plugins/humans.py
```

`plugins/humans.py`:

```python
def register(rynz):
    @rynz.generator
    def humans(site, render):
        yield "humans.txt", f"Written by {site.config['author']}\n"

    @rynz.hook("html")
    def highlight_todos(html, page, site):
        return html.replace("TODO", "<mark>TODO</mark>")
```

| Hook | Runs | Arguments |
| --- | --- | --- |
| `config` | after config.yml is read | `config` |
| `page` | after a page's frontmatter is read | `page, site` |
| `html` | after Markdown becomes HTML; return the new HTML | `html, page, site` |
| `site` | after posts and tags are collected | `site` |
| `context` | before a page's template renders | `context, page, site` |
| `done` | after every file is written | `site, written` |

Also available: `@rynz.generator` to add files (yield `path, content`) and `@rynz.filter("name")` to add a template filter. rynz's own feed, sitemap, tags, archive, redirects, OPML and Gemini output are built with this same API; see `rynz/features/` for examples.

---

## Deploying

`rynz init-ci` writes a ready-to-use deploy file:

| Where | Command | Notes |
| --- | --- | --- |
| GitLab Pages | `rynz init-ci gitlab` | Builds and publishes on every push to your main branch |
| Cloudflare Workers | `rynz init-ci cloudflare` | Add `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID` as CI variables |
| Your own server | `rynz init-ci rsync` | Then `DEST=user@host:/srv/www ./deploy.sh` |

Every option runs `rynz build --check` first, so a broken link stops the deploy.

---

## Upgrading from rynz 1.x

Your 1.x site builds with 2.0 as it is. rynz prints a warning listing the old config keys, and pages come out the same except for intended fixes:

- Markdown tables, fenced code and lists directly under a bold line now render properly.
- Headings get `id`s, so you can link to them.
- The feed's `<description>` is filled from your config.
- `sitemap.xml` and `robots.txt` are added.

When you're ready, run:

```bash
rynz migrate
```

It renames the old keys in `config.yml` (keeping your comments) and saves a backup as `config.yml.bak`. Renamed commands: `create` → `new`, `deploy` → `build`, `test` → `check`. The old names still work in 2.0. `rynz save` was removed; use git directly.

---

## FAQ

**Does the output really have no JavaScript?** Yes. Not on your pages, not in `rynz serve`. That's why you refresh the browser yourself after a rebuild.

**Why does code highlighting use `style=""` instead of classes?** So highlighted code works with class-free stylesheets. Turn it off with `markdown: {highlight: false}`.

**Can I use my own CSS framework?** Yes. Put your stylesheet in `static/` and your templates in `template/`.

**Where do I report a bug?** At [gitlab.com/niharokz/rynz/-/issues](https://gitlab.com/niharokz/rynz/-/issues).

---

[Changelog](CHANGELOG.md) · [Contributing](CONTRIBUTING.md) · MIT License · made by [Nihar](https://nih.ar)
