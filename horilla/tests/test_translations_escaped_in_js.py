"""A translated string placed inside a JavaScript string must go through ``|escapejs``.

``{% trans "Carry Forward" %}`` renders whatever the active language says. In French that
is ``Transporter vers l'avant``, so

    { name: '{% trans "Carry Forward" %}', data: carryData }

reaches the browser as

    { name: 'Transporter vers l'avant', data: carryData }

The apostrophe ends the JavaScript string early, the script stops with a syntax error, and
everything after it on the page - the summary cards at the top of a list tab, in the report in
issue #1207 - never loads. Nothing fails in English, so it only shows once a language with
apostrophes (French, Italian, Catalan, ...) is switched on.

``|escapejs`` turns ``'``, ``"`` and ``\\`` into ``\\uXXXX`` escapes, which are safe inside a
JavaScript string whichever quote delimits it, and inside an HTML attribute too.

This test reads the templates the way the browser will: it finds the inline ``<script>``
blocks and the ``onclick=`` style attributes, and flags a translation that sits directly
between a pair of quotes without ``|escapejs``. Translations in plain HTML text or in an
ordinary attribute are not JavaScript and are left alone.
"""

import re
import unittest
from pathlib import Path

SKIP_DIRS = {".git", "__pycache__", "node_modules", "staticfiles", "venv", ".venv", "env"}

TRANS = re.compile(r"""\{%\s*trans\s+("[^"]*"|'[^']*')(?:\s+as\s+\w+)?\s*%\}""")
INLINE_SCRIPT = re.compile(r"<script(?![^>]*\bsrc=)[^>]*>.*?</script>", re.DOTALL | re.IGNORECASE)
EVENT_ATTRIBUTE = re.compile(r"""\bon\w+\s*=\s*(?:"[^"]*"|'[^']*')""")
QUOTE_PAIRS = {("'", "'"), ('"', '"'), ("`", "`")}


def templates():
    root = Path(__file__).resolve().parents[2]
    for path in root.rglob("*.html"):
        if SKIP_DIRS.isdisjoint(path.relative_to(root).parts):
            yield root, path


def unescaped_translations_in_js(text):
    """Line numbers and tags of translations inside a JS string that are not escaped."""
    found = []
    spans = [m.span() for m in INLINE_SCRIPT.finditer(text)]
    spans += [m.span() for m in EVENT_ATTRIBUTE.finditer(text)]
    for start, end in spans:
        segment = text[start:end]
        for match in TRANS.finditer(segment):
            if "escapejs" in match.group(0):
                continue
            before = segment[max(0, match.start() - 1) : match.start()]
            after = segment[match.end() : match.end() + 1]
            if (before, after) in QUOTE_PAIRS:
                line = text.count("\n", 0, start + match.start()) + 1
                found.append((line, match.group(0)))
    return found


class TranslationsAreEscapedInJavaScript(unittest.TestCase):
    def test_the_check_sees_the_bug(self):
        broken = "<script>var x = { name: '{% trans \"Carry Forward\" %}' };</script>"
        self.assertEqual(len(unescaped_translations_in_js(broken)), 1)
        handler = "<a onclick=\"confirm('{% trans 'Sure?' %}')\">x</a>"
        self.assertEqual(len(unescaped_translations_in_js(handler)), 1)

    def test_the_check_accepts_the_fix_and_plain_html(self):
        fixed = "<script>var x = { name: '{% trans \"Carry Forward\"|escapejs %}' };</script>"
        self.assertEqual(unescaped_translations_in_js(fixed), [])
        html = "<p title='{% trans \"Approve\" %}'>{% trans \"Reject\" %}</p>"
        self.assertEqual(unescaped_translations_in_js(html), [])

    def test_no_template_puts_an_unescaped_translation_inside_a_js_string(self):
        problems = []
        for root, path in templates():
            try:
                text = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            for line, tag in unescaped_translations_in_js(text):
                problems.append(f"{path.relative_to(root).as_posix()}:{line}  {tag}")
        self.assertEqual(
            problems,
            [],
            "A translation inside a JavaScript string needs |escapejs "
            "(see this module's docstring):\n  " + "\n  ".join(problems),
        )


if __name__ == "__main__":
    unittest.main()
