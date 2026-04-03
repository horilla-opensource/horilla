"""
Tests for horilla/models.py

Covers:
- has_xss() XSS detection function
- upload_path() file path generation
- HorillaModel.save() auto-setting created_by / modified_by
- HorillaModel.clean_fields() XSS validation on char/text fields
- FieldFile.url monkey-patch returning /404/ for missing files
"""

import re
from unittest.mock import MagicMock, PropertyMock, patch

from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import models
from django.db.models.fields.files import FieldFile

from base.models import Tags
from horilla.horilla_middlewares import _thread_locals
from horilla.models import HorillaModel, has_xss, upload_path
from horilla.test_utils.base import HorillaTestCase


# ---------------------------------------------------------------------------
# has_xss()
# ---------------------------------------------------------------------------
class HasXssTests(HorillaTestCase):
    """Tests for the has_xss() XSS detection utility."""

    # -- Should detect (return True) --

    def test_script_tag(self):
        self.assertTrue(has_xss("<script>alert('xss')</script>"))

    def test_script_tag_with_attributes(self):
        self.assertTrue(has_xss('<script type="text/javascript">alert(1)</script>'))

    def test_script_tag_multiline(self):
        payload = "<script>\nalert('xss')\n</script>"
        self.assertTrue(has_xss(payload))

    def test_script_tag_extra_spaces(self):
        self.assertTrue(has_xss("< script >alert(1)</ script >"))

    def test_javascript_pseudo_protocol(self):
        self.assertTrue(has_xss("javascript:alert(1)"))

    def test_javascript_pseudo_protocol_with_space(self):
        self.assertTrue(has_xss("javascript  :alert(1)"))

    def test_javascript_pseudo_protocol_case_insensitive(self):
        self.assertTrue(has_xss("JAVASCRIPT:alert(1)"))

    def test_inline_event_handler_onerror(self):
        self.assertTrue(has_xss('<img onerror="alert(1)" src=x>'))

    def test_inline_event_handler_onclick(self):
        self.assertTrue(has_xss('<div onclick="alert(1)">click</div>'))

    def test_inline_event_handler_onload(self):
        self.assertTrue(has_xss('onload="alert(1)"'))

    def test_inline_event_handler_onmouseover(self):
        self.assertTrue(has_xss('<a onmouseover="alert(1)">hover</a>'))

    def test_iframe(self):
        self.assertTrue(has_xss('<iframe src="evil.com">'))

    def test_embed_tag(self):
        self.assertTrue(has_xss('<embed src="evil.swf">'))

    def test_object_tag(self):
        self.assertTrue(has_xss('<object data="evil.swf">'))

    def test_svg_tag(self):
        self.assertTrue(has_xss('<svg onload="alert(1)">'))

    def test_math_tag(self):
        self.assertTrue(has_xss("<math><maction>evil</maction></math>"))

    def test_link_tag(self):
        self.assertTrue(has_xss('<link rel="stylesheet" href="evil.css">'))

    def test_meta_tag(self):
        self.assertTrue(has_xss('<meta http-equiv="refresh" content="0;url=evil">'))

    def test_js_api_eval(self):
        self.assertTrue(has_xss("onload=\"eval('code')\""))

    def test_js_api_settimeout(self):
        self.assertTrue(has_xss("onclick=\"setTimeout('alert(1)',0)\""))

    def test_js_api_setinterval(self):
        self.assertTrue(has_xss("onclick=\"setInterval('alert(1)',1000)\""))

    def test_js_api_fetch(self):
        self.assertTrue(has_xss("onload=\"fetch('http://evil.com')\""))

    def test_js_api_new_function(self):
        self.assertTrue(has_xss("onload=\"new Function('alert(1)')()\""))

    # -- Should NOT detect (return False) --

    def test_clean_bold_html(self):
        self.assertFalse(has_xss("<b>bold text</b>"))

    def test_clean_paragraph(self):
        self.assertFalse(has_xss("<p>Hello World</p>"))

    def test_plain_text(self):
        self.assertFalse(has_xss("Hello World"))

    def test_url(self):
        self.assertFalse(has_xss("https://example.com"))

    def test_url_with_path(self):
        self.assertFalse(has_xss("https://example.com/path?query=value"))

    def test_empty_string(self):
        self.assertFalse(has_xss(""))

    def test_none(self):
        self.assertFalse(has_xss(None))

    def test_integer(self):
        self.assertFalse(has_xss(42))

    def test_float(self):
        self.assertFalse(has_xss(3.14))

    def test_boolean(self):
        self.assertFalse(has_xss(True))

    def test_list(self):
        self.assertFalse(has_xss([1, 2, 3]))

    def test_safe_html_with_class(self):
        self.assertFalse(has_xss('<div class="container">content</div>'))

    def test_safe_html_anchor(self):
        self.assertFalse(has_xss('<a href="https://example.com">link</a>'))


