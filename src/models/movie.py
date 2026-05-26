from pydantic import BaseModel, Field
from typing import Optional


class Movie(BaseModel):
    id: int
    title: str
    genre: str
    duration: int
    age_restriction: int
    poster_url: Optional[str] = None


class MovieCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    genre: str = Field(..., min_length=1, max_length=100)
    duration: int = Field(..., gt=0)
    age_restriction: int = Field(..., ge=0, le=18)
    poster_url: Optional[str] = Field(None, max_length=500)


class MovieUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    genre: Optional[str] = Field(None, min_length=1, max_length=100)
    duration: Optional[int] = Field(None, gt=0)
    age_restriction: Optional[int] = Field(None, ge=0, le=18)
    poster_url: Optional[str] = Field(None, max_length=500)
