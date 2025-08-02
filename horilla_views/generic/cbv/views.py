"""
horilla/generic/views.py
"""

import io
import json
import logging
import traceback
from typing import Any
from urllib.parse import parse_qs, urlencode

import pandas as pd
from bs4 import BeautifulSoup
from django import forms
from django.contrib import messages
from django.core.cache import cache as CACHE
from django.core.exceptions import FieldDoesNotExist
from django.core.paginator import Page
from django.db import transaction
from django.db.models import CharField, F
from django.db.models.functions import Cast
from django.http import HttpRequest, HttpResponse, JsonResponse, QueryDict
from django.shortcuts import render
from django.template.loader import render_to_string
from django.urls import resolve, reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView, FormView, ListView, TemplateView
from xhtml2pdf import pisa

from base.methods import closest_numbers, eval_validate, get_key_instances
from horilla.filters import FilterSet
from horilla.group_by import group_by_queryset
from horilla.horilla_middlewares import _thread_locals
from horilla.signals import post_generic_import, pre_generic_import
from horilla_views import models
from horilla_views.cbv_methods import (  # update_initial_cache,
    assign_related,
    export_xlsx,
    generate_import_excel,
    get_short_uuid,
    get_verbose_name_from_field_path,
    hx_request_required,
    paginator_qry,
    sortby,
    split_by_import_reference,
    structured,
    update_saved_filter_cache,
)
from horilla_views.forms import DynamicBulkUpdateForm, ToggleColumnForm
from horilla_views.templatetags.generic_template_filters import getattribute

logger = logging.getLogger(__name__)


