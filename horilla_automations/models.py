from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _trans

from base.methods import eval_validate
from base.models import HorillaMailTemplate
from employee.models import Employee
from horilla.models import HorillaModel
from horilla_views.cbv_methods import render_template

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
    SEND_OPTIONS = [
        ("email", "Send as Email"),
        ("notification", "Send as Notification"),
        ("both", "Send as Email and Notification"),
    ]

    title = models.CharField(max_length=256, unique=True)
    method_title = models.CharField(max_length=100, editable=False)
    model = models.CharField(max_length=100, choices=MODEL_CHOICES, null=False)
    mail_to = models.TextField(verbose_name="Mail to/Notify to")
    mail_details = models.CharField(
        max_length=250,
        help_text=_trans(
            "Fill mail template details(reciever/instance, `self` will be the person who trigger the automation), `As template` option will sent instead of the mail template"
        ),
    )
    mail_detail_choice = models.TextField(default="", editable=False)
    trigger = models.CharField(max_length=10, choices=choices)
    # udpate the on_update logic to if and only if when
    # changes in the previous and current value
    mail_template = models.ForeignKey(
        HorillaMailTemplate, on_delete=models.CASCADE, null=True, blank=True
    )
    also_sent_to = models.ManyToManyField(
        Employee,
        blank=True,
        verbose_name=_trans("Also Send to"),
    )
    delivery_channel = models.CharField(
        default="email",
        max_length=50,
        choices=SEND_OPTIONS,
        verbose_name=_trans("Choose Delivery Channel"),
    )
    template_attachments = models.ManyToManyField(
        HorillaMailTemplate,
        related_name="template_attachment",
        blank=True,
    )
    condition_html = models.TextField(null=True, editable=False)
    condition_querystring = models.TextField(null=True, editable=False)

    condition = models.TextField()

    xss_exempt_fields = [
        "condition_html",
        "condition",
        "condition_querystring",
    ]

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
        mail_to = eval_validate(self.mail_to)
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

    def get_mail_cc_display(self):
        employees = self.also_sent_to.all()
        return render_template(
            "horilla_automations/mail_cc.html", {"employees": employees}
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
