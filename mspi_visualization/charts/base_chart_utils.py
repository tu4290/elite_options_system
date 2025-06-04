# charts/base_chart_utils.py
"""
Utility functions for creating base charts for the MSPIVisualizer.
These functions are intended to be called from the main visualizer class
and rely on configuration and pre-processed data passed as arguments.
Version: BaseChartUtils-Canon-V1.1.0 - Alignment with PlotUtils V1.0.1
"""

import logging
from typing import Dict, Any, Optional, List, Tuple, Union
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Import the plot_utils module to access its functions
# This assumes plot_utils.py is in the same parent directory or accessible via PYTHONPATH
from .. import plot_utils # This will be resolved by the calling environment.


def _build_volval_hovertemplate(
    col_strike: str,
    config: Dict[str, Any], # Visualizer-specific config
    hover_df: pd.DataFrame,
    plotted_labels: List[str],
    instance_logger: logging.Logger # Added instance_logger
) -> Dict[str, str]:
    """
    Builds hover templates for volume and value plots, potentially including order history.

    Args:
        col_strike: Name of the strike column.
        config: The visualizer-specific configuration dictionary.
        hover_df: DataFrame containing data for hover information.
        plotted_labels: List of labels for which plots are being generated.
        instance_logger: Logger instance.

    Returns:
        A dictionary mapping labels to their hovertemplate strings.
    """
    hovertemplates: Dict[str, str] = {}
    plot_order_history_config = config.get("plot_order_history", [])
    column_names_config = config.get("column_names", {}) # For resolving actual column names
    hover_settings = config.get("hover_settings", {})   # For generic hover text creation

    log = instance_logger.getChild("_build_volval_hovertemplate_baseutil")

    for label in plotted_labels:
        # Determine the chart_type_hover_key for _create_hover_text
        # This is a heuristic; a more robust mapping might be needed if labels are very dynamic
        chart_type_key_for_hover = "volval_line" # A generic key
        if "volume" in label.lower():
            chart_type_key_for_hover = "volume_pressure_line"
        elif "value" in label.lower():
            chart_type_key_for_hover = "value_pressure_line"

        # Create hover texts for each row, this assumes hover_df is the main plotting data for these lines.
        # plot_utils._create_hover_text will generate the full HTML string.
        # The go.Scatter hovertemplate will just be "%{hovertext}<extra></extra>"
        # We need to generate a list of these HTML strings, one for each point.
        
        # For this _build_volval_hovertemplate, it seems the original intent might have been
        # to construct a Plotly hovertemplate string directly, rather than a list of pre-rendered HTML.
        # Let's stick to the Plotly template string construction:

        template_parts = [f"<b>{label}</b><br>"]
        custom_data_fields_for_template = [] # List of column names for customdata

        # Always include strike
        # Ensure col_strike from function arg is the one we use for customdata mapping
        custom_data_fields_for_template.append(col_strike)
        template_parts.append(f"{col_strike.replace('_',' ').title()}: %{{customdata[0]:.2f}}<br>")
        
        # Add the Y-value itself
        template_parts.append(f"{label.split('(')[0].strip()}: %{{y:,.2f}}<br>")


        # Check if this label corresponds to a type for which order history should be plotted
        order_history_for_label_config = None
        # plot_order_history_config is like: ["T-5", "T-4", "T-3", "T-2", "T-1", "T-B", "T-A", "Now"]
        # This implies fixed column names like "NetOI_T-5", "NetOI_T-4" etc.
        # The _build_volval_hovertemplate was originally in MSPIVisualizerV2 where self.plot_order_history was these strings.
        # It would then generate column names like f"{metric_prefix}{slot_name}" (e.g., "NetOIT-5")
        # For now, let's assume that if plot_order_history is configured, it refers to suffixes for the *current* metric label's base.
        
        # This part needs more clarity on how 'plotted_labels' relate to 'plot_order_history_config'
        # if 'plot_order_history_config' is just a list of time slots.
        # The original _build_volval_hovertemplate in mspi_visualizer_v2.py seemed to imply
        # that the `hover_df` would already have columns named like `NetOIT-5`, `NetOIT-4`, etc.
        # and `plotted_labels` were fixed like "Net Order Imbalance", "Net Order Exposure".

        # Let's assume `hover_df` contains columns matching the `params_to_plot_values` in `plot_order_history` config.
        # Example config (visualizer_config.py -> DEFAULT_VISUALIZER_CONFIG):
        # "plot_order_history": [
        #     {"label": "Now", "column": "current_value_col", "format": ".2f"}, 
        #     {"label": "T-1", "column": "t_minus_1_col", "format": ".0f"}
        # ],
        # The current `plot_order_history` from mspi_config.py is just a list of strings.
        # This means we assume hover_df has columns like `NetVolPressureT-5`, etc.
        # Let's re-evaluate the goal of _build_volval_hovertemplate based on its prior context.
        # It's meant for the VolVal Comparison chart, which plots 'Net Volume Pressure' and 'Net Value Pressure'.
        # The "ghost traces" were handled separately in `create_volval_comparison`.
        # So, this hovertemplate is likely for the *main* current traces, not for dynamically adding history.
        
        # For simplicity and robustness, let's use the generic plot_utils._create_hover_text.
        # To do this, _build_volval_hovertemplate would need to return a list of HTML strings, not a template string.
        # This seems to be a change in direction from the original code.
        # Given the structure, plot_utils._create_hover_text is the more modern way.
        
        # If the goal is truly a PLOTLY TEMPLATE STRING for customdata:
        # Reverting to a simpler interpretation for now: just strike and y-value for these main lines.
        # Any additional metrics for hover on these specific lines should be part of 'overview_metrics_config'
        # and handled by plot_utils._create_hover_text if that's used instead.
        # For now, this function provides a basic Plotly template string.
        
        # Let's assume we want to add a few standard metrics from `hover_df` if they exist.
        common_hover_metrics = ['sai', 'ssi', 'arfi'] # Example
        for idx, metric_key in enumerate(common_hover_metrics):
            actual_metric_col_name = column_names_config.get(metric_key, metric_key) # Get mapped name
            if actual_metric_col_name in hover_df.columns:
                custom_data_fields_for_template.append(actual_metric_col_name)
                template_parts.append(f"{metric_key.upper()}: %{{customdata[{len(custom_data_fields_for_template)-1}]:.3f}}<br>")
        
        template_parts.append("<extra></extra>") # Important for clean hover
        hovertemplates[label] = {
            "template_string": "".join(template_parts),
            "custom_data_columns": custom_data_fields_for_template # List of column names for customdata stack
        }
    
    return hovertemplates


