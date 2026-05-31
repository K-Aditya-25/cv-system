from pydantic import Field, field_validator

from schemas.base import StrictBaseModel


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
