"""
Document Summarizer — auto-generates summary, keywords, topics, and
department classification when a document is uploaded.
"""
import asyncio
import json
import logging
from typing import Dict, List, Any
import google.generativeai as genai
from app.core.config import settings

logger = logging.getLogger(__name__)

SUMMARY_PROMPT = """You are an enterprise document analyzer.

Analyze the following document text and extract:
1. A concise 2-3 sentence summary
2. 5-10 key keywords/terms
3. 2-4 main topics covered
4. The most likely department this document belongs to (choose ONE from: HR, Finance, Legal, Engineering, Marketing, Operations, General)

Document title: "{title}"

Document text (first portion):
{text}

Return ONLY a valid JSON object with this exact structure:
{{
  "summary": "...",
  "keywords": ["keyword1", "keyword2", ...],
  "topics": ["topic1", "topic2", ...],
  "department": "HR"
}}"""


class DocumentSummarizer:
    def __init__(self):
        genai.configure(api_key=settings.gemini_api_key)
        self.model = genai.GenerativeModel("gemini-1.5-flash")

    async def summarize(self, text: str, title: str) -> Dict[str, Any]:
        """
        Generate summary, keywords, topics, and department for a document.
        """
        # Truncate text to avoid token limits (first ~3000 chars)
        truncated_text = text[:3000]

        prompt = SUMMARY_PROMPT.format(title=title, text=truncated_text)

        try:
            response = await asyncio.to_thread(
                self.model.generate_content,
                prompt,
                generation_config=genai.GenerationConfig(
                    temperature=0.2,
                    max_output_tokens=500,
                ),
            )

            text_response = response.text.strip()
            # Extract JSON
            start = text_response.find("{")
            end = text_response.rfind("}") + 1
            if start >= 0 and end > start:
                result = json.loads(text_response[start:end])
                logger.info(f"Summarized: '{title}' → dept: {result.get('department')}")
                return result

        except Exception as e:
            logger.error(f"Summarization failed for '{title}': {e}")

        return {
            "summary": f"Document: {title}",
            "keywords": [],
            "topics": [],
            "department": "General",
        }
