# charts/heatmaps.py
"""
Standalone functions for creating various heatmap visualizations
for the MSPIVisualizer. These functions are intended to be called from
the main visualizer class and rely on configuration and pre-processed
data passed as arguments.
Version: Heatmaps-Canon-V1.2.1 - Ultra-Verbose Logging for Debugging
"""

import logging
from typing import Dict, Any, Optional, List
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# Import the plot_utils module to access its functions
# The main visualizer will pass the imported module object.
# import plot_utils # No direct import needed here if passed as arg

def _log_df_details(logger_instance: logging.Logger, df: pd.DataFrame, df_name: str, expected_cols: List[str]):
    """Helper function to log detailed DataFrame info."""
    logger_instance.info(f"  DataFrame Details for '{df_name}':")
    if not isinstance(df, pd.DataFrame):
        logger_instance.warning(f"    '{df_name}' is not a DataFrame. Type: {type(df)}")
        return
    if df.empty:
        logger_instance.warning(f"    '{df_name}' is an EMPTY DataFrame.")
        return

    logger_instance.info(f"    Shape: {df.shape}")
    logger_instance.info(f"    Columns: {df.columns.tolist()}")
    logger_instance.debug(f"    Head (first 3 rows, if available):\n{df.head(3).to_string()}")

    for col_check in list(set(expected_cols + df.columns.tolist()[:5])): # Check expected + first few actual
        if col_check in df.columns:
            non_na_count = df[col_check].notna().sum()
            dtype_col = df[col_check].dtype
            sample_vals = df[col_check].head(3).tolist() if non_na_count > 0 else "All NaN or Empty"
            unique_vals_sample = df[col_check].dropna().unique()[:3]
            logger_instance.debug(f"      Col Check: '{col_check}' - Exists. Dtype: {dtype_col}. Non-NaN: {non_na_count}/{len(df)}. Sample: {sample_vals}. Unique (sample): {unique_vals_sample}")
        else:
            logger_instance.warning(f"      Col Check: Column '{col_check}' - MISSING in '{df_name}'.")


