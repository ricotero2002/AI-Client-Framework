"""
Agent Definitions for GBeder Multi-Agent System (Refactored)
Four specialized agents with Pydantic schema outputs and Prompt class usage.
"""
import sys
import os
import json
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
from langsmith import traceable

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from client_factory import create_client
from prompt import Prompt
from gbeder_system.config import AGENT_MODELS, SYSTEM_PROMPTS, TAVILY_SEARCH_DEFAULTS
from gbeder_system.state import GBederState
from gbeder_system.direct_tavily_client import DirectTavilyClient
from gbeder_system.schemas import (
    SearchQueryRefinement,
    ResearchOutput,
    SourceInfo,
    AnalysisOutput,
    SynthesisOutput,
    ReviewOutput,
    QualityScore
)


class ResearcherAgent:
    """
    Research Agent - Uses LLM to refine queries, then gathers information via Tavily.
    Model: gemini-2.5-flash (high complexity for advanced reasoning)
    """
    
    def __init__(self, tavily_client: Optional[DirectTavilyClient] = None):
        """
        Initialize Researcher Agent.
        
        Args:
            tavily_client: Optional DirectTavilyClient for Tavily search
        """
        self.model_name = AGENT_MODELS["researcher"]
        self.client = create_client("gemini", langsmith=True)
        self.client.select_model(self.model_name)
        self.tavily_client = tavily_client or DirectTavilyClient()
        self.system_prompt = SYSTEM_PROMPTS["researcher"]
    
    def _refine_search_query(self, query: str, feedback: str = "") -> SearchQueryRefinement:
        """
        Use LLM to refine the search query for better results.
        
        Args:
            query: Original user query
            feedback: Optional feedback requesting more data
            
        Returns:
            SearchQueryRefinement schema with refined queries
        """
        # Build prompt using Prompt class
        prompt = (Prompt()
            .set_system("""You are an expert at crafting effective search queries.
Your task is to take a user's research question and transform it into 1-2 optimized search queries
that will retrieve the most relevant information.

Consider:
- Breaking complex questions into focused sub-queries
- Using specific terminology
- Targeting different aspects of the question

Return your response as a JSON object matching this schema:
{
    "original_query": str,
    "refined_queries": [str, str, ...],
    "search_strategy": str,
    "reasoning": str
}"""
)
            .set_user_input(f"""Research Question: {query}

{f"Feedback (areas needing more data): {feedback}" if feedback else ""}

Generate optimized search queries to find the most relevant information.""")
        )
        
        # Check for undefined variables
        if prompt.has_undefined_variables():
            raise ValueError(f"Prompt has undefined variables: {prompt.get_undefined_variables()}")
        
        prompt.set_output_schema(SearchQueryRefinement)
        # Get LLM response
        response, usage = self.client.get_response(prompt)
        
        # Track token usage (note: state not available here, tracked in execute)
        
        # Parse JSON response
        try:
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0].strip()
            else:
                json_str = response
            
            data = json.loads(json_str)
            return SearchQueryRefinement(**data)
        except (json.JSONDecodeError, Exception) as e:
            # Fallback: use original query
            return SearchQueryRefinement(
                original_query=query,
                refined_queries=[query],
                search_strategy="Direct search with original query (refinement failed)",
                reasoning=f"Query refinement error: {str(e)}"
            )
    @traceable(name="execute researcher")
    async def execute(self, state: GBederState) -> Dict[str, Any]:
        """
        Execute research task with LLM-powered query refinement.
        
        Args:
            state: Current GBeder state
            
        Returns:
            Updated state with structured research results
        """
        print("\n🔬 RESEARCHER: Starting execution...")
        query = state["query"]
        feedback = state.get("feedback", "")
        print(f"🔬 RESEARCHER: Query = {query[:100]}...")
        print(f"🔬 RESEARCHER: Feedback = {feedback[:50] if feedback else 'None'}")
        
        # Step 1: Use LLM to refine search queries
        print("🔬 RESEARCHER: Step 1 - Refining search queries with LLM...")
        query_refinement = self._refine_search_query(query, feedback)
        print(f"🔬 RESEARCHER: Refined queries: {query_refinement.refined_queries}")
        
        # Step 2: Execute searches with refined queries
        print("🔬 RESEARCHER: Step 2 - Executing searches...")
        all_sources = []
        
        if not self.tavily_client:
            print("🔬 RESEARCHER: No Tavily client - using fallback")
            # Fallback: mock response
            research_output = ResearchOutput(
                sources=[],
                key_findings=["Tavily client not available - using fallback"],
                statistics={},
                gaps=["Full Tavily search not performed"],
                search_queries_used=query_refinement.refined_queries,
                summary="No search performed (Tavily unavailable)"
            )
        else:
            print(f"🔬 RESEARCHER: Tavily client available, executing {len(query_refinement.refined_queries)} searches...")
            # Execute each refined query
            for i, refined_query in enumerate(query_refinement.refined_queries, 1):
                print(f"🔬 RESEARCHER: Search {i}/{len(query_refinement.refined_queries)}: {refined_query}")
                search_args = {
                    "query": refined_query,
                    **TAVILY_SEARCH_DEFAULTS
                }
                
                try:
                    print(f"🔬 RESEARCHER: Calling Tavily search...")
                    search_response = await self.tavily_client.call_tool("tavily_search", search_args)
                    print(f"🔬 RESEARCHER: Got response, parsing results...")
                    results = search_response.get("results", [])
                    print(f"🔬 RESEARCHER: Found {len(results)} results")
                    
                    # Convert to SourceInfo schemas
                    for r in results:
                        source = SourceInfo(
                            url=r.get("url", ""),
                            title=r.get("title", "Unknown"),
                            content=r.get("content", ""),
                            score=r.get("score", 0.0),
                            key_points=[]
                        )
                        all_sources.append(source)
                except Exception as e:
                    print(f"Search error for query '{refined_query}': {str(e)}")
            
            # Create ResearchOutput directly (no extra LLM call needed)
            # Extract key findings from top sources
            key_findings = []
            for i, source in enumerate(all_sources[:5]):
                if source.content:
                    snippet = source.content[:250].strip()
                    key_findings.append(f"{source.title}: {snippet}")
            
            summary = f"Retrieved {len(all_sources)} sources across {len(query_refinement.refined_queries)} refined queries."
            
            research_output = ResearchOutput(
                sources=all_sources,
                key_findings=key_findings if key_findings else ["No findings"],
                statistics={},
                gaps=[],  # Analyst will identify gaps
                search_queries_used=query_refinement.refined_queries,
                summary=summary
            )
        
        # Update state
        updated_state = state.copy()
        updated_state["retrieved_context"] = [s.dict() for s in research_output.sources]
        updated_state["messages"] = state["messages"] + [
            {"role": "assistant", "content": research_output.summary, "agent": "researcher", "structured_output": research_output.dict()}
        ]
        updated_state["current_agent"] = "researcher"
        
        # Track Tavily API usage
        if self.tavily_client:
            # We made API calls (one per refined query if Tavily is available)
            num_api_calls = len(query_refinement.refined_queries)
            num_searches = len(query_refinement.refined_queries)  # Each API call executes 1 search query
            
            updated_state["tavily_api_calls"] = state.get("tavily_api_calls", 0) + num_api_calls
            updated_state["tavily_total_searches"] = state.get("tavily_total_searches", 0) + num_searches
            
            print(f"🔬 RESEARCHER: Tavily usage - {num_api_calls} API calls, {num_searches} searches")
        
        # Track tokens for cost calculation
        if "input_tokens" not in updated_state:
            updated_state["input_tokens"] = {}
        if "output_tokens" not in updated_state:
            updated_state["output_tokens"] = {}
        if "total_tokens" not in updated_state:
            updated_state["total_tokens"] = {}
            
        model = self.model_name
        # Note: In production, track actual usage. Using placeholder for Tavily search logic.
        updated_state["input_tokens"][model] = updated_state["input_tokens"].get(model, 0) + 500
        updated_state["output_tokens"][model] = updated_state["output_tokens"].get(model, 0) + 500
        updated_state["total_tokens"][model] = updated_state["total_tokens"].get(model, 0) + 1000
        
        return updated_state


