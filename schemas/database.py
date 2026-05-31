from pydantic import Field, field_validator, model_validator

from schemas.base import StrictBaseModel
from schemas.common import Profile
from schemas.custom_sections import CustomSection
from schemas.primary_items import EducationItem, ExperienceItem, ProjectItem
from schemas.secondary_items import AchievementItem, CertificationItem, LeadershipItem, VolunteeringItem
from schemas.validators import ensure_unique_ids, find_duplicates


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
