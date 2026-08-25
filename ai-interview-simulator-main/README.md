# 💼 Universal AI Interview Simulator

A full-stack, AI-powered interview simulator that dynamically adapts to any company and job role. 

Unlike standard static chatbots, this application utilizes **Retrieval-Augmented Generation (RAG)** to scrape real-time company culture blogs, interview guides, and job descriptions from the web. It then forces an LLM to adopt the persona of a hiring manager for that specific context, creating a highly realistic and customized interview experience.

## 🚀 Features
* **Dynamic Context Loading:** Paste any URL (job description, company wiki) and the system scrapes and ingests the data on the fly.
* **Persistent Memory:** Utilizes an SQLite database to maintain conversation history and state across sessions.
* **Persona Engineering:** The AI is strictly prompted to act as an evaluator, asking one question at a time and reacting naturally to candidate responses.
* **Modern UI:** A clean, responsive chat interface built with Tailwind CSS.

## 🛠️ Tech Stack
* **Backend:** Python, FastAPI, Uvicorn
* **AI & Data:** Groq API (LLaMA 3), Firecrawl API (Web Scraping), LangChain components
* **Database:** SQLite
* **Frontend:** HTML5, Vanilla JavaScript, Tailwind CSS

## ⚙️ Local Setup
1. Clone the repository.
2. Install the required Python packages: `pip install fastapi uvicorn groq firecrawl-py pydantic`
3. Create a `.env` file in the root directory and add your API keys:
   ```env
GROQ_API_KEY=your_groq_api_key_here
FIRECRAWL_API_KEY=your_firecrawl_api_key_here