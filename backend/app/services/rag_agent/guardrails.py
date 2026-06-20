"""
DRDO-specific input guardrails and dynamic router for the RAG pipeline.

Decides whether a query should be:
  1. BLOCKED (off-topic, harmful)
  2. RAG (requires internal PDF knowledge base)
  3. LLM_ONLY (general knowledge, basic math, facts)

Uses a 3-layer approach:
  Layer 1 — BLOCKLIST: Fast regex/string matching for explicitly blocked patterns.
  Layer 2 — KEYWORD MATCH: If query strongly matches ingested PDF keywords, route to RAG.
  Layer 3 — LLM ROUTER: Ask Gemini to make the final decision.
"""

import logging
from typing import List, Tuple
import google.generativeai as genai

logger = logging.getLogger(__name__)

# =========================================================================
# STATIC BLOCKLIST
# =========================================================================

BLOCKED_PATTERNS: List[str] = [
    # Entertainment / creative writing
    "tell me a joke", "tell me a funny", "write a poem", "write me a poem",
    "write a song", "write me a story", "write a story", "make me laugh", "entertain me",
    # Movie / TV / streaming
    "movie recommendation", "recommend a movie", "best movies", "netflix", "amazon prime",
    "disney+", "hotstar",
    # Social media
    "instagram", "facebook", "twitter", "tiktok", "snapchat", "reddit", "youtube", "whatsapp",
    # Personal / relationship
    "relationship advice", "dating tips", "love advice", "girlfriend", "boyfriend",
    # Food & lifestyle
    "recipe for", "how to cook", "best restaurant", "what to eat", "diet plan",
    # Sports / gaming
    "ipl", "cricket score", "football score", "gaming tips", "how to play fortnite", "pubg",
    # explicit security exploits
    "how to bypass security", "crack the password", "how to phish", "malware tutorial", "ransomware tutorial",
]

REJECTION_MESSAGE = (
    "❌ Your query is outside the scope of this system.\n\n"
    "This assistant is designed to answer questions related to:\n"
    "  • Internal Knowledge Base (DRDO, Defence, Legal)\n"
    "  • General Knowledge and Facts\n\n"
    "Please refrain from asking about entertainment, recipes, or unsafe topics."
)

# =========================================================================
# LLM ROUTER PROMPT
# =========================================================================

ROUTER_PROMPT = """You are an intelligent router for an AI assistant.
Your task is to classify the user's query into one of three categories: [BLOCK, LLM, RAG].

CATEGORIES:
1. BLOCK: The query is inappropriate, toxic, highly offensive, or asks for a joke/creative story.
2. RAG: The query asks for specific organizational details, policies, internal documents, or matches the following knowledge-base keywords: {keywords}
3. LLM: The query asks about general world knowledge, basic math, code generation, summarization of a generic concept, or things that do not require internal specific documents.

Output ONLY the category name (BLOCK, LLM, or RAG). Do not output any explanation.

User Query:
{query}
"""

def route_query(
    query: str, 
    stored_keywords: List[str], 
    gemini_api_key: str, 
    model_name: str = "gemini-1.5-flash"
) -> Tuple[str, str]:
    """Route the query to the appropriate system.

    Returns:
        Tuple of (route_name, message_or_query).
        Routes can be "BLOCK", "LLM", or "RAG".
    """
    query_lower = query.lower().strip()

    if not query_lower:
        return "BLOCK", "Query cannot be empty. Please enter your question."

    # ---- Layer 1: Off-topic blocklist ------------------------------------
    for pattern in BLOCKED_PATTERNS:
        if pattern in query_lower:
            logger.warning("Query blocked by static guardrail — pattern: '%s'", pattern)
            return "BLOCK", REJECTION_MESSAGE

    # ---- Layer 2: Fast Keyword Match (Optional shortcut) -----------------
    top_keywords_str = ", ".join(stored_keywords[:50]) if stored_keywords else "None"

    # ---- Layer 3: LLM Router ---------------------------------------------
    try:
        genai.configure(api_key=gemini_api_key)
        model = genai.GenerativeModel(model_name)
        
        prompt = ROUTER_PROMPT.format(keywords=top_keywords_str, query=query)

        response = model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(
                temperature=0,
                max_output_tokens=10
            )
        )
        decision = response.text.strip().upper()
        
        if "BLOCK" in decision:
            return "BLOCK", REJECTION_MESSAGE
        elif "LLM" in decision:
            logger.info("Router decision: LLM (General Knowledge)")
            return "LLM", query
        elif "RAG" in decision:
            logger.info("Router decision: RAG (Internal Knowledge Base)")
            return "RAG", query
        else:
            logger.warning("Router returned unexpected decision: '%s'. Defaulting to RAG.", decision)
            return "RAG", query

    except Exception as exc:
        logger.error("LLM Router failed (%s) — Defaulting to RAG pipeline.", exc)
        return "RAG", query
