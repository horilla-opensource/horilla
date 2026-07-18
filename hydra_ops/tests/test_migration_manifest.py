import importlib.util
import tempfile
from pathlib import Path

from django.test import SimpleTestCase


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
VERIFIER_PATH = REPOSITORY_ROOT / "scripts" / "verify-migration-manifest.py"
SPEC = importlib.util.spec_from_file_location(
    "hydra_migration_manifest_verifier",
    VERIFIER_PATH,
)
verifier = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(verifier)


class MigrationManifestTests(SimpleTestCase):
    def test_repository_manifest_matches_exact_source_set(self):
        current = verifier.discover_migrations(REPOSITORY_ROOT)
        manifest = verifier.load_manifest(
            REPOSITORY_ROOT / "deployment" / "migration-manifest.sha256"
        )

        self.assertEqual(verifier.comparison_errors(manifest, current), [])
        self.assertEqual(len(current), 80)
        self.assertIn(
            "deployment/django_auth_migrations/0013_user_is_new_employee.py",
            current,
        )

    def test_comparison_reports_missing_unreviewed_and_changed_sources(self):
        manifest = {
            "app/migrations/0001_initial.py": "a" * 64,
            "app/migrations/0002_reviewed.py": "b" * 64,
        }
        current = {
            "app/migrations/0001_initial.py": "c" * 64,
            "app/migrations/0003_unreviewed.py": "d" * 64,
        }

        errors = verifier.comparison_errors(manifest, current)

        self.assertEqual(
            errors,
            [
                "reviewed migration is missing: app/migrations/0002_reviewed.py",
                "migration is absent from the reviewed manifest: "
                "app/migrations/0003_unreviewed.py",
                "reviewed migration content changed: "
                "app/migrations/0001_initial.py",
            ],
        )

    def test_digest_is_stable_across_lf_and_crlf_checkouts(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            lf_path = root / "lf.py"
            crlf_path = root / "crlf.py"
            lf_path.write_bytes(b"line_one\nline_two\n")
            crlf_path.write_bytes(b"line_one\r\nline_two\r\n")

            lf_digest = verifier.normalized_sha256(lf_path)
            crlf_digest = verifier.normalized_sha256(crlf_path)

        self.assertEqual(lf_digest, crlf_digest)

    def test_manifest_parser_rejects_duplicate_paths(self):
        with tempfile.TemporaryDirectory() as temporary:
            manifest = Path(temporary) / "manifest.sha256"
            line = f"{'a' * 64}  app/migrations/0001_initial.py\n"
            manifest.write_text(line + line, encoding="ascii")

            with self.assertRaisesRegex(
                verifier.ManifestError,
                "Duplicate migration manifest path",
            ):
                verifier.load_manifest(manifest)
