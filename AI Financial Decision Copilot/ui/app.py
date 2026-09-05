"""
ui/app.py
──────────
Streamlit frontend for the Agentic Financial RAG System.

Features:
  - Ask financial questions with optional ticker filter
  - See agent reasoning steps (expandable)
  - View retrieved source passages
  - Compare multiple tickers side-by-side
  - Evaluation dashboard tab

Run:
    streamlit run ui/app.py
"""

import sys
import time
from pathlib import Path

import requests
import streamlit as st

sys.path.append(str(Path(__file__).parent.parent))
import config

# ── Page config ────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Financial RAG System",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

API_URL = f"http://localhost:{config.API_PORT}"

# ── Styling ────────────────────────────────────────────────────────────────────

st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1a1a2e;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1rem;
        color: #555;
        margin-bottom: 2rem;
    }
    .answer-box {
        background: #f8f9ff;
        border-left: 4px solid #4361ee;
        padding: 1.2rem;
        border-radius: 0 8px 8px 0;
        font-size: 0.95rem;
        line-height: 1.7;
    }
    .source-card {
        background: #fff;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 0.8rem;
        margin-bottom: 0.5rem;
        font-size: 0.85rem;
    }
    .metric-badge {
        display: inline-block;
        padding: 0.2rem 0.6rem;
        border-radius: 999px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    .verified { background: #d1fae5; color: #065f46; }
    .score { background: #dbeafe; color: #1e40af; }
    .stButton > button {
        background-color: #4361ee;
        color: white;
        border-radius: 8px;
        border: none;
        padding: 0.5rem 2rem;
        font-weight: 600;
    }
    .stButton > button:hover { background-color: #3451d1; }
</style>
""", unsafe_allow_html=True)

# ── Sidebar ────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## ⚙️ Configuration")

    # Health check
    with st.expander("🔌 System Health", expanded=True):
        if st.button("Check Status"):
            try:
                resp = requests.get(f"{API_URL}/health", timeout=10)
                health = resp.json()
                st.success(f"**Status:** {health['status']}")
                st.write(f"🦙 **Ollama:** {health['ollama']}")
                st.write(f"🔍 **FAISS:** {health['faiss']}")
                st.write(f"🧠 **ChromaDB:** {health['chromadb']}")
                st.write(f"🤖 **Model:** {health['model']}")
            except Exception as e:
                st.error(f"API unreachable: {e}\nStart with: `uvicorn api.main:app`")

    st.markdown("---")

    # Retrieval settings
    st.markdown("### 🔍 Retrieval Settings")
    retrieval_strategy = st.selectbox(
        "Strategy", ["hybrid", "faiss", "chroma"], index=0
    )
    top_k = st.slider("Documents to retrieve", 3, 15, 5)

    st.markdown("---")

    # Available tickers
    st.markdown("### 📂 Indexed Filings")
    if st.button("Load Filings"):
        try:
            resp = requests.get(f"{API_URL}/filings", timeout=10)
            data = resp.json()
            if data.get("indexed"):
                st.write(f"**Chunks:** {data['total_chunks']:,}")
                for ticker, dates in data["filings"].items():
                    st.write(f"**{ticker}:** {', '.join(dates)}")
            else:
                st.warning(data.get("message", "Not indexed"))
        except Exception as e:
            st.error(f"Failed: {e}")

    st.markdown("---")
    st.markdown("### 🚀 Quick Start")
    st.code("""
# 1. Start Ollama
ollama serve
ollama pull llama3:8b
ollama pull nomic-embed-text

# 2. Download & ingest data
python scripts/download_sec_filings.py
python scripts/ingest_documents.py

# 3. Start API
uvicorn api.main:app

# 4. Start UI (this app)
streamlit run ui/app.py
    """, language="bash")


# ── Main content ───────────────────────────────────────────────────────────────

st.markdown('<p class="main-header">📊 Agentic Financial RAG</p>', unsafe_allow_html=True)
st.markdown(
    '<p class="sub-header">Multi-agent analysis over SEC 10-K filings · '
    'Powered by CrewAI + LLaMA-3 + FAISS + ChromaDB</p>',
    unsafe_allow_html=True,
)

# ── Tabs ───────────────────────────────────────────────────────────────────────

tab_query, tab_retrieve, tab_compare, tab_eval = st.tabs([
    "💬 Ask a Question",
    "🔍 Raw Retrieval",
    "⚖️ Compare Tickers",
    "📈 Evaluation",
])

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TAB 1: Ask a Question
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

with tab_query:
    col1, col2 = st.columns([3, 1])

    with col1:
        query = st.text_area(
            "Your financial question",
            placeholder="e.g. What were Apple's main revenue segments in FY2023? How did they change YoY?",
            height=100,
            key="main_query",
        )

    with col2:
        ticker = st.text_input("Ticker (optional)", placeholder="AAPL", key="main_ticker")
        ticker = ticker.upper().strip() if ticker else None
        run_btn = st.button("🚀 Run Analysis", key="run_main", use_container_width=True)

    # Sample questions
    st.markdown("**💡 Sample questions:**")
    sample_qs = [
        "What were Apple's total revenues and net income in FY2023?",
        "What are the main risk factors disclosed by NVIDIA in their 2023 10-K?",
        "How did Microsoft's cloud revenue grow from 2022 to 2023?",
        "What is Amazon's operating income breakdown by segment?",
    ]
    cols = st.columns(2)
    for i, q in enumerate(sample_qs):
        if cols[i % 2].button(q, key=f"sample_{i}"):
            st.session_state["main_query"] = q
            st.rerun()

    if run_btn and query:
        with st.spinner("🤖 Agents working... (Retriever → Analyst → Validator)"):
            start = time.time()
            try:
                resp = requests.post(
                    f"{API_URL}/query",
                    json={"query": query, "ticker": ticker, "verbose": False},
                    timeout=300,
                )
                result = resp.json()
                elapsed = time.time() - start

                if result.get("error"):
                    st.error(f"**Error:** {result['error']}")
                else:
                    st.success(f"✅ Completed in {result['elapsed_seconds']:.1f}s")

                    st.markdown("### 📋 Analysis Result")
                    st.markdown(
                        f'<div class="answer-box">{result["final_answer"].replace(chr(10), "<br>")}</div>',
                        unsafe_allow_html=True,
                    )

                    with st.expander("📊 Query Metadata"):
                        meta = result.get("metadata", {})
                        c1, c2, c3 = st.columns(3)
                        c1.metric("Model", meta.get("model", "N/A"))
                        c2.metric("Strategy", meta.get("retrieval_strategy", "N/A"))
                        c3.metric("Top-K", meta.get("top_k", "N/A"))

            except requests.exceptions.ConnectionError:
                st.error(
                    "❌ Cannot connect to the API.\n\n"
                    "Start it with: `uvicorn api.main:app --host 0.0.0.0 --port 8000`"
                )
            except Exception as e:
                st.error(f"Unexpected error: {e}")

    elif run_btn:
        st.warning("Please enter a question first.")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TAB 2: Raw Retrieval (debug view)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

with tab_retrieve:
    st.markdown("### 🔍 Raw Vector Search")
    st.markdown("Retrieve document chunks directly without agent reasoning — useful for debugging.")

    r_query = st.text_input("Search query", placeholder="Apple revenue 2023", key="r_query")
    r_col1, r_col2, r_col3 = st.columns(3)
    r_ticker = r_col1.text_input("Ticker filter", placeholder="AAPL", key="r_ticker")
    r_topk = r_col2.slider("Top K", 1, 20, 5, key="r_topk")
    r_strat = r_col3.selectbox("Strategy", ["hybrid", "faiss", "chroma"], key="r_strat")

    if st.button("🔍 Search", key="r_search"):
        if r_query:
            try:
                resp = requests.post(
                    f"{API_URL}/retrieve",
                    json={
                        "query": r_query,
                        "ticker": r_ticker.upper() or None,
                        "top_k": r_topk,
                        "strategy": r_strat,
                    },
                    timeout=60,
                )
                data = resp.json()
                st.success(f"Found {data['num_results']} documents using **{data['strategy']}** strategy")

                for i, doc in enumerate(data["documents"], 1):
                    meta = doc["metadata"]
                    with st.expander(
                        f"[{i}] {meta.get('ticker','?')} | {meta.get('filing_date','?')} | "
                        f"{meta.get('section','?')} | score: {doc['score']:.4f}"
                    ):
                        st.markdown(f'<div class="source-card">{doc["text"]}</div>', unsafe_allow_html=True)
                        st.json(meta)
            except Exception as e:
                st.error(f"Search failed: {e}")
        else:
            st.warning("Enter a search query.")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TAB 3: Compare Tickers
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

with tab_compare:
    st.markdown("### ⚖️ Side-by-Side Ticker Comparison")
    st.markdown("Ask the same question about two companies simultaneously.")

    cmp_query = st.text_area(
        "Comparison question",
        placeholder="Compare revenue growth rates between the two companies",
        height=80,
    )
    c1, c2 = st.columns(2)
    ticker_a = c1.text_input("Company A ticker", placeholder="AAPL")
    ticker_b = c2.text_input("Company B ticker", placeholder="MSFT")

    if st.button("⚖️ Compare", key="compare_btn"):
        if cmp_query and ticker_a and ticker_b:
            col_a, col_b = st.columns(2)

            with col_a:
                st.markdown(f"#### 🏢 {ticker_a.upper()}")
                with st.spinner(f"Analyzing {ticker_a.upper()}..."):
                    try:
                        resp = requests.post(
                            f"{API_URL}/query",
                            json={"query": cmp_query, "ticker": ticker_a.upper()},
                            timeout=300,
                        )
                        result = resp.json()
                        st.markdown(
                            f'<div class="answer-box">{result["final_answer"].replace(chr(10), "<br>")}</div>',
                            unsafe_allow_html=True,
                        )
                        st.caption(f"⏱ {result['elapsed_seconds']:.1f}s")
                    except Exception as e:
                        st.error(str(e))

            with col_b:
                st.markdown(f"#### 🏢 {ticker_b.upper()}")
                with st.spinner(f"Analyzing {ticker_b.upper()}..."):
                    try:
                        resp = requests.post(
                            f"{API_URL}/query",
                            json={"query": cmp_query, "ticker": ticker_b.upper()},
                            timeout=300,
                        )
                        result = resp.json()
                        st.markdown(
                            f'<div class="answer-box">{result["final_answer"].replace(chr(10), "<br>")}</div>',
                            unsafe_allow_html=True,
                        )
                        st.caption(f"⏱ {result['elapsed_seconds']:.1f}s")
                    except Exception as e:
                        st.error(str(e))
        else:
            st.warning("Fill in the question and both tickers.")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TAB 4: Evaluation Dashboard
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

with tab_eval:
    st.markdown("### 📈 RAGAS Evaluation Results")
    st.markdown(
        "Run the evaluation benchmark from the terminal to populate this dashboard:\n"
        "```bash\npython evaluation/run_evaluation.py\n```"
    )

    results_dir = Path(config.RAGAS_OUTPUT_PATH)
    result_files = sorted(results_dir.glob("*.json")) if results_dir.exists() else []

    if not result_files:
        st.info("No evaluation results found yet. Run the evaluation script first.")
    else:
        import json
        import pandas as pd

        selected_file = st.selectbox(
            "Select evaluation run",
            options=[f.name for f in result_files],
        )
        data = json.loads((results_dir / selected_file).read_text())

        metrics = data.get("aggregate_metrics", {})
        if metrics:
            st.markdown("#### 📊 Aggregate Metrics")
            cols = st.columns(len(metrics))
            for i, (k, v) in enumerate(metrics.items()):
                cols[i].metric(k.replace("_", " ").title(), f"{v:.3f}")

        if "results" in data:
            st.markdown("#### 📋 Per-Question Results")
            df = pd.DataFrame(data["results"])
            st.dataframe(df, use_container_width=True)
