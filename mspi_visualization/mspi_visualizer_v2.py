# mspi_visualizer_v2.py
# Version: MSPIVisualizerV2-Canon-V2.2.2 - Corrected Relative Imports
# This script is designed to be the central visualization component for the EOTS system.
# It orchestrates calls to specialized chart generation modules.

import os
import sys
import json
import traceback
import logging
from datetime import datetime, date, time, timedelta # <<<< ADD timedelta HERE
import time as pytime # <<<< ADD this line to import and alias 'time'
from typing import Optional, Dict, Any, List, Tuple, Union, Deque, Callable
from collections import deque

# Third-Party Imports
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# --- Module-Specific Logger ---
logger = logging.getLogger(__name__) # Logger for mspi_visualizer_v2

# --- Project-Specific Utility Imports ---
# Since mspi_visualizer_v2.py is INSIDE elite_options_system_package,
# and visualizer_config.py & plot_utils.py are SIBLINGS within this package,
# use relative imports.
_utils_imported_successfully = False
try:
    from . import visualizer_config # Correct: Relative import for sibling
    from . import plot_utils        # Correct: Relative import for sibling
    _utils_imported_successfully = True
    logger.debug("MSPI_VISUALIZER: Successfully imported '.visualizer_config' and '.plot_utils' (relative).")
except ImportError as e_proj_imp_utils:
    if not logging.getLogger().hasHandlers(): # Fallback basicConfig
        logging.basicConfig(level=logging.CRITICAL, format='[%(levelname)s] (%(name)s:%(lineno)d) %(asctime)s - %(message)s')
    logger.critical(f"MSPI_VISUALIZER CRITICAL RELATIVE IMPORT ERROR: Cannot import '.visualizer_config' or '.plot_utils'. Error: {e_proj_imp_utils}", exc_info=True)
    # Dummy fallbacks (self-contained)
    class DummyPlotUtils: # type: ignore
        def _create_empty_figure(self, instance_logger, default_chart_height, plotly_template, reason_for_empty=None): instance_logger.error(f"DummyPlotUtils._create_empty_figure called. Reason: {reason_for_empty}"); return go.Figure()
        def _format_hover_value(self, value, value_type="generic", precision=2): return str(value)
        def _add_timestamp_annotation(self, *args, **kwargs): pass
        def _add_price_line(self, *args, **kwargs): pass
        def _ensure_columns(self, df, required_columns, instance_logger): return df, False # type: ignore
        def _create_hover_text(self, *args, **kwargs): return "Hover Error (DummyPlotUtils)"
        def _check_hover_enabled(self, *args, **kwargs): return False
    plot_utils = DummyPlotUtils() # type: ignore
    class DummyVizConfig: # type: ignore
        def _load_visualizer_specific_config(self, *args, **kwargs): return {"_dummy_viz_config": True, "default_chart_height": 600, "plotly_template": "plotly_dark"}
        def _get_config_value(self, instance_logger, full_cfg, viz_cfg, key, default): return default
    visualizer_config = DummyVizConfig() # type: ignore
    logger.warning("MSPI_VISUALIZER: Using DUMMY '.visualizer_config' and '.plot_utils' due to import failure.")


# --- Charting Submodule Imports ---
# Correct: Use relative imports because 'charts' is a sub-package of the current package
# (elite_options_system_package) where mspi_visualizer_v2.py resides.
_charts_submodules_imported_successfully = False
try:
    from .charts import base_chart_utils
    from .charts import heatmaps
    from .charts import component_charts
    from .charts import signal_level_charts
    from .charts import derived_metric_charts
    _charts_submodules_imported_successfully = True
    logger.info("MSPI_VISUALIZER: Successfully imported chart submodules using RELATIVE paths from .charts.")
except ImportError as e_charts_imp:
    if not logging.getLogger().hasHandlers(): # Fallback basicConfig
        logging.basicConfig(level=logging.CRITICAL, format='[%(levelname)s] (%(name)s:%(lineno)d) %(asctime)s - %(message)s')
    logger.critical(f"MSPI_VISUALIZER CRITICAL RELATIVE IMPORT ERROR from .charts: {e_charts_imp}. Charting will use dummies.", exc_info=True)
    
    class DummyChartModule:
        def __init__(self, module_name="UnknownChartModule"):
            self._module_name = module_name
            self._dummy_logger = logger.getChild(f"DummyChartModule.{self._module_name}")

        def __getattr__(self, name: str) -> Callable[..., Any]:
            def _dummy_chart_func(*args: Any, **kwargs: Any) -> go.Figure:
                logger_param = kwargs.get('instance_logger', self._dummy_logger)
                plot_utils_param = kwargs.get('plot_utils_module', plot_utils if _utils_imported_successfully else DummyPlotUtils())
                config_param = kwargs.get('config', {})
                height_val = int(config_param.get("default_chart_height", 600))
                template_val = str(config_param.get("plotly_template", "plotly_dark"))
                reason_text = f"Chart module '{self._module_name}' or function '{name}' failed to load/call."
                logger_param.error(reason_text + f" Args: {str(args)[:100]}, Kwargs: {str(kwargs)[:100]}")
                if hasattr(plot_utils_param, '_create_empty_figure') and callable(plot_utils_param._create_empty_figure):
                    return plot_utils_param._create_empty_figure(logger_param, height_val, template_val, reason_text) # type: ignore
                fig_fallback = go.Figure(); fig_fallback.update_layout(title=reason_text, height=height_val, template=template_val); return fig_fallback
            return _dummy_chart_func

    base_chart_utils = DummyChartModule("base_chart_utils") # type: ignore
    heatmaps = DummyChartModule("heatmaps") # type: ignore
    component_charts = DummyChartModule("component_charts") # type: ignore
    signal_level_charts = DummyChartModule("signal_level_charts") # type: ignore
    derived_metric_charts = DummyChartModule("derived_metric_charts") # type: ignore
    logger.warning("MSPI_VISUALIZER: Using DUMMY chart submodules due to import failure from '.charts'.")
