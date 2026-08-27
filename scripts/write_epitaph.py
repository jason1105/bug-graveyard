#!/usr/bin/env python3
import os
import sys
import json
import datetime
from openai import OpenAI

event_name = os.environ.get("EVENT_NAME", "issues")

# ── Extract issue data ──────────────────────────────────────────────
if event_name == "workflow_dispatch":
    title        = os.environ.get("INPUT_TITLE", "Unknown Bug")
    body         = os.environ.get("INPUT_BODY", "")
    issue_number = int(os.environ.get("INPUT_NUMBER") or 0)
    raw_labels   = os.environ.get("INPUT_LABELS", "")
    labels       = [l.strip() for l in raw_labels.split(",") if l.strip()]
    repo         = os.environ.get("REPO_FULL_NAME", "")
    issue_url    = f"https://github.com/{repo}/issues/{issue_number}" if issue_number else ""
    now          = datetime.datetime.utcnow()
    created_at   = now - datetime.timedelta(days=7)   # synthetic for testing
    closed_at    = now
else:
    title        = os.environ.get("EVENT_ISSUE_TITLE", "Unknown Bug")
    body         = os.environ.get("EVENT_ISSUE_BODY", "")
    issue_number = int(os.environ.get("EVENT_ISSUE_NUMBER") or 0)
    issue_url    = os.environ.get("EVENT_ISSUE_URL", "")
    raw_labels   = os.environ.get("EVENT_ISSUE_LABELS", "[]")
    try:
        label_objs = json.loads(raw_labels) if raw_labels else []
        labels = [l.get("name", "") for l in label_objs if isinstance(l, dict)]
    except Exception:
        labels = []
    created_str  = os.environ.get("EVENT_ISSUE_CREATED_AT", "")
    closed_str   = os.environ.get("EVENT_ISSUE_CLOSED_AT", "")
    def parse_dt(s):
        for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S%z"):
            try:
                return datetime.datetime.strptime(s, fmt).replace(tzinfo=None)
            except Exception:
                pass
        return datetime.datetime.utcnow()
    created_at = parse_dt(created_str)
    closed_at  = parse_dt(closed_str)

# 跳过失败告警 issue：它们带 ci-failure 标签，不该被写墓志铭
if "ci-failure" in labels:
    print("这是 CI 失败告警 issue，跳过墓志铭生成。")
    sys.exit(0)

# ── Calculate lifespan ─────────────────────────────────────────────
days_lived = max(0, (closed_at - created_at).days)

born_str  = created_at.strftime("%Y年%m月%d日")
died_str  = closed_at.strftime("%Y年%m月%d日")
labels_str = "、".join(labels) if labels else "无标签"

print(f"[epitaph] Issue #{issue_number}: {title}")
print(f"[epitaph] Lived {days_lived} days ({born_str} → {died_str})")
print(f"[epitaph] Labels: {labels_str}")

# ── Build prompt ───────────────────────────────────────────────────
body_excerpt = (body or "（无描述）")[:500]

prompt = f"""你是一个幽默的程序员，正在为一个已修复的 Bug 撰写墓志铭。请用诙谐、富有程序员文化的语气，为以下 Bug 写一段墓志铭。

要求（严格按照此格式，不要多余解释）：
第一行：Bug 的诗意别名（不超过10字，不含标点）
第二行：生卒年月（直接输出，如：生于 {born_str}，卒于 {died_str}）
第三行至第五行：2-3句精彩的墓志铭正文，可以包含技术梗、程序员黑话，每句一行
最后一行：一句令人回味的格言，以"格言："开头

Issue标题：{title}
描述：{body_excerpt}
标签：{labels_str}
存活天数：{days_lived} 天"""

# ── Call Claude API ────────────────────────────────────────────────
MODEL = os.environ.get("LLM_MODEL") or os.environ.get("OPENROUTER_MODEL") or "deepseek-v4-flash"
client = OpenAI(base_url=os.environ.get("LLM_BASE_URL") or "https://api.deepseek.com",
                api_key=os.environ.get("LLM_API_KEY") or os.environ.get("OPENROUTER_API_KEY", ""))
message = client.chat.completions.create(
    model=MODEL,
    max_tokens=512,
    messages=[{"role": "user", "content": prompt}]
)
epitaph_raw = message.choices[0].message.content.strip()
print(f"[epitaph] Raw response:\n{epitaph_raw}")

# ── Parse response ─────────────────────────────────────────────────
lines = [l.strip() for l in epitaph_raw.splitlines() if l.strip()]
alias        = lines[0] if len(lines) > 0 else title
dates_line   = lines[1] if len(lines) > 1 else f"生于 {born_str}，卒于 {died_str}"
body_lines   = []
motto_line   = ""
for l in lines[2:]:
    if l.startswith("格言：") or l.startswith("格言:"):
        motto_line = l.lstrip("格言：").lstrip("格言:")
    else:
        body_lines.append(l)
epitaph_body = "\n".join(body_lines)
if not epitaph_body.strip():           # 空正文兜底，避免无字墓志
    epitaph_body = "此 bug 已归档，愿它不再复现。"
motto        = motto_line or "愿代码世界少一个 bug，多一份宁静。"

epitaph_text = f"{epitaph_body}\n\n——{motto}"

# ── Build record ───────────────────────────────────────────────────
new_entry = {
    "id": f"issue-{issue_number}-{closed_at.strftime('%Y%m%d%H%M%S')}",
    "issue_number": issue_number,
    "issue_url": issue_url,
    "title": title,
    "alias": alias,
    "epitaph_text": epitaph_text,
    "motto": motto,
    "born": born_str,
    "died": died_str,
    "days_lived": days_lived,
    "labels": labels
}

# ── Read / update epitaphs.json ────────────────────────────────────
json_path = "epitaphs/epitaphs.json"
try:
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
except Exception:
    data = {"epitaphs": []}

epitaphs = data.get("epitaphs", [])
epitaphs.insert(0, new_entry)
epitaphs = epitaphs[:100]          # keep at most 100
data["epitaphs"] = epitaphs

with open(json_path, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"[epitaph] Written entry for issue #{issue_number}. Total: {len(epitaphs)}")