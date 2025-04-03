from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import PermissionDenied
from django import forms
from .models import Project
from employee.models import Employee
from .decorators import project_access_required, project_create_required, project_update_required, delete_permission
import logging
from django_select2.forms import Select2MultipleWidget
# Set up logging
logger = logging.getLogger(__name__)

# Project Form (Removed actual_cost)
class ProjectForm(forms.ModelForm):
    team_members = forms.ModelMultipleChoiceField(
        queryset=Employee.objects.all(),
        widget=Select2MultipleWidget(attrs={'class': 'form-control', 'data-placeholder': 'Search and select team members'}),
        required=False
    )

    class Meta:
        model = Project
        fields = ['name', 'start_date', 'end_date', 'attachment', 'description1',
                  'status', 'project_owner', 'team_members', 'estimated_cost']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Project Name', 'required': True}),
            'start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control', 'required': True}),
            'end_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'description1': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Project Description', 'required': True}),
            'status': forms.Select(attrs={'class': 'form-select', 'required': True}),
            'project_owner': forms.Select(attrs={'class': 'form-select', 'required': True}),
            'estimated_cost': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Estimated Cost', 'required': True}),
        }

# List Projects
@login_required
def project_list(request):
    query = request.GET.get('q', '').strip()

    try:
        employee = Employee.objects.filter(employee_user_id=request.user).first()
        if not employee and not request.user.is_superuser:
            messages.error(request, _('Employee profile not found for current user.'))
            return redirect('home-page')

        if request.user.is_superuser:
            projects = Project.objects.filter(name__icontains=query) if query else Project.objects.all()
        else:
            projects = Project.objects.filter(team_members=employee)
            if query:
                projects = projects.filter(name__icontains=query)

        context = {
            'projects': projects,
            'query': query,
            'page_title': _('Projects List'),
            'is_admin': request.user.is_superuser,
        }
        return render(request, 'project/project_list.html', context)

    except Exception as e:
        logger.error(f"Error in project_list: {e}")
        messages.error(request, _('An error occurred while fetching projects.'))
        return redirect('home-page')

# View Project Details
@login_required
@project_access_required("project.view_project")
def project_detail(request, pk):
    project = get_object_or_404(Project, pk=pk)

    try:
        profit_margin = project.get_profit_margin() if hasattr(project, 'get_profit_margin') else None
    except Exception as e:
        logger.error(f"Error calculating profit margin: {e}")
        profit_margin = None

    context = {
        'project': project,
        'page_title': f"Project: {project.name}",
        'profit_margin': profit_margin,
        'is_admin': request.user.is_superuser,
    }
    return render(request, 'project/project_detail.html', context)

# Create Project
@login_required
@project_create_required()
def project_create(request):
    if request.method == 'POST':
        form = ProjectForm(request.POST, request.FILES)
        if form.is_valid():
            project = form.save(commit=False)
            project.attachment = request.FILES.get('attachment', None)  # Handle file properly
            project.save()
            form.save_m2m()
            messages.success(request, _('Project created successfully'))
            return redirect('project:project_detail', pk=project.pk)
        else:
            logger.error(f"Project Form Errors: {form.errors}")
            messages.error(request, _('Please fill all the required fields correctly.'))
    else:
        form = ProjectForm()

    return render(request, 'project/project_form.html', {
        'form': form,
        'is_admin': True
    })

# Update Project
@login_required
@project_update_required()
def project_update(request, pk):
    project = get_object_or_404(Project, pk=pk)

    if request.method == 'POST':
        form = ProjectForm(request.POST, request.FILES, instance=project)
        if form.is_valid():
            if not request.FILES.get('attachment'):
                form.instance.attachment = project.attachment 
            project = form.save(commit=False)
            project.save()
            form.save_m2m()
            messages.success(request, _('Project updated successfully'))
            return redirect('project:project_detail', pk=project.pk)
        else:
            logger.error(f"Project Update Form Errors: {form.errors}")
            messages.error(request, _('Please fill all the required fields correctly.'))
    else:
        form = ProjectForm(instance=project)

    return render(request, 'project/project_form.html', {
        'form': form,
        'project': project,
        'page_title': _('Update Project'),
        'is_admin': True
    })

# Delete Project
@login_required
@delete_permission
def project_delete(request, pk):
    project = get_object_or_404(Project, pk=pk)
    
    if request.method == 'POST':
        project.delete()
        messages.success(request, _('Project deleted successfully'))
        return redirect('project:project_list')

    return render(request, 'project/project_confirm_delete.html', {
        'project': project,
        'page_title': _('Delete Project'),
        'is_admin': True
    })
