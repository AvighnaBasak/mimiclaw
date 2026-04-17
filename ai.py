import json
import os
import requests
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
API_URL = "https://openrouter.ai/api/v1/chat/completions"
MODELS = [
    "google/gemma-4-31b-it:free",
    "qwen/qwen3-coder:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "deepseek/deepseek-r1-0528:free",
]
HEADERS = {
    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
    "Content-Type": "application/json",
    "HTTP-Referer": "https://mimiclaw.local",
    "X-Title": "MimiClaw",
}


class AIClient:
    def _call(self, messages: list, max_tokens: int = 2048) -> str:
        for model in MODELS:
            try:
                payload = {
                    "model": model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                }
                headers = {**HEADERS, "Authorization": f"Bearer {OPENROUTER_API_KEY}"}
                resp = requests.post(API_URL, headers=headers, json=payload, timeout=120)
                resp.raise_for_status()
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                if content and content.strip():
                    return content.strip()
            except Exception:
                continue
        raise RuntimeError("All AI models failed to respond.")

    def chat(self, user_message: str, history: list) -> str:
        messages = [
            {
                "role": "system",
                "content": (
                    "You are MimiClaw, a helpful personal AI assistant. "
                    "You help with schoolwork, answer questions, and keep the user organized. "
                    "Be concise, friendly, and accurate."
                ),
            }
        ]
        for h in history:
            messages.append({"role": h.role, "content": h.content})
        messages.append({"role": "user", "content": user_message})
        return self._call(messages, max_tokens=1024)

    def complete_assignment(self, assignment: dict, pdf_text: str | None = None) -> str:
        context_parts = [
            f"Course: {assignment.get('course_name', 'Unknown')}",
            f"Assignment Title: {assignment.get('title', 'Untitled')}",
            f"Assignment Description:\n{assignment.get('description', 'No description provided.')}",
        ]
        if pdf_text:
            context_parts.append(f"\nAttached PDF Content:\n{pdf_text}")

        prompt = "\n\n".join(context_parts)
        messages = [
            {
                "role": "system",
                "content": (
                    "You are an expert academic assistant. Your task is to write a complete, "
                    "well-structured, submittable academic response to the assignment provided. "
                    "Write as if you are the student. Be thorough, accurate, and appropriately formal. "
                    "Do not include meta-commentary about the assignment — only produce the actual work."
                ),
            },
            {"role": "user", "content": prompt},
        ]
        return self._call(messages, max_tokens=4096)

    def split_into_files(self, assignment: dict, completed_text: str) -> list[dict]:
        prompt = (
            f"Assignment Title: {assignment.get('title', '')}\n"
            f"Assignment Description: {assignment.get('description', '')}\n\n"
            f"Completed Work:\n{completed_text}\n\n"
            "Based on the assignment description and completed work above, determine if this should "
            "be split into multiple separate files (e.g. 'report AND bibliography', 'Part A, B, C'). "
            "Return ONLY valid JSON in this exact format with no extra text:\n"
            '{"files": [{"filename": "report.txt", "content": "...full content here..."}]}\n'
            "If only one deliverable, return a single-item list. Use .txt extension for all files."
        )
        messages = [
            {
                "role": "system",
                "content": "You are a file splitter. Return only valid JSON, nothing else.",
            },
            {"role": "user", "content": prompt},
        ]
        try:
            raw = self._call(messages, max_tokens=8192)
            start = raw.find("{")
            end = raw.rfind("}") + 1
            if start == -1 or end == 0:
                raise ValueError("No JSON found")
            parsed = json.loads(raw[start:end])
            files = parsed.get("files", [])
            if not files:
                raise ValueError("Empty files list")
            for f in files:
                if not isinstance(f.get("filename"), str) or not isinstance(f.get("content"), str):
                    raise ValueError("Malformed file entry")
            return files
        except Exception:
            title = assignment.get("title", "assignment").replace(" ", "_").lower()
            return [{"filename": f"{title}.txt", "content": completed_text}]
