from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Literal

from nexus_engine.agents.tools import AgentTools, AgentContext


@dataclass
class ChatMessage:
    role: Literal["system", "user", "assistant", "tool"]
    content: str
    name: str | None = None
    tool_calls: list[dict[str, Any]] | None = None


@dataclass
class ChatCompletionResult:
    content: str
    tool_calls: list[dict[str, Any]] | None = None
    finish_reason: str = "stop"


class LLMInterface:
    def __init__(
        self,
        model: str = "gpt-4",
        api_base: str | None = None,
        api_key: str | None = None,
        tools: AgentTools | None = None,
    ):
        self.model = model
        self.api_base = api_base
        self.api_key = api_key
        self._tools = tools
        self._tool_schemas: list[dict[str, Any]] = []
        if tools:
            self._tool_schemas = tools.get_tool_schemas()

    async def completion(
        self,
        messages: list[ChatMessage],
        tools: list[dict[str, Any]] | None = None,
        **kwargs,
    ) -> ChatCompletionResult:
        if tools is None:
            tools = self._tool_schemas

        return ChatCompletionResult(
            content="This is a mock LLM response. Configure with a real LLM provider for actual responses.",
            finish_reason="stop",
        )

    async def structured_completion(
        self,
        messages: list[ChatMessage],
        response_schema: dict[str, Any],
    ) -> Any:
        result = await self.completion(messages)
        try:
            return json.loads(result.content)
        except json.JSONDecodeError:
            return {"error": "Failed to parse structured response"}

    async def chat(
        self,
        prompt: str,
        system: str | None = None,
        context: AgentContext | None = None,
    ) -> str:
        messages = []
        if system:
            messages.append(ChatMessage(role="system", content=system))
        messages.append(ChatMessage(role="user", content=prompt))

        result = await self.completion(messages)
        return result.content

    async def chat_with_tools(
        self,
        prompt: str,
        system: str | None = None,
        context: AgentContext | None = None,
    ) -> tuple[str, list[dict[str, Any]]]:
        messages = []
        if system:
            messages.append(ChatMessage(role="system", content=system))
        messages.append(ChatMessage(role="user", content=prompt))

        result = await self.completion(messages, tools=self._tool_schemas)
        return result.content, result.tool_calls or []

    async def generate_narrative(
        self,
        events: list[Any],
        context: dict[str, Any],
        style: dict[str, Any] | None = None,
    ) -> str:
        facts = []
        for event in events:
            facts.append(event.narrative_summary if hasattr(event, "narrative_summary") else str(event))

        prompt = "Events:\n" + "\n".join(f"  - {f}" for f in facts)
        prompt += "\n\nGenerate a narrative description of these events."

        return await self.chat(prompt)

    async def parse_intent(
        self,
        input_text: str,
        context: AgentContext,
        schema: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        scene_desc = f"Player at location {context.current_location}"
        prompt = f"""
User input: {input_text}

Current scene: {scene_desc}

Parse the user's intent and return a structured action.
"""
        if schema:
            result = await self.structured_completion(
                [ChatMessage(role="user", content=prompt)],
                response_schema=schema,
            )
            return result

        return {
            "action_type": "unknown",
            "targets": [],
            "parameters": {},
        }
