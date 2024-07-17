""""
asset.py

This module is used to """

import json
from datetime import date, datetime
from urllib.parse import parse_qs

import pandas as pd
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import ProtectedError
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from asset.filters import (
    AssetAllocationFilter,
    AssetAllocationReGroup,
    AssetCategoryFilter,
    AssetExportFilter,
    AssetFilter,
    AssetHistoryFilter,
    AssetHistoryReGroup,
    AssetRequestFilter,
    AssetRequestReGroup,
    CustomAssetFilter,
)
from asset.forms import (
    AssetAllocationForm,
    AssetBatchForm,
    AssetCategoryForm,
    AssetForm,
    AssetReportForm,
    AssetRequestForm,
    AssetReturnForm,
)
from asset.models import (
    Asset,
    AssetAssignment,
    AssetCategory,
    AssetDocuments,
    AssetLot,
    AssetRequest,
    ReturnImages,
)
from base.methods import (
    closest_numbers,
    filtersubordinates,
    get_key_instances,
    get_pagination,
    sortby,
)
from base.models import Company
from base.views import paginator_qry
from employee.models import EmployeeWorkInformation
from horilla.decorators import (
    hx_request_required,
    login_required,
    manager_can_enter,
    permission_required,
)
from horilla.group_by import group_by_queryset
from notifications.signals import notify


def asset_del(request, asset):
    """
    Handle the deletion of an asset and provide message to the user.
    """
    try:
        asset.delete()
        messages.success(request, _("Asset deleted successfully"))
    except ProtectedError:
        messages.error(request, _("You cannot delete this asset."))


@login_required
@hx_request_required
@permission_required("asset.add_asset")
def asset_creation(request, asset_category_id):
    """
    View function for creating a new asset object.
    Args:
        request (HttpRequest): A Django HttpRequest object that contains information
        about the current request.
        asset_category_id (int): An integer representing the ID of the asset category for which
        the asset is being created.

    Returns:
        If the request method is 'POST' and the form is valid, the function saves the
        new asset object to the database
        and redirects to the asset creation page with a success message.
        If the form is not valid, the function returns the asset creation page with the
        form containing the invalid data.
        If the request method is not 'POST', the function renders the asset creation
        page with the form initialized with
        the ID of the asset category for which the asset is being created.
    Raises:
        None
    """
    initial_data = {"asset_category_id": asset_category_id}
    form = AssetForm(initial=request.GET.dict() if request.GET else initial_data)
    if request.method == "POST":
        form = AssetForm(request.POST, initial=initial_data)
        if form.is_valid():
            form.save()
            messages.success(request, _("Asset created successfully"))
            return redirect("asset-creation", asset_category_id=asset_category_id)
    context = {"asset_creation_form": form}
    return render(request, "asset/asset_creation.html", context)


@login_required
def add_asset_report(request, asset_id=None):
    """
    Function for adding asset report to the asset
    """
    asset_report_form = AssetReportForm()
    if asset_id:
        asset = Asset.objects.get(id=asset_id)
        asset_report_form = AssetReportForm(initial={"asset_id": asset})
        if not request.GET.get("asset_list"):
            if request.user.employee_get == AssetAssignment.objects.get(
                asset_id=asset_id, return_date__isnull=True
            ).assigned_to_employee_id or request.user.has_perm("asset.change_asset"):
                pass
            else:
                return redirect(asset_request_allocation_view)

    if request.method == "POST":
        asset_report_form = AssetReportForm(
            request.POST, request.FILES, initial={"asset_id": asset_id}
        )

        if asset_report_form.is_valid():
            asset_report = asset_report_form.save()
            messages.success(request, _("Report added successfully."))

            if asset_report_form.is_valid() and request.FILES:
                for file in request.FILES.getlist("file"):
                    AssetDocuments.objects.create(asset_report=asset_report, file=file)

                return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))
            # return HttpResponse("<script>window.location.reload()</script>")

    return render(
        request,
        "asset/asset_report_form.html",
        {"asset_report_form": asset_report_form, "asset_id": asset_id},
    )


@login_required
@hx_request_required
@permission_required("asset.delete_asset")
def asset_update(request, asset_id):
    """
    Updates an asset with the given ID.
    If the request method is GET, it displays the form to update the asset. If the
    request method is POST and the form is valid, it updates the asset and
    redirects to the asset list view for the asset's category.
    Args:
    - request: the HTTP request object
    - id (int): the ID of the asset to be updated
    Returns:
    - If the request method is GET, the rendered 'asset_update.html' template
      with the form to update the asset.
    - If the request method is POST and the form is valid, a redirect to the asset
      list view for the asset's category.
    """

    if request.method == "GET":
        # modal form get
        asset_under = request.GET.get("asset_under")
    elif request.method == "POST":
        # modal form post
        asset_under = request.POST.get("asset_under")

    if not asset_under:
        # if asset there is no asset_under data that means the request is form the category list
        asset_under = "asset_category"
    instance = Asset.objects.get(id=asset_id)
    asset_form = AssetForm(instance=instance)
    previous_data = request.GET.urlencode()

    if request.method == "POST":
        asset_form = AssetForm(request.POST, instance=instance)
        if asset_form.is_valid():
            asset_form.save()
            messages.success(request, _("Asset Updated"))
    context = {
        "asset_form": asset_form,
        "asset_under": asset_under,
        "pg": previous_data,
        "asset_cat_id": instance.asset_category_id.id,
    }
    requests_ids_json = request.GET.get("requests_ids")
    if requests_ids_json:
        requests_ids = json.loads(requests_ids_json)
        request_copy = request.GET.copy()
        request_copy.pop("requests_ids", None)
        previous_data = request_copy.urlencode()
        context["requests_ids"] = requests_ids
        context["pd"] = previous_data
    return render(request, "asset/asset_update.html", context=context)


@login_required
@hx_request_required
def asset_information(request, asset_id):
    """
    Display information about a specific Asset object.
    Args:
        request: the HTTP request object
        asset_id (int): the ID of the Asset object to retrieve
    Returns:
        A rendered HTML template displaying the information about the requested Asset object.
    """

    asset = Asset.objects.get(id=asset_id)
    context = {"asset": asset}
    requests_ids_json = request.GET.get("requests_ids")
    if requests_ids_json:
        requests_ids = json.loads(requests_ids_json)
        previous_id, next_id = closest_numbers(requests_ids, asset_id)
        context["requests_ids"] = requests_ids_json
        context["previous"] = previous_id
        context["next"] = next_id
    return render(request, "asset/asset_information.html", context)


