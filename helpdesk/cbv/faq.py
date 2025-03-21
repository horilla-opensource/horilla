"""
This page handles the cbv methods for faq page
"""

from django.contrib import messages
from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _

from base.forms import TagsForm
from base.models import Tags
from helpdesk.cbv.tags import DynamicTagsCreateFormView
from helpdesk.forms import FAQCategoryForm, FAQForm
from helpdesk.models import FAQ, FAQCategory
from horilla_views.cbv_methods import login_required, permission_required
from horilla_views.generic.cbv.views import HorillaFormView


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required("helpdesk_addfaqcategory"), name="dispatch")
class FaqCategoryCreateFormView(HorillaFormView):
    """
    form view for create and update faq categories
    """

    form_class = FAQCategoryForm
    model = FAQCategory
    new_display_title = _("FAQ category Create")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.form.instance.pk:
            self.form_class.verbose_name = _("FAQ category Update")

        return context

    def form_valid(self, form: FAQCategoryForm) -> HttpResponse:
        if form.is_valid():
            if form.instance.pk:
                message = _("The FAQ category updated successfully.")
            else:
                message = _("The FAQ Category created successfully.")
            form.save()

            messages.success(self.request, _(message))
            return self.HttpResponse("<script>location.reload();</script>")
        return super().form_valid(form)


# class DynamicFaqTagCreate(HorillaFormView):
#     """
#     form view for dynamic creation of tags
#     """

#     model = Tags
#     form_class = TagsForm
#     new_display_title = _("Create Tags")
#     is_dynamic_create_view = True

#     def form_valid(self, form: TagsForm) -> HttpResponse:

#         if form.is_valid():
#             message = _("Tag Created")
#             messages.success(self.request, _(message))
#             form.save()
#             return self.HttpResponse()
#         return super().form_valid(form)


class FaqCreateFormView(HorillaFormView):
    """
    form view for create and update faqs
    """

    model = FAQ
    form_class = FAQForm
    new_display_title = _("FAQ Create")
    dynamic_create_fields = [("tags", DynamicTagsCreateFormView)]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        category = self.kwargs.get("cat_id")
        self.form.fields["category"].initial = category
        if self.form.instance.pk:
            self.form_class.verbose_name = _("FAQ Update")
        context["form"] = self.form
        return context

    def form_valid(self, form: FAQForm) -> HttpResponse:
        if form.is_valid():
            if form.instance.pk:
                messages.success(self.request, _("The FAQ updated successfully."))
            else:
                messages.success(self.request, _("The FAQ created successfully."))
            form.save()

            return self.HttpResponse("<script>location.reload();</script>")
        return super().form_valid(form)
