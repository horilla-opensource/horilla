from django.urls import path
from .views import finance_project_list, finance_dashboard, finance_project_edit ,profit_distribution_view  , add_additional_cost 
urlpatterns = [
    path("", finance_project_list, name="finance_project_list"),
    path("<int:project_id>/", finance_dashboard, name="finance_dashboard"),
    path("<int:project_id>/edit/", finance_project_edit, name="finance_project_edit"),
    path('profit-distribution/<int:project_id>/', profit_distribution_view, name='profit_distribution_view'),
    path("<int:project_id>/add-additional-cost/", add_additional_cost, name="add_additional_cost"),
]