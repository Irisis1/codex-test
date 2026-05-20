from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUTPUTS = ROOT / "outputs"
FIGURES = ROOT / "figures"

CATALOG_PATH = OUTPUTS / "N468_figure_table_catalog.csv"
MAP_PATH = OUTPUTS / "N468_data_source_map.csv"
NOTES_PATH = OUTPUTS / "N468_result_interpretation_notes.md"
PPT_PLAN_PATH = OUTPUTS / "N468_ppt_organization_plan.md"
PAPER_PLAN_PATH = OUTPUTS / "N468_paper_results_figure_plan.md"


def norm(path: str) -> str:
    return path.replace("\\", "/")


def infer_file_type(path: str) -> str:
    suffix = Path(path).suffix.lower().lstrip(".")
    return suffix if suffix else "unknown"


def file_exists(path: str) -> bool:
    return (ROOT / path).exists()


def build_catalog_rows() -> list[dict[str, str]]:
    items = [
        # Source data
        ("outputs/N4_period_scan_summary_0p90_2p00.csv", "N4", "source data", "run_ring_array.py", "-", "center_mean_abs|center_max_abs|front_abs|rear_abs|S_rear_front"),
        ("outputs/N6_period_scan_summary_0p90_2p00.csv", "N6", "source data", "run_ring_array.py", "-", "center_mean_abs|center_max_abs|front_abs|rear_abs|S_rear_front"),
        ("outputs/N8_period_scan_summary_0p90_2p00.csv", "N8", "source data", "run_ring_array.py", "-", "center_mean_abs|center_max_abs|front_abs|rear_abs|S_rear_front"),
        ("outputs/N4_period_scan_point_probes_0p90_2p00.csv", "N4", "source data", "run_ring_array.py", "-", "P0-P4 total_abs|diffracted_abs"),
        ("outputs/N6_period_scan_point_probes_0p90_2p00.csv", "N6", "source data", "run_ring_array.py", "-", "P0-P4 total_abs|diffracted_abs"),
        ("outputs/N8_period_scan_point_probes_0p90_2p00.csv", "N8", "source data", "run_ring_array.py", "-", "P0-P4 total_abs|diffracted_abs"),
        ("outputs/N4_period_scan_line_probes_0p90_2p00.csv", "N4", "source data", "run_ring_array.py", "-", "line total_abs|diffracted_abs"),
        ("outputs/N6_period_scan_line_probes_0p90_2p00.csv", "N6", "source data", "run_ring_array.py", "-", "line total_abs|diffracted_abs"),
        ("outputs/N8_period_scan_line_probes_0p90_2p00.csv", "N8", "source data", "run_ring_array.py", "-", "line total_abs|diffracted_abs"),
        # Single-model diagnostics
        ("outputs/N4_analysis_report.md", "N4", "single-model diagnostic", "analyze_scan_results.py", "outputs/N4_period_scan_summary_0p90_2p00.csv;outputs/N4_period_scan_point_probes_0p90_2p00.csv", "center_mean_abs|center_max_abs|P0-P4"),
        ("outputs/N6_analysis_report.md", "N6", "single-model diagnostic", "analyze_scan_results.py", "outputs/N6_period_scan_summary_0p90_2p00.csv;outputs/N6_period_scan_point_probes_0p90_2p00.csv", "center_mean_abs|center_max_abs|P0-P4"),
        ("outputs/N8_analysis_report.md", "N8", "single-model diagnostic", "analyze_scan_results.py", "outputs/N8_period_scan_summary_0p90_2p00.csv;outputs/N8_period_scan_point_probes_0p90_2p00.csv", "center_mean_abs|center_max_abs|P0-P4"),
        ("outputs/anomaly_check_N4.csv", "N4", "single-model diagnostic", "analyze_scan_results.py", "outputs/N4_period_scan_summary_0p90_2p00.csv", "anomaly flags"),
        ("outputs/anomaly_check_N6.csv", "N6", "single-model diagnostic", "analyze_scan_results.py", "outputs/N6_period_scan_summary_0p90_2p00.csv", "anomaly flags"),
        ("outputs/anomaly_check_N8.csv", "N8", "single-model diagnostic", "analyze_scan_results.py", "outputs/N8_period_scan_summary_0p90_2p00.csv", "anomaly flags"),
        ("figures/N4_center_summary_0p90_2p00.png", "N4", "single-model diagnostic", "plot_scan_diagnostics.py", "outputs/N4_period_scan_summary_0p90_2p00.csv", "center_mean_abs|center_max_abs|center_max_to_mean_ratio"),
        ("figures/N4_center_five_points_0p90_2p00.png", "N4", "single-model diagnostic", "plot_scan_diagnostics.py", "outputs/N4_period_scan_point_probes_0p90_2p00.csv", "P0-P4 total_abs"),
        ("figures/N4_front_rear_S_0p90_2p00.png", "N4", "single-model diagnostic", "plot_scan_diagnostics.py", "outputs/N4_period_scan_summary_0p90_2p00.csv", "front_abs|rear_abs|S_rear_front"),
        ("figures/N6_center_summary_0p90_2p00.png", "N6", "single-model diagnostic", "plot_scan_diagnostics.py", "outputs/N6_period_scan_summary_0p90_2p00.csv", "center_mean_abs|center_max_abs|center_max_to_mean_ratio"),
        ("figures/N6_center_five_points_0p90_2p00.png", "N6", "single-model diagnostic", "plot_scan_diagnostics.py", "outputs/N6_period_scan_point_probes_0p90_2p00.csv", "P0-P4 total_abs"),
        ("figures/N6_front_rear_S_0p90_2p00.png", "N6", "single-model diagnostic", "plot_scan_diagnostics.py", "outputs/N6_period_scan_summary_0p90_2p00.csv", "front_abs|rear_abs|S_rear_front"),
        ("figures/N8_center_summary_0p90_2p00.png", "N8", "single-model diagnostic", "plot_scan_diagnostics.py", "outputs/N8_period_scan_summary_0p90_2p00.csv", "center_mean_abs|center_max_abs|center_max_to_mean_ratio"),
        ("figures/N8_center_five_points_0p90_2p00.png", "N8", "single-model diagnostic", "plot_scan_diagnostics.py", "outputs/N8_period_scan_point_probes_0p90_2p00.csv", "P0-P4 total_abs"),
        ("figures/N8_front_rear_S_0p90_2p00.png", "N8", "single-model diagnostic", "plot_scan_diagnostics.py", "outputs/N8_period_scan_summary_0p90_2p00.csv", "front_abs|rear_abs|S_rear_front"),
        # Cross-array
        ("outputs/N468_key_metrics_comparison.csv", "N468", "cross-array comparison", "compare_N4_N6_N8.py", "outputs/N4_period_scan_summary_0p90_2p00.csv;outputs/N6_period_scan_summary_0p90_2p00.csv;outputs/N8_period_scan_summary_0p90_2p00.csv", "center_mean_abs|center_max_abs|center_max_to_mean_ratio|front_abs|rear_abs|S_rear_front"),
        ("outputs/N468_peak_periods_comparison.csv", "N468", "cross-array comparison", "compare_N4_N6_N8.py", "outputs/N4_period_scan_point_probes_0p90_2p00.csv;outputs/N6_period_scan_point_probes_0p90_2p00.csv;outputs/N8_period_scan_point_probes_0p90_2p00.csv", "P0-P4 peak value|peak period"),
        ("outputs/N468_center_probe_comparison.csv", "N468", "cross-array comparison", "compare_N4_N6_N8.py", "outputs/N4_period_scan_point_probes_0p90_2p00.csv;outputs/N6_period_scan_point_probes_0p90_2p00.csv;outputs/N8_period_scan_point_probes_0p90_2p00.csv", "P0-P4 total_abs"),
        ("outputs/N468_summary_table_for_paper.csv", "N468", "cross-array comparison", "compare_N4_N6_N8.py", "outputs/N468_key_metrics_comparison.csv;outputs/N468_peak_periods_comparison.csv", "paper summary metrics"),
        ("figures/N468_center_mean_comparison.png", "N468", "cross-array comparison", "compare_N4_N6_N8.py", "outputs/N468_key_metrics_comparison.csv", "center_mean_abs"),
        ("figures/N468_center_max_comparison.png", "N468", "cross-array comparison", "compare_N4_N6_N8.py", "outputs/N468_key_metrics_comparison.csv", "center_max_abs"),
        ("figures/N468_front_rear_S_comparison.png", "N468", "cross-array comparison", "compare_N4_N6_N8.py", "outputs/N468_key_metrics_comparison.csv", "front_abs|rear_abs|S_rear_front"),
        ("figures/N468_center_probe_peak_comparison.png", "N468", "cross-array comparison", "compare_N4_N6_N8.py", "outputs/N468_peak_periods_comparison.csv", "P0-P4 peak value"),
        ("figures/N468_center_max_to_mean_ratio_comparison.png", "N468", "cross-array comparison", "compare_N4_N6_N8.py", "outputs/N468_key_metrics_comparison.csv", "center_max_to_mean_ratio"),
        ("figures/N468_center_probe_peak_period_comparison.png", "N468", "cross-array comparison", "compare_N4_N6_N8.py", "outputs/N468_peak_periods_comparison.csv", "P0-P4 peak period"),
        # PPT and scripts
        ("outputs/N468_summary_comparison_slide.pptx", "N468", "ppt", "make_N468_summary_ppt.py", "outputs/N468_key_metrics_comparison.csv;figures/N468_center_mean_comparison.png", "summary visuals"),
        ("run_ring_array.py", "general", "script", "-", "-", "simulation generation"),
        ("analyze_scan_results.py", "general", "script", "-", "-", "single-model analysis"),
        ("plot_scan_diagnostics.py", "general", "script", "-", "-", "diagnostic plotting"),
        ("compare_N4_N6_N8.py", "general", "script", "-", "-", "cross-array comparison"),
        ("make_N468_summary_ppt.py", "general", "script", "-", "-", "ppt generation"),
    ]

    rows: list[dict[str, str]] = []
    for file_path, array_size, scope, source_script, source_data, main_metrics in items:
        exists = file_exists(file_path)
        caution = "boundary peak @0.90 s must be treated as boundary peak; S_rear_front transmission-like only; not uniform amplification"
        if not exists:
            caution = f"missing file; {caution}"
        rows.append(
            {
                "file_path": norm(file_path),
                "file_type": infer_file_type(file_path),
                "array_size": array_size,
                "scope": scope,
                "source_script": source_script,
                "source_data": source_data,
                "main_metrics": main_metrics,
                "period_range": "0.90-2.00 s" if "0p90_2p00" in file_path or "N468_" in file_path else "unknown",
                "mesh_level": "medium" if "period_scan" in file_path or "N468_" in file_path else "unknown",
                "purpose": "结果资产索引与解释支持",
                "recommended_use": "PPT/paper/appendix/internal check",
                "ppt_section": "单模型诊断页/总对比页/方法补充页",
                "paper_section": "Methods/Results/Appendix",
                "caution_notes": caution,
            }
        )
    return rows


