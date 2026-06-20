"""
RAG pipeline accuracy evaluation.

Provides tools to evaluate RAG answers against a ground-truth dataset,
compute accuracy metrics (containment, token overlap, LLM-as-judge,
retrieval accuracy), and store historical results for trend tracking.
"""

import csv
import json
import logging
import re
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Default mapping from dataset document labels → PDF filenames in vectorstore
# Update this dict to match your actual filenames.
# ---------------------------------------------------------------------------
DEFAULT_DOC_NAME_MAP: Dict[str, List[str]] = {
    # Dataset label → list of possible filename substrings (case-insensitive)
    "DPDP Act 2023": ["dpdp", "digital_personal_data_protection"],
    "IT Act 2000": ["itact", "it_act", "it-act"],
    "Income Tax Act 2025": ["incometax", "income_tax", "income-tax"],
    "Finance Act 2026": ["financeact", "finance_act", "finance-act"],
    "Multiple Documents": [],  # cross-doc questions — no single expected source
}

# ---------------------------------------------------------------------------
# Data containers
# ---------------------------------------------------------------------------

@dataclass
class QuestionResult:
    """Result for a single evaluated question."""

    id: int
    question: str
    ground_truth: str
    rag_answer: str
    document: str
    difficulty: str
    answer_type: str

    # Keyword / token metrics
    contains_exact: bool = False
    token_overlap: float = 0.0

    # LLM-as-judge
    llm_score: Optional[int] = None  # 0-3
    llm_reasoning: Optional[str] = None

    # Retrieval
    retrieval_hit: bool = False
    retrieved_sources: List[str] = field(default_factory=list)

    # Timing
    query_time_seconds: float = 0.0


@dataclass
class EvalReport:
    """Full evaluation report for a test run."""

    run_id: str
    timestamp: str
    dataset_path: str
    total_questions: int
    config: Dict[str, Any]
    vectorstore_info: Dict[str, Any]
    runtime_seconds: float

    # Aggregate metrics
    overall: Dict[str, float] = field(default_factory=dict)
    by_document: Dict[str, Dict[str, float]] = field(default_factory=dict)
    by_difficulty: Dict[str, Dict[str, float]] = field(default_factory=dict)

    # Per-question details (stored separately in the details file)
    question_results: List[QuestionResult] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Dataset loading
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Column aliases: maps canonical names → possible CSV column names
# This lets us support both the old schema and the new evaluation dataset.
# ---------------------------------------------------------------------------
_COLUMN_ALIASES: Dict[str, List[str]] = {
    "ID":                 ["ID", "id", "#", "No", "Sr"],
    "Question":           ["Question", "question", "query", "Query"],
    "Ground_Truth_Answer": ["Ground_Truth_Answer", "ground_truth", "answer",
                            "Ground Truth Answer", "GroundTruth"],
    "Document":           ["Document", "document", "source_document",
                           "source", "Source Document"],
    "Difficulty":         ["Difficulty", "difficulty"],
    "Answer_Type":        ["Answer_Type", "question_type", "type",
                           "answer_type", "Type"],
}


def _resolve_columns(fieldnames: List[str]) -> Dict[str, str]:
    """Resolve actual CSV column names to canonical names.

    Returns a dict mapping canonical_name → actual_csv_column.
    Raises ValueError if a required canonical column cannot be resolved.
    """
    resolved: Dict[str, str] = {}
    for canonical, aliases in _COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in fieldnames:
                resolved[canonical] = alias
                break
    missing = set(_COLUMN_ALIASES.keys()) - {"ID"} - set(resolved.keys())
    if missing:
        raise ValueError(
            f"Dataset is missing required columns: {missing}.\n"
            f"Found columns: {fieldnames}\n"
            f"Supported aliases: {_COLUMN_ALIASES}"
        )
    return resolved


