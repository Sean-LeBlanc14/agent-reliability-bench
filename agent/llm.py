"""
Thin client over the orchestrator model. One primitive, complete(), so model +
temp are pinned in exactly one place and every caller (extraction, the loop)
inherits the same pinning and the same retry policy.
"""

from __future__ import annotations

import os
from dotenv import load_dotenv
load_dotenv()

import anthropic

from agent.config import CONFIG

_MAX_TOKENS = 512  # generous for an ANSWER line or a short loop decision; not a study knob
_MAX_RETRIES = 6   # above the SDK default of 2, to ride out rate limits across ~1,350 episodes


class LLM:
    def __init__(self):
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise RuntimeError("ANTHROPIC_API_KEY not set")
        self._client = anthropic.Anthropic(max_retries=_MAX_RETRIES)
        self._model = CONFIG["orchestrator"]["model"]
        self._temperature = CONFIG["orchestrator"]["temperature"]
        self._input_tokens = 0
        self._output_tokens = 0


    def complete(self, system: str, messages: list[dict]) -> str:
        """
        system/messages in, text out. Kept dumb on purpose: the study logic
        (what to ask, how to read the reply) lives in the caller, so the client
        can't influence the experiment
        """
        resp = self._client.messages.create(
            model=self._model,
            temperature=self._temperature,
            max_tokens=_MAX_TOKENS,
            system=system,
            messages=messages,
        )

        # Accumulated rather than returned
        self._input_tokens += resp.usage.input_tokens
        self._output_tokens += resp.usage.output_tokens
        return "".join(b.text for b in resp.content if b.type == "text")


    @property
    def model(self) -> str:
        # Exposed so the harness can stamp the pinned string into every trace
        return self._model

    @property
    def usage(self) -> dict[str, int]:
        # Cumulative per process, which is per cell, since each cell is its own run
        return {"input_tokens": self._input_tokens, "output_tokens": self._output_tokens}
