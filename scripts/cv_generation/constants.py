DEFAULT_PAGE_MARGIN = "0.55in"

DEFAULT_SECTION_ORDERS: dict[str, list[str]] = {
    "technical_ml": [
        "education", "technical_skills", "experience", "projects", "achievements", "certifications",
    ],
    "software_engineering": [
        "education", "technical_skills", "experience", "projects", "achievements", "certifications",
    ],
    "data_science": [
        "profile", "education", "technical_skills", "experience", "projects", "achievements",
        "certifications",
    ],
    "startup_events": [
        "profile", "education", "experience", "projects", "leadership_volunteering_outreach",
        "skills",
    ],
    "leadership_community": [
        "profile", "education", "experience", "leadership", "volunteering",
        "leadership_volunteering_outreach", "skills", "achievements",
    ],
    "general": [
        "profile", "education", "skills", "experience", "projects", "leadership", "volunteering",
        "achievements", "certifications",
    ],
}

SECTION_TITLES: dict[str, str] = {
    "profile": "Profile",
    "education": "Education",
    "technical_skills": "Technical Skills",
    "skills": "Skills",
    "experience": "Experience",
    "projects": "Projects",
    "volunteering": "Volunteering",
    "leadership": "Leadership",
    "achievements": "Achievements",
    "certifications": "Certifications",
}
