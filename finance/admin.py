from django.contrib import admin
from .models import Finance, EmployeeAllocation , CostDistribution
admin.site.register(CostDistribution)
admin.site.register(EmployeeAllocation)

from .models import ProfitDistribution

@admin.register(ProfitDistribution)
class ProfitDistributionAdmin(admin.ModelAdmin):
    list_display = ("project", "category", "percentage")