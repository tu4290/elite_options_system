# charts/derived_metric_charts.py
"""
Standalone functions for creating visualizations of derived metrics like
Time Decay (TDPI), Volatility Regime Index (VRI), and various sDAG components.
These functions primarily wrap the _create_raw_greek_chart utility.
Version: DerivedMetricCharts-Canon-V1.1.0 - Alignment with BaseChartUtils V1.1.0
"""

import logging
from typing import Dict, Any, Optional, List

import pandas as pd
import numpy as np
import plotly.graph_objects as go

# Import utility modules
import plot_utils # Alias to plot_utils_module in function args
import charts.base_chart_utils as base_chart_utils # Alias to base_chart_utils_module in function args


def create_time_decay_visualization(
    instance_logger: logging.Logger,
    config: Dict[str, Any], # Full config (Visualizer specific merged with relevant app config)
    base_chart_utils_module: Any, # The imported base_chart_utils module
    plot_utils_module: Any, # The imported plot_utils module
    processed_data: pd.DataFrame,
    symbol: str,
    current_price: Optional[float], # This is the SCALAR underlying price
    selected_price_range_pct_override: Optional[float],
    fetch_timestamp: Optional[str],
    col_strike: str = "strike_price" # Default from viz config, passed by orchestrator
) -> go.Figure:
    """
    Creates a visualization for Time Decay Pressure Index (TDPI) or D-TDPI.
    Uses _create_raw_greek_chart as a base.
    """
    chart_func_logger = instance_logger.getChild("CreateTimeDecayViz_V1.1")
    chart_func_logger.info(f"Attempting to create Time Decay (TDPI/D-TDPI) visualization for {symbol}")

    # Determine if D-TDPI is enabled and its column name, otherwise use base TDPI.
    # This logic assumes the orchestrator (MSPIVisualizerV2) has already put these resolved values into `config`.
    d_tdpi_enabled = config.get("d_tdpi_enabled_viz", False) # From visualizer's effective_config
    metric_to_plot: str
    chart_title_label: str

    if d_tdpi_enabled:
        metric_to_plot = config.get("tdpi_norm_col_cfg", "d_tdpi_norm") # d_tdpi_norm or similar from config
        chart_title_label = "Dynamic TDPI (D-TDPI)"
        color_key_base_tdpi = "d_tdpi_norm" # Key for mspi_components_bar_colors
    else: # Fallback to original TDPI concept if D-TDPI is not enabled or configured for viz
        # The original 'tdpi_score_norm' might not exist if only D-TDPI is calculated by ITS.
        # This part needs careful alignment with what columns ITS actually produces.
        # For now, assume 'tdpi_norm' from data_processor_settings.weights might be the base TDPI.
        metric_to_plot = config.get("column_names",{}).get("tdpi_norm", "tdpi_norm") # A generic TDPI norm column
        chart_title_label = "Time Decay Pressure (TDPI)"
        color_key_base_tdpi = "tdpi_norm"
        # Fallback: If even generic 'tdpi_norm' is not found, this will fail later in _ensure_columns.
        # A more robust system would have distinct config for base TDPI plotting if it's separate from D-TDPI.

    chart_func_logger.info(f"Plotting metric '{metric_to_plot}' for Time Decay chart, labeled as '{chart_title_label}'.")
    
    # Colors from mspi_components_bar_colors
    chart_specific_params_cfg = config.get("chart_specific_params", {})
    mspi_comp_colors_cfg = chart_specific_params_cfg.get("mspi_components_bar_colors", {})
    call_color_tdpi = mspi_comp_colors_cfg.get(color_key_base_tdpi, {}).get("pos", "rgba(255,127,14,0.8)") # Default orange-ish
    put_color_tdpi = mspi_comp_colors_cfg.get(color_key_base_tdpi, {}).get("neg", "rgba(255,187,120,0.8)") # Lighter orange
    
    # col_opt_kind is needed by _create_raw_greek_chart
    # The orchestrator (MSPIVisualizerV2) should resolve this from its config.
    # We assume it's standard or can be fetched from column_names_config if necessary.
    col_opt_kind_name = config.get("column_names", {}).get("option_kind", "opt_kind")


    return base_chart_utils_module._create_raw_greek_chart(
        instance_logger=chart_func_logger,
        config=config, # Pass full config
        plot_utils_module=plot_utils_module,
        col_strike=col_strike, # Passed from orchestrator
        col_opt_kind=col_opt_kind_name, # Get from config
        underlying_price_scalar=current_price, # Pass scalar underlying price
        processed_data=processed_data,
        metric_col=metric_to_plot, # The actual TDPI/D-TDPI column name
        chart_title_part=chart_title_label, # The display name for the chart
        xaxis_title="Strike Price",
        call_color=str(call_color_tdpi),
        put_color=str(put_color_tdpi),
        symbol=symbol,
        selected_price_range_pct_override=selected_price_range_pct_override,
        fetch_timestamp=fetch_timestamp,
        yaxis_title_override=f"{chart_title_label} Score" # Specific Y-axis title
    )


