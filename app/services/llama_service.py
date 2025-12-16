"""
Llama3 AI service for generating summaries and recommendations
"""
import asyncio
import httpx
from typing import List, Optional
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
import torch
from loguru import logger

from app.config.settings import settings


class LlamaService:
    def __init__(self):
        self.model = None
        self.tokenizer = None
        self.pipeline = None
        self._initialized = False
        self.use_openrouter = bool(settings.OPENROUTER_API_KEY)
    
    async def initialize(self):
        """Initialize the Llama model (call this once at startup)"""
        if self._initialized:
            return
        
        try:
            logger.info(f"Loading Llama model: {settings.LLAMA_MODEL_PATH}")
            
            # For this demo, we'll use a smaller model that's easier to run locally
            # In production, you would use the actual Llama3 model
            model_name = "microsoft/DialoGPT-medium"  # Fallback model for demo
            
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModelForCausalLM.from_pretrained(model_name)
            
            # Set up generation pipeline
            self.pipeline = pipeline(
                "text-generation",
                model=self.model,
                tokenizer=self.tokenizer,
                device=0 if torch.cuda.is_available() else -1,
                do_sample=True,
                temperature=settings.LLAMA_TEMPERATURE,
                max_length=settings.LLAMA_MAX_LENGTH,
                pad_token_id=self.tokenizer.eos_token_id
            )
            
            self._initialized = True
            logger.info("Llama model initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Llama model: {str(e)}")
            # Fallback to a simple rule-based system
            self._initialized = False

    async def generate_summary(self, text: str) -> str:
        """Generate a summary of the given text"""
        if self.use_openrouter:
            return await self._generate_summary_openrouter(text)
        
        if not self._initialized:
            # Fallback summary generation
            return self._fallback_summary(text)
        
        try:
            prompt = f"Summarize the following text in 2-3 sentences:\n{text[:1000]}\nSummary:"
            
            # Run in thread to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, 
                self._generate_text, 
                prompt
            )
            
            # Extract summary from result
            if result and len(result) > 0:
                generated = result[0]['generated_text']
                summary = generated.split("Summary:")[-1].strip()
                return summary[:500]  # Limit summary length
            
            return self._fallback_summary(text)
            
        except Exception as e:
            logger.error(f"Error generating summary: {str(e)}")
            return self._fallback_summary(text)

    async def generate_recommendations(self, user_preferences: str, books_context: str) -> str:
        """Generate book recommendations based on user preferences"""
        if self.use_openrouter:
            return await self._generate_recommendations_openrouter(user_preferences, books_context)
        
        if not self._initialized:
            return "Based on your preferences, I recommend exploring books in similar genres and by authors you've enjoyed before."
        
        try:
            prompt = f"User preferences: {user_preferences}\nAvailable books: {books_context[:800]}\nRecommendation reasoning:"
            
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, 
                self._generate_text, 
                prompt
            )
            
            if result and len(result) > 0:
                generated = result[0]['generated_text']
                reasoning = generated.split("Recommendation reasoning:")[-1].strip()
                return reasoning[:300]
            
            return "Based on your reading history and preferences, these books match your interests."
            
        except Exception as e:
            logger.error(f"Error generating recommendations: {str(e)}")
            return "Based on your preferences, these books are recommended for you."

    def _generate_text(self, prompt: str):
        """Internal method to generate text (runs in executor)"""
        return self.pipeline(
            prompt,
            max_length=len(prompt.split()) + 100,
            num_return_sequences=1,
            do_sample=True
        )

    def _fallback_summary(self, text: str) -> str:
        """Simple fallback summary when AI model is not available"""
        sentences = text.split('.')[:3]  # Take first 3 sentences
        summary = '. '.join(sentences).strip()
        if summary and not summary.endswith('.'):
            summary += '.'
        return summary or "Summary not available."

    async def _generate_summary_openrouter(self, text: str) -> str:
        """Generate summary using OpenRouter API"""
        try:
            prompt = f"Please provide a concise 2-3 sentence summary of the following text:\n\n{text[:2000]}"
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": settings.OPENROUTER_MODEL,
                        "messages": [
                            {"role": "user", "content": prompt}
                        ],
                        "max_tokens": 150,
                        "temperature": settings.LLAMA_TEMPERATURE,
                    },
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get("choices") and len(result["choices"]) > 0:
                        summary = result["choices"][0]["message"]["content"].strip()
                        return summary[:500]  # Limit summary length
                
                logger.warning(f"OpenRouter API error: {response.status_code}")
                return self._fallback_summary(text)
                
        except Exception as e:
            logger.error(f"Error with OpenRouter API: {str(e)}")
            return self._fallback_summary(text)

    async def _generate_recommendations_openrouter(self, user_preferences: str, books_context: str) -> str:
        """Generate recommendations using OpenRouter API"""
        try:
            prompt = f"""Based on the user preferences and available books below, explain why these books are good recommendations:

User Preferences: {user_preferences}

Available Books:
{books_context}

Please provide a brief, engaging explanation of why these books match the user's interests."""
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": settings.OPENROUTER_MODEL,
                        "messages": [
                            {"role": "user", "content": prompt}
                        ],
                        "max_tokens": 200,
                        "temperature": settings.LLAMA_TEMPERATURE,
                    },
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get("choices") and len(result["choices"]) > 0:
                        reasoning = result["choices"][0]["message"]["content"].strip()
                        return reasoning[:300]
                
                logger.warning(f"OpenRouter API error: {response.status_code}")
                return "Based on your preferences, these books are recommended for you."
                
        except Exception as e:
            logger.error(f"Error with OpenRouter API: {str(e)}")
            return "Based on your preferences, these books are recommended for you."


# Global instance
llama_service = LlamaService()
