from typing import Any
from django.conf import settings
from django.db import models
from django.urls import reverse
from horilla.models import HorillaModel
from django.utils.translation import gettext_lazy as _trans
from horilla_automations.methods.methods import get_related_models
from employee.models import Employee
from horilla_views.cbv_methods import render_template
from recruitment.models import RecruitmentMailTemplate

MODEL_CHOICES = []

CONDITIONS = [
    ("equal", _trans("Equal (==)")),
    ("notequal", _trans("Not Equal (!=)")),
    ("lt", _trans("Less Than (<)")),
    ("gt", _trans("Greater Than (>)")),
    ("le", _trans("Less Than or Equal To (<=)")),
    ("ge", _trans("Greater Than or Equal To (>=)")),
    ("icontains", _trans("Contains")),
]


class MailAutomation(HorillaModel):
    """
    MailAutoMation
    """

    choices = [
        ("on_create", "On Create"),
        ("on_update", "On Update"),
        ("on_delete", "On Delete"),
    ]
    title = models.CharField(max_length=50, unique=True)
    method_title = models.CharField(max_length=50, editable=False)
    model = models.CharField(max_length=100, choices=MODEL_CHOICES, null=False)
    mail_to = models.TextField(verbose_name="Mail to")
    mail_details = models.CharField(
        max_length=250,
        help_text="Fill mail template details(reciever/instance, `self` will be the person who trigger the automation)",
    )
    mail_detail_choice = models.TextField(default="", editable=False)
    trigger = models.CharField(max_length=10, choices=choices)
    # udpate the on_update logic to if and only if when
    # changes in the previous and current value
    mail_template = models.ForeignKey(RecruitmentMailTemplate, on_delete=models.CASCADE)
    template_attachments = models.ManyToManyField(
        RecruitmentMailTemplate,
        related_name="template_attachment",
        blank=True,
    )
    condition_html = models.TextField(null=True, editable=False)
    condition_querystring = models.TextField(null=True, editable=False)

    condition = models.TextField()

    def save(self, *args, **kwargs):
        if not self.pk:
            self.method_title = self.title.replace(" ", "_").lower()
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.title

    def get_avatar(self):
        """
        Method will retun the api to the avatar or path to the profile image
        """
        url = f"https://ui-avatars.com/api/?name={self.title}&background=random"

        return url

    def get_mail_to_display(self):
        """
        method that returns the display value for `mail_to`
        field
        """
        mail_to = eval(self.mail_to)
        mappings = []
        for mapping in mail_to:
            mapping = mapping.split("__")
            display = ""
            for split in mapping:
                split = split.replace("_id", "").replace("_", " ")
                split = split.capitalize()
                display = display + f"{split} >"
            display = display[:-1]
            mappings.append(display)
        return render_template(
            "horilla_automations/mail_to.html", {"instance": self, "mappings": mappings}
        )

    def detailed_url(self):
        return reverse("automation-detailed-view", kwargs={"pk": self.pk})

    def conditions(self):
        return render_template(
            "horilla_automations/conditions.html", {"instance": self}
        )

    def delete_url(self):
        return reverse("delete-automation", kwargs={"pk": self.pk})

    def edit_url(self):
        """
        Edit url
        """
        return reverse("update-automation", kwargs={"pk": self.pk})

    def trigger_display(self):
        """"""
        return self.get_trigger_display()
