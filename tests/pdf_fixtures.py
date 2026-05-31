import json

from schemas.career_schema import CareerDatabase, JobConfig


def minimal_database() -> CareerDatabase:
    return CareerDatabase.model_validate(
        {"profile": {"name": "Alex Example", "email": "alex@example.com"}}
    )


def database_with_skills() -> CareerDatabase:
    return CareerDatabase.model_validate(
        {
            "profile": {"name": "Alex Example", "email": "alex@example.com"},
            "skills": {
                "machine_learning": ["Interpretability", "SHAP"],
                "ai_llm_engineering": ["Explainable AI", "LLMs"],
            },
        }
    )


def minimal_job_config() -> JobConfig:
    return JobConfig.model_validate(
        {"company": "Target", "role": "Engineer", "output_name": "target_engineer"}
    )


def llm_payload() -> str:
    return json.dumps(
        {
            "job_config": {
                "company": "Target", "role": "Engineer", "location": None,
                "cv_length": "one_page", "cv_variant": "general", "target_profile": None,
                "output_name": "target_engineer", "template": "cv_template.tex.j2",
                "sections_order": ["education", "experience", "projects", "skills"],
                "include_coursework": False, "include_education_bullets": False,
                "show_experience_technologies": False, "show_project_technologies": False,
                "page_margin": None,
            },
            "selection": {},
            "job_summary_text": "Target engineer role.",
            "selection_rationale": ["Reduced content for a one-page CV."],
        }
    )
