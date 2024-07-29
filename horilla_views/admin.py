from django.contrib import admin

from horilla_views import models

admin.site.register(
    [
        models.ToggleColumn,
        models.ActiveTab,
        models.ActiveGroup,
        models.SavedFilter,
        models.ActiveView,
    ]
)
