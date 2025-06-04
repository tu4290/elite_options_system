# charts/component_charts.py
"""
Standalone functions for creating complex component and flow comparison charts
for the MSPIVisualizer. These functions are intended to be called from
the main visualizer class and rely on configuration and pre-processed
data passed as arguments.
Version: ComponentCharts-Canon-V1.1.0 - Aligned with PlotUtils V1.0.1 & BaseChartUtils V1.1.0
"""

import logging
from typing import Dict, Any, Optional, List, Tuple, Union, Deque
from collections import deque # For create_combined_rolling_flow_chart

import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Import utility modules
import plot_utils # Alias to plot_utils_module in function args
import charts.base_chart_utils as base_chart_utils # Alias in function args

def create_component_comparison(
    instance_logger: logging.Logger,
    config: Dict[str, Any], # Combined config (Visualizer specific merged with relevant app config)
    plot_utils_module: Any, # The imported plot_utils module
    processed_data: pd.DataFrame,
    symbol: str,
    current_price: Optional[float],
    fetch_timestamp: Optional[str],
    trace_visibility: Optional[Dict[str, Any]] = None,
    col_strike: str = "strike_price", # Default from viz config
    col_mspi: str = "mspi"     # Default from viz config
) -> go.Figure:
    """
    Creates a comparison chart of MSPI and its underlying components.
    'config' should already contain resolved component enablement flags (e.g., a_dag_enabled_viz)
    and corresponding column names (e.g., dag_norm_col_cfg).
    """
    chart_func_logger = instance_logger.getChild("CreateMSPIComponentComparison_V1.1")
    chart_func_logger.info(f"Creating MSPI component comparison chart for {symbol}")

    chart_specific_params = config.get("chart_specific_params", {})
    comp_chart_height = chart_specific_params.get("component_comparison_height", config.get("default_chart_height", 800))
    plotly_template = config.get("plotly_template", "plotly_dark")
    # Default bar colors for components, e.g., {"MSPI_Score": "white", "DAG": "blue", "TDPI": "orange"}
    default_bar_colors = chart_specific_params.get("mspi_components_bar_colors", {})
    legend_config = config.get("legend_settings", {})
    hover_settings = config.get("hover_settings", {})
    column_names_config = config.get("column_names", {}) # For _create_hover_text if used
    price_line_config = config.get("price_line_config", {})
    timestamp_config = config.get("timestamp_config", {"enabled": True})
    # Saving parameters (though saving is usually handled by orchestrator)
    # output_dir = config.get("output_dir")
    # save_charts_html = config.get("save_charts_as_html", False)
    # save_charts_png = config.get("save_charts_as_png", False)
    # plot_width_save = config.get("PLOT_WIDTH", 1200) # Example from old config

    # Component specific configs are expected to be already resolved and present in `config` by the orchestrator
    a_dag_enabled = config.get("a_dag_enabled_viz", False)
    dag_norm_col = config.get("dag_norm_col_cfg", "a_dag_norm") # Default to its output if not specified elsewhere
    d_tdpi_enabled = config.get("d_tdpi_enabled_viz", False)
    tdpi_norm_col = config.get("tdpi_norm_col_cfg", "d_tdpi_norm")
    vri_2_0_enabled = config.get("vri_2_0_enabled_viz", False)
    vri_norm_col = config.get("vri_norm_col_cfg", "vri_2_0_norm")
    e_sdag_enabled = config.get("e_sdag_enabled_viz", False)
    e_sdag_composite_norm_col = config.get("e_sdag_composite_norm_col_cfg", "e_sdag_composite_norm")
    # Original SDAG method configs (for plotting individual original SDAGs if enabled for component chart)
    # This structure assumes orchestrator has placed it in config like this:
    dag_method_configs_for_plot = config.get("dag_method_configs", {}).get("components", {}) # Get the 'components' sub-dict

    required_cols = [col_strike, col_mspi]
    if a_dag_enabled: required_cols.append(dag_norm_col)
    if d_tdpi_enabled: required_cols.append(tdpi_norm_col)
    if vri_2_0_enabled: required_cols.append(vri_norm_col)
    if e_sdag_enabled: required_cols.append(e_sdag_composite_norm_col)
    
    # Add original SDAG components if their configs say to plot them here
    for comp_key, comp_detail_cfg in dag_method_configs_for_plot.items():
        if isinstance(comp_detail_cfg, dict) and comp_detail_cfg.get("enabled", False) and \
           comp_detail_cfg.get("plot_in_component_comparison", False): # Custom flag in config
            # Use 'normalized_column' if it exists, otherwise fallback to a conventional name
            # The actual column name for original SDAGs might be like 'sdag_multiplicative_norm'
            # This mapping logic needs to be robust based on ITS output.
            # Defaulting to `f"sdag_{comp_key}_norm"` if not specified in component config.
            norm_col_for_plot = comp_detail_cfg.get("normalized_column", f"sdag_{comp_key}_norm")
            if norm_col_for_plot: required_cols.append(norm_col_for_plot)

    df_validated, cols_ok = plot_utils_module._ensure_columns(processed_data, list(set(required_cols)), chart_func_logger)
    if not cols_ok or df_validated.empty:
        chart_func_logger.warning(f"Data for component comparison chart for {symbol} is empty or missing required columns.")
        return plot_utils_module._create_empty_figure(instance_logger, comp_chart_height, plotly_template, f"Missing data for {symbol} Component Comparison")

    plot_data = df_validated.sort_values(by=col_strike)
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Plot MSPI Score as a line on primary y-axis
    mspi_hover_texts = [
        plot_utils_module._create_hover_text(row, "mspi_score_line_comp_chart", hover_settings, column_names_config, chart_func_logger,
                                       extra_context={"Symbol": symbol, "Metric": col_mspi.replace("_"," ").title()})
        for _, row in plot_data.iterrows()
    ] if plot_utils_module._check_hover_enabled(hover_settings, "mspi_score_line_comp_chart") else None
    
    mspi_line_color = default_bar_colors.get(col_mspi, {}).get("pos", default_bar_colors.get("mspi",{}).get("pos", "white")) # Try specific "mspi" key or a general "MSPI_Score" key
    fig.add_trace(go.Scatter(
        x=plot_data[col_strike], y=plot_data[col_mspi], name=col_mspi.replace("_"," ").title(),
        mode='lines+markers', line=dict(color=str(mspi_line_color), width=2),
        hovertext=mspi_hover_texts, hoverinfo="text" if mspi_hover_texts else "skip",
        visible=trace_visibility.get(col_mspi.replace("_"," ").title(), True) if trace_visibility else True
    ), secondary_y=False)

    # Plot components as bars on secondary y-axis
    component_traces_to_plot: List[Dict[str, str]] = []
    if a_dag_enabled: component_traces_to_plot.append({"name": "A-DAG", "col": dag_norm_col, "color_key": "a_dag_norm"})
    if d_tdpi_enabled: component_traces_to_plot.append({"name": "D-TDPI", "col": tdpi_norm_col, "color_key": "d_tdpi_norm"})
    if vri_2_0_enabled: component_traces_to_plot.append({"name": "VRI 2.0", "col": vri_norm_col, "color_key": "vri_2_0_norm"})
    if e_sdag_enabled: component_traces_to_plot.append({"name": "E-SDAG Comp.", "col": e_sdag_composite_norm_col, "color_key": "e_sdag_composite_norm"})

    for comp_key, comp_detail_cfg in dag_method_configs_for_plot.items():
        if isinstance(comp_detail_cfg, dict) and comp_detail_cfg.get("enabled", False) and \
           comp_detail_cfg.get("plot_in_component_comparison", False):
            norm_col_for_plot = comp_detail_cfg.get("normalized_column", f"sdag_{comp_key}_norm")
            comp_display_name = comp_detail_cfg.get("name_for_plot", f"SDAG({comp_key.title()[:1]})") # Example name
            color_key_for_comp = comp_detail_cfg.get("color_config_key", f"sdag_{comp_key}_norm")
            if norm_col_for_plot:
                component_traces_to_plot.append({"name": comp_display_name, "col": norm_col_for_plot, "color_key": color_key_for_comp})

    for comp_info in component_traces_to_plot:
        if comp_info["col"] not in plot_data.columns:
            chart_func_logger.warning(f"Component column '{comp_info['col']}' for '{comp_info['name']}' not found. Skipping trace.")
            continue
        
        comp_hover_texts = [
            plot_utils_module._create_hover_text(row, f"{comp_info['name'].lower()}_bar_comp_chart", hover_settings, column_names_config, chart_func_logger,
                                           extra_context={"Symbol": symbol, "Metric": comp_info['name']})
            for _, row in plot_data.iterrows()
        ] if plot_utils_module._check_hover_enabled(hover_settings, f"{comp_info['name'].lower()}_bar_comp_chart") else None

        # Get colors from config: pos and neg based on component's color_key
        comp_color_cfg = default_bar_colors.get(comp_info["color_key"], {})
        bar_color_positive = comp_color_cfg.get("pos", "rgba(0,128,255,0.7)") # Default blueish
        bar_color_negative = comp_color_cfg.get("neg", "rgba(255,128,0,0.7)") # Default orangish
        
        # Create separate traces for positive and negative parts for distinct colors if needed
        # Or, if plotly handles positive/negative colors for bars based on value, one trace is enough.
        # For simplicity with Plotly bars, often a single color is set per bar trace,
        # or a color array can be passed. If colors are dynamically based on value (pos/neg),
        # this needs more complex color array generation.
        # The mspi_components_bar_colors in config suggests distinct pos/neg colors.
        # This typically implies separate traces or a more complex marker_color array.
        # For now, let's use a single color and assume it's a neutral one or the "positive" one.
        # TODO: Implement logic for pos/neg bar colors if strictly required by config structure.
        
        # Simplified: use positive color for now
        effective_bar_color = bar_color_positive 

        fig.add_trace(go.Bar(
            x=plot_data[col_strike], y=plot_data[comp_info["col"]], name=comp_info["name"],
            marker_color=str(effective_bar_color), opacity=0.7,
            hovertext=comp_hover_texts, hoverinfo="text" if comp_hover_texts else "skip",
            visible=trace_visibility.get(comp_info["name"], True) if trace_visibility else True
        ), secondary_y=True)

    chart_title = f"{symbol} MSPI & Component Analysis"
    if fetch_timestamp:
        try: chart_title += f" (Data: {pd.to_datetime(fetch_timestamp).strftime('%Y-%m-%d %H:%M:%S')})"
        except: chart_title += f" (Data: {fetch_timestamp})"

    fig.update_layout(
        height=int(comp_chart_height), template=plotly_template,
        title=dict(text=chart_title, x=0.5, xanchor='center'),
        barmode='relative', 
        xaxis_title="Strike Price",
        yaxis_title=f"{col_mspi.replace('_',' ').title()} (Line)",
        yaxis2_title="Component Scores (Bars)",
        legend=legend_config,
        showlegend=bool(legend_config.get("show_legend", True)),
        hovermode=str(hover_settings.get("mode", "closest")),
        xaxis_showgrid=config.get("show_grid", True), yaxis_showgrid=config.get("show_grid", True), yaxis2_showgrid=False
    )

    if pd.notna(current_price) and price_line_config.get("show_current_price_line", True):
        plot_utils_module._add_price_line(
            fig, current_price,
            str(price_line_config.get("current_price_line_color", "rgba(255,255,0,0.6)")),
            int(price_line_config.get("current_price_line_width", 1.5)),
            str(price_line_config.get("current_price_line_dash", "dash")),
            "Current Price", instance_logger=chart_func_logger
        )

    if timestamp_config.get("enabled", True):
        plot_utils_module._add_timestamp_annotation(fig, chart_func_logger, timestamp_config)

    chart_func_logger.info(f"MSPI Component Comparison chart for {symbol} generated successfully.")
    return fig


