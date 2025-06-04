# charts/heatmaps.py
"""
Standalone functions for creating various heatmap visualizations
for the MSPIVisualizer. These functions are intended to be called from
the main visualizer class and rely on configuration and pre-processed
data passed as arguments.
Version: Heatmaps-Canon-V1.1.0 - Aligned with PlotUtils V1.0.1 and Orchestrator
"""

import logging
from typing import Dict, Any, Optional, List, Tuple, Union
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# Import the plot_utils module to access its functions
import plot_utils # Alias to plot_utils_module in function args

def create_mspi_heatmap(
    instance_logger: logging.Logger,
    config: Dict[str, Any], # Visualizer-specific config merged with relevant app config
    plot_utils_module: Any, # The imported plot_utils module
    options_df: pd.DataFrame, # DataFrame containing options data including MSPI, strike, opt_kind
    symbol: str,
    fetch_timestamp: Optional[str] = None,
    mspi_col: str = "mspi",        # Actual name of the MSPI column in options_df
    strike_col: str = "strike_price", # Actual name of the strike column
    opt_kind_col: str = "opt_kind",   # Actual name of the option kind column
    current_price: Optional[float] = None # Scalar current underlying price for potential price line
    # expiry_col is not used in this particular heatmap variant which shows Calls vs Puts directly
) -> go.Figure:
    """
    Creates a heatmap of MSPI scores, showing Calls and Puts side-by-side against strikes.
    """
    chart_func_logger = instance_logger.getChild("CreateMSPIHeatmap_V1.1")
    chart_func_logger.info(f"Creating MSPI heatmap (Calls vs Puts) for {symbol}")

    default_chart_height = config.get("default_chart_height", 700)
    plotly_template = config.get("plotly_template", "plotly_dark")
    colorscales = config.get("colorscales", {})
    mspi_colorscale_name = colorscales.get("mspi_heatmap", "RdBu") # Default if not specified
    hover_settings = config.get("hover_settings", {})
    column_names_config = config.get("column_names", {}) # For _create_hover_text
    figure_title_prefix = config.get("figure_title_prefix", "EOTS - ")
    timestamp_config = config.get("timestamp_config", {"enabled": True})
    price_line_config = config.get("price_line_config", {})
    
    # Columns needed for this specific heatmap logic:
    # mspi_col (values), strike_col (y-axis), opt_kind_col (to split data for x-axis categories)
    # Also, any columns needed for hover text via core_indices_keys
    core_indices_keys_for_hover = config.get("hover_settings", {}).get("chart_specific_hover", {}).get("mspi_heatmap", {}).get("core_indices_keys", [])
    
    required_cols = [strike_col, opt_kind_col, mspi_col] + core_indices_keys_for_hover
    df_validated, cols_ok = plot_utils_module._ensure_columns(options_df, list(set(required_cols)), chart_func_logger) # Use set for unique cols
    if not cols_ok or df_validated.empty:
        chart_func_logger.warning(f"Data for MSPI heatmap for {symbol} is missing required columns or empty.")
        return plot_utils_module._create_empty_figure(instance_logger, default_chart_height, plotly_template, f"Missing data for {symbol} MSPI Heatmap")

    # Ensure key columns are numeric for proper sorting and plotting
    df_validated[strike_col] = pd.to_numeric(df_validated[strike_col], errors='coerce')
    df_validated[mspi_col] = pd.to_numeric(df_validated[mspi_col], errors='coerce')
    df_validated.dropna(subset=[strike_col, mspi_col, opt_kind_col], inplace=True)

    if df_validated.empty:
        chart_func_logger.warning(f"No valid data remaining for MSPI heatmap for {symbol} after NaN drop.")
        return plot_utils_module._create_empty_figure(instance_logger, default_chart_height, plotly_template, f"No valid data for {symbol} MSPI Heatmap")

    calls_data_hm = df_validated[df_validated[opt_kind_col].astype(str).str.lower() == 'call']
    puts_data_hm = df_validated[df_validated[opt_kind_col].astype(str).str.lower() == 'put']

    if calls_data_hm.empty and puts_data_hm.empty:
        chart_func_logger.info(f"No specific Call or Put data for MSPI heatmap for {symbol}.")
        return plot_utils_module._create_empty_figure(instance_logger, default_chart_height, plotly_template, f"No Call/Put data for {symbol} MSPI Heatmap")
        
    # Determine common strike range for y-axis consistency, ensure sorted
    all_strikes_for_y_axis = sorted(pd.concat([calls_data_hm[strike_col], puts_data_hm[strike_col]]).unique())
    if not all_strikes_for_y_axis: # Should not happen if calls_data or puts_data is not empty
        return plot_utils_module._create_empty_figure(instance_logger, default_chart_height, plotly_template, "No strikes found for heatmap")

    heatmap_traces_list = []
    x_axis_categories = ["Calls", "Puts"] # Fixed categories for the x-axis of this heatmap type

    # --- Prepare Z-data and Hovertext for Calls ---
    z_calls = []
    hover_calls = []
    if not calls_data_hm.empty:
        calls_pivot = calls_data_hm.groupby(strike_col)[mspi_col].mean().reindex(all_strikes_for_y_axis) # Ensure all strikes are present
        z_calls = calls_pivot.values.tolist() # This will be a 1D list of MSPI scores for call column
        
        if plot_utils_module._check_hover_enabled(hover_settings, "mspi_heatmap_cell_call"):
            for strike_val_hover in all_strikes_for_y_axis:
                if strike_val_hover in calls_pivot.index and pd.notna(calls_pivot.loc[strike_val_hover]):
                    # Find original row(s) for this strike in calls_data_hm for richer hover
                    original_call_row = calls_data_hm[calls_data_hm[strike_col] == strike_val_hover].iloc[0] # Take first if multiple (e.g. expiries)
                    hover_text = plot_utils_module._create_hover_text(
                        original_call_row, "mspi_heatmap_cell_call", hover_settings, column_names_config, chart_func_logger,
                        extra_context={"Symbol": symbol, "Type": "Call", "Strike": f"{strike_val_hover:.2f}"}
                    )
                    hover_calls.append(hover_text)
                else:
                    hover_calls.append("") # Empty hover for NaN/missing cells
    else: # Fill with NaNs if no call data
        z_calls = [np.nan] * len(all_strikes_for_y_axis)
        hover_calls = [""] * len(all_strikes_for_y_axis)

    # --- Prepare Z-data and Hovertext for Puts ---
    z_puts = []
    hover_puts = []
    if not puts_data_hm.empty:
        puts_pivot = puts_data_hm.groupby(strike_col)[mspi_col].mean().reindex(all_strikes_for_y_axis)
        z_puts = puts_pivot.values.tolist()
        
        if plot_utils_module._check_hover_enabled(hover_settings, "mspi_heatmap_cell_put"):
            for strike_val_hover in all_strikes_for_y_axis:
                if strike_val_hover in puts_pivot.index and pd.notna(puts_pivot.loc[strike_val_hover]):
                    original_put_row = puts_data_hm[puts_data_hm[strike_col] == strike_val_hover].iloc[0]
                    hover_text = plot_utils_module._create_hover_text(
                        original_put_row, "mspi_heatmap_cell_put", hover_settings, column_names_config, chart_func_logger,
                        extra_context={"Symbol": symbol, "Type": "Put", "Strike": f"{strike_val_hover:.2f}"}
                    )
                    hover_puts.append(hover_text)
                else:
                    hover_puts.append("")
    else:
        z_puts = [np.nan] * len(all_strikes_for_y_axis)
        hover_puts = [""] * len(all_strikes_for_y_axis)

    # Combine Z and Hovertext into 2D arrays for the heatmap trace
    # Heatmap Z: rows are strikes (y-axis), columns are option types (x-axis)
    final_z_data = np.array([z_calls, z_puts]).T # Transpose to make strikes rows
    final_hover_data = np.array([hover_calls, hover_puts]).T if (hover_calls and hover_puts) else None

    heatmap_traces_list.append(go.Heatmap(
        z=final_z_data,
        x=x_axis_categories, 
        y=all_strikes_for_y_axis,
        colorscale=mspi_colorscale_name,
        colorbar=dict(title="MSPI Score", thickness=15, len=0.9),
        hovertext=final_hover_data,
        hoverinfo="text" if final_hover_data is not None else "x+y+z",
        xgap=2, ygap=2
    ))
    
    fig = go.Figure(data=heatmap_traces_list)
    chart_title = f"{figure_title_prefix}{symbol} MSPI Score Heatmap"
    if fetch_timestamp:
        try: chart_title += f" (Data: {pd.to_datetime(fetch_timestamp).strftime('%Y-%m-%d %H:%M:%S')})"
        except: chart_title += f" (Data: {fetch_timestamp})"

    fig.update_layout(
        title=dict(text=chart_title, x=0.5, xanchor='center'),
        xaxis_title="Option Type", yaxis_title="Strike Price",
        height=int(default_chart_height), template=plotly_template,
        xaxis_type="category", # Ensure "Calls" and "Puts" are treated as distinct categories
        yaxis_autorange='reversed' if config.get("heatmap_yaxis_reversed", False) else True,
        margin=dict(l=60, r=40, t=80, b=50)
    )
    
    if pd.notna(current_price) and price_line_config.get("show_current_price_line_heatmap", True):
        plot_utils_module._add_price_line(
            fig, current_price,
            str(price_line_config.get("current_price_line_color", "rgba(255,255,0,0.7)")),
            int(price_line_config.get("current_price_line_width", 2)),
            str(price_line_config.get("current_price_line_dash", "solid")),
            "Current Price", annotation_position="top left", instance_logger=chart_func_logger
        )

    if timestamp_config.get("enabled", True):
        plot_utils_module._add_timestamp_annotation(fig, chart_func_logger, timestamp_config)
    
    chart_func_logger.info(f"MSPI Heatmap for {symbol} (Calls vs Puts) generated successfully.")
    return fig


