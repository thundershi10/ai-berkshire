# -*- coding: utf-8 -*-
"""生成 WPP 贝叶斯分析微信长图（1080px 宽）。"""
import os
import re
from functools import lru_cache

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "WPP-微信长图-20261108.png")
FAN = os.path.join(HERE, "wpp_bayes_fan.png")

W = 1080
M = 64
CW = W - 2 * M

BG = (245, 242, 235)
CREAM = (251, 249, 244)
INK = (19, 25, 35)
DARK = (17, 26, 38)
MUTED = (108, 116, 128)
LINE = (220, 213, 199)
RED = (176, 24, 43)
RED_L = (226, 178, 182)
STEEL = (52, 88, 120)
WHITE = (255, 255, 255)

FONT_SERIF_B = "/usr/share/fonts/opentype/noto-cjk-otf/NotoSerifCJKsc-Bold.otf"
FONT_SANS_R = "/usr/share/fonts/opentype/noto-cjk-otf/NotoSansCJKsc-Regular.otf"
FONT_SANS_B = "/usr/share/fonts/opentype/noto-cjk-otf/NotoSansCJKsc-Bold.otf"
FONT_NUM = "/usr/share/fonts/opentype/smiley-sans/SmileySans-Oblique.otf"


@lru_cache(maxsize=None)
def font(path, size):
    return ImageFont.truetype(path, size)


def tok(s):
    return re.findall(r"[A-Za-z0-9$%.,\-–—+/:'\"()]+|.", s)


def para(d, x, y, text, f, fill, maxw, lh=None):
    lh = lh or int(f.size * 1.62)
    line = ""
    for t in tok(text):
        cand = line + t
        if d.textlength(cand, font=f) > maxw and line:
            d.text((x, y), line, font=f, fill=fill)
            y += lh
            line = t
        else:
            line = cand
    if line:
        d.text((x, y), line, font=f, fill=fill)
        y += lh
    return y


def para_h(d, text, f, maxw, lh=None):
    lh = lh or int(f.size * 1.62)
    n, line = 1, ""
    for t in tok(text):
        cand = line + t
        if d.textlength(cand, font=f) > maxw and line:
            n += 1
            line = t
        else:
            line = cand
    return n * lh


def section(d, y, num, zh, en):
    d.text((M, y), num, font=font(FONT_NUM, 44), fill=RED)
    d.text((M + 62, y + 6), zh, font=font(FONT_SERIF_B, 38), fill=INK)
    d.text((M + 62, y + 58), en, font=font(FONT_SANS_R, 18), fill=MUTED)
    d.line([(M, y + 96), (M + 56, y + 96)], fill=RED, width=4)
    return y + 130


def card(d, box, r=18, fill=CREAM, outline=LINE, width=2):
    d.rounded_rectangle(box, radius=r, fill=fill, outline=outline, width=width)


img = Image.new("RGB", (W, 8600), BG)
d = ImageDraw.Draw(img)

# ---------------- HERO ----------------
HERO_H = 660
d.rectangle([0, 0, W, HERO_H], fill=DARK)
d.rectangle([0, HERO_H, W, HERO_H + 6], fill=RED)

d.text((M, 64), "INVESTMENT RESEARCH  /  BAYESIAN POSTERIOR", font=font(FONT_SANS_B, 18), fill=(150, 160, 175))
d.text((M, 104), "WPP 的 37 个交易日", font=font(FONT_SERIF_B, 68), fill=WHITE)
d.text((M, 194), "截至 2026-12-31 的价格分布", font=font(FONT_SANS_R, 30), fill=(196, 202, 212))
d.text((M, 238), "NYSE: WPP   ·   LSE: WPP.L   ·   1 ADR = 5 普通股   ·   GBP/USD 1.3385",
       font=font(FONT_SANS_R, 18), fill=(132, 143, 158))

