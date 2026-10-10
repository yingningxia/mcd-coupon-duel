# MCP 集成说明 · MCP_INTEGRATION.md

本文说明「麦麦对赌 2.0」实际使用的麦当劳 MCP Server、Tool、调用流程与业务价值。

---

## 一、使用的 MCP Server

| 项 | 值 |
|---|---|
| Server 名称 | `mcd-mcp` |
| 端点 | `https://mcp.mcd.cn` |
| 传输协议 | Streamable HTTP |
| 鉴权方式 | `Authorization: Bearer <MCP Token>` |
| Token 获取 | [open.mcd.cn/mcp](https://open.mcd.cn/mcp)，手机号登录后在控制台激活 |
| 限流 | 官方限制 600 次/分钟；本 Skill 实际调用量极低（立约 1 次 + 每日晨报 1 次） |

**配置方式**（WorkBuddy 自定义连接器 / 任意 MCP 客户端）：

```json
{
  "mcpServers": {
    "mcd-mcp": {
      "type": "streamablehttp",
      "url": "https://mcp.mcd.cn",
      "headers": { "Authorization": "Bearer YOUR_MCP_TOKEN" }
    }
  }
}
```

> 仓库内所有配置均使用 `YOUR_MCP_TOKEN` 占位符，不含任何真实凭据。

**响应解包要点**：MCP 返回体中的干净业务数据位于 `result.structuredContent`，
而非 `content[0].text`。`scripts/mcd_client.py` 的 `_parse_mcp_response()` 优先读取前者。

---

## 二、实际调用的 Tool 清单

| Tool | 用途 | 本 Skill 用它做什么 |
|---|---|---|
| `query-my-coupons` | 我的券包 | **核心数据源**。立约时挑出 `tradeEndDateTime` 在 7 天内的券作为赌注标的；晨报时重查，用"券是否还在包里"判定胜负 |
| `now-time-info` | 当前时间 | 算第几天、剩几天、是否已到期 |
| `query-nearby-stores` | 附近门店 | 晨报行动提示：结合券可用时段与门店营业时间，判断"现在出门还来不来得及用这张"（三线交叉之一） |
| `query-my-account` | 积分账户 | 可选：把 `currentMouthExpirePoint`（本月将作废积分）也拉进赌约标的 |
| `query-meals` / `calculate-price` | 菜单 / 算价 | 未来接入"一键帮用掉"时用于生成下单方案（当前版本聚焦对赌循环，下单为可选扩展） |

> 本 Skill **只读取数据，不写入**。唯一写入动作 `create-order` 若存在，需用户明确二次确认。

---

## 三、调用流程

### 立约 → 晨报 → 结算 的游戏循环

```
① query-my-coupons ─┐
                     ├─→ ② 立约（duel.py start）
   now-time-info ────┘         · 挑 7 天内到期券 = 赌注标的
                              · 持久化到 data/duel.json
                              · 生成契约卡
                                        │
③（每日）query-my-coupons ────────────┤ ④ 晨报（duel.py check）
                                        │   · 标的券消失且未过期 → 赢这张
                                        │   · 还在包里 → 下战书（嘲讽）
                                        │   · 已过期还在包里 → 输这张
                                        ↓
                              ⑤ 结算（到期或全清自动触发）
                                 · 赢 → 战报卡（省钱战神）
                                 · 输 → 处刑卡 + 债务山（白扔金额可视化）
```

### 「券消失 = 被用了 = 赢这张」的判定逻辑

麦当劳券包接口只返回**当前还在的券**，过期会被静默移除。本 Skill 复用这一特性做胜负判定：

- 立约时记录每张标的券的 `couponId` 与 `tradeEndDateTime`
- 晨报时重查券包，若某标的 `couponId` **不在当前包里**：
  - 且 `now <= tradeEndDateTime` → 它在到期前消失了 = 你用了它 = **赢这张**
  - 且 `now > tradeEndDateTime` → 它过期后消失 = 你没用 = **输这张**
- 若标的券**还在包里且未过期** → 继续施压（战书）

这套判定不需要"已用券"接口，完全由 MCP 原生返回的"在/不在包里"推导，是 MCP 原生能力的巧妙用法。

---

## 四、业务价值

### 1. 把"存量查询"变成"一场赌约"

`query-my-coupons` 单独用，只能回答"我有什么券"。本 Skill 把它变成赌桌：券是筹码，到期是 deadline，胜负是结局。用户从"看报告的人"变成"赌局里的玩家"。

### 2. 用 MCP 原生特性做胜负判定

"券在不在包里"是 MCP 天然返回的信息，本 Skill 不依赖任何"已用/已废"字段，仅用 `couponId` 集合差 + `tradeEndDateTime` 时间比较就完成胜负裁决——零额外接口。

### 3. 驱动真实的下单行为

战书的落点永远是"快去用"。晨报给出"现在出门还来不来得及"（门店 × 券时段三线交叉），让用户能立刻行动，而不是只看一个数字。

---

## 五、工程上的稳健性设计

| 设计 | 目的 |
|---|---|
| **自动降级** | Token 失效 / 401 / 断网时不抛异常，切换到 DEMO 模式继续跑。演示与开发永不中断 |
| **零第三方依赖** | 全部脚本只用 Python 标准库，评委 clone 下来即可运行 |
| **状态持久化** | 对赌进度落 `data/duel.json`，跨天、跨会话连续；该目录已在 `.gitignore` 排除，不含个人数据 |
| **虚拟筹码** | 赌注纯虚拟，明说"认真但不较真"，不诱导真实赌博 |

---

## 六、数据合规

- 所有数据来自使用者**自己账号**的 MCP 实时查询，本地处理，不外传
- 仓库不含任何真实 Token、账号或个人信息（详见 `CONTEST_DECLARATION.md`）
- `data/`（本地对赌账本）已在 `.gitignore` 中排除
- 只读取，不写入（除非用户明确确认下单）
