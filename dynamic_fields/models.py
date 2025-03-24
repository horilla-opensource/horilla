import logging
import re

from django import forms
from django.core.management import call_command
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from dynamic_fields.df_not_allowed_models import DF_NOT_ALLOWED_MODELS
from horilla.horilla_middlewares import _thread_locals
from horilla_automations.methods.methods import get_model_class

logger = logging.getLogger(__name__)


# Create your models here.
FIELD_MAP = {
    "1": models.CharField,
    "2": models.IntegerField,
    "3": models.TextField,
    "4": models.DateField,
    "5": models.FileField,
}

# Define the additional arguments for specific fields
ARGS = {
    "1": {"max_length": 30, "default": None},
    "2": {"default": 0},
    "3": {"default": None},
    "4": {"default": timezone.now},
    "5": {"null": True, "upload_to": "media/dynamic_fields"},
}


TYPE = (
    ("1", "Character field"),
    ("2", "Integer field"),
    ("3", "Text field"),
    ("4", "Date field"),
    ("5", "File field"),
)


class Choice(models.Model):
    """
    Choice
    """

    title = models.CharField(max_length=25)

    def __str__(self):
        return self.title


class DynamicField(models.Model):
    """
    DynamicFields
    """

    model = models.CharField(max_length=100)
    verbose_name = models.CharField(max_length=30)
    field_name = models.CharField(max_length=30, editable=False)
    type = models.CharField(max_length=50, choices=TYPE)
    choices = models.ManyToManyField(Choice, blank=True)
    is_required = models.BooleanField(default=False)
    remove_column = models.BooleanField(default=False)

    class Meta:
        """
        Meta class to additional options
        """

        unique_together = ("model", "field_name")

    def delete(self, *args, **kwargs):
        self.remove_column = True
        self.save()
        return

    def __str__(self):
        return f"{self.field_name} | {self.model}"

    def get_field(self):
        """
        Field generate method
        """

        def _args(key):
            args = ARGS.get(key, {})
            args["blank"] = not self.is_required
            args["verbose_name"] = self.verbose_name
            args["null"] = True
            return args

        field_object: models.CharField = {
            key: FIELD_MAP[key](**_args(key)) for key in FIELD_MAP
        }[self.type]
        if self.choices.exists() and self.type == "1":
            choices = [(choice.pk, choice.title) for choice in self.choices.all()]
            field_object.choices = choices
        field_object.remove_column = self.remove_column
        return field_object

    def get_model(self):
        """
        method to get the model
        """
        return get_model_class(self.model)

    def clean(self):
        """
        Clean method to write the validations
        """
        if not re.match(r"^[a-zA-Z]+( [a-zA-Z]+)*$", self.verbose_name):
            raise forms.ValidationError(
                {
                    "verbose_name": _(
                        "Name can only contain alphabetic characters,\
                              and multiple spaces are not allowed."
                    )
                }
            )
        field_name = "hdf_" + self.verbose_name.lower().replace(" ", "_")
        request = getattr(_thread_locals, "request", None)
        model = self.model
        if not model and request:
            model = request.GET.get("df_model_path", "")
        if model:
            records = DynamicField.objects.filter(model=model).values_list(
                "field_name", flat=True
            )
            if not self.pk and field_name in records:
                raise forms.ValidationError(
                    {"verbose_name": _("Please enter different name")}
                )
            elif field_name in records.exclude(pk=self.id):
                raise forms.ValidationError(
                    {"verbose_name": _("Please enter different name")}
                )

        return super().clean()

    def save(self, *args, **kwargs):
        # instance = self
        is_create = self.pk is None
        # hdf -> horilla_dynamic_field
        field_name = "hdf_" + self.verbose_name.lower().replace(" ", "_")

        if is_create:
            self.field_name = field_name
            super().save(*args, **kwargs)
            call_command("add_field", *(self.pk,))

        else:
            instance = DynamicField.objects.get(pk=self.pk)
            model = instance.get_model()
            field = instance.get_field()
            if self.remove_column:
                try:
                    field_to_remove = instance.field_name
                    if hasattr(model, field_to_remove):
                        # Dynamically remove the field
                        model._meta.local_fields = [
                            field
                            for field in model._meta.local_fields
                            if field.name != field_to_remove
                        ]
                        setattr(model, instance.field_name, None)

                        logger.info(f"Field '{field_to_remove}' removed successfully.")
                except Exception as e:
                    logger.info(e)
            super().save(*args, **kwargs)
        return self


DF_NOT_ALLOWED_MODELS += [
    DynamicField,
]
