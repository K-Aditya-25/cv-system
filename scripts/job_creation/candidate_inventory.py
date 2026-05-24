from __future__ import annotations

from typing import Any
import yaml

from schemas.career_schema import CareerDatabase
from .inventory_compact import compact_bullets


def _custom_sections(database: CareerDatabase) -> dict[str, Any]:
    return {
        key: {
            "title": section.title,
            "items": [
                {"id": item.id, "text": item.text, "tags": item.tags, "strength": item.strength}
                for item in section.items
            ],
        }
        for key, section in database.custom_sections.items()
    }


def _education(database: CareerDatabase) -> list[dict[str, Any]]:
    return [
        {
            "id": item.id,
            "institution": item.institution,
            "degree": item.degree,
            "coursework": item.coursework,
            "bullets": [
                {
                    "id": bullet.id,
                    "text": bullet.text,
                    "tags": bullet.tags,
                    "strength": bullet.strength,
                }
                for bullet in item.bullets
            ],
        }
        for item in database.education
    ]


def _achievements(database: CareerDatabase) -> list[dict[str, Any]]:
    return [
        {
            "id": item.id,
            "title": item.title,
            "description": item.description,
            "tags": item.tags,
            "strength": item.strength,
        }
        for item in database.achievements
    ]


def _certifications(database: CareerDatabase) -> list[dict[str, Any]]:
    return [
        {
            "id": item.id,
            "name": item.name,
            "issuer": item.issuer,
            "tags": item.tags,
            "strength": item.strength,
        }
        for item in database.certifications
    ]


def allowed_section_keys(database: CareerDatabase) -> list[str]:
    base = [
        "profile", "education", "technical_skills", "skills", "experience",
        "projects", "volunteering", "leadership", "achievements", "certifications",
    ]
    return list(dict.fromkeys([*base, *database.custom_sections.keys()]))


def build_candidate_inventory(database: CareerDatabase) -> str:
    inventory = {
        "profile_summary": database.profile.summary,
        "education": _education(database),
        "experience": compact_bullets(database.experience),
        "projects": compact_bullets(database.projects),
        "skills": database.skills,
        "volunteering": compact_bullets(database.volunteering),
        "leadership": compact_bullets(database.leadership),
        "achievements": _achievements(database),
        "certifications": _certifications(database),
        "custom_sections": _custom_sections(database),
        "allowed_cv_variants": [
            "technical_ml", "software_engineering", "data_science",
            "startup_events", "leadership_community", "general",
        ],
        "allowed_section_keys": allowed_section_keys(database),
    }
    return yaml.safe_dump(inventory, sort_keys=False, allow_unicode=True)
