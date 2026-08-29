"""ProvisionedAccountEntry model — permits a Microsoft account to sign in and states its role(s)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

VALID_ROLES = {"Player", "Administrator"}


@dataclass
class ProvisionedAccountEntry:
    email: str
    roles: list[str]
    objectId: Optional[str] = None
    dateAdded: Optional[str] = None
    addedBy: Optional[str] = None
    dateBound: Optional[str] = None
    id: Optional[str] = None
    entityType: str = field(default="ProvisionedAccountEntry")

    def __post_init__(self) -> None:
        if not self.email:
            raise ValueError("email is required")
        self.email = self.email.lower()
        if not self.roles:
            raise ValueError("roles must contain at least one of " f"{sorted(VALID_ROLES)}")
        invalid = set(self.roles) - VALID_ROLES
        if invalid:
            raise ValueError(f"roles must be drawn from {sorted(VALID_ROLES)}, got invalid: {sorted(invalid)}")
        self.id = self.email

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "email": self.email,
            "roles": self.roles,
            "objectId": self.objectId,
            "dateAdded": self.dateAdded,
            "addedBy": self.addedBy,
            "dateBound": self.dateBound,
            "entityType": self.entityType,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProvisionedAccountEntry":
        return cls(
            email=data["email"],
            roles=list(data.get("roles", [])),
            objectId=data.get("objectId"),
            dateAdded=data.get("dateAdded"),
            addedBy=data.get("addedBy"),
            dateBound=data.get("dateBound"),
            id=data.get("id"),
        )
