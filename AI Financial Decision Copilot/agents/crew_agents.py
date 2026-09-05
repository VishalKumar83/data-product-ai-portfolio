"""
agents/crew_agents.py
──────────────────────
Defines the three specialist agents in the financial RAG crew:

  1. RetrieverAgent  — Searches and fetches relevant 10-K passages
  2. AnalystAgent    — Interprets financial data, computes metrics, synthesizes insights
  3. ValidatorAgent  — Cross-checks claims against source material for accuracy

Each agent is backed by Ollama (LLaMA-3) running locally.
"""

from __future__ import annotations

import sys
from pathlib import Path

from crewai import Agent

sys.path.append(str(Path(__file__).parent.parent))
import config
from agents.tools import (
    FinancialCalculatorTool,
    FinancialRetrievalTool,
    FactValidationTool,
    SECFilingMetadataTool,
)

# ── Shared LLM config for CrewAI ──────────────────────────────────────────────
# CrewAI expects an LLM string in "provider/model" format for Ollama
CREW_LLM = f"ollama/{config.OLLAMA_MODEL}"


def build_retriever_agent() -> Agent:
    """
    RetrieverAgent: Expert at searching SEC filings.
    Knows how to craft effective queries, filter by ticker/section,
    and return the most relevant context passages.
    """
    return Agent(
        role="Senior Financial Research Retriever",
        goal=(
            "Retrieve the most relevant and accurate passages from SEC 10-K filings "
            "to answer financial questions. Focus on exact figures, dates, and sections. "
            "Always specify the ticker and date of each source."
        ),
        backstory=(
            "You are a veteran financial analyst with 15 years of experience reading "
            "SEC filings. You have an encyclopedic knowledge of 10-K structure: "
            "Part I (Business, Risk Factors), Part II (MDA, Financial Statements), "
            "and Notes to Financial Statements. You know exactly where to look for "
            "revenue figures, risk disclosures, segment breakdowns, and forward guidance."
        ),
        tools=[
            FinancialRetrievalTool(),
            SECFilingMetadataTool(),
        ],
        llm=CREW_LLM,
        verbose=config.VERBOSE_AGENTS,
        max_iter=config.MAX_ITERATIONS,
        allow_delegation=False,
    )


def build_analyst_agent() -> Agent:
    """
    AnalystAgent: Interprets and synthesizes financial data.
    Computes ratios, identifies trends, and produces structured analysis.
    """
    return Agent(
        role="Senior Financial Analyst",
        goal=(
            "Analyze retrieved financial data to produce accurate, insightful answers. "
            "Calculate growth rates, margins, and ratios when relevant. "
            "Structure responses with clear numerical evidence and year-over-year comparisons."
        ),
        backstory=(
            "You are a CFA charterholder with deep expertise in equity research and "
            "fundamental analysis. You have covered technology, finance, and energy sectors "
            "for top-tier investment banks. You excel at translating dense 10-K language "
            "into clear, actionable insights. You always show your calculations and cite "
            "specific line items from financial statements."
        ),
        tools=[
            FinancialRetrievalTool(),
            FinancialCalculatorTool(),
        ],
        llm=CREW_LLM,
        verbose=config.VERBOSE_AGENTS,
        max_iter=config.MAX_ITERATIONS,
        allow_delegation=False,
    )


def build_validator_agent() -> Agent:
    """
    ValidatorAgent: Fact-checks the Analyst's output against source documents.
    Flags hallucinations, unsupported claims, and numerical errors.
    """
    return Agent(
        role="Financial Compliance Validator",
        goal=(
            "Rigorously verify that all facts, figures, and claims in the analyst's "
            "response are directly supported by the retrieved SEC filing passages. "
            "Flag any hallucinated numbers, unsupported claims, or misattributions. "
            "Produce a final validated answer with confidence score."
        ),
        backstory=(
            "You are a financial auditor and compliance specialist with Big-4 experience. "
            "Your job is to ensure zero tolerance for inaccurate financial information. "
            "You compare claims against primary source documents line by line, "
            "verify all arithmetic, and ensure all cited figures match the original filings. "
            "You have caught countless errors in analyst reports over your career."
        ),
        tools=[
            FactValidationTool(),
            FinancialRetrievalTool(),
            FinancialCalculatorTool(),
        ],
        llm=CREW_LLM,
        verbose=config.VERBOSE_AGENTS,
        max_iter=config.MAX_ITERATIONS,
        allow_delegation=False,
    )
