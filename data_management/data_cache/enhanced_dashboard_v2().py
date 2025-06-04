# --- START OF FILE enhanced_dashboard_v2.py ---

# /home/ubuntu/dashboard_v2/enhanced_dashboard_v2.py
# -*- coding: utf-8 -*-
"""
Core Dash application definition script for the Enhanced Options Dashboard V2.
This script initializes the Dash application, loads configuration,
instantiates backend services, sets the layout, and registers callbacks.
(Version: 3.0.4 - Corrected Instantiation Variable Scopes and Runner Call)
"""

# Standard Library Imports
import os
import logging
import json
from typing import Dict, Any, List, Tuple, Deque, Callable, Optional
from collections import deque
from datetime import datetime
import pandas as pd # For dummy data type hints and DataFrame operations
import plotly.graph_objects as go # For dummy visualizer type hints

# Third-Party Imports
import dash
import dash_bootstrap_components as dbc
from dash import html, dcc, Output, Input, State # Essential Dash components

# --- Initialize Logger for this Script ---
# Configuration of logging level will happen after APP_CONFIG is loaded.
dashboard_app_logger = logging.getLogger(__name__) # Use __name__ for module-level logger

# --- Attempt to Import Core Local Dashboard Modules ---
# These are foundational for the dashboard. If they fail, this module is considered non-functional.
try:
    # Ensure this matches the definition in utils.py (i.e., without _V2)
    from .utils import load_app_config_into_cache, get_config_value, CACHE_TIMEOUT_SECONDS_UTILS
    from .layout import get_main_layout, ALL_CHART_IDS_FOR_FACTORY_CB # Essential constants
    from .styling import APP_THEME
    from .callbacks import register_callbacks
    _core_dashboard_modules_loaded_successfully_app = True
    dashboard_app_logger.info("DASH_APP (V3.0.4): Core local modules (.utils, .layout, .styling, .callbacks) imported successfully.")
except ImportError as e_core_module_imp:
    dashboard_app_logger.critical(
        f"DASH_APP (V3.0.4) CRITICAL: Failed to import essential local dashboard modules: {e_core_module_imp}. "
        f"This application module cannot initialize correctly. Re-raising error.",
        exc_info=True
    )
    raise ImportError(
        f"Critical core dashboard module import failed within enhanced_dashboard_v2.py: {e_core_module_imp}"
    ) from e_core_module_imp


# --- Load Application Configuration ---
# This uses the successfully imported function from utils.py.
# The path is relative to the project root (parent of the 'dashboard_v2' directory).
# Define _DEFAULT_CONFIG_PATH_APP_V304 before using it.
_DEFAULT_CONFIG_PATH_APP_V304 = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config_v2.json")
APP_CONFIG: Dict[str, Any] = load_app_config_into_cache(_DEFAULT_CONFIG_PATH_APP_V304)

if not APP_CONFIG:
    dashboard_app_logger.critical(f"DASH_APP (V3.0.4): APP_CONFIG is empty after load attempt from '{_DEFAULT_CONFIG_PATH_APP_V304}'. This will likely lead to widespread errors.")
# Ensure the loaded config path is stored within APP_CONFIG for reference.
# load_app_config_into_cache from utils.py should already be doing this if the file is found.
if "_config_file_path" not in APP_CONFIG and os.path.exists(_DEFAULT_CONFIG_PATH_APP_V304):
     APP_CONFIG["_config_file_path"] = os.path.abspath(_DEFAULT_CONFIG_PATH_APP_V304)


# --- Configure Logging Level for this Script (based on loaded config) ---
# Define LOG_LEVEL_APP_SCRIPT_STR in a scope accessible by service instantiations.
LOG_LEVEL_APP_SCRIPT_STR: str
_log_level_cfg = ["system_settings", "log_level"]
_log_level_default = "INFO"
LOG_LEVEL_APP_SCRIPT_STR = get_config_value(_log_level_cfg, _log_level_default, APP_CONFIG)
if not isinstance(LOG_LEVEL_APP_SCRIPT_STR, str):
    LOG_LEVEL_APP_SCRIPT_STR = _log_level_default