except Exception as e_charts_generic_imp: # Catch any other unexpected import error for charts
    if not logging.getLogger().hasHandlers(): logging.basicConfig(level=logging.CRITICAL, format='[%(levelname)s] (%(name)s:%(lineno)d) %(asctime)s - %(message)s')
    logger.critical(f"MSPI_VISUALIZER: UNEXPECTED CRITICAL ERROR during chart submodule RELATIVE imports: {e_charts_generic_imp}", exc_info=True)
    _charts_submodules_imported_successfully = False
    if 'DummyChartModule' not in locals():
        class DummyChartModule: pass # Minimal re-definition
    base_chart_utils = DummyChartModule("base_chart_utils_ERR_GENERIC") # type: ignore
    # ... (assign other dummies as above)
    logger.error("MSPI_VISUALIZER: Critical generic error during chart submodule import forced DUMMY modules.")


# --- Fallback Logging Setup for this module ---
if not logger.hasHandlers() and not logging.getLogger().handlers:
    _mspi_viz_log_formatter = logging.Formatter(
        '[%(levelname)s] (%(name)s:%(lineno)d) %(asctime)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    _mspi_viz_log_handler = logging.StreamHandler(sys.stdout)
    _mspi_viz_log_handler.setFormatter(_mspi_viz_log_formatter)
    logger.addHandler(_mspi_viz_log_handler)
    logger.setLevel(logging.INFO)
    logger.info("MSPI_VISUALIZER (V2.2.2): Applied FALLBACK logging for this module.")
else:
    logger.debug("MSPI_VISUALIZER (V2.2.2): Logging pre-configured.")

logger.info(f"mspi_visualizer_v2.py (MSPIVisualizerV2-Canon-V2.2.2 - Relative Imports) setup. Utils OK: {_utils_imported_successfully}. Charts OK: {_charts_submodules_imported_successfully}.")

class MSPIVisualizerV2:
    """
    Orchestrates the creation of various MSPI-related visualizations
    by calling specialized chart generation functions.
    """
    def __init__(self, config_path: Optional[str] = None, config_data: Optional[Dict[str, Any]] = None):
        self.instance_logger = logger.getChild(self.__class__.__name__)
        self.instance_logger.info(f"MSPIVisualizerV2 (V2.2.0) Initializing...")

        self.full_app_config: Dict[str, Any] = {}
        if isinstance(config_data, dict):
            self.full_app_config = json.loads(json.dumps(config_data)) # Deep copy for safety
            self.instance_logger.debug("Visualizer initialized with provided 'config_data' (full app config).")
        elif config_path:
            self.instance_logger.debug(f"Visualizer will attempt to load full app config from path: {config_path} to extract its section.")

        # Load visualizer-specific configuration, potentially falling back to defaults
        # _load_visualizer_specific_config is expected to handle merging.
        self.config = visualizer_config._load_visualizer_specific_config(
            instance_logger=self.instance_logger,
            full_app_config_from_init=self.full_app_config, # Pass the copied full config
            config_path_override=config_path if not config_data else None
        )
        
        self._setup_logging() # Set instance logger level based on its own config

        self.output_dir: Optional[str] = self.config.get("output_dir")
        if self.output_dir and isinstance(self.output_dir, str):
            try:
                abs_output_dir = os.path.abspath(self.output_dir)
                os.makedirs(abs_output_dir, exist_ok=True)
                self.output_dir = abs_output_dir
                self.instance_logger.info(f"Output directory for saved charts ensured: {self.output_dir}")
            except OSError as e_dir:
                self.instance_logger.warning(f"Could not create visualizer output directory '{self.output_dir}': {e_dir}. Saving charts might fail.")
                self.output_dir = None
        else:
            self.instance_logger.info("No output directory specified or configured. Charts will not be saved to disk by default.")
            self.output_dir = None

        # Initialize common column names from config
        column_names_config = self.config.get("column_names", {})
        self.col_strike: str = str(column_names_config.get("strike", "strike_price"))
        self.col_opt_kind: str = str(column_names_config.get("option_kind", "opt_kind"))
        self.col_mspi: str = str(column_names_config.get("mspi_score", "mspi")) # Use the one from mspi_config.py
        self.col_net_vol_p: str = str(column_names_config.get("net_volume_pressure", "net_volume_pressure"))
        self.col_net_val_p: str = str(column_names_config.get("net_value_pressure", "net_value_pressure"))
        self.col_expiration_date: str = str(column_names_config.get("expiration_date", "expiration_date"))

        self.instance_logger.info(
            f"Visualizer Column Names Configured: Strike='{self.col_strike}', OptKind='{self.col_opt_kind}', "
            f"MSPI='{self.col_mspi}', Expiry='{self.col_expiration_date}'"
        )
        
        if not _charts_submodules_imported_successfully:
            self.instance_logger.critical("One or more chart submodules from 'elite_options_system_package.charts' failed to import. Visualizer will use dummy charts.")
        
        self.instance_logger.info("MSPIVisualizerV2 Initialized successfully.")

    def _setup_logging(self):
        log_level_str = str(self.config.get("log_level", "INFO")).upper()
        try:
            log_level_to_set = getattr(logging, log_level_str)
            self.instance_logger.setLevel(log_level_to_set)
            self.instance_logger.info(f"MSPIVisualizerV2 instance logger level set to {logging.getLevelName(self.instance_logger.getEffectiveLevel())}.")
        except AttributeError:
            self.instance_logger.warning(f"Invalid log level '{log_level_str}' in visualizer config. Defaulting instance logger to INFO.")
            self.instance_logger.setLevel(logging.INFO)

    def _get_chart_creation_defaults(self) -> Tuple[int, str]:
        """Helper to get default height and template for empty figures."""
        default_height = self.config.get("default_chart_height", 600)
        plotly_template = self.config.get("plotly_template", "plotly_dark")
        return int(default_height), str(plotly_template)

    # --- Chart Creation Methods ---

    def create_mspi_heatmap(self, processed_data: pd.DataFrame, symbol: str = "N/A", current_price: Optional[float] = None, fetch_timestamp: Optional[str] = None, **kwargs) -> go.Figure:
        chart_logger = self.instance_logger.getChild("OrchMSPIHeatmap")
        chart_logger.info(f"Orchestrating MSPI Heatmap for {symbol}...")
        height, template = self._get_chart_creation_defaults()
        try:
            return heatmaps.create_mspi_heatmap_plotly(
                instance_logger=chart_logger, config=self.config, plot_utils_module=plot_utils,
                options_df=processed_data, symbol=symbol, current_price=current_price, fetch_timestamp=fetch_timestamp,
                mspi_col=self.col_mspi, strike_col=self.col_strike, expiry_col=self.col_expiration_date, opt_kind_col=self.col_opt_kind
            )
        except Exception as e:
            chart_logger.error(f"Error orchestrating MSPI Heatmap: {e}", exc_info=True)
            return plot_utils._create_empty_figure(self.instance_logger, height, template, f"Error in MSPI Heatmap for {symbol}: {e}")

    def create_net_value_heatmap(self, processed_data: pd.DataFrame, symbol: str = "N/A", current_price: Optional[float] = None, fetch_timestamp: Optional[str] = None, **kwargs) -> go.Figure:
        chart_logger = self.instance_logger.getChild("OrchNetValueHeatmap")
        chart_logger.info(f"Orchestrating Net Value Heatmap for {symbol}...")
        height, template = self._get_chart_creation_defaults()
        try:
            return heatmaps.create_net_value_heatmap_plotly(
                instance_logger=chart_logger, config=self.config, plot_utils_module=plot_utils,
                options_df=processed_data, symbol=symbol, current_price=current_price, fetch_timestamp=fetch_timestamp,
                net_value_col=self.col_net_val_p, strike_col=self.col_strike, expiry_col=self.col_expiration_date, opt_kind_col=self.col_opt_kind
            )
        except Exception as e:
            chart_logger.error(f"Error orchestrating Net Value Heatmap: {e}", exc_info=True)
            return plot_utils._create_empty_figure(self.instance_logger, height, template, f"Error in Net Value Heatmap for {symbol}: {e}")

    def create_net_volume_pressure_heatmap(self, processed_data: pd.DataFrame, symbol: str = "N/A", current_price: Optional[float] = None, fetch_timestamp: Optional[str] = None, **kwargs) -> go.Figure:
        chart_logger = self.instance_logger.getChild("OrchNetVolHeatmap")
        chart_logger.info(f"Orchestrating Net Volume Pressure Heatmap for {symbol}...")
        height, template = self._get_chart_creation_defaults()
        try:
            return heatmaps.create_net_volume_pressure_heatmap_plotly(
                instance_logger=chart_logger, config=self.config, plot_utils_module=plot_utils,
                options_df=processed_data, symbol=symbol, current_price=current_price, fetch_timestamp=fetch_timestamp,
                net_volume_col=self.col_net_vol_p, strike_col=self.col_strike, expiry_col=self.col_expiration_date, opt_kind_col=self.col_opt_kind
            )
        except Exception as e:
            chart_logger.error(f"Error orchestrating Net Volume Pressure Heatmap: {e}", exc_info=True)
            return plot_utils._create_empty_figure(self.instance_logger, height, template, f"Error in Net Volume Heatmap for {symbol}: {e}")

    def create_component_comparison(self, processed_data: pd.DataFrame, symbol: str = "N/A", current_price: Optional[float] = None, fetch_timestamp: Optional[str] = None, trace_visibility: Optional[Dict[str, Any]] = None, **kwargs) -> go.Figure:
        chart_logger = self.instance_logger.getChild("OrchCompComparison")
        chart_logger.info(f"Orchestrating MSPI Component Comparison for {symbol}...")
        height = int(visualizer_config._get_config_value(self.instance_logger, self.full_app_config, self.config, "chart_specific_params.component_comparison_height", 700))
        template = str(self.config.get("plotly_template", "plotly_dark"))
        try:
            # Prepare effective_config for component_charts by merging visualizer's understanding of full app config
            effective_config = self.config.copy() # Start with visualizer's specific config
            effective_config["a_dag_enabled_viz"] = visualizer_config._get_config_value(self.instance_logger, self.full_app_config, self.config, "enhanced_metrics.a_dag.enabled", False)
            effective_config["dag_norm_col_cfg"] = visualizer_config._get_config_value(self.instance_logger, self.full_app_config, self.config, "enhanced_metrics.a_dag.norm_column_name", "a_dag_norm")
            effective_config["d_tdpi_enabled_viz"] = visualizer_config._get_config_value(self.instance_logger, self.full_app_config, self.config, "enhanced_metrics.d_tdpi.enabled", False)
            effective_config["tdpi_norm_col_cfg"] = visualizer_config._get_config_value(self.instance_logger, self.full_app_config, self.config, "enhanced_metrics.d_tdpi.norm_column_name", "d_tdpi_norm")
            effective_config["vri_2_0_enabled_viz"] = visualizer_config._get_config_value(self.instance_logger, self.full_app_config, self.config, "enhanced_metrics.vri_2_0.enabled", False)
            effective_config["vri_norm_col_cfg"] = visualizer_config._get_config_value(self.instance_logger, self.full_app_config, self.config, "enhanced_metrics.vri_2_0.norm_column_name", "vri_2_0_norm")
            effective_config["e_sdag_enabled_viz"] = visualizer_config._get_config_value(self.instance_logger, self.full_app_config, self.config, "enhanced_metrics.e_sdag.enabled", False)
            effective_config["e_sdag_composite_norm_col_cfg"] = visualizer_config._get_config_value(self.instance_logger, self.full_app_config, self.config, "enhanced_metrics.e_sdag.composite_norm_column_name", "e_sdag_composite_norm")
            effective_config["dag_method_configs"] = visualizer_config._get_config_value(self.instance_logger, self.full_app_config, self.config, "strategy_settings.dag_methodologies", {})


            return component_charts.create_component_comparison(
                instance_logger=chart_logger, config=effective_config, plot_utils_module=plot_utils,
                processed_data=processed_data, symbol=symbol, current_price=current_price, fetch_timestamp=fetch_timestamp,
                trace_visibility=trace_visibility, col_strike=self.col_strike, col_mspi=self.col_mspi
            )
        except Exception as e:
            chart_logger.error(f"Error orchestrating Component Comparison: {e}", exc_info=True)
            return plot_utils._create_empty_figure(self.instance_logger, height, template, f"Error in Component Comparison for {symbol}: {e}")

    def create_combined_rolling_flow_chart(self, processed_data: pd.DataFrame, symbol: str = "N/A", current_price: Optional[float] = None, fetch_timestamp: Optional[str] = None, trace_visibility: Optional[Dict[str, Any]] = None, selected_price_range_pct_override: Optional[float] = None, bar_metric_prefix: str = "volmbs", area_metric_prefix: str = "valuebs", component_history: Optional[Deque[Tuple[float, pd.DataFrame]]] = None, **kwargs) -> go.Figure:
        chart_logger = self.instance_logger.getChild("OrchCombRollFlow")
        chart_logger.info(f"Orchestrating Combined Rolling Flow for {symbol} (Bar: {bar_metric_prefix}, Area: {area_metric_prefix})...")
        height = int(visualizer_config._get_config_value(self.instance_logger, self.full_app_config, self.config, "chart_specific_params.combined_flow_chart_height", 700))
        template = str(self.config.get("plotly_template", "plotly_dark"))
        try:
            return component_charts.create_combined_rolling_flow_chart(
                instance_logger=chart_logger, config=self.config, plot_utils_module=plot_utils,
                processed_data=processed_data, symbol=symbol, current_price=current_price, fetch_timestamp=fetch_timestamp,
                trace_visibility=trace_visibility, selected_price_range_pct_override=selected_price_range_pct_override,
                bar_metric_prefix=bar_metric_prefix, area_metric_prefix=area_metric_prefix,
                col_strike=self.col_strike, component_history=component_history
            )
        except Exception as e:
            chart_logger.error(f"Error orchestrating Combined Rolling Flow: {e}", exc_info=True)
            return plot_utils._create_empty_figure(self.instance_logger, height, template, f"Error in Combined Rolling Flow for {symbol}: {e}")

    def create_key_levels_visualization(self, key_levels_data: Optional[pd.DataFrame], processed_data: pd.DataFrame, symbol: str="N/A", current_price: Optional[float]=None, fetch_timestamp: Optional[str]=None, **kwargs) -> go.Figure:
        chart_logger = self.instance_logger.getChild("OrchKeyLevels")
        chart_logger.info(f"Orchestrating Key Levels Visualization for {symbol}...")
        height = int(visualizer_config._get_config_value(self.instance_logger, self.full_app_config, self.config, "chart_specific_params.key_levels_height", 600))
        template = str(self.config.get("plotly_template", "plotly_dark"))
        try:
            return signal_level_charts.create_key_levels_visualization(
                instance_logger=chart_logger, config=self.config, plot_utils_module=plot_utils,
                col_strike=self.col_strike, col_mspi=self.col_mspi,
                key_levels_data=key_levels_data, base_metric_data_for_line=processed_data,
                symbol=symbol, current_price=current_price, fetch_timestamp=fetch_timestamp
            )
        except Exception as e:
            chart_logger.error(f"Error orchestrating Key Levels Visualization: {e}", exc_info=True)
            return plot_utils._create_empty_figure(self.instance_logger, height, template, f"Error in Key Levels Chart for {symbol}: {e}")

    def create_trading_signals_visualization(self, trading_signals_data: pd.DataFrame, raw_signal_events: Optional[Dict[str, Any]], symbol: str="N/A", current_price: Optional[float]=None, fetch_timestamp: Optional[str]=None, **kwargs) -> go.Figure:
        chart_logger = self.instance_logger.getChild("OrchTradingSignals")
        chart_logger.info(f"Orchestrating Trading Signals Visualization for {symbol}...")
        height = int(visualizer_config._get_config_value(self.instance_logger, self.full_app_config, self.config, "chart_specific_params.trading_signals_height", 650))
        template = str(self.config.get("plotly_template", "plotly_dark"))
        try:
            return signal_level_charts.create_trading_signals_visualization(
                instance_logger=chart_logger, config=self.config, plot_utils_module=plot_utils,
                col_strike=self.col_strike, trading_signals_data=trading_signals_data, raw_signal_events=raw_signal_events,
                symbol=symbol, current_price=current_price, fetch_timestamp=fetch_timestamp
            )
        except Exception as e:
            chart_logger.error(f"Error orchestrating Trading Signals Visualization: {e}", exc_info=True)
            return plot_utils._create_empty_figure(self.instance_logger, height, template, f"Error in Trading Signals Chart for {symbol}: {e}")

    def create_strategy_recommendations_table(self, recommendations_list: Optional[List[Dict[str, Any]]], symbol: str = "N/A", fetch_timestamp: Optional[str] = None, **kwargs) -> go.Figure:
        chart_logger = self.instance_logger.getChild("OrchStrategyTable")
        chart_logger.info(f"Orchestrating Strategy Recommendations Table for {symbol}...")
        height = int(visualizer_config._get_config_value(self.instance_logger, self.full_app_config, self.config, "chart_specific_params.recommendations_table_height", 450))
        template = str(self.config.get("plotly_template", "plotly_dark"))
        try:
            return signal_level_charts.create_strategy_recommendations_table(
                instance_logger=chart_logger, config=self.config, plot_utils_module=plot_utils,
                recommendations_list=recommendations_list or [], symbol=symbol, fetch_timestamp=fetch_timestamp
            )
        except Exception as e:
            chart_logger.error(f"Error orchestrating Strategy Recommendations Table: {e}", exc_info=True)
            return plot_utils._create_empty_figure(self.instance_logger, height, template, f"Error in Recommendations Table for {symbol}: {e}")

    def create_net_greek_flow_heatmap(self, processed_data: pd.DataFrame, metric_column_to_plot: str, chart_main_title_prefix: str, colorscale_config_key: str, colorbar_title_text: str, symbol: str = "N/A", current_price: Optional[float] = None, fetch_timestamp: Optional[str] = None, **kwargs) -> go.Figure:
        chart_logger = self.instance_logger.getChild("OrchNetGreekHeatmap")
        chart_logger.info(f"Orchestrating Net Greek Flow Heatmap for {symbol} (Metric: {metric_column_to_plot})...")
        height, template = self._get_chart_creation_defaults()
        try:
            return base_chart_utils.create_net_greek_flow_heatmap( # Calling from base_chart_utils
                instance_logger=chart_logger, config=self.config, plot_utils_module=plot_utils,
                processed_data=processed_data, metric_column_to_plot=metric_column_to_plot,
                chart_main_title_prefix=chart_main_title_prefix, colorscale_config_key=colorscale_config_key,
                colorbar_title_text=colorbar_title_text, symbol=symbol, current_price=current_price,
                fetch_timestamp=fetch_timestamp, col_strike=self.col_strike, opt_kind_col=self.col_opt_kind,
                expiry_col=self.col_expiration_date
            )
        except Exception as e:
            chart_logger.error(f"Error orchestrating Net Greek Flow Heatmap for {metric_column_to_plot}: {e}", exc_info=True)
            return plot_utils._create_empty_figure(...)

    def create_time_decay_visualization(self, processed_data:pd.DataFrame, symbol:str="N/A", current_price:Optional[float]=None, selected_price_range_pct_override:Optional[float]=None, fetch_timestamp:Optional[str]=None, **kwargs) -> go.Figure:
        chart_logger = self.instance_logger.getChild("OrchTimeDecay")
        chart_logger.info(f"Orchestrating Time Decay Visualization for {symbol}...")
        height, template = self._get_chart_creation_defaults()
        try:
            return derived_metric_charts.create_time_decay_visualization(
                instance_logger=chart_logger, config=self.config, base_chart_utils_module=base_chart_utils, plot_utils_module=plot_utils,
                processed_data=processed_data, symbol=symbol, current_price=current_price,
                selected_price_range_pct_override=selected_price_range_pct_override, fetch_timestamp=fetch_timestamp,
                col_strike=self.col_strike
            )
        except Exception as e:
            chart_logger.error(f"Error orchestrating Time Decay Visualization: {e}", exc_info=True)
            return plot_utils._create_empty_figure(self.instance_logger, height, template, f"Error in Time Decay Chart for {symbol}: {e}")

    def create_volatility_regime_visualization(self, processed_data:pd.DataFrame, symbol:str="N/A", current_price:Optional[float]=None, selected_price_range_pct_override:Optional[float]=None, fetch_timestamp:Optional[str]=None, **kwargs) -> go.Figure:
        chart_logger = self.instance_logger.getChild("OrchVolRegime")
        chart_logger.info(f"Orchestrating Volatility Regime Visualization for {symbol}...")
        height, template = self._get_chart_creation_defaults()
        try:
            return derived_metric_charts.create_volatility_regime_visualization(
                instance_logger=chart_logger, config=self.config, base_chart_utils_module=base_chart_utils, plot_utils_module=plot_utils,
                processed_data=processed_data, symbol=symbol, current_price=current_price,
                selected_price_range_pct_override=selected_price_range_pct_override, fetch_timestamp=fetch_timestamp,
                col_strike=self.col_strike
            )
        except Exception as e:
            chart_logger.error(f"Error orchestrating Volatility Regime Visualization: {e}", exc_info=True)
            return plot_utils._create_empty_figure(self.instance_logger, height, template, f"Error in Volatility Regime Chart for {symbol}: {e}")

    def _plot_sdag_variant(self, sdag_method_name: str, processed_data: pd.DataFrame, symbol: str, current_price: Optional[float], fetch_timestamp: Optional[str], selected_price_range_pct_override: Optional[float]) -> go.Figure:
        chart_logger = self.instance_logger.getChild(f"OrchSDAG_{sdag_method_name.title()}")
        chart_logger.info(f"Orchestrating SDAG {sdag_method_name.title()} for {symbol}...")
        height, template = self._get_chart_creation_defaults()
        
        plot_function_map = {
            "multiplicative": derived_metric_charts.plot_sdag_multiplicative,
            "directional": derived_metric_charts.plot_sdag_directional,
            "weighted": derived_metric_charts.plot_sdag_weighted,
            "volatility_focused": derived_metric_charts.plot_sdag_volatility_focused
        }
        plot_func = plot_function_map.get(sdag_method_name)
        if not plot_func:
            chart_logger.error(f"Unknown SDAG method name: {sdag_method_name}")
            return plot_utils._create_empty_figure(self.instance_logger, height, template, f"Unknown SDAG Variant: {sdag_method_name}")

        try:
            return plot_func(
                instance_logger=chart_logger, config=self.config, base_chart_utils_module=base_chart_utils, plot_utils_module=plot_utils,
                processed_data=processed_data, symbol=symbol, current_price=current_price, fetch_timestamp=fetch_timestamp,
                selected_price_range_pct_override=selected_price_range_pct_override, col_strike=self.col_strike
            )
        except Exception as e:
            chart_logger.error(f"Error orchestrating SDAG {sdag_method_name.title()}: {e}", exc_info=True)
            return plot_utils._create_empty_figure(self.instance_logger, height, template, f"Error in SDAG {sdag_method_name.title()} Chart for {symbol}: {e}")

    def plot_sdag_multiplicative(self, processed_data: pd.DataFrame, symbol: str = "N/A", current_price: Optional[float] = None, fetch_timestamp: Optional[str] = None, selected_price_range_pct_override: Optional[float]=None, **kwargs) -> go.Figure:
        return self._plot_sdag_variant("multiplicative", processed_data, symbol, current_price, fetch_timestamp, selected_price_range_pct_override)

    def plot_sdag_directional(self, processed_data: pd.DataFrame, symbol: str = "N/A", current_price: Optional[float] = None, fetch_timestamp: Optional[str] = None, selected_price_range_pct_override: Optional[float]=None, **kwargs) -> go.Figure:
        return self._plot_sdag_variant("directional", processed_data, symbol, current_price, fetch_timestamp, selected_price_range_pct_override)

    def plot_sdag_weighted(self, processed_data: pd.DataFrame, symbol: str = "N/A", current_price: Optional[float] = None, fetch_timestamp: Optional[str] = None, selected_price_range_pct_override: Optional[float]=None, **kwargs) -> go.Figure:
        return self._plot_sdag_variant("weighted", processed_data, symbol, current_price, fetch_timestamp, selected_price_range_pct_override)

    def plot_sdag_volatility_focused(self, processed_data: pd.DataFrame, symbol: str = "N/A", current_price: Optional[float] = None, fetch_timestamp: Optional[str] = None, selected_price_range_pct_override: Optional[float]=None, **kwargs) -> go.Figure:
        return self._plot_sdag_variant("volatility_focused", processed_data, symbol, current_price, fetch_timestamp, selected_price_range_pct_override)

# --- Standalone Test Block ---
if __name__ == '__main__':
    if not logging.getLogger().hasHandlers() or not any(isinstance(h, logging.StreamHandler) for h in logging.getLogger().handlers):
        logging.basicConfig(
            level=logging.DEBUG,
            format='[%(levelname)s] (%(module)s-%(funcName)s:%(lineno)d) %(asctime)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    main_test_logger = logging.getLogger(__name__ + ".__main__") # Logger for this test block
    main_test_logger.setLevel(logging.DEBUG)
    
    # Ensure the visualizer's own logger and its children also get DEBUG for testing
    # This assumes 'logger' is the module-level logger for mspi_visualizer_v2.py
    logging.getLogger("mspi_visualizer_v2").setLevel(logging.DEBUG)
    for handler in logging.getLogger("mspi_visualizer_v2").handlers: # type: ignore
        if handler: # Check if handler exists
            handler.setLevel(logging.DEBUG)

    main_test_logger.info("--- MSPIVisualizerV2 Standalone Test (Canon V2.2.2 with corrected imports) --- ")

    test_config_path = "config_v2.json" # Assumes config_v2.json is in the same directory or project root
    main_app_config_for_test = {}
    abs_test_config_path = os.path.abspath(test_config_path)
    if not os.path.exists(abs_test_config_path):
        try:
            script_dir_test_viz = os.path.dirname(os.path.abspath(__file__))
        except NameError: # Fallback if __file__ is not defined (e.g. interactive)
            script_dir_test_viz = os.getcwd()
        abs_test_config_path = os.path.join(script_dir_test_viz, test_config_path)

    try:
        if os.path.exists(abs_test_config_path):
            with open(abs_test_config_path, 'r') as f_cfg_viz_test:
                main_app_config_for_test = json.load(f_cfg_viz_test)
            main_test_logger.info(f"Loaded main application config for visualizer test run from {abs_test_config_path}")
        else:
            main_test_logger.warning(f"Main config file '{abs_test_config_path}' not found. Visualizer will use its internal defaults and passed config_data if any.")
    except Exception as e_cfg_load_test:
        main_test_logger.error(f"Could not load main app config from '{abs_test_config_path}': {e_cfg_load_test}. Visualizer will use defaults.")

    visualizer_test_instance = MSPIVisualizerV2(config_data=main_app_config_for_test) # Pass potentially empty dict if load failed
    if hasattr(visualizer_test_instance, 'instance_logger') and visualizer_test_instance.instance_logger:
        visualizer_test_instance.instance_logger.setLevel(logging.DEBUG) 
    main_test_logger.info("MSPIVisualizerV2 instance created for testing.")

    # Create Sample Data (minimal, focus on structure)
    test_symbol_viz = 'TESTSYM'
    current_underlying_price_viz = 100.0
    fetch_timestamp_viz = datetime.now().isoformat()
    sample_strikes = np.arange(90, 111, 5).astype(float)
    sample_data_list = []
    for strike in sample_strikes:
        for opt_kind in ['call', 'put']:
            sample_data_list.append({
                visualizer_test_instance.col_strike: strike,
                visualizer_test_instance.col_opt_kind: opt_kind,
                visualizer_test_instance.col_mspi: np.random.uniform(-0.8, 0.8),
                visualizer_test_instance.col_net_val_p: np.random.uniform(-1e6, 1e6),
                visualizer_test_instance.col_net_vol_p: np.random.uniform(-500, 500),
                # Use the imported timedelta
                visualizer_test_instance.col_expiration_date: (date.today() + timedelta(days=30)).strftime('%Y-%m-%d'),
                'dag_custom_norm': np.random.uniform(-1,1),
                'tdpi_norm': np.random.uniform(-1,1),
                'vri_norm': np.random.uniform(-1,1),
                'volmbs_5m': np.random.randint(-100,100), 'valuebs_5m': np.random.randint(-10000,10000),
                'volmbs_15m': np.random.randint(-100,100), 'valuebs_15m': np.random.randint(-10000,10000),
                'volmbs_30m': np.random.randint(-100,100), 'valuebs_30m': np.random.randint(-10000,10000),
                'volmbs_60m': np.random.randint(-100,100), 'valuebs_60m': np.random.randint(-10000,10000),
                'net_gamma_flow': np.random.uniform(-50,50) 
            })
    sample_processed_data_df_viz = pd.DataFrame(sample_data_list)

    sample_key_levels_list = [
        {'level_price': 95.0, 'level_type': 'Support', 'strength_score': 0.8, 'source_metrics': 'MSPI,NVP'},
        {'level_price': 105.0, 'level_type': 'Resistance', 'strength_score': 0.7, 'source_metrics': 'MSPI'},
    ]
    sample_key_levels_df = pd.DataFrame(sample_key_levels_list)

    sample_signals_raw = {
        'directional_signals': [{'type': 'Bullish MSPI Peak', 'strike': 100, 'opt_kind': 'call', 'score': 0.75, 'timestamp': datetime.now().isoformat()}]
    }
    sample_recommendations_list = [
        {'id': 'REC001', 'Category': 'Directional', 'direction_label': 'Bullish', 'strike': 100, 'strategy': 'Long Call', 'conviction_stars': 3, 'status': 'NEW', 'timestamp': datetime.now().isoformat()}
    ]
    dummy_history_deque: Deque[Tuple[float, pd.DataFrame]] = deque(maxlen=5) # Type hint for clarity
    if not sample_processed_data_df_viz.empty:
        # Use the imported pytime
        dummy_history_deque.append((pytime.time() - 60, sample_processed_data_df_viz.head(2).copy()))


    # --- Test Individual Chart Generation Methods ---
    main_test_logger.info("\n--- Testing Individual Chart Orchestration Methods ---")
    chart_tests = [
        ("MSPI Heatmap", visualizer_test_instance.create_mspi_heatmap, {"processed_data": sample_processed_data_df_viz, "symbol": test_symbol_viz, "current_price": current_underlying_price_viz, "fetch_timestamp": fetch_timestamp_viz}),
        ("Net Value Heatmap", visualizer_test_instance.create_net_value_heatmap, {"processed_data": sample_processed_data_df_viz, "symbol": test_symbol_viz, "current_price": current_underlying_price_viz, "fetch_timestamp": fetch_timestamp_viz}),
        ("Net Volume Heatmap", visualizer_test_instance.create_net_volume_pressure_heatmap, {"processed_data": sample_processed_data_df_viz, "symbol": test_symbol_viz, "current_price": current_underlying_price_viz, "fetch_timestamp": fetch_timestamp_viz}),
        ("Component Comparison", visualizer_test_instance.create_component_comparison, {"processed_data": sample_processed_data_df_viz, "symbol": test_symbol_viz, "current_price": current_underlying_price_viz, "fetch_timestamp": fetch_timestamp_viz}),
        ("Combined Rolling Flow", visualizer_test_instance.create_combined_rolling_flow_chart, {"processed_data": sample_processed_data_df_viz, "symbol": test_symbol_viz, "current_price": current_underlying_price_viz, "fetch_timestamp": fetch_timestamp_viz, "component_history": dummy_history_deque}),
        ("Key Levels", visualizer_test_instance.create_key_levels_visualization, {"key_levels_data": sample_key_levels_df, "processed_data": sample_processed_data_df_viz, "symbol": test_symbol_viz, "current_price": current_underlying_price_viz, "fetch_timestamp": fetch_timestamp_viz}),
        ("Trading Signals", visualizer_test_instance.create_trading_signals_visualization, {"trading_signals_data": sample_processed_data_df_viz, "raw_signal_events": sample_signals_raw, "symbol": test_symbol_viz, "current_price": current_underlying_price_viz, "fetch_timestamp": fetch_timestamp_viz}),
        ("Strategy Table", visualizer_test_instance.create_strategy_recommendations_table, {"recommendations_list": sample_recommendations_list, "symbol": test_symbol_viz, "fetch_timestamp": fetch_timestamp_viz}),
        ("Net Greek Flow (Gamma)", visualizer_test_instance.create_net_greek_flow_heatmap, {"processed_data": sample_processed_data_df_viz, "metric_column_to_plot": "net_gamma_flow", "chart_main_title_prefix": "Net Gamma Flow", "colorscale_config_key": "gamma_colorscale", "colorbar_title_text": "Net Gamma", "symbol": test_symbol_viz, "current_price": current_underlying_price_viz, "fetch_timestamp": fetch_timestamp_viz}),
        ("Time Decay (TDPI)", visualizer_test_instance.create_time_decay_visualization, {"processed_data": sample_processed_data_df_viz, "symbol": test_symbol_viz, "current_price": current_underlying_price_viz, "fetch_timestamp": fetch_timestamp_viz}),
        ("Volatility Regime (VRI)", visualizer_test_instance.create_volatility_regime_visualization, {"processed_data": sample_processed_data_df_viz, "symbol": test_symbol_viz, "current_price": current_underlying_price_viz, "fetch_timestamp": fetch_timestamp_viz}),
        ("SDAG Multiplicative", visualizer_test_instance.plot_sdag_multiplicative, {"processed_data": sample_processed_data_df_viz, "symbol": test_symbol_viz, "current_price": current_underlying_price_viz, "fetch_timestamp": fetch_timestamp_viz}),
    ]

    for chart_name, chart_func, chart_kwargs in chart_tests:
        main_test_logger.info(f"  Testing: {chart_name}")
        try:
            fig = chart_func(**chart_kwargs)
            if fig and isinstance(fig, go.Figure) and (fig.data or (hasattr(fig.layout, 'title') and fig.layout.title and fig.layout.title.text != "No Data Available or Error in Plotting")): 
                main_test_logger.info(f"    OK: '{chart_name}' generated successfully.")
            elif fig and hasattr(fig.layout, 'title') and fig.layout.title and fig.layout.title.text and fig.layout.title.text.startswith("Error in"):
                main_test_logger.error(f"    FAIL: '{chart_name}' generation resulted in an error figure: {fig.layout.title.text}")
            else:
                title_text_debug = fig.layout.title.text if hasattr(fig.layout, 'title') and fig.layout.title and fig.layout.title.text else 'N/A'
                main_test_logger.warning(f"    WARN: '{chart_name}' generated an empty or placeholder figure. Figure data: {fig.data}, Title: {title_text_debug}")
        except Exception as e_chart_test:
            main_test_logger.error(f"    FAIL: '{chart_name}' generation raised an exception: {e_chart_test}", exc_info=True)

    main_test_logger.info("--- MSPIVisualizerV2 Standalone Test Complete ---")