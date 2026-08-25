#  Autonomous VC Firm (7-Agent AI System)

An autonomous multi-agent Venture Capital firm built to conduct automated due diligence on startup pitches. Powered by completely local, private LLMs.

##  The Architecture
This system utilizes a sequential pipeline of 7 specialized AI agents, each with distinct roles and custom-built Python tools:

1. **Financial Auditor:** Extracts burn rates, valuation, and funding asks.
2. **Market Researcher:** Uses a custom `Competitor Database` tool to check market saturation.
3. **Technical Due Diligence Engineer:** Uses a `Tech Stack Analyzer` to evaluate feasibility and flag vaporware.
4. **Social Traction Analyst:** Uses a `Web Sentiment Tool` to measure real public demand vs. bot hype.
5. **Risk Assessment Director:** Synthesizes reports to flag critical investment risks.
6. **Investment Memo Writer:** Drafts a formal, comprehensive due diligence report.
7. **Managing Partner:** Reviews the final memo and issues a definitive YES/NO investment verdict.

##  Tech Stack
* **Framework:** CrewAI, Streamlit
* **Language:** Python
* **Models:** Llama 3.2 (running 100% locally via Ollama)

##  Running it Locally
1. Clone the repository.
2. Install dependencies: `pip install crewai streamlit`
3. Ensure Ollama is running locally with Llama 3.2.
4. Launch the web app: `python -m streamlit run app.py`