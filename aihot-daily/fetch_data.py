"""
从 AI HOT 公开 API 拉数据，归一化成日报渲染需要的结构。

优先级：
  1) /api/v1/dailies/latest  —— 已经分好 5 个版块 + 主编导语 + 中文摘要（最省事）
  2) /api/v1/items?window=24h —— 日报当天还没生成（北京时间 08:00 前）时的降级方案

所有请求都是匿名只读，不需要 API Key。
"""

import json
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

BASE = "https://aihot.virxact.com"

# 必须带浏览器 UA，默认的 python-urllib / curl UA 会被 nginx 挡掉
UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

CN_TZ = timezone(timedelta(hours=8))

# items API 的英文 slug -> 日报里的中文版块名
CATEGORY_LABELS = {
    "ai-models": "模型发布/更新",
    "ai-products": "产品发布/更新",
    "industry": "行业动态",
    "paper": "论文研究",
    "tip": "技巧与观点",
}

# 版块固定顺序
SECTION_ORDER = [
    "模型发布/更新",
    "产品发布/更新",
    "行业动态",
    "论文研究",
    "技巧与观点",
]


def _get(path, retries=3):
    """带重试的匿名 GET，返回解析后的 JSON；404 返回 None。"""
    url = BASE + path
    last_err = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": UA,
                "Accept": "application/json",
            })
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            # 429 / 503 按 Retry-After 退避
            if e.code in (429, 503):
                wait = int(e.headers.get("Retry-After", 5))
                print(f"  [{e.code}] 限流，等待 {wait}s 后重试")
                time.sleep(wait)
                last_err = e
                continue
            last_err = e
        except Exception as e:  # 网络抖动
            last_err = e
        time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"请求失败 {url}: {last_err}")


def to_beijing(iso_str):
    """ISO 8601 UTC -> 北京时间 datetime。"""
    if not iso_str:
        return None
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        return dt.astimezone(CN_TZ)
    except Exception:
        return None


def human_time(iso_str, now=None):
    """把时间戳转成人话：'2 小时前' / '今天 09:48' / '8月4日'。"""
    dt = to_beijing(iso_str)
    if not dt:
        return ""
    now = now or datetime.now(CN_TZ)
    delta = now - dt
    mins = delta.total_seconds() / 60
    if mins < 60:
        return f"{max(1, int(mins))} 分钟前"
    if mins < 60 * 24:
        return f"{int(mins // 60)} 小时前"
    if dt.date() == (now.date() - timedelta(days=1)):
        return f"昨天 {dt.strftime('%H:%M')}"
    return f"{dt.month} 月 {dt.day} 日"


def from_daily(payload):
    """把 /api/v1/dailies/latest 的返回归一化。"""
    report = payload["report"]
    lead = report.get("lead") or {}

    sections = []
    for sec in report.get("sections", []):
        items = []
        for it in sec.get("items", []):
            links = it.get("links") or {}
            items.append({
                "title": it.get("title", "").strip(),
                "summary": (it.get("summary") or "").strip(),
                "source": (it.get("source") or {}).get("name", ""),
                "url": links.get("original") or links.get("aihot") or "",
                "aihot_url": links.get("aihot") or "",
                "time_label": "",
            })
        if items:
            sections.append({"label": sec.get("label", "其它"), "items": items})

    # 按固定顺序排版块
    sections.sort(key=lambda s: SECTION_ORDER.index(s["label"])
                  if s["label"] in SECTION_ORDER else 99)

    flashes = []
    for f in report.get("flashes", []):
        links = f.get("links") or {}
        flashes.append({
            "title": f.get("title", "").strip(),
            "source": (f.get("source") or {}).get("name", ""),
            "url": links.get("original") or links.get("aihot") or "",
            "time_label": human_time(f.get("publishedAt")),
        })

    return {
        "date": report.get("date"),
        "generated_at": report.get("generatedAt"),
        "lead_title": (lead.get("title") or "").strip(),
        "lead_paragraph": (lead.get("leadParagraph") or "").strip(),
        "sections": sections,
        "flashes": flashes,
        "window": "按北京时间整日切片",
        "mode": "daily",
    }


def from_items(payload):
    """把 /api/v1/items 的返回按 category 分组，归一化成同样的结构。"""
    buckets = {}
    for it in payload.get("items", []):
        label = CATEGORY_LABELS.get(it.get("category"), "其它")
        links = it.get("links") or {}
        buckets.setdefault(label, []).append({
            "title": (it.get("title") or "").strip(),
            "summary": (it.get("summary") or "").strip(),
            "source": (it.get("source") or {}).get("name", ""),
            "url": links.get("original") or links.get("aihot") or "",
            "aihot_url": links.get("aihot") or "",
            "time_label": human_time(it.get("publishedAt") or it.get("discoveredAt")),
        })

    sections = [{"label": lbl, "items": buckets[lbl]}
                for lbl in SECTION_ORDER if lbl in buckets]
    if "其它" in buckets:
        sections.append({"label": "其它", "items": buckets["其它"]})

    today = datetime.now(CN_TZ)
    total = sum(len(s["items"]) for s in sections)
    return {
        "date": today.strftime("%Y-%m-%d"),
        "generated_at": today.isoformat(),
        "lead_title": "过去 24 小时 AI 圈速览",
        "lead_paragraph": (
            f"今天的编辑版日报还没出，这里是过去 24 小时 AI HOT 精选的 {total} 条动态，"
            f"按模型、产品、行业、论文、观点五类分好，按发布时间倒序。"
        ),
        "sections": sections,
        "flashes": [],
        "window": "过去 24 小时滚动窗口",
        "mode": "items",
    }


def fetch(date=None):
    """
    抓一期日报。
      date=None  -> 最新一期，拿不到就降级到 24h 精选
      date='YYYY-MM-DD' -> 指定日期的历史日报
    """
    if date:
        print(f"→ 拉取 {date} 的日报")
        payload = _get(f"/api/v1/dailies/{date}")
        if not payload:
            raise RuntimeError(f"{date} 没有日报")
        return from_daily(payload)

    print("→ 拉取最新日报 /api/v1/dailies/latest")
    payload = _get("/api/v1/dailies/latest")
    if payload:
        data = from_daily(payload)
        print(f"  拿到 {data['date']} 日报，"
              f"{len(data['sections'])} 个版块 / "
              f"{sum(len(s['items']) for s in data['sections'])} 条")
        return data

    print("  日报暂未生成（北京时间 08:00 前），降级到 24 小时精选")
    payload = _get("/api/v1/items?mode=selected&window=24h&limit=100")
    data = from_items(payload)
    print(f"  拿到 {sum(len(s['items']) for s in data['sections'])} 条精选")
    return data


if __name__ == "__main__":
    print(json.dumps(fetch(), ensure_ascii=False, indent=2)[:3000])
