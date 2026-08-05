"""
用大模型给每条新闻写一句点评，再写一段结尾总结。

走 OpenAI 兼容接口，所以 DeepSeek / 智谱 / 月之暗面 / OpenAI / 硅基流动
这些都能用，只是换个 base_url 和模型名。

三个环境变量：
    LLM_API_KEY    你的 key（必填，不填就整个跳过，日报照常出，只是没点评）
    LLM_BASE_URL   接口地址，默认 https://api.deepseek.com/v1
    LLM_MODEL      模型名，默认 deepseek-chat

在 GitHub 上配：仓库 Settings -> Secrets and variables -> Actions -> New repository secret
"""

import json
import os
import urllib.error
import urllib.request

import config

DEFAULT_BASE_URL = "https://api.deepseek.com/v1"
DEFAULT_MODEL = "deepseek-chat"


def _chat(messages, timeout=120):
    """调一次 chat completions，返回文本内容。"""
    key = os.environ.get("LLM_API_KEY", "").strip()
    base = os.environ.get("LLM_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
    model = os.environ.get("LLM_MODEL", DEFAULT_MODEL)

    body = json.dumps({
        "model": model,
        "messages": messages,
        "temperature": 0.7,
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{base}/chat/completions",
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"].strip()


def _strip_fence(text):
    """模型有时会用 ```json 包起来，扒掉。"""
    t = text.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[1] if "\n" in t else t
        t = t.rsplit("```", 1)[0]
    return t.strip()


def enrich(data):
    """
    给 data 里每条加 comment 字段，再加一个 closing 字段。
    任何一步失败都只是少点东西，不影响日报生成。
    """
    if not config.ENABLE_COMMENT:
        return data
    if not os.environ.get("LLM_API_KEY", "").strip():
        print("  没配 LLM_API_KEY，跳过点评（日报照常生成）")
        return data

    items = []
    for sec in data["sections"]:
        for it in sec["items"]:
            items.append(it)
    if not items:
        return data

    # 把所有条目打包成一次请求，比一条一条调便宜也快
    listing = "\n\n".join(
        f"[{i + 1}] 标题：{it['title']}\n"
        f"    来源：{it.get('source', '')}\n"
        f"    摘要：{it.get('summary', '') or '（无摘要）'}"
        for i, it in enumerate(items)
    )

    # 有语气样本就当 few-shot 塞进去，比纯文字描述风格准得多
    voice_block = ""
    samples = [s for s in getattr(config, "VOICE_SAMPLES", []) if s.strip()]
    if samples:
        examples = "\n".join(f'- "{s.strip()}"' for s in samples)
        voice_block = f"""
点评要模仿下面这几句话的语气和用词习惯（内容不用一样，是学说话方式）：
{examples}
"""

    prompt = f"""下面是今天 AI 领域的 {len(items)} 条新闻。

{listing}

读者画像：
{config.AUDIENCE}

请为每一条写一句点评，要求：
{config.COMMENT_STYLE}
{voice_block}
然后再写一段结尾总结，要求：
{config.CLOSING_STYLE}

只输出 JSON，不要任何解释文字，不要 markdown 代码块，格式：
{{"comments": ["第1条的点评", "第2条的点评", ...], "closing": "结尾总结"}}
comments 数组必须正好 {len(items)} 个元素，顺序和上面编号一致。"""

    try:
        print(f"  → 让模型给 {len(items)} 条写点评")
        raw = _chat([
            {"role": "system",
             "content": "你是一个中文科技媒体的主编，判断准，说话直接，不说套话。"},
            {"role": "user", "content": prompt},
        ])
        parsed = json.loads(_strip_fence(raw))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "ignore")[:200]
        print(f"  ! 模型接口返回 {e.code}：{detail}")
        return data
    except Exception as e:
        print(f"  ! 点评生成失败，跳过：{e}")
        return data

    comments = parsed.get("comments") or []
    for it, c in zip(items, comments):
        if isinstance(c, str) and c.strip():
            it["comment"] = c.strip()

    closing = parsed.get("closing")
    if isinstance(closing, str) and closing.strip():
        data["closing"] = closing.strip()

    print(f"  ✓ 拿到 {len([i for i in items if i.get('comment')])} 条点评")
    return data
