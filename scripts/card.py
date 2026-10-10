#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
麦麦对赌 2.0 · 卡片生成器（card.py）
=====================================

把对赌的几个关键时刻渲染成可分享的 HTML 卡片：
  - 契约卡（立约时）
  - 晨报卡（每日进度 + 施压）
  - 战报卡（赢）
  - 处刑卡（输，含「债务山」可视化）

零第三方依赖，纯标准库拼 HTML。配色走麦当劳红黄，明亮、有食欲。
"""

from __future__ import annotations

from datetime import datetime, timedelta
from html import escape
from pathlib import Path

import roast_duel as R

RED = "#E4002B"
YELLOW = "#FFC72C"
INK = "#2b2b2b"
PAPER = "#fff8ef"


def arches_svg(color: str = "#FFFFFF") -> str:
    """金拱门（双拱）纯 SVG。"""
    return f'''<svg viewBox="0 0 64 56" width="34" height="30" aria-hidden="true">
      <path d="M14 54 V30 a10 10 0 0 1 20 0 V54" fill="none" stroke="{color}" stroke-width="9" stroke-linecap="round"/>
      <path d="M30 54 V30 a10 10 0 0 1 20 0 V54" fill="none" stroke="{color}" stroke-width="9" stroke-linecap="round"/>
    </svg>'''


def _page(title: str, inner: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(title)}</title>
<style>
  *{{box-sizing:border-box}}
  body{{margin:0;background:{PAPER};color:{INK};
       font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;
       display:flex;justify-content:center;padding:24px}}
  .card{{width:420px;max-width:100%;background:#fff;border-radius:18px;
        overflow:hidden;box-shadow:0 10px 30px rgba(228,0,43,.18)}}
  .hd{{background:{RED};color:#fff;padding:16px 20px;display:flex;
      align-items:center;gap:10px}}
  .hd h1{{font-size:18px;margin:0;font-weight:800}}
  .bd{{padding:20px}}
  .kicker{{color:{RED};font-weight:800;font-size:13px;letter-spacing:1px}}
  .big{{font-size:30px;font-weight:900;margin:6px 0}}
  .row{{display:flex;justify-content:space-between;padding:7px 0;
       border-bottom:1px dashed #f0d9c2;font-size:14px}}
  .row:last-child{{border-bottom:none}}
  .bar{{height:14px;border-radius:8px;background:#ffe6c2;overflow:hidden;margin:10px 0}}
  .bar>i{{display:block;height:100%;background:{RED}}}
  .taunt{{background:{PAPER};border-left:4px solid {YELLOW};padding:10px 12px;
         border-radius:8px;margin:8px 0;font-size:13px;font-style:italic}}
  .foot{{padding:12px 20px;background:{PAPER};color:#9a7b5f;font-size:12px;
        text-align:center}}
  .pill{{display:inline-block;background:{YELLOW};color:#5a3b00;font-weight:800;
        border-radius:999px;padding:2px 10px;font-size:12px}}
  .mt{{margin-top:14px}}
</style></head><body><div class="card">{inner}</div></body></html>"""


def render_contract(state: dict) -> str:
    targets = state["targets"]
    rows = "".join(
        f'<div class="row"><span>{escape(c["title"])}</span>'
        f'<span>¥{c["value"]:.1f} · 限 {escape(str(c.get("tradeEndDateTime","")))}</span></div>'
        for c in targets
    )
    inner = f'''
      <div class="hd">{arches_svg()}<h1>麦麦对赌 · 契约</h1></div>
      <div class="bd">
        <div class="kicker">立约人：你</div>
        <div class="big">押上 ¥{state["stake"]:.2f} 尊严</div>
        <p style="font-size:14px;margin:4px 0 12px">赌约：{state["duration_days"]} 天内清零下面
        <b>{len(targets)}</b> 张临期券，一张不落才算赢。到期自动结算。</p>
        {rows}
        <p style="font-size:12px;color:#9a7b5f;margin-top:12px">
        ① 券消失且未过期＝你赢这张 ② 券过期未用＝进浪费博物馆 ③ 赢则筹码翻倍＋称号，输则本金归零＋债务山</p>
      </div>
      <div class="foot">麦麦对赌 2.0 · 虚拟筹码，认真但不较真</div>'''
    return _page("麦麦对赌契约", inner)