# ---------------------------------------------------------------------------
# upload_path()
# ---------------------------------------------------------------------------
class _FakeMeta:
    """Lightweight _meta stand-in for upload_path tests."""

    def __init__(self, app_label, model_name):
        self.app_label = app_label
        self.model_name = model_name


class _FakeInstance:
    """Lightweight instance for upload_path — avoids MagicMock __dict__ issues."""

    def __init__(self, app_label="base", model_name="tags"):
        self._meta = _FakeMeta(app_label, model_name)


class UploadPathTests(HorillaTestCase):
    """Tests for the upload_path() file naming utility."""

    def _make_instance(self, app_label="base", model_name="tags"):
        return _FakeInstance(app_label, model_name)

    def test_basic_path_format(self):
        """upload_path returns app_label/model_name/<slugified-uuid>.ext"""
        instance = self._make_instance()
        result = upload_path(instance, "report.pdf")
        parts = result.split("/")
        self.assertEqual(parts[0], "base")
        self.assertEqual(parts[1], "tags")
        # filename portion: slugified-name + 8-char hex + .ext
        self.assertTrue(parts[-1].endswith(".pdf"))
        self.assertIn("report-", parts[-1])

    def test_filename_preserves_extension(self):
        instance = self._make_instance()
        result = upload_path(instance, "photo.JPEG")
        self.assertTrue(result.endswith(".JPEG"))

    def test_filename_with_special_characters(self):
        """Special characters in the name portion get slugified."""
        instance = self._make_instance()
        result = upload_path(instance, "my photo (1).png")
        filename = result.split("/")[-1]
        # slugify converts spaces and parens; no spaces or parens in output
        self.assertNotIn(" ", filename)
        self.assertNotIn("(", filename)

    def test_filename_without_extension(self):
        """A filename without a dot still produces a path."""
        instance = self._make_instance()
        result = upload_path(instance, "noextension")
        # When there's no extension, split(".")[-1] returns the whole name
        # and split(".")[:-1] is empty, so base_name becomes "file"
        filename = result.split("/")[-1]
        self.assertTrue(filename.startswith("file-"))

    def test_uuid_portion_is_8_hex_chars(self):
        """The UUID segment is exactly 8 hex characters."""
        instance = self._make_instance()
        result = upload_path(instance, "test.txt")
        filename = result.split("/")[-1]
        # Format: slugified-name-<8hex>.ext
        name_without_ext = filename.rsplit(".", 1)[0]
        uuid_part = name_without_ext.split("-")[-1]
        self.assertEqual(len(uuid_part), 8)
        # Must be valid hex
        int(uuid_part, 16)

    def test_different_app_labels(self):
        instance = self._make_instance(app_label="leave", model_name="leaverequest")
        result = upload_path(instance, "doc.pdf")
        self.assertTrue(result.startswith("leave/leaverequest/"))

    def test_includes_field_name_when_matched(self):
        """When instance.__dict__ has a matching field, include it in the path."""
        instance = self._make_instance()
        # Simulate a file field value with a .name attribute
        mock_field_value = MagicMock()
        mock_field_value.name = "avatar.jpg"
        instance.profile_pic = mock_field_value
        result = upload_path(instance, "avatar.jpg")
        self.assertIn("profile_pic", result)


# ---------------------------------------------------------------------------
# HorillaModel.save() — created_by / modified_by
# ---------------------------------------------------------------------------
class HorillaModelSaveTests(HorillaTestCase):
    """Tests for HorillaModel.save() auto-setting created_by and modified_by."""

    def test_created_by_set_on_new_instance(self):
        """New instance gets created_by from _thread_locals request user."""
        self.set_request_user(self.admin_user)
        tag = Tags.objects.create(title="Urgent", color="red")
        tag.refresh_from_db()
        self.assertEqual(tag.created_by, self.admin_user)

    def test_modified_by_set_on_new_instance(self):
        """New instance also gets modified_by on first save."""
        self.set_request_user(self.admin_user)
        tag = Tags.objects.create(title="Priority", color="blue")
        tag.refresh_from_db()
        self.assertEqual(tag.modified_by, self.admin_user)

    def test_created_by_not_changed_on_update(self):
        """On update, created_by stays with the original creator."""
        self.set_request_user(self.admin_user)
        tag = Tags.objects.create(title="V1", color="green")

        # Switch user and update
        self.set_request_user(self.manager_user)
        tag.title = "V2"
        tag.save()
        tag.refresh_from_db()

        self.assertEqual(tag.created_by, self.admin_user)

    def test_modified_by_updated_on_save(self):
        """On update, modified_by reflects the current user."""
        self.set_request_user(self.admin_user)
        tag = Tags.objects.create(title="Original", color="red")

        self.set_request_user(self.manager_user)
        tag.title = "Updated"
        tag.save()
        tag.refresh_from_db()

        self.assertEqual(tag.modified_by, self.manager_user)

    def test_save_without_thread_locals_request(self):
        """save() does not crash when _thread_locals has no request."""
        if hasattr(_thread_locals, "request"):
            del _thread_locals.request

        tag = Tags(title="NoRequest", color="gray")
        # Should not raise
        tag.save()
        tag.refresh_from_db()
        self.assertIsNone(tag.created_by)
        self.assertIsNone(tag.modified_by)

    def test_save_with_anonymous_user(self):
        """save() handles AnonymousUser without crashing."""
        mock_request = MagicMock()
        mock_request.user = AnonymousUser()
        _thread_locals.request = mock_request

        tag = Tags(title="AnonTag", color="white")
        tag.save()
        tag.refresh_from_db()
        # AnonymousUser is not authenticated, so created_by stays None
        self.assertIsNone(tag.created_by)


