import json
import logging
import os
import re
import requests
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

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


def _strip_thinking(text: str) -> str:
    text = re.sub(r'<thought>.*?</thought>', '', text, flags=re.DOTALL)
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    return text.strip()


def _strip_code_fences(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        first_newline = cleaned.find("\n")
        cleaned = cleaned[first_newline + 1:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    return cleaned.strip()


class AIClient:
    def _call(self, messages: list, max_tokens: int = 2048) -> str:
        errors = []
        for model in MODELS:
            try:
                logger.info(f"Trying model: {model['name']}")
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
                    model["url"], headers=headers, json=payload, timeout=120
                )
                resp.raise_for_status()
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                if content and content.strip():
                    logger.info(f"Success with {model['name']} ({len(content)} chars)")
                    return _strip_thinking(content)
                errors.append(f"{model['name']}: empty response")
            except requests.exceptions.Timeout:
                errors.append(f"{model['name']}: timeout")
                logger.warning(f"Timeout with {model['name']}")
            except Exception as e:
                errors.append(f"{model['name']}: {e}")
                logger.warning(f"Error with {model['name']}: {e}")
        raise RuntimeError(f"All AI models failed: {'; '.join(errors)}")

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

    def _build_context(self, assignment: dict, pdf_text: str | None = None) -> str:
        parts = [
            f"Course: {assignment.get('course_name', 'Unknown')}",
            f"Assignment Title: {assignment.get('title', 'Untitled')}",
            f"Assignment Description:\n{assignment.get('description', 'No description provided.')}",
        ]
        if pdf_text:
            parts.append(f"\nAttached PDF/Document Content:\n{pdf_text}")
        return "\n\n".join(parts)

    def _parse_json(self, raw: str) -> dict | None:
        cleaned = _strip_code_fences(raw)
        start = cleaned.find("{")
        end = cleaned.rfind("}") + 1
        if start == -1 or end == 0:
            return None
        try:
            return json.loads(cleaned[start:end])
        except Exception:
            return None

    def plan_files(self, assignment: dict, pdf_text: str | None = None) -> list[str]:
        context = self._build_context(assignment, pdf_text)
        messages = [
            {
                "role": "system",
                "content": (
                    "You are an expert academic assistant. Analyze the assignment and determine "
                    "what files need to be created.\n\n"
                    "RULES:\n"
                    "1. Use the CORRECT file extension (.c, .py, .java, .cpp, .h, .txt, .md, etc.)\n"
                    "2. If the assignment requires multiple files (e.g. client.c and server.c), "
                    "list each separately.\n"
                    "3. Use descriptive filenames matching what the assignment asks for.\n"
                    "4. Return ONLY valid JSON: {\"files\": [\"filename1.ext\", \"filename2.ext\"]}\n"
                    "5. No text before or after the JSON."
                ),
            },
            {"role": "user", "content": context},
        ]
        raw = self._call(messages, max_tokens=256)
        parsed = self._parse_json(raw)
        if parsed and isinstance(parsed.get("files"), list) and parsed["files"]:
            filenames = [f for f in parsed["files"] if isinstance(f, str)]
            if filenames:
                logger.info(f"Planned {len(filenames)} files: {filenames}")
                return filenames
        title = assignment.get("title", "assignment").replace(" ", "_").lower()
        return [f"{title}.txt"]

    def generate_file(self, filename: str, assignment: dict, pdf_text: str | None = None) -> str:
        context = self._build_context(assignment, pdf_text)
        messages = [
            {
                "role": "system",
                "content": (
                    "You are an expert academic assistant. You must produce the COMPLETE content "
                    f"for a file named: {filename}\n\n"
                    "RULES:\n"
                    "1. Output ONLY the file content. No explanations, no introductions, "
                    "no design overviews, no markdown fences, no fluff.\n"
                    "2. For code files: output clean, compilable/runnable source code with "
                    "necessary inline comments only.\n"
                    "3. For written files: output only the essay/report text.\n"
                    "4. The code must be COMPLETE — every function fully implemented, "
                    "nothing truncated or left as TODO.\n"
                    "5. Start directly with the code/content. No preamble."
                ),
            },
            {"role": "user", "content": f"{context}\n\nProduce the complete content for: {filename}"},
        ]
        raw = self._call(messages, max_tokens=8192)
        return _strip_code_fences(raw)