def create_net_value_heatmap(
    instance_logger: logging.Logger,
    config: Dict[str, Any],
    plot_utils_module: Any,
    options_df: pd.DataFrame, # Renamed from processed_data for clarity
    symbol: str,
    fetch_timestamp: Optional[str] = None,
    net_value_col: str = "net_value_pressure",
    strike_col: str = "strike_price",
    expiry_col: str = "expiration_date",
    opt_kind_col: str = "opt_kind", # For potential filtering or more detailed hover if needed
    current_price: Optional[float] = None
) -> go.Figure:
    """
    Creates a heatmap of Net Value Pressure by strike and expiry.
    The `options_df` is expected to have data aggregated to strike/expiry level if `opt_kind_col` is not used for pivoting.
    If `opt_kind_col` is relevant (e.g., showing net value for calls vs puts per expiry), the pivot needs adjustment.
    Current implementation assumes `net_value_col` is already net across option kinds if not pivoting by it.
    """
    chart_func_logger = instance_logger.getChild("CreateNetValueHeatmap_V1.1")
    chart_func_logger.info(f"Creating Net Value Pressure heatmap for {symbol}")

    default_chart_height = config.get("default_chart_height", 700)
    plotly_template = config.get("plotly_template", "plotly_dark")
    colorscales = config.get("colorscales", {})
    net_value_colorscale_name = colorscales.get("net_value_heatmap", "RdYlGn")
    hover_settings = config.get("hover_settings", {})
    column_names_config = config.get("column_names", {})
    figure_title_prefix = config.get("figure_title_prefix", "EOTS - ")
    timestamp_config = config.get("timestamp_config", {"enabled": True})
    price_line_config = config.get("price_line_config", {})

    required_cols_hm = [strike_col, expiry_col, net_value_col]
    df_validated, cols_ok = plot_utils_module._ensure_columns(options_df, required_cols_hm, chart_func_logger)
    if not cols_ok or df_validated.empty:
        chart_func_logger.warning(f"Data for Net Value heatmap for {symbol} missing required columns or empty.")
        return plot_utils_module._create_empty_figure(instance_logger, default_chart_height, plotly_template, f"Missing data for {symbol} Net Value Heatmap")

    df_validated[strike_col] = pd.to_numeric(df_validated[strike_col], errors='coerce')
    df_validated[net_value_col] = pd.to_numeric(df_validated[net_value_col], errors='coerce')
    try: df_validated[expiry_col] = pd.to_datetime(df_validated[expiry_col], errors='coerce')
    except Exception: chart_func_logger.warning(f"Could not parse '{expiry_col}' to datetime for Net Value heatmap.")
    
    df_validated.dropna(subset=[strike_col, expiry_col, net_value_col], inplace=True)
    if df_validated.empty:
        return plot_utils_module._create_empty_figure(instance_logger, default_chart_height, plotly_template, f"No valid data for {symbol} Net Value Heatmap")

    try:
        heatmap_pivot = df_validated.pivot_table(index=strike_col, columns=expiry_col, values=net_value_col, aggfunc='mean')
    except Exception as e_pivot_nv:
        chart_func_logger.error(f"Error pivoting data for Net Value heatmap: {e_pivot_nv}", exc_info=True)
        return plot_utils_module._create_empty_figure(instance_logger, default_chart_height, plotly_template, f"Pivot error for {symbol} Net Value Heatmap")

    if heatmap_pivot.empty:
        return plot_utils_module._create_empty_figure(instance_logger, default_chart_height, plotly_template, f"No pivot data for {symbol} Net Value Heatmap")

    heatmap_pivot = heatmap_pivot.sort_index(ascending=True) # Sort strikes
    if pd.api.types.is_datetime64_any_dtype(heatmap_pivot.columns):
        heatmap_pivot = heatmap_pivot.reindex(sorted(heatmap_pivot.columns), axis=1)
        x_labels_hm = heatmap_pivot.columns.strftime('%Y-%m-%d')
    else:
        heatmap_pivot = heatmap_pivot.reindex(sorted(heatmap_pivot.columns, key=str), axis=1)
        x_labels_hm = heatmap_pivot.columns.astype(str)

    hover_texts_hm_matrix = []
    if plot_utils_module._check_hover_enabled(hover_settings, "net_value_heatmap_cell"):
        for strike_val_hm_nv in heatmap_pivot.index:
            row_hover_texts = []
            for expiry_idx_hm_nv, expiry_val_hm_nv in enumerate(heatmap_pivot.columns):
                metric_val_hm_nv = heatmap_pivot.loc[strike_val_hm_nv, expiry_val_hm_nv]
                mock_row_hm_nv = pd.Series({strike_col: strike_val_hm_nv, expiry_col: x_labels_hm[expiry_idx_hm_nv], net_value_col: metric_val_hm_nv, "Date": x_labels_hm[expiry_idx_hm_nv]})
                hover_text = plot_utils_module._create_hover_text(mock_row_hm_nv, "net_value_heatmap_cell", hover_settings, column_names_config, chart_func_logger,
                                                            extra_context={"Symbol": symbol, "Metric": "Net Value Pressure"})
                row_hover_texts.append(hover_text)
            hover_texts_hm_matrix.append(row_hover_texts)

    fig = go.Figure(data=go.Heatmap(
        z=heatmap_pivot.values, x=x_labels_hm, y=heatmap_pivot.index,
        colorscale=net_value_colorscale_name, colorbar=dict(title="Net Value Pressure", thickness=15, len=0.9),
        hovertext=hover_texts_hm_matrix if hover_texts_hm_matrix else None, 
        hoverinfo="text" if hover_texts_hm_matrix else "x+y+z",
        xgap=1, ygap=1
    ))

    chart_title_hm_nv = f"{figure_title_prefix}{symbol} Net Value Pressure Heatmap"
    if fetch_timestamp:
        try: chart_title_hm_nv += f" (Data: {pd.to_datetime(fetch_timestamp).strftime('%Y-%m-%d %H:%M:%S')})"
        except: chart_title_hm_nv += f" (Data: {fetch_timestamp})"

    fig.update_layout(
        title=dict(text=chart_title_hm_nv, x=0.5, xanchor='center'),
        xaxis_title="Expiration Date", yaxis_title="Strike Price",
        height=int(default_chart_height), template=plotly_template,
        xaxis_type="category", yaxis_autorange='reversed' if config.get("heatmap_yaxis_reversed", False) else True,
        margin=dict(l=60, r=40, t=80, b=50)
    )
    if pd.notna(current_price) and price_line_config.get("show_current_price_line_heatmap", True):
        plot_utils_module._add_price_line(fig, current_price, str(price_line_config.get("current_price_line_color", "rgba(255,255,0,0.7)")),
                                          int(price_line_config.get("current_price_line_width", 2)), str(price_line_config.get("current_price_line_dash", "solid")),
                                          "Current Price", instance_logger=chart_func_logger)
    if timestamp_config.get("enabled", True):
        plot_utils_module._add_timestamp_annotation(fig, chart_func_logger, timestamp_config)
    
    chart_func_logger.info(f"Net Value Pressure Heatmap for {symbol} generated successfully.")
    return fig

