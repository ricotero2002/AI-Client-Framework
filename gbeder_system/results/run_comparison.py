"""
Run Comparison - Execute all patterns and generate comparison report.
This script runs all three GBeder patterns with test queries and compares performance.
"""
import sys
import os
import asyncio

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# Add parent directory to path so gbeder_system can be imported
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from gbeder_system.graphs.supervisor_pattern import create_supervisor_graph
from gbeder_system.graphs.sequential_pattern import create_sequential_graph
from gbeder_system.graphs.reflexion_pattern import create_reflexion_graph
from gbeder_system.mcp_client import MCPClient
from gbeder_system.results.benchmark import PatternBenchmark


# Test queries with varying complexity
TEST_QUERIES = [
    #"Explain Boca Juniors 2025-2026 football transfer market",
    #"What are the most used frameworks for AI engineering in 2026?",
    #"Most popular Vegan Recipies in sudamerica",
    "Best cost-effective phones in Argentina 2026"
]


async def run_all_comparisons(query: str = None, use_mcp: bool = True):
    """
    Run all three patterns and generate comparison.
    
    Args:
        query: Optional specific query to test (uses first test query if None)
        use_mcp: Whether to use MCP client for Tavily integration
    """
    if query is None:
        query = TEST_QUERIES[0]
    
    print("\n" + "="*80)
    print("GBEDER MULTI-AGENT SYSTEM - PATTERN COMPARISON")
    print("="*80)
    print(f"\nQuery: {query}")
    
    # Create benchmark runner
    benchmark = PatternBenchmark()
    
    # Pattern configurations
    patterns = [
        ("supervisor", create_supervisor_graph),
        ("sequential", create_sequential_graph),
        ("reflexion", create_reflexion_graph)
    ]
    
    # Run each pattern
    for pattern_name, graph_func in patterns:
        try:
            await benchmark.run_pattern(
                pattern_name=pattern_name,
                graph_func=graph_func,
                query=query
            )
        except Exception as e:
            print(f"\n❌ Error running {pattern_name}: {str(e)}")
            import traceback
            traceback.print_exc()
    
    # Generate and display report
    report = benchmark.generate_report()
    print(report)
    
    # Save results
    results_dir = os.path.join(os.path.dirname(__file__), "output")
    filename = benchmark.save_results(results_dir)
    
    # Save report as text file
    report_filename = filename.replace(".json", "_report.txt")
    with open(report_filename, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"📄 Report saved to: {report_filename}")
    
    return benchmark.results


async def run_multiple_queries():
    """Run all test queries and generate comprehensive comparison."""
    print("\n" + "="*80)
    print("RUNNING COMPREHENSIVE BENCHMARK WITH MULTIPLE QUERIES")
    print("="*80)
    
    all_results = []
    
    for i, query in enumerate(TEST_QUERIES, 1):
        print(f"\n\n{'#'*80}")
        print(f"TEST QUERY {i}/{len(TEST_QUERIES)}")
        print(f"{'#'*80}")
        
        results = await run_all_comparisons(query=query)
        all_results.extend(results)
        
        # Brief pause between queries
        if i < len(TEST_QUERIES):
            print("\nWaiting 2 seconds before next query...")
            await asyncio.sleep(2)
    
    # Generate aggregate report
    print("\n\n" + "="*80)
    print("AGGREGATE RESULTS ACROSS ALL QUERIES")
    print("="*80)
    
    # Group by pattern
    from collections import defaultdict
    pattern_stats = defaultdict(lambda: {
        "total_latency": 0,
        "total_cost": 0,
        "total_tokens": 0,
        "avg_quality": [],
        "success_count": 0,
        "total_runs": 0
    })
    
    for result in all_results:
        pattern = result["pattern_name"]
        pattern_stats[pattern]["total_latency"] += result["latency_seconds"]
        pattern_stats[pattern]["total_cost"] += result["estimated_cost_usd"]
        pattern_stats[pattern]["total_tokens"] += result["total_tokens"]
        pattern_stats[pattern]["avg_quality"].append(result["avg_score"])
        if result["success"]:
            pattern_stats[pattern]["success_count"] += 1
        pattern_stats[pattern]["total_runs"] += 1
    
    # Display aggregate stats
    print(f"\n{'Pattern':<15} {'Avg Latency':<15} {'Avg Cost':<15} {'Avg Quality':<15} {'Success Rate':<15}")
    print("-" * 75)
    
    for pattern, stats in pattern_stats.items():
        n = stats["total_runs"]
        avg_latency = stats["total_latency"] / n
        avg_cost = stats["total_cost"] / n
        avg_quality = sum(stats["avg_quality"]) / len(stats["avg_quality"])
        success_rate = (stats["success_count"] / n) * 100
        
        print(
            f"{pattern:<15} "
            f"{avg_latency:<15.2f} "
            f"${avg_cost:<14.4f} "
            f"{avg_quality:<15.3f} "
            f"{success_rate:<14.1f}%"
        )
    
    print("\n" + "="*80)


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run GBeder pattern comparisons")
    parser.add_argument(
        "--query",
        type=str,
        help="Specific query to test (default: first test query)"
    )
    parser.add_argument(
        "--no-mcp",
        action="store_true",
        help="Run without MCP integration (fallback mode)"
    )
    parser.add_argument(
        "--all-queries",
        action="store_true",
        help="Run all test queries for comprehensive comparison"
    )
    
    args = parser.parse_args()
    
    if args.all_queries:
        asyncio.run(run_multiple_queries())
    else:
        asyncio.run(run_all_comparisons(
            query=args.query,
            use_mcp=not args.no_mcp
        ))


if __name__ == "__main__":
    main()