try:
    dashboard_app_logger.setLevel(getattr(logging, LOG_LEVEL_APP_SCRIPT_STR.upper()))
except AttributeError:
    dashboard_app_logger.setLevel(logging.INFO) # Fallback to INFO
    dashboard_app_logger.warning(f"DASH_APP (V3.0.4): Invalid log level '{LOG_LEVEL_APP_SCRIPT_STR}' from config. Dashboard App logger defaulting to INFO.")
dashboard_app_logger.info(f"DASH_APP (V3.0.4): Logging level for '{__name__}' set to: {logging.getLevelName(dashboard_app_logger.getEffectiveLevel())}.")


# --- Backend Service DUMMY Fallback Class Definitions ---
class _FallbackCVFetcher:
    def __init__(self, *args, **kwargs): dashboard_app_logger.warning("DASH_APP: Using Fallback CONVEXVALUE Fetcher (DUMMY).")
    def fetch_market_data_bundle(self, symbols: List[str], *args, **kwargs) -> Dict[str, Dict[str, Any]]: return {s: {"options_chain": pd.DataFrame(), "underlying": {"symbol": s, "price": 100.0, "fetch_timestamp": datetime.now().isoformat(), "error": f"CV_Fallback for {s}"}, "error": f"CV_Fallback overall for {s}"} for s in symbols}
    def get_version(self) -> str: return "CV_Fallback_v0"

class _FallbackTradierFetcher:
    def __init__(self, *args, **kwargs): dashboard_app_logger.warning("DASH_APP: Using Fallback TRADIER Fetcher (DUMMY).")
    def fetch_market_data_bundle(self, symbols: List[str], *args, **kwargs) -> Dict[str, Dict[str, Any]]: return {s: {"iv_and_quote_data": {}, "historical_ohlcv_df": pd.DataFrame(), "expiration_calendar": [], "error": f"Tradier_Fallback for {s}"} for s in symbols}
    def get_version(self) -> str: return "Tradier_Fallback_v0"

class _FallbackProcessor:
    def __init__(self, *args, **kwargs): dashboard_app_logger.warning("DASH_APP: Using Fallback Processor (DUMMY).")
    def process_market_data_bundle(self, market_data_from_fetcher: Dict[str, Dict[str, Any]], *args, **kwargs) -> Dict[str, Dict[str, Any]]: return {sym: {"processed_data": {"options_chain": []}, "final_metric_rich_df_obj": pd.DataFrame(), "error": f"Processor_Fallback for {sym}"} for sym in market_data_from_fetcher.keys()}

class _FallbackITS:
    def __init__(self, *args, **kwargs): dashboard_app_logger.warning("DASH_APP: Using Fallback ITS (DUMMY).")
    def process_market_data_and_generate_recommendations(self, symbol: str, raw_options_data: pd.DataFrame, *args, **kwargs) -> Dict[str, Any]:
        df = raw_options_data if isinstance(raw_options_data, pd.DataFrame) else pd.DataFrame(raw_options_data if isinstance(raw_options_data, list) else [])
        return {"symbol": symbol, "processed_options_df": df.to_dict(orient='records'), "final_metric_rich_df_obj": df, "key_levels": {}, "signals": {}, "recommendations": [], "error": f"ITS_Fallback for {symbol}"}

