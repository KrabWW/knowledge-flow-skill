#!/usr/bin/env python3
"""
CI 环境下的 Commit Review

用法:
    uv run python scripts/commit_review/ci_main.py --pr-number 123 --repo owner/repo

用于 GitHub Actions 等 CI 环境。
"""

import argparse
import os
import sys
from pathlib import Path

# 设置项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

# Windows stdout encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


def get_pr_diff(pr_number: int, repo: str) -> str:
    """通过 GitHub API 获取 PR 的 diff"""
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        return ""

    import urllib.request
    url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}"
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3.diff"
    })

    try:
        with urllib.request.urlopen(req) as response:
            return response.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"[WARN] Failed to fetch PR diff: {e}")
        return ""


def post_review_comment(pr_number: int, repo: str, body: str):
    """发布 PR 评论"""
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("[WARN] GITHUB_TOKEN not set, cannot post comment")
        return

    import urllib.request
    import json

    url = f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments"
    data = json.dumps({"body": body}).encode("utf-8")

    req = urllib.request.Request(url, data=data, headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    })

    try:
        with urllib.request.urlopen(req) as response:
            print(f"[OK] Posted review comment")
    except Exception as e:
        print(f"[WARN] Failed to post comment: {e}")


def write_to_lark(review_result: str, pr_info: dict):
    """
    将审查结果写入飞书文档（可选）

    需要配置:
    - LARK_APP_ID
    - LARK_APP_SECRET
    - LARK_DOC_TOKEN (目标文档 token)
    """
    app_id = os.environ.get("LARK_APP_ID")
    app_secret = os.environ.get("LARK_APP_SECRET")
    doc_token = os.environ.get("LARK_DOC_TOKEN")

    if not all([app_id, app_secret, doc_token]):
        print("[INFO] Lark credentials not configured, skipping")
        return

    # TODO: 实现飞书文档写入
    # 参考 lark-doc skill 或使用 lark-cli
    print("[INFO] Lark integration not yet implemented")


def main():
    parser = argparse.ArgumentParser(description="CI Commit Review")
    parser.add_argument("--pr-number", type=int, required=True, help="PR number")
    parser.add_argument("--repo", type=str, required=True, help="Owner/repo format")
    args = parser.parse_args()

    print(f"[Review] Commit Review for PR #{args.pr_number}")
    print("=" * 50)

    # 1. 获取 PR diff
    pr_diff = get_pr_diff(args.pr_number, args.repo)
    if not pr_diff:
        print("[ERROR] Could not fetch PR diff")
        sys.exit(1)

    # 2. 获取变更文件列表（简化处理）
    import subprocess
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only"],
            capture_output=True, text=True, encoding="utf-8", errors="replace"
        )
        changed_files = [f.strip() for f in result.stdout.strip().split("\n") if f.strip()]
    except Exception:
        changed_files = []

    # 3. 读取需求文档
    from commit_review.fetcher import get_requirements_docs
    requirements = get_requirements_docs()

    # 4. 审查
    from commit_review.reviewer import review_with_claude_code
    result = review_with_claude_code(
        diff=pr_diff[:5000],  # 限制大小
        requirements=requirements,
        changed_files=changed_files,
        commit_msg=f"PR #{args.pr_number}"
    )

    # 5. 输出结果
    print("\n" + "=" * 50)
    print("[Result] Review Result")
    print("=" * 50)
    print(result)

    # 6. 发布到 PR 评论
    comment_body = f"""## Commit Review 结果

{result}

---
*This review was generated automatically by Commit Review.*"""

    post_review_comment(args.pr_number, args.repo, comment_body)

    # 7. 可选：写入飞书文档
    write_to_lark(result, {"pr": args.pr_number, "repo": args.repo})

    # 输出到环境变量供 GitHub Actions 使用
    with open(os.environ.get("GITHUB_OUTPUT", "/dev/null"), "a") as f:
        f.write(f"REVIEW_RESULT={result}\n")


if __name__ == "__main__":
    main()
