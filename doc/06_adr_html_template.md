## HTML template framework — PicoCSS selected

### Date
`2023-06-05` (updated `2026-05-31`)

### Status
Done

### Context
The application uses Django server-side rendering with standard HTML templates.
A CSS framework was needed to provide consistent styling, responsive layout,
and accessible components without adding a JavaScript build pipeline.

Requirements:
- Semantic HTML-first approach (no utility-class soup)
- Dark mode support
- Minimal JavaScript dependency
- Works well with Django template inheritance

Alternatives considered:
- **Bootstrap 5** — widely used but class-heavy; overrides are verbose.
- **Tailwind CSS** — requires a build step; conflicts with the no-build-pipeline constraint.
- **Bulma** — no dark mode out of the box.
- **Plain CSS** — too much boilerplate for a rapid prototype.

### Decision
**Pico CSS 2.1.1** was selected. It styles native HTML elements directly (no class annotations needed
for most components), ships a dark mode variant, and requires zero JavaScript.

Configuration:
- Theme file: `static/css/pico-2.1.1/pico.yellow.min.css` (yellow accent, dark mode).
- All custom overrides and project-specific styles live in `static/css/custom_pico.css`.
  This is the single source of truth for new styles — do not override Pico inline or in templates.
- CSS custom properties are defined in `:root` at the top of `custom_pico.css`:

| Variable             | Value                  | Role              |
|----------------------|------------------------|-------------------|
| `--ahc-font-display` | Bricolage Grotesque    | Headings font     |
| `--ahc-font-body`    | DM Sans                | Body font         |

Both fonts are loaded via Google Fonts (`<link rel="preconnect">` + stylesheet) in `base.html`.

### Consequences
- Pico's opinionated defaults mean most form elements, buttons, and layout primitives look
  styled without any class attributes — useful for rapid prototyping.
- Overriding Pico defaults requires understanding its CSS custom property cascade; inspect
  `custom_pico.css` before adding new styles to avoid duplicates.
- JavaScript-free modal support uses the native `<dialog>` element styled by Pico (see ADR-11).
- Dark mode is handled by Pico automatically; custom colors must be defined using CSS variables
  in both `:root` and `[data-theme="dark"]` scopes if they need to respond to theme switching.

### Keywords
- frontend, CSS, Pico CSS, dark mode, template, HTML

### Links
*[2026-05-31]*\
https://picocss.com/docs

*[2023-06-15]*\
https://picocss.com/

*[2023-05-23]*\
[One of the fastest ways to make the Django app look good](https://levelup.gitconnected.com/one-of-the-fastest-ways-to-make-the-django-app-look-good-c2b23006a574)