def create_net_volume_pressure_heatmap(
    instance_logger: logging.Logger,
    config: Dict[str, Any],
    plot_utils_module: Any,
    options_df: pd.DataFrame,
    symbol: str,
    fetch_timestamp: Optional[str] = None,
    net_volume_col: str = "net_volume_pressure",
    strike_col: str = "strike_price",
    expiry_col: str = "expiration_date",
    opt_kind_col: str = "opt_kind",
    current_price: Optional[float] = None
) -> go.Figure:
    """
    Creates a heatmap of Net Volume Pressure by strike and expiry.
    """
    chart_func_logger = instance_logger.getChild("CreateNetVolumeHeatmap_V1.1")
    chart_func_logger.info(f"Creating Net Volume Pressure heatmap for {symbol}")

    # Similar configuration extraction as create_net_value_heatmap
    default_chart_height = config.get("default_chart_height", 700)
    plotly_template = config.get("plotly_template", "plotly_dark")
    colorscales = config.get("colorscales", {})
    net_vol_colorscale_name = colorscales.get("net_volume_pressure_heatmap", "coolwarm") # Different default
    hover_settings = config.get("hover_settings", {})
    column_names_config = config.get("column_names", {})
    figure_title_prefix = config.get("figure_title_prefix", "EOTS - ")
    timestamp_config = config.get("timestamp_config", {"enabled": True})
    price_line_config = config.get("price_line_config", {})

    required_cols_hm_vol = [strike_col, expiry_col, net_volume_col]
    df_validated, cols_ok = plot_utils_module._ensure_columns(options_df, required_cols_hm_vol, chart_func_logger)
    if not cols_ok or df_validated.empty:
        return plot_utils_module._create_empty_figure(instance_logger, default_chart_height, plotly_template, f"Missing data for {symbol} Net Volume Heatmap")

    df_validated[strike_col] = pd.to_numeric(df_validated[strike_col], errors='coerce')
    df_validated[net_volume_col] = pd.to_numeric(df_validated[net_volume_col], errors='coerce')
    try: df_validated[expiry_col] = pd.to_datetime(df_validated[expiry_col], errors='coerce')
    except Exception: chart_func_logger.warning(f"Could not parse '{expiry_col}' to datetime for Net Volume heatmap.")
    
    df_validated.dropna(subset=[strike_col, expiry_col, net_volume_col], inplace=True)
    if df_validated.empty:
        return plot_utils_module._create_empty_figure(instance_logger, default_chart_height, plotly_template, f"No valid data for {symbol} Net Volume Heatmap")

    try:
        heatmap_pivot_vol = df_validated.pivot_table(index=strike_col, columns=expiry_col, values=net_volume_col, aggfunc='mean')
    except Exception as e_pivot_vol:
        chart_func_logger.error(f"Error pivoting data for Net Volume heatmap: {e_pivot_vol}", exc_info=True)
        return plot_utils_module._create_empty_figure(instance_logger, default_chart_height, plotly_template, f"Pivot error for {symbol} Net Volume Heatmap")

    if heatmap_pivot_vol.empty:
        return plot_utils_module._create_empty_figure(instance_logger, default_chart_height, plotly_template, f"No pivot data for {symbol} Net Volume Heatmap")

    heatmap_pivot_vol = heatmap_pivot_vol.sort_index(ascending=True)
    if pd.api.types.is_datetime64_any_dtype(heatmap_pivot_vol.columns):
        heatmap_pivot_vol = heatmap_pivot_vol.reindex(sorted(heatmap_pivot_vol.columns), axis=1)
        x_labels_hm_vol = heatmap_pivot_vol.columns.strftime('%Y-%m-%d')
    else:
        heatmap_pivot_vol = heatmap_pivot_vol.reindex(sorted(heatmap_pivot_vol.columns, key=str), axis=1)
        x_labels_hm_vol = heatmap_pivot_vol.columns.astype(str)

    hover_texts_hm_vol_matrix = []
    if plot_utils_module._check_hover_enabled(hover_settings, "net_volume_heatmap_cell"):
        for strike_val_hm_vol in heatmap_pivot_vol.index:
            row_hover_texts_vol = []
            for expiry_idx_hm_vol, expiry_val_hm_vol in enumerate(heatmap_pivot_vol.columns):
                metric_val_hm_vol = heatmap_pivot_vol.loc[strike_val_hm_vol, expiry_val_hm_vol]
                mock_row_hm_vol = pd.Series({strike_col: strike_val_hm_vol, expiry_col: x_labels_hm_vol[expiry_idx_hm_vol], net_volume_col: metric_val_hm_vol, "Date": x_labels_hm_vol[expiry_idx_hm_vol]})
                hover_text_vol = plot_utils_module._create_hover_text(mock_row_hm_vol, "net_volume_heatmap_cell", hover_settings, column_names_config, chart_func_logger,
                                                                  extra_context={"Symbol": symbol, "Metric": "Net Volume Pressure"})
                row_hover_texts_vol.append(hover_text_vol)
            hover_texts_hm_vol_matrix.append(row_hover_texts_vol)

    fig = go.Figure(data=go.Heatmap(
        z=heatmap_pivot_vol.values, x=x_labels_hm_vol, y=heatmap_pivot_vol.index,
        colorscale=net_vol_colorscale_name, colorbar=dict(title="Net Volume Pressure", thickness=15, len=0.9),
        hovertext=hover_texts_hm_vol_matrix if hover_texts_hm_vol_matrix else None, 
        hoverinfo="text" if hover_texts_hm_vol_matrix else "x+y+z",
        xgap=1, ygap=1
    ))

    chart_title_hm_vol = f"{figure_title_prefix}{symbol} Net Volume Pressure Heatmap"
    if fetch_timestamp:
        try: chart_title_hm_vol += f" (Data: {pd.to_datetime(fetch_timestamp).strftime('%Y-%m-%d %H:%M:%S')})"
        except: chart_title_hm_vol += f" (Data: {fetch_timestamp})"

    fig.update_layout(
        title=dict(text=chart_title_hm_vol, x=0.5, xanchor='center'),
        xaxis_title="Expiration Date", yaxis_title="Strike Price",
        height=int(default_chart_height), template=plotly_template,
        xaxis_type="category", yaxis_autorange='reversed' if config.get("heatmap_yaxis_reversed", False) else True,
        margin=dict(l=60, r=40, t=80, b=50)
    )
    if pd.notna(current_price) and price_line_config.get("show_current_price_line_heatmap", True):
        plot_utils_module._add_price_line(fig, current_price, str(price_line_config.get("current_price_line_color", "rgba(255,255,0,0.7)")),
                                          int(price_line_config.get("current_price_line_width", 2)), str(price_line_config.get("current_price_line_dash", "solid")),
                                          "Current Price", instance_logger=chart_func_logger)
    if timestamp_config.get("enabled", True):
        plot_utils_module._add_timestamp_annotation(fig, chart_func_logger, timestamp_config)
        
    chart_func_logger.info(f"Net Volume Pressure Heatmap for {symbol} generated successfully.")
    return fig

