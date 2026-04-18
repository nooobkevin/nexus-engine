from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from nexus_engine.core.entity import Entity
from nexus_engine.core.event import Event
from nexus_engine.core.value_objects import EntityId, GameTime
from nexus_engine.npc.drives import NPCContext
from nexus_engine.npc.ensemble import npc_tick


class RegionType(str, Enum):
    ACTIVE = "active"
    NEARBY = "nearby"
    DISTANT = "distant"


@dataclass
class Region:
    region_id: str
    region_type: RegionType
    npcs: list[Entity] = field(default_factory=list)
    locations: list[EntityId] = field(default_factory=list)
    pending_events: list[Event] = field(default_factory=list)


@dataclass
class RegionConfig:
    active_radius: int = 5
    nearby_radius: int = 20


def partition_by_player_proximity(
    all_regions: list[Region],
    player_location: EntityId,
    config: RegionConfig | None = None,
) -> dict[RegionType, list[Region]]:
    if config is None:
        config = RegionConfig()

    active: list[Region] = []
    nearby: list[Region] = []
    distant: list[Region] = []

    for region in all_regions:
        if region.region_type == RegionType.ACTIVE:
            active.append(region)
        elif region.region_type == RegionType.NEARBY:
            nearby.append(region)
        else:
            distant.append(region)

    return {
        RegionType.ACTIVE: active,
        RegionType.NEARBY: nearby,
        RegionType.DISTANT: distant,
    }


async def fast_forward_region(region: Region, delta: int) -> list[Event]:
    events: list[Event] = []

    for npc in region.npcs:
        context = NPCContext(
            world_time=GameTime(delta),
            current_location=region.locations[0] if region.locations else EntityId(),
        )
        npc_events = await npc_tick(npc, delta, context)
        events.extend(npc_events)

    return events


async def process_scheduled_only(region: Region, delta: int) -> list[Event]:
    return region.pending_events.copy()
