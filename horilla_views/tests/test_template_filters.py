"""with_dot / without_dot split a view's row_status_indications. A view that
defines none passes None; the Document Requests pipeline did, and its whole
list failed to render (TypeError: 'NoneType' object is not iterable)."""

from django.test import SimpleTestCase

from horilla_views.templatetags.generic_template_filters import with_dot, without_dot


class StatusIndicationFilterTests(SimpleTestCase):
    def test_none_means_no_indications(self):
        self.assertEqual(with_dot(None), [])
        self.assertEqual(without_dot(None), [])

    def test_splits_on_whether_a_dot_class_is_set(self):
        indications = [("approved--dot", "Approved", "a"), ("", "Today", "b")]
        self.assertEqual(with_dot(indications), [indications[0]])
        self.assertEqual(without_dot(indications), [indications[1]])
