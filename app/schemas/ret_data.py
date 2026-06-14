"""Common ``RetData`` envelope used by every endpoint (port of ``RetDataDto``)."""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class RetData(BaseModel, Generic[T]):
    data: T | None = None
    message: str = ""
    type: str = "info"


class RetDataFilePayload(BaseModel):
    filename: str


class RetDataFile(BaseModel):
    data: RetDataFilePayload | None = None
    message: str = ""
    type: str = "info"


class RetDataFilesPayload(BaseModel):
    files: list[Any] = Field(default_factory=list)


class RetDataFiles(BaseModel):
    data: RetDataFilesPayload | None = None
    message: str = ""
    type: str = "info"


class CookiePayload(BaseModel):
    accessToken: str
    refreshToken: str | None = None


class RetDataUser(BaseModel):
    cookie: CookiePayload
    data: Any | None = None
    message: str = ""
    type: str = "info"
