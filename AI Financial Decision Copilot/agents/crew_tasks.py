"""
agents/crew_tasks.py
─────────────────────
Defines the three tasks that form the crew's pipeline for each query:

  Task 1: Retrieval    → Fetch relevant 10-K passages
  Task 2: Analysis     → Synthesize and compute insights
  Task 3: Validation   → Verify accuracy and produce final answer
"""

from __future__ import annotations

from crewai import Task

from agents.crew_agents import (
    build_analyst_agent,
    build_retriever_agent,
    build_validator_agent,
)


def build_tasks(query: str, ticker: str | None = None) -> tuple[list[Task], dict]:
    """
    Build the three-task pipeline for a given query.

    Returns:
        tasks: Ordered list of Task objects for the Crew
        agents: Dict of agent instances (for reuse)
    """
    retriever = build_retriever_agent()
    analyst = build_analyst_agent()
    validator = build_validator_agent()

    ticker_context = f" Focus on {ticker.upper()} filings." if ticker else ""

    # ── Task 1: Retrieval ──────────────────────────────────────────────────────
    retrieval_task = Task(
        description=(
            f"Search the SEC 10-K knowledge base to find the most relevant passages "
            f"for the following question:\n\n'{query}'\n\n"
            f"{ticker_context}"
            f"Use the financial_retrieval tool with the hybrid strategy. "
            f"Try multiple query variations if needed to capture all relevant data "
            f"(e.g., search for revenue, then 'net sales', then 'total revenue'). "
            f"Return all retrieved passages with their source metadata (ticker, date, section)."
        ),
        expected_output=(
            "A comprehensive set of verbatim passages from 10-K filings that are relevant "
            "to the query. Each passage must include: ticker, filing date, section name, "
            "and the full text. Include at least 3-5 distinct passages."
        ),
        agent=retriever,
    )

    # ── Task 2: Analysis ───────────────────────────────────────────────────────
    analysis_task = Task(
        description=(
            f"Using the retrieved 10-K passages from the previous task, "
            f"answer the following question with a thorough financial analysis:\n\n"
            f"'{query}'\n\n"
            f"Requirements:\n"
            f"1. Extract all relevant numerical figures with units and periods\n"
            f"2. Calculate growth rates, margins, or ratios if relevant using the calculator tool\n"
            f"3. Compare across years or companies if data is available\n"
            f"4. Identify key trends or risk factors mentioned\n"
            f"5. Structure the response: Summary → Key Figures → Analysis → Conclusion\n"
            f"6. Cite specific sections (e.g., 'AAPL 2023 10-K, Item 8') for every claim"
        ),
        expected_output=(
            "A structured financial analysis with:\n"
            "- Executive summary (2-3 sentences)\n"
            "- Key numerical findings with sources\n"
            "- Calculated metrics (growth %, margins, ratios) shown step-by-step\n"
            "- Trend analysis or comparison if applicable\n"
            "- Clear conclusion answering the original question\n"
            "All figures must be traceable to the retrieved source passages."
        ),
        agent=analyst,
        context=[retrieval_task],
    )

    # ── Task 3: Validation ─────────────────────────────────────────────────────
    validation_task = Task(
        description=(
            f"Review the analyst's response to the question: '{query}'\n\n"
            f"Your job is to:\n"
            f"1. Use the fact_validation tool to check each key numerical claim\n"
            f"2. Verify all arithmetic calculations are correct\n"
            f"3. Confirm every figure is traceable to the source 10-K passages\n"
            f"4. Flag any statements that are not directly supported (mark as [UNVERIFIED])\n"
            f"5. Correct any errors found\n"
            f"6. Add a Validation Summary at the end with:\n"
            f"   - Overall confidence score (0-100%)\n"
            f"   - Number of claims verified vs unverified\n"
            f"   - Any corrections made"
        ),
        expected_output=(
            "The final validated answer including:\n"
            "- The full analyst response with [VERIFIED] or [UNVERIFIED] tags on key claims\n"
            "- Any corrections in [CORRECTION: ...] brackets\n"
            "- A Validation Summary section with confidence score\n"
            "- Source citations confirmed against original passages"
        ),
        agent=validator,
        context=[retrieval_task, analysis_task],
    )

    tasks = [retrieval_task, analysis_task, validation_task]
    agents = {"retriever": retriever, "analyst": analyst, "validator": validator}
    return tasks, agents
