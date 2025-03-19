from typing import Dict, Any, List
import json
import uuid
import traceback
from datetime import datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel
from loguru import logger
from motor.motor_asyncio import AsyncIOMotorClient

from ..settings import get_settings
from ..utils.vector_store import VectorStore
from ..utils.llm import GroqLLM

settings = get_settings()

router = APIRouter()

# Initialize services
vector_store = VectorStore()
llm = GroqLLM()

class ChatMessage(BaseModel):
    """Chat message model."""
    role: str
    content: str
    timestamp: datetime = None
    feedback: Dict[str, Any] = {
        "thumbs": None,  # "up" or "down"
        "comment": None,  # Optional feedback comment
        "submitted_at": None  # Timestamp when feedback was submitted
    }

    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary with ISO formatted timestamp."""
        data = self.model_dump()
        if self.timestamp:
            data["timestamp"] = self.timestamp.isoformat()
        if self.feedback and self.feedback.get("submitted_at"):
            data["feedback"]["submitted_at"] = self.feedback["submitted_at"].isoformat()
        return data

class ConversationResponse(BaseModel):
    """Response model for conversation operations."""
    id: str
    title: str
    metadata: Dict[str, Any] = {}
    created_at: datetime
    updated_at: datetime = None
    message_count: int = 0
    last_message: ChatMessage | None = None

class Conversation(BaseModel):
    """Conversation model."""
    id: str
    title: str
    messages: List[ChatMessage]
    metadata: Dict[str, Any] = {}
    created_at: datetime = None
    updated_at: datetime = None

class ConnectionManager:
    """Manages WebSocket connections."""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.mongo_client = AsyncIOMotorClient(settings.MONGODB_URL)
        self.db = self.mongo_client[settings.MONGODB_DB_NAME]
    
    async def connect(self, websocket: WebSocket, conversation_id: str):
        """Connect a new client."""
        # Verify conversation exists
        conversation = await self.get_conversation_history(conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
            
        await websocket.accept()
        self.active_connections[conversation_id] = websocket
        logger.info(f"Client connected to conversation {conversation_id}")
    
    def disconnect(self, conversation_id: str):
        """Disconnect a client."""
        if conversation_id in self.active_connections:
            del self.active_connections[conversation_id]
            logger.info(f"Client disconnected from conversation {conversation_id}")
    
    async def send_message(self, conversation_id: str, message: ChatMessage):
        """Send a message to a specific client."""
        if conversation_id in self.active_connections:
            websocket = self.active_connections[conversation_id]
            await websocket.send_json(message.to_dict())
    
    async def get_conversation_history(self, conversation_id: str) -> Conversation:
        """Get conversation history from MongoDB."""
        conversation = await self.db.conversations.find_one({"id": conversation_id})
        if conversation:
            return Conversation(**conversation)
        return None
    
    async def save_message(self, conversation_id: str, message: ChatMessage):
        """Save a message to conversation history."""
        now = datetime.utcnow()
        message.timestamp = now
        
        # Update or create conversation
        await self.db.conversations.update_one(
            {"id": conversation_id},
            {
                "$push": {"messages": message.to_dict()},
                "$set": {"updated_at": now},
                "$setOnInsert": {
                    "id": conversation_id,
                    "created_at": now,
                    "metadata": {}
                }
            },
            upsert=True
        )
    
    async def update_title(self, conversation_id: str, title: str):
        """Update conversation title."""
        await self.db.conversations.update_one(
            {"id": conversation_id},
            {"$set": {"title": title}}
        )
        logger.info(f"Updated title for conversation {conversation_id}: {title}")

# Initialize connection manager
manager = ConnectionManager()

class ChatRequest(BaseModel):
    """Chat request model."""
    message: str

class ChatResponse(BaseModel):
    """Chat response model."""
    role: str
    content: str
    timestamp: datetime = None

class FeedbackRequest(BaseModel):
    """Feedback request model."""
    thumbs: str  # "up" or "down"
    comment: str | None = None

@router.put("/conversation", response_model=ConversationResponse)
async def create_conversation():
    """Create a new conversation with temporary title."""
    conversation_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    # Use a temporary title that will be updated with the first message
    title = "New Conversation"
    
    # System metadata
    metadata = {
        "created_by": "system",
        "created_at_timestamp": now.timestamp(),
        "source": "api",
        "title_generated": False  # Flag to track if title has been generated
    }
    
    conversation_data = {
        "id": conversation_id,
        "title": title,
        "metadata": metadata,
        "messages": [],
        "created_at": now,
        "updated_at": now
    }
    
    await manager.db.conversations.insert_one(conversation_data)
    logger.info(f"Created conversation {conversation_id}")
    
    return ConversationResponse(
        id=conversation_id,
        title=title,
        metadata=metadata,
        created_at=now,
        updated_at=now,
        message_count=0
    )

@router.get("/conversations", response_model=List[ConversationResponse])
async def list_conversations(skip: int = 0, limit: int = 10):
    """List all conversations."""
    conversations = []
    cursor = manager.db.conversations.find().sort("updated_at", -1).skip(skip).limit(limit)
    
    async for conv in cursor:
        last_message = None
        messages = conv.get("messages", [])
        if messages:
            last_message = ChatMessage(**messages[-1])
        conversations.append(ConversationResponse(
            id=conv["id"],
            title=conv.get("title", "New Conversation"),
            metadata=conv.get("metadata", {}),
            created_at=conv["created_at"],
            updated_at=conv.get("updated_at"),
            message_count=len(messages),
            last_message=last_message
        ))
    
    return conversations

@router.get("/conversations/{conversation_id}", response_model=Conversation)
async def get_conversation(conversation_id: str):
    """Get a specific conversation."""
    conversation = await manager.get_conversation_history(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation

@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """Delete a conversation."""
    result = await manager.db.conversations.delete_one({"id": conversation_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Disconnect any active WebSocket connections
    manager.disconnect(conversation_id)
    return {"status": "success", "message": "Conversation deleted"}

async def generate_title(message: str) -> str:
    """Generate a concise title from the first message using LLM."""
    try:
        system_prompt = """You are a helpful assistant that generates concise conversation titles. 
        Create a brief, descriptive title (maximum 6 words) based on the user's first message.
        The title should capture the main topic or intent. Respond with ONLY the title, no other text."""
        
        response = await llm.chat_completion(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Generate a title for this conversation that starts with: {message}"}
            ],
            temperature=settings.TEMPERATURE,
            max_tokens=25
        )
        
        # Clean up the response
        title = response.strip("'").strip('"').strip()
        return title
        
    except Exception as e:
        traceback.print_exc()
        logger.error(f"Error generating title: {str(e)}")
        return "New Conversation"  # Fallback title

@router.websocket("/ws/{conversation_id}")
async def chat_websocket(websocket: WebSocket, conversation_id: str):
    """WebSocket endpoint for chat."""
    try:
        await manager.connect(websocket, conversation_id)
        
        # Load conversation history
        logger.info("Retrieve Conv. History")
        conversation = await manager.get_conversation_history(conversation_id)

        # NOTE: Buat apa?
        # if conversation:
        #     for message in conversation.messages:
        #         await manager.save_message(conversation_id, message)
        
        while True:

            # Receive message from client
            data = await websocket.receive_json()
            user_message = ChatMessage(
                role="user",
                content=data["message"]
            )
            
            # Save user message
            await manager.save_message(conversation_id, user_message)
            
            try:
                # Generate title if this is the first message
                logger.info("Generate Title...")
                if not conversation or (not conversation.messages and not conversation.metadata.get("title_generated")):
                    title = await generate_title(user_message.content)
                    await manager.update_title(conversation_id, title)
                    await manager.db.conversations.update_one(
                        {"id": conversation_id},
                        {"$set": {"metadata.title_generated": True}}
                    )
                
                # Get relevant context from vector store
                logger.info("Retrieve Relevant Context...")
                context = await vector_store.similarity_search(
                    query=user_message.content,
                    k=settings.TOP_K
                )
                
                # Determine if this is a basic conversation or needs context
                logger.info("Determine Route Conversation (Basic / RAG)")
                is_basic_conversation = len(context) == 0 or all(c['score'] < settings.RAG_THRESHOLD for c in context)
                
                # Prepare conversation context
                conversation_context = ["Conversation History:"]
                if conversation:
                    logger.info(conversation.messages)
                    for message in conversation.messages[settings.N_LAST_MESSAGE:]:
                        conversation_context.append(f"{message.role}: {message.content}")
                conversation_context = "\n".join(conversation_context)
                
                # Select appropriate system prompt based on query type
                if is_basic_conversation:
                    system_prompt = """
                    Answer accoding user language, also consider conversation history if necessary to answer question.
                    You are a helpful and friendly AI assistant. 
                    Engage in natural conversation and provide accurate, concise responses. 
                    If the user mentions something vague or unclear, politely ask for clarification or context 
                    to ensure you provide the most relevant and helpful answer. 
                    If the user refers to specific documents or information, 
                    let them know you can search through the knowledge base to assist them.
                    """
                    
                    messages = [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": conversation_context},
                        {"role": "user", "content": user_message.content}
                    ]
                else:
                    system_prompt = """
                    Answer according to user language, also consider conversation history if necessary to answer question.
                    You are a helpful AI assistant with access to a knowledge base of documents.
                    Use the provided context to answer questions accurately and comprehensively.
                    
                    For each response:
                    1. Analyze the provided context and cite specific sources using page numbers
                    2. Structure your response to clearly separate information from different sources
                    3. When citing information, use the format: [Source: filename, Page: X]
                    4. If multiple sources support a point, cite all relevant sources
                    5. If the context doesn't fully address the question, clearly state what information is from the sources and what is general knowledge
                    
                    Always maintain accuracy over completeness. If you're unsure about something, acknowledge your uncertainty and explain what evidence you do have from the sources.
                    
                    Remember to:
                    - Provide page numbers for all cited information
                    - Distinguish between direct quotes and paraphrased content
                    - Note any conflicting information between sources
                    - Be transparent about gaps in the provided context
                    """
                    context_knowledge = [f"{cont['text']}\nSource: {cont['file_path']} - Page Number: {cont['page_number']}" for cont in context]
                    context_knowledge = "\n".join(context_knowledge)
                    messages = [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": conversation_context},
                        {
                            "role": "user", 
                            "content": f"""
                        Context: {context_knowledge}
                        Question: {user_message.content}
                        """}
                    ]
                
                # Generate response using LLM
                logger.info("LLM Generate Response...")
                logger.info(f"Message Throw: {messages}")
                response = await llm.chat_completion(
                    messages=messages,
                    temperature=settings.TEMPERATURE
                )
                
                # Create assistant message
                assistant_message = ChatMessage(
                    role="assistant",
                    content=response
                )
                logger.info(f"Generated response for {'basic' if is_basic_conversation else 'context-based'} query")
                logger.info(assistant_message.to_dict())
                
                # Save assistant message
                await manager.save_message(conversation_id, assistant_message)
                
                # Send response to client
                await manager.send_message(conversation_id, assistant_message)
                
            except Exception as e:
                traceback.print_exc()
                logger.error(f"Error processing message: {str(e)}")
                error_message = ChatMessage(
                    role="system",
                    content="I apologize, but I encountered an error processing your message."
                )
                await manager.send_message(conversation_id, error_message)
    
    except WebSocketDisconnect:
        traceback.print_exc()
        manager.disconnect(conversation_id)

    except Exception as e:
        traceback.print_exc()
        logger.error(f"WebSocket error: {str(e)}")
        manager.disconnect(conversation_id)

@router.post("/{conversation_id}", response_model=ChatResponse)
async def chat_post(conversation_id: str, request: ChatRequest):
    """POST endpoint for chat - mirrors WebSocket functionality."""
    try:
        # Verify conversation exists
        conversation = await manager.get_conversation_history(conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Create user message
        user_message = ChatMessage(
            role="user",
            content=request.message
        )
        
        # Save user message
        await manager.save_message(conversation_id, user_message)
        
        try:
            # Generate title if this is the first message
            logger.info("Generate Title...")
            if not conversation or (not conversation.messages and not conversation.metadata.get("title_generated")):
                title = await generate_title(user_message.content)
                await manager.update_title(conversation_id, title)
                await manager.db.conversations.update_one(
                    {"id": conversation_id},
                    {"$set": {"metadata.title_generated": True}}
                )
            
            # Get relevant context from vector store
            logger.info("Retrieve Relevant Context...")
            context = await vector_store.similarity_search(
                query=user_message.content,
                k=settings.TOP_K
            )
            
            # Determine if this is a basic conversation or needs context
            logger.info("Determine Route Conversation (Basic / RAG)")
            is_basic_conversation = len(context) == 0 or all(c['score'] < settings.RAG_THRESHOLD for c in context)
            
            # Prepare conversation context
            conversation_context = ["Conversation History:"]
            if conversation:
                for message in conversation.messages[settings.N_LAST_MESSAGE:]:
                    conversation_context.append(f"{message.role}: {message.content}")
            conversation_context = "\n".join(conversation_context)
            
            # Select appropriate system prompt based on query type
            if is_basic_conversation:
                system_prompt = """
                Answer accoding user language, also consider conversation history if necessary to answer question.
                You are a helpful and friendly AI assistant. 
                Engage in natural conversation and provide accurate, concise responses. 
                If the user mentions something vague or unclear, politely ask for clarification or context 
                to ensure you provide the most relevant and helpful answer. 
                If the user refers to specific documents or information, 
                let them know you can search through the knowledge base to assist them.
                """
                
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": conversation_context},
                    {"role": "user", "content": user_message.content}
                ]
            else:
                system_prompt = """
                Answer accoding user language, also consider conversation history if necessary to answer question.
                You are a helpful AI assistant with access to a knowledge base of documents.
                Use the provided context to answer questions accurately and comprehensively.
                If the context doesn't fully address the question, acknowledge what you know from the context
                and what you're unsure about. Always maintain accuracy over completeness.
                """
                
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": conversation_context},
                    {"role": "user", "content": f"""Context: {json.dumps([c['text'] for c in context])}
                    Question: {user_message.content}"""}
                ]
            
            # Generate response using LLM
            logger.info("LLM Generate Response...")
            logger.info(f"Message Throw: {messages}")
            response = await llm.chat_completion(
                messages=messages,
                temperature=settings.TEMPERATURE
            )
            
            # Create assistant message
            assistant_message = ChatMessage(
                role="assistant",
                content=response
            )
            logger.info(f"Generated response for {'basic' if is_basic_conversation else 'context-based'} query")
            logger.info(assistant_message.to_dict())
            
            # Save assistant message
            await manager.save_message(conversation_id, assistant_message)
            
            # Return the response
            return ChatResponse(
                role=assistant_message.role,
                content=assistant_message.content,
                timestamp=assistant_message.timestamp
            )
            
        except Exception as e:
            traceback.print_exc()
            logger.error(f"Error processing message: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="An error occurred while processing your message"
            )
    
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        logger.error(f"Chat error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred"
        )

@router.post("/{conversation_id}/messages/{message_index}/feedback")
async def submit_feedback(conversation_id: str, message_index: int, feedback: FeedbackRequest):
    """Submit feedback for a specific message in a conversation."""
    try:
        # Get conversation
        conversation = await manager.get_conversation_history(conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Validate message index
        if message_index < 0 or message_index >= len(conversation.messages):
            raise HTTPException(status_code=404, detail="Message not found")
        
        # Update feedback in the message
        now = datetime.utcnow()
        await manager.db.conversations.update_one(
            {"id": conversation_id},
            {"$set": {
                f"messages.{message_index}.feedback": {
                    "thumbs": feedback.thumbs,
                    "comment": feedback.comment,
                    "submitted_at": now
                }
            }}
        )
        
        return {"status": "success", "message": "Feedback submitted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error submitting feedback: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to submit feedback")