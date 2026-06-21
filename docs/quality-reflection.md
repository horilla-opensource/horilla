# Quality Reflection
**Candidate:** Purabh Singh  
**Project:** Horilla HRMS — DeepThought QA Fellowship  
**Date:** 2026-06-21

---

## 1. My Personal Testing Habits

I test from the outside in. Before I open a codebase, I try to become the most confused user who could ever land on a screen. I ask: what does this form do if I submit it empty? What happens if I navigate directly to a URL I shouldn't? What does the system tell me when something goes wrong?

My habit is to always test the **silent failure** first — the case where the system accepts bad input and says nothing. These are the bugs that reach production because every automated test only checks the happy path. On this project, that habit found Defect E: accessing `/payroll/create-payslip/` via GET silently reloads the page and creates no record. No error. No alert. Just silence. A payroll operator would assume the payslip was created.

I also keep a bug journal — not a formal tracker, just a running note of things that felt wrong while I was doing something else. Two of the five defects in QA-302 came from noticing something during unrelated exploration and writing it down before I forgot.

---

## 2. A Production Bug Story

During a personal project involving a batch data-processing script, I introduced a bug that corrupted output records silently. The script looped over a list of items and modified a shared variable inside the loop body — the exact same class of bug as Defect B in this project (`start_date` mutation in `generate_payslip`).

The bug ran undetected for two weeks because the first item in every batch always processed correctly, and spot-checking only looked at the first few results. It was only when a downstream consumer flagged inconsistencies in item counts that we traced it back to the loop variable.

The lesson I carry: **a bug that only affects items after the first one in a batch is one of the hardest to find manually**, because human reviewers almost always start from the top. Automated tests that assert all items — not just the first — are the only reliable defence. That is exactly what `test_bulk_payslip_start_date.py` does.

---

## 3. The One Thing This Team Needs Most

Based on everything I investigated in Horilla's payroll module, the single highest-leverage improvement this team could make is:

**Validation at the boundary — before data enters the system, not after it corrupts the output.**

Right now, invalid overtime values, overlapping contracts, and incomplete attendance records all pass through every layer of the system without being challenged. The bugs I found are not complex — they are simple missing guards. A `MinValueValidator` here, a `clean()` method there, a method-check on a view. None of these require architectural changes. But each one would prevent a class of silent failure that currently reaches the payslip.

The team needs a shared norm: **every form field that feeds into a financial calculation must have an explicit validation test.** Not just "does it save?" — but "does it reject invalid input with a clear error message?"

---

## 4. How I Would Convince a Senior Developer That QA Matters

I would not argue in the abstract. I would open the codebase and show them `find_half_day_leaves()` in `payroll/methods/methods.py`.

```python
def find_half_day_leaves(*args, **kwargs):
    return 0, 0
```

Then I would ask: "When did this get stubbed? Does anyone know? Has it been like this in production? How many months of payslips have been generated without half-day leave deductions? How much has the company overpaid?"

That question — not a presentation, not a theory — would end the conversation. QA matters not because it is a process checkbox, but because a stubbed function returning zeros has been silently computing wrong salaries for every employee who ever took a half-day leave. That is a financial liability. That is a legal risk. And the only reason we know it exists is because someone read the code with the intent to find what was broken.

That is what QA is.

---

## 5. A Personal Systems-Thinking Example

When I began this assessment, I mapped every module in Horilla before writing a single test case. Most people start with the login page or the employee list. I started with the question: *what is the final output that every other thing feeds into?*

The answer — the payslip — changed everything about how I approached the audit. Instead of testing features in isolation, I traced each module's data forward to the payslip: does attendance reach it? Do contracts feed it? What happens when leave records are missing? What happens when two contracts exist for the same employee?

This systems lens produced findings that a feature-by-feature test approach would have missed entirely. Defect B (bulk start_date mutation) is only visible when you think about what happens across multiple employees in the same batch — not when you test one employee at a time. Defect D (stubbed leave calculation) is only visible when you ask "what does each function actually return?" rather than "does the form submit?"

Systems thinking in QA means asking: **where does this data go, who depends on it, and what breaks downstream if it is wrong?** That question, asked consistently, found five payroll defects that were not on any bug tracker and may not have been discovered before this assessment.
