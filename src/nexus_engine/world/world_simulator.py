from __future__ import annotations


from nexus_engine.core.event import Event
from nexus_engine.core.value_objects import EntityId, GameTime
from nexus_engine.world.director import Director, Scheduler, WorldConfig
from nexus_engine.world.region import Region, RegionType, partition_by_player_proximity


class WorldSimulator:
    def __init__(
        self,
        config: WorldConfig | None = None,
        director: Director | None = None,
    ):
        self.config = config or WorldConfig()
        self.director = director or Director()
        self.scheduler = Scheduler()
        self.world_regions: list[Region] = []
        self.player_location: EntityId | None = None
        self._tick_count = 0
        self._game_time = GameTime(0)

    def set_player_location(self, location: EntityId) -> None:
        self.player_location = location

    def add_region(self, region: Region) -> None:
        self.world_regions.append(region)

    async def advance_time(self, delta: int) -> list[Event]:
        all_events: list[Event] = []
        self._tick_count += delta
        self._game_time = GameTime(self._game_time.ticks + delta)

        regions = partition_by_player_proximity(
            self.world_regions,
            self.player_location or EntityId(),
            self.config.proximity_config,
        )

        for region in regions.get(RegionType.ACTIVE, []):
            for npc in region.npcs:
                from nexus_engine.npc.drives import NPCContext
                context = NPCContext(
                    world_time=self._game_time,
                    current_location=region.locations[0] if region.locations else EntityId(),
                    player_location=self.player_location,
                )
                events = await npc.tick(delta, context)
                all_events.extend(events)

        for region in regions.get(RegionType.NEARBY, []):
            from nexus_engine.world.region import fast_forward_region
            events = await fast_forward_region(region, delta)
            all_events.extend(events)

        for region in regions.get(RegionType.DISTANT, []):
            from nexus_engine.world.region import process_scheduled_only
            events = await process_scheduled_only(region, delta)
            all_events.extend(events)

        if self.director.should_invoke(self._tick_count):
            blueprint = await self.director.plan(self, {})
            self.scheduler.ingest(blueprint)

        return all_events

    @property
    def game_time(self) -> GameTime:
        return self._game_time
