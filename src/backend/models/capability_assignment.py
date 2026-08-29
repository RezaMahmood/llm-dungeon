"""CapabilityAssignment model — grants a capability role to an allow-listed user."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

VALID_CAPABILITIES = {"Player", "Administrator"}


@dataclass
class CapabilityAssignment:
    user_oid: str
    capability: str
    dateAssigned: Optional[str] = None
    dateRevoked: Optional[str] = None
    assignedBy: Optional[str] = None
    revokedBy: Optional[str] = None
    id: Optional[str] = None
    entityType: str = field(default="CapabilityAssignment")

    def __post_init__(self) -> None:
        if not self.user_oid:
            raise ValueError("user_oid is required")
        if self.capability not in VALID_CAPABILITIES:
            raise ValueError(
                f"capability must be one of {sorted(VALID_CAPABILITIES)}, got {self.capability!r}"
            )
        if self.id is None:
            self.id = f"capability-{self.user_oid}-{self.capability}"

    def is_active(self) -> bool:
        return self.dateRevoked is None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "user_oid": self.user_oid,
            "capability": self.capability,
            "dateAssigned": self.dateAssigned,
            "dateRevoked": self.dateRevoked,
            "assignedBy": self.assignedBy,
            "revokedBy": self.revokedBy,
            "entityType": self.entityType,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CapabilityAssignment":
        return cls(
            user_oid=data["user_oid"],
            capability=data["capability"],
            dateAssigned=data.get("dateAssigned"),
            dateRevoked=data.get("dateRevoked"),
            assignedBy=data.get("assignedBy"),
            revokedBy=data.get("revokedBy"),
            id=data.get("id"),
        )
