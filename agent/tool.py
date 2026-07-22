"""
generate_sql() tool: the fine-tuned Qwen adapter as a function, question in,
SQL out. Three study invariants are enforced here, structurally, so it can't
be ignored the  way a prompt instruction can:

    - No authorship: the id is bound to the exact SQL string emitted; verify()
      checks identity and content, so the orchestrator can neither run untagged
      SQL nor edit-and-resubmit the tool's SQL under the same id
    - Input contract: repair context arrives only as (previous_sql, executor_error),
      both or neither
    - Seed: applied immediately before generate, the one place RNG is touched, so
      config's arm-independent seeding holds at generation time
"""

from __future__ import annotations

import uuid
import sys
from pathlib import Path
from typing import Callable, Optional

import torch
from peft import PeftModel
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    set_seed,
)

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "vendor"))

from agent.config import CONFIG, derive_seed
from paths import ADAPTER_DIR
from prompt_utils import build_messages

BASE_MODEL_ID = "Qwen/Qwen2.5-Coder-1.5B-Instruct"

RunQuery = Callable[[str, str], tuple]


class Tool:
    def __init__(self, run_query: RunQuery, adapter_dir=ADAPTER_DIR):
        self._run_query = run_query          # read-only, schema introspection only
        self._registry: dict[str, str] = {} # tool_output_id -> exact SQL, for verify()

        self._tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL_ID)
        if self._tokenizer.pad_token is None:
            self._tokenizer.pad_token = self._tokenizer.eos_token

        # Reproduce training's 4-bit config since the adapter was learned
        # against these quantized weights
        bnb = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_use_double_quant=True,
            bnb_4bit_compute_dtype=torch.bfloat16,
        )
        base = AutoModelForCausalLM.from_pretrained(
            BASE_MODEL_ID,
            quantization_config=bnb,
            dtype=torch.bfloat16,
            device_map={"": 0},
        )
        self._model = PeftModel.from_pretrained(base, str(adapter_dir))
        self._model.eval()
        self._device = next(self._model.parameters()).device


    def generate_sql(
        self,
        task_id: str,
        db_id: str,
        question: str,
        run_idx: int,
        attempt_idx: int,
        previous_sql: Optional[str] = None,
        executor_error: Optional[str] = None,
    ) -> dict:
        if (previous_sql is None) != (executor_error is None):
            raise ValueError(
                "repair context is both or neither: pass previous_sql and executor_error together"
            )
        
        error_truncated = False
        if previous_sql is not None:
            error_text, error_truncated = _truncate_error(executor_error)
            question = _repair_question(question, previous_sql, error_text)
        messages = build_messages(self._run_query, db_id, question, few_shots=[])

        prompt = self._tokenizer.apply_chat_template(
            messages, add_generation_prompt=True, tokenize=False
        )
        inputs = self._tokenizer(prompt, return_tensors="pt").to(self._device)

        set_seed(derive_seed(task_id, run_idx, attempt_idx))
        with torch.inference_mode():
            out = self._model.generate(
                **inputs,
                do_sample=True,
                temperature=CONFIG["tool"]["temperature"],
                top_p=CONFIG["tool"]["top_p"],
                max_new_tokens=CONFIG["tool"]["max_new_tokens"],
                pad_token_id=self._tokenizer.pad_token_id,
            )

        gen = out[0][inputs["input_ids"].shape[1]:]
        sql = _strip_fence(self._tokenizer.decode(gen, skip_special_tokens=True))

        tool_output_id = uuid.uuid4().hex
        self._registry[tool_output_id] = sql
        return {"sql": sql, "tool_output_id": tool_output_id, "prompt": prompt, "error_truncated": error_truncated}


    def verify(self, tool_output_id: str, sql: str) -> bool:
        return self._registry.get(tool_output_id) == sql


def _strip_fence(text: str) -> str:
    # Training completions are bare SQL; this only catches an occasional stray fence
    t = text.strip()
    if t.startswith("```"):
        nl = t.find("\n")
        t = t[nl + 1:] if nl != -1 else ""
        if t.rstrip().endswith("```"):
            t = t.rstrip()[:-3]
    return t.strip()


def _repair_question(question: str, previous_sql: str, error_text: str) -> str:
    """
    Repair context rides in the question slot rather than extra chat turns. The
    adapter trained on a single zero-shot user turn (build_prompt_completion ->
    few_shots=[]), so appending assistant/user turns changes the block structure
    the weights were tuned on. Question stays first so attempt 0 and repair
    attempts share the longest identical prefix. No trailing SQL: cue here,
    _user_turn supplies it.
    """

    return (
        f"{question}\n\n"
        f"Previous query:\n{previous_sql}\n"
        f"Error:\n{error_text}\n"
        "Write a single corrected SQL query that answers the question."
    )


def _truncate_error(error_text: str) -> tuple[str, bool]:
    # Head-truncate: sqlite puts the diagnostic first, so the tail is the
    # expendable part. Flag rides into the trace as a candidate explanation
    # if repair underperforms.
    cap = CONFIG["repair"]["max_error_chars"]
    if len(error_text) <= cap:
        return error_text, False
    return error_text[:cap] + " ...[truncated]", True

