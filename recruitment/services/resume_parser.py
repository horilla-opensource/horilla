"""
Resume parse orchestrator: validate → AI or legacy → normalize → return.

Single entry point for resume parsing used by resume_completion and
matching_resume_completion views.
"""

import io
import logging
import threading
from typing import Optional

from django.conf import settings

from recruitment.services.ai_resume_parser import parse_resume_from_bytes as ai_parse
from recruitment.services.legacy_resume_parser import (
    extract_info as legacy_extract_info,
)
from recruitment.services.normalize_resume_data import normalize_resume_output

logger = logging.getLogger(__name__)

# Allowed MIME / extensions for resume upload
ALLOWED_EXTENSIONS = (".pdf",)
ALLOWED_CONTENT_TYPES = ("application/pdf",)


class ResumeParseError(Exception):
    """Raised when validation fails (e.g. file type/size)."""

    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class ResumeParseOrchestrator:
    """
    Orchestrates resume parsing: validate file, run AI or legacy parser,
    normalize output to canonical schema.
    """

    @staticmethod
    def _get_config():
        use_ai = getattr(settings, "RESUME_PARSING_USE_AI", False)
        timeout = getattr(settings, "RESUME_PARSING_AI_TIMEOUT_SECONDS", 8.0)
        max_mb = getattr(settings, "RESUME_PARSING_MAX_FILE_SIZE_MB", 10.0)
        return use_ai, float(timeout), float(max_mb)

    @staticmethod
    def _validate_file(file_bytes: bytes, filename: str = "") -> None:
        """Raise ResumeParseError if file type or size is invalid."""
        use_ai, _, max_mb = ResumeParseOrchestrator._get_config()
        max_bytes = int(max_mb * 1024 * 1024)
        if len(file_bytes) > max_bytes:
            raise ResumeParseError(
                f"File size exceeds {max_mb} MB limit.",
                status_code=400,
            )
        if len(file_bytes) < 50:
            raise ResumeParseError("File is too small or empty.", status_code=400)
        ext = filename.lower().split(".")[-1] if filename else ""
        if ext and ext != "pdf":
            raise ResumeParseError(
                "Only PDF files are supported for resume parsing.",
                status_code=400,
            )

    @staticmethod
    def _run_ai_with_timeout(
        file_bytes: bytes, filename: str, timeout: float
    ) -> Optional[dict]:
        """Run AI parser in a thread with timeout; return None on timeout/error."""
        result = [None]
        exc_holder = [None]

        def run():
            try:
                result[0] = ai_parse(file_bytes, filename=filename, timeout=timeout)
            except Exception as e:
                exc_holder[0] = e

        thread = threading.Thread(target=run, daemon=True)
        thread.start()
        thread.join(timeout=timeout)
        if thread.is_alive():
            logger.warning("Resume parsing AI timeout after %s s", timeout)
            return None
        if exc_holder[0]:
            logger.warning("Resume parsing AI error: %s", exc_holder[0])
            return None
        return result[0]

    @staticmethod
    def parse(
        file_bytes: Optional[bytes] = None,
        file_object=None,
        resume_id=None,
    ) -> dict:
        """
        Parse resume and return canonical schema dict for form fill.

        Call with either:
          - file_bytes: raw bytes (e.g. from request.FILES["resume"].read())
          - file_object: file-like (e.g. request.FILES["resume"]) — will be read to bytes
          - resume_id: PK of recruitment.Resume — file will be read from storage

        Returns:
            dict with keys full_name, email_id, phone_number, address, country,
            state, city, zip, dob, gender, portfolio (all strings).
        """
        from recruitment.models import Resume

        if resume_id is not None:
            resume = Resume.objects.filter(pk=resume_id).first()
            if not resume or not resume.file:
                raise ResumeParseError(
                    "Resume not found or file missing.", status_code=404
                )
            resume.file.open("rb")
            try:
                file_bytes = resume.file.read()
                filename = getattr(resume.file, "name", "") or "resume.pdf"
            finally:
                resume.file.close()
        elif file_object is not None:
            file_bytes = (
                file_object.read() if hasattr(file_object, "read") else file_object
            )
            filename = getattr(file_object, "name", "") or "resume.pdf"
        elif file_bytes is not None:
            filename = ""
        else:
            raise ResumeParseError("No file or resume_id provided.", status_code=400)

        if isinstance(file_bytes, str):
            file_bytes = file_bytes.encode("utf-8")

        ResumeParseOrchestrator._validate_file(file_bytes, filename)

        use_ai, timeout, _ = ResumeParseOrchestrator._get_config()
        raw = None
        used_ai = False

        if use_ai:
            raw = ResumeParseOrchestrator._run_ai_with_timeout(
                file_bytes, filename, timeout
            )
            if raw is not None:
                used_ai = True
            else:
                logger.info("Resume parse fallback to legacy after AI timeout/error")

        if raw is None:
            try:
                raw = legacy_extract_info(io.BytesIO(file_bytes))
            except Exception as e:
                logger.exception("Legacy resume parse failed: %s", e)
                raise ResumeParseError(
                    "Could not parse resume. Please enter details manually.",
                    status_code=500,
                )

        if used_ai:
            logger.debug("Resume parsed via AI path")
        else:
            logger.debug("Resume parsed via legacy path")

        normalized = normalize_resume_output(raw)
        return normalized