def create_volatility_regime_visualization(
    instance_logger: logging.Logger,
    config: Dict[str, Any],
    base_chart_utils_module: Any,
    plot_utils_module: Any,
    processed_data: pd.DataFrame,
    symbol: str,
    current_price: Optional[float], # Scalar underlying price
    selected_price_range_pct_override: Optional[float],
    fetch_timestamp: Optional[str],
    col_strike: str = "strike_price"
) -> go.Figure:
    """
    Creates a visualization for Volatility Regime Index (VRI / VRI 2.0).
    """
    chart_func_logger = instance_logger.getChild("CreateVolRegimeViz_V1.1")
    chart_func_logger.info(f"Attempting to create Volatility Regime (VRI/VRI 2.0) visualization for {symbol}")

    vri_2_0_enabled = config.get("vri_2_0_enabled_viz", False)
    metric_to_plot: str
    chart_title_label: str

    if vri_2_0_enabled:
        metric_to_plot = config.get("vri_norm_col_cfg", "vri_2_0_norm")
        chart_title_label = "Volatility Regime Index (VRI 2.0)"
        color_key_base_vri = "vri_2_0_norm"
    else:
        metric_to_plot = config.get("column_names",{}).get("vri_norm", "vri_norm")
        chart_title_label = "Volatility Regime Index (VRI)"
        color_key_base_vri = "vri_norm"
        
    chart_func_logger.info(f"Plotting metric '{metric_to_plot}' for Volatility Regime chart, labeled as '{chart_title_label}'.")

    chart_specific_params_cfg = config.get("chart_specific_params", {})
    mspi_comp_colors_cfg = chart_specific_params_cfg.get("mspi_components_bar_colors", {})
    call_color_vri = mspi_comp_colors_cfg.get(color_key_base_vri, {}).get("pos", "rgba(44,160,44,0.8)") # Default greenish
    put_color_vri = mspi_comp_colors_cfg.get(color_key_base_vri, {}).get("neg", "rgba(152,223,138,0.8)")# Lighter green

    col_opt_kind_name = config.get("column_names", {}).get("option_kind", "opt_kind")

    return base_chart_utils_module._create_raw_greek_chart(
        instance_logger=chart_func_logger,
        config=config,
        plot_utils_module=plot_utils_module,
        col_strike=col_strike,
        col_opt_kind=col_opt_kind_name,
        underlying_price_scalar=current_price,
        processed_data=processed_data,
        metric_col=metric_to_plot,
        chart_title_part=chart_title_label,
        xaxis_title="Strike Price",
        call_color=str(call_color_vri),
        put_color=str(put_color_vri),
        symbol=symbol,
        selected_price_range_pct_override=selected_price_range_pct_override,
        fetch_timestamp=fetch_timestamp,
        yaxis_title_override=f"{chart_title_label} Score"
    )