@login_required
@permission_required(perm="asset.delete_asset")
def asset_delete(request, asset_id):
    """Delete the asset with the given id.
    If the asset is currently in use, display an info message and
    redirect to the asset list.
    Otherwise, delete the asset and display a success message.
    Args:
        request: HttpRequest object representing the current request.
        asset_id: int representing the id of the asset to be deleted.
    Returns:
        If the asset is currently in use or the asset list filter is
        applied, render the asset list template
        with the corresponding context.
        Otherwise, redirect to the asset list view for the asset
        category of the deleted asset.
    """
    try:
        asset = Asset.objects.get(id=asset_id)
    except Asset.DoesNotExist:
        messages.error(request, _("Asset not found"))
        return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))
    asset_cat_id = asset.asset_category_id.id
    status = asset.asset_status
    asset_list_filter = request.GET.get("asset_list")
    asset_allocation = AssetAssignment.objects.filter(asset_id=asset).first()
    if asset_list_filter:
        # if the asset deleted is from the filtered list of asset
        asset_under = "asset_filter"
        assets = Asset.objects.all()
        previous_data = request.GET.urlencode()
        asset_filtered = AssetFilter(request.GET, queryset=assets)
        asset_list = asset_filtered.qs
        paginator = Paginator(asset_list, 20)
        page_number = request.GET.get("page")
        page_obj = paginator.get_page(page_number)
        context = {
            "assets": page_obj,
            "pg": previous_data,
            "asset_category_id": asset.asset_category_id.id,
            "asset_under": asset_under,
        }
        if status == "In use":
            messages.info(request, _("Asset is in use"))
        elif asset_allocation:
            messages.error(request, _("Asset is used in allocation!."))
        else:
            asset_del(request, asset)
        return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))

    if status == "In use":
        messages.info(request, _("Asset is in use"))
    elif asset_allocation:
        messages.error(request, _("Asset is used in allocation!."))
    else:
        asset_del(request, asset)
    return redirect(f"/asset/asset-list/{asset_cat_id}")


