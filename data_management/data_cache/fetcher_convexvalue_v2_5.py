# --- START OF FILE enhanced_dashboard_v2.py ---

# /home/ubuntu/dashboard_v2/enhanced_dashboard_v2.py
# -*- coding: utf-8 -*-
"""
Core Dash application definition script for the Enhanced Options Dashboard V2.
This script initializes the Dash application, loads configuration,
instantiates backend services, sets the layout, and registers callbacks.
(Version: 3.0.7 - Corrected Processor Instantiation and Debug Focus)
"""

# Standard Library Imports
import os
import logging
import json
from typing import Dict, Any, List, Tuple, Deque, Callable, Optional
from collections import deque
from datetime import datetime
import pandas as pd
import plotly.graph_objects as go

# Third-Party Imports
import dash
import dash_bootstrap_components as dbc
from dash import html, dcc, Output, Input, State

# --- Initialize Logger for this Script ---
dashboard_app_logger = logging.getLogger(__name__)

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

# --- Attempt to Import Core Local Dashboard Modules ---
_core_dashboard_modules_loaded_successfully_app = False
try:
    from .utils import load_app_config_into_cache, get_config_value
    from .layout import get_main_layout
    from .styling import APP_THEME
    from .callbacks import register_callbacks
    _core_dashboard_modules_loaded_successfully_app = True
    dashboard_app_logger.info("DASH_APP (V3.0.7): Core local modules (.utils, .layout, .styling, .callbacks) imported successfully.")
except ImportError as e_core_module_imp:
    dashboard_app_logger.critical(
        f"DASH_APP (V3.0.7) CRITICAL: Failed to import essential local dashboard modules: {e_core_module_imp}. "
        f"This application module cannot initialize correctly. Re-raising error.",
        exc_info=True
    )
    raise

# --- Load Application Configuration ---
# Determine the absolute path to config_v2.json, assuming it's one level up from the 'dashboard_v2' package
# This is a common structure: project_root/config_v2.json and project_root/dashboard_v2/enhanced_dashboard_v2.py
_DEFAULT_CONFIG_PATH_APP_V307 = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "config_v2.json"))
APP_CONFIG: Dict[str, Any] = {}
if _core_dashboard_modules_loaded_successfully_app:
    APP_CONFIG = load_app_config_into_cache(_DEFAULT_CONFIG_PATH_APP_V307)
    dashboard_app_logger.info(f"DASH_APP_DEBUG: APP_CONFIG defined. Type: {type(APP_CONFIG)}. Keys: {list(APP_CONFIG.keys()) if isinstance(APP_CONFIG, dict) else 'Not a dict'}")

if not APP_CONFIG:
    dashboard_app_logger.critical(f"DASH_APP (V3.0.7): APP_CONFIG is empty after load attempt from '{_DEFAULT_CONFIG_PATH_APP_V307}'. Using empty dict fallback.")
    APP_CONFIG = {}

if "_config_file_path" not in APP_CONFIG and os.path.exists(_DEFAULT_CONFIG_PATH_APP_V307):
     APP_CONFIG["_config_file_path"] = os.path.abspath(_DEFAULT_CONFIG_PATH_APP_V307)
elif "_config_file_path" not in APP_CONFIG: # If still not set, log a warning
    dashboard_app_logger.warning(f"DASH_APP: _config_file_path could not be determined or set in APP_CONFIG. Path checked: {_DEFAULT_CONFIG_PATH_APP_V307}")


# --- Configure Logging Level for this Script ---
LOG_LEVEL_APP_SCRIPT_STR: str = get_config_value(["system_settings", "log_level"], "INFO", APP_CONFIG)
if not isinstance(LOG_LEVEL_APP_SCRIPT_STR, str): LOG_LEVEL_APP_SCRIPT_STR = "INFO"
try:
    dashboard_app_logger.setLevel(getattr(logging, LOG_LEVEL_APP_SCRIPT_STR.upper()))
