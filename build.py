"""
主入口：拉数据 -> 生成 HTML -> 截成长图 -> 更新归档首页。

用法：
    python build.py                 # 生成最新一期
    python build.py --date 2026-08-04   # 补一期历史日报
    python build.py --no-image      # 只出 HTML，不截图（本地快速预览）
    python build.py --mock          # 用假数据跑一遍，验证排版
"""

import argparse
import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

from fetch_data import CN_TZ, fetch
from render import esc, format_date_cn, render_html

ROOT = Path(__file__).parent
SITE = ROOT / "site"
ARCHIVE = SITE / "archive"
IMG = SITE / "img"


def screenshot(html_path, png_path):
    """用 Playwright 把整页 HTML 截成一张长图。"""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("  ! 没装 playwright，跳过截图")
        return False

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(args=["--no-sandbox"])
            # deviceScaleFactor=2 出 2 倍图，手机上看不糊
            page = browser.new_page(
                viewport={"width": 760, "height": 1200},
                device_scale_factor=2,
            )
            page.goto(f"file://{html_path.resolve()}")
            page.wait_for_timeout(600)  # 等字体加载
            page.locator(".page").screenshot(path=str(png_path))
            browser.close()
        size_kb = png_path.stat().st_size / 1024
        print(f"  ✓ 长图 {png_path.name}（{size_kb:.0f} KB）")
        return True
    except Exception as e:
        print(f"  ! 截图失败：{e}")
        return False


