from moared.settings import TEMPLATES

TEMPLATES[0]["OPTIONS"]["context_processors"].append(
    "moared_crumbs.context_processors.breadcrumbs",
)