class _FallbackVisualizer:
    def __init__(self, *args, **kwargs): dashboard_app_logger.warning("DASH_APP: Using Fallback VISUALIZER (DUMMY).")
    def create_empty_figure(self, title="Fallback Chart", *args, **kwargs): fig = go.Figure(); fig.update_layout(title=f"{title} (AppFallbackVisualizer)"); return fig
    # Add all other chart methods as stubs
    def create_mspi_heatmap(self, *args, **kwargs): return self.create_empty_figure("MSPI Heatmap")
    def create_net_value_heatmap(self, *args, **kwargs): return self.create_empty_figure("Net Value Heatmap")
    def create_net_volume_pressure_heatmap(self, *args, **kwargs): return self.create_empty_figure("Net Volume Heatmap")
    def create_component_comparison(self, *args, **kwargs): return self.create_empty_figure("MSPI Components")
    def create_time_decay_visualization(self, *args, **kwargs): return self.create_empty_figure("Time Decay")
    def create_volatility_regime_visualization(self, *args, **kwargs): return self.create_empty_figure("Volatility Regime")
    def create_combined_rolling_flow_chart(self, *args, **kwargs): return self.create_empty_figure("Rolling Flow")
    def create_key_levels_visualization(self, *args, **kwargs): return self.create_empty_figure("Key Levels")
    def create_trading_signals_visualization(self, *args, **kwargs): return self.create_empty_figure("Trading Signals")
    def create_strategy_recommendations_table(self, *args, **kwargs): return self.create_empty_figure("Recommendations Table")
    def create_net_greek_flow_heatmap(self, *args, **kwargs): return self.create_empty_figure("Net Greek Flow")
    def plot_sdag_multiplicative(self, *args, **kwargs): return self.create_empty_figure("SDAG Mult")
    def plot_sdag_directional(self, *args, **kwargs): return self.create_empty_figure("SDAG Dir")
    def plot_sdag_weighted(self, *args, **kwargs): return self.create_empty_figure("SDAG Weight")
    def plot_sdag_volatility_focused(self, *args, **kwargs): return self.create_empty_figure("SDAG Vol")

# --- Backend Service Imports & Instantiation ---
cv_fetcher_instance_app: Any
tradier_fetcher_instance_app: Any
processor_instance_app: Any
its_instance_app: Any
visualizer_instance_app: Any

dashboard_app_logger.info("DASH_APP (V3.0.4): Attempting to import and instantiate backend services...")
try:
    from enhanced_data_fetcher_v2 import ConvexValueDataFetcher
    _cv_fetcher_cfg_val = get_config_value(["data_fetcher_settings", "convexvalue_fetcher_v2_5"], 
                                       get_config_value(["api_credentials", "convexvalue"], {}, APP_CONFIG), APP_CONFIG)
    cv_fetcher_instance_app = ConvexValueDataFetcher(cv_settings=_cv_fetcher_cfg_val, main_system_log_level=LOG_LEVEL_APP_SCRIPT_STR)
    dashboard_app_logger.info("DASH_APP: ConvexValueDataFetcher instantiated.")
except Exception as e_cv_inst_app_v304:
    dashboard_app_logger.critical(f"DASH_APP: Failed to instantiate ConvexValueDataFetcher: {e_cv_inst_app_v304}", exc_info=True)
    cv_fetcher_instance_app = _FallbackCVFetcher()

try:
    from enhanced_tradier_fetcher_v2 import TradierDataFetcher
    _tradier_cfg_val = get_config_value(["data_fetcher_settings", "tradier_fetcher_v2_5"], 
                                      get_config_value(["api_credentials", "tradier"], {}, APP_CONFIG), APP_CONFIG)
    tradier_fetcher_instance_app = TradierDataFetcher(tradier_settings=_tradier_cfg_val, main_system_log_level=LOG_LEVEL_APP_SCRIPT_STR)
    dashboard_app_logger.info("DASH_APP: TradierDataFetcher instantiated.")
except Exception as e_trad_inst_app_v304:
    dashboard_app_logger.critical(f"DASH_APP: Failed to instantiate TradierDataFetcher: {e_trad_inst_app_v304}", exc_info=True)
    tradier_fetcher_instance_app = _FallbackTradierFetcher()

