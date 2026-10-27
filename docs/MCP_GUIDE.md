# 长龙航空 · 畅飞智能助手 - Model Context Protocol (MCP) 接入指南

> **Model Context Protocol (MCP)** 是由 Anthropic 提出并迅速成为行业标准的 AI 上下文协议。  
> 通过 MCP，您可以将 **Clairline（长龙航空放票监测助手）** 作为专属智能工具集挂载到 **Claude Desktop**、**Cursor**、**Antigravity**、**Windsurf** 等各类大模型助手或自主 Agent 中。

---

## 🌟 为什么支持“即时实时数据”？

很多用户担心：“AI 助手是不是只能查本地写死的数据，无法查到即时放票？”  
**答案是：Clairline MCP 原生打通长龙官方实时网关！**

- **即时查验直连**：`query_flight_tickets` 工具在被 AI 触发时，会直接穿透向浙江长龙航空官方后端发起在线查票请求，返回当班**真实剩余机位**、起降时刻与机型；
- **大盘日历缓存**：`get_route_calendar` 工具毫秒级索引本地 SQLite 数据库，过滤无票日与禁兑日，秒级呈现未来 60 天放票全貌；
- **操控后台巡检**：`add_patrol_monitor` 让大模型能够直接替您在后台添加轮巡任务，24 小时全自动监票。

---

## 🛠️ 提供的 6 大 MCP 工具 (Tools)

| 工具名称 | 作用说明 | 核心输入参数 |
| :--- | :--- | :--- |
| `query_flight_tickets` | **实时向长龙官方接口查票**，获取航班号、起降时间、机型、畅飞卡即时余票 | `from_city`, `to_city`, `date` (YYYY-MM-DD), `force_refresh` |
| `get_route_calendar` | 检索本地数据库中指定航线**未来 60 天放票日历**（已排除禁兑与无票日） | `from_city`, `to_city` |
| `get_direct_destinations` | 查询航网拓扑中从指定城市直飞可达的所有目的地（全国 397 条航线） | `from_city` (默认杭州) |
| `list_patrol_monitors` | 查询后台当前重点监控的航线清单与巡检状态 | 无 |
| `add_patrol_monitor` | 指示后台将一条航线添加到重点监控轮巡队列中 | `from_city`, `to_city`, `remark` (选填备注) |
| `get_user_profile` | 获取当前登录长龙会员档案、畅飞卡产品及绑定状态 | 无 |

---

## 🚀 接入模式配置 (任选一种即可)

### 模式 1：SSE 网络模式（推荐 Docker / 远程 NAS / 本地服务）

若您已通过 Docker（`docker-compose up -d`）或本地启动了 Web 服务（默认监听 3000 端口）：  
任何 MCP 客户端均可直接通过 HTTP/SSE 端点接入，**无需配置 Python 环境，零路径依赖**！

- **SSE URL**: `http://localhost:3000/sse`（若部署在 NAS 或云服务器，替换为对应局域网 IP）

#### 1. Cursor 配置 (`.cursor/mcp.json` 或 设置 -> MCP)
```json
{
  "mcpServers": {
    "clairline": {
      "url": "http://localhost:3000/sse"
    }
  }
}
```

#### 2. Antigravity 配置 (`~/.gemini/antigravity-ide/mcp_config.json`)
```json
{
  "mcpServers": {
    "clairline": {
      "url": "http://localhost:3000/sse"
    }
  }
}
```

---

### 模式 2：Docker 管道模式（标准 stdio）

若您使用 Docker 运行容器且客户端支持 stdio 命令，可直接调用 `docker exec`：

#### Claude Desktop 配置 (`claude_desktop_config.json`)
- **Windows 路径**: `%APPDATA%\Claude\claude_desktop_config.json`
- **macOS 路径**: `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "clairline": {
      "command": "docker",
      "args": [
        "exec",
        "-i",
        "clairline",
        "python",
        "-m",
        "backend.mcp_server"
      ]
    }
  }
}
```

---

### 模式 3：本地 Python 源码模式（标准 stdio）

若您直接从本地源码运行助手：

```json
{
  "mcpServers": {
    "clairline": {
      "command": "python",
      "args": [
        "-m",
        "backend.mcp_server"
      ],
      "cwd": "/path/to/ChanglongAirlines"
    }
  }
}
```
*(Windows 用户请将 cwd 填写为实际目录，例如 `"D:\\project\\ChanglongAirlines"`)*

---

## 💬 真实对话 Prompt 示例

将 MCP 挂载到 AI 助手后，您可以像与私人航空管家对话一样提出需求：

### 场景 1：查询当班实时机票与剩余座位
> **用户**：“帮我查一下这周末 2026-10-31 杭州飞阿勒泰有没有长龙畅飞卡的票？”  
> **AI（自动调用 `query_flight_tickets`）**：“正在为您实时向长龙航空官方接口发起查票... 查到了！GJ8775 航班 07:15 起飞，经停银川，当前畅飞卡可兑座位剩余 2 张，机型为 A320。建议您尽快在官方 App 下单兑换。”

### 场景 2：检索 60 天放票日历
> **用户**：“看看未来一个月杭州到西双版纳哪几天有放票？”  
> **AI（自动调用 `get_route_calendar`）**：“为您查询了杭州 ➔ 西双版纳的放票日历大盘。根据长龙航空提前 3 天起兑规则，未来 30 天共有 11 天有票可兑，主要集中在周二和周四的 GJ8023 班次...”

### 场景 3：让 AI 操控后台进行盯票监控
> **用户**：“我很想去喀什旅游，帮我把杭州到喀什加到后台监控列表里，备注写‘南疆深度游’。”  
> **AI（自动调用 `add_patrol_monitor`）**：“已成功将【杭州 ➔ 喀什】（备注：南疆深度游）添加到后台巡检队列！当前后台共重点监控 7 条航线，系统将在设定的时间自动轮询放票并刷新日历。”

### 场景 4：探索长龙航网拓扑
> **用户**：“从宁波出发，长龙航空都有直飞去哪里的航线？”  
> **AI（自动调用 `get_direct_destinations`）**：“长龙航空从宁波机场直飞可达的城市共有 16 个，包括重庆、贵阳、海口、昆明、西安、银川、长春等...”

---

## 🛡️ 数据安全与隐私保障

- **凭证仅在本地**：所有会员 Token 与会话信息完全存储在您本地容器或私有 SQLite 中，绝不经由任何第三方中继；
- **脱敏输出**：`get_user_profile` 工具对外输出时自动对手机号与身份证号进行脱敏掩码（如 `138****1234`），防止对话泄露敏感个人隐私。
