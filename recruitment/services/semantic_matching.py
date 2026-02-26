"""
Semantic candidate–job fit: score and rank resumes by similarity to a recruitment.

Phase 1: Local TF-IDF + cosine similarity (no external API).
Used by matching_resumes view when SEMANTIC_MATCHING_ENABLED is True.
"""

import math
import re
from collections import Counter

from django.conf import settings


def _tokenize(text):
    """Lowercase tokenize; keep only word characters (letters, digits)."""
    if not text:
        return []
    return re.findall(r"\b\w+\b", text.lower())


def _tf_idf_vectors(documents):
    """
    Build TF-IDF vectors for a list of document strings.
    Returns (list of Counter, idf_dict) where each Counter is term -> tfidf weight.
    """
    if not documents:
        return [], {}

    tokenized = [_tokenize(d) for d in documents]
    n_docs = len(documents)
    df = Counter()
    for tokens in tokenized:
        for term in set(tokens):
            df[term] += 1

    idf = {}
    for term, count in df.items():
        idf[term] = math.log((n_docs + 1) / (count + 1)) + 1

    def tf_counter(tokens):
        total = len(tokens) or 1
        return Counter(
            {t: (c / total) * idf.get(t, 1) for t, c in Counter(tokens).items()}
        )

    vectors = [tf_counter(tokens) for tokens in tokenized]
    return vectors, idf


def _cosine_similarity(vec_a, vec_b):
    """Cosine similarity between two Counter-based vectors (term -> weight)."""
    if not vec_a or not vec_b:
        return 0.0
    all_terms = set(vec_a) | set(vec_b)
    dot = sum(vec_a.get(t, 0) * vec_b.get(t, 0) for t in all_terms)
    norm_a = math.sqrt(sum(v * v for v in vec_a.values()))
    norm_b = math.sqrt(sum(v * v for v in vec_b.values()))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


class LocalSemanticMatchingBackend:
    """
    In-process semantic scoring using TF-IDF and cosine similarity.
    No external API; suitable for Phase 1.
    """

    def score(self, job_text, resume_texts):
        """
        Return a list of semantic scores (0–1) for each resume text against job_text.
        """
        if not job_text or not resume_texts:
            return [0.0] * len(resume_texts)

        documents = [job_text] + resume_texts
        vectors, _ = _tf_idf_vectors(documents)
        if not vectors:
            return [0.0] * len(resume_texts)

        job_vec = vectors[0]
        resume_vectors = vectors[1:]
        scores = []
        for rv in resume_vectors:
            sim = _cosine_similarity(job_vec, rv)
            scores.append(max(0.0, min(1.0, sim)))
        return scores


def build_job_text(recruitment):
    """Build a single text representation of the recruitment for matching."""
    parts = []
    if getattr(recruitment, "title", None):
        parts.append(f"Job Title: {recruitment.title}")
    if getattr(recruitment, "job_position_id", None) and recruitment.job_position_id:
        pos = recruitment.job_position_id.job_position
        if pos:
            parts.append(f"Position: {pos}")
    skills = []
    if getattr(recruitment, "skills", None):
        skills = list(recruitment.skills.values_list("title", flat=True))
    if skills:
        parts.append("Skills: " + ", ".join(skills))
    if getattr(recruitment, "description", None) and recruitment.description:
        parts.append(str(recruitment.description))
    return " ".join(parts) if parts else ""


def get_resume_text(resume):
    """
    Extract text from a Resume instance for semantic matching.
    Uses legacy extract_words_from_pdf; returns a single string (words joined).
    On failure (e.g. corrupt PDF), returns empty string.
    """
    from recruitment.services.legacy_resume_parser import extract_words_from_pdf

    try:
        words = extract_words_from_pdf(resume.file)
        return " ".join(words) if words else ""
    except Exception:
        return ""


def score_resumes_for_recruitment(recruitment, resumes, *, top_k=None):
    """
    Score and rank resumes for a given recruitment using semantic + keyword scores.

    Returns a list of dicts:
        {
            "resume": Resume,
            "keyword_score": int,      # matching_skills_count
            "semantic_score": float,    # 0–1
            "combined_score": float,    # 0–1, used for ordering
            "image_pdf": bool,
        }
    Resumes are not reordered here; caller partitions by is_candidate and sorts
    by combined_score within each group.
    """
    from recruitment.services.legacy_resume_parser import extract_words_from_pdf

    resumes = list(resumes)
    if not resumes:
        return []

    skills = list(recruitment.skills.values_list("title", flat=True))
    job_text = build_job_text(recruitment)
    resume_texts = []
    keyword_scores = []
    image_pdf_flags = []

    for resume in resumes:
        words = []
        try:
            words = extract_words_from_pdf(resume.file)
        except Exception:
            pass
        resume_text = " ".join(words) if words else ""
        resume_texts.append(resume_text)
        matching = sum(skill.lower() in words for skill in skills) if words else 0
        keyword_scores.append(matching)
        image_pdf_flags.append(len(words) == 0)

    backend = LocalSemanticMatchingBackend()
    semantic_scores = backend.score(job_text, resume_texts)

    max_kw = max(keyword_scores) if keyword_scores else 0
    weight = getattr(settings, "SEMANTIC_MATCHING_WEIGHT", 0.7)

    result = []
    for i, resume in enumerate(resumes):
        kw = keyword_scores[i]
        norm_kw = (kw / max_kw) if max_kw > 0 else 0
        sem = semantic_scores[i]
        combined = weight * sem + (1 - weight) * norm_kw
        combined = max(0.0, min(1.0, combined))
        result.append(
            {
                "resume": resume,
                "keyword_score": kw,
                "matching_skills_count": kw,  # backward compatibility for template
                "semantic_score": sem,
                "combined_score": combined,
                "image_pdf": image_pdf_flags[i],
            }
        )

    if top_k is not None:
        result = sorted(result, key=lambda x: x["combined_score"], reverse=True)[:top_k]
    return result


