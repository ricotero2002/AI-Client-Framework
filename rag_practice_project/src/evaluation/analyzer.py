"""
Analizador de resultados de experimentos RAG
"""
from typing import List, Dict, Any
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import json

class ResultsAnalyzer:
    """
    Analiza y visualiza resultados de experimentos RAG
    """
    
    def __init__(self, results: List[Dict[str, Any]]):
        """
        Inicializa el analizador
        
        Args:
            results: Lista de resultados de experimentos
        """
        self.results = results
        self.df = self._create_dataframe()
    
    def _create_dataframe(self) -> pd.DataFrame:
        """
        Crea DataFrame desde los resultados
        
        Returns:
            pd.DataFrame: DataFrame con resultados
        """
        rows = []
        for result in self.results:
            row = {
                "strategy": result["strategy"],
                "query": result["query"],
                "latency_ms": result["latency_ms"],
                "total_tokens": result["total_tokens"],
                "cost_usd": result["cost_usd"],
                **result["quality_metrics"]
            }
            rows.append(row)
        
        return pd.DataFrame(rows)
    
    def print_summary(self):
        """
        Imprime resumen de resultados
        """
        print("\n📊 MÉTRICAS POR ESTRATEGIA\n")
        
        summary = self.df.groupby("strategy").agg({
            "latency_ms": ["mean", "std"],
            "total_tokens": ["mean", "sum"],
            "cost_usd": ["mean", "sum"],
            "overall_score": ["mean", "std"],
            "relevance": "mean",
            "clarity": "mean",
            "conciseness": "mean"
        }).round(3)
        
        print(summary)
        
        # Ranking por score general
        print("\n🏆 RANKING POR CALIDAD (Overall Score)\n")
        ranking = self.df.groupby("strategy")["overall_score"].mean().sort_values(ascending=False)
        for i, (strategy, score) in enumerate(ranking.items(), 1):
            print(f"{i}. {strategy}: {score:.3f}")
        
        # Ranking por latencia
        print("\n⚡ RANKING POR VELOCIDAD (Latencia)\n")
        latency_ranking = self.df.groupby("strategy")["latency_ms"].mean().sort_values()
        for i, (strategy, latency) in enumerate(latency_ranking.items(), 1):
            print(f"{i}. {strategy}: {latency:.1f} ms")
        
        # Ranking por costo
        print("\n💰 RANKING POR COSTO\n")
        cost_ranking = self.df.groupby("strategy")["cost_usd"].sum().sort_values()
        for i, (strategy, cost) in enumerate(cost_ranking.items(), 1):
            print(f"{i}. {strategy}: ${cost:.4f}")
    
    def generate_visualizations(self, output_dir: Path):
        """
        Genera visualizaciones de los resultados
        
        Args:
            output_dir: Directorio de salida
        """
        sns.set_style("whitegrid")
        
        # 1. Comparación de latencia
        plt.figure(figsize=(12, 6))
        sns.boxplot(data=self.df, x="strategy", y="latency_ms")
        plt.xticks(rotation=45, ha="right")
        plt.title("Comparación de Latencia por Estrategia")
        plt.ylabel("Latencia (ms)")
        plt.tight_layout()
        plt.savefig(output_dir / "latency_comparison.png", dpi=300)
        plt.close()
        
        # 2. Comparación de calidad
        plt.figure(figsize=(12, 6))
        quality_metrics = ["relevance", "clarity", "conciseness", "overall_score"]
        quality_data = self.df.groupby("strategy")[quality_metrics].mean()
        quality_data.plot(kind="bar", figsize=(12, 6))
        plt.title("Comparación de Métricas de Calidad")
        plt.ylabel("Score (0-1)")
        plt.xlabel("Estrategia")
        plt.xticks(rotation=45, ha="right")
        plt.legend(title="Métrica")
        plt.tight_layout()
        plt.savefig(output_dir / "quality_comparison.png", dpi=300)
        plt.close()
        
        # 3. Costo vs Calidad
        plt.figure(figsize=(10, 6))
        cost_quality = self.df.groupby("strategy").agg({
            "cost_usd": "sum",
            "overall_score": "mean"
        })
        plt.scatter(cost_quality["cost_usd"], cost_quality["overall_score"], s=200, alpha=0.6)
        for strategy, row in cost_quality.iterrows():
            plt.annotate(strategy, (row["cost_usd"], row["overall_score"]), 
                        xytext=(5, 5), textcoords="offset points")
        plt.xlabel("Costo Total (USD)")
        plt.ylabel("Score de Calidad Promedio")
        plt.title("Costo vs Calidad")
        plt.tight_layout()
        plt.savefig(output_dir / "cost_vs_quality.png", dpi=300)
        plt.close()
        
        # 4. Latencia vs Calidad
        plt.figure(figsize=(10, 6))
        latency_quality = self.df.groupby("strategy").agg({
            "latency_ms": "mean",
            "overall_score": "mean"
        })
        plt.scatter(latency_quality["latency_ms"], latency_quality["overall_score"], s=200, alpha=0.6)
        for strategy, row in latency_quality.iterrows():
            plt.annotate(strategy, (row["latency_ms"], row["overall_score"]), 
                        xytext=(5, 5), textcoords="offset points")
        plt.xlabel("Latencia Promedio (ms)")
        plt.ylabel("Score de Calidad Promedio")
        plt.title("Latencia vs Calidad")
        plt.tight_layout()
        plt.savefig(output_dir / "latency_vs_quality.png", dpi=300)
        plt.close()
        
        # 5. Heatmap de métricas
        plt.figure(figsize=(10, 8))
        metrics_heatmap = self.df.groupby("strategy")[
            ["relevance", "clarity", "conciseness", "overall_score"]
        ].mean()
        sns.heatmap(metrics_heatmap.T, annot=True, fmt=".3f", cmap="YlGnBu", cbar_kws={"label": "Score"})
        plt.title("Heatmap de Métricas de Calidad")
        plt.tight_layout()
        plt.savefig(output_dir / "quality_heatmap.png", dpi=300)
        plt.close()
        
        print(f"✓ Visualizaciones guardadas en: {output_dir}")
    
    def export_to_csv(self, output_path: Path):
        """
        Exporta resultados a CSV
        
        Args:
            output_path: Ruta del archivo CSV
        """
        self.df.to_csv(output_path, index=False)
        print(f"✓ Resultados exportados a: {output_path}")
    
    def generate_report(self, output_path: Path):
        """
        Genera reporte en formato Markdown
        
        Args:
            output_path: Ruta del archivo de reporte
        """
        report = []
        report.append("# Reporte de Evaluación RAG - Recetas Vegetarianas\n")
        report.append(f"Fecha: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        report.append(f"Total de experimentos: {len(self.results)}\n")
        report.append(f"Estrategias evaluadas: {self.df['strategy'].nunique()}\n")
        report.append(f"Consultas de prueba: {self.df['query'].nunique()}\n\n")
        
        report.append("## Resumen de Métricas por Estrategia\n\n")
        summary = self.df.groupby("strategy").agg({
            "latency_ms": ["mean", "std"],
            "total_tokens": ["mean", "sum"],
            "cost_usd": ["mean", "sum"],
            "overall_score": ["mean", "std"]
        }).round(3)
        report.append(summary.to_markdown())
        report.append("\n\n")
        
        report.append("## Rankings\n\n")
        report.append("### Por Calidad (Overall Score)\n\n")
        ranking = self.df.groupby("strategy")["overall_score"].mean().sort_values(ascending=False)
        for i, (strategy, score) in enumerate(ranking.items(), 1):
            report.append(f"{i}. **{strategy}**: {score:.3f}\n")
        
        report.append("\n### Por Velocidad (Latencia)\n\n")
        latency_ranking = self.df.groupby("strategy")["latency_ms"].mean().sort_values()
        for i, (strategy, latency) in enumerate(latency_ranking.items(), 1):
            report.append(f"{i}. **{strategy}**: {latency:.1f} ms\n")
        
        report.append("\n### Por Costo\n\n")
        cost_ranking = self.df.groupby("strategy")["cost_usd"].sum().sort_values()
        for i, (strategy, cost) in enumerate(cost_ranking.items(), 1):
            report.append(f"{i}. **{strategy}**: ${cost:.4f}\n")
        
        # Guardar reporte
        with open(output_path, 'w', encoding='utf-8') as f:
            f.writelines(report)
        
        print(f"✓ Reporte generado en: {output_path}")
