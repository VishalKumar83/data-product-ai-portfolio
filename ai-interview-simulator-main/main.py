from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel
from agent import InterviewerAgent
from scraper import scrape_interview_data

# Import your new database functions!
from database import init_db, save_message, get_all_messages, clear_history

app = FastAPI(title="Dynamic AI Interview Agent API")

# Initialize the database file as soon as the server starts
init_db()

# Initialize our agent
agent = InterviewerAgent()

# We still cache the context so we don't spam the web scraper
current_url = ""
cached_context = ""

class UserRequest(BaseModel):
    message: str
    company: str
    position: str
    url: str

@app.post("/api/chat")
async def chat_with_agent(user_data: UserRequest):
    global current_url, cached_context
    
    # 1. Check if the user changed the URL (New Interview)
    if user_data.url != current_url:
        print(f"Detecting new context URL. Scraping: {user_data.url}...")
        fresh_scrape = scrape_interview_data(user_data.url)
        
        if fresh_scrape:
            cached_context = fresh_scrape
            current_url = user_data.url
            # WIPE the database memory because we are starting a brand new interview
            clear_history()
            print("Successfully updated interview context material!")
        else:
            if not cached_context:
                cached_context = "No structural background data available."
    
    # 2. SAVE the user's message to the database
    save_message("user", user_data.message)
    
    # 3. LOAD the entire conversation history from the database
    chat_history = get_all_messages()
    
    # 4. Generate AI response
    ai_response = agent.generate_question(
        company=user_data.company,
        position=user_data.position,
        hiring_stories=cached_context,
        chat_history=chat_history
    )
    
    # 5. SAVE the AI's response to the database
    save_message("assistant", ai_response)
    
    return {"reply": ai_response}

@app.get("/")
async def root():
    return FileResponse("index.html")