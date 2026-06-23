# Company Memory MVP Backend

A minimal FastAPI microservice that parses raw conversation transcripts (like Slack logs, Teams chat, email threads) and extracts structured tasks, owners, deadlines, and key decisions using a Large Language Model (Gemini or OpenAI).

---

## Repository Structure

```text
backend/
├── app/
│   ├── api/
│   │   └── routes.py       # API endpoints (e.g., POST /extract)
│   ├── core/
│   │   └── config.py       # Configuration and .env manager
│   ├── schemas/
│   │   └── models.py       # Pydantic request/response schemas
│   ├── services/
│   │   ├── extractor.py    # Prompts & parsing coordination logic
│   │   └── llm.py          # Abstract LLM client (Gemini and OpenAI)
│   └── main.py             # FastAPI entrypoint and health endpoints
├── .env.example            # Environment template file
├── requirements.txt        # PIP dependencies list
└── README.md               # Setup and usage guide (this file)
```

---

## Getting Started

### 1. Prerequisites
- Python 3.11+
- Virtual environment tool (`venv` or `conda`)

### 2. Setup
Clone or navigate to the directory containing the project:
```bash
# Navigate to the backend directory
cd backend

# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# On Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# On Windows (CMD):
.\venv\Scripts\activate.bat
# On macOS / Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configuration
Copy the sample environment file to `.env`:
```bash
cp .env.example .env
```
Open `.env` in a text editor and configure:
1. `LLM_PROVIDER`: Set to `gemini` (default) or `openai`.
2. Provide your API Key in the corresponding field:
   - `GEMINI_API_KEY=AIzaSy...`
   - or `OPENAI_API_KEY=sk-...`

---

## Running the Application

Start the FastAPI development server:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
The server will start on `http://localhost:8000`. You can access the interactive API docs at `http://localhost:8000/docs`.

---

## API Usage

### Extract Items Endpoint
- **URL**: `POST /extract`
- **Headers**: `Content-Type: application/json`

#### Example Curl Request
```bash
curl -X POST http://localhost:8000/extract \
  -H "Content-Type: application/json" \
  -d '{
    "messages": "John: Hey team, we need to finalize the landing page. Sarah, can you finish the hero design assets by Wednesday? Sarah: Sure, I will take care of it. John: Also, we decided to drop support for Internet Explorer starting next sprint because it accounts for less than 0.5% of our traffic. Dave, make sure we update the browser support policy doc."
  }'
```

#### Example Output Response
```json
{
  "tasks": [
    {
      "task": "Finish the hero design assets",
      "owner": "Sarah",
      "deadline": "Wednesday"
    },
    {
      "task": "Update the browser support policy doc",
      "owner": "Dave",
      "deadline": ""
    }
  ],
  "decisions": [
    {
      "decision": "Drop support for Internet Explorer starting next sprint",
      "context": "Internet Explorer accounts for less than 0.5% of overall traffic"
    }
  ]
}
```