@login_required
@hx_request_required
def asset_list(request, cat_id):
    """
    View function is used as asset list inside a category and also in
    filter asset list
    Args:
        request (HttpRequest): A Django HttpRequest object that contains
        information about the  current request.
        cat_id (int): An integer representing the id of the asset category
        to list assets for.
    Returns:
        A rendered HTML template that displays a paginated list of assets in the given
        asset  category.
    Raises:
        None
    """
    asset_list_filter = request.GET.get("asset_list")
    asset_info = request.GET.get("asset_info")
    context = {}
    if asset_list_filter:
        # if the data is present means that it is for asset filtered list
        query = request.GET.get("query")
        asset_under = "asset_filter"
        if query:
            assets_in_category = Asset.objects.filter(asset_name__icontains=query)
        else:
            assets_in_category = Asset.objects.all()
    elif asset_info:
        pass
    else:
        # if the data is not present means that it is for asset category list
        asset_under = "asset_category"
        asset_category = AssetCategory.objects.get(id=cat_id)
        assets_in_category = Asset.objects.filter(asset_category_id=asset_category)

    previous_data = request.GET.urlencode()
    asset_filtered = AssetFilter(request.GET, queryset=assets_in_category)
    asset_list = asset_filtered.qs
    # Change 20 to the desired number of items per page
    paginator = Paginator(asset_list, 20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    requests_ids = json.dumps([instance.id for instance in page_obj.object_list])
    data_dict = parse_qs(previous_data)
    get_key_instances(Asset, data_dict)
    context = {
        "assets": page_obj,
        "pg": previous_data,
        "asset_category_id": cat_id,
        "asset_under": asset_under,
        "asset_count": len(assets_in_category) or None,
        "filter_dict": data_dict,
        "requests_ids": requests_ids,
    }
    return render(request, "asset/asset_list.html", context)


@login_required
@hx_request_required
@permission_required(perm="asset.add_assetcategory")
def asset_category_creation(request):
    """
    Allow a user to create a new AssetCategory object using a form.
    Args:
        request: the HTTP request object
    Returns:
        A rendered HTML template displaying the AssetCategory creation form.
    """
    asset_category_form = AssetCategoryForm()

    if request.method == "POST":
        asset_category_form = AssetCategoryForm(request.POST)
        if asset_category_form.is_valid():
            asset_category_form.save()
            messages.success(request, _("Asset category created successfully"))
            asset_category_form = AssetCategoryForm()
            if AssetCategory.objects.filter().count() == 1:
                return HttpResponse("<script>window.location.reload();</script>")
    context = {"asset_category_form": asset_category_form}
    return render(request, "category/asset_category_creation.html", context)


@login_required
@hx_request_required
@permission_required(perm="asset.change_assetcategory")
def asset_category_update(request, cat_id):
    """
    This view is used to update an existing asset category.
    Args:
        request: HttpRequest object.
        id: int value representing the id of the asset category to update.
    Returns:
        Rendered HTML template.
    """

    previous_data = request.GET.urlencode()
    asset_category = AssetCategory.objects.get(id=cat_id)
    asset_category_form = AssetCategoryForm(instance=asset_category)
    context = {"asset_category_update_form": asset_category_form, "pg": previous_data}
    if request.method == "POST":
        asset_category_form = AssetCategoryForm(request.POST, instance=asset_category)
        if asset_category_form.is_valid():
            asset_category_form.save()
            messages.success(request, _("Asset category updated successfully"))
        else:
            context["asset_category_form"] = asset_category_form

    return render(request, "category/asset_category_update.html", context)


@login_required
@permission_required(perm="asset.delete_assetcategory")
def delete_asset_category(request, cat_id):
    """
    This method is used to delete asset category
    """
    previous_data = request.GET.urlencode()
    try:
        AssetCategory.objects.get(id=cat_id).delete()
        messages.success(request, _("Asset category deleted."))
    except:
        messages.error(request, _("Assets are located within this category."))
    if not AssetCategory.objects.filter():
        return HttpResponse("<script>window.location.reload();</script>")
    return redirect(f"/asset/asset-category-view-search-filter?{previous_data}")


def filter_pagination_asset_category(request):
    """
    This view is used for pagination
    """
    search = request.GET.get("search")
    if search is None:
        search = ""

    previous_data = request.GET.urlencode()
    asset_category_queryset = AssetCategory.objects.all().filter(
        asset_category_name__icontains=search
    )
    asset_category_filtered = AssetCategoryFilter(
        request.GET, queryset=asset_category_queryset
    )
    asset_category_paginator = Paginator(asset_category_filtered.qs, get_pagination())
    page_number = request.GET.get("page")
    asset_categories = asset_category_paginator.get_page(page_number)
    data_dict = parse_qs(previous_data)
    get_key_instances(AssetCategory, data_dict)
    asset_creation_form = AssetForm()
    asset_category_form = AssetCategoryForm()
    asset_filter_form = AssetFilter()
    return {
        "asset_creation_form": asset_creation_form,
        "asset_category_form": asset_category_form,
        "asset_categories": asset_categories,
        "asset_category_filter_form": asset_category_filtered.form,
        "asset_filter_form": asset_filter_form.form,
        "pg": previous_data,
        "filter_dict": data_dict,
        "dashboard": request.GET.get("dashboard"),
    }


@login_required
@permission_required(perm="asset.view_assetcategory")
def asset_category_view(request):
    """
    View function for rendering a paginated list of asset categories.
    Args:
        request (HttpRequest): A Django HttpRequest object that contains information
        about the current request.
    Returns:
        A rendered HTML template that displays a paginated list of asset categories.
    Raises:
        None
    """

    queryset = AssetCategory.objects.all()
    if queryset.exists():
        template = "category/asset_category_view.html"
    else:
        template = "category/asset_empty.html"
    context = filter_pagination_asset_category(request)
    return render(request, template, context)


@login_required
@permission_required(perm="asset.view_assetcategory")
def asset_category_view_search_filter(request):
    """
    View function for rendering a paginated list of asset categories with search and filter options.
    Args:
        request (HttpRequest): A Django HttpRequest object that contains information
        about the current request.
    Returns:
        A rendered HTML template that displays a paginated list of asset
        categories  with search and filter options.
    Raises:
        None
    """

    search_type = request.GET.get("type")
    query = request.GET.get("search")
    if search_type == "asset":
        # searching asset will redirect to asset list and pass the query
        return redirect(f"/asset/asset-list/0?asset_list=asset&query={query}")
    context = filter_pagination_asset_category(request)
    return render(request, "category/asset_category.html", context)


@login_required
def asset_request_creation(request):
    """
    Creates a new AssetRequest object and saves it to the database.
    Renders the asset_request_creation.html template if the request method is GET.
    If the request method is POST and the form data is valid, the new
    AssetRequest is saved to the database and
    the user is redirected to the asset_request_view_search_filter view.
    If the form data is invalid, or if the request method is POST but the
    form data is not present, the user is
    presented with the asset_request_creation.html template with error
    messages displayed.
    """
    # intitial  = {'requested_employee_id':request.user.employee_get}
    form = AssetRequestForm(user=request.user)
    context = {"asset_request_form": form}
    if request.method == "POST":
        form = AssetRequestForm(request.POST, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, _("Asset request created!"))
            return HttpResponse("<script>window.location.reload()</script>")
        context["asset_request_form"] = form

    return render(request, "request_allocation/asset_request_creation.html", context)


@login_required
@manager_can_enter(perm="asset.add_asset")
def asset_request_approve(request, req_id):
    """
    Approves an asset request with the given ID and updates the corresponding asset record
    to mark it as allocated.
    Args:
        request: The HTTP request object.
        req_id (int): The ID of the asset request to be approved.
    Returns:
        A redirect response to the asset request allocation view, or an error message if the
        request with the given ID cannot be found or its asset has already been allocated.
    """
    asset_request = AssetRequest.objects.filter(id=req_id).first()
    asset_category = asset_request.asset_category_id
    assets = asset_category.asset_set.filter(asset_status="Available")
    form = AssetAllocationForm()
    form.fields["asset_id"].queryset = assets
    context = {"asset_allocation_form": form, "id": req_id}
    if request.method == "POST":
        post_data = request.POST.dict()
        # Add additional fields to the dictionary
        post_data["assigned_to_employee_id"] = asset_request.requested_employee_id
        post_data["assigned_by_employee_id"] = request.user.employee_get
        form = AssetAllocationForm(post_data, request.FILES)
        if form.is_valid():
            asset = form.instance.asset_id.id
            asset = Asset.objects.filter(id=asset).first()
            asset.asset_status = "In use"
            asset.save()
            form = form.save(commit=False)
            form.assigned_by_employee_id = request.user.employee_get
            form.save()
            asset_request.asset_request_status = "Approved"
            asset_request.save()
            messages.success(request, _("Asset request approved successfully!."))
            notify.send(
                request.user.employee_get,
                recipient=form.assigned_to_employee_id.employee_user_id,
                verb="Your asset request approved!.",
                verb_ar="تم الموافقة على طلب الأصول الخاص بك!",
                verb_de="Ihr Antragsantrag wurde genehmigt!",
                verb_es="¡Su solicitud de activo ha sido aprobada!",
                verb_fr="Votre demande d'actif a été approuvée !",
                redirect=reverse("asset-request-allocation-view")
                + f"?asset_request_date={asset_request.asset_request_date}\
                &asset_request_status={asset_request.asset_request_status}",
                icon="bag-check",
            )
            return HttpResponse("<script>window.location.reload()</script>")

        context["asset_allocation_form"] = form

    return render(request, "request_allocation/asset_approve.html", context)


@login_required
@manager_can_enter(perm="asset.add_asset")
def asset_request_reject(request, req_id):
    """
    View function to reject an asset request.
    Parameters:
    request (HttpRequest): the request object sent by the client
    req_id (int): the id of the AssetRequest object to reject

    Returns:
    HttpResponse: a redirect to the asset request list view with a success
        message if the asset request is rejected successfully, or a redirect to the
        asset request detail view with an error message if the asset request is not
        found or already rejected
    """
    asset_request = AssetRequest.objects.get(id=req_id)
    asset_request.asset_request_status = "Rejected"
    asset_request.save()
    messages.info(request, _("Asset request rejected"))
    notify.send(
        request.user.employee_get,
        recipient=asset_request.requested_employee_id.employee_user_id,
        verb="Your asset request rejected!.",
        verb_ar="تم رفض طلب الأصول الخاص بك!",
        verb_de="Ihr Antragsantrag wurde abgelehnt!",
        verb_es="¡Se ha rechazado su solicitud de activo!",
        verb_fr="Votre demande d'actif a été rejetée !",
        redirect=reverse("asset-request-allocation-view")
        + f"?asset_request_date={asset_request.asset_request_date}\
        &asset_request_status={asset_request.asset_request_status}",
        icon="bag-check",
    )
    return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))


