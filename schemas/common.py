from pydantic import Field

from schemas.base import StrictBaseModel


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
