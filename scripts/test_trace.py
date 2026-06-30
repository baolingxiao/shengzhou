#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
可运行的 Execution Trace 端到端测试入口。

用法（项目根目录）：
  python scripts/test_trace.py
  python scripts/test_trace.py --text "你好，贾维斯"
  python scripts/test_trace.py --trace-id <已有 trace_id>   # 仅查看

需要：后端依赖已安装；可选 .env 中配置 DOUBAO_API_KEY 才会真正调用 LLM。
无 API Key 时仍会生成 trace 文件并记录 preflight 错误。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
except ImportError:
    pass

from neuralpal.characters.constants import DEFAULT_CHARACTER_ID, DEFAULT_SESSION_ID
from neuralpal.trace import ExecutionTraceRecorder, new_trace_id, trace_scope
from neuralpal.trace.storage import load_trace, trace_path
from server.main import ChatService


def print_timings(data: dict) -> None:
    timings = data.get("timings") or {}
    items = sorted(timings.items(), key=lambda x: x[1], reverse=True)
    print("\n=== 耗时 Top ===")
    for key, ms in items[:6]:
        print(f"  {key}: {ms} ms")


def main() -> int:
    parser = argparse.ArgumentParser(description="Jarvis Execution Trace 测试")
    parser.add_argument("--text", default="你好，简单介绍一下你自己。", help="用户输入")
    parser.add_argument("--session-id", default=DEFAULT_SESSION_ID)
    parser.add_argument("--character-id", default=DEFAULT_CHARACTER_ID)
    parser.add_argument("--trace-id", default="", help="查看已有 trace，不发起新请求")
    args = parser.parse_args()

    if args.trace_id:
        data = load_trace(args.trace_id.strip())
        if not data:
            print(f"未找到 trace: {args.trace_id}")
            return 1
        print(json.dumps(data, ensure_ascii=False, indent=2))
        print_timings(data)
        print(f"\n文件: {trace_path(args.trace_id.strip())}")
        return 0

    trace_id = new_trace_id()
    print(f"[TRACE] {trace_id}")
    print(f"用户输入: {args.text!r}")

    service = ChatService()
    recorder = ExecutionTraceRecorder(
        trace_id,
        user_input=args.text,
        session_id=args.session_id,
        character_id=args.character_id,
    )
    recorder.record_backend_received()

    import asyncio

    async def run():
        with trace_scope(recorder):
            return await service.chat(
                args.session_id,
                args.text,
                character_id=args.character_id,
            )

    try:
        result = asyncio.run(run())
        payload = {
            "text": result.text,
            "route": result.route,
            "blocked": result.blocked,
            "segments": result.segments,
            "trace_id": trace_id,
        }
        recorder.record_api_response(payload)
        recorder.save()
        print("\n=== 回复摘要 ===")
        print(f"route={result.route} blocked={result.blocked} len={len(result.text)}")
        print(result.text[:300])
    except Exception as exc:
        recorder.record_error("test_trace", str(exc), exc_type=type(exc).__name__)
        recorder.save()
        print(f"错误: {exc}")
        return 1

    data = load_trace(trace_id) or {}
    print(f"\n=== Trace 已写入 ===\n{trace_path(trace_id)}")
    print_timings(data)

    # 最慢 3 环节（排除 total_ms）
    timings = {k: v for k, v in (data.get("timings") or {}).items() if k != "total_ms"}
    slowest = sorted(timings.items(), key=lambda x: x[1], reverse=True)[:3]
    print("\n=== 最慢 3 环节 ===")
    for i, (k, v) in enumerate(slowest, 1):
        print(f"  {i}. {k}: {v} ms")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
