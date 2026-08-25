import sqlite3

# This is the file where all your chat history will be saved locally
DB_NAME = "interview_memory.db"

def init_db():
    """Creates the database and the table if they don't exist yet."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # Create a table with 3 columns: ID, Role (user/assistant), and Content (the message)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT,
            content TEXT
        )
    ''')
    conn.commit()
    conn.close()

def save_message(role: str, content: str):
    """Saves a single message to the database."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO chat_history (role, content) VALUES (?, ?)', (role, content))
    conn.commit()
    conn.close()

def get_all_messages():
    """Retrieves the entire chat history in the format LangChain expects."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT role, content FROM chat_history ORDER BY id ASC')
    rows = cursor.fetchall()
    conn.close()
    
    # Formats the data like: [("user", "hello"), ("assistant", "hi!")]
    return [(row[0], row[1]) for row in rows]

def clear_history():
    """Wipes the memory clean (useful when starting a new interview)."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM chat_history')
    conn.commit()
    conn.close()