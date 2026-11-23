"""Retrieval (RAG) pipeline as a LangGraph:

rewrite -> embed_query -> search -> grade --(relevant)--> generate
                                         \\--(none)-----> fallback
"""
import time
from typing import Literal, TypedDict

from langgraph.graph import END, START, StateGraph

from app.core.config import get_settings
from app.core.embeddings import get_embedder
from app.core.events import step
from app.core.llm import get_llm
from app.core.vector_store import get_store
from app.retrieval.prompts import REWRITE_PROMPT, SYSTEM_PROMPT, build_answer_prompt


class RAGState(TypedDict, total=False):
    question: str
    history: list[dict]
    standalone: str
    query_vec: object
    hits: list[dict]
    relevant: list[dict]
    answer: str
    sources: list[dict]


def _hit_view(h: dict) -> dict:
    return {"id": h["id"], "score": round(h["score"], 4), "filename": h["filename"],
            "page": h["page"], "section": h.get("section"), "text": h["text"]}


def rewrite_node(state: RAGState) -> RAGState:
    with step("rewrite", "Understand question") as s:
        history = state.get("history") or []
        q = state["question"].strip()
        if not history:
            s.emit("done", rewritten=False, standalone=q, reason="No chat history, used as-is")
            return {"standalone": q}
        llm = get_llm()
        hist = "\n".join(f"{m['role']}: {m['content'][:400]}" for m in history[-6:])
        standalone = llm.chat([{"role": "user", "content": REWRITE_PROMPT.format(history=hist, question=q)}],
                              fast=True, max_tokens=120) or q
        s.emit("done", rewritten=standalone != q, original=q, standalone=standalone, model=llm.fast_model)
        return {"standalone": standalone}


def embed_query_node(state: RAGState) -> RAGState:
    with step("embed_query", "Embed query") as s:
        emb = get_embedder()
        vec = emb.embed_query(state["standalone"])
        s.emit("done", model=emb.name, dim=emb.dim, vector_preview=[round(float(x), 4) for x in vec[:24]])
        return {"query_vec": vec}


def search_node(state: RAGState) -> RAGState:
    cfg = get_settings()
    with step("search", "Search FAISS") as s:
        store = get_store()
        hits = store.search(state["query_vec"], cfg.top_k)
        s.emit("done", top_k=cfg.top_k, searched_vectors=store.stats()["vectors"],
               metric="cosine (inner product)", hits=[_hit_view(h) for h in hits])
        return {"hits": hits}


def grade_node(state: RAGState) -> RAGState:
    cfg = get_settings()
    with step("grade", "Filter relevant chunks") as s:
        hits = state.get("hits") or []
        relevant = [h for h in hits if h["score"] >= cfg.score_threshold]
        s.emit("done", threshold=cfg.score_threshold, kept=len(relevant), dropped=len(hits) - len(relevant),
               kept_ids=[h["id"] for h in relevant],
               route="generate" if relevant else "fallback")
        return {"relevant": relevant}


def route_after_grade(state: RAGState) -> Literal["generate", "fallback"]:
    return "generate" if state.get("relevant") else "fallback"


def generate_node(state: RAGState) -> RAGState:
    with step("generate", "Generate answer") as s:
        llm = get_llm()
        hits = state["relevant"]
        messages = [{"role": "system", "content": SYSTEM_PROMPT},
                    *[{"role": m["role"], "content": m["content"]} for m in (state.get("history") or [])[-4:]],
                    {"role": "user", "content": build_answer_prompt(state["standalone"], hits)}]
        t0, first, parts = time.perf_counter(), None, []
        for tok in llm.stream(messages):
            if first is None:
                first = time.perf_counter() - t0
            parts.append(tok)
            s.raw({"type": "token", "content": tok})
        answer = "".join(parts).strip()
        sources = [{"n": i, **_hit_view(h)} for i, h in enumerate(hits, 1)]
        s.emit("done", model=llm.model, provider=llm.provider, context_chunks=len(hits),
               prompt_chars=sum(len(m["content"]) for m in messages),
               first_token_ms=round((first or 0) * 1000, 1), answer_chars=len(answer))
        return {"answer": answer, "sources": sources}


def fallback_node(state: RAGState) -> RAGState:
    with step("fallback", "No relevant policy found") as s:
        empty = get_store().stats()["vectors"] == 0
        answer = ("No documents have been ingested yet. Upload an HR policy PDF first."
                  if empty else
                  "I couldn't find this in the HR policy documents. Please contact HR "
                  "(hr@nimbustech.example) or rephrase your question.")
        s.raw({"type": "token", "content": answer})
        s.emit("done", reason="empty index" if empty else "all scores below threshold")
        return {"answer": answer, "sources": []}


def build_rag_graph():
    g = StateGraph(RAGState)
    g.add_node("rewrite", rewrite_node)
    g.add_node("embed_query", embed_query_node)
    g.add_node("search", search_node)
    g.add_node("grade", grade_node)
    g.add_node("generate", generate_node)
    g.add_node("fallback", fallback_node)
    g.add_edge(START, "rewrite")
    g.add_edge("rewrite", "embed_query")
    g.add_edge("embed_query", "search")
    g.add_edge("search", "grade")
    g.add_conditional_edges("grade", route_after_grade, {"generate": "generate", "fallback": "fallback"})
    g.add_edge("generate", END)
    g.add_edge("fallback", END)
    return g.compile()


rag_graph = build_rag_graph()

RAG_STEPS = [
    {"id": "rewrite", "title": "Understand"}, {"id": "embed_query", "title": "Embed query"},
    {"id": "search", "title": "Vector search"}, {"id": "grade", "title": "Grade"},
    {"id": "generate", "title": "Generate"},
]


def run_rag(question: str, history: list[dict] | None = None):
    """Yield UI events while the graph runs."""
    yield {"type": "start", "pipeline": "retrieval", "steps": RAG_STEPS, "question": question}
    final = {}
    try:
        for mode, chunk in rag_graph.stream({"question": question, "history": history or []},
                                            stream_mode=["custom", "values"]):
            if mode == "custom":
                yield chunk
            else:
                final = chunk
        yield {"type": "complete", "answer": final.get("answer", ""), "sources": final.get("sources", []),
               "standalone": final.get("standalone")}
    except Exception as exc:
        yield {"type": "error", "message": str(exc)}
