from typing import List, Dict
from loguru import logger
import groq

from ..settings import get_settings

settings = get_settings()

class GroqLLM:
    """
    Utility class for interacting with Groq's LLM API.
    Handles chat completions with proper context management.
    """
    
    def __init__(self):
        """Initialize the Groq client."""
        self.client = groq.AsyncGroq(api_key=settings.GROQ_API_KEY)
        self.model = settings.MODEL_NAME
        logger.info(f"Initialized GroqLLM with model: {self.model}")
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = None,
        max_tokens: int = None
    ) -> str:
        """
        Generate a chat completion response.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            temperature: Optional temperature override
            max_tokens: Optional max tokens override
            
        Returns:
            str: Generated response text
        """
        try:
            # Calculate approximate token count
            total_chars = sum(len(m["content"]) for m in messages)
            approx_tokens = total_chars // 4  # Rough estimate
            
            # Ensure we don't exceed context window
            if max_tokens is None:
                max_tokens = min(
                    settings.MAX_CONTEXT_LENGTH - approx_tokens,
                    2048  # Default max response length
                )
            
            # Generate completion
            completion = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature or settings.TEMPERATURE,
                max_tokens=max_tokens,
                stream=False  # We'll implement streaming later
            )
            
            # Extract and return the response text
            response = completion.choices[0].message.content
            return response.strip()
            
        except Exception as e:
            logger.error(f"Error generating chat completion: {str(e)}")
            raise
    
    async def stream_chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = None,
        max_tokens: int = None
    ):
        """
        Generate a streaming chat completion response.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            temperature: Optional temperature override
            max_tokens: Optional max tokens override
            
        Yields:
            str: Generated response text chunks
        """
        try:
            # Calculate approximate token count
            total_chars = sum(len(m["content"]) for m in messages)
            approx_tokens = total_chars // 4  # Rough estimate
            
            # Ensure we don't exceed context window
            if max_tokens is None:
                max_tokens = min(
                    settings.MAX_CONTEXT_LENGTH - approx_tokens,
                    2048  # Default max response length
                )
            
            # Generate streaming completion
            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature or settings.TEMPERATURE,
                max_tokens=max_tokens,
                stream=True
            )
            
            # Yield response chunks
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            logger.error(f"Error generating streaming chat completion: {str(e)}")
            raise 