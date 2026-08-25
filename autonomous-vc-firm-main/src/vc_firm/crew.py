from crewai import Agent, Crew, Process, Task, LLM
from crewai.tools import tool

# --- OUR CUSTOM VC TOOLS ---

@tool("Competitor Database")
def competitor_database_tool(search_query: str) -> str:
    """Search for competitors in a specific industry or product category."""
    return "DATABASE RESULT: Highly saturated market. Legacy players own the space. Hard to acquire new users."

@tool("Tech Stack Analyzer")
def tech_analyzer_tool(tech_claim: str) -> str:
    """Analyze a startup's claimed technology to see if it is realistic or just buzzwords."""
    return "ANALYSIS: The claimed technology is highly improbable. Combining blockchain and quantum computing for this use-case makes no architectural sense. High risk of vaporware."

@tool("Web Sentiment Tool")
def sentiment_tool(company_name: str) -> str:
    """Scan Reddit, Twitter, and HackerNews for public sentiment about the startup."""
    return "SENTIMENT: Massive viral hype on TikTok, but 90% of comments are bots or memes. Zero actual buyer intent. Industry experts on HackerNews are calling it a scam."

# Point CrewAI directly to your laptop's local Ollama instance
local_llm = LLM(
    model="ollama/llama3.2",
    base_url="http://localhost:11434"
)

class VcFirmCrew():
    """Ultimate 7-Agent VC Firm"""

    # --- THE AGENTS ---

    def financial_parser(self) -> Agent:
        return Agent(
            role="Principal Financial Auditor",
            goal="Extract exact financial metrics from the startup's pitch data.",
            backstory="You are a meticulous auditor. You find burn rates, valuations, and asks without making assumptions.",
            verbose=True,
            llm=local_llm
        )

    def market_researcher(self) -> Agent:
        return Agent(
            role="Market Research Analyst",
            goal="Find out if the startup's core product has too much competition.",
            backstory="You ALWAYS use your 'Competitor Database' tool to check market saturation.",
            verbose=True,
            llm=local_llm,
            tools=[competitor_database_tool]
        )

    def tech_engineer(self) -> Agent:
        return Agent(
            role="Technical Due Diligence Engineer",
            goal="Evaluate if the startup's technology is real or fake.",
            backstory="You are a cynical ex-Google engineer. You ALWAYS use your 'Tech Stack Analyzer' tool to call out fake tech buzzwords.",
            verbose=True,
            llm=local_llm,
            tools=[tech_analyzer_tool]
        )

    def social_analyst(self) -> Agent:
        return Agent(
            role="Social Traction Analyst",
            goal="Measure real public demand vs fake internet hype.",
            backstory="You are a marketing expert. You ALWAYS use your 'Web Sentiment Tool' to see if people actually want to buy this product.",
            verbose=True,
            llm=local_llm,
            tools=[sentiment_tool]
        )

    def risk_assessor(self) -> Agent:
        return Agent(
            role="Risk Assessment Director",
            goal="Compile financials, market, tech, and social data to flag massive risks.",
            backstory="You are a highly skeptical VC risk analyst. You synthesize everyone's reports into a brutal list of red flags.",
            verbose=True,
            llm=local_llm
        )

    def investment_writer(self) -> Agent:
        return Agent(
            role="Investment Committee Memo Writer",
            goal="Draft a formal executive memo based on the massive amount of compiled data.",
            backstory="You write concise, Wall-Street-grade investment memos summarizing all due diligence.",
            verbose=True,
            llm=local_llm
        )

    def managing_partner(self) -> Agent:
        return Agent(
            role="Managing Partner",
            goal="Read the final memo and make a definitive YES or NO investment decision.",
            backstory="You run the VC firm. You are ruthless. You read the memo and output a final verdict of either 'YES: Take a Meeting' or 'NO: Hard Pass', followed by a one-sentence justification.",
            verbose=True,
            llm=local_llm
        )

    # --- THE TASKS ---

    def extraction_task(self) -> Task:
        return Task(description="Extract the Valuation, Ask, and Core Product from: {pitch_data}", expected_output="Bulleted list of metrics.", agent=self.financial_parser())

    def research_task(self) -> Task:
        return Task(description="Use the Competitor Database tool on the extracted core product.", expected_output="Competition summary.", agent=self.market_researcher())

    def tech_task(self) -> Task:
        return Task(description="Use the Tech Stack Analyzer tool on the startup's tech claims.", expected_output="Tech feasibility report.", agent=self.tech_engineer())

    def social_task(self) -> Task:
        return Task(description="Use the Web Sentiment Tool on the startup's name.", expected_output="Public traction report.", agent=self.social_analyst())

    def risk_task(self) -> Task:
        return Task(description="Review the extracted data, competition, tech, and social reports. Identify major red flags.", expected_output="Paragraph of top risks.", agent=self.risk_assessor())

    def writing_task(self) -> Task:
        return Task(
            description="Using all previous findings, write a formal 4-paragraph investment memo.", 
            expected_output="Markdown memo detailing Financials, Market, Tech, Social, and Risks.", 
            agent=self.investment_writer(),
            output_file='due_diligence_report.md'  # <--- SAVES DETAILED REPORT
        )

    def decision_task(self) -> Task:
        return Task(
            description="Read the drafted memo. Decide if we should invest. Give a final YES or NO and a one-sentence reason.", 
            expected_output="A final verdict.", 
            agent=self.managing_partner(),
            output_file='partner_verdict.md'  # <--- SAVES MANAGING PARTNER VERDICT
        )

    # --- THE FINAL ASSEMBLY ---
    def crew(self) -> Crew:
        return Crew(
            agents=[self.financial_parser(), self.market_researcher(), self.tech_engineer(), self.social_analyst(), self.risk_assessor(), self.investment_writer(), self.managing_partner()],
            tasks=[self.extraction_task(), self.research_task(), self.tech_task(), self.social_task(), self.risk_task(), self.writing_task(), self.decision_task()],
            process=Process.sequential,
            verbose=True,
        )