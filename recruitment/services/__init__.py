"""
Recruitment services package.

Provides resume parsing (legacy, AI, orchestrator), semantic candidate–job fit,
and related utilities.
"""

from recruitment.services.resume_parser import ResumeParseOrchestrator
from recruitment.services.semantic_matching import (
    build_candidate_text,
    find_similar_candidates,
    get_ranked_resumes_for_view,
    score_resumes_for_recruitment,
)

__all__ = [
    "ResumeParseOrchestrator",
    "build_candidate_text",
    "find_similar_candidates",
    "get_ranked_resumes_for_view",
    "score_resumes_for_recruitment",
]
