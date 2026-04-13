import re
import time
from pathlib import Path

import polib
from deep_translator import GoogleTranslator


PO_PATH = Path("horilla/locale/uk/LC_MESSAGES/django.po")
BATCH_SIZE = 35
TOKEN_PREFIX = "ZXPH"
PLACEHOLDER_RE = re.compile(r"(%\([^)]+\)[a-zA-Z]|%[a-zA-Z]|\{[^{}]*\}|<[^>]+>)")


def protect(text: str):
    placeholders = []

    def repl(match):
        placeholders.append(match.group(0))
        return f"{TOKEN_PREFIX}{len(placeholders)-1}Q"

    return PLACEHOLDER_RE.sub(repl, text), placeholders


def restore(text: str, placeholders):
    restored = text
    for i, placeholder in enumerate(placeholders):
        restored = restored.replace(f"{TOKEN_PREFIX}{i}Q", placeholder)
    return restored


def tr(text: str, translator: GoogleTranslator) -> str:
    protected, placeholders = protect(text)
    translated = translator.translate(protected)
    return restore(translated, placeholders)


def should_translate(entry) -> bool:
    if not entry.msgid:
        return False
    if entry.msgid_plural:
        return False
    if not entry.msgstr.strip():
        return True
    return entry.msgstr.strip() == entry.msgid.strip()


def main():
    po = polib.pofile(str(PO_PATH))
    translator = GoogleTranslator(source="en", target="uk")

    entries = [entry for entry in po if should_translate(entry)]
    print(f"to_translate={len(entries)}")

    translated_count = 0
    errors = 0

    for start in range(0, len(entries), BATCH_SIZE):
        batch = entries[start : start + BATCH_SIZE]

        protected_batch = []
        placeholder_maps = []
        for entry in batch:
            protected_text, placeholder_map = protect(entry.msgid)
            protected_batch.append(protected_text)
            placeholder_maps.append(placeholder_map)

        try:
            translated_batch = translator.translate_batch(protected_batch)
            if not isinstance(translated_batch, list):
                translated_batch = [translated_batch]
        except Exception:
            translated_batch = []
            for text in protected_batch:
                try:
                    translated_batch.append(translator.translate(text))
                    time.sleep(0.3)
                except Exception:
                    translated_batch.append("")
                    errors += 1

        for entry, translated, placeholders in zip(batch, translated_batch, placeholder_maps):
            if translated:
                entry.msgstr = restore(translated, placeholders)
                if "fuzzy" in entry.flags:
                    entry.flags.remove("fuzzy")
                translated_count += 1

        if (start // BATCH_SIZE) % 4 == 0:
            print(
                f"progress={min(start + BATCH_SIZE, len(entries))}/{len(entries)} "
                f"translated={translated_count} errors={errors}"
            )

    plural_entries = [entry for entry in po if entry.msgid_plural]
    print(f"plural_entries={len(plural_entries)}")

    for index, entry in enumerate(plural_entries, start=1):
        try:
            singular_missing = not entry.msgstr_plural.get(0, "").strip()
            plural_1_missing = not entry.msgstr_plural.get(1, "").strip()
            plural_2_missing = not entry.msgstr_plural.get(2, "").strip()

            singular_tr = tr(entry.msgid, translator) if singular_missing else entry.msgstr_plural.get(0)
            plural_tr = tr(entry.msgid_plural, translator) if plural_1_missing else entry.msgstr_plural.get(1)

            entry.msgstr_plural[0] = singular_tr
            entry.msgstr_plural[1] = plural_tr
            entry.msgstr_plural[2] = plural_tr if plural_2_missing else entry.msgstr_plural.get(2)

            if "fuzzy" in entry.flags:
                entry.flags.remove("fuzzy")
        except Exception:
            errors += 1

        if index % 100 == 0:
            print(f"plural_progress={index}/{len(plural_entries)} errors={errors}")

    po.save(str(PO_PATH))
    print(f"done translated={translated_count} errors={errors}")


if __name__ == "__main__":
    main()