def _create_raw_greek_chart(
    instance_logger: logging.Logger,
    config: Dict[str, Any], 
    plot_utils_module: Any, 
    col_strike: str,
    col_opt_kind: str,
    # NEW: underlying_price_scalar is now explicitly passed for context
    underlying_price_scalar: Optional[float], 
    processed_data: pd.DataFrame,
    metric_col: str, # The specific greek/metric column to plot from processed_data
    chart_title_part: str, # E.g., "Gamma Exposure", "TDPI"
    xaxis_title: str, # E.g., "Strike Price"
    call_color: str,
    put_color: str,
    symbol: str,
    # current_price: Optional[float], # This is now underlying_price_scalar
    selected_price_range_pct_override: Optional[float] = None,
    fetch_timestamp: Optional[str] = None,
    # NEW: Allow passing specific y-axis title
    yaxis_title_override: Optional[str] = None
) -> go.Figure:
    """
    Creates a raw greek chart (e.g., Gamma, Vanna) showing values for calls and puts.
    Uses the scalar `underlying_price_scalar` for price context (e.g., current price line, range calculation).
    `metric_col` is the primary data column to plot.
    """
    chart_func_logger = instance_logger.getChild(f"_create_raw_greek_chart.{metric_col}")
    chart_func_logger.info(f"Creating raw Greek-style chart for metric '{metric_col}' ({chart_title_part}) for {symbol}")

    plotly_template = config.get("plotly_template", "plotly_dark")
    default_chart_height = config.get("chart_specific_params", {}).get(f"{metric_col.lower()}_chart_height", config.get("default_chart_height", 700))
    show_grid = config.get("show_grid", True)
    figure_title_prefix = config.get("figure_title_prefix", "EOTS - ")
    hover_settings = config.get("hover_settings", {})
    column_names_config = config.get("column_names", {})
    legend_config = config.get("legend_settings", {})
    price_line_config = config.get("price_line_config", {})
    timestamp_config = config.get("timestamp_config", {"enabled": True})
    
    # Saving config (though typically main visualizer methods handle saving)
    # output_dir = config.get("output_dir") # Corrected key
    # save_html = config.get("save_charts_as_html", False)
    # save_png = config.get("save_charts_as_png", False)
    # plot_width = config.get("PLOT_WIDTH", 1200) # From old config, check new path

    required_df_cols = [col_strike, metric_col, col_opt_kind]
    df_validated, cols_ok = plot_utils_module._ensure_columns(processed_data, required_df_cols, chart_func_logger)
    if not cols_ok or df_validated.empty:
        chart_func_logger.warning(f"Data for raw Greek chart ('{metric_col}') is empty or missing required columns ({required_df_cols}).")
        return plot_utils_module._create_empty_figure(instance_logger, default_chart_height, plotly_template, f"Missing data for {chart_title_part} chart")

    fig = go.Figure()
    
    # Ensure data types for plotting
    df_validated[col_strike] = pd.to_numeric(df_validated[col_strike], errors='coerce')
    df_validated[metric_col] = pd.to_numeric(df_validated[metric_col], errors='coerce')
    df_validated.dropna(subset=[col_strike, metric_col], inplace=True) # Drop rows where essential plot data is NaN

    calls_data = df_validated[df_validated[col_opt_kind].astype(str).str.lower() == 'call'].sort_values(by=col_strike)
    puts_data = df_validated[df_validated[col_opt_kind].astype(str).str.lower() == 'put'].sort_values(by=col_strike)

    hover_enabled = plot_utils_module._check_hover_enabled(hover_settings, f"{metric_col.lower()}_raw_greek")

    if not calls_data.empty:
        calls_hover_texts = [
            plot_utils_module._create_hover_text(row, f"{metric_col.lower()}_call_point", hover_settings, column_names_config, chart_func_logger,
                                           extra_context={"Symbol": symbol, "Metric": f"Call {chart_title_part}"})
            for _, row in calls_data.iterrows()
        ] if hover_enabled else None
        
        fig.add_trace(go.Scatter(
            x=calls_data[col_strike], y=calls_data[metric_col], mode='lines+markers', name=f'Call {chart_title_part}',
            line=dict(color=str(call_color)), marker=dict(size=6),
            hovertext=calls_hover_texts, hoverinfo="text" if hover_enabled and calls_hover_texts else "skip"
        ))

    if not puts_data.empty:
        puts_hover_texts = [
            plot_utils_module._create_hover_text(row, f"{metric_col.lower()}_put_point", hover_settings, column_names_config, chart_func_logger,
                                          extra_context={"Symbol": symbol, "Metric": f"Put {chart_title_part}"})
            for _, row in puts_data.iterrows()
        ] if hover_enabled else None

        fig.add_trace(go.Scatter(
            x=puts_data[col_strike], y=puts_data[metric_col], mode='lines+markers', name=f'Put {chart_title_part}',
            line=dict(color=str(put_color)), marker=dict(size=6),
            hovertext=puts_hover_texts, hoverinfo="text" if hover_enabled and puts_hover_texts else "skip"
        ))

    title = f"{figure_title_prefix}{symbol} {chart_title_part} Profile"
    if fetch_timestamp:
        try: title += f" (Data: {pd.to_datetime(fetch_timestamp).strftime('%Y-%m-%d %H:%M:%S')})"
        except: title += f" (Data: {fetch_timestamp})"

    fig.update_layout(
        title=dict(text=title, x=0.5, xanchor='center'),
        xaxis_title=str(xaxis_title),
        yaxis_title=str(yaxis_title_override if yaxis_title_override else chart_title_part),
        height=int(default_chart_height), template=plotly_template,
        showlegend=bool(legend_config.get("show_legend", True)),
        legend=legend_config, # Pass the whole legend dict
        hovermode=str(hover_settings.get("mode", "closest")),
        xaxis_showgrid=bool(show_grid), yaxis_showgrid=bool(show_grid),
        margin=dict(l=60, r=40, t=80, b=50) # Example margins
    )

    if pd.notna(underlying_price_scalar) and price_line_config.get("show_current_price_line", True):
        plot_utils_module._add_price_line(
            fig, underlying_price_scalar, # Use the scalar value
            str(price_line_config.get("current_price_line_color", "rgba(255, 255, 0, 0.6)")),
            int(price_line_config.get("current_price_line_width", 1)),
            str(price_line_config.get("current_price_line_dash", "dash")),
            label_text="Current Price", instance_logger=chart_func_logger
        )
    
    # Apply price range override if provided
    default_price_range_for_metric = float(config.get("chart_specific_params", {}).get("raw_greek_charts_price_range_pct", 10.0))
    effective_price_range_pct = selected_price_range_pct_override if selected_price_range_pct_override is not None else default_price_range_for_metric

    if pd.notna(underlying_price_scalar) and pd.notna(effective_price_range_pct) and effective_price_range_pct > 0:
        lower_bound = underlying_price_scalar * (1 - effective_price_range_pct / 100)
        upper_bound = underlying_price_scalar * (1 + effective_price_range_pct / 100)
        fig.update_xaxes(range=[lower_bound, upper_bound])
        chart_func_logger.info(f"Applied X-axis price range ({effective_price_range_pct}%): {lower_bound:.2f} - {upper_bound:.2f}")

    if timestamp_config.get("enabled", True):
        plot_utils_module._add_timestamp_annotation(fig, chart_func_logger, timestamp_config) # Pass config dict

    # Saving is typically handled by the main visualizer orchestrator method, not here.
    # If saving were to be done here:
    # filename_prefix = f"{symbol.lower()}_raw_{metric_col.lower()}"
    # plot_utils_module._save_figure(fig, filename_prefix, output_dir, save_html, save_png, chart_func_logger, plot_width, default_chart_height)
    
    chart_func_logger.info(f"Raw Greek-style chart for '{metric_col}' successfully generated.")
    return fig