def load_dataset(csv_path: str) -> List[Dict[str, str]]:
    """Load and validate the evaluation dataset from a CSV file.

    Supports two column name formats:
      - New  : query, ground_truth, source_document, difficulty, question_type
      - Legacy: ID, Question, Ground_Truth_Answer, Document, Difficulty, Answer_Type

    All rows are normalised to use the canonical (legacy) column names so
    the rest of the evaluator works without any changes.

    Args:
        csv_path: Path to the CSV file.

    Returns:
        List of row dicts with canonical column names.

    Raises:
        FileNotFoundError: If csv_path does not exist.
        ValueError: If required columns are missing.
    """
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"Dataset not found: {path}")

    rows: List[Dict[str, str]] = []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError("CSV file appears to be empty")

        # Normalise header whitespace
        reader.fieldnames = [h.strip() for h in reader.fieldnames]

        # Resolve column aliases → canonical names
        col_map = _resolve_columns(list(reader.fieldnames))

        for row_idx, row in enumerate(reader):
            norm = {k.strip(): v.strip() for k, v in row.items()}

            # Build a row dict with canonical keys
            canonical_row: Dict[str, str] = {}
            for canonical, actual in col_map.items():
                canonical_row[canonical] = norm.get(actual, "")

            # Synthesise an ID if absent from the CSV
            if "ID" not in col_map:
                canonical_row["ID"] = str(row_idx + 1)

            rows.append(canonical_row)

    logger.info("Loaded dataset with %d questions from %s", len(rows), path)
    return rows


# ---------------------------------------------------------------------------
# Answer evaluation — keyword / token methods
# ---------------------------------------------------------------------------

def _normalise(text: str) -> str:
    """Lower-case, collapse whitespace, strip punctuation for comparison."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text


def evaluate_answer(rag_answer: str, ground_truth: str) -> Dict[str, Any]:
    """Evaluate a RAG answer against ground truth using text metrics.

    Returns:
        Dictionary with:
            - contains_exact (bool): ground truth appears in RAG answer
            - token_overlap (float): Jaccard similarity of word tokens
    """
    norm_answer = _normalise(rag_answer)
    norm_truth = _normalise(ground_truth)

    # Containment check
    contains_exact = norm_truth in norm_answer

    # Token overlap (Jaccard)
    answer_tokens = set(norm_answer.split())
    truth_tokens = set(norm_truth.split())

    if not truth_tokens:
        token_overlap = 0.0
    else:
        intersection = answer_tokens & truth_tokens
        union = answer_tokens | truth_tokens
        token_overlap = len(intersection) / len(union) if union else 0.0

    return {
        "contains_exact": contains_exact,
        "token_overlap": round(token_overlap, 4),
    }


# ---------------------------------------------------------------------------
# Answer evaluation — LLM-as-judge
# ---------------------------------------------------------------------------

LLM_JUDGE_PROMPT = """You are an impartial evaluator. Given a question, a ground truth answer, and a candidate answer from a RAG system, score the candidate answer's correctness.

Score on this scale:
0 = Completely wrong or irrelevant
1 = Partially correct — mentions related concepts but key facts are wrong or missing
2 = Mostly correct — captures the main idea but has minor inaccuracies or omissions
3 = Fully correct — semantically matches the ground truth

Question: {question}

Ground Truth Answer: {ground_truth}

Candidate (RAG) Answer: {rag_answer}

