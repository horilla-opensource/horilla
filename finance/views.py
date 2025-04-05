from django.shortcuts import render, get_object_or_404, redirect
from decimal import Decimal
from django.forms import modelformset_factory
from django.contrib.auth.decorators import login_required
from .decorators import finance_update_required
from employee.models import Employee
from .decorators import project_finance_list
from payroll.models.models import Contract
from django.contrib import messages
from django.forms import modelformset_factory
from django.shortcuts import get_object_or_404, redirect, render
from .decorators import profit_distribution_required
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .decorators import finance_view_required
from .forms import AdditionalCostForm , ProfitDistributionForm , EmployeeAllocationForm , CostDistributionForm , AdditionalCostForm
from project.models import Project
from .models import AdditionalCost, Project, Finance , AdditionalCost 
from .models import AdditionalCost, Project
from .models import Finance, CostDistribution, EmployeeAllocation,ProfitDistribution



CostDistributionFormSet = modelformset_factory(
    CostDistribution,
    form=CostDistributionForm,
    extra=0,
    can_delete=True
)
EmployeeAllocationFormSet = modelformset_factory(
    EmployeeAllocation,
    form=EmployeeAllocationForm,
    extra=0,
    can_delete=False
)
@login_required
@project_finance_list()
def finance_project_list(request):
    query = request.GET.get("q", "")
    projects = Project.objects.filter(name__icontains=query) if query else Project.objects.all()
    context = {
        "projects": projects,
    }
    return render(request, "finance/finance_project_list.html", context)


@login_required
@finance_view_required()
def finance_dashboard(request, project_id):
    project = get_object_or_404(Project.objects.prefetch_related("team_members__contract_set"), id=project_id)
    employee_allocations = []
    additional_costs = AdditionalCost.objects.filter(project=project)
    total_additional_costs = 0
    for costs in additional_costs:
        total_additional_costs = sum(costs.cost_value for costs in additional_costs)
    total_employee_cost = Decimal(0)
    allocations = EmployeeAllocation.objects.filter(finance__project=project).select_related("employee")
    allocation_map = {alloc.employee_id: alloc for alloc in allocations}
    for employee in project.team_members.all():
        contract = employee.contract_set.order_by("-contract_start_date").first()
        monthly_salary = Decimal(contract.wage) / Decimal(12) if contract and contract.wage else Decimal(0)
        allocation = allocation_map.get(employee.id)
        percentage_allocation = Decimal(allocation.percentage_allocation) if allocation else Decimal(0)
        allocated_cost = (percentage_allocation / Decimal(100)) * monthly_salary
        employee_allocations.append({
            "employee": employee,
            "monthly_salary": monthly_salary,
            "percentage_allocation": percentage_allocation,
            "allocated_cost": allocated_cost,
        })
        total_employee_cost += allocated_cost
    estimated_cost = project.estimated_cost
    cost_distributions = CostDistribution.objects.filter(project=project).only("category", "percentage")
    calculated_costs = []
    operational_cost = Decimal(0)
    for dist in cost_distributions:
        calculated_value = (Decimal(dist.percentage) / Decimal(100)) * estimated_cost
        calculated_costs.append({
            "category": dist.category,
            "percentage": dist.percentage,
            "calculated_value": calculated_value,
        })
        if dist.category.lower() in ["operation cost", "operational cost"]:
            operational_cost = calculated_value
    profit = operational_cost - total_employee_cost - total_additional_costs
    profit_distributions = ProfitDistribution.objects.filter(project=project).only("category", "percentage")
    distributed_profits = [
        {
            "category": dist.category,
            "percentage": dist.percentage,
            "allocated_profit": dist.allocated_profit(profit),
        }
        for dist in profit_distributions
    ]
    context = {
        "project": project,
        "employee_allocations": employee_allocations,
        "total_employee_cost": total_employee_cost,
        "estimated_cost": estimated_cost,
        "calculated_costs": calculated_costs,
        "operational_cost": operational_cost,
        "profit": profit,
        "distributed_profits": distributed_profits,
        "additional_costs": additional_costs,
    }
    return render(request, "finance/finance_dashboard.html", context)




