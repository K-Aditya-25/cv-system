from pydantic import Field, model_validator

from schemas.base import StrictBaseModel
from schemas.common import Bullet
from schemas.validators import ensure_unique_ids


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