@login_required
@permission_required(perm="asset.add_asset")
def asset_allocate_creation(request):
    """
    View function to create asset allocation.
    Returns:
    - to allocated view.
    """

    form = AssetAllocationForm(
        initial={"assigned_by_employee_id": request.user.employee_get}
    )
    context = {"asset_allocation_form": form}
    if request.method == "POST":
        form = AssetAllocationForm(request.POST)
        if form.is_valid():
            asset = form.instance.asset_id.id
            asset = Asset.objects.filter(id=asset).first()
            asset.asset_status = "In use"
            asset.save()
            instance = form.save()
            files = request.FILES.getlist("assign_images")
            attachments = []
            if request.FILES:
                for file in files:
                    attachment = ReturnImages()
                    attachment.image = file
                    attachment.save()
                    attachments.append(attachment)
                instance.assign_images.add(*attachments)
            messages.success(request, _("Asset allocated successfully!."))
            return HttpResponse("<script>window.location.reload()</script>")
        context["asset_allocation_form"] = form

    return render(request, "request_allocation/asset_allocation_creation.html", context)


def asset_allocate_return_request(request, asset_id):
    """
    Handle the initiation of a return request for an allocated asset.
    """
    asset_assign = AssetAssignment.objects.get(id=asset_id)
    asset_assign.return_request = True
    asset_assign.save()
    message = _("Return request for {} initiated.").format(asset_assign.asset_id)
    messages.info(request, message)
    return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))


@login_required
def asset_allocate_return(request, asset_id):
    """
    View function to return asset.
    Args:
    - asset_id: integer value representing the ID of the asset
    Returns:
    - message of the return
    """

    asset_return_form = AssetReturnForm()
    asset_allocation = AssetAssignment.objects.filter(
        asset_id=asset_id, return_status__isnull=True
    ).first()
    if request.method == "POST":
        asset_return_form = AssetReturnForm(request.POST, request.FILES)

        if asset_return_form.is_valid():
            asset = Asset.objects.filter(id=asset_id).first()
            asset_return_status = request.POST.get("return_status")
            asset_return_date = request.POST.get("return_date")
            asset_return_condition = request.POST.get("return_condition")
            files = request.FILES.getlist("return_images")
            attachments = []
            context = {"asset_return_form": asset_return_form, "asset_id": asset_id}
            response = render(request, "asset/asset_return_form.html", context)
            if asset_return_status == "Healthy":
                asset_allocation = AssetAssignment.objects.filter(
                    asset_id=asset_id, return_status__isnull=True
                ).first()
                asset_allocation.return_date = asset_return_date
                asset_allocation.return_status = asset_return_status
                asset_allocation.return_condition = asset_return_condition
                asset_allocation.return_request = False
                asset_allocation.save()
                if request.FILES:
                    for file in files:
                        attachment = ReturnImages()
                        attachment.image = file
                        attachment.save()
                        attachments.append(attachment)
                    asset_allocation.return_images.add(*attachments)
                asset.asset_status = "Available"
                asset.save()
                messages.info(request, _("Asset Return Successful !."))
                return HttpResponse(
                    response.content.decode("utf-8")
                    + "<script>location.reload();</script>"
                )
            asset.asset_status = "Not-Available"
            asset.save()
            asset_allocation = AssetAssignment.objects.filter(
                asset_id=asset_id, return_status__isnull=True
            ).first()
            asset_allocation.return_date = asset_return_date
            asset_allocation.return_status = asset_return_status
            asset_allocation.return_condition = asset_return_condition
            asset_allocation.save()
            if request.FILES:
                for file in files:
                    attachment = ReturnImages()
                    attachment.image = file
                    attachment.save()
                    attachments.append(attachment)
                asset_allocation.return_images.add(*attachments)
            messages.info(request, _("Asset Return Successful!."))
            return HttpResponse(
                response.content.decode("utf-8") + "<script>location.reload();</script>"
            )

    context = {"asset_return_form": asset_return_form, "asset_id": asset_id}
    context["asset_alocation"] = asset_allocation
    return render(request, "asset/asset_return_form.html", context)


