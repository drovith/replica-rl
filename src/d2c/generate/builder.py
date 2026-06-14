from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import anthropic

from d2c.generate.prompt import build_system_prompt, build_task_prompt

GENERATION_MODEL = "claude-opus-4-8"
MAX_OUTPUT_TOKENS = 128000
MAX_STEPS = 80

TOOLS = [
    {
        "name": "write_file",
        "description": (
            "Create or overwrite a UTF-8 text file at `path`, relative to the site "
            "root. Send the file's full final contents."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Relative file path."},
                "content": {"type": "string", "description": "Full file contents."},
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "finish",
        "description": "Call once, last, when the site is complete and manifest.json is written.",
        "input_schema": {
            "type": "object",
            "properties": {
                "summary": {
                    "type": "string",
                    "description": "One-line summary of the finished site.",
                },
            },
            "required": ["summary"],
        },
    },
]


@dataclass
class GenerationResult:
    site_dir: Path
    files: list[str] = field(default_factory=list)
    summary: str | None = None
    stop_reason: str | None = None
    steps: int = 0
    finished: bool = False


def _resolve_within(root: Path, relative: str) -> Path:
    target = (root / relative).resolve()
    root = root.resolve()
    if target != root and root not in target.parents:
        raise ValueError(f"path escapes site root: {relative}")
    return target


def _write_file(root: Path, relative: str, content: str) -> str:
    target = _resolve_within(root, relative)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return f"wrote {relative} ({len(content)} bytes)"


def generate_site(
    brief: str,
    site_dir: Path,
    *,
    viewport_width: int = 1440,
    model: str = GENERATION_MODEL,
    effort: str = "high",
    client: anthropic.Anthropic | None = None,
) -> GenerationResult:
    site_dir.mkdir(parents=True, exist_ok=True)
    client = client or anthropic.Anthropic()

    system = [
        {
            "type": "text",
            "text": build_system_prompt(viewport_width),
            "cache_control": {"type": "ephemeral"},
        }
    ]
    messages: list[dict] = [{"role": "user", "content": build_task_prompt(brief)}]
    result = GenerationResult(site_dir=site_dir)

    for step in range(1, MAX_STEPS + 1):
        result.steps = step
        with client.messages.stream(
            model=model,
            max_tokens=MAX_OUTPUT_TOKENS,
            thinking={"type": "adaptive"},
            output_config={"effort": effort},
            system=system,
            tools=TOOLS,
            messages=messages,
        ) as stream:
            message = stream.get_final_message()

        messages.append({"role": "assistant", "content": message.content})
        result.stop_reason = message.stop_reason

        if message.stop_reason != "tool_use":
            break

        tool_results = []
        for block in message.content:
            if block.type != "tool_use":
                continue
            if block.name == "write_file":
                try:
                    note = _write_file(
                        site_dir, block.input["path"], block.input["content"]
                    )
                    result.files.append(block.input["path"])
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": note,
                        }
                    )
                except (ValueError, OSError) as exc:
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": f"error: {exc}",
                            "is_error": True,
                        }
                    )
            elif block.name == "finish":
                result.finished = True
                result.summary = block.input.get("summary")
                tool_results.append(
                    {"type": "tool_result", "tool_use_id": block.id, "content": "ok"}
                )

        messages.append({"role": "user", "content": tool_results})
        if result.finished:
            break

    return result
