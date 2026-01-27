"""
Benchmark Analysis Script
Analyzes benchmark report files to generate aggregate statistics across patterns.
Only includes reports where all patterns completed successfully.
"""
import os
import re
from collections import defaultdict
from typing import Dict, List, Any
from datetime import datetime


class BenchmarkAnalyzer:
    """Analyzes benchmark report files and generates aggregate statistics."""
    
    def __init__(self, reports_dir: str = "results/output"):
        """
        Initialize analyzer.
        
        Args:
            reports_dir: Directory containing benchmark report .txt files
        """
        self.reports_dir = reports_dir
        self.valid_reports = []
        self.pattern_stats = defaultdict(lambda: {
            "latencies": [],
            "costs": [],
            "tokens": [],
            "tavily_searches": [],
            "qualities": [],
            "iterations": [],
            "count": 0
        })
        self.queries = defaultdict(int)
    
    def parse_report_file(self, filepath: str) -> Dict[str, Any]:
        """
        Parse a single benchmark report file.
        
        Args:
            filepath: Path to report .txt file
            
        Returns:
            Dictionary with query and pattern results
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract query
        query_match = re.search(r'Query:\s*(.+?)(?:\n|$)', content)
        query = query_match.group(1).strip() if query_match else "Unknown"
        
        # Find Pattern Comparison section
        comparison_section = re.search(
            r'## Pattern Comparison(.+?)(?:## Detailed Results|$)',
            content,
            re.DOTALL
        )
        
        if not comparison_section:
            return None
        
        comparison_text = comparison_section.group(1)
        
        # Parse each pattern's row
        patterns = {}
        pattern_lines = re.findall(
            r'(\w+)\s+(\d+\.\d+)\s+(\d+\.\d+)\s+([\d,]+)\s+(\d+)\s+(\d+\.\d+)\s+([✓✗])',
            comparison_text
        )
        
        for match in pattern_lines:
            pattern_name = match[0]
            patterns[pattern_name] = {
                "latency": float(match[1]),
                "cost": float(match[2]),
                "tokens": int(match[3].replace(',', '')),
                "tavily": int(match[4]),
                "quality": float(match[5]),
                "complete": match[6] == '✓'
            }
        
        # Extract iterations from detailed section
        detailed_section = re.search(
            r'## Detailed Results(.+?)(?:## Recommendations|$)',
            content,
            re.DOTALL
        )
        
        if detailed_section:
            detailed_text = detailed_section.group(1)
            for pattern_name in patterns.keys():
                iter_match = re.search(
                    rf'### {pattern_name.upper()}.*?Iterations:\s*(\d+)',
                    detailed_text,
                    re.DOTALL | re.IGNORECASE
                )
                if iter_match:
                    patterns[pattern_name]["iterations"] = int(iter_match.group(1))
                else:
                    patterns[pattern_name]["iterations"] = 0
        
        return {
            "query": query,
            "patterns": patterns,
            "filepath": filepath
        }
    
    def is_valid_report(self, report_data: Dict[str, Any]) -> bool:
        """
        Check if report is valid (all patterns complete with values).
        
        Args:
            report_data: Parsed report data
            
        Returns:
            True if all patterns completed successfully
        """
        if not report_data or "patterns" not in report_data:
            return False
        
        patterns = report_data["patterns"]
        
        # Must have at least one pattern
        if len(patterns) == 0:
            return False
        
        # All patterns must be complete
        for pattern_name, data in patterns.items():
            if not data.get("complete", False):
                return False
            # Must have valid values
            if data.get("latency", 0) <= 0 or data.get("tokens", 0) <= 0:
                return False
        
        return True
    
    def analyze_reports(self):
        """Analyze all report files in the directory."""
        if not os.path.exists(self.reports_dir):
            print(f"❌ Directory not found: {self.reports_dir}")
            return
        
        # Find all report .txt files
        report_files = [
            f for f in os.listdir(self.reports_dir)
            if f.endswith('_report.txt') and 'benchmark_' in f
        ]
        
        print(f"📁 Found {len(report_files)} report files\n")
        
        # Parse each report
        for filename in sorted(report_files):
            filepath = os.path.join(self.reports_dir, filename)
            report_data = self.parse_report_file(filepath)
            
            if report_data and self.is_valid_report(report_data):
                self.valid_reports.append(report_data)
                
                # Count query
                query = report_data["query"]
                self.queries[query] += 1
                
                # Aggregate pattern stats
                for pattern_name, data in report_data["patterns"].items():
                    stats = self.pattern_stats[pattern_name]
                    stats["latencies"].append(data["latency"])
                    stats["costs"].append(data["cost"])
                    stats["tokens"].append(data["tokens"])
                    stats["tavily_searches"].append(data["tavily"])
                    stats["qualities"].append(data["quality"])
                    stats["iterations"].append(data.get("iterations", 0))
                    stats["count"] += 1
        
        print(f"✅ Valid reports (all patterns complete): {len(self.valid_reports)}\n")
    
    def generate_report(self) -> str:
        """
        Generate aggregate statistics report.
        
        Returns:
            Formatted report string
        """
        if not self.valid_reports:
            return "No valid reports found (all patterns must be complete)"
        
        lines = []
        lines.append("=" * 80)
        lines.append("BENCHMARK AGGREGATE ANALYSIS")
        lines.append("=" * 80)
        lines.append(f"\nAnalyzed: {len(self.valid_reports)} complete benchmark runs")
        lines.append(f"Report Directory: {self.reports_dir}")
        lines.append(f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        # Query statistics
        lines.append("\n" + "=" * 80)
        lines.append("QUERIES ANALYZED")
        lines.append("=" * 80 + "\n")
        
        for query, count in sorted(self.queries.items(), key=lambda x: -x[1]):
            lines.append(f"• {query}")
            lines.append(f"  Runs: {count}\n")
        
        # Pattern statistics
        lines.append("\n" + "=" * 80)
        lines.append("PATTERN PERFORMANCE AVERAGES")
        lines.append("=" * 80 + "\n")
        
        # Header
        lines.append(f"{'Pattern':<20} {'Runs':<8} {'Avg Latency':<15} {'Avg Cost':<12} {'Avg Tokens':<12} {'Avg Tavily':<12} {'Avg Quality':<12} {'Avg Iters':<10}")
        lines.append("-" * 110)
        
        # Sort patterns by average quality (descending)
        sorted_patterns = sorted(
            self.pattern_stats.items(),
            key=lambda x: sum(x[1]["qualities"]) / len(x[1]["qualities"]) if x[1]["qualities"] else 0,
            reverse=True
        )
        
        for pattern_name, stats in sorted_patterns:
            if stats["count"] == 0:
                continue
            
            avg_latency = sum(stats["latencies"]) / stats["count"]
            avg_cost = sum(stats["costs"]) / stats["count"]
            avg_tokens = sum(stats["tokens"]) / stats["count"]
            avg_tavily = sum(stats["tavily_searches"]) / stats["count"]
            avg_quality = sum(stats["qualities"]) / stats["count"]
            avg_iters = sum(stats["iterations"]) / stats["count"]
            
            lines.append(
                f"{pattern_name:<20} {stats['count']:<8} "
                f"{avg_latency:<15.2f} ${avg_cost:<11.4f} "
                f"{avg_tokens:<12,.0f} {avg_tavily:<12.1f} "
                f"{avg_quality:<12.3f} {avg_iters:<10.1f}"
            )
        
        # Detailed breakdown
        lines.append("\n\n" + "=" * 80)
        lines.append("DETAILED PATTERN STATISTICS")
        lines.append("=" * 80)
        
        for pattern_name, stats in sorted_patterns:
            if stats["count"] == 0:
                continue
            
            lines.append(f"\n### {pattern_name.upper()}")
            lines.append(f"Runs: {stats['count']}")
            
            # Latency
            avg_latency = sum(stats["latencies"]) / stats["count"]
            min_latency = min(stats["latencies"])
            max_latency = max(stats["latencies"])
            lines.append(f"• Latency: avg={avg_latency:.2f}s, min={min_latency:.2f}s, max={max_latency:.2f}s")
            
            # Cost
            avg_cost = sum(stats["costs"]) / stats["count"]
            min_cost = min(stats["costs"])
            max_cost = max(stats["costs"])
            total_cost = sum(stats["costs"])
            lines.append(f"• Cost: avg=${avg_cost:.4f}, min=${min_cost:.4f}, max=${max_cost:.4f}, total=${total_cost:.4f}")
            
            # Tokens
            avg_tokens = sum(stats["tokens"]) / stats["count"]
            min_tokens = min(stats["tokens"])
            max_tokens = max(stats["tokens"])
            total_tokens = sum(stats["tokens"])
            lines.append(f"• Tokens: avg={avg_tokens:,.0f}, min={min_tokens:,}, max={max_tokens:,}, total={total_tokens:,}")
            
            # Tavily
            avg_tavily = sum(stats["tavily_searches"]) / stats["count"]
            total_tavily = sum(stats["tavily_searches"])
            lines.append(f"• Tavily Searches: avg={avg_tavily:.1f}, total={total_tavily}")
            
            # Quality
            avg_quality = sum(stats["qualities"]) / stats["count"]
            min_quality = min(stats["qualities"])
            max_quality = max(stats["qualities"])
            lines.append(f"• Quality: avg={avg_quality:.3f}, min={min_quality:.3f}, max={max_quality:.3f}")
            
            # Iterations
            avg_iters = sum(stats["iterations"]) / stats["count"]
            min_iters = min(stats["iterations"])
            max_iters = max(stats["iterations"])
            lines.append(f"• Iterations: avg={avg_iters:.1f}, min={min_iters}, max={max_iters}")
        
        # Best performers
        lines.append("\n\n" + "=" * 80)
        lines.append("BEST PERFORMERS")
        lines.append("=" * 80 + "\n")
        
        if len(sorted_patterns) > 0:
            # Fastest
            fastest_pattern = min(
                sorted_patterns,
                key=lambda x: sum(x[1]["latencies"]) / x[1]["count"]
            )
            fastest_avg = sum(fastest_pattern[1]["latencies"]) / fastest_pattern[1]["count"]
            lines.append(f"⚡ Fastest (avg latency): {fastest_pattern[0]} ({fastest_avg:.2f}s)")
            
            # Cheapest
            cheapest_pattern = min(
                sorted_patterns,
                key=lambda x: sum(x[1]["costs"]) / x[1]["count"]
            )
            cheapest_avg = sum(cheapest_pattern[1]["costs"]) / cheapest_pattern[1]["count"]
            lines.append(f"💰 Cheapest (avg cost): {cheapest_pattern[0]} (${cheapest_avg:.4f})")
            
            # Most efficient (tokens)
            efficient_pattern = min(
                sorted_patterns,
                key=lambda x: sum(x[1]["tokens"]) / x[1]["count"]
            )
            efficient_avg = sum(efficient_pattern[1]["tokens"]) / efficient_pattern[1]["count"]
            lines.append(f"🔋 Most Token-Efficient: {efficient_pattern[0]} ({efficient_avg:,.0f} tokens)")
            
            # Least Tavily usage
            tavily_pattern = min(
                sorted_patterns,
                key=lambda x: sum(x[1]["tavily_searches"]) / x[1]["count"]
            )
            tavily_avg = sum(tavily_pattern[1]["tavily_searches"]) / tavily_pattern[1]["count"]
            lines.append(f"🔍 Least Tavily Usage: {tavily_pattern[0]} ({tavily_avg:.1f} searches)")
            
            # Highest quality
            quality_pattern = max(
                sorted_patterns,
                key=lambda x: sum(x[1]["qualities"]) / x[1]["count"]
            )
            quality_avg = sum(quality_pattern[1]["qualities"]) / quality_pattern[1]["count"]
            lines.append(f"⭐ Highest Quality: {quality_pattern[0]} ({quality_avg:.3f})")
        
        lines.append("\n" + "=" * 80)
        
        return "\n".join(lines)
    
    def save_report(self, output_file: str = None):
        """
        Save analysis report to file.
        
        Args:
            output_file: Optional output filepath
        """
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = os.path.join(self.reports_dir, f"aggregate_analysis_{timestamp}.txt")
        
        report = self.generate_report()
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(f"\n📊 Analysis saved to: {output_file}")
        return output_file


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Analyze benchmark reports")
    parser.add_argument(
        "--dir",
        type=str,
        default="results/output",
        help="Directory containing benchmark report files"
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output file path (default: auto-generate in reports dir)"
    )
    
    args = parser.parse_args()
    
    # Create analyzer
    analyzer = BenchmarkAnalyzer(reports_dir=args.dir)
    
    # Analyze reports
    analyzer.analyze_reports()
    
    # Generate and display report
    report = analyzer.generate_report()
    print("\n" + report)
    
    # Save to file
    analyzer.save_report(output_file=args.output)


if __name__ == "__main__":
    main()
