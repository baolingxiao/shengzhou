# -*- coding: utf-8 -*-
"""本机任务路由：何时走本地快捷通道，何时必须 Computer Use。"""

from __future__ import annotations

# 需要在 App 内操作 UI（键鼠 + 截图）
_UI_INTERACTION_KEYS = (
    "微信",
    "wechat",
    "联系人",
    "好友",
    "聊天",
    "发消息",
    "发送",
    "输入",
    "点击",
    "回复",
    "对话",
    "消息",
    "填表",
    "登录",
    "备忘录",
    "notes",
    "写一条",
    "新建一条",
    "粘贴",
    "复制到",
)

# 明确是文件系统操作
_FILE_KEYS = (
    "文件",
    "文件夹",
    "媒体文件",
    "桌面",
    "图片",
    "照片",
    "视频",
    ".mp4",
    ".mov",
    ".jpg",
    ".png",
    ".heic",
    "整理",
    "移入",
    "移出",
)

_WEB_SEARCH_KEYS = (
    "搜索",
    "查询",
    "查一下",
    "调研",
    "比价",
    "对比",
    "对比价格",
    "品牌",
    "了解",
    "最新",
    "新闻",
    "资讯",
    "信息",
    "汇总",
    "整理",
    "列出",
    "收集",
    "排名",
    "价格",
    "多少钱",
    "官网",
    "联网",
    "网上",
    "google",
    "bing",
    "百度",
)

_WEB_BROWSER_KEYS = (
    "填表",
    "登录",
    "注册",
    "下单",
    "购买",
    "付款",
    "提交订单",
    "点击",
    "发布",
    "上传",
    "下载文件",
    "截图网页",
    "在网站",
    "网页上操作",
    "代填",
    "购物车",
    "checkout",
)


def proposal_blob(proposal) -> str:
    return " ".join(
        [
            str(getattr(proposal, "goal", "") or ""),
            *list(getattr(proposal, "steps", []) or []),
        ]
    )


def needs_computer_use(proposal) -> bool:
    """多步 UI 代操（微信发消息、备忘录写字等）必须走 Computer Use。"""
    blob = proposal_blob(proposal).lower()
    if any(k.lower() in blob for k in _UI_INTERACTION_KEYS):
        # 「打开微信」且仅此一步 → 本地 open -a 即可
        steps = [str(s).strip() for s in (getattr(proposal, "steps", None) or []) if str(s).strip()]
        send_like = any(
            k in blob
            for k in ("发送", "发消息", "联系人", "好友", "聊天", "输入", "点击", "回复", "对话")
        )
        if send_like:
            return True
        if len(steps) > 1:
            return True
    return False


def needs_web_browser(proposal) -> bool:
    """需要在浏览器里登录、填表、点按等交互。"""
    blob = proposal_blob(proposal).lower()
    return any(k.lower() in blob for k in _WEB_BROWSER_KEYS)


def is_web_search_only(proposal) -> bool:
    """纯信息检索：走 Claude web_search，不操控本机 Chrome。"""
    if needs_web_browser(proposal):
        return False
    blob = proposal_blob(proposal).lower()
    surface = str(getattr(proposal, "surface", "") or "").strip().lower()
    if surface == "web":
        return True
    return any(k.lower() in blob for k in _WEB_SEARCH_KEYS)


def looks_like_file_operation(proposal) -> bool:
    blob = proposal_blob(proposal)
    if needs_computer_use(proposal):
        return False
    return any(k in blob for k in _FILE_KEYS)
