""""
asset.py

This module is used to """
import json
from django.db.models import Q
from urllib.parse import parse_qs
import pandas as pd
from django.db.models import ProtectedError
from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpResponseRedirect
from django.contrib import messages
from django.core.paginator import Paginator
from django.utils.translation import gettext_lazy as _
from base.methods import closest_numbers, get_key_instances
from notifications.signals import notify
from horilla.decorators import login_required, hx_request_required
from horilla.decorators import permission_required
from asset.models import Asset, AssetRequest, AssetAssignment, AssetCategory, AssetLot
from asset.forms import (
    AssetBatchForm,
    AssetForm,
    AssetRequestForm,
    AssetAllocationForm,
    AssetCategoryForm,
    AssetReturnForm,
)
from asset.filters import (
    AssetAllocationFilter,
    AssetAllocationReGroup,
    AssetRequestFilter,
    AssetRequestReGroup,
    CustomAssetFilter,
    AssetCategoryFilter,
    AssetExportFilter,
    AssetFilter,
)

def asset_del(request, asset):
    try:
        asset.delete()
        messages.success(request, _("Asset deleted successfully"))
    except ProtectedError:
        messages.error(request, _("You cannot delete this asset."))
    return

@login_required
@hx_request_required
@permission_required("asset.add_asset")
def asset_creation(request, id):
    """
    View function for creating a new asset object.
    Args:
        request (HttpRequest): A Django HttpRequest object that contains information
        about the current request.
        id (int): An integer representing the ID of the asset category for which
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
    initial_data = {"asset_category_id": id}
    form = AssetForm(initial=initial_data)
    context = {"asset_creation_form": form}
    if request.method == "POST":
        form = AssetForm(request.POST, initial=initial_data)
        if form.is_valid():
            form.save()
            messages.success(request, _("Asset created successfully"))
            return redirect("asset-creation", id=id)
        else:
            context["asset_creation_form"] = form
    return render(request, "asset/asset_creation.html", context)


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
    context = {
        "asset_form": asset_form,
        "asset_under": asset_under,
        "pg": previous_data,
    }
    if request.method == "POST":
        asset_form = AssetForm(request.POST, instance=instance)
        if asset_form.is_valid():
            asset_form.save()
            messages.success(request, _("Asset Updated"))
        context["asset_form"] = asset_form
    return render(request, "asset/asset_update.html", context)


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
    status = asset.asset_status
    asset_list_filter = request.GET.get("asset_list")
    asset_allocation = AssetAssignment.objects.filter(asset_id=asset).first()
    if asset_list_filter:
        # if the asset deleted is from the filterd list of asset
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
            return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))

        elif asset_allocation:
            # if this asset is used in any allocation
            messages.error(request, _("Asset is used in allocation!."))
            return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))
        
        asset_del(request, asset)

        return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))

    else:
        # if the asset is deleted under the category
        if status == "In use":
            # if asset under the category
            messages.info(request, _("Asset is in use"))
            return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))

        elif asset_allocation:
            # if this asset is used in any allocation
            messages.error(request, _("Asset is used in allocation!."))
            return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))
        
        asset_del(request, asset)

        return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))


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
    context = {}
    if asset_list_filter:
        # if the data is present means that it is for asset filtered list
        query = request.GET.get("query")
        asset_under = "asset_filter"
        if query:
            assets_in_category = Asset.objects.filter(asset_name__icontains=query)
        else:
            assets_in_category = Asset.objects.all()
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
    data_dict = parse_qs(previous_data)
    get_key_instances(Asset, data_dict)
    context = {
        "assets": page_obj,
        "pg": previous_data,
        "asset_category_id": cat_id,
        "asset_under": asset_under,
        "asset_count": len(assets_in_category) or None,
        "filter_dict": data_dict,
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
            return HttpResponse("<script>location.reload();</script>")
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


@permission_required(perm="asset.delete_assetcategory")
def asset_category_delete(request, cat_id):
    """
    Deletes an asset category and redirects to the asset category view.
    Args:
        request (HttpRequest): The HTTP request object.
        id (int): The ID of the asset category to be deleted.
    Returns:
        HttpResponseRedirect: A redirect to the asset category view.
    Raises:
        None.
    """
    try:
        asset_category = AssetCategory.objects.get(id=cat_id)
    except AssetCategory.DoesNotExist:
        messages.error(request, _("Asset not found"))
        return redirect(asset_category_view_search_filter)
    asset_status = Asset.objects.filter(asset_category_id=asset_category).filter(
        asset_status="In use"
    )

    if asset_status:
        messages.info(
            request,
            _("There are assets in use in the %(asset_category)s category.")
            % {"asset_category": asset_category},
        )
        return redirect(asset_category_view_search_filter)
    try:
        asset_category.delete()
        messages.success(request, _("Asset Category Deleted"))
    except ProtectedError:
        messages.error(request, _("You cannot delete this asset category."))
    return redirect(asset_category_view_search_filter)


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
    asset_export_filter = AssetExportFilter(request.GET, queryset=Asset.objects.all())
    asset_category_paginator = Paginator(asset_category_filtered.qs, 20)
    page_number = request.GET.get("page")
    asset_categorys = asset_category_paginator.get_page(page_number)
    data_dict = parse_qs(previous_data)
    get_key_instances(AssetCategory, data_dict)
    asset_creation_form = AssetForm()
    asset_category_form = AssetCategoryForm()
    asset_filter_form = AssetFilter()
    return {
        "asset_creation_form": asset_creation_form,
        "asset_category_form": asset_category_form,
        "asset_export_filter": asset_export_filter,
        "asset_categorys": asset_categorys,
        "asset_category_filter_form": asset_category_filtered.form,
        "asset_filter_form": asset_filter_form.form,
        "pg": previous_data,
        "filter_dict": data_dict,
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
@permission_required(perm="asset.add_asset")
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
        form = AssetAllocationForm(post_data)
        if form.is_valid():
            asset = form.instance.asset_id.id
            asset = Asset.objects.filter(id=asset).first()
            asset.asset_status = "In use"
            asset.save()
            form = form.save()
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
                redirect="/asset/asset-request-allocation-view",
                icon="bag-check",
            )
            response = render(
                request,
                "request_allocation/asset_approve.html",
                {"asset_allocation_form": form, "id": req_id},
            )
            return HttpResponse(
                response.content.decode("utf-8") + "<script>location.reload();</script>"
            )
        context["asset_allocation_form"] = form

    return render(request, "request_allocation/asset_approve.html", context)


@login_required
@permission_required(perm="asset.add_asset")
def asset_request_reject(request, req_id):
    """
    View function to reject an asset request.
    Parameters:
    request (HttpRequest): the request object sent by the client
    req_id (int): the id of the AssetRequest object to reject

    Returns:
    HttpResponse: a redirect to the asset request list view with a success m
        essage if the asset request is rejected successfully, or a redirect to the
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
        redirect="/asset/asset-request-allocation-view",
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

    form = AssetAllocationForm()
    context = {"asset_allocation_form": form}
    if request.method == "POST":
        form = AssetAllocationForm(request.POST)
        if form.is_valid():
            asset = form.instance.asset_id.id
            asset = Asset.objects.filter(id=asset).first()
            asset.asset_status = "In use"
            asset.save()
            form.save()
            messages.success(request, _("Asset allocated successfully!."))
            return HttpResponse("<script>window.location.reload()</script>")
        context["asset_allocation_form"] = form

    return render(request, "request_allocation/asset_allocation_creation.html", context)


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
    if request.method == "POST":
        asset_return_form = AssetReturnForm(request.POST)

        if asset_return_form.is_valid():
            asset = Asset.objects.filter(id=asset_id).first()
            asset_return_status = request.POST.get("return_status")
            asset_return_date = request.POST.get("return_date")
            asset_return_condition = request.POST.get("return_condition")
            context = {"asset_return_form":asset_return_form,"asset_id":asset_id}
            response = render(
                request, "asset/asset_return_form.html", context
            )
            if asset_return_status == "Healthy":
                asset_allocation = AssetAssignment.objects.filter(
                    asset_id=asset_id, return_status__isnull=True
                ).first()
                asset_allocation.return_date = asset_return_date
                asset_allocation.return_status = asset_return_status
                asset_allocation.return_condition = asset_return_condition
                asset_allocation.save()
                asset.asset_status = "Available"
                asset.save()
                messages.info(request, _("Asset Return Successful !."))
                return HttpResponse(
                response.content.decode("utf-8") + "<script>location.reload();</script>"
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
            messages.info(request, _("Asset Return Successful!."))
            return HttpResponse(
                response.content.decode("utf-8") + "<script>location.reload();</script>"
            )
    context = {"asset_return_form":asset_return_form,"asset_id":asset_id}
    return render(request, "asset/asset_return_form.html",context )


def filter_pagination_asset_request_allocation(request):
    asset_request_alloaction_search = request.GET.get("search")
    request_field = request.GET.get("request_field")
    allocation_field = request.GET.get("allocation_field")
    if asset_request_alloaction_search is None:
        asset_request_alloaction_search = ""
    employee = request.user.employee_get

    assets = (
        AssetAssignment.objects.filter(assigned_to_employee_id=employee)
        .exclude(return_status__isnull=False)
        .filter(asset_id__asset_name__icontains=asset_request_alloaction_search)
    )
    
    search_term = asset_request_alloaction_search.strip()

    if request.user.has_perm(("asset.view_assetrequest", "asset.view_assetassignment")):
        asset_allocations_queryset = AssetAssignment.objects.all().filter(
            Q(assigned_to_employee_id__employee_first_name__icontains=search_term) |
            Q(assigned_to_employee_id__employee_last_name__icontains=search_term) |
            (Q(assigned_to_employee_id__employee_first_name__icontains=search_term.split()[0]) if search_term.split() else Q()) |
            (Q(assigned_to_employee_id__employee_last_name__icontains=search_term.split()[-1]) if len(search_term.split()) > 1 else Q())
        )
        asset_requests_queryset = AssetRequest.objects.all().filter(
            Q(requested_employee_id__employee_first_name__icontains=search_term) |
            Q(requested_employee_id__employee_last_name__icontains=search_term) |
            (Q(requested_employee_id__employee_first_name__icontains=search_term.split()[0]) if search_term.split() else Q()) |
            (Q(requested_employee_id__employee_last_name__icontains=search_term.split()[-1]) if len(search_term.split()) > 1 else Q())
        )
    else:
        asset_allocations_queryset = AssetAssignment.objects.filter(
            assigned_to_employee_id=employee
        ).filter(
            Q(assigned_to_employee_id__employee_first_name__icontains=search_term) |
            Q(assigned_to_employee_id__employee_last_name__icontains=search_term) |
            (Q(assigned_to_employee_id__employee_first_name__icontains=search_term.split()[0]) if search_term.split() else Q()) |
            (Q(assigned_to_employee_id__employee_last_name__icontains=search_term.split()[-1]) if len(search_term.split()) > 1 else Q())
        )
        asset_requests_queryset = AssetRequest.objects.filter(
            requested_employee_id=employee
        ).filter(
            Q(requested_employee_id__employee_first_name__icontains=search_term) |
            Q(requested_employee_id__employee_last_name__icontains=search_term) |
            (Q(requested_employee_id__employee_first_name__icontains=search_term.split()[0]) if search_term.split() else Q()) |
            (Q(requested_employee_id__employee_last_name__icontains=search_term.split()[-1]) if len(search_term.split()) > 1 else Q())
        )

    previous_data = request.GET.urlencode()
    assets_filtered = CustomAssetFilter(request.GET, queryset=assets)
    asset_request_filtered = AssetRequestFilter(
        request.GET, queryset=asset_requests_queryset
    ).qs
    if request_field != "" and request_field is not None:
        request_field_copy = request_field.replace(".", "__")
        asset_request_filtered = asset_request_filtered.order_by(request_field_copy)

    asset_allocation_filtered = AssetAllocationFilter(
        request.GET, queryset=asset_allocations_queryset
    ).qs

    if allocation_field != "" and allocation_field is not None:
        allocation_field_copy = allocation_field.replace(".", "__")
        asset_allocation_filtered = asset_allocation_filtered.order_by(allocation_field_copy)

    asset_paginator = Paginator(assets_filtered.qs, 20)
    asset_request_paginator = Paginator(asset_request_filtered, 20)
    asset_allocation_paginator = Paginator(asset_allocation_filtered, 20)
    page_number = request.GET.get("page")
    assets = asset_paginator.get_page(page_number)
    asset_requests = asset_request_paginator.get_page(page_number)
    asset_allocations = asset_allocation_paginator.get_page(page_number)
    requests_ids = json.dumps(
        [
            instance.id
            for instance in asset_requests.object_list
        ]
    )
    allocations_ids = json.dumps(
        [
            instance.id
            for instance in asset_allocations.object_list
        ]
    )

    data_dict = parse_qs(previous_data)
    get_key_instances(AssetRequest, data_dict)
    get_key_instances(AssetAssignment, data_dict)
    get_key_instances(Asset, data_dict)
    return {
        "assets": assets,
        "asset_requests": asset_requests,
        "asset_allocations": asset_allocations,
        "assets_filter_form": assets_filtered.form,
        "asset_request_filter_form": AssetRequestFilter(request.GET, queryset=asset_requests_queryset).form,
        "asset_allocation_filter_form": AssetAllocationFilter(request.GET, queryset=asset_allocations_queryset).form,
        "pg": previous_data,
        "filter_dict":data_dict,
        "gp_request_fields": AssetRequestReGroup.fields,
        "gp_Allocation_fields": AssetAllocationReGroup.fields,
        "request_field":request_field,
        "allocation_field":allocation_field,
        "requests_ids":requests_ids,
        "allocations_ids":allocations_ids
    }


@login_required
def asset_request_alloaction_view(request):
    """
    This view is used to display a paginated list of asset allocation requests.
    Args:
        request (HttpRequest): The HTTP request object.
    Returns:
        HttpResponse: The HTTP response object with the rendered HTML template.
    """
    context = filter_pagination_asset_request_allocation(request)
    template = "request_allocation/asset_request_allocation_view.html"

    if request.GET.get("request_field") != "" and request.GET.get("request_field") is not None or request.GET.get("allocation_field") != "" and request.GET.get("allocation_field") is not None:
        template = "request_allocation/group_by.html"

    return render(
        request, template , context
    )


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
    if request.GET.get("request_field") != "" and request.GET.get("request_field") is not None or request.GET.get("allocation_field") != "" and request.GET.get("allocation_field") is not None:
        template = "request_allocation/group_by.html"

    return render(
        request, template, context
    )

def asset_request_individual_view(request,id):
    asset_request = AssetRequest.objects.get(id=id)
    context = {"asset_request":asset_request}
    requests_ids_json = request.GET.get("requests_ids")
    if requests_ids_json:
        requests_ids = json.loads(requests_ids_json)
        previous_id, next_id = closest_numbers(requests_ids, id)
        context["requests_ids"] = requests_ids_json
        context["previous"] = previous_id
        context["next"] = next_id
    return render(
        request,
        "request_allocation/individual_request.html",
        context
    )


def asset_allocation_individual_view(request,id):
    asset_allocation = AssetAssignment.objects.get(id=id)
    context = {"asset_allocation":asset_allocation}
    allocation_ids_json = request.GET.get("allocations_ids")
    if allocation_ids_json:
        allocation_ids = json.loads(allocation_ids_json)
        previous_id, next_id = closest_numbers(allocation_ids, id)
        context["allocations_ids"] = allocation_ids_json
        context["previous"] = previous_id
        context["next"] = next_id
    return render(
        request,
        "request_allocation/individual allocation.html",
        context
    )


def convert_nan(val):
    if pd.isna(val):
        return None
    return val


@login_required
@permission_required(perm="asset.add_asset")
def asset_import(request):
    """asset import view"""

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
                    lot_number = convert_nan(row["lot number"])
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
            "lot number",
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


@login_required
def asset_batch_number_creation(request):
    """asset batch number creation view"""
    asset_batch_form = AssetBatchForm()
    context = {
        "asset_batch_form": asset_batch_form,
    }
    if request.method == "POST":
        asset_batch_form = AssetBatchForm(request.POST)
        if asset_batch_form.is_valid():
            asset_batch_form.save()
            messages.success(request, _("Batch number created successfully."))
            response = render(
                request, "batch/asset_batch_number_creation.html", context
            )
            return HttpResponse(
                response.content.decode("utf-8") + "<script>location.reload();</script>"
            )
        context = {
            "asset_batch_form": asset_batch_form,
        }
        return render(request, "batch/asset_batch_number_creation.html", context)
    return render(request, "batch/asset_batch_number_creation.html", context)


@login_required
@permission_required(perm="asset.add_assetlot")
def asset_batch_view(request):
    """
    View function to display details of all batch numbers.

    Returns:
    -  all asset batch numbers based on page
    """

    asset_batchs = AssetLot.objects.all()
    previous_data = request.GET.urlencode()
    asset_batch_numbers_search_paginator = Paginator(asset_batchs, 20)
    page_number = request.GET.get("page")
    asset_batch_numbers = asset_batch_numbers_search_paginator.get_page(page_number)
    asset_batch_form = AssetBatchForm()
    if asset_batchs.exists():
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
    try:
        asset_batch_number = AssetLot.objects.get(id=batch_id)
    except AssetLot.DoesNotExist:
        messages.error(request, _("Batch number not found"))
        return redirect(asset_batch_view)
    assigned_batch_number = Asset.objects.filter(asset_lot_number_id=asset_batch_number)
    if assigned_batch_number:
        messages.error(request, _("Batch number in-use"))
        return redirect(asset_batch_view)
    try:
        asset_batch_number.delete()
        messages.success(request, _("Batch number deleted"))
    except ProtectedError:
        messages.error(request, _("You cannot delete this Batch number."))
    return redirect(asset_batch_view)


@login_required
@hx_request_required
@permission_required(perm="asset.delete_assetlot")
def asset_batch_number_search(request):
    """
    View function to return search  data of asset batch number.

    Args:
    - id: integer value representing the ID of the asset

    Returns:
    - message of the return
    """
    asset_batch_number_search = request.GET.get("search")
    if asset_batch_number_search is None:
        asset_batch_number_search = ""

    asset_batchs = AssetLot.objects.all().filter(
        lot_number__icontains=asset_batch_number_search
    )
    previous_data = request.GET.urlencode()
    asset_batch_numbers_search_paginator = Paginator(asset_batchs, 20)
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
@permission_required(perm="asset.delete_assetcategory")
def delete_asset_category(request, cat_id):
    """
    This method is used to delete asset category
    """
    try:
        AssetCategory.objects.get(id=cat_id).delete()
        messages.success(request, _("Asset category deleted."))
    except:
        messages.error(request, _("Assets are located within this category."))
    return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))
