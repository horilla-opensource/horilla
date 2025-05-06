from django.contrib import admin
from horilla_views.models import (
    ToggleColumn,
    ActiveTab,
    ActiveGroup,
    SavedFilter
)

admin.site.register([ToggleColumn, ActiveTab, ActiveGroup])
