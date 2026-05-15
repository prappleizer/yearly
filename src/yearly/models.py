from typing import Optional

from pydantic import BaseModel, field_validator

# ─── Tag models ──────────────────────────────────────────────────────────────


class TagCreate(BaseModel):
    name: str
    color: Optional[str] = "#6b7280"


class TagUpdate(BaseModel):
    name: Optional[str] = None
    color: Optional[str] = None
    sort_order: Optional[int] = None


class Tag(BaseModel):
    id: int
    name: str
    color: str
    sort_order: int
    created_at: Optional[str] = None


# ─── Event models ─────────────────────────────────────────────────────────────


class EventCreate(BaseModel):
    title: str
    start_date: str  # "YYYY-MM-DD"
    end_date: str
    tag_id: Optional[int] = None
    is_travel: bool = False
    is_preliminary: bool = False
    description: Optional[str] = None

    @field_validator("end_date")
    @classmethod
    def end_after_start(cls, v, info):
        start = info.data.get("start_date")
        if start and v < start:
            raise ValueError("end_date must be >= start_date")
        return v


class EventUpdate(BaseModel):
    title: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    tag_id: Optional[int] = None
    is_travel: Optional[bool] = None
    is_preliminary: Optional[bool] = None
    description: Optional[str] = None


class Event(BaseModel):
    id: int
    title: str
    start_date: str
    end_date: str
    tag_id: Optional[int] = None
    is_travel: int  # kept as 0/1 so the JS side stays unchanged
    is_preliminary: int
    description: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    tag_name: Optional[str] = None
    tag_color: Optional[str] = None
