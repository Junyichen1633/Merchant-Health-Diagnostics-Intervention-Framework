from __future__ import annotations

from pathlib import Path
from textwrap import wrap

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PDF = ROOT / "docs" / "merchant_health_project_overview_bilingual.pdf"
PREVIEW_DIR = ROOT / "docs" / "pdf_preview"

PAGE_W, PAGE_H = 1654, 2339  # A4 at roughly 200 DPI.
MARGIN_X = 120
MARGIN_TOP = 110
LINE_GAP = 14

FONT_REGULAR = "/System/Library/Fonts/PingFang.ttc"
FONT_BOLD = "/System/Library/Fonts/STHeiti Medium.ttc"


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(FONT_BOLD if bold else FONT_REGULAR, size=size)


TITLE = font(56, bold=True)
SUBTITLE = font(32)
H1 = font(36, bold=True)
H2 = font(28, bold=True)
BODY = font(25)
SMALL = font(22)
FOOT = font(18)


def draw_wrapped(
    draw: ImageDraw.ImageDraw,
    text: str,
    xy: tuple[int, int],
    text_font: ImageFont.FreeTypeFont,
    fill: tuple[int, int, int],
    max_chars: int,
    line_gap: int = LINE_GAP,
) -> int:
    x, y = xy
    lines = []
    for paragraph in text.split("\n"):
        if not paragraph.strip():
            lines.append("")
            continue
        lines.extend(wrap(paragraph, width=max_chars, break_long_words=False))

    for line in lines:
        if line:
            draw.text((x, y), line, font=text_font, fill=fill)
        bbox = draw.textbbox((x, y), line or " ", font=text_font)
        y += bbox[3] - bbox[1] + line_gap
    return y


def bullet(
    draw: ImageDraw.ImageDraw,
    text: str,
    y: int,
    fill: tuple[int, int, int] = (31, 41, 55),
    max_chars: int = 62,
    text_font: ImageFont.FreeTypeFont = BODY,
) -> int:
    draw.ellipse((MARGIN_X, y + 12, MARGIN_X + 12, y + 24), fill=(38, 101, 190))
    return draw_wrapped(draw, text, (MARGIN_X + 28, y), text_font, fill, max_chars) + 6


def section_title(draw: ImageDraw.ImageDraw, title: str, y: int) -> int:
    draw.rounded_rectangle(
        (MARGIN_X, y, PAGE_W - MARGIN_X, y + 58),
        radius=14,
        fill=(232, 240, 255),
    )
    draw.text((MARGIN_X + 24, y + 12), title, font=H1, fill=(25, 73, 145))
    return y + 86


def page_canvas(page_no: int, total: int) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGB", (PAGE_W, PAGE_H), "white")
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, 0, PAGE_W, 34), fill=(25, 73, 145))
    draw.text(
        (MARGIN_X, PAGE_H - 64),
        f"Merchant Health Diagnostics | Interview Overview | {page_no}/{total}",
        font=FOOT,
        fill=(102, 112, 133),
    )
    return img, draw


def add_cover(total: int) -> Image.Image:
    img, draw = page_canvas(1, total)
    y = 220
    draw.text((MARGIN_X, y), "Merchant Health Diagnostics", font=TITLE, fill=(18, 32, 64))
    y += 74
    draw.text((MARGIN_X, y), "Shopify Product Data Scientist Portfolio Project", font=SUBTITLE, fill=(38, 101, 190))
    y += 110
    draw.rounded_rectangle((MARGIN_X, y, PAGE_W - MARGIN_X, y + 420), radius=22, fill=(246, 248, 252), outline=(210, 220, 235), width=2)
    y += 42
    y = draw_wrapped(draw, "EN: I built a merchant health system that identifies at-risk sellers, decomposes health drops into product-relevant drivers, and maps each merchant to a targeted intervention.", (MARGIN_X + 42, y), BODY, (31, 41, 55), 72)
    y += 24
    y = draw_wrapped(draw, "中文：这个项目模拟 Shopify Product Data Scientist 的真实工作：定义商家健康度，识别高风险商家，解释健康度下降的原因，并给出可落地的产品干预方案。", (MARGIN_X + 42, y), BODY, (31, 41, 55), 50)
    y += 90
    draw.text((MARGIN_X, y), "Core numbers / 核心结果", font=H1, fill=(18, 32, 64))
    y += 72
    for item in [
        "16,441 merchant-month rows; 3,095 merchants; about $13.6M GMV.",
        "Latest segments: 705 Champions, 519 At-Risk, 758 Logistics Issue, 1,113 Stable Core.",
        "One additional late delivery day is associated with -0.091 review-score points and -1.71 health-score points.",
        "Repeat purchase is sparse in Olist, so reviews and fulfillment are treated as leading indicators.",
    ]:
        y = bullet(draw, item, y)
    return img