d.text((M - 6, 300), "$28.51", font=font(FONT_NUM, 152), fill=WHITE)
badge = (M + 470, 330, M + 640, 390)
d.rounded_rectangle(badge, radius=30, fill=RED)
d.text((M + 492, 344), "+4.6%", font=font(FONT_SANS_B, 30), fill=WHITE)
d.text((M, 470), "后验中位数", font=font(FONT_SANS_R, 22), fill=(150, 160, 175))
d.text((M + 150, 466), "现价 $27.26（约 407p）", font=font(FONT_SANS_B, 22), fill=(206, 212, 221))
d.text((M, 510), "50% 区间  $25.41 – $31.48        80% 区间  $22.61 – $34.34",
       font=font(FONT_SANS_R, 22), fill=(206, 212, 221))
d.text((M, 556), "P(期末高于现价) = 61.0%", font=font(FONT_SANS_B, 24), fill=(255, 214, 218))

y = HERO_H + 76

# ---------------- 01 结论 ----------------
y = section(d, y, "01", "一句话结论", "THE ONE-LINER")
f_lead = font(FONT_SERIF_B, 34)
lead = "方向偏多，但优势很薄。市场已经为“转型继续改善”付了钱：上行需要新催化，下行只需要一个坏消息。"
y = para(d, M, y, lead, f_lead, INK, CW, lh=56)
y += 30

