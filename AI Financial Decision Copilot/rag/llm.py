"""
rag/llm.py
───────────
Thin wrapper around Ollama for use in agents and RAG chains.
Provides a .chat() interface compatible with CrewAI's LLM protocol.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

sys.path.append(str(Path(__file__).parent.parent))
import config


class OllamaLLM:
    """
    Wrapper around the Ollama Python client.
    - Supports streaming and non-streaming responses
    - Auto-retries on transient failures
    - Compatible with CrewAI's LLM interface
    """

    def __init__(
        self,
        model: str | None = None,
        temperature: float | None = None,
        base_url: str | None = None,
        system_prompt: str | None = None,
    ):
        self.model = model or config.OLLAMA_MODEL
        self.temperature = temperature if temperature is not None else config.AGENT_TEMPERATURE
        self.base_url = base_url or config.OLLAMA_BASE_URL
        self.system_prompt = system_prompt
        self._client = None
        self._init_client()

    def _init_client(self):
        try:
            import ollama
            self._client = ollama.Client(host=self.base_url)
            # Verify connection
            self._client.list()
            logger.info(f"Ollama connected at {self.base_url} | model: {self.model}")
        except Exception as e:
            logger.error(
                f"Cannot connect to Ollama at {self.base_url}.\n"
                f"Make sure Ollama is running: `ollama serve`\n"
                f"And the model is pulled: `ollama pull {self.model}`\n"
                f"Error: {e}"
            )
            raise

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int = 2048,
    ) -> str:
        """
        Send a list of chat messages and return the assistant response text.

        Args:
            messages: List of {"role": "user"|"assistant"|"system", "content": "..."}
            temperature: Override instance temperature
            max_tokens: Max tokens in response
        """
        import ollama

        # Prepend system prompt if set and not already in messages
        if self.system_prompt and (not messages or messages[0].get("role") != "system"):
            messages = [{"role": "system", "content": self.system_prompt}] + messages

        response = self._client.chat(
            model=self.model,
            messages=messages,
            options={
                "temperature": temperature if temperature is not None else self.temperature,
                "num_predict": max_tokens,
            },
        )
        return response["message"]["content"]

    def complete(self, prompt: str, temperature: float | None = None) -> str:
        """Simple single-prompt completion (wraps chat)."""
        return self.chat([{"role": "user", "content": prompt}], temperature=temperature)

    def stream(self, messages: list[dict[str, str]]):
        """Yield response tokens as a generator for streaming."""
        if self.system_prompt and messages[0].get("role") != "system":
            messages = [{"role": "system", "content": self.system_prompt}] + messages

        for chunk in self._client.chat(model=self.model, messages=messages, stream=True):
            yield chunk["message"]["content"]

    # ── CrewAI compatibility ───────────────────────────────────────────────────
    # CrewAI calls llm(prompt) or llm.call(messages)

    def __call__(self, prompt: str, **kwargs) -> str:
        return self.complete(prompt)

    def call(self, messages: list[dict] | str, **kwargs) -> str:
        if isinstance(messages, str):
            return self.complete(messages)
        return self.chat(messages)

    # LangChain-style invoke
    def invoke(self, input: Any, **kwargs) -> Any:
        if isinstance(input, str):
            return self.complete(input)
        if isinstance(input, list):
            return self.chat(input)
        return self.complete(str(input))