def add_metric_page(page_no: int, total: int) -> Image.Image:
    img, draw = page_canvas(page_no, total)
    y = section_title(draw, "1. Metric Design / 指标设计", MARGIN_TOP)
    for item in [
        "Grain: seller_id + order_month. The order-item table is first collapsed to order-seller grain to avoid duplicating review and customer signals.",
        "North star: repeat purchase / retention. In Olist this signal is sparse, so it remains the strategic metric while reviews and delivery are leading indicators.",
        "Health score = 30% fulfillment + 30% satisfaction + 20% retention + 20% growth.",
        "Scores are standardized with z-scores, direction-aligned, then converted to 0-100 percentile ranks for dashboard readability.",
    ]:
        y = bullet(draw, item, y)
    y += 44
    y = section_title(draw, "中文讲法", y)
    for item in [
        "粒度是 merchant-month，也就是每个商家每个月一行；这样可以观察健康度随时间变化，而不是只做静态排名。",
        "Repeat purchase 是北极星指标，但 Olist 数据里复购非常稀疏，所以我没有硬凹结论，而是把 review 和 fulfillment 当作更可观察的先导指标。",
        "健康度不是黑箱模型，而是一个可解释的产品指标体系，方便 PM 判断问题来自物流、满意度、留存还是增长。",
    ]:
        y = bullet(draw, item, y, max_chars=45)
    return img


def add_pipeline_page(page_no: int, total: int) -> Image.Image:
    img, draw = page_canvas(page_no, total)
    y = section_title(draw, "2. Data Pipeline / 数据流程", MARGIN_TOP)
    steps = [
        ("Load", "orders, order_items, reviews, customers, sellers, products, category translation"),
        ("Model", "build order-seller table, parse timestamps, compute delay, reviews, repeat orders"),
        ("Aggregate", "merchant-month metrics: GMV, order count, review score, on-time rate, repeat rate"),
        ("Score", "fulfillment, satisfaction, retention, growth, overall health score"),
        ("Diagnose", "month-over-month component deltas and dominant issue"),
        ("Act", "segment merchants and recommend intervention playbooks"),
    ]
    for name, desc in steps:
        draw.rounded_rectangle((MARGIN_X, y, PAGE_W - MARGIN_X, y + 92), radius=14, fill=(248, 250, 252), outline=(220, 226, 235))
        draw.text((MARGIN_X + 26, y + 24), name, font=H2, fill=(25, 73, 145))
        draw_wrapped(draw, desc, (MARGIN_X + 210, y + 24), BODY, (31, 41, 55), 62)
        y += 112
    y += 30
    y = draw_wrapped(draw, "Interview angle: this is not just an EDA notebook. It is a reproducible product analytics system with metric definitions, model outputs, dashboard-ready data, and intervention logic.", (MARGIN_X, y), BODY, (31, 41, 55), 74)
    return img


def add_findings_page(page_no: int, total: int) -> Image.Image:
    img, draw = page_canvas(page_no, total)
    y = section_title(draw, "3. Findings / 关键发现", MARGIN_TOP)
    for item in [
        "Delivery reliability is a meaningful driver: one extra late day is associated with a lower review score, even after controlling for merchant size, category, and month.",
        "Average review score, GMV momentum, good-review rate, and on-time rate are the strongest health-score drivers in the feature-importance model.",
        "At-risk merchants are not one uniform group. Some have logistics problems, some have satisfaction problems, and some have weak growth momentum.",
        "Repeat purchase is not ignored, but it is interpreted carefully because only 4.31% of merchant-months show any repeat orders.",
    ]:
        y = bullet(draw, item, y)
    y += 36
    y = section_title(draw, "中文讲法", y)
    for item in [
        "我最重要的发现不是“哪个商家分数低”，而是能解释为什么低：物流、满意度、留存、增长四个维度可以拆开看。",
        "回归不是严格因果，但可以支持产品假设：配送延迟和评分下降有显著关联，因此 Shopify 可以优先做物流诊断工具。",
        "这个项目的亮点是诚实处理数据限制：Olist 复购低，我不会说能精准预测 churn，而是说建立了可执行的 merchant health monitoring framework。",
    ]:
        y = bullet(draw, item, y, max_chars=45)
    return img


def add_segments_page(page_no: int, total: int) -> Image.Image:
    img, draw = page_canvas(page_no, total)
    y = section_title(draw, "4. Segmentation + Intervention / 分群与干预", MARGIN_TOP)
    rows = [
        ("Champions", "705", "Nurture with growth experiments; use as benchmark cohort."),
        ("At-Risk", "519", "Prioritize diagnosis and intervention based on weakest component."),
        ("Logistics Issue", "758", "Shipping diagnostics, carrier SLA monitoring, fulfillment guidance."),
        ("Stable Core", "1,113", "Monitor and offer targeted growth support when momentum weakens."),
    ]
    col_x = [MARGIN_X, MARGIN_X + 330, MARGIN_X + 500]
    draw.rounded_rectangle((MARGIN_X, y, PAGE_W - MARGIN_X, y + 64), radius=10, fill=(25, 73, 145))
    draw.text((col_x[0] + 20, y + 16), "Segment", font=H2, fill="white")
    draw.text((col_x[1], y + 16), "Count", font=H2, fill="white")
    draw.text((col_x[2], y + 16), "Action", font=H2, fill="white")
    y += 72
    for seg, count, action in rows:
        draw.rounded_rectangle((MARGIN_X, y, PAGE_W - MARGIN_X, y + 112), radius=10, fill=(248, 250, 252), outline=(220, 226, 235))
        draw.text((col_x[0] + 20, y + 30), seg, font=BODY, fill=(31, 41, 55))
        draw.text((col_x[1], y + 30), count, font=BODY, fill=(31, 41, 55))
        draw_wrapped(draw, action, (col_x[2], y + 22), SMALL, (31, 41, 55), 56)
        y += 126
    y += 36
    y = draw_wrapped(draw, "Decision framework: flag low-health merchants, identify the dominant issue, estimate likely impact, recommend the product playbook, then track future movement in review score, repeat rate, and GMV momentum.", (MARGIN_X, y), BODY, (31, 41, 55), 72)
    return img