except AttributeError:
    dashboard_app_logger.setLevel(logging.INFO)
    dashboard_app_logger.warning(f"DASH_APP (V3.0.7): Invalid log level '{LOG_LEVEL_APP_SCRIPT_STR}'. Defaulting to INFO.")
dashboard_app_logger.info(f"DASH_APP (V3.0.7): Logging level for '{__name__}' set to: {logging.getLevelName(dashboard_app_logger.getEffectiveLevel())}.")

# --- Backend Service Imports & Instantiation ---
cv_fetcher_instance_app: Any
tradier_fetcher_instance_app: Any
processor_instance_app: Any
its_instance_app: Any
visualizer_instance_app: Any

dashboard_app_logger.info("DASH_APP (V3.0.7): Attempting to import and instantiate backend services...")

# ConvexValue Fetcher
try:
    from data_management.fetcher_convexvalue_v2_5 import ConvexValueDataFetcher
    _cv_fetcher_cfg_val = get_config_value(
        ["data_fetcher_settings", "convexvalue_fetcher_v2_5"],
        {}, APP_CONFIG
    )
    dashboard_app_logger.debug(f"DASH_APP: Config slice for ConvexValueDataFetcher: {_cv_fetcher_cfg_val}")
    cv_fetcher_instance_app = ConvexValueDataFetcher(cv_settings=_cv_fetcher_cfg_val, main_system_log_level=LOG_LEVEL_APP_SCRIPT_STR)
    dashboard_app_logger.info(f"DASH_APP: REAL ConvexValueDataFetcher instantiated. Init failed: {cv_fetcher_instance_app.initialization_failed}")
except ImportError as e_cv_imp:
    dashboard_app_logger.critical(f"DASH_APP: IMPORT ERROR for ConvexValueDataFetcher: {e_cv_imp}", exc_info=True)
    cv_fetcher_instance_app = _FallbackCVFetcher()
except Exception as e_cv_inst:
    dashboard_app_logger.critical(f"DASH_APP: Failed to instantiate REAL ConvexValueDataFetcher: {e_cv_inst}", exc_info=True)
    cv_fetcher_instance_app = _FallbackCVFetcher()

# Tradier Fetcher
try:
    from data_management.fetcher_tradier_v2_5 import TradierDataFetcher
    _tradier_cfg_val = get_config_value(
        ["data_fetcher_settings", "tradier_fetcher_v2_5"],
        {}, APP_CONFIG
    )
    dashboard_app_logger.debug(f"DASH_APP: Config slice for TradierDataFetcher: {_tradier_cfg_val}")
    tradier_fetcher_instance_app = TradierDataFetcher(tradier_settings=_tradier_cfg_val, main_system_log_level=LOG_LEVEL_APP_SCRIPT_STR)
    dashboard_app_logger.info(f"DASH_APP: REAL TradierDataFetcher instantiated. Init failed: {tradier_fetcher_instance_app.initialization_failed}")
except ImportError as e_trad_imp:
    dashboard_app_logger.critical(f"DASH_APP: IMPORT ERROR for TradierDataFetcher: {e_trad_imp}", exc_info=True)
    tradier_fetcher_instance_app = _FallbackTradierFetcher()
except Exception as e_trad_inst:
    dashboard_app_logger.critical(f"DASH_APP: Failed to instantiate REAL TradierDataFetcher: {e_trad_inst}", exc_info=True)
    tradier_fetcher_instance_app = _FallbackTradierFetcher()

