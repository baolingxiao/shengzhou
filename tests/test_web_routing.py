# -*- coding: utf-8 -*-
from types import SimpleNamespace

from neuralpal.desktop.routing import is_web_search_only, needs_web_browser


def _proposal(**kwargs):
    return SimpleNamespace(
        goal=kwargs.get("goal", ""),
        steps=kwargs.get("steps", []),
        surface=kwargs.get("surface", "local"),
    )


def test_web_surface_defaults_to_search():
    p = _proposal(
        surface="web",
        goal="搜索精油品牌并比价",
        steps=["整理列表"],
    )
    assert is_web_search_only(p)
    assert not needs_web_browser(p)


def test_login_requires_browser():
    p = _proposal(
        surface="web",
        goal="登录淘宝下单",
    )
    assert needs_web_browser(p)
    assert not is_web_search_only(p)


def test_research_keywords_without_web_surface():
    p = _proposal(
        surface="local",
        goal="帮我调研一下竞品价格",
    )
    assert is_web_search_only(p)