def create_mspi_heatmap_plotly(
    instance_logger: logging.Logger,
    config: Dict[str, Any],
    plot_utils_module: Any,
    options_df: pd.DataFrame,
    symbol: str,
    mspi_col: str,
    strike_col: str,
    opt_kind_col: str,
    current_price: Optional[float],
    fetch_timestamp: Optional[str] = None
) -> go.Figure:
    chart_func_logger = instance_logger.getChild("charts.heatmaps.CreateMSPIHeatmapPlotly_V1_2_1_VERBOSE")
    chart_func_logger.info(f"--- CHART GENERATION START: MSPI Heatmap (Call/Put) for {symbol} ---")
    _log_df_details(chart_func_logger, options_df, "Input options_df", [strike_col, opt_kind_col, mspi_col])
    chart_func_logger.debug(f"  Using mspi_col='{mspi_col}', strike_col='{strike_col}', opt_kind_col='{opt_kind_col}'")

    default_chart_height = int(config.get("default_chart_height", 700))
    plotly_template = str(config.get("plotly_template", "plotly_dark"))
    colorscales = config.get("colorscales", {})
    mspi_colorscale_name = str(colorscales.get("mspi_heatmap", "RdBu"))
    hover_settings = config.get("hover_settings", {})
    column_names_config = config.get("column_names", {})
    figure_title_prefix = str(config.get("figure_title_prefix", "EOTS - "))
    timestamp_config = config.get("timestamp_config", {"enabled": True})
    price_line_config = config.get("price_line_config", {})
    chart_func_logger.debug(f"  Chart config: height={default_chart_height}, template='{plotly_template}', colorscale='{mspi_colorscale_name}'")

    core_indices_keys_for_hover = hover_settings.get("chart_specific_hover", {}).get("mspi_heatmap", {}).get("core_indices_keys", [])
    required_cols = [strike_col, opt_kind_col, mspi_col] + core_indices_keys_for_hover
    df_validated, cols_ok = plot_utils_module._ensure_columns(options_df, list(set(required_cols)), chart_func_logger)

    if not cols_ok or df_validated.empty:
        missing_cols_str = str([col for col in required_cols if col not in options_df.columns]) if isinstance(options_df, pd.DataFrame) else "N/A"
        chart_func_logger.error(f"  MSPI Heatmap: Data for {symbol} empty/missing critical columns. Missing: {missing_cols_str}. Required for plot: {[strike_col, opt_kind_col, mspi_col]}")
        return plot_utils_module._create_empty_figure(instance_logger, default_chart_height, plotly_template, f"MSPI Heatmap: Missing/Invalid Data ({symbol})")

    chart_func_logger.debug(f"  DataFrame validated (cols_ok={cols_ok}). Initial Shape: {df_validated.shape}. Ensuring numeric types...")
    try:
        df_validated[strike_col] = pd.to_numeric(df_validated[strike_col], errors='coerce')
        df_validated[mspi_col] = pd.to_numeric(df_validated[mspi_col], errors='coerce')
        # opt_kind_col is usually string, ensure_columns might handle it, or we handle explicitly if needed below
        df_validated.dropna(subset=[strike_col, mspi_col, opt_kind_col], inplace=True)
        chart_func_logger.debug(f"  Numeric conversion and NaN drop (on key cols) complete. Shape after drop: {df_validated.shape}")
    except Exception as e_conv:
        chart_func_logger.error(f"  Error during numeric conversion/dropna for MSPI heatmap: {e_conv}", exc_info=True)
        return plot_utils_module._create_empty_figure(instance_logger, default_chart_height, plotly_template, f"MSPI Heatmap: Data Type Error ({symbol})")

    if df_validated.empty:
        chart_func_logger.warning(f"  MSPI Heatmap: No valid data for {symbol} after NaN drop on essential columns. Initial required cols for plot: {[strike_col, opt_kind_col, mspi_col]}")
        return plot_utils_module._create_empty_figure(instance_logger, default_chart_height, plotly_template, f"MSPI Heatmap: No Valid Data Points After Cleaning ({symbol})")

    calls_data_hm = df_validated[df_validated[opt_kind_col].astype(str).str.lower() == 'call'].copy()
    puts_data_hm = df_validated[df_validated[opt_kind_col].astype(str).str.lower() == 'put'].copy()
    chart_func_logger.info(f"  Filtered Data: Calls DF shape: {calls_data_hm.shape}, Puts DF shape: {puts_data_hm.shape}")
    if not calls_data_hm.empty: chart_func_logger.debug(f"    Calls MSPI non-NaN: {calls_data_hm[mspi_col].notna().sum()}, Strikes non-NaN: {calls_data_hm[strike_col].notna().sum()}")
    if not puts_data_hm.empty: chart_func_logger.debug(f"    Puts MSPI non-NaN: {puts_data_hm[mspi_col].notna().sum()}, Strikes non-NaN: {puts_data_hm[strike_col].notna().sum()}")


    if calls_data_hm.empty and puts_data_hm.empty:
        chart_func_logger.info(f"  MSPI Heatmap: No Call or Put data found for {symbol} after filtering by '{opt_kind_col}'.")
        return plot_utils_module._create_empty_figure(instance_logger, default_chart_height, plotly_template, f"MSPI Heatmap: No Call/Put Data Filtered ({symbol})")

    all_strikes_for_y_axis = []
    if not calls_data_hm.empty: all_strikes_for_y_axis.extend(calls_data_hm[strike_col].dropna().unique())
    if not puts_data_hm.empty: all_strikes_for_y_axis.extend(puts_data_hm[strike_col].dropna().unique())
    if not all_strikes_for_y_axis:
        chart_func_logger.error(f"  MSPI Heatmap: No unique, non-NaN strikes found for Y-axis for {symbol}.")
        return plot_utils_module._create_empty_figure(instance_logger, default_chart_height, plotly_template, f"MSPI Heatmap: No Valid Strikes ({symbol})")
    all_strikes_for_y_axis = sorted(list(set(all_strikes_for_y_axis)))
    chart_func_logger.debug(f"  Y-axis strikes determined (count {len(all_strikes_for_y_axis)}). Sample: {all_strikes_for_y_axis[:5]}...")

    x_axis_categories = ["Calls", "Puts"]
    final_z_data = np.full((len(all_strikes_for_y_axis), len(x_axis_categories)), np.nan)
    final_hover_data_list: List[List[Optional[str]]] = [[None] * len(x_axis_categories) for _ in range(len(all_strikes_for_y_axis))]

    if not calls_data_hm.empty:
        calls_pivot = calls_data_hm.groupby(strike_col)[mspi_col].mean().reindex(all_strikes_for_y_axis)
        final_z_data[:, 0] = calls_pivot.values
        chart_func_logger.debug(f"  Z-data for Calls (sample): {final_z_data[:5, 0]}. Non-NaN count: {np.count_nonzero(~np.isnan(final_z_data[:, 0]))}")
        if plot_utils_module._check_hover_enabled(hover_settings, "mspi_heatmap_cell_call"):
            for i, strike_val in enumerate(all_strikes_for_y_axis):
                if pd.notna(final_z_data[i, 0]):
                    original_call_rows = calls_data_hm[calls_data_hm[strike_col] == strike_val]
                    if not original_call_rows.empty:
                        final_hover_data_list[i][0] = plot_utils_module._create_hover_text(
                            original_call_rows.iloc[0], "mspi_heatmap_cell_call", hover_settings, column_names_config, chart_func_logger,
                            extra_context={"Symbol": symbol, "Type": "Call", "Strike": f"{strike_val:.2f}", mspi_col: f"{final_z_data[i, 0]:.3f}"})
    else:
        chart_func_logger.info("  No call data to populate heatmap.")

    if not puts_data_hm.empty:
        puts_pivot = puts_data_hm.groupby(strike_col)[mspi_col].mean().reindex(all_strikes_for_y_axis)
        final_z_data[:, 1] = puts_pivot.values
        chart_func_logger.debug(f"  Z-data for Puts (sample): {final_z_data[:5, 1]}. Non-NaN count: {np.count_nonzero(~np.isnan(final_z_data[:, 1]))}")
        if plot_utils_module._check_hover_enabled(hover_settings, "mspi_heatmap_cell_put"):
            for i, strike_val in enumerate(all_strikes_for_y_axis):
                if pd.notna(final_z_data[i, 1]):
                    original_put_rows = puts_data_hm[puts_data_hm[strike_col] == strike_val]
                    if not original_put_rows.empty:
                        final_hover_data_list[i][1] = plot_utils_module._create_hover_text(
                            original_put_rows.iloc[0], "mspi_heatmap_cell_put", hover_settings, column_names_config, chart_func_logger,
                            extra_context={"Symbol": symbol, "Type": "Put", "Strike": f"{strike_val:.2f}", mspi_col: f"{final_z_data[i, 1]:.3f}"})
    else:
        chart_func_logger.info("  No put data to populate heatmap.")

    final_hover_data_np = np.array(final_hover_data_list, dtype=object) if any(any(cell is not None for cell in row) for row in final_hover_data_list) else None
    if final_hover_data_np is not None: chart_func_logger.debug(f"  Final hover_data_np created. Shape: {final_hover_data_np.shape}")

    if np.isnan(final_z_data).all():
        chart_func_logger.warning(f"  MSPI Heatmap: Final Z-data for {symbol} is all NaN. Heatmap will be blank.")
        # Return empty figure earlier if no data will be plotted
        return plot_utils_module._create_empty_figure(instance_logger, default_chart_height, plotly_template, f"MSPI Heatmap: All Z Data NaN ({symbol})")

    fig = go.Figure(data=[go.Heatmap(
        z=final_z_data, x=x_axis_categories, y=all_strikes_for_y_axis,
        colorscale=mspi_colorscale_name, colorbar=dict(title="MSPI Score", thickness=15, len=0.9),
        hovertext=final_hover_data_np, hoverinfo="text" if final_hover_data_np is not None else "z", # Fallback to z if no hover
        xgap=2, ygap=2,
        zmin=float(config.get("heatmap_zmin", -1.0)), zmax=float(config.get("heatmap_zmax", 1.0))
    )])
    chart_func_logger.debug(f"  MSPI Heatmap trace added. Z-data shape for plot: {final_z_data.shape if final_z_data is not None else 'N/A'}")

    chart_title = f"{figure_title_prefix}{symbol} MSPI Score Heatmap (Calls vs Puts)"
    # ... (rest of layout, annotations, price line, timestamp) ... (same as before)
    if fetch_timestamp:
        try: chart_title += f" (Data: {pd.to_datetime(fetch_timestamp).strftime('%Y-%m-%d %H:%M:%S')})"
        except: chart_title += f" (Data: {fetch_timestamp})"

    fig.update_layout(
        title=dict(text=chart_title, x=0.5, xanchor='center'),
        xaxis_title="Option Type", yaxis_title="Strike Price",
        height=default_chart_height, template=plotly_template,
        xaxis_type="category",
        yaxis_autorange='reversed' if bool(config.get("heatmap_yaxis_reversed", False)) else True,
        margin=dict(l=70, r=50, t=90, b=60)
    )
    chart_func_logger.debug("  Layout updated.")

    if pd.notna(current_price) and price_line_config.get("show_current_price_line_heatmap", True):
        plot_utils_module._add_price_line(
            fig, current_price,
            str(price_line_config.get("current_price_line_color", "rgba(255,255,0,0.7)")),
            int(price_line_config.get("current_price_line_width", 2)),
            str(price_line_config.get("current_price_line_dash", "solid")),
            "Current Price", annotation_position="top left", instance_logger=chart_func_logger
        )
        chart_func_logger.debug(f"  Current price line added at {current_price}.")

    if timestamp_config.get("enabled", True):
        plot_utils_module._add_timestamp_annotation(fig, chart_func_logger, timestamp_config)
        chart_func_logger.debug("  Timestamp annotation added.")

    chart_func_logger.info(f"--- CHART GENERATION END: MSPI Heatmap for {symbol}. Figure has {len(fig.data)} traces. ---")
    return fig


