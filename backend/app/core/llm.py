"""LLM clients: Groq (real) and Mock (offline tests)."""
import re
from collections.abc import Iterator

from app.core.config import get_settings


class LLMError(RuntimeError):
    pass


class GroqLLM:
    provider = "groq"

    def __init__(self):
        s = get_settings()
        if not s.groq_api_key:
            raise LLMError("GROQ_API_KEY is not set. Add it to backend/.env")
        from groq import Groq

        self._client = Groq(api_key=s.groq_api_key)
        self.model = s.groq_model
        self.fast_model = s.groq_fast_model
        self._s = s

    def chat(self, messages: list[dict], fast: bool = False, max_tokens: int = 200) -> str:
        resp = self._client.chat.completions.create(
            model=self.fast_model if fast else self.model, messages=messages,
            temperature=0, max_tokens=max_tokens)
        return resp.choices[0].message.content.strip()

    def stream(self, messages: list[dict]) -> Iterator[str]:
        stream = self._client.chat.completions.create(
            model=self.model, messages=messages, stream=True,
            temperature=self._s.llm_temperature, max_tokens=self._s.llm_max_tokens)
        for part in stream:
            delta = part.choices[0].delta.content
            if delta:
                yield delta


class MockLLM:
    """Extractive stand-in. Picks best-matching context sentences."""

    provider = "mock"
    model = "mock-extractive"
    fast_model = "mock-extractive"
    _word = re.compile(r"[a-z0-9]+")

    def chat(self, messages: list[dict], fast: bool = False, max_tokens: int = 200) -> str:
        # rewrite: return last question as-is
        text = messages[-1]["content"]
        m = re.search(r"Follow-up question:\s*(.+)", text, re.S)
        return (m.group(1) if m else text).strip()

    def stream(self, messages: list[dict]) -> Iterator[str]:
        prompt = messages[-1]["content"]
        q = prompt.split("Question:")[-1]
        q_words = set(self._word.findall(q.lower())) - {"the", "a", "is", "of", "what", "how", "for", "i", "do", "my", "to", "in", "can"}
        best = []
        for block in re.findall(r"\[(\d+)\][^\n]*\n(.*?)(?=\n\[\d+\]|\nQuestion:)", prompt, re.S):
            num, body = block
            for sent in re.split(r"(?<=[.!?])\s+|\n+", body):
                overlap = len(q_words & set(self._word.findall(sent.lower())))
                if overlap:
                    best.append((overlap, sent.strip(), num))
        best.sort(key=lambda x: -x[0])
        answer = " ".join(f"{s} [{n}]" for _, s, n in best[:2]) or "I could not find this in the policy documents."
        for tok in re.findall(r"\S+\s*", answer):
            yield tok


def get_llm():
    return MockLLM() if get_settings().llm_provider == "mock" else GroqLLM()
