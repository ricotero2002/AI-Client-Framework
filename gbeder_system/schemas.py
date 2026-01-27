"""
Pydantic Schemas for GBeder Agent Outputs
Structured outputs for type safety and validation.
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Optional


# ============================================================================
# RESEARCHER SCHEMAS
# ============================================================================

class SearchQueryRefinement(BaseModel):
    """LLM-refined search query with reasoning."""
    original_query: str = Field(description="Original user query")
    refined_queries: List[str] = Field(
        description="Refined search queries optimized for search engines",
        min_items=1,
        max_items=2
    )
    search_strategy: str = Field(description="Strategy for using these queries")
    reasoning: str = Field(description="Why these refinements were made")


class SourceInfo(BaseModel):
    """Information from a single source."""
    url: str
    title: str
    content: str
    score: float = Field(ge=0.0, le=1.0)
    key_points: List[str] = Field(default_factory=list)


class ResearchOutput(BaseModel):
    """Structured output from Researcher agent."""
    sources: List[SourceInfo] = Field(description="Retrieved sources")
    key_findings: List[str] = Field(description="Main discoveries")
    statistics: Dict[str, str] = Field(
        default_factory=dict,
        description="Relevant numerical data"
    )
    gaps: List[str] = Field(
        default_factory=list,
        description="Information gaps identified"
    )
    search_queries_used: List[str] = Field(
        description="Actual search queries executed"
    )
    summary: str = Field(description="Brief summary of research findings")


# ============================================================================
# ANALYST SCHEMAS
# ============================================================================

class Insight(BaseModel):
    """A single analytical insight."""
    title: str
    description: str
    supporting_evidence: List[str]
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in this insight")


class Pattern(BaseModel):
    """An identified pattern or trend."""
    name: str
    description: str
    examples: List[str]


class Controversy(BaseModel):
    """Area of disagreement or uncertainty."""
    topic: str
    different_views: List[str]
    implications: str


class AnalysisOutput(BaseModel):
    """Structured output from Analyst agent."""
    main_insights: List[Insight] = Field(description="Primary conclusions")
    patterns: List[Pattern] = Field(
        default_factory=list,
        description="Identified trends or patterns"
    )
    controversies: List[Controversy] = Field(
        default_factory=list,
        description="Areas of disagreement"
    )
    recommendations: List[str] = Field(
        description="Suggestions for the Synthesizer"
    )
    summary: str = Field(description="Analysis summary")


# ============================================================================
# SYNTHESIZER SCHEMAS
# ============================================================================

class SynthesisOutput(BaseModel):
    """Structured output from Synthesizer agent."""
    draft: str = Field(description="Complete report draft")
    sections: List[str] = Field(description="Section titles in the draft")
    citations_count: int = Field(description="Number of citations included")
    word_count: int = Field(description="Total word count")
    revision_notes: Optional[str] = Field(
        None,
        description="Notes about revisions made based on feedback"
    )


# ============================================================================
# REVIEWER SCHEMAS
# ============================================================================

class QualityScore(BaseModel):
    """Individual quality dimension score."""
    dimension: str
    score: float = Field(ge=0.0, le=1.0)
    reasoning: str


class ReviewOutput(BaseModel):
    """Structured output from Reviewer agent."""
    scores: List[QualityScore] = Field(description="Quality scores by dimension")
    overall_score: float = Field(ge=0.0, le=1.0, description="Average score")
    strengths: List[str] = Field(description="What's good about the draft")
    weaknesses: List[str] = Field(description="Issues found")
    actionable_feedback: List[str] = Field(
        description="Specific suggestions for improvement"
    )
    approval: bool = Field(description="Whether draft meets quality threshold")
    needs_more_data: bool = Field(
        default=False,
        description="Whether more research is needed"
    )


# ============================================================================
# SUPERVISOR SCHEMAS
# ============================================================================

class SupervisorDecision(BaseModel):
    """Routing decision from Supervisor."""
    next_agent: str = Field(
        description="Next agent to execute: 'researcher', 'analyst', 'synthesizer', 'reviewer', or 'END'"
    )
    reasoning: str = Field(description="Why this routing decision was made")
    progress_assessment: str = Field(description="Current state of the research")
    estimated_completion: float = Field(
        ge=0.0,
        le=1.0,
        description="Estimated progress toward completion (0-1)"
    )


class MessageSummary(BaseModel):
    """Summarized message history."""
    summary: str = Field(description="Concise summary of conversation so far")
    key_decisions: List[str] = Field(description="Important decisions made")
    current_state: str = Field(description="Current state of the workflow")
    message_count_summarized: int = Field(description="Number of messages summarized")


# ============================================================================
# UTILITY SCHEMAS
# ============================================================================

class AgentMetadata(BaseModel):
    """Metadata about agent execution."""
    agent_name: str
    model_used: str
    tokens_used: int
    execution_time_seconds: float
    timestamp: str