def create_net_greek_flow_heatmap(
    instance_logger: logging.Logger,
    config: Dict[str, Any], 
    plot_utils_module: Any, 
    processed_data: pd.DataFrame, # This DataFrame should contain the specific metric column
    metric_column_to_plot: str, # The actual name of the column in processed_data to plot
    chart_main_title_prefix: str, # E.g., "Net Gamma Flow"
    colorscale_config_key: str, # Key in config.colorscales, e.g., "net_gamma_flow_heatmap"
    colorbar_title_text: str, # Text for the colorbar, e.g., "Net Gamma"
    symbol: str,
    fetch_timestamp: Optional[str] = None,
    current_price: Optional[float] = None, # Scalar current underlying price for price line
    col_strike: str = "strike_price", # Default strike column name from config
    opt_kind_col: str = "opt_kind", # Default option kind column name from config
    expiry_col: str = "expiration_date" # Default expiry column name from config
) -> go.Figure:
    """
    Creates a generic heatmap for a specified net Greek flow or exposure metric.
    Pivots data by expiry (x-axis) and strike (y-axis).
    """
    chart_func_logger = instance_logger.getChild(f"NetGreekFlowHeatmap.{metric_column_to_plot}")
    chart_func_logger.info(f"Creating Net Greek Flow Heatmap for metric '{metric_column_to_plot}' for symbol '{symbol}'")

    plotly_template = config.get("plotly_template", "plotly_dark")
    default_chart_height = config.get("default_chart_height", 700)
    colorscales = config.get("colorscales", {})
    selected_colorscale = colorscales.get(colorscale_config_key, "RdBu") # Default if key not found
    figure_title_prefix = config.get("figure_title_prefix", "EOTS - ")
    hover_settings = config.get("hover_settings", {})
    column_names_config = config.get("column_names", {}) # For hover text consistency
    timestamp_config = config.get("timestamp_config", {"enabled": True})
    price_line_config = config.get("price_line_config", {})
    
    # Ensure required columns for pivot are present (strike, expiry, and the metric itself)
    required_cols_for_pivot = [col_strike, expiry_col, metric_column_to_plot]
    # opt_kind_col is also passed in args but not used directly in this heatmap's pivot logic,
    # unless data needs pre-filtering by option type before pivoting for this specific greek.
    # For a "net" greek flow, it's usually already aggregated across calls/puts or applies to both.

    df_validated, cols_ok = plot_utils_module._ensure_columns(processed_data, required_cols_for_pivot, chart_func_logger)
    if not cols_ok or df_validated.empty:
        chart_func_logger.warning(f"Data for Net Greek Flow Heatmap ('{metric_column_to_plot}') is empty or missing required columns: {required_cols_for_pivot}.")
        return plot_utils_module._create_empty_figure(instance_logger, default_chart_height, plotly_template, f"Missing data for {chart_main_title_prefix} Heatmap")

    # Ensure numeric types for pivot values and axes
    df_validated[col_strike] = pd.to_numeric(df_validated[col_strike], errors='coerce')
    df_validated[metric_column_to_plot] = pd.to_numeric(df_validated[metric_column_to_plot], errors='coerce')
    try: # Attempt to convert expiry_col to datetime for proper sorting
        df_validated[expiry_col] = pd.to_datetime(df_validated[expiry_col], errors='coerce')
    except Exception as e_dt_conv:
        chart_func_logger.warning(f"Could not convert '{expiry_col}' to datetime for sorting: {e_dt_conv}. Heatmap x-axis might not be sorted correctly by date.")
    
    df_validated.dropna(subset=[col_strike, expiry_col, metric_column_to_plot], inplace=True)
    if df_validated.empty:
        chart_func_logger.warning(f"DataFrame became empty after NaN drop for essential heatmap columns (Strike, Expiry, '{metric_column_to_plot}').")
        return plot_utils_module._create_empty_figure(instance_logger, default_chart_height, plotly_template, f"No valid data for {chart_main_title_prefix} Heatmap")

    try:
        # Average metric values if multiple records exist for same strike/expiry (e.g. after merging C/P specific flows)
        heatmap_pivot_data = df_validated.pivot_table(
            index=col_strike, columns=expiry_col, values=metric_column_to_plot, aggfunc='mean'
        )
    except Exception as e_pivot:
        chart_func_logger.error(f"Error pivoting data for Net Greek Flow Heatmap ('{metric_column_to_plot}'): {e_pivot}", exc_info=True)
        return plot_utils_module._create_empty_figure(instance_logger, default_chart_height, plotly_template, f"Error pivoting data for {chart_main_title_prefix} Heatmap")

    if heatmap_pivot_data.empty:
        chart_func_logger.warning(f"Pivot table for Net Greek Flow Heatmap ('{metric_column_to_plot}') resulted in empty data.")
        return plot_utils_module._create_empty_figure(instance_logger, default_chart_height, plotly_template, f"No data to display for {chart_main_title_prefix} Heatmap")

    # Sort by strike price (y-axis) and expiry date (x-axis)
    heatmap_pivot_data = heatmap_pivot_data.sort_index(ascending=True) # Sort strikes (y-axis)
    if pd.api.types.is_datetime64_any_dtype(heatmap_pivot_data.columns):
        heatmap_pivot_data = heatmap_pivot_data.reindex(sorted(heatmap_pivot_data.columns), axis=1) # Sort expiries if datetime
        x_axis_labels_for_heatmap = heatmap_pivot_data.columns.strftime('%Y-%m-%d')
    else: # If expiry was not converted to datetime, sort as string
        heatmap_pivot_data = heatmap_pivot_data.reindex(sorted(heatmap_pivot_data.columns, key=str), axis=1)
        x_axis_labels_for_heatmap = heatmap_pivot_data.columns.astype(str)


    hover_texts_matrix = []
    if plot_utils_module._check_hover_enabled(hover_settings, f"net_greek_flow_heatmap_cell_{metric_column_to_plot.lower()}"):
        for strike_val_heatmap in heatmap_pivot_data.index:
            row_texts_list = []
            for expiry_idx_heatmap, expiry_val_heatmap in enumerate(heatmap_pivot_data.columns):
                metric_value_at_cell = heatmap_pivot_data.loc[strike_val_heatmap, expiry_val_heatmap]
                display_expiry_str_heatmap = x_axis_labels_for_heatmap[expiry_idx_heatmap]
                
                # Create a mock Series for _create_hover_text
                mock_hover_row_data = pd.Series({
                    col_strike: strike_val_heatmap,
                    expiry_col: display_expiry_str_heatmap, # Use the formatted date string
                    metric_column_to_plot: metric_value_at_cell,
                    "Date": display_expiry_str_heatmap # Use for 'Date' field in hover context if needed
                })
                # Optionally, lookup original full row from df_validated if more fields are needed
                # original_row_for_hover = df_validated[
                #     (df_validated[col_strike] == strike_val_heatmap) & 
                #     (df_validated[expiry_col].astype(str) == str(expiry_val_heatmap)) # Match on original expiry value
                # ]
                # if not original_row_for_hover.empty: mock_hover_row_data = original_row_for_hover.iloc[0]
                
                hover_text_for_cell = plot_utils_module._create_hover_text(
                    mock_hover_row_data,
                    chart_type_hover_key=f"net_greek_flow_heatmap_cell_{metric_column_to_plot.lower()}",
                    hover_settings_config=hover_settings,
                    column_names_config=column_names_config,
                    instance_logger=chart_func_logger,
                    extra_context={"Symbol": symbol, "Metric": chart_main_title_prefix}
                )
                row_texts_list.append(hover_text_for_cell)
            hover_texts_matrix.append(row_texts_list)

    fig = go.Figure(data=go.Heatmap(
        z=heatmap_pivot_data.values,
        x=x_axis_labels_for_heatmap, # Expiry dates (formatted)
        y=heatmap_pivot_data.index,   # Strike prices
        colorscale=selected_colorscale,
        colorbar=dict(title=str(colorbar_title_text)),
        hovertext=hover_texts_matrix if hover_texts_matrix else None,
        hoverinfo="text" if hover_texts_matrix else "x+y+z",
        xgap=1, ygap=1 # Add gaps between cells
    ))

    full_title_heatmap = f"{figure_title_prefix}{symbol} {chart_main_title_prefix} Heatmap"
    if fetch_timestamp:
        try: full_title_heatmap += f" (Data: {pd.to_datetime(fetch_timestamp).strftime('%Y-%m-%d %H:%M:%S')})"
        except: full_title_heatmap += f" (Data: {fetch_timestamp})"
    
    fig.update_layout(
        title=dict(text=full_title_heatmap, x=0.5, xanchor='center'),
        xaxis_title="Expiration Date", yaxis_title="Strike Price",
        height=int(default_chart_height), template=plotly_template,
        xaxis_type="category", # Treat dates as categories to show all of them
        yaxis_autorange='reversed' if config.get("heatmap_yaxis_reversed", False) else True,
        margin=dict(l=60, r=40, t=80, b=50)
    )

    if pd.notna(current_price) and price_line_config.get("show_current_price_line_heatmap", True):
        plot_utils_module._add_price_line(
            fig, current_price,
            str(price_line_config.get("current_price_line_color", "rgba(255, 255, 0, 0.7)")),
            int(price_line_config.get("current_price_line_width", 2)),
            str(price_line_config.get("current_price_line_dash", "solid")),
            label_text="Current Price", instance_logger=chart_func_logger
        )

    if timestamp_config.get("enabled", True):
        plot_utils_module._add_timestamp_annotation(fig, chart_func_logger, timestamp_config)

    # Saving handled by main visualizer method
    chart_func_logger.info(f"Net Greek Flow Heatmap for '{metric_column_to_plot}' successfully generated.")
    return fig