class AnalystAgent:
    """
    Analyst Agent - Analyzes research data using structured schemas.
    Model: gemini-2.0-flash (medium-high complexity for pattern recognition)
    """
    
    def __init__(self):
        """Initialize Analyst Agent."""
        self.model_name = AGENT_MODELS["analyst"]
        self.client = create_client("gemini", langsmith=True)
        self.client.select_model(self.model_name)
        self.system_prompt = SYSTEM_PROMPTS["analyst"]
    
    @traceable(name="execute analyst")
    def execute(self, state: GBederState) -> Dict[str, Any]:
        """
        Execute analysis task with structured output.
        
        Args:
            state: Current GBeder state
            
        Returns:
            Updated state with AnalysisOutput schema
        """
        query = state["query"]
        research_data = state.get("retrieved_context", [])
        
        # Prepare context
        context_text = "\n\n".join([
            f"Source: {src.get('title', 'Unknown')}\nURL: {src.get('url', '')}\nContent: {src.get('content', '')}"
            for src in research_data
        ])
        
        # Build prompt
        prompt = (Prompt()
            .set_system(self.system_prompt)
            .set_user_input(f"""Query: {query}

Research Data:
{context_text}

Analyze this data and provide structured output as JSON:
{{
    "main_insights": [{{"title": str, "description": str, "supporting_evidence": [str], "confidence": float}}],
    "patterns": [{{"name": str, "description": str, "examples": [str]}}],
    "controversies": [{{"topic": str, "different_views": [str], "implications": str}}],
    "recommendations": [str],
    "summary": str
}}""")
        )
        prompt.set_output_schema(AnalysisOutput)
        response, usage = self.client.get_response(prompt)
        
        # Update state
        updated_state = state.copy()
        
        # Track tokens for cost calculation
        if "input_tokens" not in updated_state:
            updated_state["input_tokens"] = {}
        if "output_tokens" not in updated_state:
            updated_state["output_tokens"] = {}
        if "total_tokens" not in updated_state:
            updated_state["total_tokens"] = {}
        
        model = self.model_name
        updated_state["input_tokens"][model] = updated_state["input_tokens"].get(model, 0) + usage.prompt_tokens
        updated_state["output_tokens"][model] = updated_state["output_tokens"].get(model, 0) + usage.completion_tokens
        updated_state["total_tokens"][model] = updated_state["total_tokens"].get(model, 0) + usage.total_tokens
        
        # Parse response
        try:
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
            else:
                json_str = response
            
            data = json.loads(json_str)
            analysis_output = AnalysisOutput(**data)
        except:
            # Fallback
            analysis_output = AnalysisOutput(
                main_insights=[],
                patterns=[],
                controversies=[],
                recommendations=["Review the analysis manually"],
                summary=response[:500]
            )
        
        # Update state
        updated_state["analysis"] = analysis_output.summary
        updated_state["messages"] = state["messages"] + [{
            "role": "assistant",
            "content": analysis_output.summary,
            "agent": "analyst",
            "structured_output": analysis_output.dict()
        }]
        updated_state["current_agent"] = "analyst"
        
        # Token tracking
        if "total_tokens" not in updated_state:
            updated_state["total_tokens"] = {}
        updated_state["total_tokens"][self.model_name] = updated_state["total_tokens"].get(self.model_name, 0) + usage.total_tokens
        
        return updated_state