def add_interview_page(page_no: int, total: int) -> Image.Image:
    img, draw = page_canvas(page_no, total)
    y = section_title(draw, "5. Interview Talk Track / 面试表达", MARGIN_TOP)
    english = (
        "I built a merchant health diagnostics system for marketplace sellers. "
        "The key product decision was defining health at a merchant-month level, "
        "then decomposing changes into fulfillment, satisfaction, retention, and growth. "
        "The analysis showed that delivery delays are strongly associated with lower reviews and lower health scores. "
        "Because repeat purchase is sparse in Olist, I treated retention as the north star but used review and fulfillment as leading indicators. "
        "The output is a dashboard-ready intervention framework that helps a PM decide which merchants need shipping, quality, retention, or growth tooling."
    )
    y = draw_wrapped(draw, "EN: " + english, (MARGIN_X, y), BODY, (31, 41, 55), 76)
    y += 42
    chinese = (
        "中文：我做的不是单纯 EDA，而是一个 merchant health system。"
        "我先定义商家健康度，再把健康度下降拆成物流、满意度、留存和增长四个 driver。"
        "结果显示配送延迟和评论下降、健康度下降有明显关联。"
        "同时我也发现 Olist 的复购信号很稀疏，所以没有过度声称能预测 churn，而是把复购作为北极星，把 review 和 fulfillment 作为先导指标。"
        "最后我把分析落到 dashboard 和 intervention framework，让 PM 能知道哪些商家有风险、为什么有风险、应该推荐什么产品工具。"
    )
    y = draw_wrapped(draw, chinese, (MARGIN_X, y), BODY, (31, 41, 55), 47)
    y += 46
    y = section_title(draw, "Details to Know / 必须记住的细节", y)
    for item in [
        "Merchant-month grain; Olist sellers are treated as Shopify merchants.",
        "Health score weights: 30% fulfillment, 30% satisfaction, 20% retention, 20% growth.",
        "Regression is observational, not causal proof; phrase results as 'associated with'.",
        "Dashboard answers: who is at risk, why, and what action to take.",
    ]:
        y = bullet(draw, item, y)
    return img


def add_limitations_page(page_no: int, total: int) -> Image.Image:
    img, draw = page_canvas(page_no, total)
    y = section_title(draw, "6. Limitations + Next Steps / 局限与下一步", MARGIN_TOP)
    for item in [
        "Olist is not Shopify data. Seller behavior is a useful proxy, but merchant lifecycle and subscription churn are not directly observed.",
        "Repeat purchase is sparse, so retention analysis is directionally useful but should not be overclaimed.",
        "Regression controls reduce confounding but do not prove causality. A stronger next step is a pseudo-experiment or merchant-level A/B test.",
        "Dashboard next step: build Tableau/Power BI views for health trend, metric decomposition, segment mix, and recommended action queue.",
    ]:
        y = bullet(draw, item, y)
    y += 42
    y = section_title(draw, "What to Say If Challenged / 被追问时怎么说", y)
    for item in [
        "Why percentile score? It is easier for PMs to rank and monitor merchants than raw z-scores.",
        "Why these weights? They reflect product judgment: fulfillment and satisfaction are direct customer-experience levers; retention and growth represent outcome signals.",
        "How would this work at Shopify? Replace Olist proxies with Shopify merchant data: GMV, buyer repeat behavior, support tickets, fulfillment data, app adoption, and merchant subscription status.",
    ]:
        y = bullet(draw, item, y)
    return img


def main() -> None:
    OUTPUT_PDF.parent.mkdir(parents=True, exist_ok=True)
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)

    total = 7
    pages = [
        add_cover(total),
        add_metric_page(2, total),
        add_pipeline_page(3, total),
        add_findings_page(4, total),
        add_segments_page(5, total),
        add_interview_page(6, total),
        add_limitations_page(7, total),
    ]

    preview_paths = []
    for i, page in enumerate(pages, start=1):
        path = PREVIEW_DIR / f"page_{i}.png"
        page.save(path)
        preview_paths.append(path)

    pages[0].save(
        OUTPUT_PDF,
        save_all=True,
        append_images=pages[1:],
        resolution=200.0,
    )

    print(f"PDF written to: {OUTPUT_PDF}")
    print("Preview pages:")
    for path in preview_paths:
        print(path)


if __name__ == "__main__":
    main()

