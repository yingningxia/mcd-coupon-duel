#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
麦麦对赌 2.0 · 核心状态机（duel.py）
====================================

一个 7 天清零赌约：你押上虚拟筹码，赌自己能在期限内清零所有临期券。
带状态的游戏循环（和 mcd-life 的「一次性报告」本质不同）——有立约、每日晨报、结算胜负。

子命令：
  start              立约（挑出 7 天内过期的券作为赌注标的）
  check              晨报（看进度 + 临期券战书；到期自动结算）
  settle             强制结算
  invite             生成对赌邀请文案
  status             当前对赌状态
  demo               一键跑通完整 DEMO，生成 examples/ 下的三张卡

零第三方依赖，仅用 Python 标准库。LIVE 模式读真实券包，DEMO 模式用相对日期合成的临期券。
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

import mcd_client as M
import roast_duel as R
import card as C

SKILL_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = SKILL_DIR / "data"
DUEL_FILE = DATA_DIR / "duel.json"
DEFAULT_WINDOW = 7


# ----------------------------------------------------------------------------
# 工具
# ----------------------------------------------------------------------------

def now() -> datetime:
    return datetime.now()


def _parse_dt(s: str | None) -> datetime | None:
    if not s:
        return None
    s = str(s).strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        pass
    try:
        return datetime.fromisoformat(s.replace("T", " ").replace("+00:00", ""))
    except ValueError:
        return None


def _cid(c: dict) -> str:
    return str(c.get("couponId") or c.get("id") or c.get("code") or id(c))


def _value(c: dict) -> float:
    for k in ("value", "discountAmount", "amount", "faceValue"):
        v = c.get(k)
        if isinstance(v, (int, float)) and v:
            return float(v)
    di = c.get("discountInfo")
    if isinstance(di, dict):
        for k in ("amount", "value", "discountAmount"):
            v = di.get(k)
            if isinstance(v, (int, float)) and v:
                return float(v)
    return 9.9  # 兜底估值（演示/缺字段时）


def _title(c: dict) -> str:
    return str(c.get("title") or c.get("couponName") or c.get("name") or "神秘券")


# ----------------------------------------------------------------------------
# 标的筛选
# ----------------------------------------------------------------------------

def live_targets(client: M.MCDClient, window: int) -> list[dict]:
    resp = client.my_coupons()
    coupons = resp.get("coupons") or []
    t0 = now()
    out = []
    for c in coupons:
        end = _parse_dt(c.get("tradeEndDateTime") or c.get("expireDate"))
        if not end:
            continue
        # 还没过期、且在 window 天内到期的，才进赌约
        if t0 <= end <= t0 + timedelta(days=window):
            out.append({
                "couponId": _cid(c),
                "title": _title(c),
                "value": _value(c),
                "tradeEndDateTime": end.strftime("%Y-%m-%d %H:%M"),
                "image": c.get("image") or c.get("bigImage") or "",
            })
    return out


def demo_targets() -> list[dict]:
    t0 = now()
    seed = [
        ("火腿扒堡早餐两件套", 9.9, timedelta(days=2, hours=3)),
        ("麦旋风任选", 15.0, timedelta(days=1, hours=6)),
        ("巨无霸立减券", 12.0, timedelta(days=4)),
        ("薯条买一送一", 10.0, timedelta(days=5, hours=12)),
        ("巧克力味厚松饼猪柳蛋套餐", 18.0, timedelta(days=3)),
    ]
    out = []
    for i, (title, val, off) in enumerate(seed, 1):
        end = t0 + off
        out.append({
            "couponId": f"DEMO-{i}",
            "title": title,
            "value": val,
            "tradeEndDateTime": end.strftime("%Y-%m-%d %H:%M"),
            "image": "",
        })
    return out


# ----------------------------------------------------------------------------
# 持久化
# ----------------------------------------------------------------------------

