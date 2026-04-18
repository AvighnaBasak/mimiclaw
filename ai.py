import json
import os
import requests
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

MODELS = [
    {
        "name": "gemma-4-31b-it",
        "url": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
        "api_key": GEMINI_API_KEY,
    },
    {
        "name": "openai/gpt-oss-120b",
        "url": "https://api.groq.com/openai/v1/chat/completions",
        "api_key": GROQ_API_KEY,
    },
    {
        "name": "qwen/qwen3-32b",
        "url": "https://api.groq.com/openai/v1/chat/completions",
        "api_key": GROQ_API_KEY,
    },
]


import re


def _strip_thinking(text: str) -> str:
    text = re.sub(r'<thought>.*?</thought>', '', text, flags=re.DOTALL)
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    return text.strip()


class AIClient:
    def _call(self, messages: list, max_tokens: int = 2048) -> str:
        for model in MODELS:
            try:
                payload = {
                    "model": model["name"],
                    "messages": messages,
                    "max_tokens": max_tokens,
                }
                headers = {
                    "Authorization": f"Bearer {model['api_key']}",
                    "Content-Type": "application/json",
                }
                resp = requests.post(
                    model["url"], headers=headers, json=payload, timeout=180
                )
                resp.raise_for_status()
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                if content and content.strip():
                    return _strip_thinking(content)
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

    def complete_assignment(self, assignment: dict, pdf_text: str | None = None) -> list[dict]:
        context_parts = [
            f"Course: {assignment.get('course_name', 'Unknown')}",
            f"Assignment Title: {assignment.get('title', 'Untitled')}",
            f"Assignment Description:\n{assignment.get('description', 'No description provided.')}",
        ]
        if pdf_text:
            context_parts.append(f"\nAttached PDF/Document Content:\n{pdf_text}")

        prompt = "\n\n".join(context_parts)

        messages = [
            {
                "role": "system",
                "content": (
                    "You are an expert academic assistant that produces assignment deliverables.\n\n"
                    "RULES:\n"
                    "1. Read the assignment carefully and determine what files are required.\n"
                    "2. Use the CORRECT file extension based on what the assignment asks for "
                    "(.c, .py, .java, .cpp, .h, .txt, .md, etc.).\n"
                    "3. If the assignment requires multiple files (e.g. client.c and server.c), "
                    "create each as a SEPARATE file.\n"
                    "4. For code assignments: output ONLY the source code. No introductions, "
                    "no design overviews, no architecture explanations, no fluff. "
                    "Just clean, compilable/runnable code with necessary comments.\n"
                    "5. For written assignments: output ONLY the essay/report content.\n"
                    "6. Return your response as ONLY valid JSON in this exact format:\n"
                    '{"files": [{"filename": "exact_name.ext", "content": "full file content here"}]}\n'
                    "7. No text before or after the JSON. No markdown code fences. Just the JSON object.\n"
                    "8. Make sure the code is COMPLETE and not truncated. Every function must have "
                    "a full implementation."
                ),
            },
            {"role": "user", "content": prompt},
        ]

        raw = self._call(messages, max_tokens=16384)

        # Strip markdown code fences if present
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            first_newline = cleaned.find("\n")
            cleaned = cleaned[first_newline + 1:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        try:
            start = cleaned.find("{")
            end = cleaned.rfind("}") + 1
            if start == -1 or end == 0:
                raise ValueError("No JSON found")
            parsed = json.loads(cleaned[start:end])
            files = parsed.get("files", [])
            if not files:
                raise ValueError("Empty files list")
            for f in files:
                if not isinstance(f.get("filename"), str) or not isinstance(f.get("content"), str):
                    raise ValueError("Malformed file entry")
            return files
        except Exception:
            title = assignment.get("title", "assignment").replace(" ", "_").lower()
            return [{"filename": f"{title}.txt", "content": raw}]
