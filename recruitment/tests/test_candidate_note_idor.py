"""A candidate may only write notes on their own hiring record.

GHSA-v963-hrfx-34mw: `candidate_add_notes` resolved its target with
`Candidate.find(cand_id)` -- straight from the URL -- while its only gate,
`candidate_login_required`, asserts merely that *some* candidate session
exists. Any self-registered candidate could therefore attach notes to any
other applicant's record, tampering with a hiring decision, and the same
request rendered the target's self-tracking page back to them.

The portal request carries no authenticated employee, so the company-scoped
manager does not constrain it and the write crosses tenants. That is pinned
below, because "wrong company" is the part a same-company test would miss.

This is the third view on this decorator with this shape. GHSA-p745-9729-g8jw
fixed `file_upload` and `view_file`; `candidate_add_notes` sits ninety lines
further down the same file and was missed.
"""

from django.contrib.auth.models import AnonymousUser, Permission
from django.test import TestCase
from django.urls import reverse

from base.models import Company, Department, JobPosition
from horilla_auth.models import HorillaUser
from recruitment.models import Candidate, Recruitment, Stage, StageNote
from recruitment.views.views import candidate_reachable_by


class _Request:
    """Minimal stand-in: the helper reads only .user and .session."""

    def __init__(self, user, session=None):
        self.user = user
        self.session = session or {}


class CandidateNoteScopingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.acme = Company.objects.create(company="Acme", hq=True)
        cls.other = Company.objects.create(company="Rival")

        department = Department.objects.create(department="Engineering")
        job_position = JobPosition.objects.create(
            job_position="Engineer", department_id=department
        )
        recruitment = Recruitment.objects.create(
            title="Engineer", closed=False, is_active=True
        )
        recruitment.open_positions.add(job_position)
        # Creating a Recruitment seeds its default stages, "Applied" among
        # them, so take the existing row rather than inserting a duplicate.
        cls.stage = Stage.objects.filter(recruitment_id=recruitment).first()

        cls.attacker = cls._candidate(
            "Attacker",
            "attacker@example.com",
            "2000000000",
            recruitment,
            job_position,
            cls.stage,
        )
        cls.victim = cls._candidate(
            "Victim",
            "victim@example.com",
            "1000000000",
            recruitment,
            job_position,
            cls.stage,
        )

    @staticmethod
    def _candidate(name, email, mobile, recruitment, job_position, stage):
        from django.core.files.uploadedfile import SimpleUploadedFile

        return Candidate.objects.create(
            name=name,
            email=email,
            mobile=mobile,
            recruitment_id=recruitment,
            job_position_id=job_position,
            stage_id=stage,
            resume=SimpleUploadedFile(f"{name}.pdf", b"%PDF-1.4 test"),
        )

    # -- the helper ------------------------------------------------------

    def test_candidate_cannot_reach_another_candidate(self):
        """The reported attack: session is the attacker's, id is the victim's."""
        request = _Request(AnonymousUser(), {"candidate_id": self.attacker.id})
        self.assertIsNone(candidate_reachable_by(request, self.victim.id))

    def test_candidate_can_still_reach_themselves(self):
        """A fix that denied everything would also pass the test above."""
        request = _Request(AnonymousUser(), {"candidate_id": self.attacker.id})
        self.assertEqual(
            candidate_reachable_by(request, self.attacker.id), self.attacker
        )

    def test_no_candidate_session_reaches_nobody(self):
        request = _Request(AnonymousUser(), {})
        self.assertIsNone(candidate_reachable_by(request, self.victim.id))

    def test_recruiter_permission_still_reaches_every_candidate(self):
        """The half a naive fix breaks: recruiters add notes as their job."""
        user = HorillaUser.objects.create_user(
            username="recruiter", password="Test-Passw0rd!"
        )
        user.user_permissions.add(Permission.objects.get(codename="view_candidate"))
        user = HorillaUser.objects.get(pk=user.pk)  # refresh the perm cache
        self.assertEqual(
            candidate_reachable_by(_Request(user, {}), self.victim.id), self.victim
        )

    def test_unknown_id_reaches_nobody(self):
        request = _Request(AnonymousUser(), {"candidate_id": self.attacker.id})
        self.assertIsNone(candidate_reachable_by(request, 999999))

    # -- the view --------------------------------------------------------

    def _post_note(self, cand_id, text):
        session = self.client.session
        session["candidate_id"] = self.attacker.id
        session.save()
        return self.client.post(
            reverse("candidate-add-notes", kwargs={"cand_id": cand_id}),
            {"description": text},
        )

    def test_posting_a_note_onto_another_candidate_writes_nothing(self):
        """The reported impact is a write, so assert on the database."""
        self._post_note(self.victim.id, "INJECTED-BY-ATTACKER")
        self.assertFalse(
            StageNote.objects.filter(candidate_id=self.victim).exists(),
            "a note was written onto another candidate's record",
        )

    def test_posting_a_note_onto_a_candidate_in_another_company_writes_nothing(self):
        """Cross-tenant: the portal request has no company context at all."""
        self.victim.recruitment_id.company_id = self.other
        self.victim.recruitment_id.save()
        self._post_note(self.victim.id, "CROSS-TENANT-INJECTION")
        self.assertFalse(StageNote.objects.filter(candidate_id=self.victim).exists())

    def test_a_candidate_can_still_note_their_own_record(self):
        self._post_note(self.attacker.id, "my own note")
        self.assertTrue(StageNote.objects.filter(candidate_id=self.attacker).exists())
