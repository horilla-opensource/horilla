from django.contrib import admin
from horilla_views.models import (
    ToggleColumn,
    ParentModel,
    childModel,
    ActiveTab,
    ActiveGroup,
)

admin.site.register([ToggleColumn, ParentModel, childModel, ActiveTab, ActiveGroup])
