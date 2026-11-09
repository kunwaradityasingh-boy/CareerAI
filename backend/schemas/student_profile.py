from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StudentProfileUpsert(BaseModel):
    college_name: str = Field(min_length=1, max_length=150)
    degree: str = Field(min_length=1, max_length=100)
    branch: str = Field(min_length=1, max_length=120)
    graduation_year: int = Field(ge=2000, le=2100)

    target_role: str = Field(min_length=1, max_length=120)
    preferred_industry: str = Field(min_length=1, max_length=120)

    technical_skills: list[str] = Field(min_length=1, max_length=100)
    career_interests: list[str] = Field(min_length=1, max_length=50)

    @field_validator(
        "college_name",
        "degree",
        "branch",
        "target_role",
        "preferred_industry",
        mode="before",
    )
    @classmethod
    def validate_required_text(cls, value):
        if not isinstance(value, str):
            raise ValueError("This field is required.")

        value = value.strip()

        if not value:
            raise ValueError("This field cannot be empty.")

        return value

    @field_validator("technical_skills", "career_interests")
    @classmethod
    def normalize_string_lists(cls, values: list[str]) -> list[str]:
        normalized = []
        seen = set()

        for item in values:
            item = item.strip()

            if not item:
                continue

            if len(item) > 100:
                raise ValueError("Each list item must be at most 100 characters.")

            key = item.casefold()

            if key not in seen:
                normalized.append(item)
                seen.add(key)

        if not normalized:
            raise ValueError("At least one value is required.")

        return normalized


class StudentProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int

    college_name: str | None
    degree: str | None
    branch: str | None
    graduation_year: int | None

    target_role: str | None
    preferred_industry: str | None

    technical_skills: list[str]
    career_interests: list[str]

    created_at: datetime
    updated_at: datetime
