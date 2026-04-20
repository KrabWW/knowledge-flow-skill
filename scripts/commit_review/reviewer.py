"""
Anthropic SDK 审查逻辑（直连 API，无 CLI 开销）
"""

import os
from typing import Optional

import anthropic

# 全局回调：streaming token 进来时调用
_streaming_callback = None


def set_streaming_callback(cb):
    """设置流式输出回调"""
    global _streaming_callback
    _streaming_callback = cb


SYSTEM_PROMPT = """你是一个代码审查专家，检查代码是否符合需求文档。

## 输出要求
- 用中文回答
- 简洁，控制在300字以内
- 指出：是否符合需求、修改了什么、是否有问题"""


# 模型配置：优先用 sonnet（快），可通过环境变量覆盖
REVIEW_MODEL = os.environ.get("COMMIT_REVIEW_MODEL", "claude-sonnet-4-6")


def _get_client() -> anthropic.Anthropic:
    """创建 Anthropic 客户端，自动读取环境变量"""
    kwargs = {}
    # 优先用 ANTHROPIC_AUTH_TOKEN（Claude Code 使用），其次 ANTHROPIC_API_KEY
    api_key = os.environ.get("ANTHROPIC_AUTH_TOKEN") or os.environ.get("ANTHROPIC_API_KEY")
    if api_key:
        kwargs["api_key"] = api_key
    # 自定义 base_url（代理/企业端点）
    base_url = os.environ.get("ANTHROPIC_BASE_URL")
    if base_url:
        kwargs["base_url"] = base_url
    return anthropic.Anthropic(**kwargs)


def review_with_claude_code(
    diff: str,
    requirements: dict[str, str],
    changed_files: list[str],
    commit_msg: Optional[str] = None
) -> str:
    """
    使用 Anthropic SDK 直连 API 进行审查（实时流式输出 thinking）

    比 claude --print 子进程快 10 倍以上（跳过 CLI 初始化、MCP 加载等开销）。
    """

    # 构建需求文档内容
    req_content = "\n\n".join([
        f"=== {name} ===\n{content}"
        for name, content in requirements.items()
    ]) if requirements else "（未找到需求文档）"

    # 构建变更文件说明
    files_info = "\n".join([f"- {f}" for f in changed_files]) if changed_files else "（无）"

    # 构建用户消息
    user_message = f"""## 代码变更 (git diff)
{diff}

## 变更的文件
{files_info}

## Commit 消息
{commit_msg or "（无）"}

## 需求文档
{req_content}

## 审查步骤

**第一步：识别关联子集**
先判断这次变更涉及需求文档的哪些章节/模块，只提取相关的部分。如果这次变更与需求文档完全无关（如纯工具脚本、文档更新），明确说明"本次变更与需求文档无直接关联"。

**第二步：审查关联部分**
对识别出的关联子集，对比：
1. 变更是否符合该模块的规格说明
2. 是否有遗漏的边界情况
3. 是否有明显 bug 或不合理实现

**第三步：发现隐含业务规则（如有）**
如果代码中体现了需求文档未明确记载的业务规则（来自代码逻辑推断，或只有"某人知道"的隐含流程），用【新发现】标记单独输出：

【新发现】<规则名称>
<具体描述这个隐含规则，包括触发条件、行为描述>

## 输出要求
- 用中文回答
- 简洁，300字以内（不含【新发现】）
- 先说结论（符合/不符合/无关），再说明理由
- 如果无关，说明理由即可，不需要强行审查
- 如果发现隐含业务规则，在结论后用【新发现】格式输出，这部分不受字数限制"""

    try:
        client = _get_client()

        if _streaming_callback:
            _streaming_callback(f"[TEXT][DEBUG] SDK 直连 API | 模型: {REVIEW_MODEL} | Prompt: {len(user_message)} 字符\n")

        final_text_parts = []
        thinking_buf = ""

        # 流式调用 API
        with client.messages.stream(
            model=REVIEW_MODEL,
            max_tokens=1600,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        ) as stream:
            for event in stream:
                # 处理 thinking 事件
                if event.type == "content_block_delta":
                    delta = event.delta

                    # thinking 内容
                    if hasattr(delta, "thinking") and delta.thinking:
                        new_content = delta.thinking
                        if new_content and _streaming_callback:
                            _streaming_callback("[THINK]" + new_content)
                        thinking_buf += new_content

                    # text 内容
                    elif hasattr(delta, "text") and delta.text:
                        text = delta.text
                        final_text_parts.append(text)
                        if _streaming_callback:
                            _streaming_callback("[TEXT]" + text)

        full_text = "".join(final_text_parts)
        if full_text.strip():
            return full_text.strip()

        return "API 未返回有效内容"

    except anthropic.AuthenticationError:
        return "API 认证失败：请设置 ANTHROPIC_API_KEY 或 ANTHROPIC_AUTH_TOKEN 环境变量"
    except anthropic.APIConnectionError as e:
        return f"API 连接失败: {str(e)[:200]}"
    except anthropic.APIStatusError as e:
        return f"API 错误 ({e.status_code}): {str(e.message)[:200]}"
    except Exception as e:
        return f"审查失败: {str(e)}"


def quick_review(diff: str, commit_msg: Optional[str] = None) -> str:
    """快速审查，简化版"""

    user_message = f"""## 代码变更
{diff}
## Commit: {commit_msg or '（无）'}

请快速审查这段代码，给出主要改动点和是否有明显问题（简洁回答，100字以内）。"""

    try:
        client = _get_client()
        response = client.messages.create(
            model=REVIEW_MODEL,
            max_tokens=500,
            system="你是代码审查专家，简洁回答。",
            messages=[{"role": "user", "content": user_message}],
        )
        return response.content[0].text.strip() if response.content else "无输出"

    except Exception as e:
        return f"快速审查失败: {str(e)}"