def render_morning(state: dict, cleared: int, now: datetime) -> str:
    total = len(state["targets"])
    left = total - cleared
    pct = int(cleared / total * 100) if total else 100
    days_left = max(state.get("days_left", 0), 0)
    taunts = "".join(
        f'<div class="taunt">「{escape(R.taunt(c, state["day_idx"], state["duration_days"], cleared, state["stake"]))}」</div>'
        for c in state.get("alive", [])
    )
    inner = f'''
      <div class="hd">{arches_svg()}<h1>第 {state["day_idx"]} 天 · 对赌晨报</h1></div>
      <div class="bd">
        <div class="kicker">进度 {cleared}/{total}</div>
        <div class="bar"><i style="width:{pct}%"></i></div>
        <div class="row"><span>已清零</span><span><b>{cleared}</b> 张</span></div>
        <div class="row"><span>还赖在包里</span><span><b>{left}</b> 张</span></div>
        <div class="row"><span>距结算</span><span>{escape(R.countdown_phrase(timedelta(days=days_left)))}</span></div>
        <div class="row"><span>赌注状态</span><span class="pill">{'安全' if cleared==total else '还在烧'}</span></div>
        <div class="mt"><div class="kicker">临期券的战书</div>{taunts}</div>
      </div>
      <div class="foot">每天 9:00 自动推送 · 麦麦对赌 2.0</div>'''
    return _page("对赌晨报", inner)


def render_win(state: dict, cleared: int) -> str:
    stake = state["stake"]
    inner = f'''
      <div class="hd">{arches_svg()}<h1>🏆 省钱战神</h1></div>
      <div class="bd">
        <div class="big" style="color:{RED}">你赌赢了</div>
        <p style="font-size:14px">{len(state["targets"])} 张临期券，{cleared} 张在你手里清零，
        一张没进浪费博物馆。</p>
        <div class="row"><span>赌注返还</span><span>¥{stake:.2f} → ¥{stake*2:.2f}</span></div>
        <div class="row"><span>解锁称号</span><span class="pill">省钱战神</span></div>
        <div class="row"><span>零浪费天数</span><span>{state["duration_days"]} 天</span></div>
        <p style="font-size:12px;color:#9a7b5f;margin-top:12px">把这张战报发出去，让朋友看看谁才是券包的主人。</p>
      </div>
      <div class="foot">麦麦对赌 2.0</div>'''
    return _page("省钱战神战报", inner)


def render_lose(state: dict, wasted_coupons: list[dict], wasted_amount: float) -> str:
    cleared = state.get("cleared", 0)
    total = len(state["targets"])
    debt = "".join(
        f'<div class="row"><span>{escape(c["title"])}</span><span>¥{c["value"]:.1f}</span></div>'
        for c in wasted_coupons
    )
    # 债务山：用柱状高度表现浪费金额
    maxv = max((c["value"] for c in wasted_coupons), default=1) or 1
    bars = "".join(
        f'<div style="width:100%;height:{int(c["value"]/maxv*120)}px;background:{RED};'
        f'border-radius:4px 4px 0 0;margin:0 2px"></div>'
        for c in wasted_coupons
    )
    inner = f'''
      <div class="hd" style="background:#5a3b00">{arches_svg("#FFC72C")}<h1>💀 公开处刑</h1></div>
      <div class="bd">
        <div class="big" style="color:#5a3b00">你输给了 7 天前的自己</div>
        <p style="font-size:14px">赌约 {total} 张清零，你只清了 {cleared} 张。</p>
        <div class="row"><span>白扔</span><span><b>¥{wasted_amount:.2f}</b></span></div>
        <div class="row"><span>等于</span><span>{escape(R.money_to_food(wasted_amount))}</span></div>
        <div class="mt"><div class="kicker">债务山</div>
          <div style="display:flex;align-items:flex-end;height:130px;margin-top:6px">{bars}</div>
        </div>
        <div class="mt"><div class="kicker">过期未用的券</div>{debt}</div>
        <p style="font-size:12px;color:#9a7b5f;margin-top:12px">本金 ¥{state["stake"]:.2f} 归零。下次别高估自己的执行力。</p>
      </div>
      <div class="foot">麦麦对赌 2.0</div>'''
    return _page("公开处刑", inner)


def save(path: str, html: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(html, encoding="utf-8")
