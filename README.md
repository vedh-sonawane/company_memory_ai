# company_memory_ai

A service that extracts structured tasks and decisions from conversational text using AI.

## Project Structure

```text
.
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── routes.py       # API endpoints
│   │   ├── core/
│   │   │   └── config.py       # Configuration
│   │   ├── db/
│   │   │   └── database.py     # Database operations
│   │   ├── schemas/
│   │   │   └── models.py       # Data models
│   │   ├── services/
│   │   │   ├── extractor.py    # Extraction logic
│   │   │   └── llm.py          # LLM providers
│   │   └── main.py             # FastAPI app
│   ├── static/                 # Frontend files
│   │   ├── index.html
│   │   ├── style.css
│   │   └── script.js
│   ├── .env.example
│   ├── requirements.txt
│   └── README.md
├── .gitignore
└── README.md (this file)
```

## Getting Started

### Prerequisites
- Python 3.8+
- Virtual environment tool (`venv`)
- An API key for either Google Gemini or OpenAI

### Setup

1. **Navigate to the backend directory:**
   ```bash
   cd backend
   ```

2. **Create and activate a virtual environment:**
   ```bash
   # On Windows
   python -m venv venv
   .\venv\Scripts\activate
   
   # On macOS/Linux
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables:**
   ```bash
   cp .env.example .env
   ```
   Then edit the `.env` file to add your API key:
   - For Gemini: Set `LLM_PROVIDER=gemini` and add your `GEMINI_API_KEY=your_key_here`
   - For OpenAI: Set `LLM_PROVIDER=openai` and add your `OPENAI_API_KEY=your_key_here`

### Running the Application

1. **Start the server:**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

2. **Access the application:**
   - API Documentation: http://localhost:8000/docs
   - Dashboard: http://localhost:8000/

### Testing the Application

1. **Send a test request via curl:**
   ```bash
   curl -X POST http://localhost:8000/extract \
     -H "Content-Type: application/json" \
     -d '{"messages": "John: Hey team, we need to finalize the landing page. Sarah, can you finish the hero design assets by Wednesday? Sarah: Sure, I will take care of it. John: Also, we decided to drop support for Internet Explorer starting next sprint because it accounts for less than 0.5% of our traffic. Dave, make sure we update the browser support policy doc."}'
   ```

2. **View stored data:**
   - Tasks: http://localhost:8000/tasks
   - Decisions: http://localhost:8000/decisions

3. **Use the dashboard:**
   - Open http://localhost:8000/ in your browser
   - The dashboard will show all stored tasks and decisions
   - Use the search bar to find specific items
   - Ask questions using the "Ask About Company Memory" section

### Slack Integration (Optional)
To enable Slack integration:
1. Set up a Slack bot and obtain your `SLACK_BOT_TOKEN` and `SLACK_SIGNING_SECRET`
2. Add these to your `.env` file
3. Expose your local server to the internet using a tunneling service like ngrok
4. Configure your Slack app's event subscription URL to point to your server

### Features
- Extract tasks and decisions from conversation text
- Store information in SQLite database
- Search stored information
- Ask natural language questions about company knowledge
- Web dashboard for viewing all stored information
- Slack integration for automatic processing of messages
