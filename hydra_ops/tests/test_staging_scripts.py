import io
import os
import shutil
import subprocess
import tarfile
import tempfile
import unittest
from pathlib import Path

from django.test import SimpleTestCase


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def available_shell():
    candidates = (
        shutil.which("sh"),
        r"C:\Program Files\Git\bin\sh.exe",
    )
    return next(
        (
            candidate
            for candidate in candidates
            if candidate and Path(candidate).is_file()
        ),
        None,
    )


def available_powershell():
    candidates = (
        shutil.which("pwsh"),
        shutil.which("powershell"),
        os.path.join(
            os.environ.get("SystemRoot", r"C:\Windows"),
            "System32",
            "WindowsPowerShell",
            "v1.0",
            "powershell.exe",
        ),
    )
    return next(
        (
            candidate
            for candidate in candidates
            if candidate and Path(candidate).is_file()
        ),
        None,
    )


def shell_path(path):
    path = Path(path).resolve()
    value = path.as_posix()
    if os.name == "nt" and len(value) >= 3 and value[1:3] == ":/":
        return f"/{value[0].lower()}{value[2:]}"
    return value


class StagingArchiveValidationTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.shell = available_shell()
        if cls.shell is None:
            raise unittest.SkipTest(
                "A POSIX shell is required for staging archive tests."
            )
        cls.validator = REPOSITORY_ROOT / "scripts" / "staging-validate-archive.sh"

    def run_validator(self, archive):
        return subprocess.run(
            [
                self.shell,
                shell_path(self.validator),
                shell_path(archive),
                "test archive",
            ],
            capture_output=True,
            check=False,
            env={**os.environ, "LC_ALL": "C"},
            text=True,
        )

    @staticmethod
    def add_regular(archive, name, content=b"safe"):
        member = tarfile.TarInfo(name)
        member.size = len(content)
        member.mode = 0o600
        archive.addfile(member, io.BytesIO(content))

    def test_safe_opaque_archive_is_accepted(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "safe.tar.gz"
            with tarfile.open(path, "w:gz") as archive:
                self.add_regular(
                    archive,
                    "candidate-documents/ab/abcdef0123456789.pdf",
                )

            result = self.run_validator(path)

        self.assertEqual(result.returncode, 0, result.stderr)

    def test_parent_traversal_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "traversal.tar.gz"
            with tarfile.open(path, "w:gz") as archive:
                self.add_regular(archive, "../escape.payload")

            result = self.run_validator(path)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("member-path validation", result.stderr)

    def test_symbolic_link_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "symlink.tar.gz"
            with tarfile.open(path, "w:gz") as archive:
                member = tarfile.TarInfo("portal-email/ab/payload")
                member.type = tarfile.SYMTYPE
                member.linkname = "/etc/passwd"
                archive.addfile(member)

            result = self.run_validator(path)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("member-type validation", result.stderr)

    def test_duplicate_normalized_path_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "duplicate.tar.gz"
            with tarfile.open(path, "w:gz") as archive:
                self.add_regular(archive, "portal-email/ab/payload")
                self.add_regular(archive, "./portal-email/ab/payload")

            result = self.run_validator(path)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("member-path validation", result.stderr)


class StagingInitialDeploymentGuardTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.powershell = available_powershell()
        if cls.powershell is None:
            raise unittest.SkipTest(
                "PowerShell is required for staging deployment tests."
            )

    def run_deploy(self, public_relation_count):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            deploy = root / "staging-deploy.ps1"
            smoke = root / "staging-smoke.ps1"
            env_file = root / ".env.staging"
            compose_file = root / "docker-compose.staging.yaml"
            shutil.copyfile(
                REPOSITORY_ROOT / "scripts" / "staging-deploy.ps1",
                deploy,
            )
            smoke.write_text(
                "$ErrorActionPreference = 'Stop'\nWrite-Output 'smoke-stub-ok'\n",
                encoding="utf-8",
            )
            env_file.write_text("HYDRA_TEST_ONLY=True\n", encoding="utf-8")
            compose_file.write_text("services: {}\n", encoding="utf-8")

            if os.name == "nt":
                fake_docker = root / "docker.cmd"
                fake_docker.write_text(
                    f"@echo off\r\necho {public_relation_count}\r\nexit /b 0\r\n",
                    encoding="ascii",
                )
            else:
                fake_docker = root / "docker"
                fake_docker.write_text(
                    f"#!/bin/sh\nprintf '%s\\n' '{public_relation_count}'\n",
                    encoding="ascii",
                )
                fake_docker.chmod(0o700)

            environment = {
                **os.environ,
                "PATH": f"{root}{os.pathsep}{os.environ.get('PATH', '')}",
            }
            return subprocess.run(
                [
                    self.powershell,
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(deploy),
                    "-Revision",
                    "guard-test-revision",
                    "-BaseUrl",
                    "https://staging.example.test",
                    "-InitialDeployment",
                    "-ComposeFile",
                    str(compose_file),
                    "-EnvFile",
                    str(env_file),
                ],
                capture_output=True,
                check=False,
                cwd=root,
                env=environment,
                text=True,
            )

    def test_initial_deployment_refuses_existing_schema(self):
        result = self.run_deploy(public_relation_count=7)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("InitialDeployment refused", result.stderr)
        # PowerShell 7 may wrap and decorate long exceptions differently on Linux.
        # Assert the two safety instructions independently of terminal rendering.
        self.assertIn("Hydra creates", result.stderr)
        self.assertIn("verifies a recovery point", result.stderr)

    def test_initial_deployment_allows_proven_empty_schema(self):
        result = self.run_deploy(public_relation_count=0)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("passed smoke checks", result.stdout)


class StagingColdBackupContractTests(SimpleTestCase):
    def test_cold_backup_stops_ingress_and_writers_before_snapshot(self):
        script = (REPOSITORY_ROOT / "scripts" / "staging-backup.ps1").read_text(
            encoding="utf-8"
        )

        self.assertIn("docker @compose stop proxy maintenance server", script)
        self.assertIn(
            "docker @compose up -d --wait --wait-timeout 1800 "
            "server maintenance proxy",
            script,
        )


class StagingRemoteLoadWorkflowContractTests(SimpleTestCase):
    def test_remote_load_tags_are_explicit_bounded_and_publish_evidence(self):
        workflow = (
            REPOSITORY_ROOT / ".github" / "workflows" / "hydra-staging-ci.yml"
        ).read_text(encoding="utf-8")

        self.assertIn('      - "hydra-load-*"', workflow)
        for stage in ("20", "50", "100", "150", "200", "spike"):
            self.assertIn(f"hydra-load-{stage}-*) stage={stage} ;;", workflow)
        self.assertIn("timeout-minutes: 240", workflow)
        self.assertIn("openssl rand -hex", workflow)
        self.assertIn('echo "::add-mask::$value"', workflow)
        self.assertIn("./scripts/run-load-stage.ps1", workflow)
        self.assertIn("retention-days: 30", workflow)

        compose = (REPOSITORY_ROOT / "docker-compose.load.yaml").read_text(
            encoding="utf-8"
        )
        runner = (REPOSITORY_ROOT / "scripts" / "run-load-stage.ps1").read_text(
            encoding="utf-8"
        )
        self.assertIn("HYDRA_LOAD_RUNTIME_UID:-10002", compose)
        self.assertIn("HYDRA_LOAD_RUNTIME_GID:-10002", compose)
        self.assertIn("DirectorySeparatorChar -eq '/'", runner)
        self.assertIn("runtimeUidExitCode", runner)
        self.assertIn("runtimeGidExitCode", runner)
        self.assertIn("PSObject.Properties['Health']", runner)