class SynthesizerAgent:
    """
    Synthesizer Agent - Creates drafts using Prompt templates.
    Model: gemini-2.5-flash-lite (medium complexity)
    """
    
    def __init__(self):
        """Initialize Synthesizer Agent."""
        self.model_name = AGENT_MODELS["synthesizer"]
        self.client = create_client("gemini", langsmith=True)
        self.client.select_model(self.model_name)
        self.system_prompt = SYSTEM_PROMPTS["synthesizer"]
    
    @traceable(name="execute synthesizer")
    def execute(self, state: GBederState) -> Dict[str, Any]:
        """
        Execute synthesis with structured schema.
        
        Args:
            state: Current GBeder state
            
        Returns:
            Updated state with SynthesisOutput schema
        """
        query = state["query"]
        analysis = state.get("analysis", "")
        feedback = state.get("feedback", "")
        previous_draft = state.get("draft", "")
        
        # Build prompt
        if feedback and previous_draft:
            prompt = (Prompt()
                .set_system(self.system_prompt)
                .set_user_input(f"""Query: [[query]]

Analysis: [[analysis]]

Previous Draft:
[[previous_draft]]

Reviewer Feedback:
[[feedback]]

Revise the draft based on feedback. Return JSON:
{{"draft": str, "sections": [str], "citations_count": int, "word_count": int, "revision_notes": str}}""")
                .set_variables(
                    query=query,
                    analysis=analysis,
                    previous_draft=previous_draft,
                    feedback=feedback
                )
            )
        else:
            prompt = (Prompt()
                .set_system(self.system_prompt)
                .set_user_input(f"""Query: [[query]]

Analysis: [[analysis]]

Create a comprehensive report. Return JSON:
{{"draft": str, "sections": [str], "citations_count": int, "word_count": int}}""")
                .set_variables(query=query, analysis=analysis)
            )
        prompt.set_output_schema(SynthesisOutput)
        response, usage = self.client.get_response(prompt)
        
        # Update state
        updated_state = state.copy()
        
        # Track tokens for cost calculation
        if "input_tokens" not in updated_state:
            updated_state["input_tokens"] = {}
        if "output_tokens" not in updated_state:
            updated_state["output_tokens"] = {}
        if "total_tokens" not in updated_state:
            updated_state["total_tokens"] = {}
        
        model = self.model_name
        updated_state["input_tokens"][model] = updated_state["input_tokens"].get(model, 0) + usage.prompt_tokens
        updated_state["output_tokens"][model] = updated_state["output_tokens"].get(model, 0) + usage.completion_tokens
        updated_state["total_tokens"][model] = updated_state["total_tokens"].get(model, 0) + usage.total_tokens
        
        # Parse
        try:
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
            else:
                json_str = response
            data = json.loads(json_str)
            synthesis_output = SynthesisOutput(**data)
        except:
            # Fallback - use raw response as draft
            synthesis_output = SynthesisOutput(
                draft=response,
                sections=["Introduction", "Main Content", "Conclusion"],
                citations_count=0,
                word_count=len(response.split())
            )
        
        # Update state
        updated_state["draft"] = synthesis_output.draft
        updated_state["messages"] = state["messages"] + [{
            "role": "assistant",
            "content": f"Draft created ({synthesis_output.word_count} words)",
            "agent": "synthesizer",
            "structured_output": synthesis_output.dict()
        }]
        updated_state["current_agent"] = "synthesizer"
        
        # Token tracking
        if "total_tokens" not in updated_state:
            updated_state["total_tokens"] = {}
        updated_state["total_tokens"][self.model_name] = updated_state["total_tokens"].get(self.model_name, 0) + usage.total_tokens
        
        return updated_state


