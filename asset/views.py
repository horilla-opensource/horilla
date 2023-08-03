""""
asset.py

This module is used to """
import pandas as pd
from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpResponseRedirect
from django.contrib import messages
from django.core.paginator import Paginator
from django.utils.translation import gettext_lazy as _
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
    AssetRequestFilter,
    CustomAssetFilter,
    AssetCategoryFilter,
    AssetExportFilter,
    AssetFilter,
)


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
def asset_update(request, id):
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
    instance = Asset.objects.get(id=id)
    asset_form = AssetForm(instance=instance)
    previous_data = request.environ["QUERY_STRING"]
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
def asset_information(request, id):
    """
    Display information about a specific Asset object.
    Args:
        request: the HTTP request object
        id (int): the ID of the Asset object to retrieve
    Returns:
        A rendered HTML template displaying the information about the requested Asset object.
    """

    asset = Asset.objects.get(id=id)
    context = {"asset": asset}
    return render(request, "asset/asset_information.html", context)


@login_required
@permission_required("asset.delete_asset")
def asset_delete(request, id):
    """Delete the asset with the given id.
    If the asset is currently in use, display an info message and
    redirect to the asset list.
    Otherwise, delete the asset and display a success message.
    Args:
        request: HttpRequest object representing the current request.
        id: int representing the id of the asset to be deleted.
    Returns:
        If the asset is currently in use or the asset list filter is
        applied, render the asset list template
        with the corresponding context.
        Otherwise, redirect to the asset list view for the asset
        category of the deleted asset.
    """

    asset = Asset.objects.get(id=id)
    status = asset.asset_status
    asset_list_filter = request.GET.get("asset_list")
    asset_allocation = AssetAssignment.objects.filter(asset_id=asset).first()
    if asset_list_filter:
        # if the asset deleted is from the filterd list of asset
        asset_under = "asset_filter"
        assets = Asset.objects.all()
        previous_data = request.environ["QUERY_STRING"]
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

        asset.delete()
        messages.success(request, _("Asset deleted successfully"))
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

        asset.delete()
        messages.success(request, _("Asset deleted successfully"))
    return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))