def create_combined_rolling_flow_chart(
    instance_logger: logging.Logger,
    config: Dict[str, Any],
    plot_utils_module: Any, # The imported plot_utils module
    processed_data: pd.DataFrame,
    symbol: str,
    current_price: Optional[float],
    fetch_timestamp: Optional[str],
    col_strike: str = "strike_price", # Default from viz config
    trace_visibility: Optional[Dict[str, Any]] = None,
    selected_price_range_pct_override: Optional[float] = None,
    bar_metric_prefix: str = "volmbs", # e.g., 'volmbs' -> volmbs_5m, volmbs_15m
    area_metric_prefix: str = "valuebs", # e.g., 'valuebs' -> valuebs_5m, valuebs_15m
    component_history: Optional[Deque[Tuple[float, pd.DataFrame]]] = None # For ghost traces
) -> go.Figure:
    """
    Creates a combined chart with bars for one metric (e.g., net volume flow) and
    area plots for another (e.g., net value flow), across different rolling intervals.
    Optionally includes historical "ghost" traces for the primary metrics if component_history is provided.
    """
    chart_func_logger = instance_logger.getChild("CreateCombinedRollingFlow_V1.1")
    chart_func_logger.info(f"Creating combined rolling flow chart for {symbol} (Bar: {bar_metric_prefix}, Area: {area_metric_prefix})")

    chart_specific_params = config.get("chart_specific_params", {})
    chart_height = chart_specific_params.get("combined_flow_chart_height", config.get("default_chart_height", 750))
    # Rolling intervals (e.g., "5m", "15m") are taken from the main config this time
    rolling_interval_suffixes: List[str] = config.get("rolling_intervals", ["5m", "15m", "30m", "60m"])
    
    plotly_template = config.get("plotly_template", "plotly_dark")
    legend_config = config.get("legend_settings", {})
    # Color/style customization for rolling flow traces, e.g., {"5m": {"volume_positive_color": "...", ...}, "defaults": {...}}
    flow_customization_map = chart_specific_params.get("rolling_flow_customization", {})
    barmode_cfg = chart_specific_params.get("combined_rolling_flow_chart_barmode", "relative") # 'group', 'overlay', 'relative'
    default_price_range_pct_cfg = chart_specific_params.get("combined_flow_chart_price_range_pct", 15.0)
    price_line_config = config.get("price_line_config", {})
    timestamp_config = config.get("timestamp_config", {"enabled": True})
    hover_settings = config.get("hover_settings", {})
    column_names_config = config.get("column_names", {})
    # Ghost trace settings from chart_specific_params (similar to volval comparison)
    ghost_settings = chart_specific_params.get("rolling_flow_ghost_settings", chart_specific_params.get("volval_ghost_settings", {}))


    # Construct full column names based on prefixes and interval suffixes
    # Example: bar_metric_prefix="volmbs", suffix="5m" -> "volmbs_5m"
    required_cols_flow: List[str] = [col_strike]
    for suffix in rolling_interval_suffixes:
        required_cols_flow.append(f"{bar_metric_prefix}_{suffix}")
        required_cols_flow.append(f"{area_metric_prefix}_{suffix}")
    
    df_validated, cols_ok = plot_utils_module._ensure_columns(processed_data, list(set(required_cols_flow)), chart_func_logger)
    if not cols_ok or df_validated.empty:
        chart_func_logger.warning(f"Data for combined rolling flow chart for {symbol} is empty or missing required columns. Needed prefixes: {bar_metric_prefix}, {area_metric_prefix} with suffixes: {rolling_interval_suffixes}")
        return plot_utils_module._create_empty_figure(instance_logger, chart_height, plotly_template, f"Missing data for {symbol} Rolling Flow")

    plot_data = df_validated.sort_values(by=col_strike).copy()
    fig = make_subplots(specs=[[{"secondary_y": True}]]) # Bars on primary, Areas on secondary

    # --- Plot Traces for Each Interval ---
    for interval_suffix in rolling_interval_suffixes:
        interval_style_cfg = flow_customization_map.get(interval_suffix, flow_customization_map.get("defaults", {}))
        
        # Bar Metric (e.g., Volume Flow)
        bar_col_name = f"{bar_metric_prefix}_{interval_suffix}"
        if bar_col_name in plot_data.columns:
            bar_hover_texts = [
                plot_utils_module._create_hover_text(row, f"{bar_metric_prefix}_{interval_suffix}_bar", hover_settings, column_names_config, chart_func_logger,
                                               extra_context={"Symbol": symbol, "Interval": interval_suffix, "Metric": bar_metric_prefix.upper()})
                for _, row in plot_data.iterrows()
            ] if plot_utils_module._check_hover_enabled(hover_settings, f"{bar_metric_prefix}_{interval_suffix}_bar") else None
            
            # Handle positive/negative bar colors if specified
            positive_bar_color = interval_style_cfg.get("volume_positive_color", "rgba(0,150,0,0.7)")
            negative_bar_color = interval_style_cfg.get("volume_negative_color", "rgba(200,0,0,0.7)")
            bar_opacity = float(interval_style_cfg.get("volume_opacity", 0.7))

            # Create color array for bars based on value
            bar_colors_array = np.where(plot_data[bar_col_name] >= 0, positive_bar_color, negative_bar_color)
            
            fig.add_trace(go.Bar(
                x=plot_data[col_strike], y=plot_data[bar_col_name],
                name=f"{bar_metric_prefix.replace('bs','').replace('mbs','').upper()} {interval_suffix}", # Cleaner name
                marker=dict(color=bar_colors_array, opacity=bar_opacity), # Use color array
                hovertext=bar_hover_texts, hoverinfo="text" if bar_hover_texts else "skip",
                legendgroup=f"group_{interval_suffix}", # Group bar and area for same interval
                visible=trace_visibility.get(f"{bar_metric_prefix.upper()} {interval_suffix}", True) if trace_visibility else True
            ), secondary_y=False)

        # Area Metric (e.g., Value Flow)
        area_col_name = f"{area_metric_prefix}_{interval_suffix}"
        if area_col_name in plot_data.columns:
            area_hover_texts = [
                plot_utils_module._create_hover_text(row, f"{area_metric_prefix}_{interval_suffix}_area", hover_settings, column_names_config, chart_func_logger,
                                                extra_context={"Symbol": symbol, "Interval": interval_suffix, "Metric": area_metric_prefix.upper()})
                for _, row in plot_data.iterrows()
            ] if plot_utils_module._check_hover_enabled(hover_settings, f"{area_metric_prefix}_{interval_suffix}_area") else None

            positive_fill_color = interval_style_cfg.get("value_positive_fill_color", "rgba(0,200,0,0.2)")
            negative_fill_color = interval_style_cfg.get("value_negative_fill_color", "rgba(255,0,0,0.2)")
            positive_line_color = interval_style_cfg.get("value_positive_line_color", "rgba(0,200,0,0.6)")
            negative_line_color = interval_style_cfg.get("value_negative_line_color", "rgba(255,0,0,0.6)")
            
            # Plotly area charts (fill='tozeroy') don't directly support conditional fill colors based on y-value in a single trace.
            # A common workaround is to plot two traces: one for positive, one for negative, or use a simpler single color.
            # For simplicity, using a single representative fill/line color for the area trace per interval.
            # Let's use the "positive" colors as the primary representation.
            area_fill_color = positive_fill_color
            area_line_color = positive_line_color
            
            fig.add_trace(go.Scatter(
                x=plot_data[col_strike], y=plot_data[area_col_name],
                name=f"{area_metric_prefix.replace('bs','').replace('mbs','').upper()} {interval_suffix}",
                mode='lines', fill='tozeroy',
                fillcolor=str(area_fill_color), line=dict(color=str(area_line_color), width=1.5),
                hovertext=area_hover_texts, hoverinfo="text" if area_hover_texts else "skip",
                legendgroup=f"group_{interval_suffix}", # Group with bar
                visible=trace_visibility.get(f"{area_metric_prefix.upper()} {interval_suffix}", True) if trace_visibility else True
            ), secondary_y=True)

    # Ghost traces for historical component_history (if provided)
    # This part needs careful definition of what metrics from history to plot (e.g., bar_metric_prefix + a primary interval)
    # Let's assume we ghost the primary bar and area metrics for the *first* rolling_interval_suffix.
    if component_history and ghost_settings.get("enabled", True) and rolling_interval_suffixes:
        num_ghosts = int(ghost_settings.get("number_of_ghosts", 3))
        base_opacity = float(ghost_settings.get("base_opacity", 0.3))
        opacity_step = float(ghost_settings.get("opacity_step", 0.08))
        min_opacity = float(ghost_settings.get("min_opacity", 0.1))
        
        primary_interval_suffix_for_ghost = rolling_interval_suffixes[0] # e.g., "5m"
        ghost_bar_col = f"{bar_metric_prefix}_{primary_interval_suffix_for_ghost}"
        ghost_area_col = f"{area_metric_prefix}_{primary_interval_suffix_for_ghost}"

        for i, (ts_hist, hist_df) in enumerate(list(component_history)[:num_ghosts]):
            if not isinstance(hist_df, pd.DataFrame) or hist_df.empty: continue
            
            hist_df_sorted = hist_df.sort_values(by=col_strike)
            current_opacity = max(min_opacity, base_opacity - (i * opacity_step))
            
            # Ghost for Bar Metric
            if ghost_bar_col in hist_df_sorted.columns:
                bar_style_cfg_ghost = flow_customization_map.get(primary_interval_suffix_for_ghost, flow_customization_map.get("defaults", {}))
                positive_bar_color_ghost = bar_style_cfg_ghost.get("volume_positive_color", "grey")
                # For ghost bars, usually a single color is fine
                effective_ghost_bar_color = plot_utils_module._parse_color_string(positive_bar_color_ghost, current_opacity, chart_func_logger)

                fig.add_trace(go.Bar(
                    x=hist_df_sorted[col_strike], y=hist_df_sorted[ghost_bar_col],
                    name=f"Hist Bar {i+1} ({primary_interval_suffix_for_ghost})",
                    marker_color=str(effective_ghost_bar_color),
                    hoverinfo='skip', legendgroup="ghost_bars", showlegend=(i==0), # Show only one legend item for all ghost bars
                    visible=trace_visibility.get(f"Historical Bars", True) if trace_visibility else True
                ), secondary_y=False)

            # Ghost for Area Metric
            if ghost_area_col in hist_df_sorted.columns:
                area_style_cfg_ghost = flow_customization_map.get(primary_interval_suffix_for_ghost, flow_customization_map.get("defaults", {}))
                area_line_color_ghost = area_style_cfg_ghost.get("value_positive_line_color", "darkgrey")
                effective_ghost_area_color = plot_utils_module._parse_color_string(area_line_color_ghost, current_opacity, chart_func_logger)

                fig.add_trace(go.Scatter(
                    x=hist_df_sorted[col_strike], y=hist_df_sorted[ghost_area_col],
                    name=f"Hist Area {i+1} ({primary_interval_suffix_for_ghost})", mode='lines',
                    line=dict(color=str(effective_ghost_area_color), width=1, dash='dot'),
                    hoverinfo='skip', legendgroup="ghost_areas", showlegend=(i==0),
                    visible=trace_visibility.get(f"Historical Areas", True) if trace_visibility else True
                ), secondary_y=True)

    chart_title = f"{symbol} Rolling Net Flows ({bar_metric_prefix.upper()} vs {area_metric_prefix.upper()})"
    if fetch_timestamp:
        try: chart_title += f" (Data: {pd.to_datetime(fetch_timestamp).strftime('%Y-%m-%d %H:%M:%S')})"
        except: chart_title += f" (Data: {fetch_timestamp})"

    fig.update_layout(
        height=int(chart_height), template=plotly_template, title=dict(text=chart_title, x=0.5, xanchor='center'),
        barmode=str(barmode_cfg), 
        xaxis_title="Strike Price",
        yaxis_title=f"{bar_metric_prefix.replace('bs','').replace('mbs','').upper()} (Bars)",
        yaxis2_title=f"{area_metric_prefix.replace('bs','').replace('mbs','').upper()} (Area)",
        legend=legend_config, showlegend=bool(legend_config.get("show_legend", True)),
        hovermode=str(hover_settings.get("mode", "x unified")),
        xaxis_showgrid=config.get("show_grid", True), yaxis_showgrid=config.get("show_grid", True), yaxis2_showgrid=False
    )

    effective_price_range_pct_val = selected_price_range_pct_override if selected_price_range_pct_override is not None else default_price_range_pct_cfg
    if pd.notna(current_price) and pd.notna(effective_price_range_pct_val) and effective_price_range_pct_val > 0:
        lower_bound = current_price * (1 - effective_price_range_pct_val / 100)
        upper_bound = current_price * (1 + effective_price_range_pct_val / 100)
        fig.update_xaxes(range=[lower_bound, upper_bound])
        chart_func_logger.info(f"Applied X-axis price range ({effective_price_range_pct_val}%): {lower_bound:.2f} - {upper_bound:.2f}")
    
    if pd.notna(current_price) and price_line_config.get("show_current_price_line", True):
        plot_utils_module._add_price_line(
            fig, current_price,
            str(price_line_config.get("current_price_line_color", "rgba(255,255,0,0.6)")),
            int(price_line_config.get("current_price_line_width", 1.5)),
            str(price_line_config.get("current_price_line_dash", "dash")),
            "Current Price", instance_logger=chart_func_logger
        )

    if timestamp_config.get("enabled", True):
        plot_utils_module._add_timestamp_annotation(fig, chart_func_logger, timestamp_config)
    
    chart_func_logger.info(f"Combined Rolling Flow chart for {symbol} generated successfully.")
    return fig
