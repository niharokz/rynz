
# Rynz

🕊️ **Rynz: Really Your Note Zenerator**  
Rynz is a lightweight, JavaScript-free static site generator crafted for developers who value Markdown, speed, and simplicity. Built with Python and Jinja2, it delivers fast, customizable static websites with an intuitive CLI, optimized page generation, and clean, minimal templates. The main website for the Rynz project is [https://rynz.de](https://rynz.de).


## Why Choose Rynz?
- **Blazing Fast**: Optimized page generation for rapid site builds.
- **No JavaScript**: Lightweight, clean HTML output by default.
- **Clean Templates**: Streamlined Jinja2 templates for easy customization.
- **Python-Powered**: Modular, forkable codebase for extensibility.
- **Markdown-First**: Effortless content creation with Markdown.
- **Open-Source**: Licensed under the [MIT License](#license).

## Table of Contents
- [Installation](#installation)
- [Usage](#usage)
- [Configuration](#configuration)
- [Folder Structure](#folder-structure)
- [Advanced Features](#advanced-features)
- [Example](#example)
- [Changelog](#changelog)
- [Contributing](#contributing)
- [License](#license)
- [Contact](#contact)

## Installation

Install Rynz via `pip` for the latest stable release:

```bash
pip install rynz
```

Or install the development version from GitLab:

```bash
pip install git+https://gitlab.com/niharokz/rynz
```

### Prerequisites
- Python 3.8 or higher
- `pip` for dependency management

### Dependencies
Rynz automatically installs:
- `pyyaml`: Parses `config.yml` and frontmatter.
- `jinja2`: Powers templating for HTML output.
- `markdown2`: Converts Markdown to HTML.
- `rich`: Enhances CLI with colorful output.

## Usage

Rynz provides a streamlined CLI for managing your static site. Run `rynz --help` for details.

```bash
usage: rynz [-h] [-v] {create,add,deploy,serve,config,test,save} ...

🕊️ Rynz: Really Your Note Zenerator.

positional arguments:
  {create,add,deploy,serve,config,test,save}
                        Available commands
    create              Create a new Rynz project.
    add                 Create a new note or blog post.
    deploy              Convert Markdown files into static HTML
    serve               Serve your site locally at http://localhost:5555
    config              View or edit site configuration (config.yml)
    test                Test your Rynz setup and structure
    save                Save changes with Git (stage and commit)

options:
  -h, --help            show this help message and exit
  -v, --version         show program's version number and exit
```

### 1. Create a New Project
Initialize a new project with the default structure:

```bash
rynz create my-site
```

Sets up `my-site/` with `config.yml`, templates, and content directories.

### 2. Add a New Note or Post
Create a new Markdown file:

```bash
rynz add pageName
```

Generates `content/note/pageName.md` with frontmatter.

### 3. Deploy the Site
Convert Markdown to static HTML, outputting to `public/`:

```bash
rynz deploy
```

### 4. Serve Locally
Preview your site with a local server:

```bash
rynz serve
```

Access at [http://localhost:5555](http://localhost:5555). Use a custom port:

```bash
rynz serve -p 8080
```

### 5. Manage Configuration
View or edit `config.yml`:

```bash
rynz config
```

Check `rynz config --help` for specific options.

### 6. Test Your Setup
Validate your project structure and configuration:

```bash
rynz test
```

Ensures no missing files or invalid frontmatter.

### 7. Save Changes with Git
Stage and commit changes:

```bash
rynz save
```

Or commit with a custom message:

```bash
rynz save -m "Your commit message"
```

## Configuration

Customize your site with `config.yml` in the project root. Example:

```yaml
site_title: My Rynz Site
base_url: https://example.com
theme: default
favicon: resource/favicon.ico
```

Access in templates with Jinja2:

```html
<link rel="icon" href="{{ config.get('favicon') }}">
```

## Folder Structure

```bash
my-site/
|-- public/                  # Generated HTML output
|-- config.yml               # Site configuration
|-- content/                 # Markdown content
|   |-- header.md           # Header content
|   |-- footer.md           # Footer content
|   |-- home.md             # Homepage content
|   `-- note/               # Individual pages/notes
|       `-- sample.md
|-- resource/                # Static assets (CSS, images, etc.)
|   `-- style.css
`-- templates/               # Jinja2 templates
    |-- home_template.html  # Homepage template
    `-- note_template.html  # Note/page template
```

### Folder Breakdown
- **`config.yml`**: Site-wide settings (title, theme, etc.).
- **`content/`**: Markdown files for pages and notes.
- **`resource/`**: Static assets (CSS, images, favicon).
- **`templates/`**: Jinja2 templates for HTML output.
- **`public/`**: Built site output.

## Advanced Features

### 1. Faster Page Generation
Rynz v1.0.0 optimizes rendering with streamlined Markdown processing and efficient Jinja2 templating, significantly reducing build times.

### 2. Cleaner Templates
Templates are now more modular and minimal, with simplified Jinja2 syntax for easier customization and maintenance.

### 3. Homepage Visibility via Tags
Control homepage visibility with tags. Add `home` to frontmatter:

```markdown
---
tags: [home]
---
```

Filter in `home_template.html`:

```html
{% for page in pages if 'home' in page.tags %}
  <a href="{{ page.url }}">{{ page.title }}</a>
{% endfor %}
```

### 4. Custom Metadata
Add per-page metadata:

```yaml
meta: '<link rel="stylesheet" href="/extra.css">'
```

Render in templates:

```html
{{ page.meta | safe }}
```

### 5. Extended Configuration
Add custom keys to `config.yml`:

```yaml
analytics_id: UA-XXXXX-Y
```

Use in templates:

```html
<script src="https://analytics.com/{{ config.get('analytics_id') }}"></script>
```

## Example

Explore a live Rynz-generated site:  
[https://nih.ar](https://nih.ar)
[https://rynz.de](https://rynz.de)

View its source:  
[https://gitlab.com/niharokz/nih.ar](https://gitlab.com/niharokz/nih.ar)

## Changelog

### v1.0.0 (April 2025) - Major Release
- **New CLI Commands**: Introduced `create`, `add`, `deploy`, `serve`, `config`, `test`, and `save` for a streamlined workflow.
- **Faster Page Generation**: Optimized Markdown processing and Jinja2 rendering for significantly reduced build times.
- **Cleaner Templates**: Simplified and modularized Jinja2 templates for easier customization.
- **Config Command**: Added `rynz config` to view/edit `config.yml`.
- **Test Command**: Added `rynz test` to validate project setup and structure.
- **Save Command**: Added `rynz save` to easily commit changes using Git.
- **Removed RSS Support**: Eliminated RSS feed generation and `rss_enabled` option for a leaner feature set.
- **Improved CLI**: Enhanced help output and error handling with `rich`.
- **Python Support**: Added compatibility for Python 3.11+.
- **Bug Fixes**: Resolved edge cases in frontmatter parsing and template rendering.

### v0.9.9 (Beta)
- Replaced `showInHome` with tag-based homepage visibility.
- Improved CLI error handling with color-coded output.
- Optimized build performance and modularity.

### v0.9.8 (Beta)
- Added custom port support for `serve`.
- Auto-handled `/abc` → `/abc.html` in dev server.
- Supported metadata injection via `meta` tag.
- Improved Windows compatibility.

See [CHANGELOG.md](CHANGELOG.md) for full details.

## Contributing

Contributions are welcome! To contribute:

1. Fork the repository.
2. Create a feature branch:
   ```bash
   git checkout -b feature/my-feature
   ```
3. Commit changes:
   ```bash
   git commit -m "Add my feature"
   ```
4. Push to the branch:
   ```bash
   git push origin feature/my-feature
   ```
5. Open a pull request.

### Code Style
- Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) for Python.
- Run tests:
   ```bash
   python -m unittest discover
   ```

## License

Licensed under the MIT License. See [LICENSE](LICENSE) for details.

## Contact

- **Maintainer**: Nihar (hi@nihars.com)
- **Repository**: [https://gitlab.com/niharokz/rynz](https://gitlab.com/niharokz/rynz)
- **Issues**: [https://gitlab.com/niharokz/rynz/-/issues](https://gitlab.com/niharokz/rynz/-/issues)

---

*Built with ❤️ using Python and Jinja2. Star the repo if Rynz sparks joy!*
