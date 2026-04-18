from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from nexus_engine.core.value_objects import EntityId, GameTime


@dataclass
class ToolResult:
    success: bool
    data: Any = None
    error: str | None = None


class AgentTool(ABC):
    name: str = ""
    description: str = ""
    input_schema: dict[str, Any] = {}

    @abstractmethod
    async def execute(self, params: dict[str, Any], context: AgentContext) -> ToolResult:
        pass


@dataclass
class AgentContext:
    state_view: Any
    event_store: Any
    memory_system: Any | None = None
    setting_pack: Any | None = None
    game_time: GameTime = field(default_factory=lambda: GameTime(0))
    current_location: EntityId | None = None
    player_id: EntityId | None = None


class FindEntityTool(AgentTool):
    name = "find_entity"
    description = "Find entities matching criteria"
    input_schema = {
        "type": "object",
        "properties": {
            "archetype": {"type": "string"},
            "filters": {"type": "object", "properties": {}},
        },
        "required": ["archetype"],
    }

    async def execute(self, params: dict[str, Any], context: AgentContext) -> ToolResult:
        archetype = params.get("archetype")
        filters = params.get("filters", {})

        entities = await context.state_view.find_by_archetype(archetype, filters)
        return ToolResult(success=True, data=[str(e.id) for e in entities])


class GetEntityTool(AgentTool):
    name = "get_entity"
    description = "Get entity details by ID"
    input_schema = {
        "type": "object",
        "properties": {
            "id": {"type": "string"},
            "depth": {"type": "integer", "default": 1},
        },
        "required": ["id"],
    }

    async def execute(self, params: dict[str, Any], context: AgentContext) -> ToolResult:
        entity_id = params.get("id")
        depth = params.get("depth", 1)

        entity = await context.state_view.get_entity(EntityId(entity_id), depth)
        if not entity:
            return ToolResult(success=False, error=f"Entity {entity_id} not found")

        return ToolResult(
            success=True,
            data={
                "id": str(entity.id),
                "archetype": entity.archetype,
                "tags": [str(t) for t in entity.tags],
                "properties": entity.properties,
            },
        )


class QueryEventsTool(AgentTool):
    name = "query_events"
    description = "Query events with filters"
    input_schema = {
        "type": "object",
        "properties": {
            "actor": {"type": "string"},
            "target": {"type": "string"},
            "location": {"type": "string"},
            "types": {"type": "array", "items": {"type": "string"}},
            "limit": {"type": "integer", "default": 10},
        },
    }

    async def execute(self, params: dict[str, Any], context: AgentContext) -> ToolResult:
        from nexus_engine.store.event_store import EventFilter

        filter_obj = EventFilter()
        filter_obj.actor = params.get("actor")
        filter_obj.target = params.get("target")
        filter_obj.location = params.get("location")
        filter_obj.types = params.get("types")
        filter_obj.limit = params.get("limit", 10)

        events = []
        async for event in context.event_store.query(filter_obj):
            events.append({
                "id": str(event.id),
                "type": event.type.value,
                "game_time": event.game_time.ticks,
                "summary": event.narrative_summary,
            })

        return ToolResult(success=True, data=events)


class RecallSimilarTool(AgentTool):
    name = "recall_similar_events"
    description = "Recall similar past events"
    input_schema = {
        "type": "object",
        "properties": {
            "description": {"type": "string"},
            "k": {"type": "integer", "default": 5},
        },
        "required": ["description"],
    }

    async def execute(self, params: dict[str, Any], context: AgentContext) -> ToolResult:
        description = params.get("description")
        k = params.get("k", 5)

        if not context.memory_system:
            return ToolResult(success=True, data=[])

        results = await context.memory_system.recall_similar(description, k)
        return ToolResult(success=True, data=results)


class GetApplicableRulesTool(AgentTool):
    name = "get_applicable_rules"
    description = "Get rules applicable to an action"
    input_schema = {
        "type": "object",
        "properties": {
            "actor_id": {"type": "string"},
            "action_tags": {"type": "array", "items": {"type": "string"}}},
        "required": ["actor_id"],
    }

    async def execute(self, params: dict[str, Any], context: AgentContext) -> ToolResult:
        actor_id = params.get("actor_id")
        action_tags = params.get("action_tags", [])

        from nexus_engine.core.value_objects import Tag

        tags = [Tag(namespace="action", value=t) for t in action_tags]
        rules = context.state_view.get_applicable_rules(actor_id, tags)

        return ToolResult(
            success=True,
            data=[{"id": str(r.id), "priority": r.priority} for r in rules],
        )


class CheckCanonTool(AgentTool):
    name = "check_canon"
    description = "Check if a claim contradicts canon"
    input_schema = {
        "type": "object",
        "properties": {
            "claim": {"type": "string"},
        },
        "required": ["claim"],
    }

    async def execute(self, params: dict[str, Any], context: AgentContext) -> ToolResult:
        claim = params.get("claim")

        if not context.memory_system or not context.memory_system.canon_store:
            return ToolResult(success=True, data={"consistent": True})

        from nexus_engine.validation.canon import Claim

        claim_obj = Claim(subject="", predicate="", object="")
        contradiction = await context.memory_system.canon_store.contradicts(claim_obj)

        return ToolResult(
            success=True,
            data={"consistent": contradiction is None, "contradiction": str(contradiction) if contradiction else None},
        )


class AgentTools:
    def __init__(self, context: AgentContext):
        self._tools: dict[str, AgentTool] = {
            "find_entity": FindEntityTool(),
            "get_entity": GetEntityTool(),
            "query_events": QueryEventsTool(),
            "recall_similar_events": RecallSimilarTool(),
            "get_applicable_rules": GetApplicableRulesTool(),
            "check_canon": CheckCanonTool(),
        }
        self._context = context

    def get_tool_schemas(self) -> list[dict[str, Any]]:
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.input_schema,
            }
            for tool in self._tools.values()
        ]

    async def execute(self, tool_name: str, params: dict[str, Any]) -> ToolResult:
        tool = self._tools.get(tool_name)
        if not tool:
            return ToolResult(success=False, error=f"Unknown tool: {tool_name}")
        return await tool.execute(params, self._context)

    async def execute_batch(
        self, calls: list[tuple[str, dict[str, Any]]]
    ) -> list[ToolResult]:
        results = []
        for tool_name, params in calls:
            result = await self.execute(tool_name, params)
            results.append(result)
        return results
