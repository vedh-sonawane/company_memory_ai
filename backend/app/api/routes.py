import json
import hmac
import hashlib
import time
import logging
from fastapi import APIRouter, HTTPException, Depends, Request, BackgroundTasks, Query
from fastapi.responses import PlainTextResponse

import uuid
from typing import List
from app.schemas.models import ExtractionRequest, ExtractionResponse, TaskDatabaseModel, DecisionDatabaseModel, SearchResponse
from app.services.extractor import ExtractorService
from app.core.config import settings
from app.db.database import insert_task, insert_decision, fetch_all_tasks, fetch_all_decisions, search_tasks, search_decisions

logger = logging.getLogger(__name__)
router = APIRouter()

def get_extractor():
    return ExtractorService()

# -----------------
# Slack Helper Functions
# -----------------
def verify_slack_signature(body: bytes, timestamp: str, signature: str) -> bool:
    secret = settings.SLACK_SIGNING_SECRET.strip()
    if not secret or "your-slack" in secret:
        logger.warning("SLACK_SIGNING_SECRET is not configured or is a placeholder. Skipping request signature validation.")
        return True
    
    if not timestamp or not signature:
        return False
    
    # Check for replay attacks (5 minute threshold)
    if abs(time.time() - int(timestamp)) > 300:
        return False
    
    sig_basestring = f"v0:{timestamp}:".encode("utf-8") + body
    computed_signature = "v0=" + hmac.new(
        settings.SLACK_SIGNING_SECRET.encode("utf-8"),
        sig_basestring,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(computed_signature, signature)

def process_slack_event(payload: dict):
    event = payload.get("event", {})
    event_type = event.get("type")
    
    if event_type == "message":
        # Ignore bot messages and updates to avoid loops/unneeded LLM costs
        subtype = event.get("subtype")
        if subtype or event.get("bot_id"):
            return
            
        user = event.get("user")
        channel = event.get("channel")
        text = event.get("text")
        ts = event.get("ts")
        
        if not text or not text.strip():
            return
            
        logger.info("\n" + "=" * 50)
        logger.info("SLACK MESSAGE EVENT RECEIVED")
        logger.info(f"Channel:   {channel}")
        logger.info(f"User:      {user}")
        logger.info(f"Timestamp: {ts}")
        logger.info(f"Message:   {text}")
        logger.info("=" * 50 + "\n")
        
        try:
            extractor = ExtractorService()
            if not extractor.llm_service:
                logger.error("LLM Provider is not initialized. Please verify your GEMINI_API_KEY/OPENAI_API_KEY settings.")
                return
            
            result = extractor.extract_from_text(text)
            
            logger.info("\n" + "*" * 50)
            logger.info("STRUCTURED EXTRACTION RESULTS (LOGGED TO CONSOLE)")
            logger.info(f"Source Text: '{text}'")
            logger.info(f"Tasks:       {result.tasks}")
            logger.info(f"Decisions:   {result.decisions}")
            logger.info("*" * 50 + "\n")
            
            # Persist Extracted Tasks to Database
            for task in result.tasks:
                task_id = str(uuid.uuid4())
                insert_task({
                    "id": task_id,
                    "task": task.task,
                    "owner": task.owner,
                    "deadline": task.deadline,
                    "source_message": text,
                    "channel_id": channel,
                    "slack_user_id": user,
                    "timestamp": ts
                })
                logger.info(f"Saved task {task_id} successfully to SQLite.")
                
            # Persist Extracted Decisions to Database
            for decision in result.decisions:
                decision_id = str(uuid.uuid4())
                insert_decision({
                    "id": decision_id,
                    "decision": decision.decision,
                    "context": decision.context,
                    "source_message": text,
                    "channel_id": channel,
                    "slack_user_id": user,
                    "timestamp": ts
                })
                logger.info(f"Saved decision {decision_id} successfully to SQLite.")
            
        except Exception as e:
            logger.error(f"Error processing Slack event extraction: {e}", exc_info=True)

# -----------------
# Routes
# -----------------
@router.post("/extract", response_model=ExtractionResponse)
async def extract_items(
    payload: ExtractionRequest, 
    extractor: ExtractorService = Depends(get_extractor)
):
    if not payload.messages or not payload.messages.strip():
        raise HTTPException(status_code=400, detail="Input field 'messages' must not be empty.")
    
    try:
        result = extractor.extract_from_text(payload.messages)
        return result
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to process extraction request: {str(e)}"
        )

@router.post("/slack/events")
async def slack_events(request: Request, background_tasks: BackgroundTasks):
    body_bytes = await request.body()
    
    # Verify signature
    timestamp = request.headers.get("X-Slack-Request-Timestamp", "")
    signature = request.headers.get("X-Slack-Signature", "")
    if not verify_slack_signature(body_bytes, timestamp, signature):
        logger.warning("Slack signature validation failed.")
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    # Parse payload
    try:
        payload = json.loads(body_bytes.decode("utf-8"))
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON body")
    
    # 1. Handle Slack verification challenge
    if payload.get("type") == "url_verification":
        challenge = payload.get("challenge")
        if not challenge:
            raise HTTPException(status_code=400, detail="Challenge key missing in payload")
        return PlainTextResponse(content=challenge)
    
    # 2. Handle Event callbacks asynchronously
    if payload.get("type") == "event_callback":
        background_tasks.add_task(process_slack_event, payload)
        return {"status": "ok"}
        
    return {"status": "ignored"}

@router.get("/tasks", response_model=List[TaskDatabaseModel])
async def get_tasks():
    try:
        tasks = fetch_all_tasks()
        return tasks
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to fetch tasks from database: {str(e)}"
        )

@router.get("/decisions", response_model=List[DecisionDatabaseModel])
async def get_decisions():
    try:
        decisions = fetch_all_decisions()
        return decisions
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to fetch decisions from database: {str(e)}"
        )

@router.get("/search", response_model=SearchResponse)
async def search_items(q: str = Query(..., min_length=1)):
    try:
        tasks = search_tasks(q)
        decisions = search_decisions(q)
        return SearchResponse(tasks=tasks, decisions=decisions)
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to search items in database: {str(e)}"
        )
