"""
Shared answer-extraction: where a result becomes an ANSWER line, imported
identically by all 3 arms. A model does the reading, so ANSWER-vs-rows
divergence is real interpretation failure, not a formatting artifact.
"""

from bench.grader import parse_answer

EXTRACTION_SYSTEM = (
    "You are given a question and the rows a SQL query returned.\n"
    "Report the answer the rows contain, then stop.\n"
    "\n"
    "Respond with exactly one line, nothing else:\n"
    "ANSWER: <json>\n"
    "\n"
    "Format rules for <json>:\n"
    "- Always valid JSON.\n"
    "- A single value: the bare value, e.g. ANSWER: 5 or ANSWER: \"France\"\n"
    "- One row with multiple columns: a JSON array, e.g. ANSWER: [\"France\", 5]\n"
    "- Multiple rows: an array of arrays, e.g. ANSWER: [[\"France\"], [\"Spain\"]]\n"
    "- A missing/empty value is JSON null, never the string \"Null\" or \"None\".\n"
    "- Keep the column order the question implies; do not sort or relabel.\n"
    "- No prose, no markdown, no code fences, no trailing semicolon.\n"
)


def extract_prompt(question: str, rows: list) -> str:
    """
    The user-turn content for the extraction call. rows is the model-facing
    (already row-capped) view. extraction reads what the loop shows it, so a
    truncated view can itself cause an interpretation failure, which is a finding.
    """
    return f"Question: {question}\n\nRows: {rows}\n\nANSWER:"
