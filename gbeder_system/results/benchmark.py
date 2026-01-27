"""
Benchmarking System for GBeder Patterns
Tracks latency, costs, token usage, and quality metrics across patterns.
"""
import time
import json
import asyncio
from typing import Dict, Any, List
from datetime import datetime
import os
import sys

from gbeder_system.state import GBederState
from gbeder_system.config import MODEL_COSTS, AGENT_MODELS

# Path hack to allow importing from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from client_factory import create_client


class PatternBenchmark:
    """Benchmark runner for comparing graph patterns."""
    
    def __init__(self):
        """
        Initialize benchmark.
        """
        self.results: List[Dict[str, Any]] = []

    def _serialize_messages(self, messages: List[Any]) -> List[Dict[str, Any]]:
        """Helper to convert mixed message types (Dict, AIMessage) to serializable dicts."""
        serialized = []
        for msg in messages:
            if isinstance(msg, dict):
                serialized.append(msg)
            elif hasattr(msg, 'model_dump'):  # Pydantic v2 / LangChain
                serialized.append(msg.model_dump())
            elif hasattr(msg, 'dict'):  # Pydantic v1
                serialized.append(msg.dict())
            else:
                # Fallback for generic objects
                serialized.append({
                    "type": getattr(msg, "type", "message"),
                    "content": getattr(msg, "content", str(msg)),
                    "role": getattr(msg, "role", "unknown"),
                    "agent": getattr(msg, "additional_kwargs", {}).get("agent", "unknown"),
                    "structured_output": getattr(msg, "structured_output", getattr(msg, "additional_kwargs", {}).get("structured_output", {}))
                })
        return serialized
    
    async def run_pattern(
        self,
        pattern_name: str,
        graph_func,
        query: str,
        thread_id: str = None
    ) -> Dict[str, Any]:
        """
        Run a single pattern and collect metrics.
        """
        print(f"\n{'='*60}")
        print(f"Running {pattern_name} Pattern")
        print(f"{'='*60}")
        
        # Create graph
        graph = graph_func()
        
        # Initial state
        initial_state: GBederState = {
            "messages": [],
            "query": query,
            "retrieved_context": [],
            "analysis": "",
            "draft": "",
            "feedback": "",
            "scores": {},
            "iteration_count": 0,
            "pattern_name": pattern_name,
            "current_agent": "",
            "total_tokens": {},
            "total_cost": 0.0,
            "is_complete": False,
            "needs_more_data": False,
            "tavily_api_calls": 0,
            "tavily_total_searches": 0
        }
        
        # Run with timing
        start_time = time.time()
        
        config = {
            "configurable": {
                "thread_id": thread_id or f"bench_{pattern_name}_{int(time.time())}"
            }
        }
        
        try:
            result = await graph.ainvoke(initial_state, config)
            success = True
            error = None
        except Exception as e:
            result = initial_state
            success = False
            error = str(e)
            print(f"ERROR: {error}")
        
        end_time = time.time()
        latency = end_time - start_time
        
        # Calculate costs
        total_cost = 0.0
        token_breakdown = result.get("total_tokens", {})
        input_tokens = result.get("input_tokens", {})
        output_tokens = result.get("output_tokens", {})

        # Create a client to use estimate_cost method
        client = create_client("gemini")
        client.select_model("gemini-2.0-flash")
        
        for model_name, tokens in token_breakdown.items():
            # estimate_cost returns a CostEstimate object, extract total_cost from it
            try:
                cost_estimate = client.estimate_cost(
                    model=model_name, 
                    prompt_tokens=input_tokens.get(model_name, 0), 
                    completion_tokens=output_tokens.get(model_name, 0)
                )
                total_cost += cost_estimate.total_cost
            except Exception:
                pass # Skip cost calculation if model not found in pricing
        
        # Serialize messages before storing in result
        serialized_messages = self._serialize_messages(result.get("messages", []))

        # Compile results
        benchmark_result = {
            "pattern_name": pattern_name,
            "query": query,
            "timestamp": datetime.now().isoformat(),
            "success": success,
            "error": error,
            "latency_seconds": round(latency, 2),
            "iterations": result.get("iteration_count", 0),
            "is_complete": result.get("is_complete", False),
            "scores": result.get("scores", {}),
            "avg_score": round(sum(result.get("scores", {}).values()) / len(result.get("scores", {})), 3) if result.get("scores") else 0.0,
            "token_usage": token_breakdown,
            "total_tokens": sum(token_breakdown.values()),
            "estimated_cost_usd": round(total_cost, 4),
            "draft_length": len(result.get("draft", "")),
            "num_sources": len(result.get("retrieved_context", [])),
            "models_used": list(token_breakdown.keys()),
            # Tavily usage tracking
            "tavily_api_calls": result.get("tavily_api_calls", 0),
            "tavily_total_searches": result.get("tavily_total_searches", 0),
            # Store complete execution details for detailed reporting
            "full_state": {
                "messages": serialized_messages,  # <--- UPDATED: Uses serialized list
                "retrieved_context": result.get("retrieved_context", []),
                "analysis": result.get("analysis", ""),
                "draft": result.get("draft", ""),
                "feedback": result.get("feedback", "")
            }
        }
        
        self.results.append(benchmark_result)
        
        # Generate and save detailed workflow report for this pattern
        self._save_detailed_report(benchmark_result, output_dir="results/output")
        
        # Print summary
        print(f"\n✓ Completed in {latency:.2f}s")
        print(f"  Iterations: {benchmark_result['iterations']}")
        print(f"  Quality: {benchmark_result['avg_score']:.3f}")
        print(f"  Cost: ${benchmark_result['estimated_cost_usd']:.4f}")
        print(f"  Tokens: {benchmark_result['total_tokens']:,}")
        print(f"  Tavily Searches: {benchmark_result['tavily_total_searches']}")
        
        return benchmark_result
    
    def _save_detailed_report(self, result: Dict[str, Any], output_dir: str = "results/output"):
        """
        Generate and save a detailed markdown report showing the complete workflow.
        """
        os.makedirs(output_dir, exist_ok=True)
        
        pattern_name = result["pattern_name"]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(output_dir, f"{pattern_name}_workflow_{timestamp}.md")
        
        # Extract data
        query = result["query"]
        messages = result["full_state"]["messages"]
        draft = result["full_state"]["draft"]
        
        # Build detailed report
        report_lines = []
        report_lines.append(f"# {pattern_name.upper()} Pattern - Detailed Workflow Report")
        report_lines.append(f"\n**Query:** {query}")
        report_lines.append(f"\n**Timestamp:** {result['timestamp']}")
        report_lines.append(f"**Status:** {'✅ Success' if result['success'] else '❌ Failed'}")
        report_lines.append(f"**Execution Time:** {result['latency_seconds']}s")
        report_lines.append(f"**Total Cost:** ${result['estimated_cost_usd']:.4f}")
        report_lines.append(f"**Iterations:** {result['iterations']}")
        report_lines.append("\n" + "="*80 + "\n")
        
        # Process messages by agent
        report_lines.append("## 🔄 Agent Execution Flow\n")
        
        for i, msg in enumerate(messages, 1):
            # Since we serialized earlier, 'msg' is now guaranteed to be a dict
            agent = msg.get("agent", "unknown")
            content = msg.get("content", "")
            structured_output = msg.get("structured_output", {})
            
            if agent == "researcher":
                report_lines.append(f"### Step {i}: 🔬 RESEARCHER\n")
                
                # Show refined queries
                if structured_output:
                    refined_queries = structured_output.get("search_queries_used", [])
                    if refined_queries:
                        report_lines.append("**Optimized Search Queries:**")
                        for q in refined_queries:
                            report_lines.append(f"- {q}")
                        report_lines.append("")
                    
                    # Show sources found
                    sources = structured_output.get("sources", [])
                    if sources:
                        report_lines.append(f"**Found {len(sources)} sources:**\n")
                        for idx, source in enumerate(sources[:5], 1):  # Top 5
                            report_lines.append(f"{idx}. **{source.get('title', 'Unknown')}**")
                            report_lines.append(f"   - URL: {source.get('url', 'N/A')}")
                            report_lines.append(f"   - Score: {source.get('score', 0):.2f}")
                            snippet = source.get('content', '')[:200]
                            report_lines.append(f"   - Preview: {snippet}...")
                            report_lines.append("")
                
            elif agent == "analyst":
                report_lines.append(f"### Step {i}: 📊 ANALYST\n")
                report_lines.append(f"**Analysis Summary:**\n{content}\n")
                
                if structured_output:
                    # Main insights
                    insights = structured_output.get("main_insights", [])
                    if insights:
                        report_lines.append("**Main Insights:**")
                        for insight in insights:
                            title = insight.get("title", "Insight")
                            desc = insight.get("description", "")
                            report_lines.append(f"- **{title}:** {desc}")
                        report_lines.append("")
                
            elif agent == "synthesizer":
                report_lines.append(f"### Step {i}: ✍️ SYNTHESIZER\n")
                if structured_output:
                    word_count = structured_output.get("word_count", 0)
                    report_lines.append(f"**Draft Created:** {word_count} words")
                report_lines.append(f"{content}\n")
                
            elif agent == "reviewer":
                report_lines.append(f"### Step {i}: 🔍 REVIEWER\n")
                if structured_output:
                    overall_score = structured_output.get("overall_score", 0)
                    approval = structured_output.get("approval", False)
                    report_lines.append(f"**Overall Score:** {overall_score:.2f}/1.0")
                    report_lines.append(f"**Status:** {'✅ Approved' if approval else '⚠️ Needs Revision'}\n")
                    
                    # Feedback
                    actionable = structured_output.get("actionable_feedback", [])
                    if actionable:
                        report_lines.append("**Feedback:**")
                        for fb in actionable:
                            report_lines.append(f"- {fb}")
            
            elif agent == "supervisor":
                report_lines.append(f"### Step {i}: 👮 SUPERVISOR\n")
                report_lines.append(f"{content}\n")

            else:
                 # Generic handler
                report_lines.append(f"### Step {i}: {str(agent).upper()}\n")
                report_lines.append(f"{content[:500]}...\n")

            report_lines.append("---\n")
        
        # Final result
        report_lines.append("## 📝 FINAL RESULT\n")
        if draft:
            report_lines.append(f"**Final Draft ({len(draft)} characters):**\n")
            report_lines.append(f"```\n{draft}\n```\n")
        else:
            report_lines.append("*No final draft available*\n")
        
        # Metrics summary
        report_lines.append("\n## 📊 Execution Metrics\n")
        report_lines.append(f"- **Latency:** {result['latency_seconds']}s")
        report_lines.append(f"- **Total Tokens:** {result['total_tokens']:,}")
        report_lines.append(f"- **Estimated Cost:** ${result['estimated_cost_usd']:.4f}")
        report_lines.append(f"- **Models Used:** {', '.join(result['models_used'])}")
        report_lines.append(f"- **Final Quality Score:** {result['avg_score']:.3f}")
        
        # Write to file
        with open(filename, "w", encoding="utf-8") as f:
            f.write("\n".join(report_lines))
        
        print(f"📄 Detailed workflow report saved to: {filename}")
    
    def save_results(self, output_dir: str = "results"):
        """Save benchmark results to JSON file."""
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(output_dir, f"benchmark_{timestamp}.json")
        
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        
        print(f"\n📊 Results saved to: {filename}")
        return filename
    
    def generate_report(self) -> str:
        """Generate a comparison report."""
        if not self.results:
            return "No results to report"
        
        report = []
        report.append("\n" + "="*80)
        report.append("GBEDER MULTI-AGENT SYSTEM - BENCHMARK REPORT")
        report.append("="*80)
        
        # Summary table
        report.append("\n## Pattern Comparison\n")
        report.append(f"{'Pattern':<20} {'Latency(s)':<12} {'Cost($)':<10} {'Tokens':<10} {'Tavily':<10} {'Quality':<10} {'Complete':<10}")
        report.append("-" * 92)
        
        for result in self.results:
            report.append(
                f"{result['pattern_name']:<20} "
                f"{result['latency_seconds']:<12.2f} "
                f"{result['estimated_cost_usd']:<10.4f} "
                f"{result['total_tokens']:<10,} "
                f"{result.get('tavily_total_searches', 0):<10} "
                f"{result['avg_score']:<10.3f} "
                f"{'✓' if result['is_complete'] else '✗':<10}"
            )
        
        # Detailed breakdown
        report.append("\n## Detailed Results\n")
        
        for result in self.results:
            report.append(f"\n### {result['pattern_name'].upper()}")
            report.append(f"- Query: {result['query']}")
            report.append(f"- Success: {'✓' if result['success'] else '✗ ' + result.get('error', '')}")
            report.append(f"- Latency: {result['latency_seconds']:.2f}s")
            report.append(f"- Iterations: {result['iterations']}")
            report.append(f"- Quality Score: {result['avg_score']:.3f}")
            report.append(f"- Individual Scores: {result['scores']}")
            report.append(f"- Total Tokens: {result['total_tokens']:,}")
            report.append(f"- Estimated Cost: ${result['estimated_cost_usd']:.4f}")
            report.append(f"- Models Used: {', '.join(result['models_used'])}")
            report.append(f"- Draft Length: {result['draft_length']} chars")
            report.append(f"- Sources: {result['num_sources']}")
            
            # Add Final Draft section
            report.append(f"\n**Final Draft:**")
            draft_content = result.get('full_state', {}).get('draft', '')
            if draft_content:
                report.append(f"```\n{draft_content}\n```")
            else:
                report.append("*No draft generated*")
        
        # Recommendations
        report.append("\n## Recommendations\n")
        
        # Find best pattern for each metric
        if len(self.results) > 1:
            fastest = min(self.results, key=lambda x: x['latency_seconds'])
            cheapest = min(self.results, key=lambda x: x['estimated_cost_usd'])
            highest_quality = max(self.results, key=lambda x: x['avg_score'])
            
            report.append(f"- **Fastest**: {fastest['pattern_name']} ({fastest['latency_seconds']:.2f}s)")
            report.append(f"- **Most Cost-Effective**: {cheapest['pattern_name']} (${cheapest['estimated_cost_usd']:.4f})")
            report.append(f"- **Highest Quality**: {highest_quality['pattern_name']} (score: {highest_quality['avg_score']:.3f})")
        
        report.append("\n" + "="*80)
        
        return "\n".join(report)


if __name__ == "__main__":
    print("Benchmark module loaded. Use run_comparison.py to execute benchmarks.")