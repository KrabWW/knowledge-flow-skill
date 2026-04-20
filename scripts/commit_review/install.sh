#!/bin/bash
# cccommit 一键安装脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  cccommit 一键安装${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# 1. 检查 uv
if ! command -v uv &> /dev/null; then
    echo -e "${YELLOW}⚠️  未找到 uv，正在安装...${NC}"
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
    echo -e "${GREEN}✓ uv 安装完成${NC}"
else
    echo -e "${GREEN}✓ uv 已安装: $(uv --version)${NC}"
fi

# 2. 检查 Claude Code CLI
if ! command -v claude &> /dev/null; then
    echo -e "${RED}✗ 未找到 Claude Code CLI${NC}"
    echo -e "${YELLOW}请先安装: npm install -g @anthropic-ai/claude-code${NC}"
    exit 1
else
    echo -e "${GREEN}✓ Claude Code CLI 已安装${NC}"
fi

# 3. 安装 Python 依赖
echo ""
echo -e "${BLUE}📦 安装 Python 依赖...${NC}"
cd "$(dirname "$0")/../.." || exit 1
uv sync --directory scripts/commit_review
echo -e "${GREEN}✓ 依赖安装完成${NC}"

# 4. 配置飞书环境变量
echo ""
echo -e "${BLUE}🔧 配置飞书环境变量${NC}"

# 检查是否已有配置
if [ -n "$LARK_DOC_URL" ]; then
    echo -e "${GREEN}✓ LARK_DOC_URL 已设置${NC}"
else
    echo -e "${YELLOW}请输入飞书需求文档 URL（留空使用默认值）:${NC}"
    read -r DOC_URL
    if [ -n "$DOC_URL" ]; then
        echo "export LARK_DOC_URL=\"$DOC_URL\"" >> ~/.bashrc
        echo "export LARK_DOC_URL=\"$DOC_URL\"" >> ~/.zshrc
        echo -e "${GREEN}✓ LARK_DOC_URL 已保存到 ~/.bashrc 和 ~/.zshrc${NC}"
    fi
fi

if [ -n "$LARK_KB_DOC_URL" ]; then
    echo -e "${GREEN}✓ LARK_KB_DOC_URL 已设置${NC}"
else
    echo -e "${YELLOW}请输入飞书知识库文档 URL（留空使用需求文档 URL）:${NC}"
    read -r KB_URL
    if [ -n "$KB_URL" ]; then
        echo "export LARK_KB_DOC_URL=\"$KB_URL\"" >> ~/.bashrc
        echo "export LARK_KB_DOC_URL=\"$KB_URL\"" >> ~/.zshrc
        echo -e "${GREEN}✓ LARK_KB_DOC_URL 已保存到 ~/.bashrc 和 ~/.zshrc${NC}"
    fi
fi

# 5. 设置 pre-commit hook
echo ""
echo -e "${BLUE}🔗 设置 pre-commit hook${NC}"
if [ -f .git/hooks/pre-commit ]; then
    echo -e "${YELLOW}⚠️  pre-commit hook 已存在，跳过${NC}"
else
    ln -sf ../../scripts/commit_review/pre-commit .git/hooks/pre-commit
    chmod +x .git/hooks/pre-commit
    echo -e "${GREEN}✓ pre-commit hook 已设置${NC}"
fi

# 6. 创建 skill 文件
SKILL_DIR=".claude/commands"
mkdir -p "$SKILL_DIR"

cat > "$SKILL_DIR/cccommit.md" << 'EOF'
---
name: "Commit Review"
description: "提交代码并触发 AI 审查 - 对比飞书需求文档检查代码一致性"
category: Workflow
tags: [commit, review, lark, feishu, pre-commit]
---

运行 Commit Review 流程，对比代码变更与飞书需求文档的一致性。

## 执行步骤

1. **检查 staged 变更**：如果没有 staged 的文件，提醒用户先 `git add`
2. **运行审查脚本**：`uv run python scripts/commit_review/main.py`
3. **处理审查结果**：
   - 显示审查结果
   - 如果用户确认，将结果写入飞书文档（知识回流）
4. **确认提交**：询问是否继续执行 `git commit`

## 用户决策选项

审查后会显示：
- 1. 修改代码（符合需求）→ 重新提交
- 2. 更新需求文档（记录新逻辑）→ 重新提交
- 3. 直接提交（认为当前实现合理）
- 4. 写入飞书（知识回流）
- 5. 取消提交

## 示例

```
用户输入: /cccommit
AI 执行: 检查 git staged 变更，运行审查脚本，显示结果，让用户决策
```

## 注意

- 如果没有 staged 变更，提示用户先 git add
- 知识回流目标默认为飞书需求文档（同一文档）
- 不拦截提交，最终决策权在用户
EOF

echo -e "${GREEN}✓ skill 文件已创建: $SKILL_DIR/cccommit.md${NC}"

# 完成
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✓ 安装完成！${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${BLUE}使用方法:${NC}"
echo -e "  ${YELLOW}手动触发:${NC} /cccommit"
echo -e "  ${YELLOW}自动触发:${NC} git commit（自动运行审查）"
echo ""
echo -e "${BLUE}配置环境变量（如果刚才未设置）:${NC}"
echo -e "  ${YELLOW}export LARK_DOC_URL=\"你的飞书文档URL\"${NC}"
echo -e "  ${YELLOW}export LARK_KB_DOC_URL=\"你的知识库URL\"${NC}"
echo ""
