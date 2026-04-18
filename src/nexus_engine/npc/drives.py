from __future__ import annotations

from dataclasses import dataclass, field

from nexus_engine.core.event import Event
from nexus_engine.core.value_objects import EntityId, GameTime


DRIVE_SURVIVAL = "survival"
DRIVE_SOCIAL = "social"
DRIVE_PRESTIGE = "prestige"
DRIVE_KNOWLEDGE = "knowledge"
DRIVE_GOODS = "goods"
DRIVE_FREEDOM = "freedom"


@dataclass
class NPCDrive:
    drive_id: str
    intensity: float
    saturation: float = 0.0

    def __post_init__(self):
        self.intensity = max(0.0, min(1.0, self.intensity))
        self.saturation = max(0.0, min(1.0, self.saturation))


@dataclass
class DriveState:
    drives: dict[str, NPCDrive] = field(default_factory=dict)

    def get(self, drive_id: str) -> NPCDrive | None:
        return self.drives.get(drive_id)

    def set(self, drive_id: str, intensity: float, saturation: float = 0.0) -> None:
        self.drives[drive_id] = NPCDrive(drive_id, intensity, saturation)

    def update(self, drive_id: str, intensity_delta: float) -> None:
        if drive_id in self.drives:
            current = self.drives[drive_id]
            self.drives[drive_id] = NPCDrive(
                drive_id,
                max(0.0, min(1.0, current.intensity + intensity_delta)),
                current.saturation,
            )


@dataclass
class NPCContext:
    world_time: GameTime
    current_location: EntityId
    player_location: EntityId | None = None
    recent_events: list[Event] = field(default_factory=list)


def calculate_drive_change(
    drive: NPCDrive,
    event: Event,
    context: NPCContext,
) -> float:
    event_type = event.type.value

    if event_type == "threat_detected":
        if drive.drive_id == DRIVE_SURVIVAL:
            return +0.3
    elif event_type == "social_interaction":
        if drive.drive_id == DRIVE_SOCIAL:
            return +0.2 * event.mechanics.degree
    elif event_type == "combat":
        if drive.drive_id == DRIVE_SURVIVAL:
            return -0.1
    elif event_type == "acquisition":
        if drive.drive_id == DRIVE_GOODS:
            return +0.2
    elif event_type == "knowledge_gained":
        if drive.drive_id == DRIVE_KNOWLEDGE:
            return +0.2

    return -0.01


def get_default_drives() -> dict[str, NPCDrive]:
    return {
        DRIVE_SURVIVAL: NPCDrive(DRIVE_SURVIVAL, 0.5, 0.0),
        DRIVE_SOCIAL: NPCDrive(DRIVE_SOCIAL, 0.3, 0.0),
        DRIVE_PRESTIGE: NPCDrive(DRIVE_PRESTIGE, 0.3, 0.0),
        DRIVE_KNOWLEDGE: NPCDrive(DRIVE_KNOWLEDGE, 0.2, 0.0),
        DRIVE_GOODS: NPCDrive(DRIVE_GOODS, 0.4, 0.0),
        DRIVE_FREEDOM: NPCDrive(DRIVE_FREEDOM, 0.2, 0.0),
    }


def select_dominant_drive(drive_state: DriveState) -> NPCDrive | None:
    if not drive_state.drives:
        return None
    return max(drive_state.drives.values(), key=lambda d: d.intensity * (1 - d.saturation))
