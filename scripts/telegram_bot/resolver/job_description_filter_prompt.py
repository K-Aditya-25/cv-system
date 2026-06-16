from __future__ import annotations

import json


def system_prompt() -> str:
    example = {
        "job_description": "What you will accomplish\nBuild reliable backend services.\n\n"
        "What you will bring\nPython, SQL, and distributed systems fundamentals.\n\n"
        "Recruiting Process\nCoding Assessment\nTechnical Interview\n\n"
        "Additional Details\nEqual opportunity employer.",
        "confidence": 0.92,
        "reason": "kept role sections and removed LinkedIn chrome",
    }
    return (
        "You extract the actual job description from noisy job-board page text. Return JSON only "
        "with keys job_description, confidence, and reason. Preserve source wording and section "
        "headings; do not summarize or invent. Keep About, responsibilities, requirements, "
        "What you will accomplish, What you will bring, Recruiting Process, and Additional "
        "Details when present. A heading without its following bullets is a failure. Remove "
        "all HTML tags such as <br>, <strong>, <ul>, and <li>; return plain text only. Remove "
        "navigation, sign-in text, related jobs, job cards, footer links, Industries, and bare "
        "category metadata. Example JSON: "
        f"{json.dumps(example, ensure_ascii=False)}"
    )


def user_prompt(source: str) -> str:
    return (
        "Clean this noisy visible page text into the actual job description:\n"
        f"<source>\n{source}\n</source>"
    )