# --- create_net_value_heatmap_plotly (and _volume) ---
# Apply similar extensive logging.

def create_generic_expiry_strike_heatmap(
    instance_logger: logging.Logger,
    config: Dict[str, Any],
    plot_utils_module: Any,
    options_df: pd.DataFrame,
    symbol: str,
    metric_col: str, # The specific column to plot (e.g., net_value_col, net_volume_col)
    chart_title_main_label: str, # E.g., "Net Value Pressure", "Net Volume Pressure"
    colorscale_config_key: str, # Key for config.colorscales
    colorbar_label: str, # Label for the colorbar
    strike_col: str,
    expiry_col: str,
    current_price: Optional[float],
    fetch_timestamp: Optional[str] = None
) -> go.Figure:
    chart_func_logger = instance_logger.getChild(f"charts.heatmaps.CreateGenericExpiryStrikeHeatmap_V1_2_1.{metric_col}")
    chart_func_logger.info(f"--- CHART GENERATION START: Generic Expiry/Strike Heatmap for '{metric_col}' ({chart_title_main_label}) for {symbol} ---")
    _log_df_details(chart_func_logger, options_df, f"Input options_df for {metric_col}", [strike_col, expiry_col, metric_col])
    chart_func_logger.debug(f"  Using metric_col='{metric_col}', strike_col='{strike_col}', expiry_col='{expiry_col}'")

    default_chart_height = int(config.get("default_chart_height", 700))
    plotly_template = str(config.get("plotly_template", "plotly_dark"))
    colorscales = config.get("colorscales", {})
    selected_colorscale_name = str(colorscales.get(colorscale_config_key, "RdBu")) # Default RdBu if specific key not found
    hover_settings = config.get("hover_settings", {})
    column_names_config = config.get("column_names", {})
    figure_title_prefix = str(config.get("figure_title_prefix", "EOTS - "))
    timestamp_config = config.get("timestamp_config", {"enabled": True})
    price_line_config = config.get("price_line_config", {})
    chart_func_logger.debug(f"  Chart config: height={default_chart_height}, template='{plotly_template}', colorscale='{selected_colorscale_name}'")

    required_cols = [strike_col, expiry_col, metric_col]
    df_validated, cols_ok = plot_utils_module._ensure_columns(options_df, required_cols, chart_func_logger)
    if not cols_ok or df_validated.empty:
        missing_cols_str = str([col for col in required_cols if col not in options_df.columns]) if isinstance(options_df, pd.DataFrame) else "N/A"
        chart_func_logger.error(f"  Generic Heatmap ('{metric_col}'): Data for {symbol} empty/missing. Missing: {missing_cols_str}. Required: {required_cols}")
        return plot_utils_module._create_empty_figure(instance_logger, default_chart_height, plotly_template, f"{chart_title_main_label} Heatmap: Missing/Invalid Data ({symbol})")

    chart_func_logger.debug(f"  DataFrame validated for '{metric_col}'. Shape: {df_validated.shape}. Ensuring numeric/datetime types...")
    try:
        df_validated[strike_col] = pd.to_numeric(df_validated[strike_col], errors='coerce')
        df_validated[metric_col] = pd.to_numeric(df_validated[metric_col], errors='coerce')
        if not pd.api.types.is_datetime64_any_dtype(df_validated[expiry_col]):
            chart_func_logger.debug(f"  Converting '{expiry_col}' to datetime for '{metric_col}' Heatmap.")
            df_validated[expiry_col] = pd.to_datetime(df_validated[expiry_col], errors='coerce')
        df_validated.dropna(subset=[strike_col, expiry_col, metric_col], inplace=True)
        chart_func_logger.debug(f"  Numeric/datetime conversion and NaN drop for '{metric_col}'. Shape: {df_validated.shape}")
    except Exception as e_conv_gen:
        chart_func_logger.error(f"  Error during data conversion/dropna for '{metric_col}' Heatmap: {e_conv_gen}", exc_info=True)
        return plot_utils_module._create_empty_figure(instance_logger, default_chart_height, plotly_template, f"{chart_title_main_label} Heatmap: Data Type Error ({symbol})")

    if df_validated.empty:
        chart_func_logger.warning(f"  Generic Heatmap ('{metric_col}'): No valid data for {symbol} after NaN drop.")
        return plot_utils_module._create_empty_figure(instance_logger, default_chart_height, plotly_template, f"{chart_title_main_label} Heatmap: No Valid Data Points ({symbol})")

    try:
        heatmap_pivot = df_validated.pivot_table(index=strike_col, columns=expiry_col, values=metric_col, aggfunc='mean')
        chart_func_logger.debug(f"  Pivot table created for '{metric_col}'. Shape: {heatmap_pivot.shape}")
        if not heatmap_pivot.empty:
            chart_func_logger.debug(f"    Pivot table head:\n{heatmap_pivot.head(3).to_string()}")
    except Exception as e_pivot_gen:
        chart_func_logger.error(f"  Error pivoting data for '{metric_col}' Heatmap: {e_pivot_gen}", exc_info=True)
        return plot_utils_module._create_empty_figure(instance_logger, default_chart_height, plotly_template, f"{chart_title_main_label} Heatmap: Pivot Error ({symbol})")

    if heatmap_pivot.empty:
        chart_func_logger.warning(f"  Generic Heatmap ('{metric_col}'): Pivot table for {symbol} is empty.")
        return plot_utils_module._create_empty_figure(instance_logger, default_chart_height, plotly_template, f"{chart_title_main_label} Heatmap: No Pivot Data ({symbol})")

    heatmap_pivot = heatmap_pivot.sort_index(ascending=True)
    if pd.api.types.is_datetime64_any_dtype(heatmap_pivot.columns):
        heatmap_pivot = heatmap_pivot.reindex(sorted(heatmap_pivot.columns), axis=1)
        x_labels = heatmap_pivot.columns.strftime('%Y-%m-%d')
    else:
        heatmap_pivot = heatmap_pivot.reindex(sorted(heatmap_pivot.columns, key=str), axis=1)
        x_labels = heatmap_pivot.columns.astype(str)
    chart_func_logger.debug(f"  Heatmap axes sorted for '{metric_col}'. X-labels (sample): {x_labels[:3].tolist() if hasattr(x_labels, 'tolist') else str(x_labels[:3])}")

    hover_texts_matrix = []
    hover_key_suffix = metric_col.lower().replace("_pressure", "").replace("net_", "") # e.g., "value", "volume"
    if plot_utils_module._check_hover_enabled(hover_settings, f"generic_heatmap_cell_{hover_key_suffix}"):
        for strike_val in heatmap_pivot.index:
            row_texts = []
            for expiry_idx, expiry_dt_or_str in enumerate(heatmap_pivot.columns):
                metric_value = heatmap_pivot.loc[strike_val, expiry_dt_or_str]
                mock_row = pd.Series({strike_col: strike_val, expiry_col: x_labels[expiry_idx], metric_col: metric_value, "Date": x_labels[expiry_idx]})
                hover_text = plot_utils_module._create_hover_text(
                    mock_row, f"generic_heatmap_cell_{hover_key_suffix}", hover_settings, column_names_config, chart_func_logger,
                    extra_context={"Symbol": symbol, "Metric": chart_title_main_label}
                )
                row_texts.append(hover_text)
            hover_texts_matrix.append(row_texts)
    chart_func_logger.debug(f"  Hover texts generated for '{metric_col}'. Matrix dim: {len(hover_texts_matrix)}x{len(hover_texts_matrix[0]) if hover_texts_matrix else 0}")

    if np.isnan(heatmap_pivot.values).all():
        chart_func_logger.warning(f"  Generic Heatmap ('{metric_col}'): Final Z-data for {symbol} is all NaN. Heatmap will be blank.")
        return plot_utils_module._create_empty_figure(instance_logger, default_chart_height, plotly_template, f"{chart_title_main_label} Heatmap: All Z Data NaN ({symbol})")

    fig = go.Figure(data=[go.Heatmap(
        z=heatmap_pivot.values, x=x_labels, y=heatmap_pivot.index,
        colorscale=selected_colorscale_name, colorbar=dict(title=str(colorbar_label), thickness=15, len=0.9),
        hovertext=hover_texts_matrix if hover_texts_matrix else None,
        hoverinfo="text" if hover_texts_matrix else "x+y+z",
        xgap=1, ygap=1,
        zmin=float(config.get(f"{metric_col}_heatmap_zmin", heatmap_pivot.values[~np.isnan(heatmap_pivot.values)].min() if np.sum(~np.isnan(heatmap_pivot.values)) > 0 else -1)),
        zmax=float(config.get(f"{metric_col}_heatmap_zmax", heatmap_pivot.values[~np.isnan(heatmap_pivot.values)].max() if np.sum(~np.isnan(heatmap_pivot.values)) > 0 else 1))
    )])
    chart_func_logger.debug(f"  Generic Heatmap trace for '{metric_col}' added.")

    chart_title = f"{figure_title_prefix}{symbol} {chart_title_main_label} Heatmap"
    if fetch_timestamp:
        try: chart_title += f" (Data: {pd.to_datetime(fetch_timestamp).strftime('%Y-%m-%d %H:%M:%S')})"
        except: chart_title += f" (Data: {fetch_timestamp})"

    fig.update_layout(
        title=dict(text=chart_title, x=0.5, xanchor='center'),
        xaxis_title="Expiration Date", yaxis_title="Strike Price",
        height=default_chart_height, template=plotly_template,
        xaxis_type="category",
        yaxis_autorange='reversed' if bool(config.get("heatmap_yaxis_reversed", False)) else True,
        margin=dict(l=70, r=50, t=90, b=60)
    )
    chart_func_logger.debug(f"  Layout updated for '{metric_col}' heatmap.")

    if pd.notna(current_price) and price_line_config.get("show_current_price_line_heatmap", True):
        plot_utils_module._add_price_line(fig, current_price, str(price_line_config.get("current_price_line_color", "rgba(255,255,0,0.7)")),
                                          int(price_line_config.get("current_price_line_width", 2)), str(price_line_config.get("current_price_line_dash", "solid")),
                                          "Current Price", instance_logger=chart_func_logger)
        chart_func_logger.debug(f"  Current price line added at {current_price} for '{metric_col}' heatmap.")
    if timestamp_config.get("enabled", True):
        plot_utils_module._add_timestamp_annotation(fig, chart_func_logger, timestamp_config)
        chart_func_logger.debug(f"  Timestamp annotation added for '{metric_col}' heatmap.")
        
    chart_func_logger.info(f"--- CHART GENERATION END: Generic Expiry/Strike Heatmap ('{metric_col}') for {symbol}. Figure has {len(fig.data)} traces. ---")
    return fig


