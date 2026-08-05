# AI 日报自动生成

每天自动从 AI HOT 拉当天的 AI 资讯，按「模型 / 产品 / 行业 / 论文 / 观点」五类排好版，
输出一个网页 + 一张可以直接发朋友圈和公众号的长图。

**运行成本：0 元。** 不需要服务器，不需要 API Key，跑在 GitHub 的免费额度里。

---

## 为什么是 0 元

| 环节 | 用什么 | 花多少 |
|---|---|---|
| 数据 | AI HOT 公开 API，匿名只读 | 免费 |
| 每天定时跑 | GitHub Actions | 公开仓库无限时长，免费 |
| 存网页和图 | GitHub Pages | 免费 |
| 出长图 | Playwright 截图，跑在 Actions 里 | 免费 |

每天跑一次约 1–2 分钟。就算你把仓库设成私有，免费额度也是每月 2000 分钟，一天两分钟一个月才用 60 分钟，一样够。

---

## 部署（大概 5 分钟）

**1. 建仓库**

在 GitHub 新建一个仓库，**选 Public**（公开仓库的 Actions 时长不限量），把这个目录里的文件全传上去。

**2. 打开 Pages**

仓库 → Settings → Pages → Source 选 **GitHub Actions**。

**3. 给 Actions 写权限**

仓库 → Settings → Actions → General → 拉到最下面 Workflow permissions →
选 **Read and write permissions** → Save。

（这一步是为了让它能把每天生成的结果 commit 回仓库存档，不做的话推送会失败。）

**4. 手动跑一次验证**

仓库 → Actions → 左边选「生成 AI 日报」→ 右边 **Run workflow** → 绿色对勾就是成了。

跑完之后访问：

```
https://<你的用户名>.github.io/<仓库名>/           归档首页
https://<你的用户名>.github.io/<仓库名>/latest.html  永远指向最新一期
https://<你的用户名>.github.io/<仓库名>/latest.png   最新一期的长图
```

`latest.png` 这个链接是固定的，存下来，以后每天直接打开右键存图就能发出去。

---

## 本地跑

```bash
pip install -r requirements.txt
python -m playwright install chromium

python build.py                  # 生成最新一期
python build.py --mock           # 用假数据看排版，不联网
python build.py --no-image       # 只出 HTML，跳过截图（快）
python build.py --date 2026-08-04  # 补一期历史日报
```

产物都在 `site/` 下面，直接双击 `site/index.html` 就能看。

---

## 时间怎么定的

AI HOT 的编辑版日报是**北京时间每天 08:00** 生成的，所以 workflow 定在 08:30 去拿，
留半小时余量。cron 写的是 `30 0 * * *`，那是 UTC 时间，换算过来就是北京时间 8:30。

想换时间就改 `.github/workflows/daily.yml` 里的 cron，记得**减 8 小时**：
想要北京时间 20:00 → 写 `0 12 * * *`。

> GitHub 的定时任务在整点前后负载高的时候会漂几分钟到几十分钟，属于正常现象，不是坏了。

**如果 08:30 那会儿日报还没生成**，脚本会自动降级去拉「过去 24 小时的精选条目」，
自己按五个类别分好组，照样出一份完整的日报，不会开天窗。

---

## 想改内容

绝大部分东西都在 **`config.py`** 一个文件里，改完不用碰其它代码：

| 想改什么 | 改哪个 |
|---|---|
| 报头写「AI 日报」还是别的 | `BRAND_MAIN` / `BRAND_ACCENT` |
| 一期留几条 | `MAX_ITEMS`（写 0 = 全要） |
| 要不要底部快讯 | `MAX_FLASHES` |
| 点评写给谁看 | `AUDIENCE` |
| 点评的语气和长度 | `COMMENT_STYLE` |
| 结尾那段总结 | `CLOSING_STYLE` |
| 底部推广区块 | `ENABLE_PROMO` 和下面几项 |

在 GitHub 网页上改：点开 `config.py` → 右上角铅笔 → 改 → Commit。

---

## 点评功能（唯一要花钱的地方，可选）

日报里每条下面那段「点评」和结尾的总结，AI HOT 的 API 给不了——它只提供
标题、摘要、来源、链接这些客观信息，观点得让大模型现写。

**不配也能跑**，只是没有点评，其余一切正常。

### 花多少钱

每天一次请求，5 条大约 1500 token 进、600 token 出。用 DeepSeek 这类模型，
**一个月不到一块钱**。

### 怎么配

1. 去 DeepSeek 开放平台（或任何 OpenAI 兼容的服务）注册，充最低额度，拿一个 API Key
2. GitHub 仓库 → Settings → Secrets and variables → Actions → New repository secret
3. 名字填 `LLM_API_KEY`，值粘贴你的 key，保存

只加这一个就够了，其它两个有默认值。想换别家再加：

| Secret 名 | 不填时的默认值 | 换成别家时填什么 |
|---|---|---|
| `LLM_API_KEY` | 无（必填） | 你的 key |
| `LLM_BASE_URL` | `https://api.deepseek.com/v1` | 对方的接口地址 |
| `LLM_MODEL` | `deepseek-chat` | 对方的模型名 |

只要是 OpenAI 兼容接口就能用：智谱、月之暗面、硅基流动、OpenAI 都行。

### 本地测

```bash
export LLM_API_KEY=你的key
python build.py
python build.py --no-comment   # 临时跳过点评，省钱
```

---

## 排版和样式

配色、字号、间距在 `render.py` 开头的 `CSS` 那段，`:root` 里几个变量是主色调。
版块前的 emoji 在 `SECTION_ICONS`。

改完 `python build.py --mock` 跑一下就能看效果，用的是假数据，不联网也不花钱。

图的宽度在 `render.py` 的 `.page { width: 760px }` 和 `build.py` 的 `viewport` 里，
两个地方要一起改。截图是 2 倍图，最终 1520px 宽，手机上不糊。

---

## 文件说明

```
config.py       个性化配置，想改内容基本都在这
fetch_data.py   拉 API + 归一化数据（日报优先，降级到 24h 精选）
enrich.py       调大模型写点评和结尾总结（没 key 就自动跳过）
render.py       数据 -> HTML，所有排版都在这
build.py        主入口：拉 -> 精简 -> 点评 -> 渲染 -> 截图 -> 更新首页
site/           产物，GitHub Pages 直接托管这个目录
  index.html      归档首页
  latest.html     最新一期（固定链接）
  latest.png      最新一期长图（固定链接）
  archive/        历史存档，一天一个 html
  img/            历史长图
```

---

## 几个注意点

**署名。** AI HOT 要求公开发布的产品在页脚之类能找到的地方标一次「数据来源：AI HOT」并链回去。
页脚里已经写好了，别删。自己私下看的话无所谓。

**摘要是 AI 生成的。** 要引用具体数字、政策条款或者原话，点进原文链接核对一遍再发，别直接抄摘要。

**别加高频轮询。** 日报一天只更新一次，items 接口服务端也有 60 秒缓存，一天跑一次完全够，
调密了只会拿到同一份缓存。
