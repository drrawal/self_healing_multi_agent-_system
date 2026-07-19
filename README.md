# Self-Healing Multi-Agent Framework
### *Reliable Enterprise AI Systems through Autonomous Failure Detection, Root-Cause Analysis, and Plan Repair*

---

## Research Overview

Most autonomous agent systems execute **predefined workflows** and halt when a step fails.
This project addresses the core gap: **agents that cannot improve after failure**.

We implement a production-grade framework where agents autonomously:

| Capability | Mechanism |
|---|---|
| **Detect failures** | Rule-based taxonomy + severity classification |
| **Identify root causes** | LLM reflection agent augmented with a knowledge graph |
| **Repair their plans** | Six repair strategies (retry, fallback, replan, skip, escalate…) |
| **Learn from executions** | Episodic memory + semantic strategy scoring + knowledge graph updates |

---

## Architecture

```
                            ┌─────────────────────────────────────────┐
                            │        Self-Healing Workflow             │
                            │                                         │
  User / API ──► Coordinator│                                         │
                            │  START → Planner → Executor             │
                            │                   │                     │
                            │             (failure)                   │
                            │                   ▼                     │
                            │          Failure Detector               │
                            │                   │                     │
                            │         Root-Cause Analyzer             │
                            │           (Reflection Agent)            │
                            │                   │                     │
                            │           Plan Repairer                 │
                            │           (Repair Agent)                │
                            │                   │                     │
                            │         ◄─(retry)─┘   (escalate)►      │
                            │                                         │
                            │  Learner → Finalizer → END              │
                            └─────────────────────────────────────────┘
                                         │            │
                              ┌──────────┘            └─────────────┐
                          Episodic                           Knowledge
                          Memory                              Graph
                         (SQLite)                           (NetworkX)
                                    Semantic Memory
                                      (SQLite)
```

### Component Map

```
selfhealingmultiagent/
├── config/              # Settings (pydantic-settings), structured logging
├── core/
│   ├── graph/           # LangGraph state, nodes, edges, workflow
│   ├── agents/          # LLM factory, ReflectionAgent, RepairAgent
│   ├── memory/          # EpisodicMemory, SemanticMemory, MemoryManager
│   ├── knowledge/       # KnowledgeGraph (NetworkX), failure taxonomy
│   └── healing/         # FailureDetector, RootCauseAnalyzer, PlanRepairer, LearningEngine
├── tools/               # BaseTool, ToolRegistry, enterprise tools, MCP server
├── api/                 # FastAPI app, routes, schemas
├── persistence/         # SQLAlchemy async ORM, repositories
├── experiments/         # Scenario runners, benchmark metrics
└── tests/               # Unit + integration tests
```

---

## Key Innovations

### 1. Typed Failure Taxonomy
`core/knowledge/taxonomy.py` classifies any raw error string into one of six types:
`NETWORK · TOOL · DATA · RESOURCE · LOGIC · DEPENDENCY`

### 2. Reflection-Augmented RCA
The `ReflectionAgent` receives: classified failure + episodic memory hits + knowledge-graph patterns → produces a structured JSON root-cause hypothesis with confidence score and repair strategy recommendation.

### 3. Six-Strategy Repair Engine
`RepairAgent` implements: `RETRY · RETRY_MODIFIED · FALLBACK · REPLAN · SKIP · ESCALATE` — each applied as a pure plan mutation, keeping the workflow stateless.

### 4. Dual-Store Memory System
- **Episodic memory** (append-only SQLite log): full execution traces for similarity-based recall
- **Semantic memory** (scored entries): strategies that can be *reinforced* (successful) or *decayed* (failed)

### 5. Learning Knowledge Graph (NetworkX)
Directed graph linking tools → failure types → repair strategies with weighted edges updated after every execution. Seeded with baseline patterns and continuously refined.

### 6. MCP Protocol Integration
`tools/mcp/server.py` exposes the framework as an MCP server, making it directly callable from Claude Desktop, VS Code Copilot, or any MCP-compatible client.

---

## Research Metrics

| Metric | Symbol | Formula |
|---|---|---|
| Plan Success Rate | PSR | tasks completed / total tasks |
| Repair Rate | RR | successful repairs / total failures |
| Mean Time To Repair | MTTR | Σ repair_time_ms / total repairs |
| Learning Performance Index | LPI | RR(later_half) − RR(earlier_half) |
| Failure Detection Rate | FDR | correct classifications / total failures |

---

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure

```bash
cp .env.example .env
# Edit .env — set OPENAI_API_KEY (or ANTHROPIC_API_KEY)
```

### 3. Run a single task (CLI demo)

```bash
python main.py run "Fetch the sales report and notify the finance team"
```

### 4. Start the REST API

```bash
python main.py api
# → http://localhost:8000/docs
```

### 5. Run experiments

```bash
python main.py experiment 10   # 10 runs per scenario
```

### 6. Run tests

```bash
pytest tests/ -v
```

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/tasks/` | Submit a task |
| `GET`  | `/tasks/{task_id}` | Get task status |
| `GET`  | `/tasks/` | List recent tasks |
| `GET`  | `/health` | Liveness probe |
| `GET`  | `/healing/stats` | Aggregate healing metrics |
| `GET`  | `/knowledge/stats` | Knowledge graph statistics |
| `GET`  | `/mcp/tools` | MCP tool catalogue |
| `POST` | `/mcp/invoke` | Invoke an MCP tool |

---

## Technology Stack

| Layer | Technology |
|---|---|
| Workflow orchestration | **LangGraph** |
| LLM (reflection / repair) | **LangChain** (OpenAI · Anthropic · Azure OpenAI) |
| Knowledge graph | **NetworkX** |
| Memory persistence | **aiosqlite** (no external DB required) |
| ORM | **SQLAlchemy** async |
| REST API | **FastAPI** |
| Tool protocol | **MCP** (Model Context Protocol) |
| Data validation | **Pydantic v2** |
| Logging | **structlog** |
| Testing | **pytest** + **pytest-asyncio** |

---

## Citation

```bibtex
@software{selfhealingmultiagent2025,
  title   = {Self-Healing Multi-Agent Framework for Reliable Enterprise AI Systems},
  year    = {2025},
  note    = {Research implementation using LangGraph, Reflection Agents,
             Knowledge Graphs, and Dual-Store Memory},
}
```

---

## License

MIT License