Respond with ONLY a JSON object in this exact format (no other text):
{{"score": <0-3>, "reasoning": "<brief explanation>"}}"""


def evaluate_answer_llm(
    ollama_base_url: str,
    model_name: str,
    question: str,
    rag_answer: str,
    ground_truth: str,
) -> Dict[str, Any]:
    """Use a local Ollama LLM to judge answer correctness on a 0-3 scale.

    Args:
        ollama_base_url: Ollama server URL (e.g. 'http://localhost:11434').
        model_name: Ollama model name (e.g. 'llama3.2', 'mistral').
        question: Original question.
        rag_answer: RAG-generated answer.
        ground_truth: Expected correct answer.

    Returns:
        Dictionary with 'llm_score' (int) and 'llm_reasoning' (str).
    """
    from langchain_ollama import ChatOllama  # local import to avoid circular imports

    prompt = LLM_JUDGE_PROMPT.format(
        question=question,
        ground_truth=ground_truth,
        rag_answer=rag_answer[:1500],  # truncate very long answers
    )

    try:
        llm = ChatOllama(
            model=model_name,
            base_url=ollama_base_url,
            temperature=0,
        )
        response = llm.invoke(prompt)
        content = response.content.strip()

        # Try to parse JSON from the response
        json_match = re.search(r"\{[^}]+\}", content, re.DOTALL)
        if json_match:
            parsed = json.loads(json_match.group())
            score = int(parsed.get("score", 0))
            score = max(0, min(3, score))  # clamp to 0-3
            reasoning = parsed.get("reasoning", "")
            return {"llm_score": score, "llm_reasoning": reasoning}

        logger.warning("Could not parse LLM judge response: %s", content[:200])
        return {"llm_score": None, "llm_reasoning": f"Parse error: {content[:200]}"}

    except Exception as e:
        logger.error("LLM judge evaluation failed: %s", e)
        return {"llm_score": None, "llm_reasoning": f"Error: {e}"}


# ---------------------------------------------------------------------------
# Retrieval evaluation
# ---------------------------------------------------------------------------

def evaluate_retrieval(
    sources: List[Dict[str, Any]],
    expected_document: str,
    doc_name_map: Optional[Dict[str, List[str]]] = None,
) -> Dict[str, Any]:
    """Check if the retriever pulled docs from the correct source file.

    Args:
        sources: List of source dicts from RAGAgent.query() result.
        expected_document: Document label from the dataset (e.g. "DPDP Act 2023").
        doc_name_map: Mapping from dataset labels to filename substrings.

    Returns:
        Dictionary with 'retrieval_hit' (bool) and 'retrieved_sources' (list).
    """
    name_map = doc_name_map or DEFAULT_DOC_NAME_MAP

    retrieved_filenames = [
        s.get("source", "").lower() for s in sources
    ]

    # Get expected filename substrings
    expected_substrings = name_map.get(expected_document, [])
    if not expected_substrings:
        # Fallback: use the document label itself as a substring
        expected_substrings = [expected_document.lower().replace(" ", "")]

    # Check if any retrieved source matches any expected substring
    retrieval_hit = False
    for filename in retrieved_filenames:
        for substring in expected_substrings:
            if substring.lower() in filename:
                retrieval_hit = True
                break
        if retrieval_hit:
            break

    return {
        "retrieval_hit": retrieval_hit,
        "retrieved_sources": [s.get("source", "unknown") for s in sources],
    }


# ---------------------------------------------------------------------------
# Aggregation helpers
# ---------------------------------------------------------------------------

def _compute_group_metrics(
    results: List[QuestionResult],
    include_llm: bool = True,
) -> Dict[str, Any]:
    """Compute aggregate metrics for a group of question results."""
    total = len(results)
    if total == 0:
        return {}

    containment_hits = sum(1 for r in results if r.contains_exact)
    avg_token_overlap = sum(r.token_overlap for r in results) / total
    retrieval_hits = sum(1 for r in results if r.retrieval_hit)

    metrics: Dict[str, Any] = {
        "total_questions": total,
        "containment_accuracy": round(containment_hits / total, 4),
        "avg_token_overlap": round(avg_token_overlap, 4),
        "retrieval_accuracy": round(retrieval_hits / total, 4),
    }

    if include_llm:
        scored = [r for r in results if r.llm_score is not None]
        if scored:
            avg_llm = sum(r.llm_score for r in scored) / len(scored)
            metrics["avg_llm_score"] = round(avg_llm, 4)
            # % that scored 2 or 3 (mostly/fully correct)
            acceptable = sum(1 for r in scored if r.llm_score >= 2)
            metrics["llm_acceptable_rate"] = round(acceptable / len(scored), 4)
        else:
            metrics["avg_llm_score"] = None
            metrics["llm_acceptable_rate"] = None

    return metrics


# ---------------------------------------------------------------------------
# Main evaluation orchestrator
# ---------------------------------------------------------------------------

def run_evaluation(
    agent,
    dataset_path: str,
    use_llm_judge: bool = True,
    doc_name_map: Optional[Dict[str, List[str]]] = None,
    progress_callback=None,
) -> EvalReport:
    """Run a full accuracy evaluation of the RAG pipeline.

    Args:
        agent: Initialized RAGAgent instance.
        dataset_path: Path to the evaluation CSV.
        use_llm_judge: Whether to run LLM-as-judge scoring.
        doc_name_map: Optional document name mapping override.
        progress_callback: Optional callable(current, total, question) for
            progress updates.

    Returns:
        EvalReport with all metrics and per-question details.
    """
    start_time = time.time()
    now = datetime.now().astimezone()
    run_id = f"eval_{now.strftime('%Y%m%d_%H%M%S')}"

    logger.info("Starting evaluation run: %s", run_id)

    # Load dataset
    dataset = load_dataset(dataset_path)
    total = len(dataset)

    # Gather config info
    config_info = {
        "llm_model": agent.config.local_model_name,
        "embed_model": agent.config.embed_model_name,
        "top_k": agent.config.top_k_context,
        "score_threshold": agent.config.retriever_score_threshold,
        "temperature": agent.config.llm_temperature,
    }

    vs_info = {}
    if agent.is_ready:
        from app.services.rag_agent.vectorstore import get_vectorstore_info
        vs_info = get_vectorstore_info(agent._vectorstore)

    # Evaluate each question
    results: List[QuestionResult] = []

    for i, row in enumerate(dataset):
        qid = int(row.get("ID", i + 1))
        question = row["Question"]
        ground_truth = row["Ground_Truth_Answer"]
        document = row["Document"]
        difficulty = row["Difficulty"]
        answer_type = row["Answer_Type"]

        if progress_callback:
            progress_callback(i + 1, total, question)

        logger.info("[%d/%d] Evaluating: %s", i + 1, total, question[:80])

        # Query the RAG agent
        q_start = time.time()
        try:
            query_result = agent.query(question)
            rag_answer = query_result["answer"]
            sources = query_result.get("sources", [])
        except Exception as e:
            logger.error("Query failed for Q%d: %s", qid, e)
            rag_answer = f"[ERROR] {e}"
            sources = []
        q_time = time.time() - q_start

        # Text-based evaluation
        text_eval = evaluate_answer(rag_answer, ground_truth)

        # Retrieval evaluation
        ret_eval = evaluate_retrieval(sources, document, doc_name_map)

        # LLM-as-judge (uses local Ollama model — no rate limits!)
        llm_eval = {"llm_score": None, "llm_reasoning": None}
        if use_llm_judge:
            llm_eval = evaluate_answer_llm(
                ollama_base_url=agent.config.ollama_base_url,
                model_name=agent.config.local_model_name,
                question=question,
                rag_answer=rag_answer,
                ground_truth=ground_truth,
            )

        result = QuestionResult(
            id=qid,
            question=question,
            ground_truth=ground_truth,
            rag_answer=rag_answer,
            document=document,
            difficulty=difficulty,
            answer_type=answer_type,
            contains_exact=text_eval["contains_exact"],
            token_overlap=text_eval["token_overlap"],
            llm_score=llm_eval.get("llm_score"),
            llm_reasoning=llm_eval.get("llm_reasoning"),
            retrieval_hit=ret_eval["retrieval_hit"],
            retrieved_sources=ret_eval["retrieved_sources"],
            query_time_seconds=round(q_time, 2),
        )
        results.append(result)

    runtime = round(time.time() - start_time, 2)

    # Compute aggregates
    include_llm = use_llm_judge
    overall = _compute_group_metrics(results, include_llm)

    by_document: Dict[str, Dict] = {}
    by_difficulty: Dict[str, Dict] = {}

    doc_groups: Dict[str, List[QuestionResult]] = {}
    diff_groups: Dict[str, List[QuestionResult]] = {}

    for r in results:
        doc_groups.setdefault(r.document, []).append(r)
        diff_groups.setdefault(r.difficulty, []).append(r)

    for doc, group in sorted(doc_groups.items()):
        by_document[doc] = _compute_group_metrics(group, include_llm)

    for diff, group in sorted(diff_groups.items(),
                               key=lambda x: {"Easy": 0, "Medium": 1, "Hard": 2}.get(x[0], 3)):
        by_difficulty[diff] = _compute_group_metrics(group, include_llm)

    report = EvalReport(
        run_id=run_id,
        timestamp=now.isoformat(),
        dataset_path=str(dataset_path),
        total_questions=total,
        config=config_info,
        vectorstore_info=vs_info,
        runtime_seconds=runtime,
        overall=overall,
        by_document=by_document,
        by_difficulty=by_difficulty,
        question_results=results,
    )

    logger.info(
        "Evaluation complete: %d questions in %.1fs — "
        "containment=%.1f%%, retrieval=%.1f%%",
        total, runtime,
        overall.get("containment_accuracy", 0) * 100,
        overall.get("retrieval_accuracy", 0) * 100,
    )

    return report


# ---------------------------------------------------------------------------
# History persistence
# ---------------------------------------------------------------------------

EVAL_HISTORY_DIR = Path("eval_history")


def save_eval_history(report: EvalReport) -> Tuple[Path, Path]:
    """Save evaluation results to the history directory.

    Creates two files:
        - history.json: append-only summary (one entry per run)
        - <run_id>_details.json: per-question details for this run

    Args:
        report: Completed EvalReport.

    Returns:
        Tuple of (summary_path, details_path).
    """
    EVAL_HISTORY_DIR.mkdir(parents=True, exist_ok=True)

    # --- Summary entry (everything except per-question details) ---
    summary_entry = {
        "run_id": report.run_id,
        "timestamp": report.timestamp,
        "dataset_path": report.dataset_path,
        "total_questions": report.total_questions,
        "config": report.config,
        "vectorstore_info": report.vectorstore_info,
        "runtime_seconds": report.runtime_seconds,
        "overall": report.overall,
        "by_document": report.by_document,
        "by_difficulty": report.by_difficulty,
    }

    summary_path = EVAL_HISTORY_DIR / "history.json"
    if summary_path.exists():
        with open(summary_path, "r", encoding="utf-8") as f:
            history = json.load(f)
    else:
        history = []

    history.append(summary_entry)

    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)

    # --- Detailed per-question results ---
    details = []
    for r in report.question_results:
        details.append({
            "id": r.id,
            "question": r.question,
            "ground_truth": r.ground_truth,
            "rag_answer": r.rag_answer,
            "document": r.document,
            "difficulty": r.difficulty,
            "answer_type": r.answer_type,
            "contains_exact": r.contains_exact,
            "token_overlap": r.token_overlap,
            "llm_score": r.llm_score,
            "llm_reasoning": r.llm_reasoning,
            "retrieval_hit": r.retrieval_hit,
            "retrieved_sources": r.retrieved_sources,
            "query_time_seconds": r.query_time_seconds,
        })

    details_path = EVAL_HISTORY_DIR / f"{report.run_id}_details.json"
    with open(details_path, "w", encoding="utf-8") as f:
        json.dump(details, f, indent=2, ensure_ascii=False)

    logger.info("Saved evaluation history to %s", EVAL_HISTORY_DIR)
    return summary_path, details_path


def load_eval_history() -> List[Dict[str, Any]]:
    """Load all historical evaluation summaries.

    Returns:
        List of summary dicts, oldest first.
    """
    summary_path = EVAL_HISTORY_DIR / "history.json"
    if not summary_path.exists():
        return []

    with open(summary_path, "r", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Report formatting (terminal output)
# ---------------------------------------------------------------------------

def format_report(report: EvalReport) -> str:
    """Format an EvalReport as a human-readable terminal string."""
    lines: List[str] = []
    o = report.overall

    lines.append("")
    lines.append("=" * 70)
    lines.append("  RAG PIPELINE ACCURACY REPORT")
    lines.append("=" * 70)
    lines.append(f"  Run ID      : {report.run_id}")
    lines.append(f"  Timestamp   : {report.timestamp}")
    lines.append(f"  Dataset     : {report.dataset_path}")
    lines.append(f"  Questions   : {report.total_questions}")
    lines.append(f"  Runtime     : {report.runtime_seconds:.1f}s")
    lines.append(f"  LLM Model   : {report.config.get('llm_model', 'N/A')}")
    lines.append(f"  Embed Model : {report.config.get('embed_model', 'N/A')}")
    if report.vectorstore_info:
        lines.append(f"  Vectors     : {report.vectorstore_info.get('total_vectors', 'N/A')}")

    # Overall metrics
    lines.append("")
    lines.append("-" * 70)
    lines.append("  OVERALL METRICS")
    lines.append("-" * 70)
    lines.append(f"  Containment Accuracy : {o.get('containment_accuracy', 0) * 100:6.1f}%")
    lines.append(f"  Avg Token Overlap    : {o.get('avg_token_overlap', 0) * 100:6.1f}%")
    lines.append(f"  Retrieval Accuracy   : {o.get('retrieval_accuracy', 0) * 100:6.1f}%")
    if o.get("avg_llm_score") is not None:
        lines.append(f"  Avg LLM Score (0-3)  : {o['avg_llm_score']:6.2f}")
        lines.append(f"  LLM Acceptable (≥2)  : {o.get('llm_acceptable_rate', 0) * 100:6.1f}%")

    # Per-document table
    lines.append("")
    lines.append("-" * 70)
    lines.append("  ACCURACY BY DOCUMENT")
    lines.append("-" * 70)

    header = f"  {'Document':<28} {'Qs':>4} {'Contain':>8} {'Overlap':>8} {'Retriev':>8}"
    if o.get("avg_llm_score") is not None:
        header += f" {'LLM':>6}"
    lines.append(header)
    lines.append("  " + "-" * (len(header) - 2))

    for doc, m in report.by_document.items():
        row = (
            f"  {doc:<28} {m['total_questions']:>4} "
            f"{m['containment_accuracy'] * 100:>7.1f}% "
            f"{m['avg_token_overlap'] * 100:>7.1f}% "
            f"{m['retrieval_accuracy'] * 100:>7.1f}%"
        )
        if m.get("avg_llm_score") is not None:
            row += f" {m['avg_llm_score']:>5.2f}"
        lines.append(row)

    # Per-difficulty table
    lines.append("")
    lines.append("-" * 70)
    lines.append("  ACCURACY BY DIFFICULTY")
    lines.append("-" * 70)

    lines.append(header.replace("Document", "Difficulty"))
    lines.append("  " + "-" * (len(header) - 2))

    for diff, m in report.by_difficulty.items():
        row = (
            f"  {diff:<28} {m['total_questions']:>4} "
            f"{m['containment_accuracy'] * 100:>7.1f}% "
            f"{m['avg_token_overlap'] * 100:>7.1f}% "
            f"{m['retrieval_accuracy'] * 100:>7.1f}%"
        )
        if m.get("avg_llm_score") is not None:
            row += f" {m['avg_llm_score']:>5.2f}"
        lines.append(row)

    # Worst performers (lowest token overlap)
    lines.append("")
    lines.append("-" * 70)
    lines.append("  WORST PERFORMING QUESTIONS (Bottom 10 by token overlap)")
    lines.append("-" * 70)

    sorted_results = sorted(report.question_results, key=lambda r: r.token_overlap)
    for r in sorted_results[:10]:
        llm_tag = f"LLM={r.llm_score}" if r.llm_score is not None else ""
        lines.append(
            f"  Q{r.id:<4} overlap={r.token_overlap:.2f}  "
            f"contain={'✓' if r.contains_exact else '✗'}  "
            f"retriev={'✓' if r.retrieval_hit else '✗'}  "
            f"{llm_tag}"
        )
        lines.append(f"        {r.question[:65]}")

    lines.append("")
    lines.append("=" * 70)
    lines.append("")

    return "\n".join(lines)


def format_history(history: List[Dict[str, Any]]) -> str:
    """Format historical eval summaries as a table."""
    if not history:
        return "No evaluation history found. Run an evaluation first."

    lines: List[str] = []
    lines.append("")
    lines.append("=" * 90)
    lines.append("  EVALUATION HISTORY")
    lines.append("=" * 90)
    lines.append(
        f"  {'#':>3}  {'Run ID':<25} {'Questions':>9} "
        f"{'Contain':>8} {'Overlap':>8} {'Retriev':>8} {'LLM':>6} {'Time':>7}"
    )
    lines.append("  " + "-" * 86)

    for i, entry in enumerate(history, 1):
        o = entry.get("overall", {})
        contain = o.get("containment_accuracy", 0) * 100
        overlap = o.get("avg_token_overlap", 0) * 100
        retrieval = o.get("retrieval_accuracy", 0) * 100
        llm = o.get("avg_llm_score")
        llm_str = f"{llm:.2f}" if llm is not None else "  —"
        runtime = entry.get("runtime_seconds", 0)

        lines.append(
            f"  {i:>3}  {entry['run_id']:<25} {entry['total_questions']:>9} "
            f"{contain:>7.1f}% {overlap:>7.1f}% {retrieval:>7.1f}% "
            f"{llm_str:>6} {runtime:>6.0f}s"
        )

    lines.append("")
    lines.append("=" * 90)
    lines.append("")

    return "\n".join(lines)
