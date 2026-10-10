# 麦麦对赌 2.0 · MCD-COUPON-DUEL

> 把"省钱"变成一场 7 天赌约。你押上虚拟筹码，赌自己能在期限内清零所有临期券；
> 每天收到临期券的战书，到期自动结算——赢了是「省钱战神」，输了是「公开处刑」+ 债务山。

[![MCP](https://img.shields.io/badge/MCP-mcd--mcp-red)](https://mcp.mcd.cn)
[![Zero Deps](https://img.shields.io/badge/deps-zero%20stdlib-blue)](https://www.python.org)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

---

## 为什么不是又一份"浪费账单"

同作者在同一个比赛里投了两个作品，刻意做了对比：

- **抢救麦券大作战**是一份报告——它算出你白扔了多少钱，你看完关掉。
- **麦麦对赌 2.0** 是一场赌约——它有立约、有每日进度、有胜负、有赌注，而且**它会每天来找你**。

报告给你结论，赌约给你**张力**。人不会因为"你浪费了 ¥61"而出门，但会因为"我押了 ¥61 尊严、还有 2 天就要输"而出门。

**赌注、倒计时、胜负——这三样东西，让"省钱"从无聊动作变成一件有 stake 的事。**

---

## 它怎么玩

```
立约 ──► 每天晨报（临期券向你下战书）──► 到期结算
              ▲                                  │
              └──────── 没清完就继续施压 ─────────┘
```

| 时刻 | 产物 | 你看到什么 |
|---|---|---|
| 立约 | 契约卡 | 押了多少尊严、赌哪几张券、限哪天前 |
| 第 N 天 | 晨报卡 | 进度条 + 剩余券的嘲讽战书 + 赌注还在烧 |
| 赢了 | 战报卡 | 「省钱战神」称号 + 筹码翻倍 |
| 输了 | 处刑卡 | "你输给了 7 天前的自己" + **债务山** |

**债务山**：把每张白扔的券变成一根红色柱子，柱高 = 金额。你浪费的钱，变成一座看得见的山。

**临期券的战书**（真实生成样例）：

> 第 3 天。是不是觉得我 ¥9.9 不配让你下楼一趟？
> 离我消失还有 2 天 3 小时。你赌的是你出门的速度，还是我的耐心？

---

## 快速开始

```bash
# 真实数据（需自行在 ~/.workbuddy/mcp.json 配置麦当劳 MCP Token）
cd scripts
python duel.py start              # 立约：挑出 7 天内临期券作为赌注
python duel.py check              # 每天晨报：看进度 + 战书（到期自动结算）
python duel.py settle             # 手动结算
python duel.py invite             # 生成对赌邀请文案，发给朋友 PK

# 无需 Token 的离线演示（一键生成四张卡到 examples/）
python duel.py demo
```

DEMO 模式用相对日期合成的临期券（永远有"临终券"），评委 clone 即可完整跑通，**不需要任何配置**。

---

## 四张卡（直接打开看效果）

| 卡 | 文件 |
|---|---|
| 契约卡 | `examples/01_契约卡.html` |
| 第 4 天晨报卡（进度 3/5） | `examples/02_晨报卡.html` |
| 处刑卡（输：白扔 2 张） | `examples/03_处刑卡.html` |
| 战报卡（赢：全清） | `examples/04_战报卡.html` |

---

## 文件结构

```
mcd-coupon-duel/
├── SKILL.md                 # WorkBuddy Skill 主文件（触发词 + SOP + 红线）
├── README.md
├── CONTEST_DECLARATION.md   # 参赛声明（官方原文，未改动）
├── MCP_INTEGRATION.md       # MCP 集成说明
├── workbuddy.md             # WorkBuddy 开发上下文（联动奖励核验）
├── scripts/
│   ├── mcd_client.py         # 麦当劳 MCP 客户端 + 自动降级
│   ├── roast_duel.py         # 对赌话术引擎（嘲讽/契约/晨报/战报/处刑）
│   ├── duel.py               # 状态机：立约/晨报/结算 + 持久化 + CLI
│   └── card.py               # 四张卡 HTML 生成器（含债务山）
├── references/
│   ├── mcp-tools.md          # 33 工具速查
│   └── offline_menu.json     # DEMO 离线数据集
└── examples/                 # DEMO 生成的四张卡
```

---

## 技术要点

- **零第三方依赖**：全部脚本仅用 Python 标准库。
- **自动降级**：Token 失效 / 断网时不抛异常，切 DEMO 模式，演示永不翻车。
- **胜负判定巧用 MCP 原生特性**：券包接口只返回"当前还在的券"，本 Skill 用"标的券在不在包里" + 到期时间，推导出每张券是"被用了（赢）"还是"过期了（输）"，不依赖任何"已用/已废"字段。
- **虚拟筹码**：赌注纯虚拟，明说"认真但不较真"，不诱导真实赌博。

---

## 合规

参赛作品，非麦当劳官方产品。不含真实 Token / 账号 / 个人信息；`data/`（本地对赌账本）已 gitignore。详见 `CONTEST_DECLARATION.md`。
