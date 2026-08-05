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

## 想改样式

排版全在 `render.py` 里：

- 颜色、字号、间距 → 文件开头的 `CSS` 那段，`:root` 里几个变量是主色调
- 版块前面的 emoji → `SECTION_ICONS`
- 报头、导语、条目、页脚的结构 → `render_html()` 函数，就是拼字符串，很直白

改完 `python build.py --mock` 跑一下就能看效果，不用等到第二天。

图的宽度在 `render.py` 的 `.page { width: 760px }` 和 `build.py` 的 `viewport` 里，
两个地方要一起改。截图用的是 2 倍图，所以最终出来是 1520px 宽，手机上看不糊。

---

## 文件说明

```
fetch_data.py   拉 API + 归一化数据（日报优先，降级到 24h 精选）
render.py       数据 -> HTML，所有排版都在这
build.py        主入口：拉 -> 渲染 -> 截图 -> 更新归档首页
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