@login_required
@hx_request_required
def asset_list(request, id):
    """
    View function is used as asset list inside a category and also in
    filterd asset list
    Args:
        request (HttpRequest): A Django HttpRequest object that contains
        information about the  current request.
        id (int): An integer representing the id of the asset category
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
        asset_category = AssetCategory.objects.get(id=id)
        assets_in_category = Asset.objects.filter(asset_category_id=asset_category)

    previous_data = request.environ["QUERY_STRING"]
    asset_filtered = AssetFilter(request.GET, queryset=assets_in_category)
    asset_list = asset_filtered.qs
    # Change 20 to the desired number of items per page
    paginator = Paginator(asset_list, 20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "assets": page_obj,
        "pg": previous_data,
        "asset_category_id": id,
        "asset_under": asset_under,
        "asset_count": len(assets_in_category) or None,
    }
    return render(request, "asset/asset_list.html", context)


@login_required
@hx_request_required
@permission_required("asset.add_assetcategory")
def asset_category_creation(request):
    """
    Allow a user to create a new AssetCategory object using a form.
    Args:
        request: the HTTP request object
    Returns:
        A rendered HTML template displaying the AssetCategory creation form.
    """
    asset_category_form = AssetCategoryForm()
    context = {"asset_category_form": asset_category_form}

    if request.method == "POST":
        asset_category_form = AssetCategoryForm(request.POST)
        if asset_category_form.is_valid():
            asset_category_form.save()
            messages.success(request, _("Asset category created successfully"))
        else:
            context["asset_category_form"] = asset_category_form
    return render(request, "category/asset_category_creation.html", context)


@login_required
@hx_request_required
@permission_required("asset.change_assetcategory")
def asset_category_update(request, id):
    """
    This view is used to update an existing asset category.
    Args:
        request: HttpRequest object.
        id: int value representing the id of the asset category to update.
    Returns:
        Rendered HTML template.
    """

    previous_data = request.environ["QUERY_STRING"]
    asset_category = AssetCategory.objects.get(id=id)
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


@permission_required("asset.delete_assetcategory")
def asset_category_delete(request, id):
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
    asset_category = AssetCategory.objects.get(id=id)
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

    asset_category.delete()
    messages.success(request, _("Asset Category Deleted"))
    return redirect(asset_category_view_search_filter)


def filter_pagination_asset_category(request):
    search = request.GET.get("search")
    if search is None:
        search = ""

    previous_data = request.environ["QUERY_STRING"]
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
    }


@login_required
@permission_required("asset.view_assetcategory")
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
    context = filter_pagination_asset_category(request)
    return render(request, "category/asset_category_view.html", context)


@login_required
@permission_required("asset.view_assetcategory")
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
@permission_required("asset.add_asset")
def asset_request_approve(request, id):
    """
    Approves an asset request with the given ID and updates the corresponding asset record
    to mark it as allocated.
    Args:
        request: The HTTP request object.
        id (int): The ID of the asset request to be approved.
    Returns:
        A redirect response to the asset request allocation view, or an error message if the
        request with the given ID cannot be found or its asset has already been allocated.
    """

    asset_request = AssetRequest.objects.filter(id=id).first()
    asset_category = asset_request.asset_category_id
    assets = asset_category.asset_set.all()
    form = AssetAllocationForm()
    form.fields["asset_id"].queryset = assets
    context = {"asset_allocation_form": form, "id": id}
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
                {"asset_allocation_form": form, "id": id},
            )
            return HttpResponse(
                response.content.decode("utf-8") + "<script>location.reload();</script>"
            )
        context["asset_allocation_form"] = form

    return render(request, "request_allocation/asset_approve.html", context)


@login_required
@permission_required("asset.add_asset")
def asset_request_reject(request, id):
    """
    View function to reject an asset request.
    Parameters:
    request (HttpRequest): the request object sent by the client
    id (int): the id of the AssetRequest object to reject

    Returns:
    HttpResponse: a redirect to the asset request list view with a success m
        essage if the asset request is rejected successfully, or a redirect to the
        asset request detail view with an error message if the asset request is not
        found or already rejected
    """
    asset_request = AssetRequest.objects.get(id=id)
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
@permission_required("asset.add_asset")
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
def asset_allocate_return(request, id):
    """
    View function to return asset.
    Args:
    - id: integer value representing the ID of the asset
    Returns:
    - message of the return
    """

    context = {"asset_return_form": AssetReturnForm(), "asset_id": id}
    if request.method == "POST":
        asset = Asset.objects.filter(id=id).first()
        asset_return_status = request.POST.get("return_status")
        asset_return_date = request.POST.get("return_date")
        asset_return_condition = request.POST.get("return_condition")
        if asset_return_status == "Healthy":
            asset_allocation = AssetAssignment.objects.filter(
                asset_id=id, return_status__isnull=True
            ).first()
            asset_allocation.return_date = asset_return_date
            asset_allocation.return_status = asset_return_status
            asset_allocation.return_condition = asset_return_condition
            asset_allocation.save()
            asset.asset_status = "Available"
            asset.save()
            messages.info(request, _("Asset Return Successful !."))
            return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))
        asset.asset_status = "Not-Available"
        asset.save()
        asset_allocation = AssetAssignment.objects.filter(
            asset_id=id, return_status__isnull=True
        ).first()
        asset_allocation.return_date = asset_return_date
        asset_allocation.return_status = asset_return_status
        asset_allocation.return_condition = asset_return_condition
        asset_allocation.save()
        messages.info(request, _("Asset Return Successful!."))
        return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))
    return render(request, "asset/asset_return_form.html", context)


def filter_pagination_asset_request_allocation(request):
    asset_request_alloaction_search = request.GET.get("search")
    if asset_request_alloaction_search is None:
        asset_request_alloaction_search = ""
    employee = request.user.employee_get

    assets = (
        AssetAssignment.objects.filter(assigned_to_employee_id=employee)
        .exclude(return_status__isnull=False)
        .filter(asset_id__asset_name__icontains=asset_request_alloaction_search)
    )
    if request.user.has_perm(("asset.view_assetrequest", "asset.view_assetassignment")):
        asset_allocations_queryset = AssetAssignment.objects.all().filter(
            assigned_to_employee_id__employee_first_name__icontains=asset_request_alloaction_search
        )
        asset_requests_queryset = AssetRequest.objects.all().filter(
            requested_employee_id__employee_first_name__icontains=asset_request_alloaction_search
        )
    else:
        asset_allocations_queryset = AssetAssignment.objects.filter(
            assigned_to_employee_id=employee
        ).filter(
            assigned_to_employee_id__employee_first_name__icontains=asset_request_alloaction_search
        )
        asset_requests_queryset = AssetRequest.objects.filter(
            requested_employee_id=employee
        ).filter(
            requested_employee_id__employee_first_name__icontains=asset_request_alloaction_search
        )

    previous_data = request.environ["QUERY_STRING"]
    assets_filtered = CustomAssetFilter(request.GET, queryset=assets)
    asset_request_filtered = AssetRequestFilter(
        request.GET, queryset=asset_requests_queryset
    )
    asset_allocation_filtered = AssetAllocationFilter(
        request.GET, queryset=asset_allocations_queryset
    )
    asset_paginator = Paginator(assets_filtered.qs, 20)
    asset_request_paginator = Paginator(asset_request_filtered.qs, 20)
    asset_allocation_paginator = Paginator(asset_allocation_filtered.qs, 20)
    page_number = request.GET.get("page")
    assets = asset_paginator.get_page(page_number)
    asset_requests = asset_request_paginator.get_page(page_number)
    asset_allocations = asset_allocation_paginator.get_page(page_number)

    return {
        "assets": assets,
        "asset_requests": asset_requests,
        "asset_allocations": asset_allocations,
        "assets_filter_form": assets_filtered.form,
        "asset_request_filter_form": asset_request_filtered.form,
        "asset_allocation_filter_form": asset_allocation_filtered.form,
        "pg": previous_data,
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
    return render(
        request, "request_allocation/asset_request_allocation_view.html", context
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
    return render(
        request, "request_allocation/asset_request_allocation_list.html", context
    )


def convert_nan(val):
    if pd.isna(val):
        return None
    else:
        return val


@login_required
@permission_required("asset.add_asset")
def asset_import(request):
    """asset import view"""

    try:
        if request.method == "POST":
            file = request.FILES.get("asset_import")

            if file is not None:
                try:
                    df = pd.read_excel(file)
                except KeyError as e:
                    messages.error(request, f"{e}")
                    return redirect(asset_category_view)

                # Create Asset objects from the DataFrame and save them to the database
                for index, row in df.iterrows():
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
    except Exception as e:
        messages.error(request, f"{e}")
        return redirect(asset_category_view)


@login_required
def asset_excel(request):
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
        df = pd.DataFrame(columns=columns)
        # Write the DataFrame to an Excel file
        response = HttpResponse(content_type="application/ms-excel")
        response["Content-Disposition"] = 'attachment; filename="my_excel_file.xlsx"'
        df.to_excel(response, index=False)
        return response
    except Exception as e:
        return HttpResponse(e)


@login_required
@permission_required("asset.add_asset")
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
    df = pd.DataFrame(data)

    # Convert any date fields to the desired format
    # Rename the columns as needed
    df = df.rename(
        columns={
            "asset_name": "Asset name",
            "asset_description": "Description",
            "asset_tracking_id": "Tracking id",
            "asset_purchase_date": "Purchase date",
            "asset_purchase_cost": "Purchase cost",
            "asset_category_id": "Category",
            "asset_status": "Status",
            "asset_lot_number_id": "lot number",
        }
    )

    # Write the DataFrame to an Excel file
    response = HttpResponse(content_type="application/vnd.ms-excel")
    response["Content-Disposition"] = 'attachment; filename="assets.xlsx"'
    df.to_excel(response, index=False)
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
        else:
            context = {
                "asset_batch_form": asset_batch_form,
            }
        return render(request, "batch/asset_batch_number_creation.html", context)
    return render(request, "batch/asset_batch_number_creation.html", context)


@login_required
@permission_required("asset.add_assetlot")
def asset_batch_view(request):
    """
    View function to display details of all batch numbers.

    Returns:
    -  all asset batch numbers based on page
    """

    asset_batchs = AssetLot.objects.all()
    previous_data = request.environ["QUERY_STRING"]
    asset_batch_numbers_search_paginator = Paginator(asset_batchs, 20)
    page_number = request.GET.get("page")
    asset_batch_numbers = asset_batch_numbers_search_paginator.get_page(page_number)
    asset_batch_form = AssetBatchForm()

    context = {
        "batch_numbers": asset_batch_numbers,
        "asset_batch_form": asset_batch_form,
        "pg": previous_data,
    }
    return render(request, "batch/asset_batch_number_view.html", context)


@login_required
@permission_required("asset.change_assetlot")
def asset_batch_update(request, id):
    """
    View function to return asset.
    Args:
    - id: integer value representing the ID of the asset
    Returns:
    - message of the return
    """
    asset_batch_number = AssetLot.objects.get(id=id)
    asset_batch = AssetLot.objects.get(id=id)
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
        context["in_use_message"] = "This batch number is already in-use"
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
@permission_required("asset.delete_assetlot")
def asset_batch_number_delete(request, id):
    """
    View function to return asset.
    Args:
    - id: integer value representing the ID of the asset
    Returns:
    - message of the return
    """
    asset_batch_number = AssetLot.objects.get(id=id)
    assigned_batch_number = Asset.objects.filter(asset_lot_number_id=asset_batch_number)
    if assigned_batch_number:
        messages.error(request, _("Batch number in-use"))
        return redirect(asset_batch_view)
    asset_batch_number.delete()
    messages.success(request, _("Batch number deleted"))
    return redirect(asset_batch_view)


@login_required
@hx_request_required
@permission_required("asset.delete_assetlot")
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
    previous_data = request.environ["QUERY_STRING"]
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
@permission_required("asset.delete_assetcategory")
def delete_asset_category(request, cat_id):
    """
    This method is used to delete asset category
    """
    try:
        AssetCategory.objects.get(id=cat_id).delete()
        messages.success(request, "Asset category deleted.")
    except:
        messages.error(request, "Something went wrong!")
    return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))
