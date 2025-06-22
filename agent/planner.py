import json
from pathlib import Path  
from typing import Any, Dict
import google.generativeai as genai
from .config import GEMINI_API_KEY
from .users import build_user_context

# task_schema and description copy-pasted once
with open(Path(__file__).parent / "task_schema.json") as f:
    task_schema = json.load(f)

description = (
    "The user will provide natural language requests for a variety of tasks. "
    "Your job is to analyze the request and generate a structured JSON response specifying which tasks to perform. "
    "These tasks include creating or reviewing Google Docs, Sheets, Calendar events, YouTube information, and Gmail operations. "
    "When assigned a task like creating a Google Doc or Sheet, perform any necessary research or reasoning to complete the task thoughtfully. For example: "
    "If the user requests a summary, short essay, list, or explanation, this should result in a structured response under the 'create_doc' task. "
    "If the task involves organizing or structuring data, it likely falls under 'create_sheet'. "
    "Only set 'run': true for tasks that are clearly implied by the user's intent. "
    "Make smart, context-aware decisions to ensure your structured output meaningfully matches the user's request. "
    "Your ultimate goal is to ensure that the plan you produce enables successful completion of the task with no ambiguity."
    "DO NOT create blanks when sending emails and ensure that the reciever of the email has a full coherent email. This means no blanks like [put your name here] or [starting here]"
)

def to_native(o: Any) -> Any:
    if hasattr(o, "items"):  return {k: to_native(v) for k, v in o.items()}
    if hasattr(o, "__iter__") and not isinstance(o, (str, bytes, bytearray)):
        return [to_native(v) for v in o]
    if hasattr(o, "value"):  return to_native(o.value)
    return o

def build_contact_prompt(book:Dict[str,str],limit=100)->str:
    return "Known contacts:\n" + "\n".join(
        f"{k} = {v}" for k,v in list(book.items())[:limit]) + "\n--- End contacts ---\n"

def _safe_task(block: Any, tmpl: Dict[str, Any]) -> Dict[str, Any]:
    if block is None: out = tmpl.copy(); out["run"] = False; return out
    out = tmpl.copy(); out.update(block); out.setdefault("run", False); return out

def plan_tasks(prompt:str,user_ctx:str,contacts:str)->Dict[str,Any]:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel(
        model_name="gemini-1.5-pro",
        tools=[{"function_declarations":[{
            "name":"interpret_user_task","description":description,
            "parameters":task_schema}]}]
    )
    resp = model.generate_content(
        contents=[
            {"role":"user","parts":[{"function_call":{"name":"interpret_user_task"}}]},
            {"role":"user","parts":[{"text":user_ctx+contacts}]},
            {"role":"user","parts":[{"text":prompt}]}
        ],
        tool_config={"function_calling_config":{"mode":"ANY"}}
    )
    args = to_native(resp.candidates[0].content.parts[0].function_call.args)

    # --- guarantee we always have something to speak -----------------
    if not args.get("assistant_response"):
        args["assistant_response"] = "All tasks completed."
    # -----------------------------------------------------------------

    return args
