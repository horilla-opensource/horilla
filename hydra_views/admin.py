from django.contrib import admin

from hydra_views.models import ActiveGroup, ActiveTab, SavedFilter, ToggleColumn

admin.site.register([ToggleColumn, ActiveTab, ActiveGroup])
