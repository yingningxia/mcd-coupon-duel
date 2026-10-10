#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
麦麦对赌 2.0 · 对赌话术引擎（roast_duel.py）
=============================================

所有对赌文案都必须过这一层，不要在业务代码里硬写字符串。
语气：损友式 + 带赌注的紧张感，不是家长式说教，也不是阴间词。

四种核心手法（与 mcd-life 一致地复用「换算成实物 / 精确到分钟 / 关注失去 / 损友吐槽」，
但加了「对赌」专属的挑衅与胜负张力）：
  - 嘲讽（taunt）      : 临期券以第一人称向你下战书
  - 契约（contract）   : 立约时的戏剧化赌约书
  - 晨报（morning）    : 每日进度 + 剩余券的施压
  - 战报（win）/处刑（lose）: 结算两种结局
"""

from __future__ import annotations

import hashlib
import random
from datetime import datetime, timedelta


# ----------------------------------------------------------------------------
# 基础换算
# ----------------------------------------------------------------------------

def money_to_food(yuan: float) -> str:
    """把钱换算成有食欲的实物。"""
    y = float(yuan)
    if y <= 0:
        return "零花钱"
    if y < 12:
        return "一个圆筒冰淇淋"
    if y < 25:
        return "一顿麦当劳早餐"
    if y < 45:
        return "一顿麦当劳正餐"
    if y < 80:
        return "一份双人套餐"
    if y < 150:
        return "两顿麦当劳正餐"
    return "一桌麦当劳全家桶"


def countdown_phrase(td: timedelta) -> str:
    """精确到分钟的倒计时文案。td 可为负（已过期）。"""
    if td.total_seconds() < 0:
        over = -td.total_seconds()
        d = int(over // 86400)
        h = int((over % 86400) // 3600)
        m = int((over % 3600) // 60)
        if d > 0:
            return f"已过期 {d} 天 {h} 小时"
        if h > 0:
            return f"已过期 {h} 小时 {m} 分"
        return f"已过期 {m} 分"
    d = int(td.total_seconds() // 86400)
    h = int((td.total_seconds() % 86400) // 3600)
    m = int((td.total_seconds() % 3600) // 60)
    if d > 0:
        return f"{d} 天 {h} 小时"
    if h > 0:
        return f"{h} 小时 {m} 分"
    return f"{m} 分"


def _seed(text: str) -> int:
    return int(hashlib.md5(text.encode("utf-8")).hexdigest(), 16)


# ----------------------------------------------------------------------------
# 嘲讽（临期券的第一人称战书）
# ----------------------------------------------------------------------------

_TAUNTS_EARLY = [
    "我还能撑 {cd}。你领我那天可不是这态度。",
    "第 {day} 天了，你包里 {total} 张临期券，你一个都没动。我排第几？",
    "你赌的是 7 天清零我，还是赌我会自己消失？后者不叫赢。",
    "我是 {title}。我值 {val}。你押的尊严里有我一份，别装没看见。",
]

_TAUNTS_MID = [
    "第 {day} 天。是不是觉得我 {val} 不配让你下楼一趟？",
    " midpoint。你清零了 {cleared} 张，剩下 {left} 张。赌注还在烧。",
    "我倒计时 {cd}。你上次说『明天一定用』，是昨天的明天吗？",
    "离我消失还有 {cd}。你赌的是你出门的速度，还是我的耐心？",
]

_TAUNTS_LATE = [
    "最后 {cd}。今天不过我，明天我就去浪费博物馆报到——你的赌注里也有我。",
    "就剩 {cd} 了。你之前那 {cleared} 张白清了？不，但我是压轴的。",
    "我是 {title}。我快没了，你的 ¥{stake} 尊严也快没了。一起？",
    "最后 {cd}。要么你现在下单，要么我替你写悔过书。",
]


def taunt(coupon: dict, day_idx: int, total_days: int,
          cleared: int, stake: float) -> str:
    """剩余券向你下战书。day_idx 从 1 开始。"""
    cd = countdown_phrase(coupon.get("_remain", timedelta(hours=1)))
    title = coupon.get("title", "这张券")
    val = coupon.get("value", 0.0)
    left = coupon.get("_left", 1)
    ratio = day_idx / total_days
    if ratio < 0.34:
        pool = _TAUNTS_EARLY
    elif ratio < 0.7:
        pool = _TAUNTS_MID
    else:
        pool = _TAUNTS_LATE
    t = random.Random(_seed(title + str(day_idx))).choice(pool)
    return t.format(
        cd=cd, day=day_idx, total=total_days, title=title,
        val=f"¥{val:.1f}", cleared=cleared, left=left, stake=f"{stake:.0f}",
    )


# ----------------------------------------------------------------------------
# 契约（立约）
# ----------------------------------------------------------------------------

def contract_text(state: dict) -> str:
    targets = state["targets"]
    n = len(targets)
    stake = state["stake"]
    lines = [
        "【麦麦对赌契约】",
        "",
        f"立约人：你（本次登录的麦当劳账号）",
        f"赌约：{state['duration_days']} 天内，清零下面 {n} 张临期券，",
        f"      合计 ¥{stake:.2f}。一张不落，才算赢。",
        f"赌注：你押上了 ¥{stake:.2f} 的尊严（虚拟筹码）。",
        "",
        "条款：",
        "  ① 券在你包里『消失』且未过期 = 你赢了这一张；",
        "  ② 券过期了你还没用 = 你输了这一张，它进浪费博物馆；",
        "  ③ 到期日一到，系统自动结算。赢则筹码翻倍 + 称号，",
        "     输则本金归零，并生成你的『债务山』。",
        "",
        "参赌标的：",
    ]
    for i, c in enumerate(targets, 1):
        end = c.get("tradeEndDateTime", "")
        lines.append(f"  {i}. {c['title']}  ¥{c['value']:.1f}  限用至 {end}")
    lines.append("")
    lines.append("—— 赌约已立。7 天后见分晓，别让自己失望。")
    return "\n".join(lines)


# ----------------------------------------------------------------------------
# 晨报
# ----------------------------------------------------------------------------

def morning_report_text(state: dict, cleared: int, now: datetime) -> str:
    total = len(state["targets"])
    left = total - cleared
    days_left = state["days_left"]
    stake = state["stake"]
    pct = int(cleared / total * 100) if total else 100
    bar = "█" * (cleared) + "░" * (left)
    head = (f"【第 {state['day_idx']} 天 · 对赌晨报】")
    prog = f"进度 {cleared}/{total}  [{bar}] {pct}%"
    if days_left > 0:
        deadline = f"距结算还有 {countdown_phrase(timedelta(days=days_left))}。"
    else:
        deadline = "今天就是结算日。"
    return "\n".join([head, prog, deadline,
                      f"赌注 ¥{stake:.2f} 的尊严，目前{'安全' if cleared==total else '还在烧'}。"])


# ----------------------------------------------------------------------------
# 结算：赢
# ----------------------------------------------------------------------------

def win_report_text(state: dict, cleared: int) -> str:
    stake = state["stake"]
    total = len(state["targets"])
    return "\n".join([
        "🏆【省钱战神 · 战报】",
        "",
        f"你赌赢了。{total} 张临期券，{cleared} 张在你手里清零，",
        f"一张没进浪费博物馆。",
        "",
        f"赌注 ¥{stake:.2f} 翻倍返还 → ¥{stake*2:.2f} 虚拟筹码。",
        "称号解锁：省钱战神（7 天零浪费）。",
        "",
        "你说得出做得到。把这张战报发出去，让朋友看看。",
    ])


# ----------------------------------------------------------------------------
# 结算：输
# ----------------------------------------------------------------------------

def lose_report_text(state: dict, wasted_coupons: list[dict],
                     wasted_amount: float) -> str:
    cleared = state.get("cleared", 0)
    total = len(state["targets"])
    lines = [
        "💀【公开处刑】",
        "",
        "你输给了 7 天前的自己。",
        "",
        f"赌约：{total} 张临期券清零。你只清了 {cleared} 张。",
        f"白扔：{len(wasted_coupons)} 张，合计 ¥{wasted_amount:.2f}",
        f"＝ {money_to_food(wasted_amount)}，本来该进你胃里的。",
        "",
        "你的债务山：",
    ]
    for c in wasted_coupons:
        lines.append(f"  ▲ {c['title']}  ¥{c['value']:.1f}  （过期未用）")
    lines.append("")
    lines.append("本金 ¥%.2f 归零。下次赌约，别再高估自己的执行力。" % state["stake"])
    return "\n".join(lines)


# ----------------------------------------------------------------------------
# 社交邀请
# ----------------------------------------------------------------------------

def invite_text(state: dict, cleared: int) -> str:
    total = len(state["targets"])
    stake = state["stake"]
    return (
        f"我赌 7 天清零我的 ¥{stake:.0f} 临期券，目前进度 {cleared}/{total}。"
        f"敢接吗？谁先让券进浪费博物馆，谁请客。"
    )
