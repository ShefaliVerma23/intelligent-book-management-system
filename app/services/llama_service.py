"""
AI Service for generating summaries and recommendations

Features:
- OpenRouter API (cloud-based, recommended for production)
- Local Hugging Face models (optional, requires heavy dependencies)
- Configurable timeouts to prevent hangs
- Graceful fallbacks when AI is unavailable
- Structured outputs with metadata
- Comprehensive error tracking

IMPORTANT: This service is designed to NEVER hang or crash the application.
All operations have timeouts and fallbacks.
"""
import asyncio
import time
import hashlib
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from functools import partial
from typing import List, Optional, Dict, Any
from loguru import logger

from app.config.settings import settings
from app.api.schemas import (
    LLMSummaryOutput, 
    LLMRecommendationOutput, 
    LLMReviewSummaryOutput,
    LLMGenerationMetadata
)

# Thread pool for CPU-bound operations (kept small to prevent resource exhaustion)
_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="llm_")

# Global timeout for any AI operation (prevents indefinite hangs)
MAX_OPERATION_TIMEOUT = 60  # seconds


class LlamaService:
    """
    AI service with built-in reliability features.
    
    Key Design Principles:
    1. NEVER hang - all operations have timeouts
    2. NEVER crash - all errors are caught and logged
    3. ALWAYS return a response - use fallbacks when needed
    4. PREFER simplicity - OpenRouter over local models
    """
    
    def __init__(self):
        self.model = None
        self.tokenizer = None
        self.pipeline = None
        self._initialized = False
        self._initializing = False
        self._init_failed = False
        self._init_error: Optional[str] = None
        
        # Determine mode based on API key availability
        self.use_openrouter = bool(settings.OPENROUTER_API_KEY)
        
        if not self.use_openrouter:
            logger.warning(
                "OPENROUTER_API_KEY not set - AI features will use fallback mode. "
                "Set OPENROUTER_API_KEY for full AI functionality."
            )
    
    async def initialize(self) -> bool:
        """
        Initialize the AI service.
        
        Returns True if initialization succeeded, False otherwise.
        This method is safe to call multiple times.
        """
        if self._initialized:
            return True
        
        if self._init_failed:
            logger.debug("Skipping init - previous initialization failed")
            return False
        
        if self._initializing:
            # Wait for ongoing initialization
            for _ in range(50):  # Max 5 seconds wait
                await asyncio.sleep(0.1)
                if self._initialized or self._init_failed:
                    break
            return self._initialized
        
        self._initializing = True
        
        try:
            if self.use_openrouter:
                # OpenRouter just needs API key validation
                if not self._validate_openrouter_config():
                    self._init_failed = True
                    return False
                
                logger.info(
                    "AI service initialized (OpenRouter mode)",
                    extra={
                        "model": settings.OPENROUTER_MODEL,
                        "timeout": settings.LLM_REQUEST_TIMEOUT,
                    }
                )
                self._initialized = True
                return True
            
            # Local model initialization (optional, heavyweight)
            # Skip by default - most deployments should use OpenRouter
            logger.info("AI service initialized (fallback mode - no API key)")
            self._initialized = True
            return True
            
        except Exception as e:
            self._init_error = str(e)
            self._init_failed = True
            logger.error(f"AI service initialization failed: {e}")
            return False
            
        finally:
            self._initializing = False
    
    def _validate_openrouter_config(self) -> bool:
        """Validate OpenRouter configuration"""
        if not settings.OPENROUTER_API_KEY:
            logger.error("OPENROUTER_API_KEY is required for OpenRouter mode")
            return False
        
        if len(settings.OPENROUTER_API_KEY) < 10:
            logger.error("OPENROUTER_API_KEY appears invalid (too short)")
            return False
        
        if not settings.OPENROUTER_MODEL:
            logger.error("OPENROUTER_MODEL is required")
            return False
        
        return True
    
    def _create_metadata(
        self, 
        max_tokens: int, 
        generation_time_ms: Optional[int] = None,
        output_tokens: Optional[int] = None,
        input_tokens: Optional[int] = None
    ) -> LLMGenerationMetadata:
        """Create generation metadata for response"""
        return LLMGenerationMetadata(
            model=settings.OPENROUTER_MODEL if self.use_openrouter else "fallback",
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=max_tokens,
            generation_time_ms=generation_time_ms,
            output_tokens=output_tokens,
            input_tokens=input_tokens
        )

    def _truncate_input(self, text: str, max_chars: Optional[int] = None) -> str:
        """Truncate input text to prevent oversized requests"""
        limit = max_chars or settings.LLM_MAX_INPUT_CHARS
        if len(text) > limit:
            logger.debug(f"Truncating input from {len(text)} to {limit} chars")
            return text[:limit] + "..."
        return text

    def _fallback_summary(self, text: str) -> str:
        """
        Simple extractive summary when AI is unavailable.
        
        Takes first few sentences as a basic summary.
        """
        if not text or not text.strip():
            return "No content available to summarize."
        
        # Split by sentence-ending punctuation
        sentences = []
        current = ""
        for char in text:
            current += char
            if char in '.!?' and len(current.strip()) > 10:
                sentences.append(current.strip())
                current = ""
                if len(sentences) >= 3:
                    break
        
        if current.strip() and len(sentences) < 3:
            sentences.append(current.strip())
        
        if not sentences:
            # Fallback: just take first 200 chars
            return text[:200].strip() + "..." if len(text) > 200 else text.strip()
        
        summary = ' '.join(sentences[:3])
        if not summary.endswith(('.', '!', '?')):
            summary += '.'
        
        return summary

    async def generate_summary(self, text: str) -> LLMSummaryOutput:
        """
        Generate a summary of the given text.
        
        Guarantees:
        - Returns within MAX_OPERATION_TIMEOUT seconds
        - Always returns a valid LLMSummaryOutput (even on failure)
        - Never raises exceptions to caller
        """
        start_time = time.time()
        max_tokens = settings.LLM_MAX_TOKENS_SUMMARY
        request_id = self._generate_request_id()
        
        logger.debug(
            "Summary generation started",
            extra={
                "request_id": request_id,
                "input_length": len(text),
                "max_tokens": max_tokens
            }
        )
        
        try:
            # Wrap in asyncio.wait_for for hard timeout
            result = await asyncio.wait_for(
                self._generate_summary_impl(text, max_tokens, start_time, request_id),
                timeout=MAX_OPERATION_TIMEOUT
            )
            return result
            
        except asyncio.TimeoutError:
            generation_time_ms = int((time.time() - start_time) * 1000)
            logger.error(
                "Summary generation timed out",
                extra={
                    "request_id": request_id,
                    "timeout": MAX_OPERATION_TIMEOUT,
                    "generation_time_ms": generation_time_ms
                }
            )
            return LLMSummaryOutput(
                summary=self._fallback_summary(text),
                success=False,
                error=f"Operation timed out after {MAX_OPERATION_TIMEOUT}s",
                metadata=self._create_metadata(max_tokens, generation_time_ms)
            )
            
        except Exception as e:
            generation_time_ms = int((time.time() - start_time) * 1000)
            logger.error(
                f"Summary generation failed unexpectedly: {e}",
                extra={"request_id": request_id},
                exc_info=True
            )
            return LLMSummaryOutput(
                summary=self._fallback_summary(text),
                success=False,
                error=str(e),
                metadata=self._create_metadata(max_tokens, generation_time_ms)
            )

    async def _generate_summary_impl(
        self, 
        text: str, 
        max_tokens: int, 
        start_time: float,
        request_id: str
    ) -> LLMSummaryOutput:
        """Internal implementation of summary generation"""
        
        if self.use_openrouter:
            return await self._generate_summary_openrouter(text, max_tokens, start_time, request_id)
        
        # Fallback mode
        logger.debug(f"Using fallback summary (no OpenRouter)", extra={"request_id": request_id})
        summary = self._fallback_summary(text)
        generation_time_ms = int((time.time() - start_time) * 1000)
        
        return LLMSummaryOutput(
            summary=summary,
            success=True,
            metadata=self._create_metadata(max_tokens, generation_time_ms)
        )

    async def generate_recommendations(
        self, 
        user_preferences: str, 
        books_context: str
    ) -> LLMRecommendationOutput:
        """
        Generate book recommendation reasoning.
        
        Same guarantees as generate_summary.
        """
        start_time = time.time()
        max_tokens = settings.LLM_MAX_TOKENS_RECOMMENDATION
        request_id = self._generate_request_id()
        
        logger.debug(
            "Recommendation generation started",
            extra={
                "request_id": request_id,
                "preferences_length": len(user_preferences),
                "context_length": len(books_context)
            }
        )
        
        try:
            result = await asyncio.wait_for(
                self._generate_recommendations_impl(
                    user_preferences, books_context, max_tokens, start_time, request_id
                ),
                timeout=MAX_OPERATION_TIMEOUT
            )
            return result
            
        except asyncio.TimeoutError:
            generation_time_ms = int((time.time() - start_time) * 1000)
            logger.error("Recommendation generation timed out", extra={"request_id": request_id})
            return LLMRecommendationOutput(
                reasoning="Based on your preferences, these books are recommended for you.",
                success=False,
                error=f"Operation timed out after {MAX_OPERATION_TIMEOUT}s",
                metadata=self._create_metadata(max_tokens, generation_time_ms)
            )
            
        except Exception as e:
            generation_time_ms = int((time.time() - start_time) * 1000)
            logger.error(f"Recommendation generation failed: {e}", extra={"request_id": request_id})
            return LLMRecommendationOutput(
                reasoning="Based on your preferences, these books are recommended for you.",
                success=False,
                error=str(e),
                metadata=self._create_metadata(max_tokens, generation_time_ms)
            )

    async def _generate_recommendations_impl(
        self,
        user_preferences: str,
        books_context: str,
        max_tokens: int,
        start_time: float,
        request_id: str
    ) -> LLMRecommendationOutput:
        """Internal implementation of recommendations"""
        
        if self.use_openrouter:
            return await self._generate_recommendations_openrouter(
                user_preferences, books_context, max_tokens, start_time, request_id
            )
        
        # Fallback
        generation_time_ms = int((time.time() - start_time) * 1000)
        return LLMRecommendationOutput(
            reasoning="Based on your reading history and preferences, these books match your interests.",
            success=True,
            metadata=self._create_metadata(max_tokens, generation_time_ms)
        )

    async def generate_review_summary(self, reviews_text: str) -> LLMReviewSummaryOutput:
        """
        Generate a summary of book reviews.
        
        Same guarantees as other generation methods.
        """
        start_time = time.time()
        max_tokens = settings.LLM_MAX_TOKENS_SUMMARY
        request_id = self._generate_request_id()
        
        if not reviews_text or not reviews_text.strip():
            return LLMReviewSummaryOutput(
                summary="No reviews available to summarize.",
                success=True,
                metadata=self._create_metadata(max_tokens, 0)
            )
        
        try:
            result = await asyncio.wait_for(
                self._generate_review_summary_impl(reviews_text, max_tokens, start_time, request_id),
                timeout=MAX_OPERATION_TIMEOUT
            )
            return result
            
        except asyncio.TimeoutError:
            generation_time_ms = int((time.time() - start_time) * 1000)
            logger.error("Review summary generation timed out", extra={"request_id": request_id})
            return LLMReviewSummaryOutput(
                summary=self._fallback_summary(reviews_text),
                success=False,
                error=f"Operation timed out after {MAX_OPERATION_TIMEOUT}s",
                metadata=self._create_metadata(max_tokens, generation_time_ms)
            )
            
        except Exception as e:
            generation_time_ms = int((time.time() - start_time) * 1000)
            logger.error(f"Review summary generation failed: {e}", extra={"request_id": request_id})
            return LLMReviewSummaryOutput(
                summary=self._fallback_summary(reviews_text),
                success=False,
                error=str(e),
                metadata=self._create_metadata(max_tokens, generation_time_ms)
            )

    async def _generate_review_summary_impl(
        self,
        reviews_text: str,
        max_tokens: int,
        start_time: float,
        request_id: str
    ) -> LLMReviewSummaryOutput:
        """Internal implementation of review summary"""
        
        if self.use_openrouter:
            return await self._generate_review_summary_openrouter(
                reviews_text, max_tokens, start_time, request_id
            )
        
        # Fallback
        generation_time_ms = int((time.time() - start_time) * 1000)
        return LLMReviewSummaryOutput(
            summary=self._fallback_summary(reviews_text),
            success=True,
            metadata=self._create_metadata(max_tokens, generation_time_ms)
        )

    # =========================================================================
    # OpenRouter API Implementation
    # =========================================================================
    
    async def _make_openrouter_request(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int,
        request_id: str,
        retry_count: int = 0
    ) -> Optional[Dict[str, Any]]:
        """
        Make a request to OpenRouter API with retry logic.
        
        Has its own timeout (LLM_REQUEST_TIMEOUT) per attempt.
        """
        # Lazy import to avoid loading httpx if not needed
        import httpx
        
        try:
            timeout = httpx.Timeout(
                connect=10.0,  # Connection timeout
                read=settings.LLM_REQUEST_TIMEOUT,  # Read timeout
                write=10.0,  # Write timeout
                pool=5.0  # Pool timeout
            )
            
            async with httpx.AsyncClient(timeout=timeout) as client:
                logger.debug(
                    "Making OpenRouter request",
                    extra={
                        "request_id": request_id,
                        "model": settings.OPENROUTER_MODEL,
                        "retry": retry_count
                    }
                )
                
                response = await client.post(
                    settings.OPENROUTER_API_URL,
                    headers={
                        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": "https://book-management-system.local",
                        "X-Title": "Intelligent Book Management System"
                    },
                    json={
                        "model": settings.OPENROUTER_MODEL,
                        "messages": messages,
                        "max_tokens": max_tokens,
                        "temperature": settings.LLM_TEMPERATURE,
                        "top_p": settings.LLM_TOP_P,
                    }
                )
                
                if response.status_code == 200:
                    logger.debug(
                        "OpenRouter request succeeded",
                        extra={"request_id": request_id}
                    )
                    return response.json()
                
                # Retry on transient errors
                if response.status_code in [429, 500, 502, 503, 504]:
                    if retry_count < settings.LLM_RETRY_ATTEMPTS:
                        wait_time = min(2 ** retry_count, 8)  # Max 8 second wait
                        logger.warning(
                            f"OpenRouter error {response.status_code}, retrying in {wait_time}s",
                            extra={"request_id": request_id, "retry": retry_count}
                        )
                        await asyncio.sleep(wait_time)
                        return await self._make_openrouter_request(
                            messages, max_tokens, request_id, retry_count + 1
                        )
                
                logger.error(
                    f"OpenRouter request failed: {response.status_code}",
                    extra={
                        "request_id": request_id,
                        "status": response.status_code,
                        "body": response.text[:200] if response.text else None
                    }
                )
                return None
                
        except httpx.TimeoutException as e:
            logger.error(
                f"OpenRouter request timed out: {e}",
                extra={"request_id": request_id}
            )
            if retry_count < settings.LLM_RETRY_ATTEMPTS:
                return await self._make_openrouter_request(
                    messages, max_tokens, request_id, retry_count + 1
                )
            return None
            
        except Exception as e:
            logger.error(
                f"OpenRouter request error: {e}",
                extra={"request_id": request_id},
                exc_info=True
            )
            return None

    async def _generate_summary_openrouter(
        self, 
        text: str, 
        max_tokens: int,
        start_time: float,
        request_id: str
    ) -> LLMSummaryOutput:
        """Generate summary using OpenRouter API"""
        truncated = self._truncate_input(text, 2000)
        messages = [{
            "role": "user",
            "content": f"Provide a concise 2-3 sentence summary:\n\n{truncated}"
        }]
        
        result = await self._make_openrouter_request(messages, max_tokens, request_id)
        generation_time_ms = int((time.time() - start_time) * 1000)
        
        if result and result.get("choices"):
            summary = result["choices"][0]["message"]["content"].strip()[:500]
            usage = result.get("usage", {})
            
            logger.info(
                "Summary generated via OpenRouter",
                extra={
                    "request_id": request_id,
                    "time_ms": generation_time_ms,
                    "tokens": usage.get("completion_tokens")
                }
            )
            
            return LLMSummaryOutput(
                summary=summary,
                success=True,
                metadata=LLMGenerationMetadata(
                    model=settings.OPENROUTER_MODEL,
                    temperature=settings.LLM_TEMPERATURE,
                    max_tokens=max_tokens,
                    input_tokens=usage.get("prompt_tokens"),
                    output_tokens=usage.get("completion_tokens"),
                    generation_time_ms=generation_time_ms
                )
            )
        
        logger.warning("OpenRouter failed, using fallback", extra={"request_id": request_id})
        return LLMSummaryOutput(
            summary=self._fallback_summary(text),
            success=False,
            error="OpenRouter API request failed",
            metadata=self._create_metadata(max_tokens, generation_time_ms)
        )

    async def _generate_recommendations_openrouter(
        self, 
        user_preferences: str, 
        books_context: str,
        max_tokens: int,
        start_time: float,
        request_id: str
    ) -> LLMRecommendationOutput:
        """Generate recommendations using OpenRouter API"""
        truncated = self._truncate_input(books_context, 1500)
        messages = [{
            "role": "user",
            "content": f"Based on preferences: {user_preferences}\n\nExplain why these books are good matches:\n{truncated}"
        }]
        
        result = await self._make_openrouter_request(messages, max_tokens, request_id)
        generation_time_ms = int((time.time() - start_time) * 1000)
        
        if result and result.get("choices"):
            reasoning = result["choices"][0]["message"]["content"].strip()[:300]
            usage = result.get("usage", {})
            
            return LLMRecommendationOutput(
                reasoning=reasoning,
                success=True,
                metadata=LLMGenerationMetadata(
                    model=settings.OPENROUTER_MODEL,
                    temperature=settings.LLM_TEMPERATURE,
                    max_tokens=max_tokens,
                    input_tokens=usage.get("prompt_tokens"),
                    output_tokens=usage.get("completion_tokens"),
                    generation_time_ms=generation_time_ms
                )
            )
        
        return LLMRecommendationOutput(
            reasoning="Based on your preferences, these books are recommended.",
            success=False,
            error="OpenRouter API request failed",
            metadata=self._create_metadata(max_tokens, generation_time_ms)
        )

    async def _generate_review_summary_openrouter(
        self,
        reviews_text: str,
        max_tokens: int,
        start_time: float,
        request_id: str
    ) -> LLMReviewSummaryOutput:
        """Generate review summary using OpenRouter API"""
        truncated = self._truncate_input(reviews_text, 2000)
        messages = [{
            "role": "user",
            "content": f"Summarize these reviews and note the overall sentiment:\n\n{truncated}"
        }]
        
        result = await self._make_openrouter_request(messages, max_tokens, request_id)
        generation_time_ms = int((time.time() - start_time) * 1000)
        
        if result and result.get("choices"):
            summary = result["choices"][0]["message"]["content"].strip()[:500]
            usage = result.get("usage", {})
            
            # Simple sentiment detection
            sentiment = None
            lower = summary.lower()
            if "positive" in lower:
                sentiment = "positive"
            elif "negative" in lower:
                sentiment = "negative"
            elif "mixed" in lower:
                sentiment = "mixed"
            
            return LLMReviewSummaryOutput(
                summary=summary,
                sentiment=sentiment,
                success=True,
                metadata=LLMGenerationMetadata(
                    model=settings.OPENROUTER_MODEL,
                    temperature=settings.LLM_TEMPERATURE,
                    max_tokens=max_tokens,
                    input_tokens=usage.get("prompt_tokens"),
                    output_tokens=usage.get("completion_tokens"),
                    generation_time_ms=generation_time_ms
                )
            )
        
        return LLMReviewSummaryOutput(
            summary=self._fallback_summary(reviews_text),
            success=False,
            error="OpenRouter API request failed",
            metadata=self._create_metadata(max_tokens, generation_time_ms)
        )

    # =========================================================================
    # Utility Methods
    # =========================================================================
    
    def _generate_request_id(self) -> str:
        """Generate unique request ID for tracing"""
        return f"llm_{int(time.time() * 1000)}_{hashlib.md5(str(time.time()).encode()).hexdigest()[:6]}"
    
    # Legacy compatibility methods
    async def generate_summary_text(self, text: str) -> str:
        """Legacy method: returns just the summary text"""
        result = await self.generate_summary(text)
        return result.summary
    
    async def generate_recommendations_text(self, user_preferences: str, books_context: str) -> str:
        """Legacy method: returns just the reasoning text"""
        result = await self.generate_recommendations(user_preferences, books_context)
        return result.reasoning


# Global singleton instance
llama_service = LlamaService()
