# Pipeline Migration Progress

Track the tasks completed during the migration of the RAG pipeline to the new advanced version running entirely on Gemini.

## Completed
- Move `new_rag_pipeline` into `backend/app/services/rag_agent`

## In Progress
- Refactoring the pipeline to use the Gemini API instead of Ollama

## Upcoming
- Integrate new `RAGAgent` into `/query` chat route
- Integrate new `RAGAgent` into `/upload` document route
- Remove old pipeline code
- Verification and testing
