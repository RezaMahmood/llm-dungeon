"""AllowListEntry model — a record permitting a Microsoft account to sign in."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class AllowListEntry:
    user_oid: str
    email: Optional[str] = None
    dateAdded: Optional[str] = None
    dateRemoved: Optional[str] = None
    addedBy: Optional[str] = None
    removedBy: Optional[str] = None
    notes: Optional[str] = None
    id: Optional[str] = None
    entityType: str = field(default="AllowListEntry")

    def __post_init__(self) -> None:
        if not self.user_oid:
            raise ValueError("user_oid is required")
        if self.id is None:
            self.id = self.user_oid

    def is_active(self) -> bool:
        return self.dateRemoved is None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "user_oid": self.user_oid,
            "email": self.email,
            "dateAdded": self.dateAdded,
            "dateRemoved": self.dateRemoved,
            "addedBy": self.addedBy,
            "removedBy": self.removedBy,
            "notes": self.notes,
            "entityType": self.entityType,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AllowListEntry":
        return cls(
            user_oid=data["user_oid"],
            email=data.get("email"),
            dateAdded=data.get("dateAdded"),
            dateRemoved=data.get("dateRemoved"),
            addedBy=data.get("addedBy"),
            removedBy=data.get("removedBy"),
            notes=data.get("notes"),
            id=data.get("id"),
        )
