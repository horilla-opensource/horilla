from django.contrib import admin

from horilla_views.models import (
    ActiveGroup,
    ActiveTab,
    ParentModel,
    ToggleColumn,
    childModel,
)

admin.site.register([ToggleColumn, ParentModel, childModel, ActiveTab, ActiveGroup])
