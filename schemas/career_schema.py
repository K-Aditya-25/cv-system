from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Link(StrictBaseModel):
    label: str = Field(min_length=1)
    url: str = Field(min_length=1)


class Bullet(StrictBaseModel):
    id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    tags: list[str] = Field(default_factory=list)
    strength: int = Field(ge=1, le=5)


class Profile(StrictBaseModel):
    name: str = Field(min_length=1)
    email: str = Field(min_length=1)
    phone: str | None = None
    location: str | None = None
    linkedin: str | None = None
    github: str | None = None
    portfolio: str | None = None
    blog: str | None = None
    kaggle: str | None = None
    devpost: str | None = None
    summary: str | None = None
    extra_links: list[Link] = Field(default_factory=list)


class EducationItem(StrictBaseModel):
    id: str = Field(min_length=1)
    institution: str = Field(min_length=1)
    location: str | None = None
    degree: str = Field(min_length=1)
    start_date: str | None = None
    end_date: str | None = None
    grade: str | None = None
    coursework: list[str] = Field(default_factory=list)
    bullets: list[Bullet] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_bullet_ids(self) -> "EducationItem":
        ensure_unique_ids(self.bullets, f"education.{self.id}.bullets")
        return self


class ExperienceItem(StrictBaseModel):
    id: str = Field(min_length=1)
    company: str = Field(min_length=1)
    title: str = Field(min_length=1)
    location: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    summary: str | None = None
    technologies: list[str] = Field(default_factory=list)
    bullets: list[Bullet] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_bullet_ids(self) -> "ExperienceItem":
        ensure_unique_ids(self.bullets, f"experience.{self.id}.bullets")
        return self


class ProjectItem(StrictBaseModel):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    date: str | None = None
    category: str | None = None
    subtitle: str | None = None
    description: str | None = None
    technologies: list[str] = Field(default_factory=list)
    links: list[Link] = Field(default_factory=list)
    bullets: list[Bullet] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_bullet_ids(self) -> "ProjectItem":
        ensure_unique_ids(self.bullets, f"projects.{self.id}.bullets")
        return self


class VolunteeringItem(StrictBaseModel):
    id: str = Field(min_length=1)
    organization: str = Field(min_length=1)
    role: str = Field(min_length=1)
    location: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    bullets: list[Bullet] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_bullet_ids(self) -> "VolunteeringItem":
        ensure_unique_ids(self.bullets, f"volunteering.{self.id}.bullets")
        return self


class LeadershipItem(StrictBaseModel):
    id: str = Field(min_length=1)
    organization: str = Field(min_length=1)
    role: str = Field(min_length=1)
    location: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    bullets: list[Bullet] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_bullet_ids(self) -> "LeadershipItem":
        ensure_unique_ids(self.bullets, f"leadership.{self.id}.bullets")
        return self


class AchievementItem(StrictBaseModel):
    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    issuer: str | None = None
    date: str | None = None
    description: str = Field(min_length=1)
    tags: list[str] = Field(default_factory=list)
    strength: int = Field(ge=1, le=5)


class CertificationItem(StrictBaseModel):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    issuer: str | None = None
    date: str | None = None
    credential_url: str | None = None
    tags: list[str] = Field(default_factory=list)
    strength: int = Field(ge=1, le=5)


class CustomSectionItem(StrictBaseModel):
    id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    tags: list[str] = Field(default_factory=list)
    strength: int = Field(ge=1, le=5)


class CustomSection(StrictBaseModel):
    title: str = Field(min_length=1)
    items: list[CustomSectionItem] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_item_ids(self) -> "CustomSection":
        ensure_unique_ids(self.items, f"custom_sections.{self.title}.items")
        return self


class CareerDatabase(StrictBaseModel):
    profile: Profile
    education: list[EducationItem] = Field(default_factory=list)
    experience: list[ExperienceItem] = Field(default_factory=list)
    projects: list[ProjectItem] = Field(default_factory=list)
    skills: dict[str, list[str]] = Field(default_factory=dict)
    volunteering: list[VolunteeringItem] = Field(default_factory=list)
    leadership: list[LeadershipItem] = Field(default_factory=list)
    achievements: list[AchievementItem] = Field(default_factory=list)
    certifications: list[CertificationItem] = Field(default_factory=list)
    custom_sections: dict[str, CustomSection] = Field(default_factory=dict)

    @field_validator("skills")
    @classmethod
    def validate_skills(cls, skills: dict[str, list[str]]) -> dict[str, list[str]]:
        for category, values in skills.items():
            if not category.strip():
                raise ValueError("skills category names must not be empty")
            if not isinstance(values, list) or not values:
                raise ValueError(f"skills.{category} must be a non-empty list")
            duplicates = find_duplicates(values)
            if duplicates:
                raise ValueError(f"skills.{category} has duplicate values: {', '.join(duplicates)}")
            for value in values:
                if not isinstance(value, str) or not value.strip():
                    raise ValueError(f"skills.{category} contains an empty skill")
        return skills

    @model_validator(mode="after")
    def validate_top_level_ids(self) -> "CareerDatabase":
        ensure_unique_ids(self.education, "education")
        ensure_unique_ids(self.experience, "experience")
        ensure_unique_ids(self.projects, "projects")
        ensure_unique_ids(self.volunteering, "volunteering")
        ensure_unique_ids(self.leadership, "leadership")
        ensure_unique_ids(self.achievements, "achievements")
        ensure_unique_ids(self.certifications, "certifications")
        return self


class SelectionWithBullets(StrictBaseModel):
    id: str = Field(min_length=1)
    bullets: list[str] = Field(default_factory=list)


class Selection(StrictBaseModel):
    education: list[str] = Field(default_factory=list)
    experience: list[SelectionWithBullets] = Field(default_factory=list)
    projects: list[SelectionWithBullets] = Field(default_factory=list)
    skills: dict[str, list[str]] = Field(default_factory=dict)
    volunteering: list[str] = Field(default_factory=list)
    leadership: list[str] = Field(default_factory=list)
    achievements: list[str] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    custom_sections: dict[str, list[str]] = Field(default_factory=dict)

    @field_validator("skills")
    @classmethod
    def validate_selected_skills(cls, skills: dict[str, list[str]]) -> dict[str, list[str]]:
        for category, values in skills.items():
            if not category.strip():
                raise ValueError("selected skills category names must not be empty")
            if not isinstance(values, list):
                raise ValueError(f"selected skills.{category} must be a list")
            for value in values:
                if not isinstance(value, str) or not value.strip():
                    raise ValueError(f"selected skills.{category} contains an empty skill")
        return skills


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


def ensure_unique_ids(items: list[object], section_name: str) -> None:
    ids = [getattr(item, "id") for item in items]
    duplicates = find_duplicates(ids)
    if duplicates:
        raise ValueError(f"{section_name} has duplicate IDs: {', '.join(duplicates)}")


def find_duplicates(values: list[str]) -> list[str]:
    seen: set[str] = set()
    duplicates: list[str] = []
    for value in values:
        if value in seen and value not in duplicates:
            duplicates.append(value)
        seen.add(value)
    return duplicates
