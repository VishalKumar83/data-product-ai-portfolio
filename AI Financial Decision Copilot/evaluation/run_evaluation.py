"""
evaluation/run_evaluation.py
─────────────────────────────
Evaluates the RAG pipeline using RAGAS metrics:
  - Faithfulness       (are answers grounded in retrieved context?)
  - Answer Relevancy   (does the answer address the question?)
  - Context Precision  (is retrieved context relevant?)
  - Context Recall     (is all needed info retrieved?)

Usage:
    python evaluation/run_evaluation.py
    python evaluation/run_evaluation.py --questions 20  # run subset
    python evaluation/run_evaluation.py --strategy faiss  # test single retriever
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from loguru import logger
from tqdm import tqdm

import config

# ── 50-Question Financial QA Benchmark ────────────────────────────────────────
# These are representative questions about SEC 10-K content.
# Ground truth answers are approximate; RAGAS uses LLM-as-judge scoring.

QA_BENCHMARK = [
    # Revenue & Financials
    {"question": "What was Apple's total net sales for fiscal year 2023?",
     "ground_truth": "Apple's total net sales for fiscal year 2023 were $383.3 billion.",
     "ticker": "AAPL"},
    {"question": "What were Apple's product revenues vs service revenues in FY2023?",
     "ground_truth": "Apple product revenue was approximately $298 billion and services revenue was approximately $85 billion.",
     "ticker": "AAPL"},
    {"question": "What was Microsoft's total revenue in fiscal year 2023?",
     "ground_truth": "Microsoft total revenue for fiscal year 2023 was approximately $211.9 billion.",
     "ticker": "MSFT"},
    {"question": "What was NVIDIA's revenue growth rate in FY2024?",
     "ground_truth": "NVIDIA's revenue grew significantly driven by AI/data center demand.",
     "ticker": "NVDA"},
    {"question": "What was Amazon's net product sales vs service sales in 2023?",
     "ground_truth": "Amazon reported net product sales and net service sales as separate line items in their income statement.",
     "ticker": "AMZN"},
    {"question": "What was Google's advertising revenue in 2023?",
     "ground_truth": "Alphabet's Google advertising revenues were a significant portion of total revenues.",
     "ticker": "GOOGL"},
    {"question": "What was Meta's total revenue in 2023?",
     "ground_truth": "Meta's total revenue in 2023 was approximately $134.9 billion.",
     "ticker": "META"},
    {"question": "What was Tesla's total revenue in 2023?",
     "ground_truth": "Tesla's total revenues were approximately $96.8 billion in 2023.",
     "ticker": "TSLA"},
    {"question": "What was JPMorgan's net income in 2023?",
     "ground_truth": "JPMorgan reported net income of approximately $49.6 billion in 2023.",
     "ticker": "JPM"},
    {"question": "What were Johnson & Johnson's sales by segment in 2023?",
     "ground_truth": "Johnson & Johnson reports MedTech and Innovative Medicine segments.",
     "ticker": "JNJ"},
    # Operating Metrics
    {"question": "What was Apple's gross margin in fiscal year 2023?",
     "ground_truth": "Apple's gross margin was approximately 44.1% in FY2023.",
     "ticker": "AAPL"},
    {"question": "What was Microsoft's operating income in FY2023?",
     "ground_truth": "Microsoft's operating income for FY2023 was approximately $88.5 billion.",
     "ticker": "MSFT"},
    {"question": "What was NVIDIA's data center revenue in FY2024?",
     "ground_truth": "NVIDIA's Data Center segment revenue grew substantially driven by AI chip demand.",
     "ticker": "NVDA"},
    {"question": "What was Amazon's AWS revenue in 2023?",
     "ground_truth": "Amazon Web Services revenue was approximately $90.8 billion in 2023.",
     "ticker": "AMZN"},
    {"question": "What was Google Cloud revenue in 2023?",
     "ground_truth": "Google Cloud revenue reached approximately $33 billion in 2023.",
     "ticker": "GOOGL"},
    # Risk Factors
    {"question": "What are Apple's main risk factors related to supply chain?",
     "ground_truth": "Apple discloses risks including concentration of manufacturing in Asia, dependence on sole-source suppliers, and geopolitical risks.",
     "ticker": "AAPL"},
    {"question": "What cybersecurity risks does Microsoft disclose in its 10-K?",
     "ground_truth": "Microsoft discloses cybersecurity threats, data breaches, and nation-state attacks as significant risk factors.",
     "ticker": "MSFT"},
    {"question": "What are NVIDIA's key risk factors related to AI chip demand?",
     "ground_truth": "NVIDIA discloses risks including customer concentration, export controls, and rapidly changing technology.",
     "ticker": "NVDA"},
    {"question": "What regulatory risks does Meta disclose?",
     "ground_truth": "Meta discloses risks related to data privacy regulations, antitrust actions, and content moderation requirements.",
     "ticker": "META"},
    {"question": "What are Tesla's main manufacturing risk factors?",
     "ground_truth": "Tesla discloses risks including production ramp challenges, supplier dependencies, and quality control issues.",
     "ticker": "TSLA"},
    # Capital & Cash Flow
    {"question": "How much cash and equivalents did Apple hold at end of FY2023?",
     "ground_truth": "Apple held approximately $162 billion in cash, cash equivalents, and marketable securities.",
     "ticker": "AAPL"},
    {"question": "What was Apple's share buyback amount in FY2023?",
     "ground_truth": "Apple repurchased approximately $77.6 billion of common stock in FY2023.",
     "ticker": "AAPL"},
    {"question": "What was Microsoft's capital expenditure in FY2023?",
     "ground_truth": "Microsoft's capital expenditures were approximately $28 billion in FY2023.",
     "ticker": "MSFT"},
    {"question": "What was Amazon's free cash flow in 2023?",
     "ground_truth": "Amazon reported positive free cash flow in 2023 after several years of investment.",
     "ticker": "AMZN"},
    {"question": "What was NVIDIA's R&D spending as a percent of revenue?",
     "ground_truth": "NVIDIA's R&D expenses represented a significant portion of revenue reflecting their technology investment.",
     "ticker": "NVDA"},
    # Business Description
    {"question": "What are Apple's reportable operating segments?",
     "ground_truth": "Apple operates as a single reportable segment.",
     "ticker": "AAPL"},
    {"question": "What cloud services does Microsoft offer as described in their 10-K?",
     "ground_truth": "Microsoft offers Azure, Microsoft 365, Dynamics 365, and other cloud services.",
     "ticker": "MSFT"},
    {"question": "What are Amazon's three main business segments?",
     "ground_truth": "Amazon's segments are North America, International, and Amazon Web Services.",
     "ticker": "AMZN"},
    {"question": "What are Google's main business segments?",
     "ground_truth": "Alphabet's segments include Google Services, Google Cloud, and Other Bets.",
     "ticker": "GOOGL"},
    {"question": "What vehicle models does Tesla sell?",
     "ground_truth": "Tesla sells Model S, Model 3, Model X, Model Y, Cybertruck, and Semi.",
     "ticker": "TSLA"},
    # Employees & Operations
    {"question": "How many employees did Apple have at end of FY2023?",
     "ground_truth": "Apple had approximately 161,000 full-time equivalent employees.",
     "ticker": "AAPL"},
    {"question": "How many employees did Microsoft have in FY2023?",
     "ground_truth": "Microsoft had approximately 221,000 full-time employees.",
     "ticker": "MSFT"},
    {"question": "How many data centers does Microsoft operate?",
     "ground_truth": "Microsoft operates data centers across multiple regions globally.",
     "ticker": "MSFT"},
    {"question": "What countries does Apple manufacture products in?",
     "ground_truth": "Apple primarily manufactures in China through contract manufacturers, with some production in India.",
     "ticker": "AAPL"},
    {"question": "How many warehouses and fulfillment centers does Amazon operate?",
     "ground_truth": "Amazon operates hundreds of fulfillment centers across North America and internationally.",
     "ticker": "AMZN"},
    # Debt & Liabilities
    {"question": "What is Apple's total long-term debt as of FY2023?",
     "ground_truth": "Apple's long-term debt was approximately $95.3 billion.",
     "ticker": "AAPL"},
    {"question": "What is Microsoft's credit rating and long-term debt?",
     "ground_truth": "Microsoft has a AAA credit rating and carries long-term debt.",
     "ticker": "MSFT"},
    {"question": "What was Tesla's total debt in 2023?",
     "ground_truth": "Tesla significantly reduced its debt levels over recent years.",
     "ticker": "TSLA"},
    # ESG & Governance
    {"question": "What are Apple's climate-related commitments disclosed in the 10-K?",
     "ground_truth": "Apple has committed to carbon neutrality across its supply chain by 2030.",
     "ticker": "AAPL"},
    {"question": "What diversity and inclusion disclosures does Microsoft make?",
     "ground_truth": "Microsoft discloses employee diversity statistics and inclusion initiatives.",
     "ticker": "MSFT"},
    # Recent Developments
    {"question": "What acquisitions did Microsoft complete in FY2023?",
     "ground_truth": "Microsoft completed the Activision Blizzard acquisition.",
     "ticker": "MSFT"},
    {"question": "What new products did NVIDIA launch related to AI in FY2024?",
     "ground_truth": "NVIDIA launched H100 and related Hopper architecture GPUs for AI workloads.",
     "ticker": "NVDA"},
    {"question": "What AI investments does Google disclose in their 2023 10-K?",
     "ground_truth": "Alphabet discloses investments in AI across Search, Cloud, DeepMind, and other products.",
     "ticker": "GOOGL"},
    {"question": "What was Meta's Reality Labs revenue and loss in 2023?",
     "ground_truth": "Meta's Reality Labs segment reported operating losses of approximately $16 billion.",
     "ticker": "META"},
    # Geographic Revenue
    {"question": "What percentage of Apple's revenue comes from China?",
     "ground_truth": "Apple's Greater China segment represented approximately 19% of total revenue.",
     "ticker": "AAPL"},
    {"question": "What is Microsoft's US vs international revenue split?",
     "ground_truth": "Microsoft generates revenue from both US and international markets.",
     "ticker": "MSFT"},
    {"question": "What is Amazon's international segment revenue?",
     "ground_truth": "Amazon's International segment reported revenues of approximately $131.2 billion in 2023.",
     "ticker": "AMZN"},
    # Comparisons
    {"question": "How did Apple's iPhone revenue change from 2022 to 2023?",
     "ground_truth": "iPhone revenue was relatively flat from FY2022 to FY2023.",
     "ticker": "AAPL"},
    {"question": "How did NVIDIA's gaming revenue change in FY2024?",
     "ground_truth": "NVIDIA gaming revenue declined before recovering.",
     "ticker": "NVDA"},
    {"question": "How did Tesla's vehicle delivery growth rate change in 2023?",
     "ground_truth": "Tesla delivered approximately 1.8 million vehicles in 2023, a significant increase.",
     "ticker": "TSLA"},
    {"question": "What was the year-over-year change in Meta's operating income in 2023?",
     "ground_truth": "Meta's operating income improved significantly in 2023 compared to 2022.",
     "ticker": "META"},
]


def evaluate_with_ragas(results: list[dict]) -> dict:
    """Run RAGAS evaluation on query results."""
    try:
        from datasets import Dataset
        from ragas import evaluate
        from ragas.metrics import (
            answer_relevancy,
            context_precision,
            context_recall,
            faithfulness,
        )

        # Build RAGAS dataset
        ragas_data = {
            "question": [r["question"] for r in results],
            "answer": [r["answer"] for r in results],
            "contexts": [r["contexts"] for r in results],
            "ground_truth": [r["ground_truth"] for r in results],
        }
        dataset = Dataset.from_dict(ragas_data)

        logger.info("Running RAGAS evaluation...")
        ragas_result = evaluate(
            dataset=dataset,
            metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
        )

        return {
            "faithfulness": float(ragas_result["faithfulness"]),
            "answer_relevancy": float(ragas_result["answer_relevancy"]),
            "context_precision": float(ragas_result["context_precision"]),
            "context_recall": float(ragas_result["context_recall"]),
        }
    except Exception as e:
        logger.error(f"RAGAS evaluation failed: {e}")
        return {"error": str(e)}


def run_evaluation(n_questions: int = 50, strategy: str = "hybrid") -> dict:
    from agents.financial_crew import FinancialAnalysisCrew
    from rag.retriever import HybridRetriever

    questions = QA_BENCHMARK[:n_questions]
    logger.info(f"Running evaluation on {len(questions)} questions | strategy: {strategy}")

    crew = FinancialAnalysisCrew()
    retriever = HybridRetriever()

    results = []
    for i, item in enumerate(tqdm(questions, desc="Evaluating")):
        try:
            # Get answer from crew
            crew_result = crew.run(item["question"], ticker=item.get("ticker"))

            # Also get raw retrieved contexts for RAGAS
            docs = retriever.retrieve(
                item["question"],
                top_k=config.TOP_K_RETRIEVAL,
                filter_ticker=item.get("ticker"),
                strategy=strategy,
            )
            contexts = [d.text for d in docs]

            results.append({
                "question": item["question"],
                "answer": crew_result.final_answer,
                "ground_truth": item["ground_truth"],
                "contexts": contexts,
                "ticker": item.get("ticker"),
                "elapsed": crew_result.elapsed_seconds,
                "error": crew_result.error,
            })

            logger.info(f"  [{i+1}/{len(questions)}] ✓ {item['question'][:60]}...")

        except Exception as e:
            logger.error(f"  [{i+1}/{len(questions)}] ✗ Failed: {e}")
            results.append({
                "question": item["question"],
                "answer": f"ERROR: {e}",
                "ground_truth": item["ground_truth"],
                "contexts": [],
                "ticker": item.get("ticker"),
                "elapsed": 0,
                "error": str(e),
            })

        time.sleep(0.5)  # Small delay between queries

    # Run RAGAS scoring
    valid_results = [r for r in results if not r.get("error")]
    aggregate_metrics = {}
    if valid_results:
        aggregate_metrics = evaluate_with_ragas(valid_results)

    # Build final report
    report = {
        "run_timestamp": datetime.now().isoformat(),
        "config": {
            "n_questions": n_questions,
            "strategy": strategy,
            "model": config.OLLAMA_MODEL,
            "top_k": config.TOP_K_RETRIEVAL,
        },
        "summary": {
            "total": len(results),
            "successful": len(valid_results),
            "failed": len(results) - len(valid_results),
            "avg_elapsed_seconds": sum(r["elapsed"] for r in results) / max(len(results), 1),
        },
        "aggregate_metrics": aggregate_metrics,
        "results": results,
    }

    # Save report
    output_dir = Path(config.RAGAS_OUTPUT_PATH)
    output_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_file = output_dir / f"eval_{ts}.json"
    out_file.write_text(json.dumps(report, indent=2))
    logger.success(f"Evaluation report saved → {out_file}")

    # Print summary
    print("\n" + "=" * 60)
    print("EVALUATION SUMMARY")
    print("=" * 60)
    print(f"Questions: {report['summary']['total']} | Successful: {report['summary']['successful']}")
    print(f"Avg response time: {report['summary']['avg_elapsed_seconds']:.1f}s")
    if aggregate_metrics and "error" not in aggregate_metrics:
        print("\nRAGAS Metrics:")
        for k, v in aggregate_metrics.items():
            bar = "█" * int(v * 20)
            print(f"  {k:<25} {v:.3f}  {bar}")
    print("=" * 60)

    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--questions", "-n", type=int, default=50, help="Number of questions to evaluate")
    parser.add_argument("--strategy", default="hybrid", choices=["faiss", "chroma", "hybrid"])
    args = parser.parse_args()
    run_evaluation(n_questions=args.questions, strategy=args.strategy)
