# RAG Document Ingestion with Ray Data

Ingest PDFs into a Milvus vector database for RAG using Ray Data, Docling,
and sentence-transformers. The pipeline runs as a RayJob on an existing
RayCluster on OpenShift.

## Architecture overview

High-level view for demos: **ingestion** builds the vector index on the cluster;
**query** runs from the notebook against Milvus and your inference endpoint.

Diagrams use **color-coded stages** (blue → violet pipeline, **emerald** Milvus, **amber** query path, **coral** LLM). They render on GitHub, GitLab, and [Mermaid Live](https://mermaid.live).

```mermaid
%%{init: {"theme": "base", "themeVariables": {"fontFamily": "ui-sans-serif, system-ui, sans-serif", "primaryColor": "#e0e7ff", "lineColor": "#6366f1", "primaryTextColor": "#1e1b4b"}}}%%
flowchart TB
  subgraph Ingest["🚀 Ingestion — RayJob · rag_ingestion.ipynb"]
    direction TB
    PVC[("📂 PVC · PDFs")]:::storage
    S1["1 · DoclingChunkActor — parse & chunk"]:::stage1
    S2["2 · EmbeddingActor — sentence-transformers"]:::stage2
    S3["3 · MilvusWriteActor — batch insert"]:::stage3
    MV[("🗄️ Milvus")]:::vector
    PVC --> S1 --> S2 --> S3 --> MV
  end

  subgraph Query["✨ Query — rag_query.ipynb"]
    direction TB
    Q["❓ User question"]:::ask
    EQ["🔢 Embed question — same model"]:::embed
    SRCH["🔍 Vector search · top-k"]:::search
    CTX["📋 Context from chunks"]:::ctx
    LLM["🤖 vLLM · OpenAI-compatible"]:::llm
    Q --> EQ --> SRCH --> CTX --> LLM
  end

  MV <-.->|rag_documents| SRCH

  classDef storage fill:#0ea5e9,stroke:#0369a1,color:#fff,stroke-width:2px
  classDef stage1 fill:#3b82f6,stroke:#1d4ed8,color:#fff,stroke-width:2px
  classDef stage2 fill:#6366f1,stroke:#4338ca,color:#fff,stroke-width:2px
  classDef stage3 fill:#8b5cf6,stroke:#6d28d9,color:#fff,stroke-width:2px
  classDef vector fill:#10b981,stroke:#047857,color:#fff,stroke-width:3px
  classDef ask fill:#f59e0b,stroke:#d97706,color:#1c1917,stroke-width:2px
  classDef embed fill:#fbbf24,stroke:#f59e0b,color:#1c1917,stroke-width:2px
  classDef search fill:#f97316,stroke:#ea580c,color:#fff,stroke-width:2px
  classDef ctx fill:#fb923c,stroke:#f97316,color:#1c1917,stroke-width:2px
  classDef llm fill:#ef4444,stroke:#b91c1c,color:#fff,stroke-width:2px

  style Ingest fill:#eff6ff,stroke:#3b82f6,stroke-width:2px
  style Query fill:#faf5ff,stroke:#9333ea,stroke-width:2px
```

Ray Data **streams** the three stages: workers overlap (Docling is usually the
slowest). Optional **Logfire** spans and metrics cover pipeline actors and query
calls when `LOGFIRE_TOKEN` is set.

**Simplified one-slide version** (fewer boxes):

```mermaid
%%{init: {'theme':'base','themeVariables':{'fontFamily':'ui-sans-serif, system-ui, sans-serif','lineColor':'#6366f1'}}}%%
flowchart LR
  subgraph Ingest["🔧 Build the index"]
    direction LR
    PDF[("📂 PDFs")]:::storage
    Doc["📄 Docling"]:::stage1
    Emb["🔢 Embed"]:::stage2
    MV2[("🗄️ Milvus")]:::vector
    PDF --> Doc --> Emb --> MV2
  end

  subgraph RAG["💬 Ask with RAG"]
    direction LR
    Qn["❓ Question"]:::ask
    Qe["🔢 Embed"]:::embed
    Ans["🤖 LLM + chunks"]:::llm
    Qn --> Qe --> MV2
    MV2 --> Ans
  end

  style Ingest fill:#eff6ff,stroke:#3b82f6,stroke-width:2px
  style RAG fill:#fff7ed,stroke:#f97316,stroke-width:2px

  classDef storage fill:#0ea5e9,stroke:#0369a1,color:#fff,stroke-width:2px
  classDef stage1 fill:#3b82f6,stroke:#1d4ed8,color:#fff,stroke-width:2px
  classDef stage2 fill:#6366f1,stroke:#4338ca,color:#fff,stroke-width:2px
  classDef vector fill:#10b981,stroke:#047857,color:#fff,stroke-width:3px
  classDef ask fill:#f59e0b,stroke:#d97706,color:#1c1917,stroke-width:2px
  classDef embed fill:#fbbf24,stroke:#f59e0b,color:#1c1917,stroke-width:2px
  classDef llm fill:#ef4444,stroke:#b91c1c,color:#fff,stroke-width:2px
```

## Quick Start

1. Open `rag_ingestion.ipynb` in your RHOAI workbench
2. Run every cell top-to-bottom: configure, review the pipeline code,
   submit the RayJob, monitor, and validate

## Prerequisites

- Red Hat OpenShift AI with KubeRay operator
- Existing RayCluster (see `manifests/raycluster-rag-optimized.yaml`)
- ReadWriteMany PVC with input PDFs mounted on all Ray workers
- Milvus accessible from the Ray cluster
- CodeFlare SDK (`pip install codeflare-sdk`)

## Files

| File | Description |
|------|-------------|
| `rag_ingestion.ipynb` | Main notebook -- walks through the pipeline, then submits it |
| `docling_milvus_process.py` | RayJob entrypoint (3-stage Ray Data pipeline) |
| `manifests/raycluster-rag-optimized.yaml` | RayCluster spec (CPU workers) |
