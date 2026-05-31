from pydantic import Field, model_validator

from schemas.base import StrictBaseModel
from schemas.common import Bullet, Link
from schemas.validators import ensure_unique_ids


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
