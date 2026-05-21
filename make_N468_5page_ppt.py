from __future__ import annotations

from pathlib import Path
import sys

try:
    from pptx import Presentation
    from pptx.enum.shapes import MSO_AUTO_SHAPE_TYPE
    from pptx.enum.text import PP_ALIGN
    from pptx.util import Inches, Pt
except ImportError:
    print("未检测到 python-pptx。请先安装：pip install python-pptx")
    sys.exit(1)


def add_title(slide, text: str) -> None:
    box = slide.shapes.add_textbox(Inches(0.5), Inches(0.2), Inches(12.3), Inches(0.5))
    tf = box.text_frame
    tf.clear()
    p = tf.paragraphs[0]
    p.text = text
    p.alignment = PP_ALIGN.LEFT
    run = p.runs[0]
    run.font.size = Pt(28)
    run.font.bold = True


def add_text(slide, text: str, left: float, top: float, width: float, height: float, size: int = 16, bold: bool = False) -> None:
    box = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    tf = box.text_frame
    tf.word_wrap = True
    tf.clear()
    for i, line in enumerate(text.split("\n")):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = line
        p.alignment = PP_ALIGN.LEFT
        if p.runs:
            run = p.runs[0]
            run.font.size = Pt(size)
            run.font.bold = bold


def add_image_keep_ratio(slide, image_path: Path, left: float, top: float, width: float, height: float) -> bool:
    if not image_path.exists():
        slide.shapes.add_shape(
            MSO_AUTO_SHAPE_TYPE.RECTANGLE,
            Inches(left),
            Inches(top),
            Inches(width),
            Inches(height),
        )
        add_text(slide, f"缺少图片:\n{image_path.as_posix()}", left + 0.1, top + 0.1, width - 0.2, height - 0.2, size=14)
        return False

    pic = slide.shapes.add_picture(str(image_path), Inches(left), Inches(top), width=Inches(width))
    max_h = Inches(height)
    if pic.height > max_h:
        scale = max_h / pic.height
        pic.width = int(pic.width * scale)
        pic.height = int(pic.height * scale)
    pic.left = Inches(left) + int((Inches(width) - pic.width) / 2)
    pic.top = Inches(top) + int((Inches(height) - pic.height) / 2)
    return True


def main() -> int:
    base_dir = Path(__file__).resolve().parent
    figures = base_dir / "figures"
    output_path = base_dir / "outputs" / "N468_5page_results_summary.pptx"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    # Page 1
    s1 = prs.slides.add_slide(prs.slide_layouts[6])
    add_title(s1, "研究对象与测点定义")
    add_text(
        s1,
        "采用统一几何参数、统一测点定义和统一扫频范围，对 N=4/6/8 单环圆柱阵列进行横向比较。",
        0.6,
        6.6,
        12.0,
        0.6,
        size=16,
    )
    box_w, box_h, y0 = 3.9, 3.0, 1.4
    for i, label in enumerate(["N=4 几何示意", "N=6 几何示意", "N=8 几何示意"]):
        x = 0.6 + i * 4.25
        s1.shapes.add_shape(MSO_AUTO_SHAPE_TYPE.RECTANGLE, Inches(x), Inches(y0), Inches(box_w), Inches(box_h))
        add_text(s1, label, x + 0.2, y0 + 1.2, box_w - 0.4, 0.5, size=16, bold=True)
    add_text(s1, "测点: P0–P4（中心五点），front/rear（前后场）", 0.8, 4.7, 6.0, 0.5, size=15)
    add_text(s1, "入射波方向: front → 阵列中心 → rear", 0.8, 5.2, 6.5, 0.5, size=15)

    # Page 2
    s2 = prs.slides.add_slide(prs.slide_layouts[6])
    add_title(s2, "数据流程与指标定义")
    flow = "run_ring_array.py → full scan CSV → analyze/diagnostic scripts → compare_N4_N6_N8.py → N468 图表"
    add_text(s2, flow, 0.7, 1.2, 12.0, 0.8, size=16, bold=True)
    defs = (
        "指标定义:\n"
        "• center_mean_abs：P0–P4 平均响应\n"
        "• center_max_abs：P0–P4 局部最大响应\n"
        "• center_max_to_mean_ratio：中心局部化指标\n"
        "• rear_abs：背浪侧测点响应\n"
        "• S_rear_front：transmission-like indicator，不是严格透射系数"
    )
    add_text(s2, defs, 0.9, 2.2, 11.8, 3.7, size=16)

    # Page 3
    s3 = prs.slides.add_slide(prs.slide_layouts[6])
    add_title(s3, "N=4/6/8 中心响应总对比")
    add_image_keep_ratio(s3, figures / "N468_center_mean_comparison.png", 0.6, 1.0, 6.0, 2.6)
    add_image_keep_ratio(s3, figures / "N468_center_max_comparison.png", 6.8, 1.0, 6.0, 2.6)
    table_text = (
        "N=4: center_mean 1.139 @ 0.96 s; center_max 1.181 @ 0.90 s*\n"
        "N=6: center_mean 1.238 @ 0.97 s; center_max 1.285 @ 0.90 s*\n"
        "N=8: center_mean 1.355 @ 1.00 s; center_max 1.419 @ 0.94 s\n"
        "注：* 表示 T=0.90 s 边界峰。"
    )
    add_text(s3, table_text, 0.8, 3.9, 12.0, 1.7, size=15)
    add_text(s3, "当前 0.90–2.00 s 统一后处理口径下，中心平均响应表现为 N=8 > N=6 > N=4。", 0.8, 6.1, 12.0, 0.5, size=16, bold=True)

    # Page 4
    s4 = prs.slides.add_slide(prs.slide_layouts[6])
    add_title(s4, "中心局部化与 P0–P4 空间分化")
    add_image_keep_ratio(s4, figures / "N468_center_max_to_mean_ratio_comparison.png", 0.5, 1.0, 4.2, 2.5)
    add_image_keep_ratio(s4, figures / "N468_center_probe_peak_period_comparison.png", 4.9, 1.0, 4.2, 2.5)
    add_image_keep_ratio(s4, figures / "N468_center_probe_peak_comparison.png", 9.3, 1.0, 3.5, 2.5)
    add_text(s4, "N=8 在短周期端表现出更高的局部化指标；P1 峰值最早且通常最强，P2 峰值周期最晚，P3/P4 基本对称。", 0.8, 4.2, 12.0, 1.2, size=16)

    # Page 5
    s5 = prs.slides.add_slide(prs.slide_layouts[6])
    add_title(s5, "前后场指标、边界峰风险与下一步")
    add_image_keep_ratio(s5, figures / "N468_front_rear_S_comparison.png", 0.6, 1.2, 7.0, 4.8)
    right_text = (
        "S_rear_front 仅为 transmission-like indicator，不是 Kt。\n\n"
        "多个关键峰值位于 T=0.90 s 边界，短周期端物理解释需保守。\n\n"
        "下一步：若面向投稿，补充 T=0.85–1.05 s, ΔT=0.005 s 加密扫描。"
    )
    add_text(s5, right_text, 7.9, 1.4, 4.9, 4.8, size=16)

    prs.save(output_path)
    print(str(output_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