class ReviewerAgent:
    """
    Reviewer Agent - Evaluates using structured ReviewOutput schema.
    Model: gemini-2.0-flash-lite (efficient evaluation)
    """
    
    def __init__(self):
        """Initialize Reviewer Agent."""
        self.model_name = AGENT_MODELS["reviewer"]
        self.client = create_client("gemini", langsmith=True)
        self.client.select_model(self.model_name)
        self.system_prompt = SYSTEM_PROMPTS["reviewer"]
        
        # Separate client for context summarization (FREE model)
        self.summary_client = create_client("gemini", langsmith=True)
        self.summary_client.select_model("gemini-2.0-flash-exp")
    
    @traceable(name="execute reviewer")
    def execute(self, state: GBederState) -> Dict[str, Any]:
        """
        Execute review with ReviewOutput schema.
        
            Updated state with structured review
        """
        query = state["query"]
        draft = state.get("draft", "")
        context = state.get("retrieved_context", [])
        
        # Intelligent context summarization using FREE model
        if context:
            # Prepare full context
            full_context = "\n\n".join([
                f"Source: {src.get('title', 'Unknown')}\nURL: {src.get('url', '')}\nContent: {src.get('content', '')}"
                for src in context[:5]  # Use top 5 sources
            ])
            
            # Use gemini-2.0-flash-exp (FREE) to summarize context
            summary_prompt = (Prompt()
                .set_system("""You are a context summarizer for fact-checking.
Your task is to condense source material into a concise summary that preserves key facts, statistics, and claims.
Focus on information relevant to verifying the accuracy of a research draft.""")
                .set_user_input(f"""Summarize these sources for fact-checking purposes:

{full_context}

Provide a concise summary focusing on key facts and claims.""")
            )
            
            context_summary, _ = self.summary_client.get_response(summary_prompt)
            context_text = context_summary
        else:
            context_text = "No context available"
        
        # Build prompt
        # Get iteration count for lenient approval
        iteration_count = state.get('iteration_count', 0)
        iteration_note = ""
        if iteration_count >= 7:
            iteration_note = "\n\n⚠️ HIGH ITERATION COUNT: Be MORE lenient - approve decent drafts (score >0.7)."
        
        prompt = (Prompt()
            .set_system(self.system_prompt)
            .set_user_input(f"""Query: {query}

Draft (full):
{draft}

Context:
{context_text}

Evaluate and return JSON.{iteration_note}

IMPORTANT: If the draft is generally accurate and answers the query, set "approval": true. 
Only set "approval": false for critical factual errors or completely missing sections.
Don't be overly pedantic about minor styling or missing minor citations.

{{
    "scores": [{{"dimension": str, "score": float, "reasoning": str}}],
    "overall_score": float,
    "strengths": [str],
    "weaknesses": [str],
    "actionable_feedback": [str],
    "approval": bool,
    "needs_more_data": bool
}}""")
        )
        prompt.set_output_schema(ReviewOutput)
        response, usage = self.client.get_response(prompt)
        
        # Update state
        updated_state = state.copy()
        
        # Track tokens for cost calculation
        if "input_tokens" not in updated_state:
            updated_state["input_tokens"] = {}
        if "output_tokens" not in updated_state:
            updated_state["output_tokens"] = {}
        if "total_tokens" not in updated_state:
            updated_state["total_tokens"] = {}
        
        model = self.model_name
        updated_state["input_tokens"][model] = updated_state["input_tokens"].get(model, 0) + usage.prompt_tokens
        updated_state["output_tokens"][model] = updated_state["output_tokens"].get(model, 0) + usage.completion_tokens
        updated_state["total_tokens"][model] = updated_state["total_tokens"].get(model, 0) + usage.total_tokens
        
        # Parse
        try:
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
            else:
                json_str = response
            data = json.loads(json_str)
            review_output = ReviewOutput(**data)
        except:
            # Fallback
            review_output = ReviewOutput(
                scores=[QualityScore(dimension="overall", score=0.6, reasoning="Fallback score")],
                overall_score=0.6,
                strengths=["Draft exists"],
                weaknesses=["Unable to parse structured review"],
                actionable_feedback=["Review manually"],
                approval=False,
                needs_more_data=False
            )
        
        # Update state
        updated_state["feedback"] = "\n".join(review_output.actionable_feedback)
        updated_state["scores"] = {s.dimension: s.score for s in review_output.scores}
        updated_state["is_complete"] = review_output.approval
        updated_state["needs_more_data"] = review_output.needs_more_data
        updated_state["messages"] = state["messages"] + [{
            "role": "assistant",
            "content": f"Review complete. Score: {review_output.overall_score:.2f}",
            "agent": "reviewer",
            "structured_output": review_output.dict()
        }]
        updated_state["current_agent"] = "reviewer"
        
        # Token tracking
        if "total_tokens" not in updated_state:
            updated_state["total_tokens"] = {}
        updated_state["total_tokens"][self.model_name] = updated_state["total_tokens"].get(self.model_name, 0) + usage.total_tokens
        
        return updated_state


# Convenience functions

def create_researcher() -> ResearcherAgent:
    """Factory function to create ResearcherAgent (now uses DirectTavilyClient internally)."""
    return ResearcherAgent()


def create_analyst() -> AnalystAgent:
    """Create an Analyst agent instance."""
    return AnalystAgent()


def create_synthesizer() -> SynthesizerAgent:
    """Create a Synthesizer agent instance."""
    return SynthesizerAgent()


def create_reviewer() -> ReviewerAgent:
    """Create a Reviewer agent instance."""
    return ReviewerAgent()