@login_required
@finance_update_required()
def finance_project_edit(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    finance, created = Finance.objects.get_or_create(project=project)
    project_employees = Employee.objects.filter(assigned_projects=project)
    EmployeeAllocation.objects.filter(finance=finance).exclude(employee__in=project_employees).delete()
    for employee in project_employees:
        EmployeeAllocation.objects.get_or_create(finance=finance, employee=employee)
    ea_qs = EmployeeAllocation.objects.filter(finance=finance)
    cd_qs = CostDistribution.objects.filter(project=project)

    if request.method == 'POST':
        cd_formset = CostDistributionFormSet(request.POST, queryset=cd_qs, prefix='cd')
        ea_formset = EmployeeAllocationFormSet(request.POST, queryset=ea_qs, prefix='ea')

        if cd_formset.is_valid() and ea_formset.is_valid():
            total_percentage = sum(
                form.cleaned_data.get('percentage', 0)
                for form in cd_formset
                if form.cleaned_data and not form.cleaned_data.get('DELETE', False)
            )
            if total_percentage != 100:
                messages.error(request, f"Total cost distribution must equal 100%. Current total is {total_percentage:.2f}%.")
            else:
                for form in cd_formset:
                    if form.cleaned_data:
                        if form.cleaned_data.get('DELETE', False) and form.instance.pk:
                            form.instance.delete()
                        else:
                            instance = form.save(commit=False)
                            instance.project = project
                            instance.save()
                for form in ea_formset:
                    if form.cleaned_data:
                        instance = form.save(commit=False)
                        instance.allocated_cost = (
                            (Decimal(instance.percentage_allocation) / Decimal(100)) * Decimal(project.estimated_cost)
                        )
                        instance.save()
                messages.success(request, "Cost distribution and employee allocations updated successfully.")
                return redirect('finance_dashboard', project_id=project.id)
        else:
            messages.error(request, "There was an error updating the forms. Please check your inputs.")
    cd_formset = CostDistributionFormSet(queryset=cd_qs, prefix='cd')
    ea_formset = EmployeeAllocationFormSet(queryset=ea_qs, prefix='ea')
    context = {
        'project': project,
        'cd_formset': cd_formset,
        'ea_formset': ea_formset,
    }
    return render(request, 'finance/project_edit.html', context)


@login_required
@profit_distribution_required()
def profit_distribution_view(request, project_id):
    finance = get_object_or_404(Finance.objects.select_related("project"), project__id=project_id)
    project = get_object_or_404(Project.objects.prefetch_related("team_members__contract_set"), id=project_id)
    additional_costs = AdditionalCost.objects.filter(project=project)
    total_additional_costs = 0
    for costs in additional_costs:
        total_additional_costs = sum(costs.cost_value for costs in additional_costs)
    employee_allocations = []
    total_employee_cost = Decimal(0)
    allocations = EmployeeAllocation.objects.filter(finance__project=project).select_related("employee")
    allocation_map = {alloc.employee_id: alloc for alloc in allocations}
    for employee in project.team_members.all():
        contract = employee.contract_set.order_by("-contract_start_date").first()
        monthly_salary = Decimal(contract.wage) / Decimal(12) if contract and contract.wage else Decimal(0)
        allocation = allocation_map.get(employee.id)
        percentage_allocation = Decimal(allocation.percentage_allocation) if allocation else Decimal(0)
        allocated_cost = (percentage_allocation / Decimal(100)) * monthly_salary
        employee_allocations.append({
            "employee": employee,
            "monthly_salary": monthly_salary,
            "percentage_allocation": percentage_allocation,
            "allocated_cost": allocated_cost,
        })
        total_employee_cost += allocated_cost
    estimated_cost = project.estimated_cost
    cost_distributions = CostDistribution.objects.filter(project=project).only("category", "percentage")
    calculated_costs = []
    operational_cost = Decimal(0)
    for dist in cost_distributions:
        calculated_value = (Decimal(dist.percentage) / Decimal(100)) * estimated_cost
        calculated_costs.append({
            "category": dist.category,
            "percentage": dist.percentage,
            "calculated_value": calculated_value,
        })
        if dist.category.lower() in ["operation cost", "operational cost"]:
            operational_cost = calculated_value
    total_profit = operational_cost - total_employee_cost - total_additional_costs
    ProfitFormSet = modelformset_factory(ProfitDistribution, form=ProfitDistributionForm, extra=1, can_delete=True)
    formset = ProfitFormSet(queryset=ProfitDistribution.objects.filter(project=finance.project).only("category", "percentage"))
    if request.method == "POST":
        formset = ProfitFormSet(request.POST)
        if formset.is_valid():
            total_percentage = sum(
                form.cleaned_data["percentage"] for form in formset if form.cleaned_data and not form.cleaned_data.get("DELETE")
            )
            if total_percentage != 100:
                messages.error(request, "Total profit distribution must be 100%.")
            else:
                instances = formset.save(commit=False)
                for instance in instances:
                    instance.project = finance.project
                    instance.save()
                for obj in formset.deleted_objects:
                    obj.delete()
                messages.success(request, "Profit distribution updated successfully.")
                return redirect("finance_dashboard", project_id=project_id)
    return render(request, "finance/profit_distribution.html", {
        "formset": formset,
        "total_profit": total_profit,
        "finance": finance
    })


@login_required
def add_additional_cost(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    
    AdditionalCostFormSet = modelformset_factory(
        AdditionalCost, form=AdditionalCostForm, extra=1, can_delete=True
    )
    
    additional_costs = AdditionalCost.objects.filter(project=project)

    if request.method == "POST":
        formset = AdditionalCostFormSet(request.POST, queryset=additional_costs)
        if formset.is_valid():
            instances = formset.save(commit=False)
            for instance in instances:
                instance.project = project  
                instance.save()
            for obj in formset.deleted_objects:
                obj.delete()  
            messages.success(request, "Additional costs updated successfully.")
            return redirect("finance_dashboard", project_id=project_id)
        else:
            print(formset.errors)  

    else:
        formset = AdditionalCostFormSet(queryset=additional_costs)

    return render(request, "finance/additional_costs.html", {
        "formset": formset,
        "project": project,
    })

from django.shortcuts import render
def finance_reports(request):
    from .models import FinanceReport  # Move import inside the function
    reports = FinanceReport.objects.all()
    return render(request, "finance/reports.html", {"reports": reports})