# EnhancedDataProcessor (V2.5 processor)
try:
    from data_management.enhanced_data_processor_v2 import EnhancedDataProcessor # CORRECTED IMPORT
    
    config_path_for_processor = APP_CONFIG.get("_config_file_path")
    if not config_path_for_processor:
        dashboard_app_logger.critical(f"DASH_APP: _config_file_path not found in APP_CONFIG. Cannot initialize EnhancedDataProcessor. Using fallback.")
        raise ValueError("_config_file_path missing in APP_CONFIG for EnhancedDataProcessor")

    dashboard_app_logger.info(f"DASH_APP: Passing config_path '{config_path_for_processor}' to EnhancedDataProcessor.")
    processor_instance_app = EnhancedDataProcessor(config_path=config_path_for_processor) # CORRECTED INSTANTIATION
    dashboard_app_logger.info(f"DASH_APP: REAL EnhancedDataProcessor instantiated. Type: {type(processor_instance_app).__name__}")
    
    its_instance_app = processor_instance_app.trading_system_instance
    dashboard_app_logger.info(f"DASH_APP: IntegratedTradingSystem instance (from processor) is type: {type(its_instance_app).__name__}")

except ImportError as e_proc_imp:
    dashboard_app_logger.critical(f"DASH_APP: IMPORT ERROR for EnhancedDataProcessor: {e_proc_imp}", exc_info=True)
    processor_instance_app = _FallbackProcessor()
    its_instance_app = _FallbackITS() 
except Exception as e_proc_inst:
    dashboard_app_logger.critical(f"DASH_APP: Failed to instantiate REAL EnhancedDataProcessor: {e_proc_inst}", exc_info=True)
    processor_instance_app = _FallbackProcessor()
    its_instance_app = _FallbackITS()

# MSPIVisualizerV2
try:
    from mspi_visualizer_v2 import MSPIVisualizerV2
    visualizer_instance_app = MSPIVisualizerV2(config_data=APP_CONFIG)
    dashboard_app_logger.info(f"DASH_APP: MSPIVisualizerV2 instantiated. Type: {type(visualizer_instance_app).__name__}")
except ImportError as e_viz_imp:
    dashboard_app_logger.critical(f"DASH_APP: IMPORT ERROR for MSPIVisualizerV2: {e_viz_imp}", exc_info=True)
    visualizer_instance_app = _FallbackVisualizer()
except Exception as e_viz_inst:
    dashboard_app_logger.critical(f"DASH_APP: Failed to instantiate MSPIVisualizerV2: {e_viz_inst}", exc_info=True)
    visualizer_instance_app = _FallbackVisualizer()

# --- Initialize Dash Application ---
dashboard_app_logger.info("DASH_APP (V3.0.7): Initializing Dash application object...")
app_title_final_val_v307 = get_config_value(["visualization_settings", "dashboard", "title"], "EOTS Dashboard V2 (Default)", APP_CONFIG)
_assets_folder_path_v307 = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets')

app = dash.Dash(
    __name__,
    external_stylesheets=[APP_THEME, dbc.icons.BOOTSTRAP],
    suppress_callback_exceptions=True,
    title=str(app_title_final_val_v307),
    assets_folder=_assets_folder_path_v307
)
server = app.server
dashboard_app_logger.info(f"DASH_APP: Dash application object initialized. Title: '{app.title}'. Assets: '{_assets_folder_path_v307}'")

# --- Global Server-Side Caches ---
SERVER_CACHE_APP_INSTANCE_V307: Dict[str, Tuple[float, Dict[str, Any]]] = {}
COMPONENT_HISTORY_CACHE_APP_INSTANCE_V307: Dict[str, Deque[Tuple[float, pd.DataFrame]]] = {}
dashboard_app_logger.info("DASH_APP: Instance-level server-side CACHE DICTS initialized.")

# --- Set Application Layout ---
dashboard_app_logger.info("DASH_APP: Setting application layout...")
try:
    app.layout = get_main_layout()
    dashboard_app_logger.info("DASH_APP: Application layout set successfully.")
except Exception as e_app_layout_main_v307:
    dashboard_app_logger.critical(f"DASH_APP: CRITICAL - Failed to set application layout: {e_app_layout_main_v307}", exc_info=True)
    app.layout = html.Div([html.H1("Layout Error",className="text-danger text-center p-5"), html.P(f"{e_app_layout_main_v307}")])

