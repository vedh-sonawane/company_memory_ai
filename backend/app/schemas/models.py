from pydantic import BaseModel, Field
from typing import List

class TaskItem(BaseModel):
    task: str = Field(..., description="The task description or action item.")
    owner: str = Field(default="", description="The owner/assignee of the task. Empty if unknown.")
    deadline: str = Field(default="", description="The deadline for the task. Empty if unknown.")

class DecisionItem(BaseModel):
    decision: str = Field(..., description="The decision that was made.")
    context: str = Field(default="", description="The context, rationale, or details behind the decision. Empty if unknown.")

class ExtractionRequest(BaseModel):
    messages: str = Field(..., description="Raw text of the conversation / chat messages.")

class ExtractionResponse(BaseModel):
    tasks: List[TaskItem] = Field(default_factory=list, description="List of tasks extracted from the conversation.")
    decisions: List[DecisionItem] = Field(default_factory=list, description="List of decisions extracted from the conversation.")

class TaskDatabaseModel(BaseModel):
    id: str
    task: str
    owner: str = ""
    deadline: str = ""
    source_message: str = ""
    channel_id: str = ""
    slack_user_id: str = ""
    timestamp: str = ""
    created_at: str = ""

class DecisionDatabaseModel(BaseModel):
    id: str
    decision: str
    context: str = ""
    source_message: str = ""
    channel_id: str = ""
    slack_user_id: str = ""
    timestamp: str = ""
    created_at: str = ""

class SearchResponse(BaseModel):
    tasks: List[TaskDatabaseModel] = Field(default_factory=list)
    decisions: List[DecisionDatabaseModel] = Field(default_factory=list)
