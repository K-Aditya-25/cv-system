from typing import Literal

from pydantic import Field

from schemas.base import StrictBaseModel

CvVariant = Literal[
    "technical_ml",
    "software_engineering",
    "data_science",
    "startup_events",
    "leadership_community",
    "general",
]


class JobConfig(StrictBaseModel):
    company: str = Field(min_length=1)
    role: str = Field(min_length=1)
    location: str | None = None
    cv_length: str = Field(default="one_page")
    cv_variant: CvVariant = "general"
    target_profile: str | None = None
    output_name: str = Field(min_length=1)
    template: str = Field(default="cv_template.tex.j2")
    sections_order: list[str] | None = None
    include_coursework: bool = False
    include_education_bullets: bool = False
    show_experience_technologies: bool = False
    show_project_technologies: bool = False
    page_margin: str | None = None
