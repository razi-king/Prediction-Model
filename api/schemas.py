"""
Request/response shapes for the API (Pydantic validates the JSON automatically:
wrong types or out-of-range numbers are rejected with a clear 422 error).
"""
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class Profile(BaseModel):
    years_code: float = Field(ge=0, le=60, description="Total years of coding (incl. learning)")
    years_pro: float = Field(ge=0, le=50, description="Years of professional coding experience")
    role: str = Field(examples=["Full-stack"])
    country: str = Field(examples=["India"])
    ed_level: int = Field(ge=0, le=6, description="0=Primary ... 4=Bachelor, 5=Master, 6=PhD")
    skills: list[str] = Field(default_factory=list, examples=[["JavaScript", "React", "Node.js"]])


class Goal(BaseModel):
    type: Literal["level", "salary"] = "level"
    level: Literal["Junior", "Mid", "Senior", "Lead"] | None = "Senior"
    salary: float | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def check(self):
        if self.type == "salary" and not self.salary:
            raise ValueError("goal.salary is required when goal.type is 'salary'")
        if self.type == "level" and not self.level:
            raise ValueError("goal.level is required when goal.type is 'level'")
        return self


class PlanRequest(BaseModel):
    profile: Profile
    hours_per_week: float = Field(default=10, ge=0, le=80)
    goal: Goal = Goal()
    plan: list[str] | None = Field(
        default=None, description="Skills to learn in order. Empty = use the recommended roadmap.")
