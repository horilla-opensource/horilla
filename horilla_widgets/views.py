from django.shortcuts import render

# Create your views here.

# urls.py
# path("employee-widget-filter",views.widget_filter,name="employee-widget-filter")

# views.py
# @login_required
# def widget_filter(request):
#     """
#     This method is used to return all the ids of the employees
#     """
#     ids = EmployeeFilter(request.GET).qs.values_list("id", flat=True)
#     return JsonResponse({'ids':list(ids)})