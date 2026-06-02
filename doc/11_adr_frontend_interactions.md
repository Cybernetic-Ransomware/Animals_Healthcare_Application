## Frontend interaction layer: htmx + native dialog

### Date:
`2026-05-31`

### Status
Done

### Context
The application uses PicoCSS server-rendered Django templates (ADR-06).
As the UI grew — tab-based animal profile, note creation from multiple surfaces — we needed
lightweight interactivity without adopting a full SPA or build pipeline.

Requirements:
- Partial page updates (tab panels loaded on demand)
- Modal dialogs for note forms (avoid full-page navigation)
- No JS build step; vendor scripts served from `static/js/vendor/`
- Graceful degradation: every interactive element must still work with JS disabled

Alternatives considered:
- **Alpine.js** — suitable for reactive bindings but no partial-rendering primitives.
- **Turbo (Hotwire)** — heavier Rails-centric model; Streams would require more backend work.
- **Full SPA (React/Vue)** — contradicts the monolith-first strategy in ADR-03 and adds build complexity.

### Decision
- **htmx** (vendored, no CDN dependency) for partial rendering:
  tab panel loading and modal form injection.
- **Native HTML `<dialog>` element** styled by Pico CSS as the sole modal primitive.
  One `<dialog id="ahc-modal">` lives in `base.html` and is reused by all modal surfaces.
- Django views branch on `request.headers.get("HX-Request")`:
  - GET → return `partials/modal_note_form.html` (no base layout)
  - POST success → `HttpResponse(status=204)` with `HX-Redirect` header
  - POST invalid → re-render the partial (htmx swaps errors back into `#modal-body`)
- `window.initNoteForm()` convention: per-form JS is exposed as a named global function
  and called from `modal.js` after every htmx swap into `#modal-body`.

### Consequences
- Every htmx trigger must also carry `href` for graceful degradation.
- Views that support modal loading need `get_template_names()` override and `form_action` / `legend` in context.
- `hiding_note_fields_in_form.js` (and any future per-form JS) must expose a stable `window.init*` function
  so `modal.js` can re-initialise it after each swap.
- htmx and `modal.js` are loaded globally on every page via `base.html`; scripts are small and guarded.
- The `{% block tab_nav %}` extension point in `base.html` is the designated place for tab bars;
  `{% block extra_css %}` and `{% block extra_js %}` remain for page-specific assets.

### Keywords
- htmx, modal, dialog, partial template, tab, frontend, interaction

### Links
*[2026-05-31]*\
https://htmx.org/reference/#response_headers (HX-Redirect)\
https://picocss.com/docs/modal (native dialog styling)
