#!/usr/bin/env python3
"""Minimal GLM 5.2 connectivity check without printing credentials."""

from __future__ import annotations

import os
import sys

from openai import OpenAI


def main() -> int:
    api_key = os.environ.get("ZHIPU_API_KEY")
    if not api_key:
        print(
            "ZHIPU_API_KEY is not set. Inject it with your existing "
            "secret-management method, then retry.",
            file=sys.stderr,
        )
        return 2

    base_url = os.environ.get(
        "GLM_API_BASE",
        "https://open.bigmodel.cn/api/paas/v4",
    )
    model = os.environ.get("GLM_MODEL", "glm-5.2")

    client = OpenAI(api_key=api_key, base_url=base_url, timeout=60.0)

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": "这是一次正常的 API 连通性检查。请只回复：GLM52_OK",
                }
            ],
            max_tokens=32,
            temperature=1.0,
        )
    except Exception as exc:  # Keep provider response bodies out of the console.
        status_code = getattr(exc, "status_code", None)
        print(
            f"request_failed type={type(exc).__name__} "
            f"status_code={status_code}",
            file=sys.stderr,
        )
        return 1

    content = response.choices[0].message.content or ""
    print(f"connected model={response.model} content={content[:120]!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

