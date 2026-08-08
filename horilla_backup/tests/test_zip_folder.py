"""Backup zip helper smoke tests."""

import tempfile
import zipfile
from pathlib import Path

from django.test import SimpleTestCase

from horilla_backup.zip import zip_folder


class ZipFolderTests(SimpleTestCase):
    def test_zips_relative_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "data"
            root.mkdir()
            (root / "note.txt").write_text("hello", encoding="utf-8")
            out = Path(tmp) / "out.zip"
            zip_folder(str(root), str(out))
            with zipfile.ZipFile(out) as zf:
                self.assertIn("note.txt", zf.namelist())
