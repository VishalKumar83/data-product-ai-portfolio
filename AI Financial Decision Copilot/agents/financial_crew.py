"""
agents/financial_crew.py
─────────────────────────
FinancialAnalysisCrew — the main orchestrator.
Assembles the three-agent pipeline and runs queries end-to-end.

Usage:
    from agents.financial_crew import FinancialAnalysisCrew

    crew = FinancialAnalysisCrew()
    result = crew.run("What was Apple's total revenue in fiscal year 2023?", ticker="AAPL")
    print(result.final_answer)
"""

from __future__ import annotations

import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

from crewai import Crew, Process
from loguru import logger

sys.path.append(str(Path(__file__).parent.parent))
import config
from agents.crew_tasks import build_tasks


@dataclass
class CrewResult:
    query: str
    final_answer: str
    ticker: str | None
    elapsed_seconds: float
    raw_output: str = ""
    error: str | None = None
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "query": self.query,
            "final_answer": self.final_answer,
            "ticker": self.ticker,
            "elapsed_seconds": round(self.elapsed_seconds, 2),
            "error": self.error,
            "metadata": self.metadata,
        }


class FinancialAnalysisCrew:
    """
    Orchestrates the Retriever → Analyst → Validator pipeline.
    Uses CrewAI's sequential process so each agent receives prior context.
    """

    def __init__(self):
        logger.info("FinancialAnalysisCrew initialized (sequential process)")
        self._validate_ollama()

    def _validate_ollama(self):
        """Warn early if Ollama is not running."""
        try:
            import ollama
            client = ollama.Client(host=config.OLLAMA_BASE_URL)
            models = client.list()
            model_names = [m["name"] for m in models.get("models", [])]
            if config.OLLAMA_MODEL not in model_names:
                logger.warning(
                    f"Model '{config.OLLAMA_MODEL}' not found in Ollama.\n"
                    f"Available models: {model_names}\n"
                    f"Pull it with: ollama pull {config.OLLAMA_MODEL}"
                )
        except Exception as e:
            logger.warning(f"Could not connect to Ollama: {e}")

    def run(
        self,
        query: str,
        ticker: str | None = None,
        verbose: bool | None = None,
    ) -> CrewResult:
        """
        Run the full three-agent pipeline on a query.

        Args:
            query: Natural language financial question
            ticker: Optional stock ticker to restrict retrieval
            verbose: Override verbosity (default: config.VERBOSE_AGENTS)

        Returns:
            CrewResult with final_answer and metadata
        """
        start = time.time()
        verbose = verbose if verbose is not None else config.VERBOSE_AGENTS
        logger.info(f"Running crew | query: '{query}' | ticker: {ticker}")

        try:
            tasks, agents = build_tasks(query, ticker)

            crew = Crew(
                agents=list(agents.values()),
                tasks=tasks,
                process=Process.sequential,
                verbose=verbose,
                max_rpm=10,   # Rate-limit LLM calls (useful for shared Ollama)
            )

            raw_output = crew.kickoff()
            elapsed = time.time() - start

            # The last task output is the validator's final answer
            final_answer = str(raw_output)

            logger.success(f"Crew completed in {elapsed:.1f}s")
            return CrewResult(
                query=query,
                final_answer=final_answer,
                ticker=ticker,
                elapsed_seconds=elapsed,
                raw_output=final_answer,
                metadata={
                    "model": config.OLLAMA_MODEL,
                    "retrieval_strategy": config.RETRIEVAL_STRATEGY,
                    "top_k": config.TOP_K_RETRIEVAL,
                },
            )

        except Exception as e:
            elapsed = time.time() - start
            logger.error(f"Crew failed after {elapsed:.1f}s: {e}")
            return CrewResult(
                query=query,
                final_answer=f"Error: {str(e)}",
                ticker=ticker,
                elapsed_seconds=elapsed,
                error=str(e),
            )

    def run_batch(self, queries: list[dict]) -> list[CrewResult]:
        """
        Run multiple queries. Each item: {"query": "...", "ticker": "..."}
        """
        results = []
        for i, item in enumerate(queries):
            logger.info(f"Batch query {i+1}/{len(queries)}: {item['query'][:60]}...")
            result = self.run(
                query=item["query"],
                ticker=item.get("ticker"),
            )
            results.append(result)
        return results


# ── CLI entrypoint ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run a single financial query through the crew")
    parser.add_argument("query", help="Financial question to answer")
    parser.add_argument("--ticker", "-t", default=None, help="Optional ticker filter e.g. AAPL")
    args = parser.parse_args()

    crew = FinancialAnalysisCrew()
    result = crew.run(args.query, ticker=args.ticker)
    print("\n" + "=" * 80)
    print("FINAL ANSWER")
    print("=" * 80)
    print(result.final_answer)
    print(f"\n[Completed in {result.elapsed_seconds:.1f}s]")
