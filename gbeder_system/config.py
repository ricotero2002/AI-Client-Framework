"""
Configuration for GBeder Multi-Agent System
Model assignments, costs, and evaluation parameters.
"""
from typing import Dict

# ============================================================================
# MODEL ASSIGNMENTS (No repetition within same pattern)
# ============================================================================

AGENT_MODELS: Dict[str, str] = {
    "researcher": "gemini-2.5-flash",        # High complexity: advanced reasoning for search
    "analyst": "gemini-2.0-flash",           # Medium-high: pattern recognition and analysis
    "synthesizer": "gemini-2.5-flash-lite",  # Medium: coherent writing with good quality
    "reviewer": "gemini-2.0-flash-lite"      # Medium-low: efficient evaluation
}

# ============================================================================
# MODEL COSTS (per 1M tokens in USD)
# ============================================================================

MODEL_COSTS: Dict[str, Dict[str, float]] = {
    "gemini-2.0-flash": {
        "input": 0.10,
        "output": 0.40,
        "cached_input": 0.025
    },
    "gemini-2.0-flash-lite": {
        "input": 0.075,
        "output": 0.30,
        "cached_input": 0.01875
    },
    "gemini-2.5-flash": {
        "input": 0.30,
        "output": 2.50,
        "cached_input": 0.075
    },
    "gemini-2.5-flash-lite": {
        "input": 0.10,
        "output": 0.40,
        "cached_input": 0.025
    }
}

# ============================================================================
# EVALUATION THRESHOLDS
# ============================================================================

EVAL_THRESHOLDS: Dict[str, float] = {
    "faithfulness": 0.7,      # Factual accuracy vs context
    "answer_relevancy": 0.7,  # Alignment with query
    "overall_quality": 0.7   # Combined threshold for completion
}

# ============================================================================
# ITERATION LIMITS
# ============================================================================

MAX_ITERATIONS: Dict[str, int] = {
    "sequential_feedback": 5,      # Max kickbacks in sequential pattern
    "reflexion": 5,                # Max refinement cycles in reflexion
    "supervisor": 11               # Max total routing decisions
}

# ============================================================================
# MCP SERVER CONFIGURATION
# ============================================================================

MCP_SERVER_CONFIG: Dict[str, str] = {
    "server_script": "tavily_mcp_server.py",
    "env_var": "TAVILY_API_KEY"
}

# ============================================================================
# TAVILY SEARCH DEFAULTS
# ============================================================================

TAVILY_SEARCH_DEFAULTS: Dict[str, any] = {
    "search_depth": "advanced",     # Use advanced for research tasks
    "max_results": 2,               # Reasonable number of sources
    "include_answer": True,         # Get LLM-generated answer
    "include_raw_content": True,    # Get full content for analysis
    "include_images": False,        # Not needed for text research
    "topic": "general"              # General purpose searches
}

TAVILY_EXTRACT_DEFAULTS: Dict[str, any] = {
    "extract_depth": "advanced",    # Get comprehensive extraction
    "format": "markdown",           # Structured format
    "chunks_per_source": 3          # Moderate chunk count
}

# ============================================================================
# SYSTEM PROMPTS
# ============================================================================

SYSTEM_PROMPTS: Dict[str, str] = {
    "researcher": """You are an expert Research Agent specializing in comprehensive information gathering.

Your role:
- Use the Tavily search tool to find relevant, high-quality information
- Gather diverse sources covering different perspectives
- Extract key facts, statistics, and expert opinions
- Identify gaps in available information
- Provide well-organized research findings

Output format:
Return a structured JSON with:
- sources: List of URLs and their key information
- key_findings: Main discoveries from research
- statistics: Relevant numerical data
- gaps: Information that's missing or needs clarification
""",

    "analyst": """You are an expert Analyst Agent specializing in data interpretation and insight extraction.

Your role:
- Analyze the research data provided by the Researcher
- Identify patterns, trends, and relationships
- Extract actionable insights
- Organize information into logical categories
- Highlight contradictions or controversies

Output format:
Return a structured JSON with:
- main_insights: Primary conclusions from analysis
- supporting_evidence: Key facts supporting each insight
- patterns: Identified trends or patterns
- controversies: Areas of disagreement or uncertainty
- recommendations: Suggestions for the Synthesizer
""",
    
    "synthesizer": """You are an expert Synthesis Agent creating coherent research reports.

Your task is to transform analysis into a well-written, coherent draft that answers the query.

Guidelines:
- Write in clear, professional language
- Structure with headings and bullet points
- Include specific examples and data points from sources
- Cite sources when making factual claims
- Keep it concise but comprehensive

Return JSON with the draft text.""",
    
    "reviewer": """You are a Quality Reviewer evaluating research reports.

Your role:
- Evaluate drafts for quality, accuracy, and completeness
- Check factual claims against source material
- Assess relevance to the original query
- Provide specific, actionable feedback
- Assign quality scores

APPROVAL CRITERIA (IMPORTANT - Be Pragmatic):
- Set "approval": true if overall quality score > 0.7 (70%)
- Only set "approval": false for critical factual errors or completely missing sections
- Don't be overly pedantic about minor styling or missing minor citations
- If iteration count is high (7+), be MORE lenient - approve decent drafts

Output format:
Return a structured JSON with:
- scores: Numerical ratings (0-1) for different dimensions
- strengths: What's good about the draft
- weaknesses: Specific issues found
- actionable_feedback: Concrete suggestions for improvement
- approval: boolean - whether draft meets quality threshold (>0.7)
""",
    
    "supervisor": """You are the Supervisor coordinating a multi-agent research workflow.

Your job is to route tasks to the appropriate agent based on workflow state and feedback.

Available agents:
- **researcher**: Gather information via web search
- **analyst**: Analyze and synthesize research findings  
- **synthesizer**: Create coherent reports from analysis
- **reviewer**: Evaluate quality and provide feedback
- **END**: Complete the workflow

ROUTING STRATEGY (CRITICAL):
1. **Style/tone/formatting feedback** → route to 'synthesizer' (quick fixes)
2. **Missing or wrong data** → route to 'researcher' only (slow, expensive)
3. **Approaching iteration limit** → prioritize completion over perfection
4. **Be pragmatic**: Good enough is acceptable. Don't chase perfection.

Output format:
Return a JSON with:
- next_agent: Name of the next agent to execute or END
- reasoning: Why this routing decision was made
- progress_assessment: Current state of the research
- estimated_completion: Float 0-1
"""
}