@method_decorator(hx_request_required, name="dispatch")
class HorillaListView(ListView):
    """
    HorillaListView
    """

    filter_class: FilterSet = None

    view_id: str = """"""

    export_file_name: str = "quick_export"
    export_formats: list = [
        ("xlsx", "Excel"),
        ("json", "Json"),
        ("csv", "CSV"),
        ("pdf", "PDF"),
    ]

    template_name: str = "generic/horilla_list_table.html"
    context_object_name = "queryset"
    # column = [("Verbose Name","field_name","avatar_mapping")], opt: avatar_mapping
    columns: list = []
    default_columns: list = []
    search_url: str = ""
    bulk_select_option: bool = True
    filter_selected: bool = True
    quick_export: bool = True
    bulk_update: bool = True
    import_fields: list = []
    import_file_name: str = "Quick Import"
    update_reference: str = "pk"
    import_related_model_column_mapping: dict = {}
    primary_key_mapping: dict = {}
    import_related_column_export_mapping: dict = {}
    reverse_model_relation_to_base_model: dict = {}
    fk_mapping: dict = {}
    import_help: dict = {}
    fk_o2o_field_in_base_model: list = []
    individual_update: bool = False
    o2o_related_name_mapping: dict = {}

    custom_empty_template: str = ""

    action_method: str = """"""
    """
    eg:
    def accessibility(
        request, instance: object = None, user_perms: PermWrapper = [], *args, **kwargs
    )->bool:
        # True if accessible to the action else False
        return True

    actions = [
        {
            "action": "Edit",
            "accessibility": "path_to_your.accessibility", # path to your accessibility method
            "attrs": '''{instance_attributes_called_like_this}''',
        },
        etc..
    ]
    """
    actions: list = []

    option_method: str = ""
    options: list = []
    row_attrs: str = """"""
    row_status_class: str = """"""
    row_status_indications: list = []

    sortby_key: str = "sortby"
    sortby_mapping: list = []

    selected_instances_key_id: str = "selectedInstances"

    show_filter_tags: bool = True
    show_toggle_form: bool = True
    filter_keys_to_remove: list = []

    records_per_page: int = 50
    export_fields: list = []
    verbose_name: str = ""
    bulk_update_fields: list = []
    bulk_template: str = "generic/bulk_form.html"
    records_count_in_tab: bool = True

    header_attrs: dict = {}

    @classmethod
    def as_view(cls, **initkwargs):
        def view(request, *args, **kwargs):
            # Inject URL params into initkwargs
            initkwargs_with_url = {**initkwargs, **kwargs}
            self = cls(**initkwargs_with_url)
            self.request = request
            self.args = args
            self.kwargs = kwargs
            return self.dispatch(request, *args, **kwargs)

        return view

    def post(self, *args, **kwargs):
        """
        POST method to handle post submissions
        """
        return self.get(self, *args, **kwargs)

    def __init__(self, **kwargs: Any) -> None:
        if not self.view_id:
            self.view_id = get_short_uuid(4)
        super().__init__(**kwargs)

        self.ordered_ids_key = f"ordered_ids_{self.model.__name__.lower()}"
        request = getattr(_thread_locals, "request", None)
        self.request = request

        self.visible_column = list(self.columns)

        hidden_fields = []
        existing_instance = None
        if request:
            existing_instance = models.ToggleColumn.objects.filter(
                user_id=request.user, path=request.path_info
            ).first()
            if existing_instance:
                hidden_fields = existing_instance.excluded_columns

        if not self.default_columns:
            self.default_columns = self.columns

        self.toggle_form = ToggleColumnForm(
            self.columns, self.default_columns, hidden_fields
        )

        # Remove hidden columns from visible_column
        hidden_field_names = (
            {
                col[1] if isinstance(col, tuple) else col
                for col in self.columns
                if col[1] in hidden_fields
            }
            if existing_instance
            else {col[1] for col in self.columns if col not in self.default_columns}
        )
        self.visible_column = [
            col
            for col in self.visible_column
            if (col[1] if isinstance(col, tuple) else col) not in hidden_field_names
        ]

        # Add verbose names to fields if possible
        updated_column = []
        get_field = self.model()._meta.get_field
        for col in self.visible_column:
            if isinstance(col, str):
                try:
                    updated_column.append((get_field(col).verbose_name, col))
                except FieldDoesNotExist:
                    updated_column.append(col)
            else:
                updated_column.append(col)

        self.visible_column = updated_column

    def bulk_update_accessibility(self) -> bool:
        """
        Accessibility method for bulk update
        """
        return self.request.user.has_perm(
            f"{self.model._meta.app_label}.change_{self.model.__name__.lower()}"
        )

    def import_accessibility(self) -> bool:
        """
        Accessibility method for bulk importz
        """
        return self.request.user.has_perm(
            f"{self.model._meta.app_label}.add_{self.model.__name__.lower()}"
        )

    def serve_bulk_form(self, request: HttpRequest) -> HttpResponse:
        """
        Bulk form serve method
        """

        if not self.bulk_update_accessibility():
            return HttpResponse("You dont have permission")
        ids = eval_validate(request.POST.get("instance_ids", "[]"))
        form = self.get_bulk_form()
        form.verbose_name = form.verbose_name + f" ({len((ids))} {_('Records')})"
        return render(
            request,
            self.bulk_template,
            {"form": form, "post_bulk_path": self.post_bulk_path, "instance_ids": ids},
        )

    def handle_bulk_submission(self, request: HttpRequest) -> HttpRequest:
        """
        This method to handle bulk update form submission
        """
        if not self.bulk_update_accessibility():
            return HttpResponse("You dont have permission")

        instance_ids = request.POST.get("instance_ids", "[]")
        instance_ids = eval_validate(instance_ids)
        form = DynamicBulkUpdateForm(
            request.POST,
            request.FILES,
            root_model=self.model,
            bulk_update_fields=self.bulk_update_fields,
            ids=instance_ids,
        )
        if instance_ids and form.is_valid():
            form.save()
            messages.success(request, _("Selected Records updated"))

            script_id = get_short_uuid(length=3, prefix="bulk")
            return HttpResponse(
                f"""
                <script id="{script_id}">
                    $("#{script_id}").closest(".oh-modal--show").removeClass("oh-modal--show");
                    $("#{self.selected_instances_key_id}").attr("data-ids", "[]");
                    $(".reload-record").click()
                    $("#reloadMessagesButton").click()
                </script>
                """
            )
        if not instance_ids:
            messages.info(request, _("No records selected"))
        return render(
            request,
            self.bulk_template,
            {"form": form, "post_bulk_path": self.post_bulk_path},
        )

    def get_bulk_form(self):
        """
        Bulk from generating method
        """
        # Bulk update feature
        return DynamicBulkUpdateForm(
            root_model=self.model, bulk_update_fields=self.bulk_update_fields
        )

    def serve_import_sheet(self, request, *args, **kwargs):
        """
        Method to serve bulk import sheet
        """
        if not self.import_accessibility():
            messages.info(request, "You dont have permission")
            return HorillaFormView.HttpResponse()
        ids = eval_validate(request.POST["selected_ids"])

        wb = generate_import_excel(
            self.model,
            self.import_fields,
            reference_field=self.update_reference,
            import_mapping=self.import_related_column_export_mapping,
            queryset=self.model.objects.filter(id__in=ids),
        )

        # Create response
        response = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        filename = f"{self.import_file_name}.xlsx"
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        wb.save(response)
        return response

    def import_records(self, request, *args, **kwargs):
        """
        Method to import records
        """
        try:
            if not self.import_accessibility():
                messages.info(request, "You dont have permission")
            field_column_mapping = {
                field: get_verbose_name_from_field_path(
                    self.model, field, self.import_related_model_column_mapping
                )
                for field in self.import_fields
            }
            update_reference = f"{get_verbose_name_from_field_path(self.model, self.update_reference, self.import_related_model_column_mapping)} | Reference"
            update_reference_key = f"{self.update_reference}_import_reference"
            field_column_mapping[f"{self.update_reference}_import_reference"] = (
                update_reference
            )

            excel_file = request.FILES.get("file")
            if not excel_file:
                return JsonResponse({"error": "No file uploaded"}, status=400)

            df = pd.read_excel(excel_file)

            serialized = []
            field_column_mapping_values = {}
            for _, row in df.iterrows():
                record = {}
                for model_field, excel_col in field_column_mapping.items():
                    if excel_col in row:
                        value = row[excel_col]
                        if model_field in (
                            list(self.primary_key_mapping.keys())
                            + list(self.import_related_model_column_mapping.keys())
                        ) and not pd.isna(value):
                            field_column_mapping_values[model_field] = (
                                field_column_mapping_values.get(
                                    model_field, set({})
                                ).union({value})
                            )
                        if pd.isna(value):
                            value = None
                        if isinstance(value, str):
                            value = value.strip()
                        parts = model_field.split("__")
                        current = record
                        for part in parts[:-1]:
                            current = current.setdefault(part, {})
                        if isinstance(value, float) and value.is_integer():
                            value = int(value)
                        current[parts[-1]] = value
                serialized.append(record)
            with_ref, without_ref = split_by_import_reference(serialized)

            error_records = []

            error_records = []
            pk_values_mapping = {}
            fk_values_mapping = {}

            for mapping, values in field_column_mapping_values.items():
                related_model = self.import_related_model_column_mapping[mapping]
                if mapping in self.primary_key_mapping:
                    field = self.primary_key_mapping[mapping]
                    if hasattr(related_model.objects, "entire"):
                        existing_objects = (
                            related_model.objects.entire()
                            .filter(**{f"{field}__in": list(values)})
                            .only("pk", field)
                        )
                    else:
                        existing_objects = related_model.objects.filter(
                            **{f"{field}__in": list(values)}
                        ).only("pk", field)

                    existing_values = existing_objects.annotate(
                        field_as_str=Cast(F(field), CharField())
                    ).values_list("field_as_str", flat=True)

                    to_create = [
                        related_model(**{field: value})
                        for value in values
                        if str(value) not in existing_values
                    ]

                    if to_create:
                        pre_generic_import.send(
                            sender=related_model,
                            records=to_create,
                            view=self,
                        )
                        related_model.objects.bulk_create(to_create)
                        post_generic_import.send(
                            sender=related_model,
                            records=to_create,
                            view=self,
                        )
                    pk_values_mapping[mapping] = pk_values_mapping.get(
                        mapping, []
                    ) + list(existing_objects)
                elif mapping in self.fk_mapping:
                    field = self.fk_mapping[mapping]
                    related_model = self.import_related_model_column_mapping[mapping]
                    existing_objects = related_model.objects.filter(
                        **{f"{field}__in": list(values)}
                    ).only("pk", field)
                    existing_values = existing_objects.values_list(field, flat=True)
                    to_create = [
                        related_model(**{field: value})
                        for value in values
                        if value not in existing_values
                    ]
                    if to_create:
                        pre_generic_import.send(
                            sender=related_model,
                            records=to_create,
                            view=self,
                        )
                        related_model.objects.bulk_create(to_create)
                        post_generic_import.send(
                            sender=related_model,
                            records=to_create,
                            view=self,
                        )
                    fk_values_mapping[mapping] = fk_values_mapping.get(
                        mapping, []
                    ) + list(existing_objects)
            if without_ref:
                with transaction.atomic():
                    records_to_import = []
                    for record in without_ref:
                        try:
                            for reverse_field in (
                                list(self.reverse_model_relation_to_base_model.keys())
                                + self.fk_o2o_field_in_base_model
                            ):
                                if reverse_field in list(
                                    self.primary_key_mapping.keys()
                                ) + list(
                                    self.reverse_model_relation_to_base_model.keys()
                                ):
                                    result = assign_related(
                                        record,
                                        reverse_field,
                                        pk_values_mapping,
                                        self.primary_key_mapping,
                                    )
                                    record[reverse_field] = result
                                elif reverse_field in self.fk_mapping:
                                    record.update(
                                        {
                                            reverse_field: data
                                            for data in fk_values_mapping[reverse_field]
                                            if getattr(
                                                data,
                                                self.fk_mapping[reverse_field],
                                                None,
                                            )
                                            == record[reverse_field]
                                        }
                                    )
                            records_to_import.append(record)

                        except Exception as e:
                            error_records.append(
                                {
                                    "record": record.get(next(iter(record)), "Unknown"),
                                    "error": str(e),
                                }
                            )
                    bulk_base_fk_grouping = {}
                    bulk_create_reverse_related_grouping = {}
                    bulk_create_base_grouping = []
                    items = []

                    related_fields = list(
                        self.reverse_model_relation_to_base_model.keys()
                    )
                    fk_fields = self.fk_o2o_field_in_base_model

                    for record in records_to_import:
                        if record.get(update_reference_key):
                            del record[update_reference_key]
                        instance_record = record.copy()
                        if update_reference_key in instance_record:
                            del instance_record[update_reference_key]
                        for relation in related_fields:
                            if relation in instance_record:
                                del instance_record[relation]
                        for fk_field in self.fk_o2o_field_in_base_model:
                            if (
                                fk_field in instance_record
                                and fk_field not in self.fk_mapping
                            ):
                                del instance_record[fk_field]

                        instance = self.model(**instance_record)
                        for relation in related_fields:
                            related_record = record[relation]
                            related_record[
                                self.reverse_model_relation_to_base_model[relation]
                            ] = instance
                            related_instance = self.import_related_model_column_mapping[
                                relation
                            ](**related_record)
                            bulk_create_reverse_related_grouping[relation] = (
                                bulk_create_reverse_related_grouping.get(relation, [])
                                + [related_instance]
                            )

                        for fk_field in fk_fields:
                            fk_record = record[fk_field]
                            if isinstance(fk_record, dict):
                                fk_instance = self.import_related_model_column_mapping[
                                    fk_field
                                ](**fk_record)
                            else:
                                fk_instance = fk_record
                            bulk_base_fk_grouping[fk_field] = bulk_base_fk_grouping.get(
                                fk_field, []
                            ) + [fk_instance]
                            setattr(instance, fk_field, fk_instance)

                        bulk_create_base_grouping.append(instance)

                    for fk_field in self.fk_o2o_field_in_base_model:
                        if fk_field not in self.fk_mapping:
                            for relation, items in bulk_base_fk_grouping.items():
                                pre_generic_import.send(
                                    sender=self.import_related_model_column_mapping[
                                        fk_field
                                    ],
                                    records=items,
                                    view=self,
                                )

                                if relation not in self.fk_mapping:
                                    pre_generic_import.send(
                                        sender=self.import_related_model_column_mapping[
                                            fk_field
                                        ],
                                        records=items,
                                        view=self,
                                    )
                                    self.import_related_model_column_mapping[
                                        fk_field
                                    ].objects.bulk_create(items)
                                    post_generic_import.send(
                                        sender=self.import_related_model_column_mapping[
                                            fk_field
                                        ],
                                        records=items,
                                        view=self,
                                    )

                    if not items:
                        items = bulk_create_base_grouping
                    pre_generic_import.send(
                        sender=self.model,
                        records=items,
                        view=self,
                    )

                    self.model.objects.bulk_create(bulk_create_base_grouping)

                    post_generic_import.send(
                        sender=self.model,
                        records=items,
                        view=self,
                    )
                    for related, items in bulk_create_reverse_related_grouping.items():
                        pre_generic_import.send(
                            sender=self.import_related_model_column_mapping[related],
                            records=items,
                            view=self,
                        )
                        self.import_related_model_column_mapping[
                            related
                        ].objects.bulk_create(items)
                        post_generic_import.send(
                            sender=self.import_related_model_column_mapping[related],
                            records=items,
                            view=self,
                        )
            if with_ref:
                base_instance_ids = [item["id_import_reference"] for item in with_ref]
                fields = (
                    list(self.reverse_model_relation_to_base_model)
                    + ["pk"]
                    + self.fk_o2o_field_in_base_model
                )
                mapped_ids_queryset = (
                    self.model.objects.filter(pk__in=base_instance_ids)
                    .only(*fields)
                    .values(*fields)
                )
                mapped_ids_with_reverse = {
                    item["pk"]: {
                        key: item[key]
                        for key in list(
                            self.reverse_model_relation_to_base_model.keys()
                        )
                        + self.fk_o2o_field_in_base_model
                        if key not in self.fk_mapping
                    }
                    for item in mapped_ids_queryset
                }
                field_to_update_o2o = {}
                o2o_to_create = []
                o2o_create_base_mapping = {}
                with transaction.atomic():
                    records_to_update = []
                    for record in with_ref:
                        try:
                            for reverse_field in (
                                list(self.reverse_model_relation_to_base_model.keys())
                                + self.fk_o2o_field_in_base_model
                            ):
                                if reverse_field in list(
                                    self.primary_key_mapping.keys()
                                ) + list(
                                    self.reverse_model_relation_to_base_model.keys()
                                ):
                                    result = assign_related(
                                        record,
                                        reverse_field,
                                        pk_values_mapping,
                                        self.primary_key_mapping,
                                    )
                                    if list(result.keys())[0] not in self.fk_mapping:
                                        if (
                                            reverse_field
                                            in self.fk_o2o_field_in_base_model
                                        ):
                                            result["main_instance_id"] = record[
                                                "id_import_reference"
                                            ]
                                        record[reverse_field] = result
                                    else:
                                        record[list(result.keys())[0]] = list(
                                            result.values()
                                        )[0]
                                elif reverse_field in self.fk_mapping:
                                    record.update(
                                        {
                                            reverse_field: data
                                            for data in fk_values_mapping[reverse_field]
                                            if getattr(
                                                data,
                                                self.fk_mapping[reverse_field],
                                                None,
                                            )
                                            == record[reverse_field]
                                        }
                                    )
                            records_to_update.append(record)

                        except Exception as e:
                            logger.error(traceback.format_exc())
                            error_records.append(
                                {
                                    "record": record[list(record.keys())[0]],
                                    "error": str(e),
                                }
                            )
                    bulk_base_fk_grouping = {}
                    bulk_update_reverse_related_grouping = {}
                    bulk_create_from_update_reverse_related_grouping = {}
                    bulk_update_base_grouping = []

                    related_fields = list(
                        self.reverse_model_relation_to_base_model.keys()
                    )
                    fk_fields = self.fk_o2o_field_in_base_model
                    related_update_fields = {}
                    for record in records_to_update:
                        instance_record = record.copy()
                        for relation in related_fields:
                            if relation in instance_record:
                                del instance_record[relation]
                        for fk_field in self.fk_o2o_field_in_base_model:
                            if (
                                fk_field in instance_record
                                and fk_field not in self.fk_mapping
                            ):
                                del instance_record[fk_field]

                        instance_record["id"] = instance_record["id_import_reference"]
                        instance_record["pk"] = instance_record["id_import_reference"]
                        del instance_record["id_import_reference"]
                        instance = self.model(**instance_record)
                        for relation in related_fields:
                            related_update_fields[relation] = record[relation].keys()

                        for relation in related_fields:
                            related_record = record[relation]
                            related_record[
                                self.reverse_model_relation_to_base_model[relation]
                            ] = instance
                            related_record["id"] = mapped_ids_with_reverse[instance.id][
                                relation
                            ]
                            related_record["pk"] = mapped_ids_with_reverse[instance.id][
                                relation
                            ]
                            related_instance = self.import_related_model_column_mapping[
                                relation
                            ](**related_record)
                            if related_instance.pk is not None:
                                bulk_update_reverse_related_grouping[relation] = (
                                    bulk_update_reverse_related_grouping.get(
                                        relation, []
                                    )
                                    + [related_instance]
                                )
                            else:
                                bulk_create_from_update_reverse_related_grouping[
                                    relation
                                ] = bulk_update_reverse_related_grouping.get(
                                    relation, []
                                ) + [
                                    related_instance
                                ]

                        for fk_field in fk_fields:
                            if fk_field not in self.fk_mapping:
                                fk_record = record[fk_field]
                                pk = mapped_ids_with_reverse[
                                    fk_record["main_instance_id"]
                                ][fk_field]
                                del fk_record["main_instance_id"]
                                if pk is None:
                                    fk_record[
                                        self.o2o_related_name_mapping[fk_field]
                                    ] = self.model(pk=pk, id=pk)
                                    o2o_related_instance = (
                                        self.import_related_model_column_mapping[
                                            fk_field
                                        ](**fk_record)
                                    )
                                    setattr(instance, fk_field, o2o_related_instance)
                                    o2o_to_create.append(o2o_related_instance)
                                    continue
                                fk_record["pk"] = pk
                                fk_record["id"] = pk
                                if fk_field not in field_to_update_o2o:
                                    field_to_update_o2o[fk_field] = list(
                                        fk_record.keys()
                                    )
                                fk_instance = self.import_related_model_column_mapping[
                                    fk_field
                                ](**fk_record)
                                bulk_base_fk_grouping[fk_field] = (
                                    bulk_base_fk_grouping.get(fk_field, [])
                                    + [fk_instance]
                                )
                                setattr(instance, fk_field, fk_instance)
                        bulk_update_base_grouping.append(instance)
            if with_ref and bulk_update_base_grouping:
                for o2o_field, records in bulk_base_fk_grouping.items():
                    field_to_update_o2o = [
                        field
                        for field in field_to_update_o2o[o2o_field]
                        if field not in ["pk", "id"]
                    ]
                    related_model = self.import_related_model_column_mapping[o2o_field]
                    pre_generic_import.send(
                        sender=related_model,
                        records=records,
                        view=self,
                    )
                    if not self.individual_update:
                        related_model.objects.bulk_update(
                            records,
                            field_to_update_o2o,
                        )
                        if o2o_to_create:
                            pre_generic_import.send(
                                sender=related_model,
                                records=o2o_to_create,
                                view=self,
                            )
                            related_model.objects.bulk_create(o2o_to_create)
                            post_generic_import.send(
                                sender=related_model,
                                records=o2o_to_create,
                                view=self,
                            )
                    else:
                        if o2o_to_create:
                            pre_generic_import.send(
                                sender=related_model,
                                records=o2o_to_create,
                                view=self,
                            )
                            related_model.objects.bulk_create(o2o_to_create)
                            post_generic_import.send(
                                sender=related_model,
                                records=o2o_to_create,
                                view=self,
                            )
                        for o2o_instance in records:
                            related_model.objects.update_or_create(
                                id=o2o_instance.id,
                                defaults={
                                    field: getattr(o2o_instance, field)
                                    for field in field_to_update_o2o
                                },
                            )
                    post_generic_import.send(
                        sender=related_model,
                        records=records,
                        view=self,
                    )
                field_to_update = [
                    key for key in instance_record.keys() if key not in ["id", "pk"]
                ] + [key for key in self.o2o_related_name_mapping]
                pre_generic_import.send(
                    sender=self.model,
                    records=bulk_update_base_grouping,
                    view=self,
                )
                if not self.individual_update:
                    self.model.objects.bulk_update(
                        bulk_update_base_grouping, field_to_update
                    )
                else:
                    for model_obj in bulk_update_base_grouping:
                        self.model.objects.update_or_create(
                            id=model_obj.id,
                            defaults={
                                field: getattr(model_obj, field)
                                for field in field_to_update
                            },
                        )
                post_generic_import.send(
                    sender=self.model,
                    records=bulk_update_base_grouping,
                    view=self,
                )

            if with_ref and related_update_fields:
                for field in related_fields:
                    related_model = self.import_related_model_column_mapping[field]
                    if field in bulk_update_reverse_related_grouping:
                        update_fields = [
                            key
                            for key in related_update_fields[field]
                            if key not in ["id", "pk"]
                        ]
                        pre_generic_import.send(
                            sender=related_model,
                            records=bulk_update_reverse_related_grouping[field],
                            view=self,
                        )
                        if not self.individual_update:
                            related_model.objects.bulk_update(
                                bulk_update_reverse_related_grouping[field],
                                update_fields,
                            )
                        else:
                            for (
                                reverse_related_obj
                            ) in bulk_update_reverse_related_grouping[field]:
                                related_model.objects.update_or_create(
                                    id=reverse_related_obj.id,
                                    defaults={
                                        field: getattr(reverse_related_obj, field)
                                        for field in update_fields
                                    },
                                )
                        post_generic_import.send(
                            sender=related_model,
                            records=bulk_update_reverse_related_grouping[field],
                            view=self,
                        )

                    elif field in bulk_create_from_update_reverse_related_grouping:
                        update_fields = [
                            key
                            for key in related_update_fields[field]
                            if key not in ["id", "pk"]
                        ]
                        pre_generic_import.send(
                            sender=related_model,
                            records=bulk_create_from_update_reverse_related_grouping[
                                field
                            ],
                            view=self,
                        )
                        if not self.individual_update:
                            related_model.objects.bulk_create(
                                bulk_create_from_update_reverse_related_grouping[field]
                            )
                        else:
                            for (
                                reverse_related_obj
                            ) in bulk_create_from_update_reverse_related_grouping[
                                field
                            ]:
                                # reverse_related_obj.save()
                                related_model.objects.update_or_create(
                                    id=reverse_related_obj.id,
                                    defaults={
                                        field: getattr(reverse_related_obj, field)
                                        for field in update_fields
                                    },
                                )
                        post_generic_import.send(
                            sender=related_model,
                            records=bulk_create_from_update_reverse_related_grouping[
                                field
                            ],
                            view=self,
                        )
            status = "Success"
            if error_records:
                status = "Error Found"

            return render(
                request,
                "cbv/import_response.html",
                context={
                    "view_id": self.view_id,
                    "status": status,
                    "imported": len(without_ref),
                    "updated": len(with_ref),
                    "errors": error_records[:10],  # Optional: truncate if too large
                    "total_errors": error_records,  # Optional: truncate if too large
                    "more_error": len(error_records) > 10,
                },
            )
        except Exception as e:
            traceback_message = traceback.format_exc()
            error = e
        return render(
            request,
            "cbv/import_response.html",
            context={
                "view_id": self.view_id,
                "status": "Error Found",
                "imported": 0,
                "updated": 0,
                "errors": 0,  # Optional: truncate if too large
                "error_message": error,  # Optional: truncate if too large
                "traceback_message": traceback_message,  # Optional: truncate if too large
            },
        )

    def get_queryset(self, queryset=None, filtered=False, *args, **kwargs):
        if not self.queryset:
            self.queryset = super().get_queryset() if not queryset else queryset
            self._saved_filters = QueryDict("", mutable=True)
            if self.filter_class:
                query_dict = self.request.GET
                selected_ids = eval_validate(
                    self.request.POST.get("selected_ids", "[]")
                )

                if (
                    self.request.session.get("prev_path")
                    and self.request.session.get("prev_path") != self.request.path
                ):
                    selected_ids = []
                    self.request.session["hlv_selected_ids"] = selected_ids
                    self.request.session["prev_path"] = self.request.path

                if selected_ids and selected_ids != self.request.session.get(
                    "hlv_selected_ids", []
                ):
                    self.request.session["hlv_selected_ids"] = selected_ids
                    self.request.session["prev_path"] = self.request.path

                if "filter_applied" in query_dict.keys():
                    update_saved_filter_cache(self.request, CACHE)
                elif CACHE.get(
                    str(self.request.session.session_key) + self.request.path + "cbv"
                ):
                    query_dict = CACHE.get(
                        str(self.request.session.session_key)
                        + self.request.path
                        + "cbv"
                    )["query_dict"]

                default_filter = models.SavedFilter.objects.filter(
                    path=self.request.path,
                    created_by=self.request.user,
                    is_default=True,
                ).first()
                if not bool(query_dict) and default_filter:
                    data = eval_validate(default_filter.filter)
                    query_dict = QueryDict("", mutable=True)
                    for key, value in data.items():
                        query_dict[key] = value

                    query_dict._mutable = False
                self._saved_filters = query_dict
                self.request.exclude_filter_form = True
                if not filtered:
                    self.queryset = self.filter_class(
                        data=query_dict, queryset=self.queryset, request=self.request
                    ).qs
                else:
                    self.queryset = queryset
                if self.request.GET.get(
                    "show_all"
                ) == "true" and self.request.session.get("hlv_selected_ids"):
                    del self.request.session["hlv_selected_ids"]
                if self.request.session.get("hlv_selected_ids"):
                    self.request.actual_ids = list(
                        self.queryset.values_list("id", flat=True)
                    )
                    self.queryset = self.queryset.filter(
                        id__in=self.request.session["hlv_selected_ids"]
                    )
        return self.queryset

    def get_context_data(self, **kwargs: Any):
        context = super().get_context_data(**kwargs)
        if not self.search_url:
            self.search_url = self.request.path
        context["view_id"] = self.view_id
        context["columns"] = self.visible_column
        context["hidden_columns"] = list(set(self.columns) - set(self.visible_column))
        context["toggle_form"] = self.toggle_form
        context["show_toggle_form"] = self.show_toggle_form
        context["search_url"] = self.search_url

        context["action_method"] = self.action_method
        context["actions"] = self.actions

        context["option_method"] = self.option_method
        context["options"] = self.options
        context["row_attrs"] = self.row_attrs

        context["header_attrs"] = self.header_attrs

        context["show_filter_tags"] = self.show_filter_tags
        context["bulk_select_option"] = self.bulk_select_option
        context["row_status_class"] = self.row_status_class
        context["sortby_key"] = self.sortby_key
        context["sortby_mapping"] = self.sortby_mapping
        context["selected_instances_key_id"] = self.selected_instances_key_id
        context["row_status_indications"] = self.row_status_indications
        context["saved_filters"] = self._saved_filters
        context["quick_export"] = self.quick_export
        context["filter_selected"] = self.filter_selected
        context["bulk_update"] = self.bulk_update
        if not self.verbose_name:
            self.verbose_name = self.model.__class__
        context["model_name"] = self.verbose_name
        context["export_fields"] = self.export_fields
        context["custom_empty_template"] = self.custom_empty_template
        context["records_count_in_tab"] = self.records_count_in_tab
        referrer = self.request.GET.get("referrer", "")
        if referrer:
            # Remove the protocol and domain part
            referrer = "/" + "/".join(referrer.split("/")[3:])
        context["stored_filters"] = (
            models.SavedFilter.objects.filter(
                path=self.request.path, created_by=self.request.user
            )
            | models.SavedFilter.objects.filter(
                referrer=referrer, created_by=self.request.user
            )
        ).distinct()

        context["select_all_ids"] = self.select_all
        if self._saved_filters.get("field"):
            active_group = models.ActiveGroup.objects.filter(
                created_by=self.request.user,
                path=self.request.path,
                group_by_field=self._saved_filters["field"],
            ).first()
            if active_group:
                context["active_target"] = active_group.group_target

        queryset = self.get_queryset()

        if self.show_filter_tags:
            data_dict = parse_qs(self._saved_filters.urlencode())
            data_dict = get_key_instances(self.model, data_dict)
            keys_to_remove = [
                key
                for key, value in data_dict.items()
                if key in ["filter_applied", "nav_url"] + self.filter_keys_to_remove
            ]

            for key in (
                keys_to_remove + ["referrer", "nav_url"] + self.filter_keys_to_remove
            ):
                if key in data_dict.keys():
                    data_dict.pop(key)
            context["filter_dict"] = data_dict
            context["keys_to_remove"] = keys_to_remove

        request = self.request
        is_first_sort = False
        query_dict = self.request.GET
        if (
            not request.GET.get(self.sortby_key)
            and not self._saved_filters.get(self.sortby_key)
        ) or (
            not request.GET.get(self.sortby_key)
            and self._saved_filters.get(self.sortby_key)
        ):
            is_first_sort = True
            query_dict = self._saved_filters

        if query_dict.get(self.sortby_key):
            queryset = sortby(
                query_dict, queryset, self.sortby_key, is_first_sort=is_first_sort
            )

        ordered_ids = []
        if not self._saved_filters.get("field"):
            for instance in queryset:
                ordered_ids.append(instance.pk)
        self.request.session[self.ordered_ids_key] = ordered_ids
        context["queryset"] = paginator_qry(
            queryset, self._saved_filters.get("page"), self.records_per_page
        )

        if request and self._saved_filters.get("field"):
            field = self._saved_filters.get("field")
            self.template_name = "generic/group_by_table.html"
            if isinstance(queryset, Page):
                queryset = self.filter_class(
                    request.GET, queryset=queryset.object_list.model.objects.all()
                ).qs
            groups = group_by_queryset(
                queryset, field, self._saved_filters.get("page"), "page"
            )
            context["groups"] = paginator_qry(
                groups, self._saved_filters.get("page"), 10
            )

            # for group in context["groups"]:
            #     for instance in group["list"]:
            #         instance.ordered_ids = ordered_ids
            #         ordered_ids.append(instance.pk)

        # CACHE.get(self.request.session.session_key + "cbv")[HorillaListView] = context
        from horilla.urls import path, urlpatterns

        self.export_path = f"export-list-view-{get_short_uuid(4)}/"

        urlpatterns.append(path(self.export_path, self.export_data))
        context["export_path"] = self.export_path

        if self.import_fields:
            get_import_sheet_path = (
                f"get-import-sheet-{self.view_id}-{self.request.session.session_key}/"
            )
            post_import_sheet_path = (
                f"post-import-sheet-{self.view_id}-{self.request.session.session_key}/"
            )
            urlpatterns.append(
                path(
                    get_import_sheet_path,
                    self.serve_import_sheet,
                )
            )
            urlpatterns.append(
                path(
                    post_import_sheet_path,
                    self.import_records,
                )
            )
            context["get_import_sheet_path"] = get_import_sheet_path
            context["post_import_sheet_path"] = post_import_sheet_path
        context["import_fields"] = self.import_fields
        if self.bulk_update_fields and self.bulk_update_accessibility():
            get_bulk_path = (
                f"get-bulk-update-{self.view_id}-{self.request.session.session_key}/"
            )
            post_bulk_path = (
                f"post-bulk-update-{self.view_id}-{self.request.session.session_key}/"
            )
            self.post_bulk_path = post_bulk_path
            urlpatterns.append(
                path(
                    get_bulk_path,
                    self.serve_bulk_form,
                )
            )
            urlpatterns.append(
                path(
                    post_bulk_path,
                    self.handle_bulk_submission,
                )
            )
            context["bulk_update_fields"] = self.bulk_update_fields
            context["bulk_path"] = get_bulk_path
        context["export_formats"] = self.export_formats
        context["import_help"] = self.import_help
        context["import_accessibility"] = self.import_accessibility()
        return context

    def select_all(self, *args, **kwargs):
        """
        Select all method
        """
        return json.dumps(list(self.get_queryset().values_list("id", flat=True)))

    def export_data(self, *args, **kwargs):
        """
        Export list view visible columns
        """
        from import_export import fields, resources

        request = getattr(_thread_locals, "request", None)
        ids = eval_validate(request.POST["ids"])
        _columns = eval_validate(request.POST["columns"])
        export_format = request.POST.get("format", "xlsx")
        queryset = self.model.objects.filter(id__in=ids)

        _model = self.model

        class HorillaListViewResorce(resources.ModelResource):
            """
            Instant Resource class
            """

            id = fields.Field(column_name="ID")

            class Meta:
                """
                Meta class for additional option
                """

                model = _model
                fields = [field[1] for field in _columns]  # 773

            def dehydrate_id(self, instance):
                """
                Dehydrate method for id field
                """
                return instance.pk

            for field_tuple in _columns:
                dynamic_fn_str = f"def dehydrate_{field_tuple[1]}(self, instance):return self.remove_extra_spaces(getattribute(instance, '{field_tuple[1]}'),{field_tuple})"
                exec(dynamic_fn_str)
                dynamic_fn = locals()[f"dehydrate_{field_tuple[1]}"]
                locals()[field_tuple[1]] = fields.Field(column_name=field_tuple[0])

            def remove_extra_spaces(self, text, field_tuple):
                """
                Clean the text:
                - If it's a <select> element, extract the selected option's value.
                - If it's an <input> or <textarea>, extract its 'value'.
                - Otherwise, remove blank spaces, keep line breaks, and handle <li> tags.
                """
                soup = BeautifulSoup(str(text), "html.parser")

                # Handle <select> tag
                select_tag = soup.find("select")
                if select_tag:
                    selected_option = select_tag.find("option", selected=True)
                    if selected_option:
                        return selected_option["value"]
                    else:
                        first_option = select_tag.find("option")
                        return first_option["value"] if first_option else ""

                # Handle <input> tag
                input_tag = soup.find("input")
                if input_tag:
                    return input_tag.get("value", "")

                # Handle <textarea> tag
                textarea_tag = soup.find("textarea")
                if textarea_tag:
                    return textarea_tag.text.strip()

                # Default: clean normal text and <li> handling
                for li in soup.find_all("li"):
                    li.insert_before("\n")
                    li.unwrap()

                text = soup.get_text()
                lines = text.splitlines()
                non_blank_lines = [line.strip() for line in lines if line.strip()]
                cleaned_text = "\n".join(non_blank_lines)
                return cleaned_text

        book_resource = HorillaListViewResorce()

        # Export the data using the resource
        dataset = book_resource.export(queryset)

        # excel_data = dataset.export("xls")

        # Set the response headers
        # file_name = self.export_file_name
        # if not file_name:
        #     file_name = "quick_export"
        # response = HttpResponse(excel_data, content_type="application/vnd.ms-excel")
        # response["Content-Disposition"] = f'attachment; filename="{file_name}.xls"'
        # return response
        json_data = json.loads(dataset.export("json"))
        merged = []

        for item in _columns:
            # Check if item has exactly 2 elements
            if len(item) == 2:
                # Check if there's a matching (type, key) in export_fields (t, k, _)
                match_found = any(
                    export_item[0] == item[0] and export_item[1] == item[1]
                    for export_item in self.export_fields
                )

                if match_found:
                    # Find the first matching metadata or use {} as fallback
                    try:
                        metadata = next(
                            (
                                export_item[2]
                                for export_item in self.export_fields
                                if export_item[0] == item[0]
                                and export_item[1] == item[1]
                            ),
                            {},
                        )
                    except Exception as e:
                        merged.append(item)
                        continue

                    merged.append([*item, metadata])
                else:
                    merged.append(item)
            else:
                merged.append(item)
        columns = []
        for column in merged:
            if len(column) >= 3 and isinstance(column[2], dict):
                column = (column[0], column[0], column[2])
            elif len(column) >= 3:
                column = (column[0], column[1])
            columns.append(column)

        if export_format == "json":
            response = HttpResponse(
                json.dumps(json_data, indent=4), content_type="application/json"
            )
            response["Content-Disposition"] = (
                f'attachment; filename="{self.export_file_name}.json"'
            )
            return response
        # CSV
        elif export_format == "csv":
            csv_data = dataset.export("csv")
            response = HttpResponse(csv_data, content_type="text/csv")
            response["Content-Disposition"] = (
                f'attachment; filename="{self.export_file_name}.csv"'
            )
            return response
        elif export_format == "pdf":

            headers = dataset.headers
            rows = dataset.dict

            # Render to HTML using a template
            html_string = render_to_string(
                "generic/export_pdf.html",
                {
                    "headers": headers,
                    "rows": rows,
                },
            )

            # Convert HTML to PDF using xhtml2pdf
            result = io.BytesIO()
            pisa_status = pisa.CreatePDF(html_string, dest=result)

            if pisa_status.err:
                return HttpResponse("PDF generation failed", status=500)

            # Return response
            response = HttpResponse(result.getvalue(), content_type="application/pdf")
            response["Content-Disposition"] = (
                f'attachment; filename="{self.export_file_name}.pdf"'
            )
            return response
        return export_xlsx(json_data, columns, file_name=self.export_file_name)


