# Configuration for MSPI Visualizer
from typing import Dict, Any

DEFAULT_VISUALIZER_CONFIG: Dict[str, Any] = {
    "log_level": "INFO",
    "output_dir": "mspi_visualizations_v2_default",
    "save_charts_as_html": False,
    "save_charts_as_png": False,
    "default_chart_height": 600,
    "plotly_template": "plotly_dark",
    "plot_order_history": ["T-5", "T-4", "T-3", "T-2", "T-1", "T-B", "T-A", "Now"],
    "rolling_intervals": ["5m", "15m", "30m", "60m"],
    "min_normalization_denominator": 1e-9,
    "min_value_for_ratio": 1e-6,
    "colorscales": {
        "mspi_heatmap": [[0.0, "rgb(139,0,0)"], [0.5, "rgb(240,240,240)"], [1.0, "rgb(0,0,139)"]],
        "net_value_heatmap": [[0.0, "rgb(160,0,0)"], [0.5, "rgb(240,240,240)"], [1.0, "rgb(0,160,0)"]],
        "net_volume_pressure_heatmap": [[0.0, "rgb(214,47,39)"], [0.5, "rgb(245,245,245)"], [1.0, "rgb(69,117,180)"]], # Added for Net Volume Pressure
        "net_delta_heuristic_heatmap": [ [ 0.0, "rgb(200,100,0)" ], [ 0.5, "rgb(240,240,240)" ], [ 1.0, "rgb(0,100,200)" ] ],
        "net_gamma_flow_heatmap": [ [ 0.0, "rgb(180,0,180)" ], [ 0.5, "rgb(240,240,240)" ], [ 1.0, "rgb(0,180,180)" ] ],
        "net_vega_flow_heatmap": [ [ 0.0, "rgb(255,120,0)" ], [ 0.5, "rgb(240,240,240)" ], [ 1.0, "rgb(0,120,255)" ] ],
        "net_theta_exposure_heatmap": [ [ 0.0, "rgb(255,0,0)" ], [ 0.5, "rgb(240,240,240)" ], [ 1.0, "rgb(0,200,0)" ] ]
    },
    "key_level_markers": {
        "Support": {"symbol": "triangle-up", "color": "rgb(34,139,34)", "name": "Support"},
        "Resistance": {"symbol": "triangle-down", "color": "rgb(220,20,60)", "name": "Resistance"},
        "High Conviction": {"symbol": "diamond", "color": "rgb(255,215,0)", "name": "High Conviction"},
        "Structure Change": {"symbol": "cross", "color": "rgb(0,191,255)", "name": "Structure Change"}
    },
    "signal_styles": {
        "bullish": {"color": "lime", "symbol": "triangle-up"}, "bearish": {"color": "red", "symbol": "triangle-down"},
        "sdag_bullish": {"color": "gold", "symbol": "diamond-wide"}, "sdag_bearish": {"color": "purple", "symbol": "diamond-wide-dot"},
        "expansion": {"color": "cyan", "symbol": "diamond-open"}, "contraction": {"color": "magenta", "symbol": "square-open"},
        "pin_risk": {"color": "yellow", "symbol": "star"}, "charm_cascade": {"color": "orange", "symbol": "hourglass"},
        "structure_change": {"color": "white", "symbol": "cross-thin"}, "flow_divergence": {"color": "lightblue", "symbol": "x-thin"},
        "default": {"color": "grey", "symbol": "circle"}
    },
    "column_names": {
        "net_volume_pressure": "net_volume_pressure",
        "net_value_pressure": "net_value_pressure",
        "mspi": "mspi",
        "strike": "strike_price", # Changed from "strike"
        "option_kind": "opt_kind",
        "expiration_date": "expiration_date", # Added for heatmaps
        "heuristic_net_delta_pressure": "heuristic_net_delta_pressure",
        "net_gamma_flow_at_strike": "net_gamma_flow",
        "net_vega_flow_at_strike": "net_vega_flow",
        "net_theta_exposure_at_strike": "net_theta_exposure",
        "net_delta_flow_total": "net_delta_flow_total",
        "true_net_volume_flow": "true_net_volume_flow",
        "true_net_value_flow": "true_net_value_flow"
    },
    "hover_settings": {
        "show_overview_metrics_default": True, "show_oi_structure_default": True, "show_details_section_default": True,
        "overview_metrics_config": [
          { "key": "mspi", "label": "MSPI", "precision": 3, "is_currency": False }, { "key": "sai", "label": "SAI", "precision": 3, "is_currency": False },
          { "key": "ssi", "label": "SSI", "precision": 3, "is_currency": False }, { "key": "arfi", "label": "ARFI", "precision": 3, "is_currency": False },
          { "key": "dag_custom", "label": "DAG(C)", "precision": 0, "is_currency": False }, { "key": "tdpi", "label": "TDPI", "precision": 0, "is_currency": False },
          { "key": "vri", "label": "VRI", "precision": 0, "is_currency": False },
          { "key": "sdag_multiplicative", "label": "SDAG(M)", "precision":0, "is_currency": False }, { "key": "sdag_directional", "label": "SDAG(D)", "precision":0, "is_currency": False },
          { "key": "sdag_weighted", "label": "SDAG(W)", "precision":0, "is_currency": False },  { "key": "sdag_volatility_focused", "label": "SDAG(VF)", "precision":0, "is_currency": False },
          { "key": "net_volume_pressure", "label": "Net Vol P (H)", "precision": 0, "is_currency": False }, { "key": "net_value_pressure", "label": "Net Val P (H)", "precision": 0, "is_currency": True },
          { "key": "heuristic_net_delta_pressure", "label": "Net Delta P (H)", "precision": 0, "is_currency": False },
          { "key": "net_gamma_flow_at_strike", "label": "Net Γ Flow", "precision": 0, "is_currency": False },
          { "key": "net_vega_flow_at_strike", "label": "Net ν Flow", "precision": 0, "is_currency": False },
          { "key": "net_theta_exposure_at_strike", "label": "Net θ Exp", "precision": 0, "is_currency": False },
          { "key": "net_delta_flow_total", "label": "True Net Δ Flow", "precision": 0, "is_currency": False },
          { "key": "true_net_volume_flow", "label": "True Net Vol Flow", "precision": 0, "is_currency": False },
          { "key": "true_net_value_flow", "label": "True Net Val Flow", "precision": 0, "is_currency": True }
        ],
        "oi_structure_metrics_config": [
          { "base_key": "dxoi", "label": "DxOI" }, { "base_key": "gxoi", "label": "GxOI" },
          { "base_key": "txoi", "label": "TxOI" }, { "base_key": "vxoi", "label": "VxOI" }
        ],
        "details_section_keys": [ "level_category", "conviction", "strategy", "rationale", "type", "agree_count", "exit_reason", "status_update" ],
        "chart_specific_hover": {
            "default": {"sections": ["base_info", "mspi_value"]},
            "mspi_heatmap": {"sections": ["base_info", "mspi_value", "core_indices"], "core_indices_keys": ["sai", "ssi"]},
            "net_value_heatmap": {"sections": ["base_info", "net_pressures"]},
            "net_volume_pressure_heatmap": {"sections": ["base_info", "net_pressures"]}, 
            "net_greek_flow_heatmap": {"sections": ["base_info", "selected_greek_flow", "overview_metrics"]},
            "mspi_components": {"sections": ["base_info", "overview_metrics", "oi_structure"]},
            "sdag": {"sections": ["base_info", "sdag_specific_value", "core_indices"], "core_indices_keys": ["mspi", "sai"]},
            "sdag_net": {"sections": ["base_info", "sdag_specific_value"]},
            "tdpi": {"sections": ["base_info", "tdpi_specific_values"]},
            "vri": {"sections": ["base_info", "vri_specific_values"]},
            "key_levels": {"sections": ["base_info", "core_metrics_context", "details_section"]},
            "trading_signals": {"sections": ["base_info", "core_metrics_context", "details_section"]}
        }
    },
    "chart_specific_params": {
        "raw_greek_charts_price_range_pct": 7.5,
        "combined_flow_chart_price_range_pct": 12.0,
        "mspi_components_bar_colors": {
            "mspi": { "pos": "darkblue", "neg": "darkred" }, "dag_custom_norm": { "pos": "rgb(255,215,0)", "neg": "rgb(128,0,128)" },
            "tdpi_norm": { "pos": "green", "neg": "red", "is_border": True }, "vri_norm": { "pos": "cyan", "neg": "magenta" },
            "sdag_multiplicative_norm": { "pos": "#FFA07A", "neg": "#6A5ACD" }, "sdag_directional_norm": { "pos": "#FFD700", "neg": "#8A2BE2" },
            "sdag_weighted_norm": { "pos": "#98FB98", "neg": "#FF6347" }, "sdag_volatility_focused_norm": { "pos": "#AFEEEE", "neg": "#DA70D6" }
        },
        "show_net_sdag_trace": True, "net_sdag_trace_default_visibility": "legendonly",
        "net_sdag_marker_style": { "symbol": "diamond", "color": "rgba(255, 255, 255, 0.7)", "size": 8, "line": { "color": "white", "width": 1 } },
        "component_comparison_height": 600, "volval_comparison_height": 600, "key_levels_height": 600, "trading_signals_height": 600, "recommendations_table_height": 650,
        "recommendations_table_column_display_map": {
            "id": "ID", "Category": "Category", "direction_label": "Bias/Type", "strike": "Strike", "strategy": "Strategy / Note",
            "conviction_stars": "Conv★", "raw_conviction_score": "Score", "status": "Status",
            "entry_ideal": "Entry", "target_1": "T1", "target_2": "T2", "stop_loss": "SL",
            "rationale": "Rationale", "target_rationale": "Tgt. Logic",
            "mspi": "MSPI", "sai": "SAI", "ssi": "SSI", "arfi": "ARFI",
            "issued_ts": "Issued", "last_adjusted_ts": "Adjusted", "exit_reason":"Exit Info", "type": "Signal Src", "status_update": "Last Update"
        },
        "combined_rolling_flow_chart_barmode": "overlay",
        "rolling_flow_customization": {
          "5m": {"volume_positive_color": "#2ca02c", "volume_negative_color": "#d62728", "volume_opacity": 0.8, "value_positive_fill_color": "rgba(44,160,44,0.15)", "value_negative_fill_color": "rgba(214,39,40,0.15)", "value_positive_line_color": "rgba(44,160,44,0.6)", "value_negative_line_color": "rgba(214,39,40,0.6)"},
          "15m": {"volume_positive_color": "#98df8a", "volume_negative_color": "#ff9896", "volume_opacity": 0.75, "value_positive_fill_color": "rgba(152,223,138,0.15)", "value_negative_fill_color": "rgba(255,152,150,0.15)", "value_positive_line_color": "rgba(152,223,138,0.55)", "value_negative_line_color": "rgba(255,152,150,0.55)"},
          "30m": {"volume_positive_color": "#1f77b4", "volume_negative_color": "#ff7f0e", "volume_opacity": 0.7, "value_positive_fill_color": "rgba(31,119,180,0.1)", "value_negative_fill_color": "rgba(255,127,14,0.1)", "value_positive_line_color": "rgba(31,119,180,0.5)", "value_negative_line_color": "rgba(255,127,14,0.5)"},
          "60m": {"volume_positive_color": "#aec7e8", "volume_negative_color": "#ffbb78", "volume_opacity": 0.65, "value_positive_fill_color": "rgba(174,199,232,0.1)", "value_negative_fill_color": "rgba(255,187,120,0.1)", "value_positive_line_color": "rgba(174,199,232,0.45)", "value_negative_line_color": "rgba(255,187,120,0.45)"},
           "defaults": {"volume_positive_color": "#cccccc", "volume_negative_color": "#777777", "volume_opacity": 0.7, "value_positive_fill_color": "rgba(204,204,204,0.1)", "value_negative_fill_color": "rgba(119,119,119,0.1)", "value_positive_line_color": "rgba(204,204,204,0.5)", "value_negative_line_color": "rgba(119,119,119,0.5)"}
        }
    },
    "legend_settings": { "orientation": "v", "y_anchor": "top", "y_pos": 1, "x_anchor": "left", "x_pos": 1.02, "trace_order": "reversed" }
}