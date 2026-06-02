## Main web framework — Django selected

### Date
`2023-06-05`

### Status
Done

### Context
A main web framework was needed to build the core of the application.

Alternatives considered:
- **Django** — full-featured, batteries-included; ORM, admin, auth, templating out of the box.
- **Flask** — microframework; would require assembling more components manually.
- **Dash Plotly** — derivative of Flask focused on interactive dashboards; dashboard functionality was deferred (see ADR-05).

### Decision
Django was selected. The developer had the most recent hands-on experience with it and wanted to
deepen that knowledge systematically. Flask would have extended time-to-first-prototype with no
offsetting benefit. Dash was out of scope until interactive dashboards are prioritised.

### Consequences
- Short time to a working prototype due to Django's built-in ORM, admin, and auth.
- Strong community and plugin ecosystem (DRF, Celery integration, etc.).
- The monolithic architecture (ADR-03) aligns naturally with Django's app model.

### Keywords
- Django, Flask, Dash Plotly, web framework

### Links
*[2023-06-05]*\
https://www.djangoproject.com/\
https://flask.palletsprojects.com\
https://dash.plotly.com/

*[2021-11-26]*\
[List of 7 Best Python Frameworks to Consider For Your Web Project](https://www.monocubed.com/blog/top-python-frameworks/)
