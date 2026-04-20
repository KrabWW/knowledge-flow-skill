---
name: knowledge-flow
description: 从飞书提取知识并回写到项目
trigger:
  - "知识回流"
  - "飞书知识"
  - "同步会议"
  - "会议纪要"
  - "wiki sync"
---

# 知识回流 Skill

从飞书的多媒体内容中提取知识，自动回写到项目知识库。

> **⚠️ 使用前必读：安装前置依赖**
>
> 本 Skill 依赖飞书 CLI 和相关 Skills。使用前请先运行一键安装器：
>
> ```bash
> npx @krab-jw/knowledge-flow-installer
> ```
>
> 安装器会自动配置：
> - ✅ 飞书 CLI (@larksuite/cli)
> - ✅ 飞书 Skills (23个)
> - ✅ 飞书应用认证
> - ✅ 本 Skill（从内网 Nacos 或外网 GitHub）
>
> **如已安装上述依赖，可直接使用本 Skill。**

## 使用方法

### 1. 同步会议纪要

> "把最近7天的飞书会议纪要同步到项目"

> "提取昨天的会议中关于 API 设计的讨论"

> "知识回流会议纪要，关键词: 性能优化"

### 2. 同步 Wiki 更新

> "检查飞书知识库的 API 设计文档更新"

> "同步 Wiki 中关于数据库 schema 的修改"

> "知识回流 Wiki，时间范围: 1w"

### 3. 提取消息待办

> "从飞书群聊中提取与本项目相关的待办事项"

> "汇总产品群中的需求讨论"

> "知识回流消息，关键词: bug, 优化"

### 4. 全量同步

> "知识回流全部内容，最近1个月"

> "同步飞书所有相关知识到项目"

## 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| source | 知识来源: meeting/wiki/doc/im/all | all |
| timeRange | 时间范围: 7d/1w/1m/1y | 7d |
| keywords | 关键词过滤 (数组) | [] |
| outputFormat | 输出格式: markdown/json/summary | summary |

## 输出位置

知识回写到项目以下位置:

```
project/
├── .knowledge/
│   ├── meetings/          # 会议纪要
│   ├── wiki/              # Wiki 文档
│   ├── decisions/         # 决策记录
│   └── action-items/      # 待办事项
└── README.md              # 自动更新项目摘要
```

## 示例命令

```bash
# 直接使用 lark-cli (高级用法)
lark-cli vc +list                    # 列出会议纪要
lark-cli wiki +list                  # 列出知识库
lark-cli im +message --help          # 发送消息
```

## 故障排除

### 认证过期

```bash
lark-cli auth login --recommend
```

### 权限不足

确保飞书应用有以下权限:
- `vc:video_minute:readonly` - 查看会议纪要
- `wiki:wiki:readonly` - 查看知识库
- `im:message` - 读取消息

### 更多帮助

```bash
lark-cli --help
lark-cli [command] --help
```
