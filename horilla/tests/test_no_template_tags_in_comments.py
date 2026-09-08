"""Django template tags must not hide inside CSS or JavaScript comments.

Django's lexer tokenises `{% ... %}` across the whole file. It has no idea what
CSS or JS comments are -- only `{% comment %}` and `{# #}` are template
comments. So a tag written inside a `/* ... */` block, as documentation
describing where the real tag lives, is parsed and executed like any other tag.

That shipped. `modern_filter_panel.html` carried

    /* The Group By accordion (appended in horilla_nav.html, right after
       {% include filter_body_template %}) is never a true DOM sibling ... */

inside a `<style>` block. `filter_body_template` is set as a class attribute by
the list views, so every page that includes the panel through the generic nav
was fine -- but the four templates that include it directly never set it, the
variable resolved empty, and `{% include %}` raised

    TemplateDoesNotExist: No template names provided

500ing /attendance/work-records/, the skill zone view and the attendance
monthly summary. It went out in 2.1.0, 2.1.1 and 2.1.2 before anyone caught it,
because nothing reads CSS comments looking for template tags. This test does.

Scoped to the tags that can actually raise. `{{ var }}` and `{% trans %}` in a
comment render harmlessly, and failing on those would need an allow-list that
would rot; `{% include %}`, `{% extends %}`, `{% url %}` and `{% ssi %}` all
resolve something that can be missing, which is what turns a comment into a
500.
"""

import re
import unittest
from pathlib import Path

# Directories that are not ours to police.
SKIP_DIRS = {
    ".git",
    "__pycache__",
    "node_modules",
    "staticfiles",
    "venv",
    ".venv",
    "env",
}

# Tags that resolve something which can be absent, and therefore raise.
DANGEROUS_TAG = re.compile(r"{%\s*(include|extends|url|ssi)\b")

CSS_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)
TEMPLATE_COMMENT = re.compile(
    r"{%\s*comment\s*%}.*?{%\s*endcomment\s*%}|{#.*?#}", re.DOTALL
)

REPO_ROOT = Path(__file__).resolve().parents[2]


def _blank_out(match):
    """Replace a match with spaces, keeping newlines.

    Deleting the text instead would shift every line number after it, and the
    whole value of this test is naming the line to go and fix.
    """
    return re.sub(r"[^\n]", " ", match.group(0))


def _offences(text):
    """Yield (line_number, tag) for dangerous tags inside CSS/JS comments."""
    # Real template comments are not executed, so blank them first -- a tag
    # inside {% comment %} is genuinely inert and must not be reported.
    stripped = TEMPLATE_COMMENT.sub(_blank_out, text)

    for block in CSS_COMMENT.finditer(stripped):
        for tag in DANGEROUS_TAG.finditer(block.group(0)):
            offset = block.start() + tag.start()
            yield stripped.count("\n", 0, offset) + 1, tag.group(0).strip()

    for lineno, line in enumerate(stripped.splitlines(), start=1):
        if line.lstrip().startswith("//"):
            found = DANGEROUS_TAG.search(line)
            if found:
                yield lineno, found.group(0).strip()


def _templates():
    for path in REPO_ROOT.rglob("*.html"):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        yield path


class TemplateTagsInCommentsTests(unittest.TestCase):
    def test_no_dangerous_tag_is_hidden_in_a_comment(self):
        offences = []
        for path in _templates():
            text = path.read_text(encoding="utf-8", errors="replace")
            # Cheap reject: most templates have no CSS/JS comment at all.
            if "/*" not in text and "//" not in text:
                continue
            for lineno, tag in _offences(text):
                offences.append(
                    f"{path.relative_to(REPO_ROOT)}:{lineno} contains {tag} ...%}}"
                )

        self.assertEqual(
            offences,
            [],
            "Django parses these tags even though they sit in a CSS/JS comment, "
            "so they run on every render and raise when what they resolve is "
            "missing. Reword the comment so it does not contain template "
            "syntax (or wrap it in {% verbatim %}):\n  " + "\n  ".join(offences),
        )

    def test_detects_a_planted_offence(self):
        """The check must fail on the exact shape that shipped."""
        planted = (
            "<style>\n"
            ".x {\n"
            "    /* appended in horilla_nav.html, right after\n"
            "       {% include filter_body_template %}) is never a sibling */\n"
            "    margin-top: 4px;\n"
            "}\n"
            "</style>\n"
        )
        self.assertEqual(list(_offences(planted)), [(4, "{% include")])

    def test_ignores_tags_in_real_template_comments(self):
        """{% comment %} and {# #} are not executed, so they are not offences."""
        inert = (
            "{% comment %}\n"
            "/* {% include 'a.html' %} */\n"
            "{% endcomment %}\n"
            "{# /* {% url 'x' %} */ #}\n"
        )
        self.assertEqual(list(_offences(inert)), [])

    def test_ignores_harmless_tags(self):
        """{{ var }} and {% trans %} in a comment cannot raise."""
        harmless = "<style>/* {{ user.name }} and {% trans 'hi' %} */</style>"
        self.assertEqual(list(_offences(harmless)), [])
