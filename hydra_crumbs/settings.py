from hydra.settings import TEMPLATES

TEMPLATES[0]["OPTIONS"]["context_processors"].append(
    "hydra_crumbs.context_processors.breadcrumbs",
)