try:
    from enhanced_data_processor_v2 import EnhancedDataProcessor
    _base_data_dir_val = get_config_value(["system_settings", "data_directory_base"], "eots_data_default_v304", APP_CONFIG)
    _proc_subdir_val = get_config_value(["system_settings", "processed_data_subdirectory"], "market_snapshots_default_v304", APP_CONFIG)
    _config_file_path_for_services = APP_CONFIG.get("_config_file_path", _DEFAULT_CONFIG_PATH_APP_V304) # Use the initially defined default if not in APP_CONFIG

    _config_base_path_for_proc = os.path.dirname(_config_file_path_for_services)
    _resolved_base_data_for_proc = os.path.join(_config_base_path_for_proc, _base_data_dir_val) if not os.path.isabs(_base_data_dir_val) else _base_data_dir_val
    _proc_output_path_final = os.path.join(_resolved_base_data_for_proc, _proc_subdir_val)
    processor_instance_app = EnhancedDataProcessor(config_path=_config_file_path_for_services, data_dir=_proc_output_path_final)
    dashboard_app_logger.info(f"DASH_APP: EnhancedDataProcessor instantiated. Config: {_config_file_path_for_services}, DataDir: {_proc_output_path_final}")
except Exception as e_proc_inst_app_v304:
    dashboard_app_logger.critical(f"DASH_APP: Failed to instantiate EnhancedDataProcessor: {e_proc_inst_app_v304}", exc_info=True)
    processor_instance_app = _FallbackProcessor()

try:
    from core_analytics.integrated_strategies_v2 import IntegratedTradingSystem
    _config_file_path_for_its = APP_CONFIG.get("_config_file_path", _DEFAULT_CONFIG_PATH_APP_V304)
    its_instance_app = IntegratedTradingSystem(config_path=_config_file_path_for_its)
    dashboard_app_logger.info(f"DASH_APP: IntegratedTradingSystem instantiated with config: {_config_file_path_for_its}")
except Exception as e_its_inst_app_v304:
    dashboard_app_logger.critical(f"DASH_APP: Failed to instantiate IntegratedTradingSystem: {e_its_inst_app_v304}", exc_info=True)
    its_instance_app = _FallbackITS()

try:
    from mspi_visualizer_v2 import MSPIVisualizerV2
    visualizer_instance_app = MSPIVisualizerV2(config_data=APP_CONFIG) # Pass the globally loaded APP_CONFIG
    dashboard_app_logger.info("DASH_APP: MSPIVisualizerV2 instantiated.")
except Exception as e_viz_inst_app_v304:
    dashboard_app_logger.critical(f"DASH_APP: Failed to instantiate MSPIVisualizerV2: {e_viz_inst_app_v304}", exc_info=True)
    visualizer_instance_app = _FallbackVisualizer()

# --- Initialize Dash Application ---
dashboard_app_logger.info("DASH_APP (V3.0.4): Initializing Dash application object...")
app_title_final_val_v304 = get_config_value(["visualization_settings", "dashboard", "title"], "Elite Options Dashboard V2 (App Default)", APP_CONFIG)
_assets_folder_path_v304 = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets')

app = dash.Dash(
    __name__,
    external_stylesheets=[APP_THEME, dbc.icons.BOOTSTRAP],
    suppress_callback_exceptions=True,
    title=str(app_title_final_val_v304),
    assets_folder=_assets_folder_path_v304
)
server = app.server
dashboard_app_logger.info(f"DASH_APP: Dash application object initialized. Title: '{app_title_final_val_v304}'. Assets: '{_assets_folder_path_v304}'")

# --- Global Server-Side Caches ---
SERVER_CACHE_APP_INSTANCE_V304: Dict[str, Tuple[float, Dict[str, Any]]] = {}
COMPONENT_HISTORY_CACHE_APP_INSTANCE_V304: Dict[str, Deque[Tuple[float, pd.DataFrame]]] = {}
dashboard_app_logger.info("DASH_APP: Instance-level server-side caches initialized.")

# --- Set Application Layout ---
dashboard_app_logger.info("DASH_APP: Setting application layout...")
try:
    app.layout = get_main_layout()
    dashboard_app_logger.info("DASH_APP: Application layout set successfully.")
