"""
Analizador de resultados de experimentos RAG con DeepEval
Implementa visualizaciones y diagnósticos especializados con explicaciones de fallos
"""
from typing import List, Dict, Any
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import json
import numpy as np


class ResultsAnalyzer:
    """
    Analiza y visualiza resultados de experimentos RAG usando métricas de DeepEval.
    
    Métricas agrupadas en:
    - RETRIEVAL: Contextual Precision, Recall, Relevancy
    - GENERATION: Faithfulness, Answer Relevancy
    
    Ahora incluye análisis de 'reasons' (explicaciones de fallos) de DeepEval.
    """
    
    def __init__(self, results: List[Dict[str, Any]]):
        """
        Inicializa el analizador.
        
        Args:
            results: Lista de resultados de experimentos con métricas DeepEval
        """
        self.results = results
        self.df = self._create_dataframe()
    
    def _create_dataframe(self) -> pd.DataFrame:
        """
        Crea DataFrame desde los resultados, aplanando estructura DeepEval.
        
        DeepEval retorna métricas como {"score": float, "reason": str}.
        Este método aplana esa estructura en columnas separadas.
        
        Returns:
            pd.DataFrame: DataFrame con resultados aplanados
        """
        rows = []
        for result in self.results:
            quality_metrics = result["quality_metrics"]
            
            row = {
                "strategy": result["strategy"],
                "query": result["query"],
                "expected_output": result.get("expected_output", ""),
                "latency_ms": result["latency_ms"],
                "total_tokens": result["total_tokens"],
                "cost_usd": result["cost_usd"],
                # Aplanar scores
                "contextual_precision_score": quality_metrics["contextual_precision"]["score"],
                "contextual_recall_score": quality_metrics["contextual_recall"]["score"],
                "contextual_relevancy_score": quality_metrics["contextual_relevancy"]["score"],
                "faithfulness_score": quality_metrics["faithfulness"]["score"],
                "answer_relevancy_score": quality_metrics["answer_relevancy"]["score"],
                "overall_score": quality_metrics["overall_score"],
                # Mantener reasons para análisis posterior
                "contextual_precision_reason": quality_metrics["contextual_precision"]["reason"],
                "contextual_recall_reason": quality_metrics["contextual_recall"]["reason"],
                "contextual_relevancy_reason": quality_metrics["contextual_relevancy"]["reason"],
                "faithfulness_reason": quality_metrics["faithfulness"]["reason"],
                "answer_relevancy_reason": quality_metrics["answer_relevancy"]["reason"],
            }
            rows.append(row)
        
        return pd.DataFrame(rows)
    
    def print_summary(self):
        """
        Imprime resumen de resultados agrupado por categorías RAG Triad.
        """
        print("\n" + "="*70)
        print("📊 RAG TRIAD EVALUATION SUMMARY (DeepEval)")
        print("="*70)
        
        # Métricas por estrategia
        summary = self.df.groupby("strategy").agg({
            "latency_ms": ["mean", "std"],
            "total_tokens": ["mean", "sum"],
            "cost_usd": ["mean", "sum"],
            "overall_score": ["mean", "std"]
        }).round(3)
        
        print("\n📈 General Metrics by Strategy:\n")
        print(summary)
        
        # === RETRIEVAL METRICS ===
        print("\n" + "="*70)
        print("🔍 RETRIEVAL METRICS (Evaluación del Retriever)")
        print("="*70)
        
        retrieval_metrics = self.df.groupby("strategy")[
            ["contextual_precision_score", "contextual_recall_score", "contextual_relevancy_score"]
        ].mean().round(3)
        
        print("\n", retrieval_metrics)
        
        # Diagnósticos automáticos para retrieval
        print("\n💡 Diagnósticos Automáticos (Retrieval):")
        for strategy in retrieval_metrics.index:
            precision = retrieval_metrics.loc[strategy, "contextual_precision_score"]
            recall = retrieval_metrics.loc[strategy, "contextual_recall_score"]
            relevancy = retrieval_metrics.loc[strategy, "contextual_relevancy_score"]
            
            print(f"\n  [{strategy}]")
            if precision < 0.5:
                print(f"    ⚠️  Baja Precision ({precision:.3f}) → Chunks irrelevantes al inicio. Revisar reranking.")
            if recall < 0.6:
                print(f"    ⚠️  Bajo Recall ({recall:.3f}) → Información faltante. Revisar embeddings o aumentar top_k.")
            if relevancy < 0.6:
                print(f"    ⚠️  Baja Relevancy ({relevancy:.3f}) → Mucho contenido irrelevante. Mejorar retrieval.")
            if precision >= 0.7 and recall >= 0.7 and relevancy >= 0.7:
                print(f"    ✓ Retrieval en buen estado (P:{precision:.2f}, R:{recall:.2f}, Rel:{relevancy:.2f})")
        
        # === GENERATION METRICS ===
        print("\n" + "="*70)
        print("🤖 GENERATION METRICS (Evaluación del Generator)")
        print("="*70)
        
        generation_metrics = self.df.groupby("strategy")[
            ["faithfulness_score", "answer_relevancy_score"]
        ].mean().round(3)
        
        print("\n", generation_metrics)
        
        # Diagnósticos automáticos para generation
        print("\n💡 Diagnósticos Automáticos (Generation):")
        for strategy in generation_metrics.index:
            faithfulness = generation_metrics.loc[strategy, "faithfulness_score"]
            relevancy = generation_metrics.loc[strategy, "answer_relevancy_score"]
            
            print(f"\n  [{strategy}]")
            if faithfulness < 0.7:
                print(f"    ⚠️  Alta Alucinación ({faithfulness:.3f}) → Mejorar prompt del generador o contexto.")
            if relevancy < 0.6:
                print(f"    ⚠️  Baja Answer Relevancy ({relevancy:.3f}) → Respuestas poco relevantes. Revisar prompt.")
            if faithfulness >= 0.8 and relevancy >= 0.8:
                print(f"    ✓ Generation en buen estado (Faith:{faithfulness:.2f}, Rel:{relevancy:.2f})")
        
        # === RANKINGS ===
        print("\n" + "="*70)
        print("🏆 RANKINGS")
        print("="*70)
        
        # Ranking por score general
        print("\n🥇 Por Calidad General (Overall Score):\n")
        ranking = self.df.groupby("strategy")["overall_score"].mean().sort_values(ascending=False)
        for i, (strategy, score) in enumerate(ranking.items(), 1):
            print(f"  {i}. {strategy}: {score:.3f}")
        
        # Ranking por latencia
        print("\n⚡ Por Velocidad (Latencia):\n")
        latency_ranking = self.df.groupby("strategy")["latency_ms"].mean().sort_values()
        for i, (strategy, latency) in enumerate(latency_ranking.items(), 1):
            print(f"  {i}. {strategy}: {latency:.1f} ms")
        
        # Ranking por costo
        print("\n💰 Por Costo Total:\n")
        cost_ranking = self.df.groupby("strategy")["cost_usd"].sum().sort_values()
        for i, (strategy, cost) in enumerate(cost_ranking.items(), 1):
            print(f"  {i}. {strategy}: ${cost:.4f}")
        
        print("\n" + "="*70)
    
    def _create_radar_chart(self, output_dir: Path):
        """
        Crea un radar chart para visualizar el balance entre las 5 métricas.
        
        Args:
            output_dir: Directorio de salida
        """
        strategies = self.df['strategy'].unique()
        metrics = [
            'contextual_precision_score',
            'contextual_recall_score',
            'contextual_relevancy_score',
            'faithfulness_score',
            'answer_relevancy_score'
        ]
        labels = ['C. Precision', 'C. Recall', 'C. Relevancy', 'Faithfulness', 'A. Relevancy']
        
        # Calcular ángulos para el polígono
        angles = np.linspace(0, 2 * np.pi, len(metrics), endpoint=False).tolist()
        angles += angles[:1]  # Cerrar el círculo
        
        fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(projection='polar'))
        
        # Colores para cada estrategia
        colors = plt.cm.Set2(np.linspace(0, 1, len(strategies)))
        
        for i, strategy in enumerate(strategies):
            values = self.df[self.df['strategy'] == strategy][metrics].mean().tolist()
            values += values[:1]  # Cerrar el polígono
            ax.plot(angles, values, 'o-', linewidth=2, label=strategy, color=colors[i])
            ax.fill(angles, values, alpha=0.15, color=colors[i])
        
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(labels, size=11)
        ax.set_ylim(0, 1)
        ax.set_title("RAG Metrics Balance (Radar Chart)", size=16, fontweight='bold', pad=20)
        ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1))
        ax.grid(True)
        
        plt.tight_layout()
        plt.savefig(output_dir / "radar_chart.png", dpi=300, bbox_inches='tight')
        plt.close()
        print(f"  - radar_chart.png")
    
    def generate_visualizations(self, output_dir: Path):
        """
        Genera visualizaciones especializadas para métricas DeepEval.
        
        Args:
            output_dir: Directorio de salida
        """
        sns.set_style("whitegrid")
        sns.set_palette("husl")
        
        print(f"\n✓ Generando visualizaciones en: {output_dir}")
        
        # 1. Radar Chart (NUEVO)
        self._create_radar_chart(output_dir)
        
        # 2. Comparación de latencia
        plt.figure(figsize=(12, 6))
        sns.boxplot(data=self.df, x="strategy", y="latency_ms")
        plt.xticks(rotation=45, ha="right")
        plt.title("Comparación de Latencia por Estrategia", fontsize=14, fontweight='bold')
        plt.ylabel("Latencia (ms)")
        plt.tight_layout()
        plt.savefig(output_dir / "latency_comparison.png", dpi=300)
        plt.close()
        print(f"  - latency_comparison.png")
        
        # 3. Gráfico de barras agrupado: Retrieval vs Generation (ACTUALIZADO)
        fig, axes = plt.subplots(1, 2, figsize=(16, 6))
        
        # Panel 1: Retrieval Metrics
        retrieval_data = self.df.groupby("strategy")[
            ["contextual_precision_score", "contextual_recall_score", "contextual_relevancy_score"]
        ].mean()
        
        retrieval_data.plot(kind="bar", ax=axes[0])
        axes[0].set_title("Retrieval Metrics", fontsize=14, fontweight='bold')
        axes[0].set_ylabel("Score (0-1)")
        axes[0].set_xlabel("Estrategia")
        axes[0].set_xticklabels(axes[0].get_xticklabels(), rotation=45, ha="right")
        axes[0].legend(["Precision", "Recall", "Relevancy"], loc="lower right")
        axes[0].set_ylim(0, 1)
        axes[0].axhline(y=0.7, color='green', linestyle='--', alpha=0.3, label='Target (0.7)')
        
        # Panel 2: Generation Metrics
        generation_data = self.df.groupby("strategy")[
            ["faithfulness_score", "answer_relevancy_score"]
        ].mean()
        
        generation_data.plot(kind="bar", ax=axes[1])
        axes[1].set_title("Generation Metrics", fontsize=14, fontweight='bold')
        axes[1].set_ylabel("Score (0-1)")
        axes[1].set_xlabel("Estrategia")
        axes[1].set_xticklabels(axes[1].get_xticklabels(), rotation=45, ha="right")
        axes[1].legend(["Faithfulness", "Answer Relevancy"], loc="lower right")
        axes[1].set_ylim(0, 1)
        axes[1].axhline(y=0.7, color='green', linestyle='--', alpha=0.3, label='Target (0.7)')
        
        plt.tight_layout()
        plt.savefig(output_dir / "retrieval_vs_generation.png", dpi=300)
        plt.close()
        print(f"  - retrieval_vs_generation.png")
        
        # 4. Matriz de Diagnóstico (Heatmap)
        plt.figure(figsize=(12, 8))
        
        all_metrics = self.df.groupby("strategy")[
            ["contextual_precision_score", "contextual_recall_score", "contextual_relevancy_score",
             "faithfulness_score", "answer_relevancy_score"]
        ].mean()
        
        # Renombrar columnas para mejor visualización
        all_metrics.columns = [
            "C. Precision", "C. Recall", "C. Relevancy",
            "Faithfulness", "A. Relevancy"
        ]
        
        sns.heatmap(
            all_metrics.T,
            annot=True,
            fmt=".3f",
            cmap="RdYlGn",
            vmin=0,
            vmax=1,
            center=0.7,
            cbar_kws={"label": "Score"},
            linewidths=0.5
        )
        plt.title("RAG Triad Diagnostic Matrix", fontsize=16, fontweight='bold', pad=20)
        plt.xlabel("Estrategia", fontsize=12)
        plt.ylabel("Métrica", fontsize=12)
        plt.tight_layout()
        plt.savefig(output_dir / "diagnostic_heatmap.png", dpi=300)
        plt.close()
        print(f"  - diagnostic_heatmap.png")
        
        # 5. Scatter Plot de Alucinación (Recall vs Faithfulness)
        plt.figure(figsize=(10, 8))
        
        hallucination_data = self.df.groupby("strategy").agg({
            "contextual_recall_score": "mean",
            "faithfulness_score": "mean"
        })
        
        plt.scatter(
            hallucination_data["contextual_recall_score"],
            hallucination_data["faithfulness_score"],
            s=300,
            alpha=0.6,
            c=range(len(hallucination_data)),
            cmap="viridis"
        )
        
        # Anotar estrategias
        for strategy, row in hallucination_data.iterrows():
            plt.annotate(
                strategy,
                (row["contextual_recall_score"], row["faithfulness_score"]),
                xytext=(5, 5),
                textcoords="offset points",
                fontsize=10,
                fontweight='bold'
            )
        
        # Línea diagonal ideal (Faithfulness >= Recall)
        plt.plot([0, 1], [0, 1], 'r--', alpha=0.4, linewidth=2, label="Ideal (no hallucination)")
        
        # Zonas de diagnóstico
        plt.axhline(y=0.7, color='green', linestyle=':', alpha=0.3)
        plt.axvline(x=0.7, color='green', linestyle=':', alpha=0.3)
        plt.text(0.75, 0.05, "High Recall\nLow Faithfulness\n⚠️ Hallucination!",
                 fontsize=9, bbox=dict(boxstyle='round', facecolor='red', alpha=0.2))
        plt.text(0.05, 0.75, "Low Recall\nHigh Faithfulness\n⚠️ Missing Info!",
                 fontsize=9, bbox=dict(boxstyle='round', facecolor='orange', alpha=0.2))
        
        plt.xlabel("Contextual Recall (Información disponible en contexto)", fontsize=11)
        plt.ylabel("Faithfulness (Información usada sin alucinar)", fontsize=11)
        plt.title("Hallucination Detection Analysis", fontsize=14, fontweight='bold')
        plt.legend(loc="lower right")
        plt.xlim(-0.05, 1.05)
        plt.ylim(-0.05, 1.05)
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(output_dir / "hallucination_analysis.png", dpi=300)
        plt.close()
        print(f"  - hallucination_analysis.png")
        
        # 6. Costo vs Calidad
        plt.figure(figsize=(10, 6))
        cost_quality = self.df.groupby("strategy").agg({
            "cost_usd": "sum",
            "overall_score": "mean"
        })
        
        plt.scatter(cost_quality["cost_usd"], cost_quality["overall_score"], s=300, alpha=0.6)
        for strategy, row in cost_quality.iterrows():
            plt.annotate(
                strategy,
                (row["cost_usd"], row["overall_score"]),
                xytext=(5, 5),
                textcoords="offset points",
                fontsize=10
            )
        
        plt.xlabel("Costo Total (USD)", fontsize=11)
        plt.ylabel("Overall Score (Promedio)", fontsize=11)
        plt.title("Costo vs Calidad General", fontsize=14, fontweight='bold')
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(output_dir / "cost_vs_quality.png", dpi=300)
        plt.close()
        print(f"  - cost_vs_quality.png")
        
        # 7. Latencia vs Calidad
        plt.figure(figsize=(10, 6))
        latency_quality = self.df.groupby("strategy").agg({
            "latency_ms": "mean",
            "overall_score": "mean"
        })
        
        plt.scatter(latency_quality["latency_ms"], latency_quality["overall_score"], s=300, alpha=0.6)
        for strategy, row in latency_quality.iterrows():
            plt.annotate(
                strategy,
                (row["latency_ms"], row["overall_score"]),
                xytext=(5, 5),
                textcoords="offset points",
                fontsize=10
            )
        
        plt.xlabel("Latencia Promedio (ms)", fontsize=11)
        plt.ylabel("Overall Score (Promedio)", fontsize=11)
        plt.title("Latencia vs Calidad General", fontsize=14, fontweight='bold')
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(output_dir / "latency_vs_quality.png", dpi=300)
        plt.close()
        print(f"  - latency_vs_quality.png")
        
        print(f"\n✓ Todas las visualizaciones generadas exitosamente")
    
    def export_to_csv(self, output_path: Path):
        """
        Exporta resultados a CSV.
        
        Args:
            output_path: Ruta del archivo CSV
        """
        self.df.to_csv(output_path, index=False)
        print(f"✓ Resultados exportados a: {output_path}")
    
    def generate_report(self, output_path: Path):
        """
        Genera reporte en formato Markdown con métricas DeepEval y análisis de fallos.
        
        Args:
            output_path: Ruta del archivo de reporte
        """
        report = []
        report.append("# Reporte de Evaluación RAG con DeepEval - Recetas Vegetarianas\n\n")
        report.append(f"**Fecha**: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        report.append(f"**Total de experimentos**: {len(self.results)}\n\n")
        report.append(f"**Estrategias evaluadas**: {self.df['strategy'].nunique()}\n\n")
        report.append(f"**Consultas de prueba**: {self.df['query'].nunique()}\n\n")
        
        report.append("---\n\n")
        report.append("## 🔍 RETRIEVAL METRICS\n\n")
        report.append("Evalúan la calidad del componente de recuperación (embeddings, reranking, etc.)\n\n")
        
        retrieval_summary = self.df.groupby("strategy")[
            ["contextual_precision_score", "contextual_recall_score", "contextual_relevancy_score"]
        ].mean().round(3)
        report.append(retrieval_summary.to_markdown())
        report.append("\n\n")
        
        # Diagnósticos retrieval
        report.append("### 💡 Diagnósticos Automáticos (Retrieval)\n\n")
        for strategy in retrieval_summary.index:
            precision = retrieval_summary.loc[strategy, "contextual_precision_score"]
            recall = retrieval_summary.loc[strategy, "contextual_recall_score"]
            relevancy = retrieval_summary.loc[strategy, "contextual_relevancy_score"]
            
            report.append(f"**{strategy}**:\n")
            if precision < 0.5:
                report.append(f"- ⚠️ Baja Precision ({precision:.3f}) → Revisar reranking\n")
            if recall < 0.6:
                report.append(f"- ⚠️ Bajo Recall ({recall:.3f}) → Aumentar top_k o mejorar embeddings\n")
            if relevancy < 0.6:
                report.append(f"- ⚠️ Baja Relevancy ({relevancy:.3f}) → Filtrar contenido irrelevante\n")
            if precision >= 0.7 and recall >= 0.7 and relevancy >= 0.7:
                report.append(f"- ✓ Retrieval en buen estado\n")
            report.append("\n")
        
        report.append("---\n\n")
        report.append("## 🤖 GENERATION METRICS\n\n")
        report.append("Evalúan la calidad del componente de generación (LLM, prompts, etc.)\n\n")
        
        generation_summary = self.df.groupby("strategy")[
            ["faithfulness_score", "answer_relevancy_score"]
        ].mean().round(3)
        report.append(generation_summary.to_markdown())
        report.append("\n\n")
        
        # Diagnósticos generation
        report.append("### 💡 Diagnósticos Automáticos (Generation)\n\n")
        for strategy in generation_summary.index:
            faithfulness = generation_summary.loc[strategy, "faithfulness_score"]
            relevancy = generation_summary.loc[strategy, "answer_relevancy_score"]
            
            report.append(f"**{strategy}**:\n")
            if faithfulness < 0.7:
                report.append(f"- ⚠️ Alta Alucinación ({faithfulness:.3f}) → Mejorar prompt o contexto\n")
            if relevancy < 0.6:
                report.append(f"- ⚠️ Baja Answer Relevancy ({relevancy:.3f}) → Revisar prompt del generador\n")
            if faithfulness >= 0.8 and relevancy >= 0.8:
                report.append(f"- ✓ Generation en buen estado\n")
            report.append("\n")
        
        # NUEVO: Análisis de Fallos con reasons de DeepEval
        report.append("---\n\n")
        report.append("## 🔍 ANÁLISIS DE FALLOS (DeepEval Reasons)\n\n")
        report.append("Ejemplos de explicaciones generadas por DeepEval para scores bajos:\n\n")
        
        # Obtener los 3 peores casos por cada métrica clave
        for metric in ['contextual_precision', 'contextual_recall', 'faithfulness']:
            score_col = f"{metric}_score"
            reason_col = f"{metric}_reason"
            
            worst_cases = self.df.nsmallest(3, score_col)[[
                'strategy', 'query', score_col, reason_col
            ]]
            
            if not worst_cases.empty:
                report.append(f"### {metric.replace('_', ' ').title()}\n\n")
                for idx, row in worst_cases.iterrows():
                    report.append(f"- **{row['strategy']}** (score: {row[score_col]:.3f})\n")
                    report.append(f"  - Query: _{row['query'][:100]}..._\n")
                    report.append(f"  - Reason: {row[reason_col]}\n\n")
        
        report.append("---\n\n")
        report.append("## 🏆 Rankings\n\n")
        
        report.append("### Por Calidad General (Overall Score)\n\n")
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
        
        report.append("\n---\n\n")
        report.append("## 📊 Métricas Generales\n\n")
        
        general_summary = self.df.groupby("strategy").agg({
            "latency_ms": ["mean", "std"],
            "total_tokens": ["mean", "sum"],
            "cost_usd": ["mean", "sum"],
            "overall_score": ["mean", "std"]
        }).round(3)
        report.append(general_summary.to_markdown())
        report.append("\n")
        
        # Guardar reporte
        with open(output_path, 'w', encoding='utf-8') as f:
            f.writelines(report)
        
        print(f"✓ Reporte generado en: {output_path}")
