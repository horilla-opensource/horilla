"""
GHSA-6fxh-v24c-4cmx: the denylist in `sanitize_mail_template_body()` was
bypassable, so the SSTI that GHSA-9p83 / CVE-2026-63432 and GHSA-fphr were
meant to close stayed reachable through 2.1.3.

Two holes, both reported by @Ntn10:

  * only the tag *name* was checked, so `{% with %}`, `{% firstof %}` and every
    other tag could carry the forbidden path the `{{ }}` check rejects;
  * filter arguments were discarded before the check (`inner.split("|", 1)[0]`),
    so `{{ x|default:a.b.password }}` passed.

An `HR Manager` -- a stock role holding no permission over `auth` or user
objects -- could therefore read any account's password hash, the superuser's
included, off the reflected mail-template endpoints.

The checks below are on the sanitizer rather than on any one endpoint because
eighteen call sites share it and only two of them add the strict allow-list.
"""

from django.template import Context, Template
from django.test import SimpleTestCase

from base.methods import sanitize_mail_template_body

SECRET = "pbkdf2_sha256$600000$saltsalt$derivedkeyderivedkey="


class _User:
    password = SECRET
    username = "admin"
    is_superuser = True


class _Employee:
    """Stands in for the real `instance`: an Employee with a linked User."""

    employee_user_id = _User()
    employee_first_name = "Ada"

    def get_full_name(self):
        return "Ada Lovelace"


def render(body):
    """Sanitize then render exactly as the mail paths do."""
    return Template(sanitize_mail_template_body(body)).render(
        Context({"instance": _Employee(), "self": _Employee(), "x": ""})
    )


class MailTemplateSSTITests(SimpleTestCase):
    def assertNoLeak(self, body):
        out = render(body)
        self.assertNotIn(SECRET, out, f"password hash leaked via: {body}")
        return out

    # --- the reported bypasses -------------------------------------------

    def test_direct_path_still_blocked(self):
        """The case the original fix did catch, as a control."""
        self.assertNoLeak("{{ instance.employee_user_id.password }}")

    def test_with_tag_cannot_smuggle_the_path(self):
        self.assertNoLeak(
            "{% with h=instance.employee_user_id.password %}{{ h }}{% endwith %}"
        )

    def test_filter_argument_is_inspected(self):
        self.assertNoLeak("{{ x|default:instance.employee_user_id.password }}")

    def test_firstof_cannot_smuggle_the_path(self):
        self.assertNoLeak("{% firstof instance.employee_user_id.password %}")

    def test_for_loop_cannot_smuggle_the_path(self):
        self.assertNoLeak(
            "{% for v in instance.employee_user_id.password %}{{ v }}{% endfor %}"
        )

    def test_regroup_cannot_smuggle_the_path(self):
        self.assertNoLeak(
            "{% regroup x by employee_user_id.password as g %}{{ g.0.grouper }}"
        )

    def test_cycle_cannot_smuggle_the_path(self):
        self.assertNoLeak("{% cycle instance.employee_user_id.password %}")

    # --- the class, not just the instances -------------------------------

    def test_unknown_tags_are_dropped(self):
        """
        `include` and `extends` read from disk and were never on the old
        denylist; nobody reported them, but the same allow-list settles them.
        """
        for body in (
            '{% include "base/auth/login.html" %}',
            '{% extends "index.html" %}',
            "{% debug %}",
            "{% load i18n %}",
            "{% csrf_token %}",
        ):
            with self.subTest(body=body):
                self.assertEqual(render(body).strip(), "")

    def test_whitespace_padding_does_not_evade(self):
        self.assertNoLeak("{{ instance . employee_user_id . password }}")
        self.assertNoLeak(
            "{%   with  h = instance.employee_user_id.password %}"
            "{{ h }}{% endwith %}"
        )

    # --- must not break ordinary templates -------------------------------

    def test_placeholders_still_render(self):
        self.assertEqual(render("Hi {{ instance.get_full_name }}"), "Hi Ada Lovelace")

    def test_conditionals_and_loops_still_render(self):
        body = (
            "{% if instance.employee_first_name %}"
            "{{ instance.employee_first_name }}"
            "{% else %}nobody{% endif %}"
        )
        self.assertEqual(render(body), "Ada")

    def test_prose_containing_a_forbidden_word_survives(self):
        """
        The check skips quoted literals, so a template that merely says the
        word "password" is not gutted. Only unquoted lookup paths are rejected.
        """
        out = render('{{ "Reset your password"|upper }}')
        self.assertEqual(out, "RESET YOUR PASSWORD")

    def test_dictsort_by_a_quoted_key_discloses_nothing(self):
        """
        `dictsort` is the one builtin that resolves a quoted string as a
        property path, which is why quoted literals are skipped by the scan.
        It sorts by that key and renders the objects, never the key's value.
        """
        self.assertNoLeak('{{ x|dictsort:"employee_user_id.password" }}')

    def test_plain_text_is_untouched(self):
        body = "<p>Dear employee, your password expires soon.</p>"
        self.assertEqual(render(body), body)

    def test_verbatim_content_is_not_executed_or_stripped(self):
        out = render(
            "{% verbatim %}{{ instance.employee_user_id.password }}{% endverbatim %}"
        )
        self.assertNotIn(SECRET, out)
        self.assertIn("{{ instance.employee_user_id.password }}", out)

    # --- fail-closed ------------------------------------------------------

    def test_stranded_block_end_does_not_raise(self):
        """
        Dropping `{% with %}` strands its `{% endwith %}`; callers compile the
        return value immediately, so this must not raise out of a mail send.
        """
        out = sanitize_mail_template_body(
            "before"
            "{% with h=instance.employee_user_id.password %}{{ h }}{% endwith %}"
            "after"
        )
        Template(out)  # must compile
        self.assertNotIn("password", out)

    def test_empty_body_is_returned_unchanged(self):
        self.assertEqual(sanitize_mail_template_body(""), "")
        self.assertIsNone(sanitize_mail_template_body(None))