def filter_pagination_asset_request_allocation(request):
    """
    Filter and paginate asset request and allocation data based on search criteria and sort options.

    This function handles the retrieval, filtering, and pagination of asset request and allocation
    data.It processes GET parameters to search, sort, and filter asset requests and allocations,
    and returns a context dictionary with the filtered data and associated forms for rendering in
    a template.
    """
    asset_request_allocation_search = request.GET.get("search")
    request_field = request.GET.get("request_field")
    allocation_field = request.GET.get("allocation_field")
    if asset_request_allocation_search is None:
        asset_request_allocation_search = ""
    employee = request.user.employee_get
    asset_assignment = AssetAssignment.objects.all()
    asset_request = filtersubordinates(
        request=request,
        perm="asset.view_assetrequest",
        queryset=AssetRequest.objects.all(),
        field="requested_employee_id",
    ) | AssetRequest.objects.filter(requested_employee_id=request.user.employee_get)
    asset_request = asset_request.distinct()
    if request.GET.get("assign_sortby"):
        asset_assignment = sortby(request, asset_assignment, "assign_sortby")
    if request.GET.get("request_sortby"):
        asset_request = sortby(request, asset_request, "request_sortby")

    assets = (
        asset_assignment.filter(assigned_to_employee_id=employee)
        .exclude(return_status__isnull=False)
        .filter(asset_id__asset_name__icontains=asset_request_allocation_search)
    )

    previous_data = request.GET.urlencode()
    assets_filtered = CustomAssetFilter(request.GET, queryset=assets)
    asset_request_filtered = AssetRequestFilter(request.GET, queryset=asset_request).qs
    if request_field != "" and request_field is not None:
        asset_request_filtered = group_by_queryset(
            asset_request_filtered, request_field, request.GET.get("page"), "page"
        )
        list_values = [entry["list"] for entry in asset_request_filtered]
        id_list = []
        for value in list_values:
            for instance in value.object_list:
                id_list.append(instance.id)

        requests_ids = json.dumps(list(id_list))

    else:
        asset_request_filtered = paginator_qry(
            asset_request_filtered, request.GET.get("page")
        )
        requests_ids = json.dumps(
            [instance.id for instance in asset_request_filtered.object_list]
        )

    asset_allocation_filtered = AssetAllocationFilter(
        request.GET, queryset=asset_assignment
    ).qs

    if allocation_field != "" and allocation_field is not None:
        asset_allocation_filtered = group_by_queryset(
            asset_allocation_filtered, allocation_field, request.GET.get("page"), "page"
        )
        list_values = [entry["list"] for entry in asset_allocation_filtered]
        id_list = []
        for value in list_values:
            for instance in value.object_list:
                id_list.append(instance.id)

        allocations_ids = json.dumps(list(id_list))

    else:
        asset_allocation_filtered = paginator_qry(
            asset_allocation_filtered, request.GET.get("page")
        )
        allocations_ids = json.dumps(
            [instance.id for instance in asset_allocation_filtered.object_list]
        )

    assets_ids = paginator_qry(assets, request.GET.get("page"))
    assets_id = json.dumps([instance.id for instance in assets_ids.object_list])
    asset_paginator = Paginator(assets_filtered.qs, get_pagination())
    page_number = request.GET.get("page")
    assets = asset_paginator.get_page(page_number)
    data_dict = parse_qs(previous_data)
    get_key_instances(AssetRequest, data_dict)
    get_key_instances(AssetAssignment, data_dict)
    get_key_instances(Asset, data_dict)
    return {
        "assets": assets,
        "asset_requests": asset_request_filtered,
        "asset_allocations": asset_allocation_filtered,
        "assets_filter_form": assets_filtered.form,
        "asset_request_filter_form": AssetRequestFilter().form,
        "asset_allocation_filter_form": AssetAllocationFilter().form,
        "pg": previous_data,
        "filter_dict": data_dict,
        "gp_request_fields": AssetRequestReGroup.fields,
        "gp_Allocation_fields": AssetAllocationReGroup.fields,
        "request_field": request_field,
        "allocation_field": allocation_field,
        "requests_ids": requests_ids,
        "allocations_ids": allocations_ids,
        "asset_ids": assets_id,
    }


@login_required
def asset_request_allocation_view(request):
    """
    This view is used to display a paginated list of asset allocation requests.
    Args:
        request (HttpRequest): The HTTP request object.
    Returns:
        HttpResponse: The HTTP response object with the rendered HTML template.
    """
    context = filter_pagination_asset_request_allocation(request)
    template = "request_allocation/asset_request_allocation_view.html"

    if (
        request.GET.get("request_field") != ""
        and request.GET.get("request_field") is not None
        or request.GET.get("allocation_field") != ""
        and request.GET.get("allocation_field") is not None
    ):
        template = "request_allocation/group_by.html"

    return render(request, template, context)


@login_required
def asset_request_alloaction_view_search_filter(request):
    """
    This view handles the search and filter functionality for the asset request allocation list.
    Args:
        request: HTTP request object.
    Returns:
        Rendered HTTP response with the filtered and paginated asset request allocation list.
    """
    context = filter_pagination_asset_request_allocation(request)
    template = "request_allocation/asset_request_allocation_list.html"
    if (
        request.GET.get("request_field") != ""
        and request.GET.get("request_field") is not None
        or request.GET.get("allocation_field") != ""
        and request.GET.get("allocation_field") is not None
    ):
        template = "request_allocation/group_by.html"

    return render(request, template, context)


@login_required
def own_asset_individual_view(request, asset_id):
    """
    This function is responsible for view the individual own asset

    Args:
        request : HTTP request object
        id (int): Id of the asset assignment
    """
    asset_assignment = AssetAssignment.objects.get(id=asset_id)
    asset = asset_assignment.asset_id
    context = {
        "asset": asset,
        "asset_assignment": asset_assignment,
    }
    requests_ids_json = request.GET.get("assets_ids")
    if requests_ids_json:
        requests_ids = json.loads(requests_ids_json)
        previous_id, next_id = closest_numbers(requests_ids, asset_id)
        context["assets_ids"] = requests_ids_json
        context["previous"] = previous_id
        context["next"] = next_id
    return render(request, "request_allocation/individual_own.html", context)


@login_required
def asset_request_individual_view(request, asset_request_id):
    """
    Display the details of an individual asset request.

    This view retrieves the asset request with the given ID and renders it in the
    'individual_request.html' template. If a JSON-encoded list of request IDs is
    provided in the GET parameters, the view also determines the previous and next
    request IDs for easy navigation.

    Args:
        request (HttpRequest): The HTTP request object containing metadata about the request.
        id (int): The ID of the asset request to be viewed.

    Returns:
        HttpResponse: The rendered 'individual_request.html' template with the context data.
    """
    asset_request = AssetRequest.objects.get(id=asset_request_id)
    context = {
        "asset_request": asset_request,
    }
    requests_ids_json = request.GET.get("requests_ids")
    if requests_ids_json:
        requests_ids = json.loads(requests_ids_json)
        previous_id, next_id = closest_numbers(requests_ids, asset_request_id)
        context["requests_ids"] = requests_ids_json
        context["previous"] = previous_id
        context["next"] = next_id
    return render(request, "request_allocation/individual_request.html", context)


@login_required
def asset_allocation_individual_view(request, asset_allocation_id):
    """
    Display the details of an individual asset allocation.

    This view retrieves the asset allocation with the given ID and renders it in the
    'individual_allocation.html' template. If a JSON-encoded list of allocation IDs is
    provided in the GET parameters, the view also determines the previous and next
    allocation IDs for easy navigation.

    Args:
        request (HttpRequest): The HTTP request object containing metadata about the request.
        id (int): The ID of the asset allocation to be viewed.

    Returns:
        HttpResponse: The rendered 'individual_allocation.html' template with the context data.
    """
    asset_allocation = AssetAssignment.objects.get(id=asset_allocation_id)
    context = {"asset_allocation": asset_allocation}
    allocation_ids_json = request.GET.get("allocations_ids")
    if allocation_ids_json:
        allocation_ids = json.loads(allocation_ids_json)
        previous_id, next_id = closest_numbers(allocation_ids, asset_allocation_id)
        context["allocations_ids"] = allocation_ids_json
        context["previous"] = previous_id
        context["next"] = next_id
    return render(request, "request_allocation/individual allocation.html", context)