def build_index():
    """扫描 archive 目录，重建归档首页。"""
    entries = []
    for f in sorted(ARCHIVE.glob("*.html"), reverse=True):
        date = f.stem
        meta_file = ARCHIVE / f"{date}.json"
        title, count = "", 0
        if meta_file.exists():
            try:
                m = json.loads(meta_file.read_text("utf-8"))
                title, count = m.get("lead_title", ""), m.get("count", 0)
            except Exception:
                pass
        entries.append({"date": date, "title": title, "count": count,
                        "has_img": (IMG / f"{date}.png").exists()})

    rows = []
    for i, e in enumerate(entries):
        tag = '<span class="latest">最新</span>' if i == 0 else ""
        img = (f'<a class="img" href="img/{e["date"]}.png">长图</a>'
               if e["has_img"] else "")
        rows.append(f"""
      <li>
        <a class="main" href="archive/{e['date']}.html">
          <span class="date">{esc(format_date_cn(e['date']))}{tag}</span>
          <span class="title">{esc(e['title'] or '——')}</span>
        </a>
        <span class="side"><span class="count">{e['count']} 条</span>{img}</span>
      </li>""")

    stamp = datetime.now(CN_TZ).strftime("%Y-%m-%d %H:%M")
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AI 日报 · 归档</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:#f4f5f7;font-family:"Noto Sans CJK SC","PingFang SC","Microsoft YaHei",-apple-system,sans-serif;color:#16181d;padding:48px 20px}}
.wrap{{max-width:760px;margin:0 auto;background:#fff;border-radius:12px;padding:44px 40px}}
h1{{font-size:34px;font-weight:900;letter-spacing:-.02em}}
h1 span{{color:#1a6b5a}}
.sub{{color:#767d8a;font-size:14px;margin:10px 0 30px;padding-bottom:22px;border-bottom:3px solid #16181d}}
ul{{list-style:none}}
li{{display:flex;align-items:center;gap:14px;padding:16px 0;border-bottom:1px solid #e6e8ec}}
a.main{{flex:1;min-width:0;text-decoration:none;color:inherit}}
.date{{display:block;font-size:13px;color:#767d8a;margin-bottom:5px}}
.latest{{background:#1a6b5a;color:#fff;font-size:11px;padding:2px 7px;border-radius:4px;margin-left:8px}}
.title{{display:block;font-size:16px;font-weight:600;line-height:1.5}}
a.main:hover .title{{color:#1a6b5a}}
.side{{display:flex;align-items:center;gap:10px;flex-shrink:0}}
.count{{font-size:12px;color:#767d8a;background:#f2f3f5;padding:3px 9px;border-radius:999px}}
a.img{{font-size:12px;color:#1a6b5a;text-decoration:none;border:1px solid #cfe0da;padding:3px 9px;border-radius:999px}}
.foot{{margin-top:32px;font-size:12.5px;color:#767d8a;text-align:center;line-height:1.9}}
.foot a{{color:#1a6b5a;text-decoration:none}}
</style>
</head>
<body>
  <div class="wrap">
    <h1>AI <span>日报</span></h1>
    <div class="sub">每天北京时间 08:30 自动生成 · 共 {len(entries)} 期 · 更新于 {stamp}</div>
    <ul>{''.join(rows) if rows else '<li>还没有内容</li>'}</ul>
    <div class="foot">数据来源：<a href="https://aihot.virxact.com">AI HOT</a></div>
  </div>
</body>
</html>"""
    (SITE / "index.html").write_text(html, "utf-8")
    print(f"  ✓ 归档首页（{len(entries)} 期）")


def mock_data():
    """假数据，用来本地验证排版，不消耗 API。"""
    return {
        "date": datetime.now(CN_TZ).strftime("%Y-%m-%d"),
        "generated_at": datetime.now(CN_TZ).isoformat(),
        "lead_title": "今天最该盯的是模型层：两家同时把长上下文推到新档位",
        "lead_paragraph": (
            "过去 24 小时抓到 18 条精选，海外 12 条。主线只有一条：模型层在长上下文和"
            "推理成本上又打了一轮，而应用层还在消化上一轮的能力。对做内容和做工具的人来说，"
            "值得关注的是成本曲线往下走之后，哪些原本不成立的产品形态开始成立了。"
        ),
        "window": "过去 24 小时滚动窗口",
        "mode": "items",
        "sections": [
            {"label": "模型发布/更新", "items": [
                {"title": "某厂发布新一代基础模型，上下文窗口拉到 200 万 token",
                 "summary": "官方给出的基准显示长文档检索准确率比上代提升明显，同时把每百万 token 的价格砍掉近四成。目前先对企业客户开放，个人开发者需要排队申请。",
                 "source": "官方博客", "url": "https://example.com/a-very-long-url-path/model-release-2026",
                 "time_label": "3 小时前"},
                {"title": "开源社区放出一个 7B 的推理特化模型，数学基准逼近闭源中杯",
                 "summary": "权重和训练配方全部公开，采用宽松许可证，可商用。作者强调只用了公开数据集，没有做基准污染。",
                 "source": "Hugging Face", "url": "https://example.com/open-weights-7b",
                 "time_label": "9 小时前"},
            ]},
            {"label": "产品发布/更新", "items": [
                {"title": "主流编辑器接入 Agent 模式，可以直接跨文件重构",
                 "summary": "不再是补全单个函数，而是给一句自然语言指令后自己规划改动范围、跑测试、提 PR。灰度中，需要手动打开开关。",
                 "source": "TechCrunch", "url": "https://example.com/editor-agent-mode",
                 "time_label": "5 小时前"},
            ]},
            {"label": "行业动态", "items": [
                {"title": "监管机构就训练数据来源发布征求意见稿",
                 "summary": "核心是要求披露训练集里受版权保护内容的占比，并给权利人留出退出通道。意见征集期 60 天，业界普遍认为最终版会比草案宽松。",
                 "source": "路透社", "url": "https://example.com/regulation-draft",
                 "time_label": "昨天 22:14"},
            ]},
            {"label": "论文研究", "items": [
                {"title": "一篇关于稀疏注意力的论文把长序列推理显存降了一半",
                 "summary": "思路是在推理阶段动态丢弃低权重的 KV 缓存，作者在多个开源模型上复现，质量损失控制在 1% 以内。代码已开源。",
                 "source": "arXiv", "url": "https://example.com/sparse-attention-paper",
                 "time_label": "12 小时前"},
            ]},
            {"label": "技巧与观点", "items": [
                {"title": "为什么大部分 Agent 项目死在了第二周",
                 "summary": "作者复盘了十几个内部项目，结论是失败原因很少是模型能力不够，多数是没有把任务边界和失败兜底想清楚，导致 Demo 惊艳、上线崩溃。",
                 "source": "个人博客", "url": "https://example.com/why-agents-fail",
                 "time_label": "7 小时前"},
            ]},
        ],
        "flashes": [
            {"title": "某云厂商下调推理实例价格", "source": "官网", "time_label": "2 小时前", "url": ""},
            {"title": "一家 AI 搜索创业公司完成新一轮融资", "source": "36氪", "time_label": "6 小时前", "url": ""},
        ],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", help="补生成指定日期的日报 YYYY-MM-DD")
    ap.add_argument("--no-image", action="store_true", help="跳过截图")
    ap.add_argument("--mock", action="store_true", help="用假数据验证排版")
    args = ap.parse_args()

    ARCHIVE.mkdir(parents=True, exist_ok=True)
    IMG.mkdir(parents=True, exist_ok=True)

    print("=" * 52)
    data = mock_data() if args.mock else fetch(args.date)

    total = sum(len(s["items"]) for s in data["sections"])
    if total == 0:
        print("! 一条内容都没有，本次不生成，直接退出")
        return 0

    date = data["date"]
    html_path = ARCHIVE / f"{date}.html"
    png_path = IMG / f"{date}.png"

    html_path.write_text(render_html(data), "utf-8")
    print(f"  ✓ HTML {html_path.name}")

    (ARCHIVE / f"{date}.json").write_text(json.dumps(
        {"date": date, "lead_title": data.get("lead_title", ""),
         "count": total, "mode": data.get("mode")},
        ensure_ascii=False), "utf-8")

    if not args.no_image:
        screenshot(html_path, png_path)

    # 最新一期同时放一份到根目录，方便固定链接引用
    shutil.copy(html_path, SITE / "latest.html")
    if png_path.exists():
        shutil.copy(png_path, SITE / "latest.png")

    build_index()

    print(f"完成：{date} · {total} 条")
    print("=" * 52)
    return 0


if __name__ == "__main__":
    sys.exit(main())
