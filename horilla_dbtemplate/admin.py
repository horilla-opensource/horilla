"""
Admin for horilla_dbtemplate.

Features exposed in Django admin:
- Rich change form with syntax validation on save (via model.clean())
- Inline version history table with per-row "Restore" button
- Side-by-side diff view comparing any two versions
- Live preview panel (renders the template with a dummy context in an iframe)
- Edit-lock: warns when another user is already editing, provides force-unlock action
- Scheduling: active_from / active_until fields with clear UI
- Usage analytics (access_count, last_accessed_at) displayed read-only
- Admin actions: invalidate cache, repopulate cache, check syntax, archive, activate,
  export as JSON fixture, force unlock
- Custom list display with state badge, lock indicator, schedule status
"""

import difflib

from django import forms
from django.contrib import admin, messages
from django.core.serializers import serialize
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.template import Context
from django.template import Template as DjangoTemplate
from django.template import TemplateSyntaxError
from django.urls import path, reverse
from django.utils.html import escape, format_html
from django.utils.safestring import mark_safe
from django.utils.timezone import localtime, now
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext

from .models import STATE_ACTIVE, STATE_ARCHIVED, STATE_DRAFT, Template, TemplateVersion
from .utils.cache import add_template_to_cache, remove_cached_template
from .utils.template import check_template_syntax

# ---------------------------------------------------------------------------
# Forms
# ---------------------------------------------------------------------------


class TemplateAdminForm(forms.ModelForm):
    """ModelForm with a wide content textarea and tag helper."""

    content = forms.CharField(
        widget=forms.Textarea(
            attrs={
                "rows": 35,
                "cols": 200,
                "style": "font-family: monospace; font-size: 13px;",
                "spellcheck": "false",
            }
        ),
        required=False,
    )

    class Meta:
        """Default model form options for :class:`~.models.Template`."""

        model = Template
        fields = "__all__"

    def clean(self):
        """Validate template syntax and scheduling fields before save."""
        cleaned_data = super().clean()
        content = cleaned_data.get("content", "")
        active_from = cleaned_data.get("active_from")
        active_until = cleaned_data.get("active_until")

        # Syntax check
        if content:
            try:
                DjangoTemplate(content)
            except TemplateSyntaxError as e:
                self.add_error("content", _("Template syntax error: %s") % str(e))

        # Scheduling window sanity
        if active_from and active_until and active_from >= active_until:
            self.add_error(
                "active_until", _("'Active until' must be after 'Active from'.")
            )

        return cleaned_data


# ---------------------------------------------------------------------------
# Inline: version history
# ---------------------------------------------------------------------------


class TemplateVersionInline(admin.TabularInline):
    """Read-only inline table of stored content versions for a template."""

    model = TemplateVersion
    extra = 0
    can_delete = False
    max_num = 0
    fields = (
        "version",
        "state",
        "content_preview",
        "created_at",
        "created_by",
        "version_actions",
    )
    readonly_fields = (
        "version",
        "state",
        "content_preview",
        "created_at",
        "created_by",
        "version_actions",
    )
    ordering = ("-version",)
    verbose_name = _("Version History")
    verbose_name_plural = _("Version History")

    def content_preview(self, obj):
        """Show a monospace snippet of stored version body text."""
        preview = (obj.content or "")[:120]
        if len(obj.content or "") > 120:
            preview += "…"
        return format_html(
            '<span style="font-family:monospace;font-size:11px;white-space:pre-wrap">{}</span>',
            preview,
        )

    content_preview.short_description = _("Content Preview")

    def version_actions(self, obj):
        """
        Render per-version actions for the inline history table.

        During the "add" view, Django still builds empty inline forms where
        ``obj.template_id`` and ``obj.version`` are ``None``. Guard against
        that so reverse() is only called for real, persisted versions.
        """
        if not obj or not obj.template_id or not obj.version:
            # On the add form Django still renders empty inline rows without a
            # backing object; in that case we just show a simple placeholder.
            return "—"

        restore_url = reverse(
            "admin:horilla_dbtemplate_template_restore_version",
            args=[obj.template_id, obj.version],
        )
        diff_url = (
            reverse(
                "admin:horilla_dbtemplate_template_diff",
                args=[obj.template_id],
            )
            + f"?v={obj.version}"
        )
        return format_html(
            '<a class="button" style="margin-right:6px" href="{}">'
            "↩ Restore</a>"
            '<a class="button" href="{}" target="_blank">'
            "⟺ Diff</a>",
            restore_url,
            diff_url,
        )

    version_actions.short_description = _("Actions")