def write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def build_data_source_map_rows() -> list[dict[str, str]]:
    base_source = "outputs/N4|N6|N8_period_scan_summary_0p90_2p00.csv;outputs/N4|N6|N8_period_scan_point_probes_0p90_2p00.csv"
    return [
        {"metric": "center_mean_abs", "definition": "P0-P4 total_abs 的平均值", "computed_from": "mean(P0_total_abs..P4_total_abs)", "source_csv": base_source, "source_script": "analyze_scan_results.py;compare_N4_N6_N8.py", "physical_meaning": "中心区域平均响应", "valid_interpretation": "比较不同N下中心平均响应强度", "invalid_interpretation": "不能据此断言全场均匀增强", "boundary_issue": "短周期端需关注0.90 s boundary peak", "recommended_plot": "N468_center_mean_comparison.png", "recommended_table": "N468_summary_table_for_paper.csv"},
        {"metric": "center_max_abs", "definition": "P0-P4 total_abs 的最大值", "computed_from": "max(P0_total_abs..P4_total_abs)", "source_csv": base_source, "source_script": "analyze_scan_results.py;compare_N4_N6_N8.py", "physical_meaning": "中心局部最大响应", "valid_interpretation": "识别中心局部热点强度", "invalid_interpretation": "不能单独用于柱数效应总判断", "boundary_issue": "N4/N6峰值可能位于0.90 s boundary peak", "recommended_plot": "N468_center_max_comparison.png", "recommended_table": "N468_key_metrics_comparison.csv"},
        {"metric": "center_max_to_mean_ratio", "definition": "center_max_abs / center_mean_abs", "computed_from": "center_max_abs / center_mean_abs", "source_csv": "outputs/N468_key_metrics_comparison.csv", "source_script": "compare_N4_N6_N8.py", "physical_meaning": "中心局部化程度", "valid_interpretation": "比值越高表示局部热点更突出", "invalid_interpretation": "不能解读为全域放大", "boundary_issue": "峰值若在0.90 s需标记boundary peak", "recommended_plot": "N468_center_max_to_mean_ratio_comparison.png", "recommended_table": "N468_key_metrics_comparison.csv"},
    ] + [
        {"metric": f"P{i}_total_abs", "definition": f"P{i}测点总自由面复振幅模值", "computed_from": "|incident + diffracted|", "source_csv": "outputs/N4|N6|N8_period_scan_point_probes_0p90_2p00.csv", "source_script": "run_ring_array.py;analyze_scan_results.py;compare_N4_N6_N8.py", "physical_meaning": "中心局部点响应", "valid_interpretation": "比较峰值大小与峰值周期", "invalid_interpretation": "不能直接外推为全中心均匀行为", "boundary_issue": "峰值落在0.90 s时仅能记为boundary peak", "recommended_plot": "N468_center_probe_peak_comparison.png;N468_center_probe_peak_period_comparison.png", "recommended_table": "N468_peak_periods_comparison.csv"}
        for i in range(5)
    ] + [
        {"metric": "front_abs", "definition": "front测点 total_abs", "computed_from": "|incident + diffracted| at front", "source_csv": "outputs/N4|N6|N8_period_scan_summary_0p90_2p00.csv", "source_script": "run_ring_array.py;plot_scan_diagnostics.py;compare_N4_N6_N8.py", "physical_meaning": "前场响应强度", "valid_interpretation": "用于前后场对照", "invalid_interpretation": "不能直接等同能量透射率", "boundary_issue": "短周期边界段需谨慎", "recommended_plot": "N468_front_rear_S_comparison.png", "recommended_table": "N468_key_metrics_comparison.csv"},
        {"metric": "rear_abs", "definition": "rear测点 total_abs", "computed_from": "|incident + diffracted| at rear", "source_csv": "outputs/N4|N6|N8_period_scan_summary_0p90_2p00.csv", "source_script": "run_ring_array.py;plot_scan_diagnostics.py;compare_N4_N6_N8.py", "physical_meaning": "后场响应强度", "valid_interpretation": "用于前后场对照", "invalid_interpretation": "不能直接等同严格透射系数", "boundary_issue": "短周期边界段需谨慎", "recommended_plot": "N468_front_rear_S_comparison.png", "recommended_table": "N468_key_metrics_comparison.csv"},
        {"metric": "S_rear_front", "definition": "rear_abs / front_abs", "computed_from": "rear_abs / front_abs", "source_csv": "outputs/N4|N6|N8_period_scan_summary_0p90_2p00.csv;outputs/N468_key_metrics_comparison.csv", "source_script": "plot_scan_diagnostics.py;compare_N4_N6_N8.py", "physical_meaning": "front/rear相对指标", "valid_interpretation": "只能解释为 transmission-like indicator", "invalid_interpretation": "不能写成Kt或strict transmission coefficient", "boundary_issue": "front_abs较小时比值敏感", "recommended_plot": "N4/N6/N8_front_rear_S_0p90_2p00.png;N468_front_rear_S_comparison.png", "recommended_table": "N468_key_metrics_comparison.csv"},
        {"metric": "total_abs", "definition": "incident + diffracted 的复自由面响应模值", "computed_from": "abs(eta_incident + eta_diffracted)", "source_csv": "outputs/N4|N6|N8_period_scan_point_probes_0p90_2p00.csv;outputs/N4|N6|N8_period_scan_line_probes_0p90_2p00.csv", "source_script": "run_ring_array.py", "physical_meaning": "总响应幅值", "valid_interpretation": "用于主结果指标构建", "invalid_interpretation": "不能忽略测点位置差异", "boundary_issue": "边界周期峰值需谨慎", "recommended_plot": "center_five_points and cross-array plots", "recommended_table": "N468_center_probe_comparison.csv"},
        {"metric": "diffracted_abs", "definition": "散射贡献模值", "computed_from": "abs(eta_diffracted)", "source_csv": "outputs/N4|N6|N8_period_scan_point_probes_0p90_2p00.csv;outputs/N4|N6|N8_period_scan_line_probes_0p90_2p00.csv", "source_script": "run_ring_array.py", "physical_meaning": "散射贡献参考量", "valid_interpretation": "可用于辅助手段理解散射贡献", "invalid_interpretation": "不作为主图核心指标", "boundary_issue": "与total_abs联合解读", "recommended_plot": "appendix diagnostic plots", "recommended_table": "appendix tables"},
    ]


