import streamlit as st
import httpx
import os
from typing import Dict, List, Any, Optional
from datetime import datetime

# Configure the app
st.set_page_config(
    page_title="RAG Chat System",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Constants
API_URL = os.getenv("API_URL", "http://localhost:8000")
API_PREFIX = "/api/v1"

# State management
if "messages" not in st.session_state:
    st.session_state.messages = []

if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = None


def get_api_url(endpoint: str) -> str:
    """Get the full API URL for an endpoint."""
    return f"{API_URL}{API_PREFIX}{endpoint}"


def load_conversations() -> List[Dict[str, Any]]:
    """Load all conversations from the API."""
    try:
        response = httpx.get(get_api_url("/chat/conversations"))
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Failed to load conversations: {response.text}")
            return []
    except Exception as _:
        return []


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


def get_conversation(conversation_id: str) -> Dict[str, Any]:
    """Get a conversation by ID."""
    try:
        response = httpx.get(get_api_url(f"/chat/conversations/{conversation_id}"))
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Failed to get conversation: {response.text}")
            return {}
    except Exception as _:
        return {}


def upload_document(file) -> bool:
    """Upload a document to the API."""
    try:
        files = {"file": (file.name, file.getvalue(), "application/pdf")}
        response = httpx.post(get_api_url("/documents/upload"), files=files)
        if response.status_code == 200:
            return True
        else:
            st.error(f"Failed to upload document: {response.text}")
            return False
    except Exception as e:
        st.error(f"Error uploading document: {str(e)}")
        return False


def get_task_status(task_id: str) -> Dict[str, Any]:
    """Get the status of a document processing task."""
    try:
        response = httpx.get(get_api_url(f"/documents/task/{task_id}"))
        if response.status_code == 200:
            return response.json()
        else:
            return {"status": "failed"}
    except Exception:
        return {"status": "failed"}


def format_message(msg: Dict[str, Any]) -> None:
    """Format and display a message in the chat UI."""
    role = msg.get("role", "")
    content = msg.get("content", "")
    
    if role == "user":
        st.chat_message("user").write(content)
    elif role == "assistant":
        st.chat_message("assistant").write(content)
    elif role == "system":
        st.chat_message("system").write(content)


def send_message(conversation_id: str, message: str) -> Optional[Dict[str, Any]]:
    """Send a message to the chat API and return the response."""
    try:
        response = httpx.post(
            get_api_url(f"/chat/{conversation_id}"),
            json={"message": message},
            timeout=60.0  # Increased timeout for long responses
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Failed to send message: {response.text}")
            return None
    except Exception as e:
        st.error(f"Error sending message: {str(e)}")
        return None


def load_conversation_history(conversation_id: str) -> None:
    """Load conversation history and update the UI."""
    conversation = get_conversation(conversation_id)
    if conversation and "messages" in conversation:
        st.session_state.messages = conversation["messages"]


# UI Components
def sidebar():
    """Render the sidebar with conversations and document upload."""
    st.sidebar.title("RAG Chat System")
    
    # Document Upload Section
    st.sidebar.header("📤 Upload Documents")
    uploaded_file = st.sidebar.file_uploader("Upload PDF", type="pdf")
    
    if uploaded_file and st.sidebar.button("Process Document"):
        with st.sidebar.status("Uploading document...") as status:
            if upload_document(uploaded_file):
                status.update(label="Document uploaded successfully!", state="complete")
                st.sidebar.success(f"Document '{uploaded_file.name}' uploaded and being processed.")
            else:
                status.update(label="Failed to upload document", state="error")
    
    # Conversation Management
    st.sidebar.header("💬 Conversations")
    
    if st.sidebar.button("New Conversation"):
        with st.spinner("Creating new conversation..."):
            # Create a new conversation
            conversation_id = create_conversation()
            if conversation_id:
                st.session_state.conversation_id = conversation_id
                st.session_state.messages = []
                st.sidebar.success("New conversation created!")
                st.rerun()
            else:
                st.sidebar.error("Failed to create new conversation.")
    
    # List existing conversations
    conversations = load_conversations()
    if conversations:
        st.sidebar.subheader("Select Conversation")
        for conv in conversations:
            conv_id = conv.get("id", "")
            title = conv.get("title", "Untitled")
            created_at = conv.get("created_at", "")
            
            # Format the date if it exists
            if created_at:
                try:
                    # Parse ISO format or timestamp
                    if isinstance(created_at, str):
                        created_date = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                    else:
                        created_date = datetime.fromtimestamp(created_at)
                    
                    date_str = created_date.strftime("%Y-%m-%d %H:%M")
                except Exception as _:
                    date_str = "Unknown date"
            else:
                date_str = "Unknown date"
            
            # Create a button for each conversation
            if st.sidebar.button(f"{title} ({date_str})", key=f"conv_{conv_id}"):
                st.session_state.conversation_id = conv_id
                load_conversation_history(conv_id)
                st.rerun()
    
    # About section
    st.sidebar.header("ℹ️ About")
    st.sidebar.info(
        """
        This is a RAG (Retrieval-Augmented Generation) chat system.
        Upload documents and ask questions about them.
        
        The system will retrieve relevant information from your documents
        to provide accurate and contextual responses.
        """
    )


def main_content():
    """Render the main chat interface."""
    st.title("RAG Chat System")
    
    # Check if we have an active conversation
    if st.session_state.conversation_id is None:
        st.info("👈 Create a new conversation or select an existing one from the sidebar.")
        return
    
    # Display conversation title
    conversation = get_conversation(st.session_state.conversation_id)
    if conversation:
        st.subheader(f"Conversation: {conversation.get('title', 'Untitled')}")
    
    # Display chat messages
    for message in st.session_state.messages:
        format_message(message)
    
    # Chat input
    if prompt := st.chat_input("Ask a question about your documents..."):
        # Add user message to UI
        st.chat_message("user").write(prompt)
        
        # Add to session state
        user_message = {
            "role": "user",
            "content": prompt
        }
        st.session_state.messages.append(user_message)
        
        # Send message and get response
        with st.spinner("Thinking..."):
            response = send_message(st.session_state.conversation_id, prompt)
            
            if response:
                # Add assistant message to session state and display it
                assistant_message = {
                    "role": response["role"],
                    "content": response["content"]
                }
                st.session_state.messages.append(assistant_message)
                format_message(assistant_message)
            else:
                st.error("Failed to get response. Please try again.")


# Main app layout
def main():
    sidebar()
    main_content()


if __name__ == "__main__":
    main() 