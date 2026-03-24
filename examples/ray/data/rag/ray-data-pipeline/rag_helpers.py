"""Query-side helpers for the RAG demo notebooks.

Kept in a separate file so the notebook cells stay short and readable.
Import with: ``from rag_helpers import ask_llm, search_milvus, build_context``
"""

import logging

logger = logging.getLogger("rag-query")


def ask_llm(question: str, *, llm, model_name: str, context: str = "") -> str:
    """Send a question to the LLM, optionally with RAG context."""
    if context:
        prompt = (
            "You are a technical research assistant. Answer the user's question "
            "based ONLY on the numbered context documents below.\n\n"
            "Rules:\n"
            "- Cite your sources using [1], [2], etc. matching the document numbers.\n"
            "- After your answer, list each cited source on its own line under "
            "'Sources:' with the document number and filename.\n"
            "- If the answer is not in the provided context, say so explicitly.\n\n"
            f"## Context\n\n{context}\n\n"
            f"## Question\n\n{question}\n\n"
            "## Answer\n\n"
        )
    else:
        prompt = (
            "You are a helpful assistant. You do NOT have access to external documents "
            "or research papers. If the user asks about specific research findings, "
            "you MUST say: 'I do not have access to research documents. Please provide "
            "context from the relevant papers.'\n\n"
            f"## Question\n\n{question}\n\n"
            "## Answer\n\n"
        )

    try:
        response = llm.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1024,
            temperature=0.1,
        )
    except Exception as exc:
        logger.error("LLM API call failed: %s", exc)
        return f"[Error: LLM request failed — {exc}]"

    if not response.choices:
        return "[Error: LLM returned no choices]"

    answer = response.choices[0].message.content
    if response.usage:
        logger.info(
            "LLM response: prompt_tokens=%d completion_tokens=%d",
            response.usage.prompt_tokens,
            response.usage.completion_tokens,
        )
    return answer


def search_milvus(
    question: str,
    *,
    milvus,
    embed_model,
    collection_name: str,
    top_k: int = 5,
    score_threshold: float = 0.5,
) -> list:
    """Embed the question and search Milvus for similar chunks."""
    query_embedding = embed_model.encode([question], normalize_embeddings=True).tolist()

    try:
        results = milvus.search(
            collection_name=collection_name,
            data=query_embedding,
            limit=top_k,
            output_fields=["source_file", "chunk_index", "text"],
            search_params={"metric_type": "COSINE", "params": {"nprobe": 16}},
        )
    except Exception as exc:
        logger.error("Milvus search failed: %s", exc)
        return []

    contexts = []
    for hits in results:
        for hit in hits:
            contexts.append({
                "text": hit["entity"]["text"],
                "source_file": hit["entity"]["source_file"],
                "chunk_index": hit["entity"]["chunk_index"],
                "score": hit["distance"],
            })

    total = len(contexts)
    contexts = [c for c in contexts if c["score"] >= score_threshold]
    logger.info(
        "Milvus search: %d results, %d after threshold filter",
        total,
        len(contexts),
    )
    return contexts


def build_context(chunks: list) -> str:
    """Format retrieved chunks with numbered references for citation."""
    return "\n\n---\n\n".join(
        f"[{i}] ({c['source_file']}, chunk {c['chunk_index']}, "
        f"score: {c['score']:.3f})\n{c['text']}"
        for i, c in enumerate(chunks, 1)
    )


def print_comparison(
    question: str, answer_no_rag: str, answer_with_rag: str, chunks: list
):
    """Print the side-by-side RAG comparison with numbered sources."""
    sep = "=" * 60
    print(f"Question: {question}")
    print(f"\n{sep}\n  WITHOUT RAG\n{sep}\n")
    print(answer_no_rag)
    print(f"\n{sep}\n  WITH RAG\n{sep}\n")
    print(answer_with_rag)
    print(f"\n{sep}\n  SOURCES\n{sep}\n")
    for i, c in enumerate(chunks, 1):
        print(
            f"  [{i}] {c['source_file']}  (chunk {c['chunk_index']}, score: {c['score']:.3f})"
        )