# ---------------------------------------------------------------------------
# HorillaModel.clean_fields() — XSS validation
# ---------------------------------------------------------------------------
class HorillaModelCleanFieldsTests(HorillaTestCase):
    """Tests for HorillaModel.clean_fields() XSS validation."""

    def test_detects_xss_in_charfield(self):
        """clean_fields() raises ValidationError for XSS in CharField."""
        tag = Tags(title="<script>alert(1)</script>", color="red")
        with self.assertRaises(ValidationError) as ctx:
            tag.clean_fields()
        self.assertIn("title", ctx.exception.message_dict)

    def test_detects_xss_in_multiple_fields(self):
        """clean_fields() reports all fields with XSS, not just the first."""
        tag = Tags(
            title="<script>alert(1)</script>",
            color="<iframe src='evil.com'>",
        )
        with self.assertRaises(ValidationError) as ctx:
            tag.clean_fields()
        self.assertIn("title", ctx.exception.message_dict)
        self.assertIn("color", ctx.exception.message_dict)

    def test_allows_clean_values(self):
        """clean_fields() passes when values are clean."""
        tag = Tags(title="Normal Tag", color="#ff0000")
        # Should not raise
        tag.clean_fields()

    def test_skips_excluded_fields(self):
        """clean_fields() respects the exclude parameter."""
        tag = Tags(title="<script>alert(1)</script>", color="red")
        # Excluding 'title' should mean no error for title
        # color is clean, so no error at all
        tag.clean_fields(exclude=["title"])

    def test_skips_xss_exempt_fields(self):
        """clean_fields() respects the model's xss_exempt_fields attribute."""
        tag = Tags(title="<script>alert(1)</script>", color="red")
        # Temporarily set xss_exempt_fields
        tag.xss_exempt_fields = ["title"]
        # Should not raise because title is exempt, color is clean
        tag.clean_fields()

    def test_xss_in_non_exempt_field_still_caught(self):
        """Exempting one field does not exempt others."""
        tag = Tags(
            title="<script>alert(1)</script>",
            color="<script>alert(2)</script>",
        )
        tag.xss_exempt_fields = ["title"]
        with self.assertRaises(ValidationError) as ctx:
            tag.clean_fields()
        self.assertNotIn("title", ctx.exception.message_dict)
        self.assertIn("color", ctx.exception.message_dict)

    def test_none_value_not_flagged(self):
        """Fields with None values are skipped (the `if value` check)."""
        tag = Tags(title=None, color="red")
        # Should not raise
        tag.clean_fields()

    def test_empty_string_not_flagged(self):
        """Empty strings are falsy, so not checked for XSS."""
        tag = Tags(title="", color="")
        tag.clean_fields()


# ---------------------------------------------------------------------------
# FieldFile.url monkey-patch
# ---------------------------------------------------------------------------
class FieldFileUrlPatchTests(HorillaTestCase):
    """Tests for the monkey-patched FieldFile.url returning /404/ for missing files."""

    def test_missing_file_returns_404_url(self):
        """Accessing .url on a FieldFile with no actual file returns the /404/ path."""
        # Create a FieldFile bound to a mock field that has no file
        mock_field = MagicMock(spec=models.FileField)
        mock_field.storage = MagicMock()

        field_file = FieldFile(instance=None, field=mock_field, name=None)
        # name is None, so _require_file() will raise
        result = field_file.url
        # Should be the /404/ URL (from reverse("404"))
        self.assertIn("404", result)

    def test_existing_file_returns_storage_url(self):
        """FieldFile.url returns the storage URL when the file exists."""
        mock_field = MagicMock(spec=models.FileField)
        mock_storage = MagicMock()
        mock_storage.url.return_value = "/media/test/file.pdf"
        mock_field.storage = mock_storage

        field_file = FieldFile(instance=None, field=mock_field, name="test/file.pdf")
        result = field_file.url
        self.assertEqual(result, "/media/test/file.pdf")
