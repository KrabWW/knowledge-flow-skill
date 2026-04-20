---
name: knowledge-flow
displayName: 知识回流
version: 1.0.0
description: 从飞书提取知识并自动回写到项目 - 支持会议纪要、Wiki文档、群聊消息
author: krab-jw
category: integration
tags: [feishu, lark, knowledge, sync, automation]
---

# 知识回流 Skill

从飞书的多媒体内容中提取知识，自动回写到项目知识库，支持会议纪要、Wiki文档、群聊消息等多种数据源。

## 功能特性

### ✅ 会议纪要同步
- 自动提取飞书会议纪要和待办事项
- 按时间范围过滤（1d、1w、1m、1y）
- 支持关键词过滤
- 自动保存到 `.knowledge/meetings/`

### ✅ Wiki 文档追踪
- 监控知识库文档更新
- 检测 API 设计文档变更
- 自动保存到 `.knowledge/wiki/`

### ✅ 群聊消息汇总
- 从群聊中提取项目相关信息
- 自动识别待办事项
- 按关键词分类
- 保存到 `.knowledge/action-items/`

### ✅ 智能关键词过滤
- 只提取相关内容
- 支持多个关键词
- 自动去重

### ✅ 多格式输出
- Markdown 格式（默认）
- JSON 格式（适合程序处理）
- 摘要格式（快速浏览）

### ✅ 代码审查回流（自动 Hook）
- Git commit 时自动触发
- 对比代码变更与飞书需求文档
- 使用 Claude Code 检查一致性
- 将审查结果写回飞书文档
- 提取【新发现】标注为粉色批注

### ✅ 平台兼容
- Claude Code（主要支持）
- GitHub Copilot（兼容层）

## ⚠️ 使用前必读：一键安装

**本 Skill 依赖飞书 CLI 和相关工具，请先运行一键安装器：**

```bash
npx @krab-jw/knowledge-flow-installer
```

**安装器会自动配置：**
- ✅ 飞书 CLI (@larksuite/cli)
- ✅ 飞书 Skills (23个)
- ✅ 飞书应用认证
- ✅ 本 Skill（从内网 Nacos 或外网 GitHub）

**如已安装上述依赖，可直接使用本 Skill。**

---

## 手动安装步骤（可选）

如果你 prefer 手动安装：

### 1. 安装飞书 CLI

```bash
npm install -g @larksuite/cli
```

### 2. 安装飞书 CLI Skills

```bash
npx skills add larksuite/cli -y -g
```

### 3. 配置飞书应用

访问 [飞书开放平台](https://open.feishu.cn/) 创建应用并配置权限：

**必需权限：**
- `vc:video_minute:readonly` - 查看会议纪要
- `wiki:wiki:readonly` - 查看知识库
- `im:message` - 读取消息
- `im:chat` - 访问群聊

### 4. 完成认证

```bash
lark-cli config init
lark-cli auth login --recommend
```

## 使用方法

### 在 Claude Code 中使用

```
知识回流会议纪要，最近7天
```

```
把昨天的飞书会议中关于 API 设计的讨论同步到项目
```

```
检查飞书知识库的数据库文档更新
```

```
从产品群中提取与 bug 相关的待办事项
```

### 代码审查回流（自动触发）

```
启用代码提交审查
```

```
配置 Commit Review Hook
```

**功能说明：**
- 每次 `git commit` 时自动触发
- 对比代码变更与飞书需求文档
- 使用 Claude Code 检查一致性
- 将审查结果写回飞书文档
- 提取【新发现】标注为粉色批注

**安装 Hook：**
```bash
cd /path/to/your/project
bash scripts/commit_review/install.sh
```

**环境变量配置：**
```bash
# 飞书需求文档 URL（必需）
export LARK_DOC_URL="https://www.feishu.cn/docx/..."

# 知识回流目标文档（可选，默认等于需求文档）
export LARK_KB_DOC_URL="https://www.feishu.cn/docx/..."
```

**手动触发审查：**
```bash
# 通过 Claude Code
运行审查：检查当前代码与需求文档的一致性

# 直接运行脚本
uv run python scripts/commit_review/main.py
```

**跳过审查（临时）：**
```bash
git commit --no-verify -m "your message"
```

### 参数说明

| 参数 | 说明 | 可选值 | 默认值 |
|------|------|--------|--------|
| source | 知识来源 | meeting, wiki, im, doc, all | all |
| timeRange | 时间范围 | 1d, 1w, 1m, 1y | 7d |
| keywords | 关键词过滤 | 字符串数组 | [] |
| outputFormat | 输出格式 | markdown, json, summary | summary |

## 输出结构

知识回写到项目以下位置：

```
项目根目录/.knowledge/
├── meetings/          # 会议纪要
│   └── 2024-04-20-API设计讨论.md
├── wiki/              # Wiki 文档
│   └── database-schema-changes.md
├── decisions/         # 决策记录
│   └── adopt-redis.md
└── action-items/      # 待办事项
    └── bug-fix-tasks.md
```

## 高级用法

### 直接使用飞书 CLI

```bash
# 查看会议纪要
lark-cli vc +list

# 查看知识库
lark-cli wiki +list

# 发送消息
lark-cli im +message --help
```

### 自定义输出位置

设置环境变量：

```bash
export KNOWLEDGE_FLOW_DIR="$PROJECT/docs/knowledge"
```

## 依赖项

- @larksuite/cli >= 1.0.0
- larksuite/cli skills
- Node.js >= 14.0.0

## 故障排除

### 认证失败

```bash
lark-cli auth login --recommend
```

### 权限不足

检查飞书应用权限配置，确保已授予所需权限。

### Skill 未生效

```bash
# 检查 skill 目录
ls ~/.claude/skills/knowledge-flow

# 重启 Claude Code
```

## 版本历史

- **1.0.0** (2026-04-20)
  - 初始版本
  - 支持会议纪要、Wiki、群聊消息
  - 支持 Claude Code 和 Copilot

## 许可证

MIT

## 作者

krab-jw

## 相关链接

- [npm 包](https://www.npmjs.com/package/@krab-jw/knowledge-flow-installer)
- [GitHub 仓库](https://github.com/KrabWW/knowledge-flow-skill)
- [飞书开放平台](https://open.feishu.cn/)
- [飞书 CLI 文档](https://github.com/larksuite/cli)