# --- Register Application Callbacks ---
dashboard_app_logger.info("DASH_APP: Registering application callbacks...")
try:
    if _core_dashboard_modules_loaded_successfully_app:
        register_callbacks(
            app_instance=app,
            cv_fetcher_instance=cv_fetcher_instance_app,
            tradier_fetcher_instance=tradier_fetcher_instance_app,
            processor_instance=processor_instance_app,
            its_instance=its_instance_app,
            visualizer_instance=visualizer_instance_app,
            server_cache_ref=SERVER_CACHE_APP_INSTANCE_V307,
            component_history_ref=COMPONENT_HISTORY_CACHE_APP_INSTANCE_V307,
            application_config=APP_CONFIG
        )
        dashboard_app_logger.info("DASH_APP: Application callbacks registered successfully.")
    else:
        dashboard_app_logger.error("DASH_APP: Skipping callback registration due to failed core local module imports.")
except Exception as e_callbacks_main_reg_v307:
    dashboard_app_logger.critical(f"DASH_APP: CRITICAL error during callback registration: {e_callbacks_main_reg_v307}", exc_info=True)
    if hasattr(app, 'layout') and app.layout is not None:
        cb_err_alert = dbc.Alert(f"Callback Registration Error: {e_callbacks_main_reg_v307}", color="danger", className="m-3")
        if hasattr(app.layout, 'children') and isinstance(app.layout.children, list):
            app.layout.children.insert(0, cb_err_alert)
        elif hasattr(app.layout, 'children'):
            app.layout.children = [cb_err_alert, app.layout.children] if app.layout.children else [cb_err_alert]
        else:
            app.layout = html.Div(cb_err_alert)

# --- Cleanup Function ---
def cleanup_cache() -> None:
    dashboard_app_logger.info("DASH_APP (V3.0.7): cleanup_cache function called...")
    SERVER_CACHE_APP_INSTANCE_V307.clear()
    COMPONENT_HISTORY_CACHE_APP_INSTANCE_V307.clear()
    dashboard_app_logger.info("DASH_APP (V3.0.7): Instance-level server-side caches cleared.")

# --- Main Execution Block (for direct run) ---
if __name__ == "__main__":
    dashboard_app_logger.info(f"--- Running '{os.path.basename(__file__)}' directly (V3.0.7) ---")
    
    run_debug_main = get_config_value(["system_settings", "dashboard_debug_mode"], True, APP_CONFIG)
    run_host_main = get_config_value(["system_settings", "dashboard_host"], "127.0.0.1", APP_CONFIG)
    run_port_main = get_config_value(["system_settings", "dashboard_port"], 8050, APP_CONFIG)

    run_debug_bool_final = bool(run_debug_main)
    run_host_str_final = str(run_host_main)
    run_port_int_final = int(run_port_main)

    dashboard_app_logger.info(f"DASH_APP: Dev server starting on http://{run_host_str_final}:{run_port_int_final}/, Debug: {run_debug_bool_final}")
    if not _core_dashboard_modules_loaded_successfully_app:
        dashboard_app_logger.critical("DASH_APP: CRITICAL - Core local dashboard modules did not load.")
    
    try:
        app.run(
            debug=run_debug_bool_final,
            host=run_host_str_final,
            port=run_port_int_final,
            use_reloader=False
        )
    except SystemExit:
        dashboard_app_logger.info("DASH_APP: Dev server shutdown (SystemExit).")
    except KeyboardInterrupt:
        dashboard_app_logger.info("DASH_APP: Dev server shutdown (KeyboardInterrupt).")
    except Exception as e_run_main_final:
        dashboard_app_logger.critical(f"DASH_APP: Failed to start/run Dash server: {e_run_main_final}", exc_info=True)
    finally:
        cleanup_cache()
        dashboard_app_logger.info(f"DASH_APP: '{os.path.basename(__file__)}' direct run finished.")