# ---------------------------------------------------------------------------
# Main admin
# ---------------------------------------------------------------------------


@admin.register(Template)
class TemplateAdmin(admin.ModelAdmin):
    """Django admin for database-backed templates, locks, previews, and actions."""

    form = TemplateAdminForm
    inlines = [TemplateVersionInline]

    list_display = (
        "name",
        "state_badge",
        "updated_at",
        "updated_by",
        "site_list",
    )
    list_filter = ("state", "sites")
    search_fields = ("name", "content")
    save_as = True
    date_hierarchy = "updated_at"

    readonly_fields = (
        "created_at",
        "updated_at",
        "created_by",
        "updated_by",
        "last_accessed_at",
        "locked_by",
        "locked_at",
        "lock_status_display",
        "preview_panel",
    )

    fieldsets = (
        (
            None,
            {
                "fields": ("name", "state", "content", "preview_panel"),
                "classes": ("wide",),
            },
        ),
        (
            _("Sites"),
            {
                "fields": ("sites",),
            },
        ),
        (
            _("Scheduling"),
            {
                "fields": ("active_from", "active_until"),
                "description": _(
                    "Leave both blank to always serve this template (subject to state). "
                    "Set Active From / Active Until to restrict serving to a time window."
                ),
            },
        ),
        (
            _("Edit Lock"),
            {
                "fields": ("lock_status_display", "locked_by", "locked_at"),
                "classes": ("collapse",),
                "description": _(
                    "A template is automatically locked when someone opens the edit page. "
                    "Locks expire after 30 minutes or when the editor saves/cancels."
                ),
            },
        ),
        (
            _("Tracking"),
            {
                "fields": ("created_at", "updated_at", "created_by", "updated_by"),
                "classes": ("collapse",),
            },
        ),
    )

    filter_horizontal = ("sites",)

    actions = [
        "action_activate",
        "action_archive",
        "action_set_draft",
        "action_invalidate_cache",
        "action_repopulate_cache",
        "action_check_syntax",
        "action_force_unlock",
        "action_export_json",
    ]

    # ------------------------------------------------------------------
    # List display helpers
    # ------------------------------------------------------------------

    def state_badge(self, obj):
        """Render state as a coloured label for the changelist."""
        colours = {
            STATE_DRAFT: ("#888", "⬜"),
            STATE_ACTIVE: ("#2e7d32", "🟢"),
            STATE_ARCHIVED: ("#b71c1c", "🔴"),
        }
        colour, icon = colours.get(obj.state, ("#888", "⬜"))
        return format_html(
            '<span style="color:{};font-weight:600">{} {}</span>',
            colour,
            icon,
            obj.get_state_display(),
        )

    state_badge.short_description = _("State")
    state_badge.admin_order_field = "state"

    def site_list(self, obj):
        """Comma-separated site names, or Global when no sites are attached."""
        sites = obj.sites.all()
        if not sites:
            return mark_safe('<span style="color:#aaa">Global</span>')
        return ", ".join(site.name for site in sites)

    site_list.short_description = _("Sites")

    # ------------------------------------------------------------------
    # Readonly field renderers
    # ------------------------------------------------------------------

    def lock_status_display(self, obj):
        """Explain current edit-lock state with optional force-unlock link."""
        if not obj.pk:
            return "—"
        if obj.is_locked():
            unlock_url = reverse(
                "admin:horilla_dbtemplate_template_unlock",
                args=[obj.pk],
            )
            return format_html(
                '<span style="color:#e65100">🔒 Locked by <strong>{}</strong> at {} '
                "(expires 30 min after lock)</span> &nbsp;"
                '<a class="button" href="{}">Force Unlock</a>',
                escape(str(obj.locked_by)),
                localtime(obj.locked_at).strftime("%Y-%m-%d %H:%M"),
                unlock_url,
            )
        return mark_safe('<span style="color:#2e7d32">🔓 Not locked</span>')

    lock_status_display.short_description = _("Lock Status")

    def preview_panel(self, obj):
        """Offer a button to open the live preview URL for persisted templates."""
        if not obj.pk:
            return format_html(
                '<em style="color:#aaa">{}</em>',
                _("Save the template first to enable live preview."),
            )
        preview_url = reverse(
            "admin:horilla_dbtemplate_template_preview", args=[obj.pk]
        )
        return format_html(
            '<div style="margin-top:6px">'
            '<a class="button" href="{}" target="_blank">🔍 Open Live Preview</a>'
            '&nbsp;<em style="color:#888;font-size:12px">{}</em>'
            "</div>",
            preview_url,
            _("Opens in a new tab. Uses a dummy/empty context."),
        )

    preview_panel.short_description = _("Live Preview")

    # ------------------------------------------------------------------
    # Change view: apply edit lock
    # ------------------------------------------------------------------

    def change_view(self, request, object_id, form_url="", extra_context=None):
        """Show the change form, warn on conflicting locks, and acquire the edit lock."""
        obj = self.get_object(request, object_id)
        extra_context = extra_context or {}

        if obj:
            if obj.is_locked() and obj.locked_by != request.user:
                messages.warning(
                    request,
                    _(
                        "⚠️ Warning: %(user)s has been editing this template since %(time)s. "
                        "Saving will overwrite their changes."
                    )
                    % {
                        "user": str(obj.locked_by),
                        "time": localtime(obj.locked_at).strftime("%H:%M"),
                    },
                )
            obj.lock(request.user)

            # Add version count and diff URL to context
            version_count = obj.versions.count()
            extra_context["version_count"] = version_count
            if version_count >= 2:
                latest_versions = list(
                    obj.versions.order_by("-version").values_list("version", flat=True)[
                        :2
                    ]
                )
                if len(latest_versions) >= 2:
                    extra_context["diff_url"] = (
                        reverse("admin:horilla_dbtemplate_template_diff", args=[obj.pk])
                        + f"?v1={latest_versions[1]}&v2={latest_versions[0]}"
                    )

        return super().change_view(request, object_id, form_url, extra_context)

    def response_change(self, request, obj):
        """Release the edit lock after a successful edit."""
        obj.unlock()
        return super().response_change(request, obj)

    def response_add(self, request, obj, post_url_continue=None):
        """Release the edit lock after creating a template with a persisted PK."""
        if obj.pk:
            obj.unlock()
        return super().response_add(request, obj, post_url_continue)

    # ------------------------------------------------------------------
    # Custom URLs
    # ------------------------------------------------------------------

    def get_urls(self):
        """Append restore, diff, preview, and unlock routes to the admin URLconf."""
        urls = super().get_urls()
        custom = [
            path(
                "<int:template_id>/restore/<int:version>/",
                self.admin_site.admin_view(self.restore_version_view),
                name="horilla_dbtemplate_template_restore_version",
            ),
            path(
                "<int:template_id>/diff/",
                self.admin_site.admin_view(self.diff_view),
                name="horilla_dbtemplate_template_diff",
            ),
            path(
                "<int:pk>/preview/",
                self.admin_site.admin_view(self.preview_view),
                name="horilla_dbtemplate_template_preview",
            ),
            path(
                "<int:pk>/unlock/",
                self.admin_site.admin_view(self.unlock_view),
                name="horilla_dbtemplate_template_unlock",
            ),
        ]
        return custom + urls

    # ------------------------------------------------------------------
    # Custom views
    # ------------------------------------------------------------------

    def restore_version_view(self, request, template_id, version):
        """Restore a template to a previous version."""
        tmpl = get_object_or_404(Template, pk=template_id)
        ver = get_object_or_404(TemplateVersion, template=tmpl, version=version)

        if request.method == "POST":
            tmpl.restore_version(version, user=request.user)
            add_template_to_cache(tmpl)
            messages.success(
                request,
                _("Template '%(name)s' restored to version %(v)d.")
                % {
                    "name": tmpl.name,
                    "v": version,
                },
            )
            return redirect(
                reverse("admin:horilla_dbtemplate_template_change", args=[template_id])
            )

        # GET: confirmation page
        change_url = reverse(
            "admin:horilla_dbtemplate_template_change", args=[template_id]
        )
        current_lines = (tmpl.content or "").splitlines(keepends=True)
        restore_lines = (ver.content or "").splitlines(keepends=True)
        diff_html = _render_diff_html(
            current_lines, restore_lines, "Current", f"v{version}"
        )

        context = {
            **self.admin_site.each_context(request),
            "title": _("Restore Template Version"),
            "template": tmpl,
            "version": ver,
            "diff_html": mark_safe(diff_html),
            "change_url": change_url,
            "opts": self.model._meta,
        }
        from django.template.response import TemplateResponse

        return TemplateResponse(
            request,
            "admin/horilla_dbtemplate/template/restore_version.html",
            context,
        )

    def diff_view(self, request, template_id):
        """Side-by-side diff between two template versions."""
        tmpl = get_object_or_404(Template, pk=template_id)
        versions = list(tmpl.versions.order_by("version"))

        if len(versions) < 1:
            messages.error(request, _("No versions available."))
            return redirect(
                reverse("admin:horilla_dbtemplate_template_change", args=[template_id])
            )

        version_choices = [
            (
                v.version,
                f"v{v.version} — {localtime(v.created_at).strftime('%Y-%m-%d %H:%M')} by {v.created_by or 'system'}",
            )
            for v in versions
        ]

        # Default: compare last two
        all_vnums = [v.version for v in versions]
        v1_num = int(request.GET.get("v1", all_vnums[0] if all_vnums else 0))
        v2_num = int(
            request.GET.get(
                "v2", all_vnums[-1] if len(all_vnums) >= 2 else all_vnums[0]
            )
        )

        try:
            v1 = tmpl.versions.get(version=v1_num)
        except TemplateVersion.DoesNotExist:
            v1 = versions[0]
        try:
            v2 = tmpl.versions.get(version=v2_num)
        except TemplateVersion.DoesNotExist:
            v2 = versions[-1]

        lines_a = (v1.content or "").splitlines(keepends=True)
        lines_b = (v2.content or "").splitlines(keepends=True)
        diff_html = _render_diff_html(
            lines_a, lines_b, f"v{v1.version}", f"v{v2.version}"
        )

        context = {
            **self.admin_site.each_context(request),
            "title": _("Template Diff — %(name)s") % {"name": tmpl.name},
            "template": tmpl,
            "v1": v1,
            "v2": v2,
            "version_choices": version_choices,
            "diff_html": mark_safe(diff_html),
            "opts": self.model._meta,
            "change_url": reverse(
                "admin:horilla_dbtemplate_template_change", args=[template_id]
            ),
        }
        from django.template.response import TemplateResponse

        return TemplateResponse(
            request,
            "admin/horilla_dbtemplate/template/diff.html",
            context,
        )

    def preview_view(self, request, pk):
        """Render the template with a dummy context and return the HTML."""
        tmpl = get_object_or_404(Template, pk=pk)

        content = (
            request.POST.get("content", tmpl.content)
            if request.method == "POST"
            else tmpl.content
        )

        dummy_context = {
            "request": request,
            "user": request.user,
            "preview_mode": True,
            "now": now(),
        }

        rendered = ""
        error = ""
        try:
            t = DjangoTemplate(content)
            ctx = Context(dummy_context)
            rendered = t.render(ctx)
        except TemplateSyntaxError as e:
            error = str(e)
        except Exception as e:
            error = str(e)

        if error:
            rendered = f"<pre style='color:red;padding:20px'>Render error:\n{escape(error)}</pre>"

        change_url = reverse("admin:horilla_dbtemplate_template_change", args=[pk])
        context = {
            **self.admin_site.each_context(request),
            "title": _("Live Preview — %(name)s") % {"name": tmpl.name},
            "template": tmpl,
            "rendered": mark_safe(rendered),
            "error": error,
            "opts": self.model._meta,
            "change_url": change_url,
        }
        from django.template.response import TemplateResponse

        return TemplateResponse(
            request,
            "admin/horilla_dbtemplate/template/preview.html",
            context,
        )

    def unlock_view(self, request, pk):
        """Force-unlock a template."""
        tmpl = get_object_or_404(Template, pk=pk)
        if not request.user.is_superuser and tmpl.locked_by != request.user:
            messages.error(
                request, _("Only a superuser or the locking user can force-unlock.")
            )
        else:
            tmpl.unlock()
            messages.success(
                request, _("Template '%(name)s' unlocked.") % {"name": tmpl.name}
            )
        return redirect(reverse("admin:horilla_dbtemplate_template_change", args=[pk]))

    # ------------------------------------------------------------------
    # Admin actions
    # ------------------------------------------------------------------

    @admin.action(description=_("✅ Set selected templates to ACTIVE"))
    def action_activate(self, request, queryset):
        """Bulk-activate rows and refresh loader cache entries."""
        n = queryset.update(state=STATE_ACTIVE)
        for t in queryset:
            add_template_to_cache(t)
        self.message_user(
            request,
            ngettext(
                "%(n)d template set to Active.",
                "%(n)d templates set to Active.",
                n,
            )
            % {"n": n},
        )

    @admin.action(description=_("🗄️ Archive selected templates"))
    def action_archive(self, request, queryset):
        """Bulk-archive rows and purge their keys from the template cache."""
        n = queryset.update(state=STATE_ARCHIVED)
        for t in queryset:
            remove_cached_template(t)
        self.message_user(
            request,
            ngettext(
                "%(n)d template archived.",
                "%(n)d templates archived.",
                n,
            )
            % {"n": n},
        )

    @admin.action(description=_("📝 Set selected templates to DRAFT"))
    def action_set_draft(self, request, queryset):
        """Bulk-set draft state and invalidate cached template source."""
        n = queryset.update(state=STATE_DRAFT)
        for t in queryset:
            remove_cached_template(t)
        self.message_user(
            request,
            ngettext(
                "%(n)d template set to Draft.",
                "%(n)d templates set to Draft.",
                n,
            )
            % {"n": n},
        )

    @admin.action(description=_("🗑️ Invalidate cache of selected templates"))
    def action_invalidate_cache(self, request, queryset):
        """Remove all cache keys associated with each selected template."""
        for template in queryset:
            remove_cached_template(template)
        n = queryset.count()
        self.message_user(
            request,
            ngettext(
                "Cache of %(n)d template invalidated.",
                "Cache of %(n)d templates invalidated.",
                n,
            )
            % {"n": n},
        )

    @admin.action(description=_("♻️ Repopulate cache for selected templates"))
    def action_repopulate_cache(self, request, queryset):
        """Re-run clear-then-warm for each row (same as post-save cache refresh)."""
        for template in queryset:
            add_template_to_cache(template)
        n = queryset.count()
        self.message_user(
            request,
            ngettext(
                "Cache repopulated for %(n)d template.",
                "Cache repopulated for %(n)d templates.",
                n,
            )
            % {"n": n},
        )

    @admin.action(description=_("🔍 Check syntax of selected templates"))
    def action_check_syntax(self, request, queryset):
        """Validate Django template syntax and surface errors in admin messages."""
        errors = []
        ok_count = 0
        for template in queryset:
            valid, err = check_template_syntax(template)
            if not valid:
                errors.append(f"{template.name}: {err}")
            else:
                ok_count += 1
        if errors:
            self.message_user(
                request,
                _("Syntax errors in %(n)d template(s): %(names)s")
                % {
                    "n": len(errors),
                    "names": " | ".join(errors),
                },
                level=messages.ERROR,
            )
        if ok_count:
            self.message_user(
                request, _("%(n)d template(s) have valid syntax.") % {"n": ok_count}
            )

    @admin.action(description=_("🔓 Force-unlock selected templates"))
    def action_force_unlock(self, request, queryset):
        """Clear locked_by / locked_at for superusers only."""
        if not request.user.is_superuser:
            self.message_user(
                request,
                _("Only superusers can force-unlock templates."),
                level=messages.ERROR,
            )
            return
        queryset.update(locked_by=None, locked_at=None)
        n = queryset.count()
        self.message_user(
            request,
            ngettext(
                "%(n)d template unlocked.",
                "%(n)d templates unlocked.",
                n,
            )
            % {"n": n},
        )

    @admin.action(description=_("📥 Export selected templates as JSON fixture"))
    def action_export_json(self, request, queryset):
        """Return a JSON download of core template fields for backup or migration."""
        data = serialize(
            "json",
            queryset,
            indent=2,
            fields=[
                "name",
                "content",
                "state",
                "active_from",
                "active_until",
            ],
        )
        response = HttpResponse(data, content_type="application/json")
        ts = now().strftime("%Y%m%d_%H%M%S")
        response["Content-Disposition"] = (
            f'attachment; filename="dbtemplate_export_{ts}.json"'
        )
        return response


