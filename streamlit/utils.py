import httpx
import os
import time
import streamlit as st
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

# Constants
API_URL = os.getenv("API_URL", "http://localhost:8000")
API_PREFIX = "/api/v1"

def get_api_url(endpoint: str) -> str:
    """Get the full API URL for an endpoint."""
    return f"{API_URL}{API_PREFIX}{endpoint}"

# Document Management
def upload_document(file) -> Tuple[bool, Optional[str]]:
    """
    Upload a document to the API.
    
    Args:
        file: The uploaded file object from Streamlit
        
    Returns:
        Tuple of (success, task_id or None)
    """
    try:
        files = {"file": (file.name, file.getvalue(), "application/pdf")}
        response = httpx.post(get_api_url("/documents/upload"), files=files)
        
        if response.status_code == 200:
            return True, response.json().get("task_id")
        else:
            st.error(f"Failed to upload document: {response.text}")
            return False, None
    except Exception as e:
        st.error(f"Error uploading document: {str(e)}")
        return False, None

def poll_task_status(task_id: str, max_attempts: int = 60, interval: float = 2.0) -> Dict[str, Any]:
    """
    Poll the task status until it completes or fails.
    
    Args:
        task_id: The ID of the task to poll
        max_attempts: Maximum number of polling attempts
        interval: Time interval between polls in seconds
        
    Returns:
        Task status information
    """
    for attempt in range(max_attempts):
        try:
            response = httpx.get(get_api_url(f"/documents/task/{task_id}"))
            if response.status_code == 200:
                task_data = response.json()
                status = task_data.get("status", "")
                
                if status in ["completed", "failed"]:
                    return task_data
                
                # Add a small delay before the next poll
                time.sleep(interval)
            else:
                return {"status": "failed", "error": f"Failed to get task status: {response.text}"}
        except Exception as e:
            return {"status": "failed", "error": f"Error polling task: {str(e)}"}
    
    return {"status": "timeout", "error": "Task polling timed out"}

# Conversation Management
def create_conversation() -> Optional[str]:
    """Create a new conversation and return its ID."""
    try:
        response = httpx.put(get_api_url("/chat/conversation"))
        if response.status_code == 200:
            return response.json()["id"]
        else:
            st.error(f"Failed to create conversation: {response.text}")
            return None
    except Exception as e:
        st.error(f"Error creating conversation: {str(e)}")
        return None

def get_conversations(skip: int = 0, limit: int = 20) -> List[Dict[str, Any]]:
    """Get a list of conversations with pagination."""
    try:
        response = httpx.get(get_api_url(f"/chat/conversations?skip={skip}&limit={limit}"))
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Failed to get conversations: {response.text}")
            return []
    except Exception as e:
        st.error(f"Error getting conversations: {str(e)}")
        return []

def get_conversation(conversation_id: str) -> Optional[Dict[str, Any]]:
    """Get a specific conversation by ID."""
    try:
        response = httpx.get(get_api_url(f"/chat/conversations/{conversation_id}"))
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Failed to get conversation: {response.text}")
            return None
    except Exception as e:
        st.error(f"Error getting conversation: {str(e)}")
        return None

def delete_conversation(conversation_id: str) -> bool:
    """Delete a conversation by ID."""
    try:
        response = httpx.delete(get_api_url(f"/chat/conversations/{conversation_id}"))
        if response.status_code == 200:
            return True
        else:
            st.error(f"Failed to delete conversation: {response.text}")
            return False
    except Exception as e:
        st.error(f"Error deleting conversation: {str(e)}")
        return False

# Utility Functions
def format_timestamp(timestamp_str: str) -> str:
    """Format an ISO timestamp to a human-readable format."""
    try:
        if not timestamp_str:
            return "Unknown"
        
        # Handle both string ISO format and numeric timestamp
        if isinstance(timestamp_str, str):
            dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        else:
            dt = datetime.fromtimestamp(timestamp_str)
        
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return "Invalid date"

def format_file_size(size_bytes: int) -> str:
    """Format file size in bytes to human-readable format."""
    if size_bytes < 1024:
        return f"{size_bytes} bytes"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB" 