def convert_nan(val):
    """
    Convert NaN values to None.
    """
    if pd.isna(val):
        return None
    return val


@login_required
@permission_required(perm="asset.add_asset")
def asset_import(request):
    """
    Handle the import of asset data from an uploaded Excel file.

    This view processes a POST request containing an Excel file, reads the data,
    creates Asset objects from the data, and saves them to the database. If the
    import is successful, a success message is displayed. Otherwise, appropriate
    error messages are shown.

    Args:
        request (HttpRequest): The HTTP request object containing metadata about the request.

    Returns:
        HttpResponseRedirect: A redirect to the asset category view after processing the import.
    """

    try:
        if request.method == "POST":
            file = request.FILES.get("asset_import")

            if file is not None:
                try:
                    dataframe = pd.read_excel(file)
                except KeyError as exception:
                    messages.error(request, f"{exception}")
                    return redirect(asset_category_view)

                # Create Asset objects from the DataFrame and save them to the database
                for index, row in dataframe.iterrows():
                    asset_name = convert_nan(row["Asset name"])
                    asset_description = convert_nan(row["Description"])
                    asset_tracking_id = convert_nan(row["Tracking id"])
                    purchase_date = convert_nan(row["Purchase date"])
                    purchase_cost = convert_nan(row["Purchase cost"])
                    category_name = convert_nan(row["Category"])
                    lot_number = convert_nan(row["Batch number"])
                    status = convert_nan(row["Status"])

                    asset_category, create = AssetCategory.objects.get_or_create(
                        asset_category_name=category_name
                    )
                    asset_lot_number, create = AssetLot.objects.get_or_create(
                        lot_number=lot_number
                    )
                    Asset.objects.create(
                        asset_name=asset_name,
                        asset_description=asset_description,
                        asset_tracking_id=asset_tracking_id,
                        asset_purchase_date=purchase_date,
                        asset_purchase_cost=purchase_cost,
                        asset_category_id=asset_category,
                        asset_status=status,
                        asset_lot_number_id=asset_lot_number,
                    )

                messages.success(request, _("Successfully imported Assets"))
                return redirect(asset_category_view)
            messages.error(request, _("File Error"))
            return redirect(asset_category_view)
    except Exception as exception:
        messages.error(request, f"{exception}")
        return redirect(asset_category_view)


@login_required
def asset_excel(_request):
    """asset excel download view"""

    try:
        columns = [
            "Asset name",
            "Description",
            "Tracking id",
            "Purchase date",
            "Purchase cost",
            "Category",
            "Status",
            "Batch number",
        ]
        # Create a pandas DataFrame with columns but no data
        dataframe = pd.DataFrame(columns=columns)
        # Write the DataFrame to an Excel file
        response = HttpResponse(content_type="application/ms-excel")
        response["Content-Disposition"] = 'attachment; filename="my_excel_file.xlsx"'
        dataframe.to_excel(response, index=False)
        return response
    except Exception as exception:
        return HttpResponse(exception)


@login_required
@permission_required(perm="asset.add_asset")
def asset_export_excel(request):
    """asset export view"""
    asset_export_filter = AssetExportFilter(request.GET, queryset=Asset.objects.all())
    if request.method == "POST":
        queryset_all = Asset.objects.all()
        if not queryset_all:
            messages.warning(request, _("There are no assets to export."))
            return redirect("asset-category-view")  # or some other URL

        queryset = AssetExportFilter(request.POST, queryset=queryset_all).qs

        # Convert the queryset to a Pandas DataFrame
        data = {
            "asset_name": [],
            "asset_description": [],
            "asset_tracking_id": [],
            "asset_purchase_date": [],
            "asset_purchase_cost": [],
            "asset_category_id": [],
            "asset_status": [],
            "asset_lot_number_id": [],
        }

        fields_to_check = [
            "asset_name",
            "asset_description",
            "asset_tracking_id",
            "asset_purchase_date",
            "asset_purchase_cost",
            "asset_category_id",
            "asset_status",
            "asset_lot_number_id",
        ]

        for asset in queryset:
            for field in fields_to_check:
                # Get the value of the field for the current asset
                value = getattr(asset, field)

                if isinstance(value, date):
                    user = request.user
                    emp = user.employee_get

                    # Taking the company_name of the user
                    info = EmployeeWorkInformation.objects.filter(employee_id=emp)
                    if info.exists():
                        for i in info:
                            employee_company = i.company_id
                        company_name = Company.objects.filter(company=employee_company)
                        emp_company = company_name.first()

                        # Access the date_format attribute directly
                        date_format = (
                            emp_company.date_format if emp_company else "MMM. D, YYYY"
                        )
                    else:
                        date_format = "MMM. D, YYYY"
                    # Define date formats
                    date_formats = {
                        "DD-MM-YYYY": "%d-%m-%Y",
                        "DD.MM.YYYY": "%d.%m.%Y",
                        "DD/MM/YYYY": "%d/%m/%Y",
                        "MM/DD/YYYY": "%m/%d/%Y",
                        "YYYY-MM-DD": "%Y-%m-%d",
                        "YYYY/MM/DD": "%Y/%m/%d",
                        "MMMM D, YYYY": "%B %d, %Y",
                        "DD MMMM, YYYY": "%d %B, %Y",
                        "MMM. D, YYYY": "%b. %d, %Y",
                        "D MMM. YYYY": "%d %b. %Y",
                        "dddd, MMMM D, YYYY": "%A, %B %d, %Y",
                    }

                    # Convert the string to a datetime.date object
                    start_date = datetime.strptime(str(value), "%Y-%m-%d").date()

                    # Print the formatted date for each format
                    for format_name, format_string in date_formats.items():
                        if format_name == date_format:
                            value = start_date.strftime(format_string)

                # Append the value if it exists, or append None if it's None
                data[field].append(value if value is not None else None)

        # Fill any missing values with None
        for key in data:
            data[key] = data[key] + [None] * (len(queryset) - len(data[key]))

        # Convert the data dictionary to a Pandas DataFrame
        dataframe = pd.DataFrame(data)

        # Convert any date fields to the desired format
        # Rename the columns as needed
        dataframe = dataframe.rename(
            columns={
                "asset_name": "Asset name",
                "asset_description": "Description",
                "asset_tracking_id": "Tracking id",
                "asset_purchase_date": "Purchase date",
                "asset_purchase_cost": "Purchase cost",
                "asset_category_id": "Category",
                "asset_status": "Status",
                "asset_lot_number_id": "Batch number",
            }
        )

        # Write the DataFrame to an Excel file
        response = HttpResponse(content_type="application/vnd.ms-excel")
        response["Content-Disposition"] = 'attachment; filename="assets.xlsx"'
        dataframe.to_excel(response, index=False)
        return response
    context = {"asset_export_filter": asset_export_filter}
    return render(request, "category/asset_filter_export.html", context)