def _plot_sdag_variant_base( # Renamed to avoid conflict with MSPIVisualizerV2's method
    instance_logger: logging.Logger,
    config: Dict[str, Any],
    base_chart_utils_module: Any,
    plot_utils_module: Any,
    processed_data: pd.DataFrame,
    symbol: str,
    current_price: Optional[float], # Scalar underlying price
    fetch_timestamp: Optional[str],
    selected_price_range_pct_override: Optional[float],
    sdag_method_key: str, # e.g., "multiplicative" (from internal mapping), NOT the config key
    chart_display_name_suffix: str, # e.g., "Multiplicative SDAG"
    col_strike: str = "strike_price"
) -> go.Figure:
    """
    Helper function to plot a specific original SDAG variant using _create_raw_greek_chart.
    This is for the *original* SDAG methods, not E-SDAG composite.
    """
    chart_func_logger = instance_logger.getChild(f"_plot_sdag_variant_base.{sdag_method_key}")
    chart_func_logger.info(f"Attempting to create {chart_display_name_suffix} visualization for {symbol}")

    # The column name for this original SDAG variant (e.g., "sdag_multiplicative_norm")
    # This should be reliably available in processed_data if the original SDAGs were calculated.
    # The `config`'s `dag_method_configs` might contain `normalized_column` for these,
    # but MSPIVisualizer already resolves these for component chart. For individual plots,
    # we assume a consistent naming convention or fetch from a dedicated config section for these.
    # Let's use a convention: `sdag_{sdag_method_key}_norm`
    metric_to_plot_sdag = f"sdag_{sdag_method_key}_norm" # Convention-based name
    
    # Check if this sdag method is actually enabled for plotting via a high-level config if available
    # For now, assume if the column exists, we plot it.
    # A more robust way might be `config.get("dag_method_configs",{}).get(sdag_method_key,{}).get("enabled_for_individual_plot", True)`

    chart_specific_params_cfg = config.get("chart_specific_params", {})
    mspi_comp_colors_cfg = chart_specific_params_cfg.get("mspi_components_bar_colors", {})
    
    # Color key for this specific sdag method, e.g., "sdag_multiplicative_norm"
    color_key_for_this_sdag = f"sdag_{sdag_method_key}_norm" 
    call_color_sdag = mspi_comp_colors_cfg.get(color_key_for_this_sdag, {}).get("pos", "rgba(148,103,189,0.8)") # Default purple-ish
    put_color_sdag = mspi_comp_colors_cfg.get(color_key_for_this_sdag, {}).get("neg", "rgba(196,156,148,0.8)") # Default brownish
    
    col_opt_kind_name = config.get("column_names", {}).get("option_kind", "opt_kind")

    return base_chart_utils_module._create_raw_greek_chart(
        instance_logger=chart_func_logger,
        config=config,
        plot_utils_module=plot_utils_module,
        col_strike=col_strike,
        col_opt_kind=col_opt_kind_name,
        underlying_price_scalar=current_price,
        processed_data=processed_data,
        metric_col=metric_to_plot_sdag,
        chart_title_part=chart_display_name_suffix, 
        xaxis_title="Strike Price",
        call_color=str(call_color_sdag),
        put_color=str(put_color_sdag),
        symbol=symbol,
        selected_price_range_pct_override=selected_price_range_pct_override,
        fetch_timestamp=fetch_timestamp,
        yaxis_title_override=f"{chart_display_name_suffix} Score"
    )

def plot_sdag_multiplicative(
    instance_logger: logging.Logger, config: Dict[str, Any], base_chart_utils_module: Any, plot_utils_module: Any,
    processed_data: pd.DataFrame, symbol: str, current_price: Optional[float], fetch_timestamp: Optional[str],
    selected_price_range_pct_override: Optional[float], col_strike: str = "strike_price"
) -> go.Figure:
    return _plot_sdag_variant_base(
        instance_logger, config, base_chart_utils_module, plot_utils_module,
        processed_data, symbol, current_price, fetch_timestamp, selected_price_range_pct_override,
        sdag_method_key="multiplicative", chart_display_name_suffix="SDAG Multiplicative", col_strike=col_strike
    )

def plot_sdag_directional(
    instance_logger: logging.Logger, config: Dict[str, Any], base_chart_utils_module: Any, plot_utils_module: Any,
    processed_data: pd.DataFrame, symbol: str, current_price: Optional[float], fetch_timestamp: Optional[str],
    selected_price_range_pct_override: Optional[float], col_strike: str = "strike_price"
) -> go.Figure:
    return _plot_sdag_variant_base(
        instance_logger, config, base_chart_utils_module, plot_utils_module,
        processed_data, symbol, current_price, fetch_timestamp, selected_price_range_pct_override,
        sdag_method_key="directional", chart_display_name_suffix="SDAG Directional", col_strike=col_strike
    )

def plot_sdag_weighted(
    instance_logger: logging.Logger, config: Dict[str, Any], base_chart_utils_module: Any, plot_utils_module: Any,
    processed_data: pd.DataFrame, symbol: str, current_price: Optional[float], fetch_timestamp: Optional[str],
    selected_price_range_pct_override: Optional[float], col_strike: str = "strike_price"
) -> go.Figure:
    return _plot_sdag_variant_base(
        instance_logger, config, base_chart_utils_module, plot_utils_module,
        processed_data, symbol, current_price, fetch_timestamp, selected_price_range_pct_override,
        sdag_method_key="weighted", chart_display_name_suffix="SDAG Weighted", col_strike=col_strike
    )

def plot_sdag_volatility_focused(
    instance_logger: logging.Logger, config: Dict[str, Any], base_chart_utils_module: Any, plot_utils_module: Any,
    processed_data: pd.DataFrame, symbol: str, current_price: Optional[float], fetch_timestamp: Optional[str],
    selected_price_range_pct_override: Optional[float], col_strike: str = "strike_price"
) -> go.Figure:
    return _plot_sdag_variant_base(
        instance_logger, config, base_chart_utils_module, plot_utils_module,
        processed_data, symbol, current_price, fetch_timestamp, selected_price_range_pct_override,
        sdag_method_key="volatility_focused", chart_display_name_suffix="SDAG Volatility-Focused", col_strike=col_strike
    )