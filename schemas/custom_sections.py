from pydantic import Field, model_validator

from schemas.base import StrictBaseModel
from schemas.validators import ensure_unique_ids


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