# ---------------------------------------------------------------------------
# TemplateVersion admin (read-only audit view)
# ---------------------------------------------------------------------------


@admin.register(TemplateVersion)
class TemplateVersionAdmin(admin.ModelAdmin):
    """Read-only audit listing of immutable template content snapshots."""

    list_display = (
        "template",
        "version",
        "state",
        "created_at",
        "created_by",
        "content_chars",
    )
    list_filter = ("state", "template")
    search_fields = ("template__name",)
    readonly_fields = (
        "template",
        "version",
        "state",
        "content",
        "created_at",
        "created_by",
    )
    ordering = ("-created_at",)

    def content_chars(self, obj):
        """Length of stored version body for quick scanning in the changelist."""
        return f"{len(obj.content or '')} chars"

    content_chars.short_description = _("Size")

    def has_add_permission(self, request):
        """Versions are created by the Template model only."""
        return False

    def has_change_permission(self, request, obj=None):
        """Keep rows immutable in admin."""
        return False


# ---------------------------------------------------------------------------
# Diff rendering helper
# ---------------------------------------------------------------------------


def _render_diff_html(lines_a, lines_b, label_a="Old", label_b="New"):
    """
    Produce an HTML side-by-side diff table from two lists of lines.
    Uses Python's difflib HtmlDiff for a clean table output.
    """
    differ = difflib.HtmlDiff(wrapcolumn=80)
    table = differ.make_table(
        lines_a,
        lines_b,
        fromdesc=label_a,
        todesc=label_b,
        context=True,
        numlines=3,
    )
    # Inject inline styles since admin pages may strip external stylesheets
    table = table.replace(
        '<td class="diff_header"',
        '<td style="background:#f5f5f5;padding:2px 6px;font-family:monospace;font-size:12px;color:#555" class="diff_header"',
    )
    return (
        "<style>"
        ".diff_add{background:#e6ffed} .diff_chg{background:#fff3cd} .diff_sub{background:#ffeef0}"
        "td{font-family:monospace;font-size:12px;white-space:pre-wrap;vertical-align:top}"
        "table.diff{width:100%;border-collapse:collapse}"
        "td,th{border:1px solid #e0e0e0;padding:2px 6px}"
        "</style>" + table
    )