def create_net_value_heatmap_plotly( # Keep original signature for orchestrator
    instance_logger: logging.Logger, config: Dict[str, Any], plot_utils_module: Any,
    options_df: pd.DataFrame, symbol: str, fetch_timestamp: Optional[str] = None,
    net_value_col: str = "net_value_pressure", strike_col: str = "strike_price",
    expiry_col: str = "expiration_date", opt_kind_col: str = "opt_kind", # opt_kind_col kept for signature, not used in this pivot
    current_price: Optional[float] = None
) -> go.Figure:
    return create_generic_expiry_strike_heatmap(
        instance_logger, config, plot_utils_module, options_df, symbol,
        metric_col=net_value_col, chart_title_main_label="Net Value Pressure",
        colorscale_config_key="net_value_heatmap", colorbar_label="Net Value Pressure",
        strike_col=strike_col, expiry_col=expiry_col,
        current_price=current_price, fetch_timestamp=fetch_timestamp
    )

def create_net_volume_pressure_heatmap_plotly( # Keep original signature
    instance_logger: logging.Logger, config: Dict[str, Any], plot_utils_module: Any,
    options_df: pd.DataFrame, symbol: str, fetch_timestamp: Optional[str] = None,
    net_volume_col: str = "net_volume_pressure", strike_col: str = "strike_price",
    expiry_col: str = "expiration_date", opt_kind_col: str = "opt_kind", # opt_kind_col kept for signature
    current_price: Optional[float] = None
) -> go.Figure:
    return create_generic_expiry_strike_heatmap(
        instance_logger, config, plot_utils_module, options_df, symbol,
        metric_col=net_volume_col, chart_title_main_label="Net Volume Pressure",
        colorscale_config_key="net_volume_pressure_heatmap", colorbar_label="Net Volume Pressure",
        strike_col=strike_col, expiry_col=expiry_col,
        current_price=current_price, fetch_timestamp=fetch_timestamp
    )