kpis = [
    ("61.0%", "期末高于现价", RED),
    ("47.5%", "突破 52 周高点 $28.77", INK),
    ("22.2%", "跌破 $25（约 374p）", STEEL),
    ("+4.7%", "37 个交易日期望收益", RED),
]
gap = 20
cw = (CW - gap) // 2
for i, (v, lab, col) in enumerate(kpis):
    cx = M + (i % 2) * (cw + gap)
    cy = y + (i // 2) * 148
    card(d, (cx, cy, cx + cw, cy + 128))
    d.text((cx + 26, cy + 20), v, font=font(FONT_NUM, 54), fill=col)
    d.text((cx + 26, cy + 84), lab, font=font(FONT_SANS_R, 20), fill=MUTED)
y += 2 * 148 + 34

# ---------------- 02 区间 ----------------
y = section(d, y, "02", "后验区间：宽得诚实", "CREDIBLE INTERVALS")
y += 8

x0, x1 = 140, 1016
vmin, vmax = 18.0, 40.0


def px(v):
    return x0 + (v - vmin) / (vmax - vmin) * (x1 - x0)


rows = [
    ("95% 可信区间", 19.73, 38.05, "$19.73 – $38.05", (206, 198, 182), 14),
    ("80% 可信区间", 22.61, 34.34, "$22.61 – $34.34", RED_L, 18),
    ("50% 可信区间", 25.41, 31.48, "$25.41 – $31.48", RED, 24),
]
for i, (lab, lo, hi, txt, col, h) in enumerate(rows):
    ry = y + i * 92
    d.text((M, ry), lab, font=font(FONT_SANS_B, 22), fill=INK)
    d.text((x1, ry - 2), txt, font=font(FONT_SANS_R, 21), fill=MUTED, anchor="ra")
    by = ry + 44
    d.rounded_rectangle((x0, by, x1, by + 8), radius=4, fill=(226, 220, 207))
    d.rounded_rectangle((px(lo), by - (h - 8) // 2, px(hi), by + 8 + (h - 8) // 2),
                        radius=h // 2, fill=col)

axis_y = y + 3 * 92 + 70
for v in (20, 25, 30, 35, 40):
    d.line([(px(v), axis_y - 8), (px(v), axis_y)], fill=(186, 178, 162), width=2)
    d.text((px(v), axis_y + 6), f"${v}", font=font(FONT_SANS_R, 18), fill=MUTED, anchor="ma")

# 现价 / 中位数 标记
for val, col, lab, above in [(27.26, STEEL, "现价 27.26", False), (28.51, RED, "中位数 28.51", True)]:
    xx = px(val)
    d.line([(xx, y + 20), (xx, axis_y - 10)], fill=col, width=2)
    d.ellipse((xx - 6, axis_y - 16, xx + 6, axis_y - 4), fill=col)
    if above:
        d.text((xx, y - 30), lab, font=font(FONT_SANS_B, 19), fill=col, anchor="ma")
    else:
        d.text((xx, axis_y + 34), lab, font=font(FONT_SANS_B, 19), fill=col, anchor="ma")

y = axis_y + 84
y = para(d, M, y, "95% 区间 295–569p，几乎覆盖了“腰斩”到“+40%”的全部可能。任何点预测都不应被当成目标价。",
         font(FONT_SANS_R, 21), MUTED, CW, lh=34)
y += 36

# ---------------- 03 三模型 ----------------
y = section(d, y, "03", "三个模型，三种叙事", "MODEL AVERAGE · 50/30/20")
y += 10

comps = [
    ("A1", "常数漂移 + Student-t（ν=5）", "稳健漂移锚，不追短期动量", 0.50, "$27.55", "+1.1%", RED),
    ("B", "局部线性趋势 DLM（Kalman）", "捕捉转型动量，趋势年化 67%", 0.30, "$30.21", "+10.8%", STEEL),
    ("C", "分析师目标价桥接", "12 个月目标 $26.05，向 12/31 收敛", 0.20, "$27.11", "-0.6%", MUTED),
]
for i, (tag, name, desc, wgt, med, chg, col) in enumerate(comps):
    ry = y + i * 124
    card(d, (M, ry, W - M, ry + 106))
    d.text((M + 24, ry + 26), tag, font=font(FONT_NUM, 40), fill=col)
    d.text((M + 96, ry + 20), name, font=font(FONT_SANS_B, 23), fill=INK)
    d.text((M + 96, ry + 56), desc, font=font(FONT_SANS_R, 19), fill=MUTED)
    d.text((W - M - 24, ry + 18), med, font=font(FONT_NUM, 42), fill=INK, anchor="ra")
    d.text((W - M - 24, ry + 62), chg, font=font(FONT_SANS_B, 21), fill=col, anchor="ra")
    # 权重条
    bw = 210
    bx = W - M - 24 - bw
    d.rounded_rectangle((bx, ry + 92, bx + bw, ry + 98), radius=3, fill=(228, 222, 209))
    d.rounded_rectangle((bx, ry + 92, bx + bw * wgt, ry + 98), radius=3, fill=col)
    d.text((bx - 12, ry + 84), f"权重 {int(wgt*100)}%", font=font(FONT_SANS_R, 16), fill=MUTED, anchor="ra")
y += 3 * 124 + 6
y = para(d, M, y, "模型内部分歧本身就是结论：这不是价值回归，而是一只叙事驱动股。混合后验中位数高于三者加权平均，是因为右尾更厚。",
         font(FONT_SANS_R, 21), MUTED, CW, lh=34)
y += 40

# ---------------- 04 扇形图 ----------------
y = section(d, y, "04", "后验预测扇形图", "POSTERIOR PREDICTIVE")
y += 6
fan = Image.open(FAN).convert("RGB")
fw = CW
fh = int(fan.height * fw / fan.width)
fan = fan.resize((fw, fh), Image.LANCZOS)
card(d, (M - 8, y - 8, W - M + 8, y + fh + 8), r=14, fill=WHITE, outline=LINE)
img.paste(fan, (M, y))
y += fh + 26
y = para(d, M, y, "2024-11 至 2026-12-31 ｜ 阴影为 50% / 80% / 95% 后验带 ｜ 红色虚线为卖方 12 个月目标 $26.05",
         font(FONT_SANS_R, 19), MUTED, CW, lh=30)
y += 44

# ---------------- 05 概率阶梯 ----------------
y = section(d, y, "05", "市场在赌什么", "PROBABILITY LADDER")
y += 10

probs = [
    ("站上 $30（约 449p）", 0.366, RED),
    ("突破 52 周高点 $28.77", 0.475, RED),
    ("跌破 $25（约 374p）", 0.222, STEEL),
    ("跌破 $22（约 329p）", 0.080, STEEL),
    ("跌破 $20（约 299p）", 0.029, STEEL),
]
bar_x0, bar_x1 = 430, 900
for i, (lab, p, col) in enumerate(probs):
    ry = y + i * 66
    d.text((M, ry + 2), lab, font=font(FONT_SANS_R, 20), fill=INK)
    by = ry + 12
    d.rounded_rectangle((bar_x0, by, bar_x1, by + 14), radius=7, fill=(229, 223, 210))
    d.rounded_rectangle((bar_x0, by, bar_x0 + (bar_x1 - bar_x0) * p, by + 14), radius=7, fill=col)
    d.text((W - M, ry - 2), f"{p*100:.1f}%", font=font(FONT_NUM, 30), fill=col, anchor="ra")
y += 5 * 66 + 22
y = para(d, M, y, "读法：当前价格已计入“转型继续改善”的基准情形。真正有赔率的不是看多到 35，而是“Q4 只是符合预期”。",
         font(FONT_SANS_R, 21), MUTED, CW, lh=34)
y += 44

# ---------------- 06 阳狮小作文 ----------------
y = section(d, y, "06", "阳狮的“小作文”", "THE PUBLICIS MOVE")

qy = y + 6
d.rounded_rectangle((M, qy, W - M, qy + 264), radius=18, fill=DARK)
d.text((M + 28, qy + 8), "“", font=font(FONT_SERIF_B, 96), fill=(120, 30, 45))
fq = font(FONT_SERIF_B, 27)
qy2 = para(d, M + 40, qy + 62, "我们会张开双臂，欢迎想继续使用 LiveRamp 的竞争对手。",
           fq, WHITE, CW - 80, lh=44)
d.text((M + 40, qy2 + 12), "—— Arthur Sadoun，阳狮集团董事长兼 CEO",
       font=font(FONT_SANS_R, 19), fill=(150, 160, 175))
d.text((M + 40, qy + 200), "但同一场采访里还有下半句：对手广告集团合计不到 LiveRamp 收入的 5%。",
       font=font(FONT_SANS_B, 22), fill=(255, 196, 202))
y = qy + 300

d.text((M, y), "翻译：你们可以继续用，但你们不是不可或缺。数据身份层现在在我手里。",
       font=font(FONT_SANS_B, 24), fill=RED)
y += 56

impacts = [
    ("数据基础设施", "WPP 媒介代理依赖 RampID 做跨平台身份匹配，这一层归了竞争对手", "中期负面"),
    ("叙事竞争", "阳狮用“Epsilon + LiveRamp + 客户自有数据”讲 AI 故事，WPP Open 需要自证", "短期负面"),
    ("客户预算", "阳狮 9 月无 pitch 拿下百事全球媒体约 $17 亿，“能力审查”替代比稿", "中性偏负"),
]
for i, (t, desc, tag) in enumerate(impacts):
    ry = y + i * 92
    d.line([(M, ry), (M, ry + 76)], fill=RED, width=3)
    d.text((M + 22, ry + 2), t, font=font(FONT_SANS_B, 23), fill=INK)
    d.text((W - M, ry + 6), tag, font=font(FONT_SANS_R, 18), fill=MUTED, anchor="ra")
    d.text((M + 22, ry + 38), desc, font=font(FONT_SANS_R, 19), fill=MUTED)
y += 3 * 92 + 14

t1 = "别读成“胜负已定”：FTC 的 5 年 FRAND 访问、数据防火墙与独立审计是硬约束；Omnicom 已加速转向 Acxiom；阳狮自己也被 UBS 下调至中性（€109→€100）。"
t2 = "真正的增量：并表后阳狮上调 FY27/28 目标——净营收增速 7–8%（原 6–7%），headline EPS 增速 8–10%（原 7–9%）。先手正在变成财务优势。"
h1 = para_h(d, t1, font(FONT_SANS_R, 20), CW - 48, lh=32)
h2 = para_h(d, t2, font(FONT_SANS_B, 20), CW - 48, lh=32)
card_h = 22 + h1 + 8 + h2 + 26
card(d, (M, y, W - M, y + card_h), fill=(238, 235, 226))
y2 = para(d, M + 24, y + 22, t1, font(FONT_SANS_R, 20), INK, CW - 48, lh=32)
para(d, M + 24, y2 + 8, t2, font(FONT_SANS_B, 20), RED, CW - 48, lh=32)
y += card_h + 40

# ---------------- 07 情景 ----------------
y = section(d, y, "07", "三种 12 月 31 日", "SCENARIOS")
y += 6

scen = [
    ("20%", "下行", "$20–25", "300–375p", "叙事破裂", (226, 222, 212), STEEL),
    ("50%", "基准", "$26–31", "390–460p", "慢修复", (250, 247, 240), INK),
    ("30%", "上行", "$32–37", "480–555p", "重估加速", (243, 228, 230), RED),
]
sg = 16
scw = (CW - 2 * sg) // 3
for i, (p, name, usd, gbp, desc, bgc, col) in enumerate(scen):
    cx = M + i * (scw + sg)
    card(d, (cx, y, cx + scw, y + 236), r=16, fill=bgc, outline=LINE)
    d.text((cx + 20, y + 18), p, font=font(FONT_NUM, 42), fill=col)
    d.text((cx + 20, y + 76), name, font=font(FONT_SANS_B, 22), fill=INK)
    d.text((cx + 20, y + 112), usd, font=font(FONT_NUM, 36), fill=col)
    d.text((cx + 20, y + 158), gbp, font=font(FONT_SANS_R, 19), fill=MUTED)
    d.text((cx + 20, y + 194), desc, font=font(FONT_SANS_R, 19), fill=MUTED)
y += 236 + 30
y = para(d, M, y, "情景概率与模型概率对齐：P(<$25)=22% 对应下行 20%，P(>$30)=37% 对应上行 30%。基准 50% 是“最可能但不激动”的路径。",
         font(FONT_SANS_R, 20), MUTED, CW, lh=32)
y += 44

# ---------------- 08 观察清单 ----------------
y = section(d, y, "08", "未来 8 周看什么", "WATCHLIST")
y += 8

watch = [
    ("Q4 更新", "2027 年 2 月底全年业绩；2027 恢复有机增长是最大二元事件"),
    ("新业务净影响", "Q3 仍是净拖累；Q4 能否转正，是转型见效的硬指标"),
    ("可口可乐北美", "北美转给 Omnicom 后的过渡执行，是否波及其他 remit"),
    ("阳狮客户反弹", "若 WPP / Omnicom 公开加速迁移，LiveRamp 中立性叙事受损"),
    ("分析师目标价", "当前均值低于现价；上修形成正反馈，下调则承压"),
]
for i, (t, desc) in enumerate(watch):
    ry = y + i * 74
    d.text((M, ry), f"0{i+1}", font=font(FONT_NUM, 26), fill=RED)
    d.text((M + 52, ry - 2), t, font=font(FONT_SANS_B, 22), fill=INK)
    d.text((M + 220, ry + 1), desc, font=font(FONT_SANS_R, 19), fill=MUTED)
    d.line([(M, ry + 52), (W - M, ry + 52)], fill=(232, 226, 214), width=1)
y += 5 * 74 + 30

# ---------------- FOOTER ----------------
fy = y
d.rectangle([0, fy, W, fy + 600], fill=DARK)
d.text((M, fy + 44), "数据与方法", font=font(FONT_SANS_B, 24), fill=WHITE)
foot = [
    "价格：WPP ADR 日收盘，2020-11-02 至 2026-11-06，共 1,511 个交易日（Nasdaq / Futunn / 雪球三源交叉）",
    "基本面：WPP 2026 Q3 交易更新（2026-10-29）、2025 年报、Publicis Groupe 公告（2026-11-02）、FTC 同意令",
    "增量：Advertising Reporter（2026-11-04）关于阳狮并表后上调 FY27/28 指引的报道",
    "模型：Student-t 常数漂移 + 局部线性趋势 DLM（Kalman/边际似然）+ 分析师目标桥，40,000 条蒙特卡洛路径",
    "校验：市值、P/E、FCF 收益率、股息率均通过 financial_rigor.py 精确验算，偏差 ≤0.03%",
]
fyy = fy + 88
for line in foot:
    fyy = para(d, M, fyy, line, font(FONT_SANS_R, 17), (150, 160, 175), CW, lh=30)
d.text((M, fyy + 16), "本图为研究分析，不构成投资建议。预测区间宽泛，请勿将中位数当作目标价。",
       font=font(FONT_SANS_B, 17), fill=(255, 196, 202))
final_h = fyy + 86

img = img.crop((0, 0, W, final_h))
img.save(OUT, optimize=True)
print("saved", OUT, img.size)
