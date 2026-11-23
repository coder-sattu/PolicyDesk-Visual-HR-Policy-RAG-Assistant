SYSTEM_PROMPT = """You are an HR Policy Assistant for the company. Answer employee questions \
using ONLY the policy context provided.

Rules:
- Be accurate and concise (2-6 sentences, or a short list when listing items).
- Quote exact numbers, limits and timelines from the context.
- Cite sources inline as [1], [2] matching the context numbers.
- If the context does not contain the answer, say you could not find it in the HR policy \
documents and suggest contacting HR. Never invent policy details.
- Do not give legal advice."""

REWRITE_PROMPT = """Rewrite the follow-up question as a standalone question about HR policy, \
using the chat history for context. Return ONLY the rewritten question.

Chat history:
{history}

Follow-up question: {question}"""


def build_context(hits: list[dict]) -> str:
    blocks = []
    for i, h in enumerate(hits, 1):
        label = f"{h['filename']}, page {h['page']}" + (f", {h['section']}" if h.get("section") else "")
        blocks.append(f"[{i}] ({label})\n{h['text']}")
    return "\n\n".join(blocks)


def build_answer_prompt(question: str, hits: list[dict]) -> str:
    return f"Policy context:\n\n{build_context(hits)}\n\nQuestion: {question}"
