import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate

# Load the API keys from our .env file
load_dotenv()

class InterviewerAgent:
    def __init__(self):
        # We check for the Groq Key before initializing
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key or api_key == "":
            raise ValueError("GROQ_API_KEY is missing from your .env file!")
            
        # Initialize the Groq chat model (using Llama 3.1)
        self.llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0.7)

    def generate_question(self, company: str, position: str, hiring_stories: str, chat_history: list) -> str:
        """
        Generates the next interview question based on the company, position,
        real internet hiring stories, and what has already been said in the chat.
        """
        system_instruction = (
            "You are an expert technical interviewer and hiring manager at {company} interviewing a candidate for a {position} role.\n\n"
            "YOUR SOURCE MATERIAL:\n"
            "Here are real-world interview experiences and questions scraped from the web for this company:\n"
            "\"\"\"\n{hiring_stories}\n\"\"\"\n\n"
            "YOUR RULES:\n"
            "1. Adopt the tone, strictness, and style of an interviewer at {company}.\n"
            "2. Use the provided source material to pull realistic questions, scenarios, or coding tasks.\n"
            "3. Stay in character completely. Do not say 'Based on the context provided...' or 'According to Reddit...'. Speak as if you thought of the question yourself.\n"
            "4. Ask exactly ONE clear question at a time. Wait for the user's response."
        )

        prompt_template = ChatPromptTemplate.from_messages([
            ("system", system_instruction),
            *chat_history 
        ])

        chain = prompt_template | self.llm
        response = chain.invoke({
            "company": company,
            "position": position,
            "hiring_stories": hiring_stories
        })

        return response.content

# --- Testing block ---
if __name__ == "__main__":
    from scraper import scrape_interview_data
    
    print("Initializing your AI Interviewer...")
    
    # 1. Fetch our data
    reddit_url = "https://www.levels.fyi/blog/amazon-leadership-principles.html"
    scraped_context = scrape_interview_data(reddit_url)
    
    if not scraped_context:
        print("Could not load context data. Aborting agent test.")
    else:
        # 2. Initialize our agent and an empty history list
        agent = InterviewerAgent()
        history = []
        
        print("\n" + "="*50)
        print("INTERVIEW STARTED. TYPE 'quit' TO EXIT.")
        print("="*50 + "\n")
        
        # 3. Start the back-and-forth chat loop
        while True:
            # The AI thinks of a question based on the history so far
            ai_response = agent.generate_question(
                company="Amazon",
                position="Software Development Engineer Intern",
                hiring_stories=scraped_context,
                chat_history=history
            )
            
            # Print the AI's question
            print(f"\n🤖 Interviewer: {ai_response}\n")
            
            # Save the AI's question to the history
            history.append(("assistant", ai_response))
            
            # Wait for YOU to type an answer in the terminal
            user_answer = input("🧑‍💻 You: ")
            
            if user_answer.lower() in ['quit', 'exit']:
                print("\nEnding interview. Great job!")
                break
                
            # Save your answer to the history
            history.append(("user", user_answer))