class HorillaSectionView(TemplateView):
    """
    Horilla Template View
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        request = getattr(_thread_locals, "request", None)
        self.request = request
        # update_initial_cache(request, CACHE, HorillaListView)

    nav_url: str = ""
    view_url: str = ""

    # view container id is used to wrap the component view with th id
    view_container_id: str = ""

    script_static_paths: list = []
    style_static_paths: list = []

    template_name = "generic/horilla_section.html"

    def get_context_data(self, **kwargs) -> dict:
        context = super().get_context_data(**kwargs)
        context["nav_url"] = self.nav_url
        context["view_url"] = self.view_url
        context["view_container_id"] = self.view_container_id
        context["script_static_paths"] = self.script_static_paths
        context["style_static_paths"] = self.style_static_paths
        return context

    @classmethod
    def as_view(cls, **initkwargs):
        def view(request, *args, **kwargs):
            # Inject URL params into initkwargs
            initkwargs_with_url = {**initkwargs, **kwargs}
            self = cls(**initkwargs_with_url)
            self.request = request
            self.args = args
            self.kwargs = kwargs
            return self.dispatch(request, *args, **kwargs)

        return view


@method_decorator(hx_request_required, name="dispatch")
class HorillaDetailedView(DetailView):
    """
    HorillDetailedView
    """

    title = "Detailed View"
    template_name = "generic/horilla_detailed_view.html"
    header: dict = {
        "title": "Horilla",
        "subtitle": "Horilla Detailed View",
        "avatar": "",
    }
    body: list = []

    action_method: list = []
    actions: list = []
    cols: dict = {}
    instance = None
    empty_template = None

    ids_key: str = "instance_ids"

    def get_object(self, queryset=None):
        try:
            self.instance = super().get_object(queryset)
        except Exception as e:
            logger.error(f"Error getting object: {e}")
        return self.instance

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        if not self.instance and self.empty_template:
            return render(request, self.empty_template, context=self.get_context_data())
        elif not self.instance:
            messages.info(request, "No record found...")
            return HttpResponse("<script>window.location.reload()</script>")
        return response

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.ordered_ids_key = f"ordered_ids_{self.model.__name__.lower()}"
        request = getattr(_thread_locals, "request", None)
        self.request = request
        # update_initial_cache(request, CACHE, HorillaDetailedView)

    def get_context_data(self, **kwargs: Any):
        context = super().get_context_data(**kwargs)
        obj = context.get("object")

        if not obj:
            return context

        pk = obj.pk
        instance_ids = self.request.session.get(self.ordered_ids_key, [])
        url_info = resolve(self.request.path)
        url_name = url_info.url_name
        key = next(iter(url_info.kwargs), "pk")

        context["instance"] = obj
        context["title"] = self.title
        context["header"] = self.header
        context["body"] = self.body
        context["actions"] = self.actions
        context["action_method"] = self.action_method
        context["cols"] = self.cols

        if instance_ids:
            prev_id, next_id = closest_numbers(instance_ids, pk)
            context.update(
                {
                    "instance_ids": str(instance_ids),
                    "ids_key": self.ids_key,
                    "next_url": reverse(url_name, kwargs={key: next_id}),
                    "previous_url": reverse(url_name, kwargs={key: prev_id}),
                }
            )

            # Filter out instance_ids key from GET params
            get_params = self.request.GET.copy()
            get_params.pop(self.ids_key, None)
            context["extra_query"] = get_params.urlencode()
        else:
            context["extra_query"] = ""

        return context


@method_decorator(hx_request_required, name="dispatch")
class HorillaTabView(TemplateView):
    """
    HorillaTabView
    """

    view_id: str = get_short_uuid(3, "htv")
    template_name = "generic/horilla_tabs.html"
    show_filter_tags = False

    tabs: list = []

    @classmethod
    def as_view(cls, **initkwargs):
        def view(request, *args, **kwargs):
            # Inject URL params into initkwargs
            initkwargs_with_url = {**initkwargs, **kwargs}
            self = cls(**initkwargs_with_url)
            self.request = request
            self.args = args
            self.kwargs = kwargs
            return self.dispatch(request, *args, **kwargs)

        return view

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        request = getattr(_thread_locals, "request", None)
        self.request = request
        self.query_params = {}
        # update_initial_cache(request, CACHE, HorillaTabView)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.user:
            active_tab = models.ActiveTab.objects.filter(
                created_by=self.request.user, path=self.request.path
            ).first()
            if active_tab:
                context["active_target"] = active_tab.tab_target

        for tab in self.tabs:
            base_url = tab.get("url")
            query_params = {**self.request.GET.dict()}
            query_params.update(self.query_params)

            tab["url"] = f"{base_url}?{urlencode(query_params)}"

        context["tabs"] = self.tabs
        context["view_id"] = self.view_id

        # CACHE.get(self.request.session.session_key + "cbv")[HorillaTabView] = context

        return context


@method_decorator(hx_request_required, name="dispatch")
class HorillaCardView(ListView):
    """
    HorillaCardView
    """

    filter_class: FilterSet = None

    view_id: str = get_short_uuid(4, prefix="hcv")

    template_name = "generic/horilla_card.html"
    context_object_name = "queryset"

    search_url: str = ""

    details: dict = {}
    """
    eg:
    def accessibility(
        request, instance: object = None, user_perms: PermWrapper = [], *args, **kwargs
    )->bool:
        # True if accessible to the action else False
        return True

    actions = [
        {
            "action": "Edit",
            "accessibility": "path_to_your.accessibility", # path to your accessibility method
            "attrs": '''{instance_attributes_called_like_this}''',
        },
        etc..
    ]
    """
    actions: list = []

    card_attrs: str = """"""

    show_filter_tags: bool = True
    filter_keys_to_remove: list = []

    records_per_page: int = 50
    card_status_class: str = """"""
    card_status_indications: list = []

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        request = getattr(_thread_locals, "request", None)
        self.request = request
        # update_initial_cache(request, CACHE, HorillaCardView)
        self._saved_filters = QueryDict()
        self.ordered_ids_key = f"ordered_ids_{self.model.__name__.lower()}"

    def get_queryset(self):
        if not self.queryset:
            queryset = super().get_queryset()
            if self.filter_class:
                query_dict = self.request.GET
                if "filter_applied" in query_dict.keys():
                    update_saved_filter_cache(self.request, CACHE)
                elif CACHE.get(
                    str(self.request.session.session_key) + self.request.path + "cbv"
                ):
                    query_dict = CACHE.get(
                        str(self.request.session.session_key)
                        + self.request.path
                        + "cbv"
                    )["query_dict"]

                self._saved_filters = query_dict
                self.request.exclude_filter_form = True
                self.queryset = self.filter_class(
                    query_dict, queryset, request=self.request
                ).qs
                default_filter = models.SavedFilter.objects.filter(
                    path=self.request.path,
                    created_by=self.request.user,
                    is_default=True,
                ).first()
                if not bool(query_dict) and default_filter:
                    data = eval_validate(default_filter.filter)
                    query_dict = QueryDict("", mutable=True)
                    for key, value in data.items():
                        query_dict[key] = value

                    query_dict._mutable = False

        return self.queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        queryset = self.get_queryset()

        context["view_id"] = self.view_id
        context["search_url"] = self.search_url
        context["card_attrs"] = self.card_attrs
        context["actions"] = self.actions
        context["details"] = self.details
        context["show_filter_tags"] = self.show_filter_tags
        context["card_status_class"] = self.card_status_class
        context["card_status_indications"] = self.card_status_indications

        if self.show_filter_tags:
            data_dict = parse_qs(self._saved_filters.urlencode())
            data_dict = get_key_instances(self.model, data_dict)
            keys_to_remove = [
                key
                for key, value in data_dict.items()
                if value[0] in ["unknown", "on"] + self.filter_keys_to_remove
            ]

            for key in (
                keys_to_remove + ["referrer", "nav_url"] + self.filter_keys_to_remove
            ):
                if key in data_dict.keys():
                    data_dict.pop(key)

            context["filter_dict"] = data_dict

        ordered_ids = list(queryset.values_list("id", flat=True))
        ordered_ids = []
        if not self._saved_filters.get("field"):
            for instance in queryset:
                ordered_ids.append(instance.pk)
        self.request.session[self.ordered_ids_key] = ordered_ids

        # CACHE.get(self.request.session.session_key + "cbv")[HorillaCardView] = context
        referrer = self.request.GET.get("referrer", "")
        if referrer:
            # Remove the protocol and domain part
            referrer = "/" + "/".join(referrer.split("/")[3:])
        context["stored_filters"] = (
            models.SavedFilter.objects.filter(
                path=self.request.path, created_by=self.request.user
            )
            | models.SavedFilter.objects.filter(
                referrer=referrer, created_by=self.request.user
            )
        ).distinct()
        context["queryset"] = paginator_qry(
            queryset, self.request.GET.get("page"), self.records_per_page
        )
        return context

    @classmethod
    def as_view(cls, **initkwargs):
        def view(request, *args, **kwargs):
            # Inject URL params into initkwargs
            initkwargs_with_url = {**initkwargs, **kwargs}
            self = cls(**initkwargs_with_url)
            self.request = request
            self.args = args
            self.kwargs = kwargs
            return self.dispatch(request, *args, **kwargs)

        return view


@method_decorator(hx_request_required, name="dispatch")
class ReloadMessages(TemplateView):
    """
    Reload messages
    """

    template_name = "generic/messages.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context


def save(self: forms.ModelForm, commit=True, *args, **kwargs):
    """
    This method is used to super save the form using custom logic
    """
    request = getattr(_thread_locals, "request", None)

    dynamic_field = request.GET["dynamic_field"]
    response = None
    if commit:
        response = super(type(self), self).save(*args, **kwargs)
        new_isntance_pk = self.instance.pk
        CACHE.set(
            request.session.session_key + "cbv" + dynamic_field,
            {
                "dynamic_field": dynamic_field,
                "value": new_isntance_pk,
                "model": self._meta.model,
            },
        )
    return response


@method_decorator(hx_request_required, name="dispatch")
class HorillaFormView(FormView):
    """
    HorillaFormView
    """

    class HttpResponse:
        """
        HttpResponse
        """

        def __new__(
            self, content: str = "", targets_to_reload: list = [], script: str = ""
        ) -> HttpResponse:
            """
            __new__ method
            """
            targets_to_reload = list(set(targets_to_reload))
            targets_to_reload.append("#reloadMessagesButton")
            script_id = get_short_uuid(4)
            script = (
                f"<script id='scriptTarget{script_id}'>"
                + "{}".format(
                    "".join([f"$(`{target}`).click();" for target in targets_to_reload])
                )
                + f"$('#scriptTarget{script_id}').closest('.oh-modal--show').first().removeClass('oh-modal--show');"
                + "$('.reload-record').click();"
                + "$('.reload-field').click();"
                + script
                + "</script>"
            )

            reload_response = HttpResponse(script).content

            user_response = HttpResponse(content).content
            response = HttpResponse(reload_response + user_response)
            self = response
            return response

    model: object = None
    view_id: str = get_short_uuid(4)
    hx_confirm: str = ""
    form_class: forms.ModelForm = None
    template_name = "generic/horilla_form.html"
    ids_key: str = "instance_ids"
    form_disaply_attr: str = ""
    new_display_title: str = "Add New"
    close_button_attrs: str = """"""
    submit_button_attrs: str = """"""

    # NOTE: Dynamic create view's forms save method will be overwritten
    is_dynamic_create_view: bool = False
    # [(field_name,DynamicFormView,[other_field1,...])] # other_fields
    # can be mentioned like this to pass the field selected
    dynamic_create_fields: list = []

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        request = getattr(_thread_locals, "request", None)
        self.ordered_ids_key = f"ordered_ids_{self.model.__name__.lower()}"
        self.request = request
        if not self.success_url:
            self.success_url = self.request.path
        # update_initial_cache(request, CACHE, HorillaFormView)

        if self.form_class:
            setattr(self.form_class, "structured", structured)

    def get(
        self, request: HttpRequest, *args: str, pk=None, **kwargs: Any
    ) -> HttpResponse:
        _pk = pk
        response = super().get(request, *args, **kwargs)
        return response

    def post(
        self, request: HttpRequest, *args: str, pk=None, **kwargs: Any
    ) -> HttpResponse:
        _pk = pk
        self.get_form()
        response = super().post(request, *args, **kwargs)
        return response

    def init_form(self, *args, data={}, files={}, instance=None, **kwargs):
        """
        method where first the form where initialized
        """
        self.form_class: forms.ModelForm

        form = self.form_class(
            data, files, instance=instance, initial=self.get_initial()
        )
        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        self.form_class_path = (
            self.get_form().__class__.__module__ + "." + self.form.__class__.__name__
        )

        context["dynamic_create_fields"] = self.dynamic_create_fields
        context["form_class_path"] = self.form_class_path
        context["view_id"] = self.view_id
        context["hx_confirm"] = self.hx_confirm
        context["hx_target"] = self.request.META.get("HTTP_HX_TARGET", "this")
        pk = None
        if self.form.instance:
            pk = self.form.instance.pk
        # next/previous option in the forms
        if pk and self.request.GET.get(self.ids_key):
            instance_ids = self.request.session.get(self.ordered_ids_key, [])
            url = resolve(self.request.path)
            key = list(url.kwargs.keys())[0]
            url_name = url.url_name
            if instance_ids:
                previous_id, next_id = closest_numbers(instance_ids, pk)

                next_url = reverse(url_name, kwargs={key: next_id})
                previous_url = reverse(url_name, kwargs={key: previous_id})

                self.form.instance_ids = str(instance_ids)
                self.form.ids_key = self.ids_key

                self.form.next_url = next_url
                self.form.previous_url = previous_url
        return context

    def get_queryset(self):
        """
        method to get the instance for the form
        """
        pk = self.kwargs.get("pk")
        return self.model.objects.filter(pk=pk).first()

    def get_form(self, form_class=None):

        pk = self.kwargs.get("pk")
        if not hasattr(self, "form"):
            instance = self.get_queryset()
            data = None
            files = None
            if self.request.method == "POST":
                data = self.request.POST
                files = self.request.FILES
            form = self.init_form(data=data, files=files, instance=instance)
            if self.is_dynamic_create_view:
                # setattr(type(form), "save", save)
                from types import MethodType

                form.save = MethodType(save, form)

            if self.request.method == "GET":
                [
                    (
                        "employee_id",
                        FormView,
                    )
                ]
                for dynamic_tuple in self.dynamic_create_fields:
                    view = dynamic_tuple[1]
                    view.display_title = "Dynamic create"
                    field = dynamic_tuple[0]
                    additional_data_fields = []
                    if len(dynamic_tuple) == 3:
                        additional_data_fields = dynamic_tuple[2]
                    key = self.request.session.session_key + "cbv" + field
                    field_instance = form.instance._meta.get_field(field)
                    value = form.initial.get(field, [])

                    form_field = forms.ChoiceField
                    if isinstance(field_instance, models.models.ManyToManyField):
                        form_field = forms.MultipleChoiceField
                        if form.instance.pk is not None:
                            value = list(
                                getattr(form.instance, field).values_list(
                                    "id", flat=True
                                )
                            )
                    else:
                        value = getattr(getattribute(form.instance, field), "pk", value)
                    CACHE.set(
                        key,
                        {
                            "dynamic_field": field,
                            "value": value,
                            "model": form._meta.model,
                        },
                    )

                    from django.urls import path

                    from horilla.urls import urlpatterns

                    urlpatterns.append(
                        path(
                            f"dynamic-path-{field}-{self.request.session.session_key}",
                            view.as_view(),
                            name=f"dynamic-path-{field}-{self.request.session.session_key}",
                        )
                    )
                    queryset = form.fields[field].queryset
                    choices = [(instance.id, instance) for instance in queryset]
                    choices.insert(0, ("", "Select option"))
                    choices.append(("dynamic_create", "Dynamic create"))
                    attrs = form.fields[field].widget.attrs
                    for data_field in additional_data_fields:

                        data_field_attr = form.fields[data_field].widget.attrs
                        if (
                            f"$('#modalButton{field}Form [name={data_field}]').val(this.value);"
                            not in data_field_attr.get("onchange", "")
                        ):
                            data_field_attr["onchange"] = (
                                data_field_attr.get("onchange", "")
                                + f"""
                                if(this.value != 'dynamic_create'){{
                                $('#modalButton{field}Form [name={data_field}]').val(this.value);
                                }}
                            """
                            )

                    form.fields[field] = form_field(
                        choices=choices,
                        label=form.fields[field].label,
                        required=form.fields[field].required,
                    )
                    form.fields[field].widget.option_template_name = (
                        "horilla_widgets/select_option.html",
                    )
                    form.fields[field].widget.attrs = attrs
                    form.initial[field] = value
                for dynamic_tuple in self.dynamic_create_fields:
                    field = dynamic_tuple[0]
                    onchange = form.fields[field].widget.attrs.get("onchange", "")
                    if onchange:
                        CACHE.set(
                            self.request.session.session_key
                            + "cbv"
                            + field
                            + "onchange",
                            onchange,
                        )

            if pk:
                form.instance = instance
                title = str(instance)
                if self.form_disaply_attr:
                    title = getattribute(instance, self.form_disaply_attr)
                if instance:
                    self.form_class.verbose_name = title
            else:
                self.form_class.verbose_name = self.new_display_title
            form.close_button_attrs = self.close_button_attrs
            form.submit_button_attrs = self.submit_button_attrs
            # CACHE.get(self.request.session.session_key + "cbv")[HorillaFormView] = form
            self.form = form
        return self.form

    @classmethod
    def as_view(cls, **initkwargs):
        def view(request, *args, **kwargs):
            # Inject URL params into initkwargs
            initkwargs_with_url = {**initkwargs, **kwargs}
            self = cls(**initkwargs_with_url)
            self.request = request
            self.args = args
            self.kwargs = kwargs
            return self.dispatch(request, *args, **kwargs)

        return view


@method_decorator(hx_request_required, name="dispatch")
class HorillaNavView(TemplateView):
    """
    HorillaNavView

    filter form submit button id: applyFilter
    """

    template_name = "generic/horilla_nav.html"

    nav_title: str = ""
    search_url: str = ""
    search_swap_target: str = ""
    search_input_attrs: str = ""
    search_in: list = []
    actions: list = []
    group_by_fields: list = []
    filter_form_context_name: str = ""
    filter_instance: FilterSet = None
    filter_instance_context_name: str = ""
    filter_body_template: str = ""
    empty_inputs: list = []
    view_types: list = []
    create_attrs: str = """"""
    apply_first_filter = True

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._initialize_model_and_group_fields()
        request = getattr(_thread_locals, "request", None)
        self.request = request
        # update_initial_cache(request, CACHE, HorillaNavView)

    def _initialize_model_and_group_fields(self) -> None:
        """
        Initialize model_class and reinitialize filter_instance if model exists
        for updating group_by_fields with verbose names.
        """
        if not self.filter_instance:
            return

        model_class_ref = self.filter_instance._meta.model
        if not model_class_ref:
            return

        model_instance = model_class_ref()
        self.nav_title = self.nav_title or model_instance._meta.verbose_name_plural
        try:
            self.filter_instance = self.filter_instance.__class__()
        except:
            pass

        if not self.group_by_fields:
            return

        get_field = model_instance._meta.get_field
        updated_fields = []
        append = updated_fields.append

        for field in self.group_by_fields:
            if isinstance(field, str):
                try:
                    verbose_name = get_field(field).verbose_name
                    append((field, verbose_name))
                except FieldDoesNotExist:
                    # Check for related fields (field paths with '__')
                    if "__" in field and hasattr(
                        model_class_ref, "get_verbose_name_related_field"
                    ):
                        try:
                            verbose_name = (
                                model_class_ref.get_verbose_name_related_field(field)
                            )
                            append((field, verbose_name))
                            continue
                        except Exception as e:
                            pass
                    append(field)
            else:
                append(field)

        self.group_by_fields = updated_fields

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["nav_title"] = self.nav_title
        context["search_url"] = self.search_url
        context["search_swap_target"] = self.search_swap_target
        context["search_input_attrs"] = self.search_input_attrs
        context["group_by_fields"] = self.group_by_fields
        context["actions"] = self.actions
        context["filter_body_template"] = self.filter_body_template
        context["view_types"] = self.view_types
        context["create_attrs"] = self.create_attrs
        context["search_in"] = self.search_in
        context["apply_first_filter"] = self.apply_first_filter
        context["filter_instance_context_name"] = self.filter_instance
        last_filter = CACHE.get(
            self.request.session.session_key
            + "last-applied-filter"
            + self.request.path,
            {},
        )
        context["empty_inputs"] = self.empty_inputs + ["nav_url"]
        context["last_filter"] = dict(last_filter)
        if self.filter_instance:
            context[self.filter_form_context_name] = self.filter_instance.form
        context["active_view"] = models.ActiveView.objects.filter(
            path=self.request.path
        ).first()
        # CACHE.get(self.request.session.session_key + "cbv")[HorillaNavView] = context
        return context

    @classmethod
    def as_view(cls, **initkwargs):
        def view(request, *args, **kwargs):
            # Inject URL params into initkwargs
            initkwargs_with_url = {**initkwargs, **kwargs}
            self = cls(**initkwargs_with_url)
            self.request = request
            self.args = args
            self.kwargs = kwargs
            return self.dispatch(request, *args, **kwargs)

        return view


@method_decorator(hx_request_required, name="dispatch")
class HorillaProfileView(DetailView):
    """
    GenericHorillaProfileView
    """

    template_name = "generic/horilla_profile_view.html"
    view_id: str = None
    filter_class: FilterSet = None
    push_url: str = None
    key_name: str = "pk"

    # add these method under the model
    # get_avatar --> image/profile
    # get_subtitle --> Job position

    actions: list = []

    tabs: list = []

    def __init__(self, **kwargs: Any) -> None:
        self.url_prefix = str(self.__class__.__name__.lower())
        if not self.view_id:
            self.view_id = get_short_uuid(4)
        super().__init__(**kwargs)

        request = getattr(_thread_locals, "request", None)
        self.request = request
        self.ordered_ids_key = f"ordered_ids_{self.model.__name__.lower()}"
        # update_initial_cache(request, CACHE, HorillaProfileView)

        from horilla.urls import path, urlpatterns

        for tab in self.tabs:
            if not tab.get("url"):
                url = f"{self.url_prefix}-{tab['title']}"
                urlpatterns.append(
                    path(
                        url + "/<int:pk>/",
                        tab["view"],
                    )
                )
                tab["url"] = "/" + url + "/{pk}/"

        # hidden columns configuration

        existing_instance = models.ToggleColumn.objects.filter(
            user_id=request.user, path=request.path_info
        ).first()

        self.visible_tabs = self.tabs.copy()

        self.tabs_list = [(tab["title"], tab["title"]) for tab in self.visible_tabs]

        hidden_tabs = (
            [] if not existing_instance else existing_instance.excluded_columns
        )
        self.toggle_form = ToggleColumnForm(
            self.tabs_list,
            hidden_tabs,
            hidden_fields=[],
        )
        for column in self.tabs_list:
            if column[1] in hidden_tabs:
                for tab in self.visible_tabs:
                    if tab["title"] == column[1]:
                        self.visible_tabs.remove(tab)

    @classmethod
    def add_tab(cls, tab: dict = None, index: int = None, tabs: list = None) -> None:
        """
        Tab adding method
        example tab arg look like
        tab = {
            "title":"About",
            "view" : views.about_tab,
            "accessibility": "path_to_your.accessibility", # path to your accessibility method

        }
        tabs = [tab,etc...]

        add_tab(tabs=tabs) / add_tab(tab=tab)
        """
        if tabs:
            cls.tabs = cls.tabs + tabs
        if tab:
            if index is None:
                cls.tabs.append(tab)
                return
            cls.tabs.index(index, tab)

    @classmethod
    def as_view(cls, **initkwargs):
        def view(request, *args, **kwargs):
            # Inject URL params into initkwargs
            initkwargs_with_url = {**initkwargs, **kwargs}
            self = cls(**initkwargs_with_url)
            self.request = request
            self.args = args
            self.kwargs = kwargs
            return self.dispatch(request, *args, **kwargs)

        return view

    def get_context_data(self, **kwargs: Any) -> dict:
        context = super().get_context_data(**kwargs)
        context["instance"] = context["object"]
        context["tabs"] = self.tabs
        context["visible_tabs"] = self.visible_tabs
        context["toggle_form"] = self.toggle_form
        context["view_id"] = self.view_id
        active_tab = models.ActiveTab.objects.filter(
            created_by=self.request.user, path=self.request.path
        ).first()
        if active_tab:
            context["active_target"] = active_tab.tab_target

        instance_ids = self.request.session.get(self.ordered_ids_key, [])

        if instance_ids:
            CACHE.set(
                f"{self.request.session.session_key}hpv-instance-ids", instance_ids
            )
        else:
            instance_ids = CACHE.get(
                f"{self.request.session.session_key}hpv-instance-ids"
            )
            instance_ids = instance_ids if instance_ids else []
        instances = self.model.objects.filter(id__in=instance_ids)
        context["instances"] = instances
        balance_count = instances.count() - 6
        if balance_count > 9:
            display_count = "9+"
        elif 1 < balance_count <= 9:
            display_count = f"{balance_count-1}+"
        else:
            display_count = None

        previous_id, next_id = closest_numbers(instance_ids, context["instance"].pk)
        url = resolve(self.request.path)
        key = list(url.kwargs.keys())[0]

        url_name = url.url_name
        next_url = reverse(url_name, kwargs={key: next_id})
        previous_url = reverse(url_name, kwargs={key: previous_id})
        push_url_next = reverse(self.push_url, kwargs={self.key_name: next_id})
        push_url_prev = reverse(self.push_url, kwargs={self.key_name: previous_id})
        context["instance_ids"] = str(instance_ids)
        if instance_ids:
            context["next_url"] = next_url
            context["previous_url"] = previous_url
            context["push_url_next"] = push_url_next
            context["push_url_prev"] = push_url_prev

        context["display_count"] = display_count
        context["actions"] = self.actions
        context["filter_class"] = self.filter_class
        cache = {
            "instances": context["instances"],
            "instance_ids": context["instance_ids"],
            "filter_class": context["filter_class"],
            "view_id": context["view_id"],
            "object": context["object"],
        }
        CACHE.set(f"{self.request.session.session_key}search_in_instance_ids", cache)
        return context
