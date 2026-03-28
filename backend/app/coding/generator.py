"""
Code generator — LLM-powered code generation and transformation.

Uses the LLM router to generate, refactor, explain, fix, test, and document code.
Parses LLM output to extract code blocks and explanations.
"""

from __future__ import annotations

import logging
import re
import time
from datetime import datetime, timezone

from backend.app.coding.models import (
    CodeAction,
    CodeLanguage,
    CodeRequest,
    CodeResult,
)
from backend.app.llm.models import ChatRequest, Message, Role
from backend.app.llm.router import get_router

logger = logging.getLogger(__name__)

# System prompts per action
_SYSTEM_PROMPTS: dict[CodeAction, str] = {
    CodeAction.GENERATE: (
        "You are an expert programmer. Generate clean, well-documented, production-quality code. "
        "Return ONLY the code inside a single markdown code block. No additional explanation outside the block."
    ),
    CodeAction.REFACTOR: (
        "You are an expert code reviewer. Refactor the provided code for better readability, "
        "performance, and maintainability. Return the refactored code in a markdown code block, "
        "followed by a brief explanation of changes."
    ),
    CodeAction.EXPLAIN: (
        "You are an expert programming teacher. Explain the provided code clearly and concisely. "
        "Break down the logic, identify patterns, and note any issues."
    ),
    CodeAction.FIX: (
        "You are an expert debugger. Fix the bugs in the provided code. "
        "Return the fixed code in a markdown code block, followed by a brief explanation of what was fixed."
    ),
    CodeAction.TEST: (
        "You are an expert test engineer. Generate comprehensive tests for the provided code. "
        "Use pytest style. Return ONLY the test code in a markdown code block."
    ),
    CodeAction.DOCUMENT: (
        "You are an expert technical writer. Add comprehensive docstrings and comments to the provided code. "
        "Return the documented code in a markdown code block."
    ),
}


async def generate_code(request: CodeRequest) -> CodeResult:
    """
    Generate or transform code using the LLM.

    Args:
        request: Code generation request with action, prompt, optional code.

    Returns:
        CodeResult with generated/transformed code and explanation.
    """
    start = time.monotonic()

    try:
        system_prompt = _SYSTEM_PROMPTS.get(request.action, _SYSTEM_PROMPTS[CodeAction.GENERATE])
        user_message = _build_user_message(request)

        messages = [
            Message(role=Role.SYSTEM, content=system_prompt),
            Message(role=Role.USER, content=user_message),
        ]

        chat_request = ChatRequest(
            messages=messages,
            model=request.model,
            provider=request.provider,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )

        router = get_router()
        response = await router.chat(chat_request)

        # Parse code and explanation from response
        code, explanation = _parse_response(response.content, request.action)
        tokens = response.usage.total_tokens if response.usage else None

        return CodeResult(
            action=request.action,
            code=code,
            language=request.language,
            explanation=explanation,
            model_used=response.model,
            provider_used=response.provider,
            tokens_used=tokens,
            duration_ms=(time.monotonic() - start) * 1000,
        )

    except Exception as exc:
        logger.error("Code generation failed: %s", exc)
        return CodeResult(
            action=request.action,
            code="",
            language=request.language,
            explanation=f"Error: {exc}",
            duration_ms=(time.monotonic() - start) * 1000,
        )


def _build_user_message(request: CodeRequest) -> str:
    """Build the user message for the LLM based on the request."""
    parts: list[str] = []

    if request.action == CodeAction.GENERATE:
        parts.append(f"Language: {request.language.value}")
        parts.append(f"Task: {request.prompt}")

    elif request.action == CodeAction.EXPLAIN:
        parts.append(f"Explain this {request.language.value} code:")
        if request.code:
            parts.append(f"```{request.language.value}\n{request.code}\n```")
        if request.prompt:
            parts.append(f"Focus on: {request.prompt}")

    elif request.action in (CodeAction.REFACTOR, CodeAction.FIX, CodeAction.DOCUMENT):
        action_label = request.action.value.capitalize()
        parts.append(f"{action_label} this {request.language.value} code:")
        if request.code:
            parts.append(f"```{request.language.value}\n{request.code}\n```")
        if request.prompt:
            parts.append(f"Instructions: {request.prompt}")

    elif request.action == CodeAction.TEST:
        parts.append(f"Generate tests for this {request.language.value} code:")
        if request.code:
            parts.append(f"```{request.language.value}\n{request.code}\n```")
        if request.prompt:
            parts.append(f"Focus on: {request.prompt}")

    return "\n\n".join(parts)


def _parse_response(content: str, action: CodeAction) -> tuple[str, str]:
    """
    Parse LLM response to extract code block(s) and explanation text.

    Returns:
        Tuple of (code, explanation).
    """
    # Find code blocks: ```language\n...\n```
    code_block_pattern = re.compile(r"```(?:\w+)?\s*\n(.*?)```", re.DOTALL)
    matches = code_block_pattern.findall(content)

    if matches:
        code = matches[0].strip()
        # Everything outside code blocks is explanation
        explanation = code_block_pattern.sub("", content).strip()
    elif action == CodeAction.EXPLAIN:
        # Explain action may not have code blocks
        code = ""
        explanation = content.strip()
    else:
        # No code block found — treat entire response as code if it looks like code
        code = content.strip()
        explanation = ""

    return code, explanation