except Exception as e_app_layout_main_v304:
    dashboard_app_logger.critical(f"DASH_APP: CRITICAL - Failed to set application layout: {e_app_layout_main_v304}", exc_info=True)
    app.layout = html.Div([html.H1("Layout Error",className="text-danger text-center p-5"), html.P(f"{e_app_layout_main_v304}")])

# --- Register Application Callbacks ---
dashboard_app_logger.info("DASH_APP: Registering application callbacks...")
try:
    register_callbacks(
        app_instance=app,
        cv_fetcher_instance=cv_fetcher_instance_app,
        tradier_fetcher_instance=tradier_fetcher_instance_app,
        processor_instance=processor_instance_app,
        its_instance=its_instance_app,
        visualizer_instance=visualizer_instance_app,
        server_cache_ref=SERVER_CACHE_APP_INSTANCE_V304,
        component_history_ref=COMPONENT_HISTORY_CACHE_APP_INSTANCE_V304,
        application_config=APP_CONFIG
    )
    dashboard_app_logger.info("DASH_APP: Application callbacks registered successfully.")
except Exception as e_callbacks_main_reg_v304:
    dashboard_app_logger.critical(f"DASH_APP: CRITICAL error during callback registration: {e_callbacks_main_reg_v304}", exc_info=True)
    if hasattr(app, 'layout') and app.layout is not None:
        cb_err_alert = dbc.Alert(f"Callback Registration Error: {e_callbacks_main_reg_v304}", color="danger", className="m-3")
        if hasattr(app.layout, 'children') and isinstance(app.layout.children, list): app.layout.children.insert(0, cb_err_alert)
        elif hasattr(app.layout, 'children'): app.layout.children = [cb_err_alert, app.layout.children] if app.layout.children else [cb_err_alert]
        else: app.layout = html.Div(cb_err_alert)

# --- Cleanup Function (for runner script to call on shutdown) ---
def cleanup_cache() -> None:
    dashboard_app_logger.info("DASH_APP (V3.0.4): cleanup_cache function called...")
    SERVER_CACHE_APP_INSTANCE_V304.clear()
    COMPONENT_HISTORY_CACHE_APP_INSTANCE_V304.clear()
    dashboard_app_logger.info("DASH_APP (V3.0.4): Instance-level server-side caches cleared.")

# --- Main Execution Block (for direct run) ---
if __name__ == "__main__":
    dashboard_app_logger.info(f"--- Running '{os.path.basename(__file__)}' directly (V3.0.4) ---")
    
    run_debug_main = get_config_value(["system_settings", "dashboard_debug_mode"], True, APP_CONFIG)
    run_host_main = get_config_value(["system_settings", "dashboard_host"], "127.0.0.1", APP_CONFIG)
    run_port_main = get_config_value(["system_settings", "dashboard_port"], 8050, APP_CONFIG)

    run_debug_bool_final = bool(run_debug_main)
    run_host_str_final = str(run_host_main)
    run_port_int_final = int(run_port_main)

    dashboard_app_logger.info(f"DASH_APP: Dev server starting on http://{run_host_str_final}:{run_port_int_final}/, Debug: {run_debug_bool_final}")
    if not _core_dashboard_modules_loaded_successfully_app:
        dashboard_app_logger.critical("DASH_APP: CRITICAL - Core local dashboard modules did not load. Functionality will be severely impaired.")
    
    try:
        app.run( # Changed from app.run_server to app.run for broader compatibility
            debug=run_debug_bool_final,
            host=run_host_str_final,
            port=run_port_int_final,
            use_reloader=False
        )
    except SystemExit: dashboard_app_logger.info("DASH_APP: Dev server shutdown (SystemExit).")
    except KeyboardInterrupt: dashboard_app_logger.info("DASH_APP: Dev server shutdown (KeyboardInterrupt).")
    except Exception as e_run_main_final:
        dashboard_app_logger.critical(f"DASH_APP: Failed to start/run Dash server: {e_run_main_final}", exc_info=True)
    finally:
        cleanup_cache()
        dashboard_app_logger.info(f"DASH_APP: '{os.path.basename(__file__)}' direct run finished.")