def save_state(state: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    DUEL_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def load_state() -> dict | None:
    if not DUEL_FILE.is_file():
        return None
    try:
        return json.loads(DUEL_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


# ----------------------------------------------------------------------------
# 立约
# ----------------------------------------------------------------------------

def start(client: M.MCDClient, days: int, stake_override: float | None,
          force_demo: bool = False) -> dict:
    mode = "DEMO" if (force_demo or client.mode != "LIVE") else "LIVE"
    targets = demo_targets() if mode == "DEMO" else live_targets(client, days)
    if not targets:
        print("你的券包里 7 天内没有临期券，没东西可赌。")
        print("先去领几张券，或者把赌约窗口拉长再来。")
        return {}
    stake = stake_override if stake_override else sum(t["value"] for t in targets)
    t0 = now()
    state = {
        "version": 1,
        "created_at": t0.strftime("%Y-%m-%d %H:%M:%S"),
        "start_date": t0.strftime("%Y-%m-%d"),
        "end_date": (t0 + timedelta(days=days)).strftime("%Y-%m-%d"),
        "duration_days": days,
        "stake": round(stake, 2),
        "mode": mode,
        "targets": targets,
        "status": "active",
        "day_idx": 1,
        "days_left": days,
        "cleared": 0,
        "result": None,
    }
    save_state(state)
    print(R.contract_text(state))
    print()
    print(f"（模式：{mode}）契约已保存到 data/duel.json。每天用 `check` 看晨报。")
    return state


# ----------------------------------------------------------------------------
# 计算 cleared
# ----------------------------------------------------------------------------

def _cleared_ids(state: dict, client: M.MCDClient,
                 override: set[str] | None) -> set[str]:
    if override is not None:
        return override
    if client.mode != "LIVE":
        return set()  # DEMO 无真实使用信号，默认未清
    resp = client.my_coupons()
    current = {_cid(c) for c in (resp.get("coupons") or [])}
    cleared = set()
    t0 = now()
    for t in state["targets"]:
        if t["couponId"] not in current:
            end = _parse_dt(t["tradeEndDateTime"])
            if end and t0 <= end:  # 在到期前消失 = 被用了 = 赢这张
                cleared.add(t["couponId"])
    return cleared


# ----------------------------------------------------------------------------
# 晨报 / 结算
# ----------------------------------------------------------------------------

def _progress(state: dict, cleared_ids: set[str], t0: datetime) -> dict:
    state["day_idx"] = max(1, (t0.date() - _parse_dt(state["start_date"]).date()).days + 1)
    state["days_left"] = max(0, (_parse_dt(state["end_date"]).date() - t0.date()).days)
    cleared = [t for t in state["targets"] if t["couponId"] in cleared_ids]
    alive = []
    for t in state["targets"]:
        if t["couponId"] in cleared_ids:
            continue
        end = _parse_dt(t["tradeEndDateTime"])
        if end and t0 > end:
            continue  # 已过期，不嘲讽
        remain = end - t0 if end else timedelta(hours=1)
        t2 = dict(t); t2["_remain"] = remain; t2["_left"] = len(state["targets"]) - len(cleared)
        alive.append(t2)
    state["cleared"] = len(cleared)
    state["alive"] = alive
    return state


def check(client: M.MCDClient, cleared_override: set[str] | None = None) -> dict:
    state = load_state()
    if not state:
        print("还没有对赌。先跑 `start` 立约。")
        return {}
    if state["status"] != "active":
        print(f"这场对赌已结算：{state['result']['outcome']}。用 `start` 开新的一场。")
        return state
    t0 = now()
    cleared_ids = _cleared_ids(state, client, cleared_override)
    state = _progress(state, cleared_ids, t0)
    print(R.morning_report_text(state, state["cleared"], t0))
    for c in state["alive"]:
        print(f"  ⚔ {R.taunt(c, state['day_idx'], state['duration_days'], state['cleared'], state['stake'])}")
    # 到期或全清 → 自动结算
    if state["days_left"] <= 0 or state["cleared"] == len(state["targets"]):
        return settle(client, cleared_ids)
    save_state(state)
    return state


def settle(client: M.MCDClient, cleared_override: set[str] | None = None) -> dict:
    state = load_state()
    if not state:
        print("还没有对赌。")
        return {}
    t0 = now()
    cleared_ids = _cleared_ids(state, client, cleared_override)
    state = _progress(state, cleared_ids, t0)
    wasted = [t for t in state["targets"] if t["couponId"] not in cleared_ids]
    wasted_amount = sum(t["value"] for t in wasted)
    outcome = "won" if not wasted else "lost"
    state["status"] = "settled"
    state["result"] = {
        "outcome": outcome,
        "cleared": state["cleared"],
        "total": len(state["targets"]),
        "wasted_amount": round(wasted_amount, 2),
        "wasted_coupons": wasted,
        "settled_at": t0.strftime("%Y-%m-%d %H:%M:%S"),
    }
    save_state(state)
    if outcome == "won":
        print(R.win_report_text(state, state["cleared"]))
    else:
        print(R.lose_report_text(state, wasted, wasted_amount))
    return state


def invite() -> None:
    state = load_state()
    if not state:
        print("还没有对赌，先 `start`。")
        return
    print(R.invite_text(state, state.get("cleared", 0)))


def status() -> None:
    state = load_state()
    if not state:
        print("无进行中的对赌。")
        return
    print(f"状态：{state['status']} | 模式：{state['mode']}")
    print(f"赌约：{state['duration_days']} 天，押 ¥{state['stake']:.2f}")
    print(f"标的：{len(state['targets'])} 张临期券")
    print(f"已清零：{state.get('cleared',0)} 张 | 第 {state.get('day_idx',1)} 天 | 剩 {state.get('days_left',0)} 天")
    if state.get("result"):
        r = state["result"]
        print(f"结算：{r['outcome']} | 白扔 ¥{r['wasted_amount']:.2f}")


# ----------------------------------------------------------------------------
# DEMO 一键跑通
# ----------------------------------------------------------------------------

def run_demo() -> None:
    print("== 麦麦对赌 2.0 · DEMO 一键跑通 ==")
    # 立约
    state = start(M.MCDClient(force_mode="DEMO"), DEFAULT_WINDOW, None, force_demo=True)
    C.save(SKILL_DIR / "examples" / "01_契约卡.html", C.render_contract(state))
    print("  ✓ 生成 examples/01_契约卡.html")

    # 第 4 天晨报（模拟已清 3 张，剩 2 张）
    cleared3 = {t["couponId"] for t in state["targets"][:3]}
    s2 = dict(state); s2["day_idx"] = 4; s2["days_left"] = 3; s2["cleared"] = 3
    alive = []
    for t in state["targets"][3:]:
        e = _parse_dt(t["tradeEndDateTime"]); remain = (e - now()) if e else timedelta(hours=1)
        tt = dict(t); tt["_remain"] = remain; tt["_left"] = 2; alive.append(tt)
    s2["alive"] = alive
    C.save(SKILL_DIR / "examples" / "02_晨报卡.html", C.render_morning(s2, 3, now()))
    print("  ✓ 生成 examples/02_晨报卡.html（第 4 天晨报，进度 3/5）")

    # 结算·输（2 张白扔）
    wasted = state["targets"][3:]
    s3 = dict(state); s3["cleared"] = 3
    C.save(SKILL_DIR / "examples" / "03_处刑卡.html",
              C.render_lose(s3, wasted, sum(t["value"] for t in wasted)))
    print("  ✓ 生成 examples/03_处刑卡.html（输：白扔 2 张）")

    # 结算·赢（全清）
    s4 = dict(state); s4["cleared"] = len(state["targets"])
    C.save(SKILL_DIR / "examples" / "04_战报卡.html", C.render_win(s4, len(state["targets"])))
    print("  ✓ 生成 examples/04_战报卡.html（赢：全清）")

    print("\nDEMO 完成。四张卡都在 examples/，直接打开看效果。")


# ----------------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------------

def _split_ids(spec: str | None) -> set[str] | None:
    if not spec:
        return None
    return {x.strip() for x in spec.split(",") if x.strip()}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="麦麦对赌 2.0")
    p.add_argument("--mode", choices=["LIVE", "DEMO"], help="强制模式")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("start", help="立约")
    s.add_argument("--days", type=int, default=DEFAULT_WINDOW)
    s.add_argument("--stake", type=float, default=None, help="自定义赌注（默认=标的券值之和）")

    c = sub.add_parser("check", help="晨报")
    c.add_argument("--cleared-ids", default=None, help="DEMO 用：已清券 id 列表，逗号分隔")

    st = sub.add_parser("settle", help="结算")
    st.add_argument("--cleared-ids", default=None)

    sub.add_parser("invite", help="对赌邀请文案")
    sub.add_parser("status", help="状态")
    sub.add_parser("demo", help="一键 DEMO")

    args = p.parse_args(argv)
    client = M.MCDClient(force_mode=args.mode)

    if args.cmd == "start":
        start(client, args.days, args.stake)
    elif args.cmd == "check":
        check(client, _split_ids(args.cleared_ids))
    elif args.cmd == "settle":
        settle(client, _split_ids(args.cleared_ids))
    elif args.cmd == "invite":
        invite()
    elif args.cmd == "status":
        status()
    elif args.cmd == "demo":
        run_demo()
    else:
        p.error(f"未知命令 {args.cmd}")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
