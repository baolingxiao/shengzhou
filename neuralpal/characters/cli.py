# -*- coding: utf-8 -*-
"""角色 CLI：颜文字等实例级配置。"""

from __future__ import annotations

import argparse
import sys

from neuralpal.characters.models import CharacterUpdateRequest
from neuralpal.characters.store import get_character_store
from neuralpal.chat.response_signature import (
    append_companion_signature,
    resolve_ending_signature,
    resolve_profile_default_signature,
)
from neuralpal.companion_life.identity import resolve_profile_key_for_character


def cmd_set_signature(character_id: str, signature: str) -> int:
    store = get_character_store()
    char = store.get_character(character_id)
    if not char:
        print(f"未找到角色：{character_id}", file=sys.stderr)
        return 1
    updated = store.update_character(
        character_id,
        CharacterUpdateRequest(ending_signature=signature.strip()),
    )
    if not updated:
        print("更新失败", file=sys.stderr)
        return 1
    preview = append_companion_signature("预览一句回复", resolve_ending_signature(updated))
    print(f"已设置 {updated.name}（{updated.id}）ending_signature={updated.ending_signature!r}")
    print(f"预览：{preview}")
    return 0


def cmd_reset_signature_to_cpc(character_id: str) -> int:
    store = get_character_store()
    char = store.get_character(character_id)
    if not char:
        print(f"未找到角色：{character_id}", file=sys.stderr)
        return 1
    pk = resolve_profile_key_for_character(char)
    default = resolve_profile_default_signature(pk) or "(系统默认)"
    updated = store.update_character(
        character_id,
        CharacterUpdateRequest(ending_signature=None),
    )
    if not updated:
        print("更新失败", file=sys.stderr)
        return 1
    resolved = resolve_ending_signature(updated)
    print(
        f"已清除实例专属颜文字；{updated.name} 将使用 CPC 默认：{default!r} → 解析为 {resolved!r}"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="neuralpal.characters.cli")
    sub = parser.add_subparsers(dest="command", required=True)

    p_set = sub.add_parser("set-signature", help="设置角色实例专属结尾颜文字")
    p_set.add_argument("--character-id", required=True)
    p_set.add_argument("--signature", required=True)

    p_reset = sub.add_parser("reset-signature", help="清除实例颜文字，恢复 CPC 默认")
    p_reset.add_argument("--character-id", required=True)

    args = parser.parse_args(argv)
    if args.command == "set-signature":
        return cmd_set_signature(args.character_id, args.signature)
    if args.command == "reset-signature":
        return cmd_reset_signature_to_cpc(args.character_id)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
