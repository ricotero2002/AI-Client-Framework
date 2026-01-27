# GBeder Multi-Agent Research System

<div align="center">

[![Documentation](https://img.shields.io/badge/docs-complete-green)](https://github.com)
[![Patterns](https://img.shields.io/badge/patterns-3-blue)](#orchestration-patterns)
[![Models](https://img.shields.io/badge/models-Gemini_2.x-orange)](#agent-models)
[![MCP](https://img.shields.io/badge/MCP-Tavily-purple)](#mcp-integration)
[![Evaluation](https://img.shields.io/badge/eval-DeepEval-red)](#evaluation-framework)

**Production-ready multi-agent research system with MCP integration, multiple orchestration patterns, and comprehensive LLM-as-a-Judge evaluation**

[Quick Start](#-quick-start) •
[Architecture](#-architecture) •
[Patterns](#-orchestration-patterns) •
[Benchmarks](#-performance-benchmarks) •
[Documentation](#-documentation)

</div>

---

## 🎯 Overview

**GBeder** is an **autonomous multi-agent research system** built on LangGraph that transforms complex research queries into comprehensive, fact-checked reports. The system implements **three orchestration patterns** to balance latency, cost, and quality, with integrated **cost tracking** and **Tavily usage monitoring**.

### Core Capabilities

- 🔍 **MCP-Native Architecture**: Custom Tavily MCP server decouples tool API from agent logic
- 🧠 **Three Orchestration Patterns**: Supervisor (hierarchical), Sequential (feedback loops), Reflexion (iterative refinement)
- 📊 **DeepEval Integration**: LLM-as-a-Judge evaluation for faithfulness, relevancy, and hallucination detection
- 💰 **Full Cost Transparency**: Real-time token usage, cost estimation, and Tavily API call tracking
- ⚡ **Performance Benchmarking**: Automated comparison across patterns with aggregate analytics
- 🔄 **Fault Tolerance**: Automatic model fallback on 429 (rate limit) and 503 (overload) errors

---

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- [Tavily API Key](https://tavily.com) (for research capabilities)
- [Google AI API Key](https://ai.google.dev) (for Gemini models)
- (Optional) [OpenAI API Key](https://platform.openai.com) (for DeepEval metrics)

### Installation

```bash
# Navigate to project directory
cd c:\Users\Agustin\Desktop\Agustin\IA

# Install dependencies
pip install -r requirements.txt
```

### Environment Setup

Create `.env` file in the root directory:

```bash
# Required
TAVILY_API_KEY=tvly-dev-YOUR_KEY_HERE
GOOGLE_API_KEY=your_google_api_key_here

# Optional (for DeepEval LLM-as-a-Judge evaluation)
OPENAI_API_KEY=sk-your_openai_key_here

# Optional (for LangSmith tracing)
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=gb eder-system
LANGCHAIN_API_KEY=your_langsmith_key
```

### Run Your First Query

```bash
cd gbeder_system
python test_gbeder.py
```

This executes all three patterns with a test query and displays results.

### Run Benchmarks

```bash
cd gbeder_system/results
python run_comparison.py --query "Your research question here"

# Or run all test queries
python run_comparison.py --all-queries
```

### Analyze Results

```bash
# From project root
python gbeder_system/analyze_benchmarks.py --dir "gbeder_system/results/output"
```

---

## 🏗️ Architecture

### System Overview

GBeder implements a **four-agent cognitive pipeline** with specialized roles:

```
┌─────────────────────────────────────────────────────────────┐
│                      USER QUERY                             │
└────────────────────────┬────────────────────────────────────┘
                         │
        ┌────────────────┴────────────────┐
        │    Orchestration Pattern        │
        │  (Supervisor/Sequential/        │
        │   Reflexion)                    │
        └────────────────┬────────────────┘
                         │
      ┌──────────────────┼──────────────────┐
      │                  │                  │
      ▼                  ▼                  ▼
┌──────────┐      ┌──────────┐      ┌──────────┐
│Researcher│      │ Analyst  │      │Synthesizer│
│(Hunter)  │─────▶│ (Filter) │─────▶│(Architect)│
└──────────┘      └──────────┘      └──────────┘
      │                                    │
      │ Tavily MCP                         │
      │ tavily_search                      │
      │ tavily_extract                     │
      │                                    ▼
      │                             ┌──────────┐
      │                             │ Reviewer │
      │                             │ (Critic) │
      │                             └──────────┘
      │                                    │
      └────────────────────────────────────┘
                         │
                         ▼
                  FINAL REPORT
        (with DeepEval quality scores)
```

### Agent Personas & Models

Each agent uses a **specialized Gemini 2.x model** optimized for its cognitive task:

| Agent | Model | Complexity | Role | Tools |
|-------|-------|------------|------|-------|
| **Researcher** | gemini-2.5-flash | High | Information gathering via web search | Tavily MCP: tavily_search, tavily_extract |
| **Analyst** | gemini-2.0-flash | Medium-High | Data processing & pattern recognition | Python REPL (quantitative analysis) |
| **Synthesizer** | gemini-2.5-flash-lite | Medium | Narrative construction & report writing | None (context-only) |
| **Reviewer** | gemini-2.0-flash-lite | Medium-Low | Quality assurance & evaluation | DeepEval metrics (Faithfulness, Relevancy) |

**Design Principle**: No model is repeated within a single execution to optimize cost-quality tradeoff.

### Project Structure

```
gbeder_system/
├── config.py                  # Model assignments, thresholds, iteration limits
├── state.py                   # TypedDict state schemas
├── agents.py                  # Four agent implementations
├── mcp_client.py              # MCP protocol client
├── tavily_mcp_server.py       # Custom Tavily MCP server
├── eval.py                    # DeepEval integration (LLM-as-a-Judge)
├── graphs/
│   ├── supervisor_pattern.py  # Hierarchical routing pattern
│   ├── sequential_pattern.py  # Linear flow with feedback loops
│   └── reflexion_pattern.py   # Iterative refinement pattern
├── results/
│   ├── benchmark.py           # Benchmark runner with cost tracking
│   ├── run_comparison.py      # Multi-pattern comparison script
│   └── output/                # Generated reports (.txt, .json, .md)
├── analyze_benchmarks.py      # Aggregate analytics script
├── test_gbeder.py             # Test suite
└── README.md                  # This file
```

---

## 🧠 Orchestration Patterns

GBeder implements three distinct multi-agent orchestration patterns, each with different performance characteristics.

### Pattern A: Sequential with Feedback

**Topology**: Linear pipeline with conditional kickback loops

```
Researcher → Analyst → Synthesizer → Reviewer
                ▲                        │
                │                        │
                └────── (if needed) ─────┘
```

**Flow Logic**:
1.  Researcher queries Tavily via MCP
2. Analyst extracts insights and performs quantitative analysis
3. Synthesizer crafts initial draft
4. Reviewer evaluates with DeepEval metrics
5. **Conditional Routing**:
   - If quality < threshold → back to Synthesizer (style fixes)
   - If data gaps detected → back to Researcher (more data)
   - If quality ≥ threshold → END
6. Max 5 iterations to prevent infinite loops

**Characteristics**:
- ✅ **Deterministic**: Easy to debug with LangSmith traces
- ✅ **Cost-Efficient**: Predictable token usage
- ⚠️ **"Telephone Effect"**: Context degradation across agents
- ⚠️ **No Cross-Agent Communication**: Agents can't negotiate directly

**Best For**: Structured research tasks with clear phases (e.g., market analysis, literature review)

**Benchmark Results** (6-run average):
- Latency: 44.76s
- Cost: $0.0026
- Quality: 0.804
- Tavily Searches: 2.0

---

### Pattern B: Supervisor (Hierarchical Routing)

**Topology**: Star network with central orchestrator

```
       ┌──────────────┐
       │  Supervisor  │ ──> Makes routing decisions
       └──────┬───────┘
              │
    ┌─────────┼──────────┬──────────┐
    ▼         ▼          ▼          ▼
Researcher  Analyst  Synthesizer  Reviewer
    │         │          │          │
    └─────────┴──────────┴──────────┘
              │
              ▼
           [END]
```

**Flow Logic**:
1. Supervisor analyzes current state
2. Selects next agent based on:   - Progress assessment (0.0-1.0)
   - Data gaps
   - Quality scores
3. Delegates task to selected agent
4.  Agent reports back to Supervisor
5. Supervisor decides: continue, pivot, or terminate
6. Max 10 iterations (configurable)

**Characteristics**:
- ✅ **Adaptive**: Non-linear workflows (e.g., Research → Analysis → Re-research)
- ✅ **Flexible**: Handles complex, multi-step queries
- ⚠️ **Supervisor Bottleneck**: Every decision requires LLM call
- ⚠️ **Context Bloat**: Supervisor must maintain global state
- ❌ **High Cost**: 6× more tokens than Reflexion

**Best For**: Exploratory research with unpredictable query structure

**Benchmark Results** (6-run average):
- Latency: 153.28s (⚠️ 3.9× slower than Reflexion)
- Cost: $0.0098 (⚠️ 3.9× more expensive)
- Quality: 0.818
- Tavily Searches: 3.0
- Iterations: 12.0 (hits max every run)

**⚠️ Known Issue**: Supervisor consistently hits max iterations, suggesting potential routing logic inefficiency. Under investigation.

---

### Pattern C: Reflexion (Critic-Reviewer Loop)

**Topology**: Focused refinement cycle

```
Researcher → Analyst → ┌──────────────┐
                       │              ▼
                       │    Synthesizer ↔ Critic
                       │              │
                       └──────────────┘
                                      │
                                      ▼
                                   [END]
```

**Flow Logic**:
1. Research phase (once): Researcher gathers data
2. Analysis phase (once): Analyst extracts insights
3. **Refinement Loop**:
   - Synthesizer creates draft
   - Critic evaluates with DeepEval
   - If score < threshold: Critic provides actionable feedback
   - Synthesizer revises draft
   - Repeat until quality threshold met
4. Max 5 refinement cycles

**Characteristics**:
- ✅ **Highest Quality**: Iterative polishing (0.820 avg)
- ✅ **Fastest**: No redundant research (39.34s avg)
- ✅ **Cheapest**: Minimal token overhead ($0.0025 avg)
- ✅ **Most Consistent**: Low variance across metrics
- ⚠️ **Refine ment-Only**: Can't request more data mid-loop

**Best For**: General-purpose research requiring high-quality output

**Benchmark Results** (6-run average):
- **⚡ Fastest**: 39.34s
- **💰 Cheapest**: $0.0025
- **⭐ Highest Quality**: 0.820
- **🔋 Most Token-Efficient**: 12,609 tokens
- Tavily Searches: 2.0
- Iterations: 1.0

**🏆 Winner**: Reflexion dominates in ALL measured dimensions.

---

## 📊 Performance Benchmarks

### Aggregate Results (6 Complete Runs)

| Metric | Reflexion | Sequential | Supervisor |
|--------|-----------|------------|------------|
| **Avg Latency** | **39.34s** ⚡ | 44.76s | 153.28s |
| **Avg Cost** | **$0.0025** 💰 | $0.0026 | $0.0098 |
| **Avg Tokens** | **12,609** 🔋 | 13,673 | 76,123 |
| **Avg Tavily** | **2.0** 🔍 | 2.0 | 3.0 |
| **Avg Quality** | **0.820** ⭐ | 0.804 | 0.818 |
| **Avg Iterations** | 1.0 | 0.0 | 12.0 |

### Cost Projection (1000 Queries)

| Pattern | Cost per Query | Cost for 1000 | Relative to Reflexion |
|---------|---------------|---------------|----------------------|
| Reflexion | $0.0025 | $2.50 | 1.00× (baseline) |
| Sequential | $0.0026 | $2.60 | 1.04× |
| Supervisor | $0.0098 | $9.80 | 3.92× ⚠️ |

**Recommendation**: Default to **Reflexion** for production unless specific workflow requirements demand alternatives.

**Full Analysis**: See [RESULTS_ANALYSIS.md](RESULTS_ANALYSIS.md) for detailed performance breakdown and architectural recommendations.

---

## 🔍 MCP Integration

### The Model Context Protocol Advantage

GBeder uses **MCP (Model Context Protocol)** to decouple external tool APIs from agent logic, enabling:

- 🔄 **Version Independence**: Update Tavily API without changing agent code
- 🏢 **Environment Portability**: Swap Tavily MCP for Google Search MCP in enterprise on-prem deployments
- 🛡️ **Security**: Centralized API key management in MCP server
- 📊 **Observability**: All tool calls traced through LangSmith

### MCP Server: Tavily

**Location**: `gbeder_system/tavily_mcp_server.py`

**Exposed Tools**:
1. **tavily_search**
   - Parameters: `query`, `search_depth` (basic/advanced/fast), `max_results`, `include_answer`, `include_images`
   - Returns: List of search results with URLs, titles, content, scores

2. **tavily_extract**
   - Parameters: `urls` (single or list), `extract_depth`, `format` (markdown/text), `query` (for reranking)
   - Returns: Full-text extraction from web pages

**Client**: `gbeder_system/mcp_client.py`
- Manages MCP lifecycle (connect, call_tool, disconnect)
- Handles stdio communication with MCP server subprocess
- Provides async tool execution

### Fallback Behavior

If Tavily API key is missing or MCP connection fails:
- Researcher generates synthetic placeholder data
- System continues with degraded  capabilities (no real web search)
- Warnings logged but execution doesn't crash

---

## 📈 Evaluation Framework

### DeepEval Integration

GBeder uses **DeepEval** for LLM-as-a-Judge evaluation, providing objective quality measurement without human annotation.

**Metrics Implemented**:

1. **Faithfulness** (Factual Accuracy)
   - Verifies claims in output are supported by retrieved context
   - Threshold: 0.7
   - **Applied to**: Analyst, Synthesizer

2. **Answer Relevancy** (Query Alignment)
   - Measures semantic relevance to user's original query
   - Threshold: 0.7
   - **Applied to**: Synthesizer

3. **Contextual Recall** (Coverage)
   - Checks if all ground-truth information was retrieved
   - Threshold: 0.7
   - **Applied to**: Researcher

4. **Hallucination Detection**
   - Identifies invented facts not present in sources
   - Used as veto mechanism in Reviewer
   - **Applied to**: All agents

**Fallback Mode**: If DeepEval/OpenAI unavailable, system uses heuristic evaluation (draft length, keyword matching).

---

## 💰 Cost Tracking

### Token & Cost Transparency

GBeder tracks resource usage at multiple levels:

**Per-Agent Tracking**:
- Input tokens (by model)
- Output tokens (by model)
- Cached tokens (context caching)
- Estimated cost (per 1M tokens)

**Per-Pattern Tracking**:
- Total tokens across all agents
- Tavily API calls count
- Tavily searches executed
- End-to-end latency
- Iteration count

**Aggregate Analytics**:
- Average metrics across multiple runs
- Min/max/median for variance analysis
- Cost projections (per 1000 queries)
- Best performers by dimension

### Model Pricing (Gemini 2.x)

| Model | Input (per 1M) | Output (per 1M) | Cached (per 1M) |
|-------|----------------|-----------------|-----------------|
| gemini-2.5-flash | $0.30 | $2.50 | $0.075 |
| gemini-2.5-flash-lite | $0.10 | $0.40 | $0.025 |
| gemini-2.0-flash | $0.10 | $0.40 | $0.025 |
| gemini-2.0-flash-lite | $0.075 | $0.30 | $0.01875 |

**Cost Estimation Formula**:
```
Total Cost = Σ (input_tokens / 1M × input_price + output_tokens / 1M × output_price)
```

---

## 🛠️ Advanced Usage

### Custom Queries

```python
import asyncio
from gbeder_system.graphs.reflexion_pattern import create_reflexion_graph
from gbeder_system.mcp_client import MCPClient

async def custom_research():
    # Connect to MCP
    mcp_client = MCPClient("gbeder_system/tavily_mcp_server.py")
    await mcp_client.connect()
    
    # Create graph
    graph = create_reflexion_graph(mcp_client)
    
    # Define query
    initial_state = {
        "query": "What are the latest breakthroughs in quantum computing?",
        "messages": [],
        "retrieved_context": [],
        "analysis": "",
        "draft": "",
        "feedback": "",
        "scores": {},
        "iteration_count": 0,
        "pattern_name": "reflexion",
        "current_agent": "",
        "total_tokens": {},
        "input_tokens": {},
        "output_tokens": {},
        "total_cost": 0.0,
        "is_complete": False,
        "needs_more_data": False,
        "tavily_api_calls": 0,
        "tavily_total_searches": 0
    }
    
    # Execute
    result = await graph.ainvoke(
        initial_state,
        {"configurable": {"thread_id": "custom_query_1"}}
    )
    
    # Access results
    print(f"Final Draft:\n{result['draft']}")
    print(f"\nQuality Score: {result['scores']}")
    print(f"Total Cost: ${result['total_cost']:.4f}")
    print(f"Tavily Searches: {result['tavily_total_searches']}")
    
    await mcp_client.disconnect()

asyncio.run(custom_research())
```

### Modify Evaluation Thresholds

Edit `gbeder_system/config.py`:

```python
EVAL_THRESHOLDS = {
    "faithfulness": 0.8,      # Stricter factual accuracy
    "answer_relevancy": 0.75, # Higher query alignment
    "overall_quality": 0.85   # Tighter completion criteria
}
```

### Change Model Assignments

While defaults use Gemini 2.x, you can swap models:

```python
# In config.py
AGENT_MODELS = {
    "researcher": "gemini-2.0-flash-exp",  # Free experimental model
    "analyst": "gemini-2.0-flash",
    "synthesizer": "gemini-2.5-flash-lite",
    "reviewer": "gemini-2.0-flash-lite"
}
```

### Adjust Iteration Limits

```python
# In config.py
MAX_ITERATIONS = {
    "sequential_feedback": 3,   # Reduce feedback loops
    "reflexion": 7,             # Allow more refinement
    "supervisor": 15            # Increase routing budget
}
```

---

## 🧪 Testing

### Unit Tests

```bash
cd gbeder_system
python test_gbeder.py
```

This runs all three patterns with a test query:
```
"Explain the latest developments in sustainable energy technology and their economic impact."
```

**Output**:
- Per-pattern results (latency, cost, quality, drafts)
- LangSmith trace links
- Cost breakdown by model

### Test Individual Pattern

```python
# In test_gbeder.py, comment out unwanted patterns:
patterns = [
    # ("supervisor", create_supervisor_graph),
    ("reflexion", create_reflexion_graph),  # Test only this
    # ("sequential", create_sequential_graph)
]
```

### Benchmark Custom Queries

```bash
cd gbeder_system/results

# Single query
python run_comparison.py --query "How does CRISPR gene editing work?"

# All test queries
python run_comparison.py --all-queries

# Custom query list
# Edit TEST_QUERIES in run_comparison.py, then:
python run_comparison.py
```

**Output Files** (in `gbeder_system/results/output/`):
- `benchmark_YYYYMMDD_HHMMSS.json` - Raw data
- `benchmark_YYYYMMDD_HHMMSS_report.txt` - Comparison report with final drafts
- `{pattern}_workflow_YYYYMMDD_HHMMSS.md` - Per-pattern detailed execution log

---

## 📊 Benchmark Analytics

### Analyze Past Runs

```bash
python gbeder_system/analyze_benchmarks.py --dir "gbeder_system/results/output"
```

**Generates**:
- Aggregate statistics across all valid runs
- Query frequency analysis
- Cost projections
- Best performers by metric
- Pattern-specific insights

**Sample Output**:
```
================================================================================
BENCHMARK AGGREGATE ANALYSIS
================================================================================

Analyzed: 6 complete benchmark runs
Report Directory: gbeder_system/results/output
Analysis Date: 2026-01-27 19:03:07

================================================================================
BEST PERFORMERS
================================================================================

⚡ Fastest (avg latency): reflexion (39.34s)
💰 Cheapest (avg cost): reflexion ($0.0025)
🔋 Most Token-Efficient: reflexion (12,609 tokens)
🔍 Least Tavily Usage: reflexion (2.0 searches)
⭐ Highest Quality: reflexion (0.820)
```

**Output File**: `aggregate_analysis_YYYYMMDD_HHMMSS.txt`

---

## 🛡️ Error Handling & Reliability

### Automatic Fallback

GBeder's `gemini_client.py` implements intelligent fallback for transient errors:

**429 (Rate Limiting)**:
```
⚠️  Rate limit hit for gemini-2.5-flash. Trying fallback models...
🔄 Attempting with gemini-2.0-flash...
✅ Success with gemini-2.0-flash!
ℹ️  Switched from gemini-2.5-flash to gemini-2.0-flash due to availability issues
```

**503 (Service Unavailable/Overloaded)**:
```
⚠️  Service overloaded for gemini-2.5-flash-lite. Trying fallback models...
🔄 Attempting with gemini-2.0-flash-lite...
✅ Success with gemini-2.0-flash-lite!
```

**Fallback Chain**:
- gemini-2.5-flash → gemini-2.0-flash → gemini-2.0-flash-exp
- gemini-2.5-flash-lite → gemini-2.0-flash-lite → gemini-2.0-flash-exp

**Behavior**:
- Switched model persists for remainder of execution
- No user intervention required
- All fallbacks logged in LangSmith traces

---

## 🧩 Integration Guide

### LangSmith Tracing

Enable observability:

```bash
# .env
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=gbeder-production
LANGCHAIN_API_KEY=ls__your_key_here
```

**View Traces**:
1. Go to [smith.langchain.com](https://smith.langchain.com)
2. Select project `gbeder-production`
3. Filter by:
   - Tag: `pattern:reflexion`, `pattern:supervisor`, `pattern:sequential`
   - User ID: Thread ID from config
   - Cost: Sort by total tokens

**Trace Includes**:
- Full message history
- Tool calls (tavily_search, tavily_extract)
- Model inputs/outputs
- Token counts
- Latency per step

### CI/CD Integration

```yaml
# .github/workflows/benchmark.yml
name: Benchmark Patterns

on:
  schedule:
    - cron: '0 2 * * 1'  # Weekly Monday 2am

jobs:
  benchmark:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: |
          cd gbeder_system/results
          python run_comparison.py --all-queries
        env:
          TAVILY_API_KEY: ${{ secrets.TAVILY_API_KEY }}
          GOOGLE_API_KEY: ${{ secrets.GOOGLE_API_KEY }}
      - run: |
          python gbeder_system/analyze_benchmarks.py > weekly_report.txt
      - uses: actions/upload-artifact@v3
        with:
          name: benchmark-results
          path: gbeder_system/results/output/
```

---

## 🔧 Troubleshooting

### MCP Connection Issues

**Problem**: `FileNotFoundError: MCP server script not found`

**Solution**:
```bash
# Verify server exists
ls gbeder_system/tavily_mcp_server.py

# Check relative paths in graph files
# Paths should be relative to execution directory
```

**Problem**: MCP server hangs on connect

**Solution**:
```bash
# Test server standalone
python gbeder_system/tavily_mcp_server.py

# Should output OpenAPI schema
# If it crashes, check TAVILY_API_KEY in .env
```

### DeepEval Not Working

**Problem**: Evaluation uses fallback mode

**Solution**:
```bash
pip install deepeval

# Set OpenAI key for evaluation model
# .env
OPENAI_API_KEY=sk-your_key_here
```

**Problem**: `ImportError: No module named 'deepeval'`

**Solution**:
```bash
pip install deepeval --upgrade
```

### High Costs

**Problem**: Benchmark costs exceeding budget

**Solutions**:
1. **Test one pattern at a time**:
   ```python
   # In run_comparison.py, comment out expensive patterns
   patterns = [
       ("reflexion", create_reflexion_graph),  # Cheapest
       # ("supervisor", create_supervisor_graph),  # Skip this
   ]
   ```

2. **Reduce search scope**:
   ```python
   # In config.py
   TAVILY_SEARCH_DEFAULTS = {
       "max_results": 3,  # Down from 5
       "search_depth": "basic",  # Faster, cheaper
   }
   ```

3. **Use experimental models** (free tier):
   ```python
   # In config.py
   AGENT_MODELS = {
       "researcher": "gemini-2.0-flash-exp",  # Free!
       "analyst": "gemini-2.0-flash-exp",
       "synthesizer": "gemini-2.0-flash-exp",
       "reviewer": "gemini-2.0-flash-exp"
   }
   ```

### Supervisor Hitting Max Iterations

**Problem**: Supervisor always uses 12/12 iterations

**Known Issue**: Under investigation. Possible routing loop.

**Workaround**:
1. Use Reflexion or Sequential instead
2. Increase `MAX_ITERATIONS["supervisor"]` to 15 in `config.py`
3. Add telemetry to track routing decisions (see [Issue #TODO])

---

## 📚 API Reference

### State Schema

```python
class GBederState(TypedDict):
    """Main state object passed between agents"""
    messages: List[Dict[str, Any]]          # Message history
    query: str                               # Original user query
    retrieved_context: List[Dict[str, Any]]  # Tavily search results
    analysis: str                            # Analyst's structured report
    draft: str                               # Current draft text
    feedback: str                            # Reviewer's critique
    scores: Dict[str, float]                 # DeepEval quality scores
    iteration_count: int                     # Current iteration number
    pattern_name: str                        # "supervisor" | "sequential" | "reflexion"
    current_agent: str                       # Last agent to execute
    next_agent: str                          # (Supervisor only) Next route
    
    # Cost tracking
    total_tokens: Dict[str, int]             # Tokens by model
    input_tokens: Dict[str, int]             # Input tokens by model
    output_tokens: Dict[str, int]            # Output tokens by model
    total_cost: float                        # Estimated cost in USD
    
    # Tavily tracking
    tavily_api_calls: int                    # Number of API calls to Tavily
    tavily_total_searches: int               # Total search queries executed
    
    # Control flags
    is_complete: bool                        # Quality threshold met
    needs_more_data: bool                    # Requires additional research
```

### Configuration Options

```python
# gbeder_system/config.py

# Model assignments
AGENT_MODELS = {
    "researcher": str,     # e.g. "gemini-2.5-flash"
    "analyst": str,
    "synthesizer": str,
    "reviewer": str
}

# Evaluation thresholds
EVAL_THRESHOLDS = {
    "faithfulness": float,      # 0.0-1.0
    "answer_relevancy": float,
    "overall_quality": float
}

# Iteration limits
MAX_ITERATIONS = {
    "sequential_feedback": int,
    "reflexion": int,
    "supervisor": int
}

# Tavily search defaults
TAVILY_SEARCH_DEFAULTS = {
    "search_depth": "basic" | "advanced" | "fast",
    "max_results": int,  # 0-20
    "include_answer": bool,
    "include_images": bool
}
```

---

## 🤝 Contributing

This is a reference implementation. To extend:

1. **Add New Agents**:
   - Create subclass of `BaseAgent` or `MCPAgent` in `agents.py`
   - Implement `invoke(state)` method
   - Add to appropriate pattern graphs

2. **Create New Patterns**:
   - Create new file in `graphs/`
   - Define StateGraph with nodes and edges
   - Add to `run_comparison.py` patterns list

3. **Modify Evaluation**:
   - Edit `eval.py` to add custom DeepEval metrics
   - Update `Reviewer` agent to call new metrics

4. **Custom Benchmarks**:
   - Extend `benchmark.py` with new metric calculations
   - Update `analyze_benchmarks.py` for new aggregate statistics

---

## 📄 License

This project uses the existing license of the LangGraph framework.

---

## 🙏 Acknowledgments

- **LangGraph** - Multi-agent orchestration framework
- **Tavily** - Powerful research API with MCP support
- **DeepEval** - LLM-as-a-Judge evaluation metrics
- **Google AI** - Gemini 2.x models with competitive pricing
- **LangSmith** - Production-grade observability for LLM apps
- **Model Context Protocol (MCP)** - Tool integration standard

---

## 📞 Support

**Documentation**:
- [Architecture Guide](#architecture)
- [Performance Analysis](RESULTS_ANALYSIS.md)
- [Troubleshooting](#troubleshooting)

**Resources**:
- LangGraph Docs: https://langchain-ai.github.io/langgraph/
- Tavily API: https://docs.tavily.com
- DeepEval Metrics: https://docs.confident-ai.com

**Issues**:
1. Check [Troubleshooting](#troubleshooting) section
2. Review LangSmith traces for execution details
3. Examine benchmark reports in `results/output/`

---

## 🎯 Quick Reference

### Best Pattern by Use Case

| Use Case | Recommended Pattern | Reason |
|----------|---------------------|--------|
| **General Research** | Reflexion | Fastest, cheapest, highest quality |
| **Budget-Constrained** | Sequential | Predictable cost, acceptable quality |
| **Complex Multi-Step** | Supervisor* | Adaptive routing (*if routing bug is fixed) |
| **High-Stakes / Critical** | Ensemble (All 3) | Redundancy + meta-review (see RESULTS_ANALYSIS.md) |

### Common Commands

```bash
# Run quick test
python gbeder_system/test_gbeder.py

# Benchmark single query
python gbeder_system/results/run_comparison.py --query "Your question"

# Analyze all past runs
python gbeder_system/analyze_benchmarks.py

# View detailed results
cat gbeder_system/results/output/aggregate_analysis_*.txt
```

---

<div align="center">

**Built with ❤️ using LangGraph, Gemini 2.x, and MCP**

[⬆ Back to Top](#gbeder-multi-agent-research-system)

</div>