@login_required
def asset_batch_number_creation(request):
    """asset batch number creation view"""
    hx_vals = (
        request.GET.get("data") if request.GET.get("data") else request.GET.urlencode()
    )
    asset_batch_form = AssetBatchForm()
    context = {
        "asset_batch_form": asset_batch_form,
        "hx_vals": hx_vals,
        "hx_get": None,
        "hx_target": None,
    }
    if request.method == "POST":
        asset_batch_form = AssetBatchForm(request.POST)
        if asset_batch_form.is_valid():
            asset_batch_form.save()
            asset_batch_form = AssetBatchForm()
            messages.success(request, _("Batch number created successfully."))
            if AssetLot.objects.filter().count() == 1 and not hx_vals:
                return HttpResponse("<script>location.reload();</script>")
            if hx_vals:
                category_id = request.GET.get("asset_category_id")
                url = reverse("asset-creation", args=[category_id])
                instance = AssetLot.objects.all().order_by("-id").first()
                mutable_get = request.GET.copy()
                mutable_get["asset_lot_number_id"] = str(instance.id)
                context["hx_get"] = f"{url}?{mutable_get.urlencode()}"
                context["hx_target"] = "#objectCreateModalTarget"
        context["asset_batch_form"] = asset_batch_form
    return render(request, "batch/asset_batch_number_creation.html", context)


@login_required
@permission_required(perm="asset.view_assetlot")
def asset_batch_view(request):
    """
    View function to display details of all batch numbers.

    Returns:
    -  all asset batch numbers based on page
    """

    asset_batches = AssetLot.objects.all()
    previous_data = request.GET.urlencode()
    asset_batch_numbers_search_paginator = Paginator(asset_batches, 20)
    page_number = request.GET.get("page")
    asset_batch_numbers = asset_batch_numbers_search_paginator.get_page(page_number)
    asset_batch_form = AssetBatchForm()
    if asset_batches.exists():
        template = "batch/asset_batch_number_view.html"
    else:
        template = "batch/asset_batch_empty.html"
    context = {
        "batch_numbers": asset_batch_numbers,
        "asset_batch_form": asset_batch_form,
        "pg": previous_data,
    }
    return render(request, template, context)


@login_required
@permission_required(perm="asset.change_assetlot")
def asset_batch_update(request, batch_id):
    """
    View function to return asset.
    Args:
    - batch_id: integer value representing the ID of the asset
    Returns:
    - message of the return
    """
    asset_batch_number = AssetLot.objects.get(id=batch_id)
    asset_batch = AssetLot.objects.get(id=batch_id)
    asset_batch_form = AssetBatchForm(instance=asset_batch)
    context = {
        "asset_batch_update_form": asset_batch_form,
    }
    assigned_batch_number = Asset.objects.filter(asset_lot_number_id=asset_batch_number)
    if assigned_batch_number:
        asset_batch_form = AssetBatchForm(instance=asset_batch)
        asset_batch_form["lot_number"].field.widget.attrs.update(
            {"readonly": "readonly"}
        )
        context["asset_batch_update_form"] = asset_batch_form
        context["in_use_message"] = _("This batch number is already in-use")
    if request.method == "POST":
        asset_batch_form = AssetBatchForm(request.POST, instance=asset_batch_number)
        if asset_batch_form.is_valid():
            asset_batch_form.save()
            messages.info(request, _("Batch updated successfully."))
            response = render(request, "batch/asset_batch_number_update.html", context)
            return HttpResponse(
                response.content.decode("utf-8") + "<script>location.reload();</script>"
            )
        context["asset_batch_update_form"] = asset_batch_form
    return render(request, "batch/asset_batch_number_update.html", context)


@login_required
@permission_required(perm="asset.delete_assetlot")
def asset_batch_number_delete(request, batch_id):
    """
    View function to return asset.
    Args:
    - batch_id: integer value representing the ID of the asset
    Returns:
    - message of the return
    """
    previous_data = request.GET.urlencode()
    try:
        asset_batch_number = AssetLot.objects.get(id=batch_id)
        assigned_batch_number = Asset.objects.filter(
            asset_lot_number_id=asset_batch_number
        )
        if assigned_batch_number:
            messages.error(request, _("Batch number in-use"))
            return redirect(f"/asset/asset-batch-number-search?{previous_data}")
        asset_batch_number.delete()
        messages.success(request, _("Batch number deleted"))
    except AssetLot.DoesNotExist:
        messages.error(request, _("Batch number not found"))
    except ProtectedError:
        messages.error(request, _("You cannot delete this Batch number."))
    if not AssetLot.objects.filter():
        return HttpResponse("<script>location.reload();</script>")
    return redirect(f"/asset/asset-batch-number-search?{previous_data}")


@login_required
@hx_request_required
def asset_batch_number_search(request):
    """
    View function to return search  data of asset batch number.

    Args:
    - id: integer value representing the ID of the asset

    Returns:
    - message of the return
    """
    search_query = request.GET.get("search")
    if search_query is None:
        search_query = ""

    asset_batches = AssetLot.objects.all().filter(lot_number__icontains=search_query)
    previous_data = request.GET.urlencode()
    asset_batch_numbers_search_paginator = Paginator(asset_batches, 20)
    page_number = request.GET.get("page")
    asset_batch_numbers = asset_batch_numbers_search_paginator.get_page(page_number)

    context = {
        "batch_numbers": asset_batch_numbers,
        "pg": previous_data,
    }

    return render(request, "batch/asset_batch_number_list.html", context)