def get_ranked_resumes_for_view(recruitment, resumes):
    """
    Return ranked list for matching_resumes view: same structure as legacy
    (non_candidate first, then candidate; within each sorted by score).
    When semantic matching is enabled, uses combined_score; otherwise
    only keyword_score for ordering (handled in view).
    """
    scored = score_resumes_for_recruitment(recruitment, resumes)
    is_candidate_ids = {r["resume"].id for r in scored if r["resume"].is_candidate}
    non_candidate = [r for r in scored if r["resume"].id not in is_candidate_ids]
    candidate = [r for r in scored if r["resume"].id in is_candidate_ids]
    non_candidate.sort(key=lambda x: x["combined_score"], reverse=True)
    candidate.sort(key=lambda x: x["combined_score"], reverse=True)
    return non_candidate + candidate


# ---------------------------------------------------------------------------
# Similar candidates (search by example)
# ---------------------------------------------------------------------------


def _get_candidate_resume_text(candidate):
    """Extract text from candidate's resume file. Returns empty string on failure."""
    from recruitment.services.legacy_resume_parser import extract_words_from_pdf

    if not getattr(candidate, "resume", None) or not candidate.resume:
        return ""
    try:
        words = extract_words_from_pdf(candidate.resume)
        return " ".join(words) if words else ""
    except Exception:
        return ""


def build_candidate_text(candidate):
    """
    Build a single text representation of the candidate for semantic comparison.
    Uses resume text (from PDF) plus name, job position, recruitment title/skills.
    """
    parts = []
    if getattr(candidate, "name", None) and candidate.name:
        parts.append(f"Name: {candidate.name}")
    # Job position: from candidate or from recruitment
    position = None
    if getattr(candidate, "job_position_id", None) and candidate.job_position_id:
        position = getattr(candidate.job_position_id, "job_position", None)
    if (
        not position
        and getattr(candidate, "recruitment_id", None)
        and candidate.recruitment_id
    ):
        rec = candidate.recruitment_id
        if getattr(rec, "job_position_id", None) and rec.job_position_id:
            position = getattr(rec.job_position_id, "job_position", None)
    if position:
        parts.append(f"Position: {position}")
    # Recruitment title and skills
    if getattr(candidate, "recruitment_id", None) and candidate.recruitment_id:
        rec = candidate.recruitment_id
        if getattr(rec, "title", None) and rec.title:
            parts.append(f"Recruitment: {rec.title}")
        if getattr(rec, "skills", None):
            skills = list(rec.skills.values_list("title", flat=True))
            if skills:
                parts.append("Skills: " + ", ".join(skills))
    # Resume body
    resume_text = _get_candidate_resume_text(candidate)
    if resume_text:
        parts.append("Resume: " + resume_text)
    return " ".join(parts) if parts else ""


def find_similar_candidates(
    reference_candidate,
    candidate_queryset=None,
    *,
    top_k=None,
    exclude_self=True,
):
    """
    Return candidates ordered by similarity to reference_candidate (TF-IDF + cosine).

    Returns list of (candidate, similarity_score) sorted by score descending.
    """
    from recruitment.models import Candidate

    if candidate_queryset is None:
        candidate_queryset = Candidate.objects.filter(is_active=True)
    if exclude_self:
        candidate_queryset = candidate_queryset.exclude(pk=reference_candidate.pk)
    candidate_list = list(candidate_queryset)
    if not candidate_list:
        return []

    reference_text = build_candidate_text(reference_candidate)
    candidate_texts = [build_candidate_text(c) for c in candidate_list]
    backend = LocalSemanticMatchingBackend()
    scores = backend.score(reference_text, candidate_texts)
    pairs = list(zip(candidate_list, scores))
    pairs.sort(key=lambda x: x[1], reverse=True)
    if top_k is not None:
        pairs = pairs[:top_k]
    return pairs
