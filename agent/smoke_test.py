"""
Smoke test. Establish Project 1 adapter loads
and generates one SQL query
"""

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from peft import PeftModel

BASE = "Qwen/Qwen2.5-Coder-1.5B-Instruct"
ADAPTER = "/home/SeanUbuntu/Github/text2sql/adapters/qlora-r16-1ep-canonical"

bnb = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.bfloat16,
)

tok = AutoTokenizer.from_pretrained(BASE)
model = AutoModelForCausalLM.from_pretrained(BASE, quantization_config=bnb, device_map="auto")
model = PeftModel.from_pretrained(model, ADAPTER)
model.eval()

SYSTEM = (
    "You are an expert data analyst who writes SQLite SQL."
    "Given a database schema and a question, reply with a single SQL query that "
    "answers it. Output only the SQL: no explanation, no markdown, no comments."
)

question = "How many singers are there?"
schema = "CREATE TABLE singer (singer_id INT, name TEXT, country TEXT, age INT);"

messages = [
    {"role": "system", "content": SYSTEM},
    {"role": "user", "content": f"Schema:\n{schema}\n\nQuestion: {question}\nSQL:"},
]

prompt = tok.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
inputs = tok(prompt, return_tensors="pt").to(model.device)
with torch.no_grad():
    out = model.generate(**inputs, max_new_tokens=128, do_sample=False)
print(tok.decode(out[0][inputs.input_ids.shape[1]:], skip_special_tokens=True))