@login_required
def asset_count_update(request):
    """
    View function to return update asset count at asset category.
    Args:
    - id: integer value representing the ID of the asset category
    Returns:
    - count of asset inside the category
    """
    if request.method == "POST":
        category_id = request.POST.get("asset_category_id")
        if category_id is not None:
            category = AssetCategory.objects.get(id=category_id)
            asset_count = category.asset_set.count()
            return HttpResponse(asset_count)
    return HttpResponse("error")


@login_required
@permission_required(perm="asset.view_assetcategory")
def asset_dashboard(request):
    """
    This method is used to render the dashboard of the asset module.
    """
    assets = Asset.objects.all()
    asset_in_use = Asset.objects.filter(asset_status="In use")
    asset_requests = AssetRequest.objects.filter(
        asset_request_status="Requested", requested_employee_id__is_active=True
    )
    requests_ids = json.dumps([instance.id for instance in asset_requests])
    asset_allocations = AssetAssignment.objects.filter(
        asset_id__asset_status="In use", assigned_to_employee_id__is_active=True
    )
    context = {
        "assets": assets,
        "asset_requests": asset_requests,
        "requests_ids": requests_ids,
        "asset_in_use": asset_in_use,
        "asset_allocations": asset_allocations,
    }
    return render(request, "asset/dashboard.html", context)


@login_required
@permission_required(perm="asset.view_assetcategory")
def asset_available_chart(request):
    """
    This function returns the response for the available asset chart in the asset dashboard.
    """
    asset_available = Asset.objects.filter(asset_status="Available")
    asset_unavailable = Asset.objects.filter(asset_status="Not-Available")
    asset_in_use = Asset.objects.filter(asset_status="In use")

    labels = ["In use", "Available", "Not-Available"]
    dataset = [
        {
            "label": _("asset"),
            "data": [len(asset_in_use), len(asset_available), len(asset_unavailable)],
        },
    ]

    response = {
        "labels": labels,
        "dataset": dataset,
        "message": _("Oops!! No Asset found..."),
        "emptyImageSrc": "/static/images/ui/asset.png",
    }
    return JsonResponse(response)


@login_required
@permission_required(perm="asset.view_assetcategory")
def asset_category_chart(request):
    """
    This function returns the response for the asset category chart in the asset dashboard.
    """
    asset_categories = AssetCategory.objects.all()
    data = []
    for asset_category in asset_categories:
        category_count = 0
        category_count = len(asset_category.asset_set.filter(asset_status="In use"))
        data.append(category_count)

    labels = [category.asset_category_name for category in asset_categories]
    dataset = [
        {
            "label": _("assets in use"),
            "data": data,
        },
    ]

    response = {
        "labels": labels,
        "dataset": dataset,
        "message": _("Oops!! No Asset found..."),
        "emptyImageSrc": "/static/images/ui/asset.png",
    }
    return JsonResponse(response)


@login_required
@permission_required(perm="asset.view_assetassignment")
def asset_history(request):
    """
    This function is responsible for loading the asset history view

    Args:


    Returns:
        returns asset history view template
    """
    previous_data = request.GET.urlencode() + "&returned_assets=True"
    asset_assignments = AssetHistoryFilter({"returned_assets": "True"}).qs.order_by(
        "-id"
    )
    data_dict = parse_qs(previous_data)
    get_key_instances(AssetAssignment, data_dict)
    asset_assignments = paginator_qry(asset_assignments, request.GET.get("page"))
    requests_ids = json.dumps(
        [instance.id for instance in asset_assignments.object_list]
    )
    context = {
        "asset_assignments": asset_assignments,
        "f": AssetHistoryFilter(),
        "filter_dict": data_dict,
        "gp_fields": AssetHistoryReGroup().fields,
        "pd": previous_data,
        "requests_ids": requests_ids,
    }
    return render(request, "asset_history/asset_history_view.html", context)


@login_required
@permission_required(perm="asset.view_assetassignment")
def asset_history_single_view(request, asset_id):
    """
    this method is used to view details of individual asset assignments

    Args:
        request (HTTPrequest): http request
        asset_id (int): ID of the asset assignment

    Returns:
        html: Returns asset history single view template
    """
    asset_assignment = get_object_or_404(AssetAssignment, id=asset_id)
    context = {"asset_assignment": asset_assignment}
    requests_ids_json = request.GET.get("requests_ids")
    if requests_ids_json:
        requests_ids = json.loads(requests_ids_json)
        previous_id, next_id = closest_numbers(requests_ids, asset_id)
        context["requests_ids"] = requests_ids_json
        context["previous"] = previous_id
        context["next"] = next_id
    return render(
        request,
        "asset_history/asset_history_single_view.html",
        context,
    )


@login_required
@permission_required(perm="asset.view_assetassignment")
def asset_history_search(request):
    """
    This method is used to filter the asset history view or to group by the datas.

    Args:
        request (HTTPrequest):http request

    Returns:
        returns asset history list or group by
    """
    previous_data = request.GET.urlencode()
    asset_assignments = AssetHistoryFilter(request.GET).qs.order_by("-id")
    asset_assignments = sortby(request, asset_assignments, "sortby")
    template = "asset_history/asset_history_list.html"
    field = request.GET.get("field")
    if field != "" and field is not None:
        asset_assignments = group_by_queryset(
            asset_assignments, field, request.GET.get("page"), "page"
        )
        template = "asset_history/group_by.html"
        list_values = [entry["list"] for entry in asset_assignments]
        id_list = []
        for value in list_values:
            for instance in value.object_list:
                id_list.append(instance.id)

        requests_ids = json.dumps(list(id_list))
    else:
        asset_assignments = paginator_qry(asset_assignments, request.GET.get("page"))

        requests_ids = json.dumps(
            [instance.id for instance in asset_assignments.object_list]
        )
    data_dict = parse_qs(previous_data)
    get_key_instances(AssetAssignment, data_dict)

    return render(
        request,
        template,
        {
            "asset_assignments": asset_assignments,
            "filter_dict": data_dict,
            "field": field,
            "pd": previous_data,
            "requests_ids": requests_ids,
        },
    )