def write_markdowns() -> None:
    notes = """# N=4/N=6/N=8 结果解读说明\n\n## 1. 项目当前状态\n当前 N=4、N=6、N=8 的 full scan、单模型诊断、横向对比及 PPT 总对比页产物均已纳入本次资产盘点范围。\n\n## 2. 数据来源链条\n1) `run_ring_array.py` 生成 full scan CSV（summary/point/line）。\n2) `analyze_scan_results.py` 与 `plot_scan_diagnostics.py` 生成单模型诊断报告与图。\n3) `compare_N4_N6_N8.py` 生成 N468 横向对比图表与汇总表。\n4) `make_N468_summary_ppt.py` 生成总对比 PPT 页面。\n\n## 3. 单模型诊断文件说明\n对 N4/N6/N8 的 `center_summary`、`center_five_points`、`front_rear_S` 三图统一说明：\n- 图展示什么：中心均值/峰值与局部化、P0-P4 细节、front/rear 与 S_rear_front。\n- 数据来自哪里：对应 `period_scan_summary` 与 `period_scan_point_probes` CSV。\n- 能支持什么结论：可比较中心响应水平、空间非均匀性、前后场相对变化。\n- 不能支持什么结论：不能把 0.90 s 边界峰写成已确认 resonance；不能将 S_rear_front 写成 Kt 或 strict transmission coefficient；不能据此得出“中心区域均匀增强”。\n\n## 4. 横向对比文件说明\n- `N468_center_mean_comparison.png`：目的=比较中心平均响应；指标=`center_mean_abs`；来源=`N468_key_metrics_comparison.csv`；观察=当前为 N=8 > N=6 > N=4；边界=短周期端解释保守。\n- `N468_center_max_comparison.png`：目的=比较中心局部最大响应；指标=`center_max_abs`；来源同上；观察=当前为 N=8 > N=6 > N=4；边界=N=4/N=6 峰值位于 0.90 s boundary peak。\n- `N468_center_max_to_mean_ratio_comparison.png`：目的=比较局部化程度；指标=`center_max_to_mean_ratio`；观察=N=8 短周期端局部热点更突出；边界=峰位边界敏感。\n- `N468_center_probe_peak_comparison.png`：目的=比较 P0-P4 峰值大小；指标=P0-P4 peak value；观察=P1 常最强。\n- `N468_center_probe_peak_period_comparison.png`：目的=比较 P0-P4 峰值周期；指标=P0-P4 peak period；观察=P1 峰值更早、P2 更晚、P3/P4 基本对称。\n- `N468_front_rear_S_comparison.png`：目的=比较前后场与相对指标；指标=front_abs/rear_abs/S_rear_front；边界=S_rear_front 仅为 transmission-like indicator。\n- `N468_summary_table_for_paper.csv`：目的=论文结果汇总表基础素材；边界=需保留 boundary peak 标注。\n\n## 5. 当前可以支持的结果判断\n- `center_mean_abs` 当前表现为 **N=8 > N=6 > N=4**。\n- `center_max_abs` 当前表现为 **N=8 > N=6 > N=4**，但 N=4/N=6 峰值位于 **0.90 s boundary peak**。\n- `center_max_to_mean_ratio` 显示 N=8 短周期端局部热点更突出，但峰值位于边界。\n- P1 峰值最早且通常最强，P2 峰值周期最晚，P3/P4 基本对称。\n- `S_rear_front` 只作为 **transmission-like indicator**。\n\n## 6. 当前不能支持的结果判断\n- 不能写“柱数越少响应越强”。\n- 不能写“0.90 s 是已确认共振峰”。\n- 不能写“S_rear_front 是 Kt”。\n- 不能写“中心区域均匀增强”。\n- 不能只用 `center_max_abs` 判断柱数效应。\n\n## 7. 后续建议\n- 当前结果可直接用于组会 PPT 总对比页。\n- 当前结果可进入论文 Results 草稿。\n- 若面向投稿，建议补做 **0.85–1.05 s、步长 0.005 s** 的短周期加密扫描，以确认 0.90 s boundary peak。\n"""

    ppt_plan = """# N468 PPT 组织建议（按页）\n\n## Page 1：模型与测点布置\n- 放置 N=4/N=6/N=8 几何图、P0-P4、front/rear、入射波方向。\n\n## Page 2：N=4 单模型诊断\n- `N4_center_summary_0p90_2p00.png`\n- `N4_center_five_points_0p90_2p00.png`\n- `N4_front_rear_S_0p90_2p00.png`\n- 强调 N=4 边界峰风险与中心空间非均匀性。\n\n## Page 3：N=6 单模型诊断\n- `N6_center_summary_0p90_2p00.png`\n- `N6_center_five_points_0p90_2p00.png`\n- `N6_front_rear_S_0p90_2p00.png`\n- 强调 N=6 中心响应特征与边界峰风险。\n\n## Page 4：N=8 单模型诊断\n- `N8_center_summary_0p90_2p00.png`\n- `N8_center_five_points_0p90_2p00.png`\n- `N8_front_rear_S_0p90_2p00.png`\n- 强调 N=8 中心增强与峰值位置。\n\n## Page 5：N=4/6/8 总对比页\n- `N468_center_mean_comparison.png`\n- `N468_center_max_comparison.png`\n- `N468_center_max_to_mean_ratio_comparison.png`\n- `N468_center_probe_peak_period_comparison.png`\n- 底部总结：统一后处理口径下，N=8 表现出更强中心响应与局部化特征；多个短周期峰值位于 0.90 s boundary peak，物理解释需保守。\n\n## Page 6：前后场与 transmission-like indicator\n- `N468_front_rear_S_comparison.png`\n- 明确 `S_rear_front` 仅为 transmission-like indicator，不是 Kt。\n\n## Page 7：总结与下一步\n- 已完成 N=4/N=6/N=8 统一横向对比。\n- 当前结果支持 N=8 中心响应与局部化更强。\n- 短周期端存在 boundary peak 不确定性。\n- 后续建议短周期加密扫描。\n"""

    paper_plan = """# 论文 Results 图表组织方案（N468）\n\n## 3.1 Numerical setup and probe definition\n- 放模型与测点图（N=4/N=6/N=8，P0-P4，front/rear，入射方向）。\n\n## 3.2 Single-array diagnostic results\n- 正文简要展示 N4/N6/N8 诊断结论，完整诊断图可置于 Appendix。\n\n## 3.3 Effect of array size on central response\n- Fig. X(a): center_mean_abs comparison (`N468_center_mean_comparison.png`)\n- Fig. X(b): center_max_abs comparison (`N468_center_max_comparison.png`)\n- 需注明 N=4/N=6 在 0.90 s 的 boundary peak 风险。\n\n## 3.4 Spatial localization and non-uniformity of the central response\n- Fig. X: center_max_to_mean_ratio comparison (`N468_center_max_to_mean_ratio_comparison.png`)\n- Fig. X: P0-P4 peak value & peak period comparison (`N468_center_probe_peak_comparison.png`, `N468_center_probe_peak_period_comparison.png`)\n\n## 3.5 Front/rear response and transmission-like indicator\n- Fig. X: front_abs, rear_abs, S_rear_front comparison (`N468_front_rear_S_comparison.png`)\n- 明确 `S_rear_front` 仅为 transmission-like indicator。\n\n## Table X\n- 采用 `N468_summary_table_for_paper.csv` 的简化版（保留关键指标、峰值周期、boundary peak 标注）。\n"""

    for p, txt in [
        (NOTES_PATH, notes),
        (PPT_PLAN_PATH, ppt_plan),
        (PAPER_PLAN_PATH, paper_plan),
    ]:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(txt, encoding="utf-8")


def main() -> None:
    rows = build_catalog_rows()
    write_csv(
        CATALOG_PATH,
        rows,
        [
            "file_path", "file_type", "array_size", "scope", "source_script", "source_data",
            "main_metrics", "period_range", "mesh_level", "purpose", "recommended_use",
            "ppt_section", "paper_section", "caution_notes",
        ],
    )
    write_csv(
        MAP_PATH,
        build_data_source_map_rows(),
        [
            "metric", "definition", "computed_from", "source_csv", "source_script",
            "physical_meaning", "valid_interpretation", "invalid_interpretation", "boundary_issue",
            "recommended_plot", "recommended_table",
        ],
    )
    write_markdowns()

    print(f"catalog: {CATALOG_PATH}")
    print(f"data source map: {MAP_PATH}")
    print(f"interpretation notes: {NOTES_PATH}")
    print(f"ppt organization plan: {PPT_PLAN_PATH}")
    print(f"paper figure plan: {PAPER_PLAN_PATH}")


if __name__ == "__main__":
    main()
