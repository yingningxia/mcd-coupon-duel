# WorkBuddy 开发上下文 · workbuddy.md

本文记录「麦麦对赌 2.0」使用 WorkBuddy 开发的真实过程，用于核验 WorkBuddy 联动活动奖励条件。

- **开发工具**：WorkBuddy（Agent 模式）
- **开发时间**：2026-10-10 ~ 2026-10-11
- **Skill 形态**：WorkBuddy Skill（`SKILL.md` + `scripts/` + `references/` + `examples/`）

---

## 一、开发过程概要

整个项目在 WorkBuddy 对话中完成。

### 起点：用户对"有趣"的两次否定

用户先投了「抢救麦券大作战」（一份浪费账单），随后明确反馈：

> 之前那个麦麦对赌名字有趣，但是具体方式并不有趣，再想一下。

以及一个更前置的判断：

> 三个模式都不够有意思和有创意，感觉就是把 MCP 给你的内容换个说法表达出来。

WorkBuddy 在复盘里确认了核心问题：**创意不是换说法，是换用法**。一份仪表盘再好看也是被看的东西，不是能玩的东西。不有趣的 root cause 是——没有 agency（能动性）、没有 stakes（赌注）、没有 play（玩）。

### 第 1 轮 · 概念发散

WorkBuddy 不再给"又一个报告"，而是列出 4 个**真能玩起来**的方向，每个都带具体机制：

1. **麦麦破产法庭**——你被券包起诉「挥霍浪费罪」，角色扮演审判
2. **麦麦对赌 2.0**——7 天清零赌约，押虚拟筹码，每日战书，胜负结算，社交 PK
3. **麦麦盲盒**——每天抽一张指定券，开箱仪式感
4. **麦麦养券**——每张券是麦宠，过期没喂就进墓园

用户用 AskUserQuestion 选定 **B. 麦麦对赌 2.0**，并选择**作为新参赛作品**（与 mcd-coupon-rescue 并列）。

### 第 2 轮 · 机制落地

WorkBuddy 复用已验证的 `mcd-life` 构建模式（MCP 客户端 + 自动降级 + 零依赖 + 四个必备 md），新建独立仓库 `mcd-coupon-duel`，写了三个新模块：

- `scripts/duel.py`——状态机：立约 / 晨报 / 结算 + `data/duel.json` 持久化
- `scripts/roast_duel.py`——对赌专属话术（嘲讽 / 契约 / 晨报 / 战报 / 处刑）
- `scripts/card.py`——四张卡 HTML 生成器（含「债务山」可视化）

关键设计决策：

- **胜负判定巧用 MCP 原生特性**：券包接口只返回"当前还在的券"，本 Skill 用"标的券在不在包里" + `tradeEndDateTime` 推导胜负，不依赖任何"已用/已废"字段。
- **DEMO 用相对日期合成临期券**，保证任何时候跑 `duel.py demo` 都有"临终券"，评委零配置可验。
- **虚拟筹码 + 明说"认真但不较真"**，守住"不诱导赌博"红线。

### 第 3 轮 · 验证与产出

- `python duel.py demo` 一键生成 `examples/` 下四张卡（契约 / 晨报 / 处刑 / 战报），本地验证渲染正确（债务山柱高与金额成比例）。
- 四张必备文件齐全：`README.md` / `CONTEST_DECLARATION.md`（官方原文未改）/ `MCP_INTEGRATION.md` / `workbuddy.md`。

---

## 二、WorkBuddy 关键能力的使用

| 能力 | 在项目中的具体作用 |
|---|---|
| **MCP 接入** | 通过自定义连接器接入麦当劳 `mcd-mcp`（Streamable HTTP），LIVE 模式真实拉取券包 |
| **Skill 开发** | 产出标准 WorkBuddy Skill 结构（SKILL.md 触发词 + SOP + 红线，scripts 可执行） |
| **文件读写与执行** | 直接编写、运行、调试 Python 脚本；跑通 LIVE / DEMO 双模式 |
| **自动化** | SKILL.md 中说明用 `automation_update` 创建"每天 9:00 晨报"定时任务 |
| **概念打磨** | 用户连续否定后，从"换说法"转向"换用法"，把被动报告重构成有状态的对赌循环 |

---

## 三、与 mcd-life 的复用关系

本 Skill 有意复用 `mcd-life`（抢救麦券大作战）已验证的底座：

- `scripts/mcd_client.py` 原样复用（MCP 客户端 + 401 自动降级）
- 话术手法一致（换算成实物 / 精确到分钟 / 关注失去 / 损友吐槽），但新增"对赌"专属的挑衅与胜负张力
- 四个必备 md 的文件格式、红线口径完全对齐

这是对同一比赛主题的**两种玩法**，而非重复提交。

---

## 四、产出物

| 类型 | 文件 |
|---|---|
| Skill 主文件 | `SKILL.md` |
| MCP 集成说明 | `MCP_INTEGRATION.md` |
| 参赛声明 | `CONTEST_DECLARATION.md`（官方原文，未改动） |
| 核心脚本 | `scripts/duel.py`（状态机）<br>`scripts/roast_duel.py`（话术引擎）<br>`scripts/card.py`（卡片生成器）<br>`scripts/mcd_client.py`（MCP 客户端 + 自动降级，复用） |
| 参考资料 | `references/mcp-tools.md`（33 工具速查）<br>`references/offline_menu.json`（离线数据集） |
| 可视化产出 | `examples/01_契约卡.html`<br>`examples/02_晨报卡.html`<br>`examples/03_处刑卡.html`<br>`examples/04_战报卡.html` |

---

## 五、可复现性

本项目**零第三方依赖**，全部脚本仅使用 Python 标准库。评委可直接运行：

```bash
cd scripts

# 无需 Token 的离线演示（生成四张卡）
python duel.py demo

# 真实数据（需自行配置 MCP Token）
python duel.py start
python duel.py check
```

Demo 数据随仓库提供，离线可完整跑通全部流程。
