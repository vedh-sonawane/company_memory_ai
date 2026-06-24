import json
import hmac
import hashlib
import time
import logging
from fastapi import APIRouter, HTTPException, Depends, Request, BackgroundTasks, Query
from fastapi.responses import PlainTextResponse

import uuid
from typing import List
from app.schemas.models import ExtractionRequest, ExtractionResponse, TaskDatabaseModel, DecisionDatabaseModel, SearchResponse, QuestionRequest, QuestionResponse
from app.services.extractor import ExtractorService
from app.core.config import settings
from app.db.database import insert_task, insert_decision, fetch_all_tasks, fetch_all_decisions, search_tasks, search_decisions, fetch_recent_items, fetch_upcoming_deadlines

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

@router.post("/ask", response_model=QuestionResponse)
async def ask_question(payload: QuestionRequest, extractor: ExtractorService = Depends(get_extractor)):
    if not payload.question or not payload.question.strip():
        raise HTTPException(status_code=400, detail="Question field must not be empty.")
    
    try:
        # First, try to search for relevant items based on keywords in the question
        # Extract potential keywords (simple approach: split by spaces and remove common words)
        common_words = {"what", "who", "when", "where", "why", "how", "the", "and", "or", "is", "are", "was", "were"}
        keywords = [word for word in payload.question.lower().split() if word not in common_words and len(word) > 2]
        
        all_tasks = []
        all_decisions = []
        
        # If we have keywords, search for relevant items
        if keywords:
            for keyword in keywords:
                tasks = search_tasks(keyword)
                decisions = search_decisions(keyword)
                all_tasks.extend(tasks)
                all_decisions.extend(decisions)
        else:
            # If no keywords, get all items
            all_tasks = fetch_all_tasks()
            all_decisions = fetch_all_decisions()
        
        # Remove duplicates while preserving order
        seen_tasks = set()
        unique_tasks = []
        for task in all_tasks:
            if task['id'] not in seen_tasks:
                seen_tasks.add(task['id'])
                unique_tasks.append(task)
        
        seen_decisions = set()
        unique_decisions = []
        for decision in all_decisions:
            if decision['id'] not in seen_decisions:
                seen_decisions.add(decision['id'])
                unique_decisions.append(decision)
        
        # Special handling for specific question types
        if "deadline" in payload.question.lower() or "deadlines" in payload.question.lower():
            unique_tasks = fetch_upcoming_deadlines()
        elif "week" in payload.question.lower() or "recent" in payload.question.lower():
            recent_items = fetch_recent_items()
            unique_tasks = recent_items["tasks"]
            unique_decisions = recent_items["decisions"]
        
        # If we have relevant items, use them to generate an answer
        if unique_tasks or unique_decisions:
            # Prepare context for the LLM
            context_parts = []
            
            if unique_tasks:
                context_parts.append("TASKS:")
                for task in unique_tasks[:10]:  # Limit to 10 tasks to avoid context overflow
                    task_info = f"- Task: {task['task']}"
                    if task['owner']:
                        task_info += f" | Owner: {task['owner']}"
                    if task['deadline']:
                        task_info += f" | Deadline: {task['deadline']}"
                    if task['timestamp']:
                        task_info += f" | Date: {task['timestamp']}"
                    context_parts.append(task_info)
            
            if unique_decisions:
                context_parts.append("\nDECISIONS:")
                for decision in unique_decisions[:10]:  # Limit to 10 decisions
                    decision_info = f"- Decision: {decision['decision']}"
                    if decision['context']:
                        decision_info += f" | Context: {decision['context']}"
                    if decision['timestamp']:
                        decision_info += f" | Date: {decision['timestamp']}"
                    context_parts.append(decision_info)
            
            context = "\n".join(context_parts)
            
            # Create prompt for LLM
            prompt = f"""
You are an AI assistant that answers questions about company knowledge based on stored tasks and decisions.

CONTEXT:
{context}

QUESTION:
{payload.question}

INSTRUCTIONS:
- Answer the question using ONLY the information provided in the context above
- Be concise and direct
- If the context doesn't contain enough information to answer the question, respond with: "I could not find enough information to answer that question."
- Include a "Sources" section that lists the relevant items from the context that support your answer
- Format your response as follows:

Answer:
[Your answer here]

Sources:
- [Source 1]
- [Source 2]
...

EXAMPLE:
Answer:
The team decided to use Stripe for credit card processing.

Sources:
- Decision: Use Stripe for credit cards | Context: Because of their easy API | Date: 2026-06-23
"""
            
            # Generate response using LLM
            try:
                llm_response = extractor.llm_service.generate(prompt, str)
                if isinstance(llm_response, str):
                    answer_text = llm_response
                elif hasattr(llm_response, 'text'):
                    answer_text = llm_response.text
                else:
                    answer_text = str(llm_response)
                
                # Extract sources from the answer (simple parsing)
                lines = answer_text.split('\n')
                sources = []
                in_sources = False
                for line in lines:
                    if line.startswith("Sources:"):
                        in_sources = True
                        continue
                    if in_sources and line.startswith("- "):
                        sources.append(line[2:])  # Remove "- " prefix
                    elif in_sources and not line.strip():
                        break  # Stop at first empty line after sources
                
                # If we couldn't parse sources, create them from the context
                if not sources:
                    for task in unique_tasks[:3]:  # Limit to 3 sources
                        source = f"Task: {task['task']}"
                        if task['timestamp']:
                            source += f" | Date: {task['timestamp']}"
                        sources.append(source)
                    for decision in unique_decisions[:3]:  # Limit to 3 sources
                        source = f"Decision: {decision['decision']}"
                        if decision['timestamp']:
                            source += f" | Date: {decision['timestamp']}"
                        sources.append(source)
                
                return QuestionResponse(answer=answer_text, sources=sources)
            except Exception as e:
                logger.error(f"Error generating answer with LLM: {e}")
                # Fallback response
                answer = "I could not find enough information to answer that question."
                sources = []
                for task in unique_tasks[:3]:
                    source = f"Task: {task['task']}"
                    if task['timestamp']:
                        source += f" | Date: {task['timestamp']}"
                    sources.append(source)
                for decision in unique_decisions[:3]:
                    source = f"Decision: {decision['decision']}"
                    if decision['timestamp']:
                        source += f" | Date: {decision['timestamp']}"
                    sources.append(source)
                return QuestionResponse(answer=answer, sources=sources)
        else:
            # No relevant items found
            return QuestionResponse(
                answer="I could not find enough information to answer that question.",
                sources=[]
            )
            
    except Exception as e:
        logger.error(f"Error processing question: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to process question: {str(e)}"
        )
