# /home/ubuntu/dashboard_v2/enhanced_dashboard_v2.py
# -*- coding: utf-8 -*-
"""
Core Dash application definition script for the Enhanced Options Dashboard V2.
This script initializes the Dash application, loads configuration,
instantiates backend services, sets the layout, and registers callbacks.
(Version: 3.2.0 - EDP/ITS Instantiation Fix & IDS Alignment - Canon Rewrite)
"""

# Standard Library Imports
import os
import sys

# --- IMPORTANT: Add the project root to sys.path for correct module imports ---
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import logging
import json
from typing import Dict, Any, List, Tuple, Deque, Callable, Optional
from collections import deque
from datetime import datetime, date, timedelta
import pandas as pd
import plotly.graph_objects as go
import traceback

# Third-Party Imports
import dash
import dash_bootstrap_components as dbc
from dash import html, dcc, Output, Input, State

# --- EOTS Project Imports (now using central ids.py) ---
# Declare imports and then use a try-except block for robustness
ids = None
load_app_config_into_cache = None
get_config_value = None
CACHE_TIMEOUT_SECONDS_UTILS = 300 # Default
get_main_layout = None
APP_THEME = dbc.themes.CYBORG # Fallback
register_callbacks = None
ConvexValueDataFetcher = None
TradierDataFetcher = None
EnhancedDataProcessor = None
IntegratedTradingSystem = None
MSPIVisualizerV2 = None

BACKEND_SERVICES_IMPORTED_SUCCESSFULLY = False
CORE_DASHBOARD_UTILS_IMPORTED_SUCCESSFULLY = False

try:
    from utils import ids # Import the centralized IDs
    from dashboard_v2.utils import load_app_config_into_cache, get_config_value, CACHE_TIMEOUT_SECONDS_UTILS
    from dashboard_v2.layout import get_main_layout
    from dashboard_v2.styling import APP_THEME
    from dashboard_v2.callbacks import register_callbacks
    CORE_DASHBOARD_UTILS_IMPORTED_SUCCESSFULLY = True
except ImportError as e_core_dash_imp:
    logging.getLogger(__name__).critical(f"CRITICAL CORE DASHBOARD IMPORT ERROR: {e_core_dash_imp}. Some utils/layout/styling/callbacks may be missing.", exc_info=True)
    # Minimal fallbacks will be handled by individual service instantiations or default values later

try:
    from data_management.fetcher_convexvalue_v2_5 import ConvexValueDataFetcher
    from data_management.fetcher_tradier_v2_5 import TradierDataFetcher
    from data_management.enhanced_data_processor_v2 import EnhancedDataProcessor
    from core_analytics.integrated_strategies_v2 import IntegratedTradingSystem
    from mspi_visualization.mspi_visualizer_v2 import MSPIVisualizerV2
    BACKEND_SERVICES_IMPORTED_SUCCESSFULLY = True
except ImportError as e_backend_import:
    logging.getLogger(__name__).critical(f"CRITICAL BACKEND SERVICE IMPORT ERROR: {e_backend_import}. Dashboard will use DUMMY services.", exc_info=True)
    BACKEND_SERVICES_IMPORTED_SUCCESSFULLY = False


# --- Initialize Logger for this Script ---
dashboard_app_logger = logging.getLogger(__name__)
dashboard_app_logger.info("enhanced_dashboard_v2.py (V3.2.0 - EDP/ITS Instantiation Fix & IDS Alignment): Logger initialized.")

# --- Backend Service DUMMY Fallback Class Definitions ---
class _FallbackCVFetcher:
    def __init__(self, *args, **kwargs):
        dashboard_app_logger.warning(f"DASH_APP: Using Fallback CONVEXVALUE Fetcher (DUMMY). Real instance failed. Args: {args}, Kwargs: {kwargs}")
    def fetch_market_data_bundle(self, symbols: List[str], dte_list: Optional[List[int]] = None, price_range_percentage: Optional[float] = None) -> Dict[str, Dict[str, Any]]:
        dashboard_app_logger.warning(f"DASH_APP: _FallbackCVFetcher.fetch_market_data_bundle called for {symbols}. DTEs: {dte_list}, Range: {price_range_percentage}")
        # Use ids if available, otherwise fallback strings
        _ids = ids if ids else type('FallbackIds', (), {'COL_OPTION_SYMBOL': 'symbol', 'CV_UND_PARAM_PRICE': 'price', 'CV_UND_PARAM_FETCH_TIMESTAMP': 'fetch_timestamp'})
        return {s: {
            "options_chain": pd.DataFrame(),
            "underlying": {_ids.COL_OPTION_SYMBOL: s, _ids.CV_UND_PARAM_PRICE: 100.0, _ids.CV_UND_PARAM_FETCH_TIMESTAMP: datetime.now().isoformat(), "error": f"CV_Fallback_Data for {s}"},
            "error": f"CV_Fallback_Bundle_Error for {s}"
        } for s in symbols}
    def get_version(self) -> str: return "CV_Fallback_v0.1-EnhancedDashboard"

class _FallbackTradierFetcher:
    def __init__(self, *args, **kwargs):
        dashboard_app_logger.warning(f"DASH_APP: Using Fallback TRADIER Fetcher (DUMMY). Real instance failed. Args: {args}, Kwargs: {kwargs}")
    def fetch_market_data_bundle(self, symbols: List[str], ohlcv_days: Optional[int] = None, iv_approx_dte: Optional[int] = None) -> Dict[str, Dict[str, Any]]:
        dashboard_app_logger.warning(f"DASH_APP: _FallbackTradierFetcher.fetch_market_data_bundle called for {symbols}. OHLCV_days: {ohlcv_days}, IV_DTE: {iv_approx_dte}")
        _ids = ids if ids else type('FallbackIds', (), {'COL_TRADIER_IV_APPROX_PREFIX': 'tradier_iv', 'CV_UND_PARAM_IV_PERCENTILE_30D': 'iv_percentile_30d'})
        return {s: {
            "iv_and_quote_data": {f"{_ids.COL_TRADIER_IV_APPROX_PREFIX}{iv_approx_dte}_approx_smv_avg": 0.15, _ids.CV_UND_PARAM_IV_PERCENTILE_30D:0.5, "average_historical_atr_pct": 1.5, "error": f"Tradier_Fallback_IV/ATR for {s}"},
            "historical_ohlcv_df": pd.DataFrame(),
            "expiration_calendar": [],
            "error": f"Tradier_Fallback_Bundle_Error for {s}"
        } for s in symbols}
    def get_version(self) -> str: return "Tradier_Fallback_v0.1-EnhancedDashboard"

class _FallbackProcessor:
    def __init__(self, *args, **kwargs):
        dashboard_app_logger.warning(f"DASH_APP: Using Fallback PROCESSOR (DUMMY). Real instance failed. Args: {args}, Kwargs: {kwargs}")
    def process_market_data_bundle(self,
                                  market_data_payload: Dict[str, Dict[str, Any]],
                                  tradier_context_payload: Optional[Dict[str, Dict[str, Any]]] = None,
                                  expiration_calendars_payload: Optional[Dict[str, List[date]]] = None
                                 ) -> Dict[str, Dict[str, Any]]:
        dashboard_app_logger.warning(f"DASH_APP: _FallbackProcessor.process_market_data_bundle called for symbols: {list(market_data_payload.keys())}")
        _ids = ids if ids else type('FallbackIds', (), { # Define a more complete fallback ids for processor
            'COL_STRIKE': 'strike_price', 'COL_OPT_KIND': 'opt_kind', 'COL_MSPI_SCORE': 'mspi', 'COL_SAI': 'sai',
            'COL_SSI': 'ssi', 'COL_ARFI': 'arfi', 'COL_DAG_CUSTOM_NORM': 'dag_custom_norm', 'COL_TDPI_NORM': 'tdpi_norm',
            'COL_VRI_NORM': 'vri_norm', 'COL_SDAG_MULTIPLICATIVE_NORM': 'sdag_multiplicative_norm',
            'COL_SDAG_DIRECTIONAL_NORM': 'sdag_directional_norm', 'COL_SDAG_WEIGHTED_NORM': 'sdag_weighted_norm',
            'COL_SDAG_VOLATILITY_FOCUSED_NORM': 'sdag_volatility_focused_norm',
            'COL_CHART_NET_VOLUME_PRESSURE': 'net_volume_pressure', 'COL_CHART_NET_VALUE_PRESSURE': 'net_value_pressure',
            'COL_CHART_HEURISTIC_NET_DELTA_PRESSURE': 'heuristic_net_delta_pressure', 'COL_CHART_NET_GAMMA_FLOW': 'net_gamma_flow',
            'COL_CHART_NET_VEGA_FLOW': 'net_vega_flow', 'COL_CHART_NET_THETA_EXPOSURE': 'net_theta_exposure',
            'COL_EXPIRATION_DATE': 'expiration_date', 'COL_UNDERLYING_SYMBOL_CHAIN': 'underlying_symbol',
            'COL_CURRENT_PRICE_EDP': 'current_price', 'CV_UND_PARAM_PRICE': 'price', 'CV_VOLM_BS_ROLLING_PREFIX': 'volmbs',
            'CV_VALUE_BS_ROLLING_PREFIX': 'valuebs', 'COL_OPTION_SYMBOL': 'symbol'
        })
        dummy_processed_data = {}
        for sym in market_data_payload.keys():
            dummy_df = pd.DataFrame([
                {
                    _ids.COL_STRIKE: 100.0, _ids.COL_OPT_KIND: 'call', _ids.COL_MSPI_SCORE: 0.5,
                    _ids.COL_SAI: 0.8, _ids.COL_SSI: 0.9, _ids.COL_ARFI: 0.5,
                    _ids.COL_DAG_CUSTOM_NORM: 0.6, _ids.COL_TDPI_NORM: 0.7, _ids.COL_VRI_NORM: 0.8,
                    _ids.COL_SDAG_MULTIPLICATIVE_NORM: 0.5, _ids.COL_SDAG_DIRECTIONAL_NORM: 0.6,
                    _ids.COL_SDAG_WEIGHTED_NORM: 0.7, _ids.COL_SDAG_VOLATILITY_FOCUSED_NORM: 0.8,
                    _ids.COL_CHART_NET_VOLUME_PRESSURE: 1000, _ids.COL_CHART_NET_VALUE_PRESSURE: 100000,
                    _ids.COL_CHART_HEURISTIC_NET_DELTA_PRESSURE: 500, _ids.COL_CHART_NET_GAMMA_FLOW: 50,
                    _ids.COL_CHART_NET_VEGA_FLOW: 20, _ids.COL_CHART_NET_THETA_EXPOSURE: -10,
                    _ids.COL_EXPIRATION_DATE: (date.today() + timedelta(days=1)).isoformat(),
                    _ids.COL_UNDERLYING_SYMBOL_CHAIN: sym,
                    _ids.COL_CURRENT_PRICE_EDP: market_data_payload.get(sym, {}).get("underlying", {}).get(_ids.CV_UND_PARAM_PRICE, 100.0),
                    _ids.CV_VOLM_BS_ROLLING_PREFIX + "_5m": 50, _ids.CV_VALUE_BS_ROLLING_PREFIX + "_5m": 5000,
                }
            ])
            dummy_processed_data[sym] = {
                "processed_data": {"options_chain": dummy_df.to_dict(orient='records')},
                "final_metric_rich_df_obj": dummy_df,
                "error": f"PROCESSOR_DUMMY_FALLBACK_MSG for {sym}",
                "underlying_data_source": market_data_payload.get(sym, {}).get("underlying", {}),
                "market_context_source": tradier_context_payload.get(sym, {}) if tradier_context_payload else {},
                _ids.COL_OPTION_SYMBOL: sym
            }
        return dummy_processed_data
    def get_config_value(self, *args): return None # Dummy method

class _FallbackITS:
    def __init__(self, *args, **kwargs):
        dashboard_app_logger.warning(f"DASH_APP: Using Fallback ITS (DUMMY). Real instance failed. Args: {args}, Kwargs: {kwargs}")
    def process_market_data_and_generate_recommendations(self,
                                                         symbol: str,
                                                         raw_options_data: pd.DataFrame,
                                                         underlying_data: Dict[str, Any],
                                                         market_context: Dict[str, Any],
                                                         historical_ohlc_data: Optional[pd.DataFrame],
                                                         expiration_calendar: Optional[List[date]]
                                                        ) -> Dict[str, Any]:
        dashboard_app_logger.warning(f"DASH_APP: _FallbackITS.process_market_data_and_generate_recommendations called for {symbol}")
        _ids = ids if ids else type('FallbackIds', (), {'COL_MSPI_SCORE': 'mspi', 'COL_OPTION_SYMBOL': 'symbol', 'CV_UND_PARAM_PRICE':'price'})
        df = raw_options_data if isinstance(raw_options_data, pd.DataFrame) else pd.DataFrame(raw_options_data if isinstance(raw_options_data, list) else [])
        if _ids.COL_MSPI_SCORE not in df.columns and not df.empty: df[_ids.COL_MSPI_SCORE] = np.random.uniform(-1,1, len(df))

        dummy_key_levels = {
            "all_levels_sorted_by_strength": [
                {"level_price": underlying_data.get(_ids.CV_UND_PARAM_PRICE, 100.0) * 0.95, "level_type": "Support", "strength_score": 0.8},
            ], "error": "Dummy Key Levels Data"
        }
        return {
            _ids.COL_OPTION_SYMBOL: symbol, "processed_options_df": df.to_dict(orient='records'),
            "final_metric_rich_df_obj": df, "key_levels": dummy_key_levels,
            "signals": {"error": "Dummy Signals Data"}, "recommendations": [],
            "error": f"ITS_Fallback_Data for {symbol}"}
    def get_config_value(self, *args): return None # Dummy method

class _FallbackVisualizer:
    def __init__(self, *args, **kwargs):
        dashboard_app_logger.warning(f"DASH_APP: Using Fallback VISUALIZER (DUMMY). Real instance failed. Args: {args}, Kwargs: {kwargs}")
        self.config = kwargs.get('config_data', {})
    def _create_empty_figure(self, title="Chart Error", height=600, reason="Fallback Visualizer Active"):
        fig = go.Figure()
        final_h = height if isinstance(height, int) and height > 100 else self.config.get("default_chart_height", 600)
        template = self.config.get("plotly_template", "plotly_dark")
        fig.update_layout(title=f"{title} ({reason})", height=final_h, template=template)
        fig.add_annotation(text="Chart unavailable (Fallback Visualizer)", xref="paper", yref="paper", showarrow=False)
        return fig
    def __getattr__(self, name: str) -> Callable[..., go.Figure]:
        # Generic fallback for any chart creation method
        if name.startswith("create_") or name.startswith("plot_"):
            def _dummy_chart_method(*args, **kwargs) -> go.Figure:
                chart_title = name.replace("create_", "").replace("plot_", "").replace("_", " ").title()
                return self._create_empty_figure(title=chart_title)
            return _dummy_chart_method
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

# --- Load Application Configuration ---
APP_CONFIG: Dict[str, Any] = {}
# Check if core dashboard utils were imported successfully
if CORE_DASHBOARD_UTILS_IMPORTED_SUCCESSFULLY and ids and load_app_config_into_cache:
    APP_CONFIG = load_app_config_into_cache(ids.DEFAULT_CONFIG_FILE_PATH)
    if not isinstance(APP_CONFIG, dict):
        dashboard_app_logger.critical(f"DASH_APP: APP_CONFIG loaded was not a dict (type: {type(APP_CONFIG)}). Using empty dict.")
        APP_CONFIG = {}
    else:
        config_path_display = APP_CONFIG.get('_config_file_path_cached_at', ids.DEFAULT_CONFIG_FILE_PATH if ids else "config_v2.json")
        dashboard_app_logger.info(f"DASH_APP: APP_CONFIG loaded from '{config_path_display}'.")
else:
    dashboard_app_logger.critical("DASH_APP: Core dashboard utils (ids, load_app_config_into_cache) did not load. APP_CONFIG will be empty.")
    APP_CONFIG = {}

if ids and ids.CFG_CONFIG_FILE_PATH_CACHED_AT not in APP_CONFIG and ids.CFG_CONFIG_FILE_PATH not in APP_CONFIG and os.path.exists(ids.DEFAULT_CONFIG_FILE_PATH if ids else "config_v2.json"):
     default_cfg_path = ids.DEFAULT_CONFIG_FILE_PATH if ids else "config_v2.json"
     APP_CONFIG[ids.CFG_CONFIG_FILE_PATH_CACHED_AT if ids else "_config_file_path_cached_at"] = os.path.abspath(default_cfg_path)

# --- Configure Logging Level ---
dashboard_app_logger.info("DASH_APP: Configuring application-wide logging levels...")
overall_log_level_str_cfg = "INFO" # Fallback
if CORE_DASHBOARD_UTILS_IMPORTED_SUCCESSFULLY and ids and get_config_value:
    overall_log_level_str_cfg = get_config_value(ids.CFG_SYSTEM_LOG_LEVEL, "INFO", APP_CONFIG).upper()
try:
    dashboard_app_logger.setLevel(getattr(logging, overall_log_level_str_cfg))
    dashboard_app_logger.info(f"  DASH_APP: Logger '{__name__}' level set to: {overall_log_level_str_cfg} (Effective: {logging.getLevelName(dashboard_app_logger.getEffectiveLevel())})")
except AttributeError:
    dashboard_app_logger.setLevel(logging.INFO)
    dashboard_app_logger.warning(f"  DASH_APP: Invalid log level '{overall_log_level_str_cfg}' from APP_CONFIG. Logger '{__name__}' defaulting to INFO.")

granular_log_levels_config = {}
if CORE_DASHBOARD_UTILS_IMPORTED_SUCCESSFULLY and ids and get_config_value:
    granular_log_levels_config = get_config_value(ids.CFG_SYSTEM_LOG_LEVELS_GRANULAR, {}, APP_CONFIG)
if not isinstance(granular_log_levels_config, dict): granular_log_levels_config = {}

modules_to_configure_logging_for_defaults = {
    "dashboard_v2.callbacks": "INFO", "mspi_visualization": "INFO", # Use package name for mspi_visualizer
    "data_management": "INFO", "core_analytics": "INFO"
}
for module_name_log_cfg, default_level_log_cfg in modules_to_configure_logging_for_defaults.items():
    level_to_set_log_cfg_str = granular_log_levels_config.get(module_name_log_cfg, overall_log_level_str_cfg if overall_log_level_str_cfg == "DEBUG" else default_level_log_cfg).upper()
    try:
        logging.getLogger(module_name_log_cfg).setLevel(getattr(logging, level_to_set_log_cfg_str))
        dashboard_app_logger.info(f"  DASH_APP: Logger for '{module_name_log_cfg}' set to: {level_to_set_log_cfg_str}")
    except Exception as e_set_mod_log:
        dashboard_app_logger.error(f"  DASH_APP: Error setting log level for '{module_name_log_cfg}': {e_set_mod_log}")
dashboard_app_logger.info("DASH_APP: Application-wide logging level configuration complete.")

# --- Backend Service Instantiation ---
cv_fetcher_instance_app: Any
tradier_fetcher_instance_app: Any
processor_instance_app: Any
its_instance_app: Any
visualizer_instance_app: Any

dashboard_app_logger.info("DASH_APP: Attempting to import and instantiate backend services...")
service_instantiation_logger = dashboard_app_logger.getChild("ServiceInstantiation")

if BACKEND_SERVICES_IMPORTED_SUCCESSFULLY and CORE_DASHBOARD_UTILS_IMPORTED_SUCCESSFULLY and ids and get_config_value:
    try:
        _cv_fetcher_cfg_path = ids.CFG_CV_FETCHER
        _cv_api_creds_cfg_path = ids.CFG_API_CREDS_CONVEXVALUE
        _cv_fetcher_config = get_config_value(_cv_fetcher_cfg_path, {}, APP_CONFIG)
        _cv_api_creds_config = get_config_value(_cv_api_creds_cfg_path, {}, APP_CONFIG)
        _cv_fetcher_settings_combined = {**_cv_api_creds_config, **_cv_fetcher_config}
        cv_fetcher_instance_app = ConvexValueDataFetcher(cv_settings=_cv_fetcher_settings_combined, main_system_log_level=overall_log_level_str_cfg)
        service_instantiation_logger.info(f"DASH_APP: REAL ConvexValueDataFetcher (v{cv_fetcher_instance_app.get_version()}) instantiated.")
    except Exception as e_inst_cv:
        service_instantiation_logger.critical(f"DASH_APP: FAILED TO INSTANTIATE real ConvexValueDataFetcher: {e_inst_cv}", exc_info=True)
        cv_fetcher_instance_app = _FallbackCVFetcher()

    try:
        _tradier_fetcher_cfg_path = ids.CFG_TRADIER_FETCHER
        _tradier_api_creds_cfg_path = ids.CFG_API_CREDS_TRADIER
        _tradier_fetcher_config = get_config_value(_tradier_fetcher_cfg_path, {}, APP_CONFIG)
        _tradier_api_creds_config = get_config_value(_tradier_api_creds_cfg_path, {}, APP_CONFIG)
        _tradier_fetcher_settings_combined = {**_tradier_api_creds_config, **_tradier_fetcher_config}
        tradier_fetcher_instance_app = TradierDataFetcher(tradier_settings=_tradier_fetcher_settings_combined, main_system_log_level=overall_log_level_str_cfg)
        service_instantiation_logger.info(f"DASH_APP: REAL TradierDataFetcher (v{tradier_fetcher_instance_app.get_version()}) instantiated.")
    except Exception as e_inst_trad:
        service_instantiation_logger.critical(f"DASH_APP: FAILED TO INSTANTIATE real TradierDataFetcher: {e_inst_trad}", exc_info=True)
        tradier_fetcher_instance_app = _FallbackTradierFetcher()

    try:
        service_instantiation_logger.info("DASH_APP: Attempting REAL EnhancedDataProcessor instantiation...")
        def _edp_config_getter_for_dashboard_enhanced(path: List[str], default_val: Any, symbol_ctx: Optional[str] = None) -> Any:
            if not path: return APP_CONFIG # Return the whole APP_CONFIG if path is empty
            return get_config_value(path, default_val, APP_CONFIG)

        processor_instance_app = EnhancedDataProcessor(config_path=None, config_retriever_func=_edp_config_getter_for_dashboard_enhanced)
        
        edp_version = "N/A_INIT_FALLBACK"
        if hasattr(processor_instance_app, 'config_manager_instance') and \
           processor_instance_app.config_manager_instance is not None and \
           hasattr(processor_instance_app.config_manager_instance, 'config') and \
           isinstance(processor_instance_app.config_manager_instance.config, dict):
            edp_version = processor_instance_app.config_manager_instance.config.get('processor_version', 'N/A_EDP_VERSION_KEY')
        
        service_instantiation_logger.info(f"DASH_APP: REAL EnhancedDataProcessor (v{edp_version}) instantiated successfully.")

    except Exception as e_inst_proc: 
        service_instantiation_logger.critical(
            f"DASH_APP: FAILED TO INSTANTIATE real EnhancedDataProcessor. ErrorType: {type(e_inst_proc).__name__}, Error: {e_inst_proc}",
            exc_info=True
        )
        service_instantiation_logger.info("DASH_APP: Falling back to _FallbackProcessor due to EnhancedDataProcessor instantiation error.")
        processor_instance_app = _FallbackProcessor()

    try:
        _config_path_for_its_init_app = APP_CONFIG.get(ids.CFG_CONFIG_FILE_PATH_CACHED_AT, 
                                                     APP_CONFIG.get(ids.CFG_CONFIG_FILE_PATH, 
                                                                    ids.DEFAULT_CONFIG_FILE_PATH))
        service_instantiation_logger.info(f"DASH_APP: Attempting to instantiate REAL IntegratedTradingSystem with config_path: '{_config_path_for_its_init_app}'")
        its_instance_app = IntegratedTradingSystem(config_path=_config_path_for_its_init_app, log_level=overall_log_level_str_cfg)
        
        its_version = "N/A_ITS_VERSION_FALLBACK"
        if hasattr(its_instance_app, 'config') and isinstance(its_instance_app.config, dict):
            its_version = its_instance_app.config.get('version', 'N/A_ITS_CONFIG_VERSION_KEY') # Example: 'version' from config
        
        service_instantiation_logger.info(f"DASH_APP: REAL IntegratedTradingSystem (v{its_version}) instantiated successfully.")
    except Exception as e_its_inst:
        service_instantiation_logger.critical(f"DASH_APP: FAILED TO INSTANTIATE real IntegratedTradingSystem: {e_its_inst}", exc_info=True)
        its_instance_app = _FallbackITS()

    try:
        visualizer_instance_app = MSPIVisualizerV2(config_data=APP_CONFIG) # MSPIVisualizerV2 manages its own config loading
        service_instantiation_logger.info(f"DASH_APP: REAL MSPIVisualizerV2 instantiated.")
    except Exception as e_viz_inst:
        service_instantiation_logger.critical(f"DASH_APP: FAILED TO INSTANTIATE real MSPIVisualizerV2: {e_viz_inst}", exc_info=True)
        visualizer_instance_app = _FallbackVisualizer(config_data=APP_CONFIG) # Pass APP_CONFIG to fallback too
else:
    service_instantiation_logger.critical("DASH_APP: Skipping real backend service instantiation due to critical import errors for core dashboard utils or backend modules. All services will be DUMMY.")
    cv_fetcher_instance_app = _FallbackCVFetcher()
    tradier_fetcher_instance_app = _FallbackTradierFetcher()
    processor_instance_app = _FallbackProcessor()
    its_instance_app = _FallbackITS()
    visualizer_instance_app = _FallbackVisualizer(config_data=APP_CONFIG)


# --- Initialize Dash Application ---
dashboard_app_logger.info("DASH_APP: Initializing Dash application object...")
app_title_from_config_defaulted = "EOTS Dashboard (Config Title Missing)"
assets_folder_name_defaulted = "assets" # Default, ids.py should override if loaded

if CORE_DASHBOARD_UTILS_IMPORTED_SUCCESSFULLY and ids and get_config_value:
    app_title_from_config_defaulted = get_config_value(ids.CFG_DASHBOARD_TITLE, app_title_from_config_defaulted, APP_CONFIG)
    assets_folder_name_defaulted = ids.DASHBOARD_ASSETS_FOLDER_NAME

assets_folder_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), assets_folder_name_defaulted)
if not os.path.isdir(assets_folder_path):
    dashboard_app_logger.warning(f"DASH_APP: Assets folder not found at '{assets_folder_path}'. Static assets might not load.")

app = dash.Dash(
    __name__,
    external_stylesheets=[APP_THEME, dbc.icons.BOOTSTRAP],
    suppress_callback_exceptions=True,
    title=str(app_title_from_config_defaulted),
    assets_folder=assets_folder_path
)
server = app.server
dashboard_app_logger.info(f"DASH_APP: Dash application object initialized. Title: '{app.title}'. Assets path: '{assets_folder_path}'")

# --- Global Server-Side Caches ---
SERVER_SIDE_DATA_CACHE: Dict[str, Tuple[float, Dict[str, Any]]] = {}
COMPONENT_HISTORY_DATA_CACHE: Dict[str, Deque[Tuple[float, pd.DataFrame]]] = {}
dashboard_app_logger.info("DASH_APP: Instance-level server-side cache dictionaries initialized.")

# --- Set Application Layout ---
dashboard_app_logger.info("DASH_APP: Setting application layout...")
if CORE_DASHBOARD_UTILS_IMPORTED_SUCCESSFULLY and get_main_layout:
    try:
        app.layout = get_main_layout() # Function from .layout
        dashboard_app_logger.info("DASH_APP: Application layout set successfully using get_main_layout().")
    except Exception as e_app_layout:
        critical_layout_error_msg = f"DASH_APP: CRITICAL - Failed to set application layout using get_main_layout(): {e_app_layout}"
        dashboard_app_logger.critical(critical_layout_error_msg, exc_info=True)
        app.layout = html.Div([html.H1("Layout Error", className="text-danger text-center p-5"), html.Pre(critical_layout_error_msg + "\n\n" + traceback.format_exc())])
else:
    dashboard_app_logger.critical("DASH_APP: get_main_layout from .layout not available. Using minimal fallback layout.")
    app.layout = html.Div([html.H1("Core Layout Utilities Missing", className="text-danger text-center p-5")])


# --- Register Application Callbacks ---
dashboard_app_logger.info("DASH_APP: Registering application callbacks...")
if CORE_DASHBOARD_UTILS_IMPORTED_SUCCESSFULLY and register_callbacks:
    try:
        register_callbacks(
            app_instance=app,
            cv_fetcher_instance=cv_fetcher_instance_app,
            tradier_fetcher_instance=tradier_fetcher_instance_app,
            processor_instance=processor_instance_app,
            its_instance=its_instance_app,
            visualizer_instance=visualizer_instance_app,
            server_cache_ref=SERVER_SIDE_DATA_CACHE,
            component_history_ref=COMPONENT_HISTORY_DATA_CACHE,
            application_config=APP_CONFIG
        )
        dashboard_app_logger.info("DASH_APP: Application callbacks registered successfully.")
    except Exception as e_callbacks_reg:
        critical_cb_reg_error_msg = f"DASH_APP: CRITICAL error during callback registration: {e_callbacks_reg}"
        dashboard_app_logger.critical(critical_cb_reg_error_msg, exc_info=True)
        # Attempt to add error to layout if layout exists
        if hasattr(app, 'layout') and app.layout is not None:
            cb_reg_err_alert = dbc.Alert(html.Pre(critical_cb_reg_error_msg + "\n\n" + traceback.format_exc()), color="danger", className="m-3", duration=None)
            if hasattr(app.layout, 'children') and isinstance(app.layout.children, list):
                app.layout.children.insert(0, cb_reg_err_alert)
            else: # Fallback if layout is not a list of children
                app.layout = html.Div([cb_reg_err_alert, app.layout])
else:
    dashboard_app_logger.critical("DASH_APP: register_callbacks from .callbacks not available. Callbacks WILL NOT be registered.")
    if hasattr(app, 'layout') and app.layout is not None:
        cb_missing_alert = dbc.Alert("Callback registration module missing. Dashboard will not be interactive.", color="danger", className="m-3")
        if hasattr(app.layout, 'children') and isinstance(app.layout.children, list):
            app.layout.children.insert(0, cb_missing_alert)
        else:
            app.layout = html.Div([cb_missing_alert, app.layout])


# --- Cleanup Function ---
def cleanup_application_resources() -> None:
    cleanup_logger = dashboard_app_logger.getChild("CleanupAppResources")
    cleanup_logger.info("DASH_APP: cleanup_application_resources function called...")
    SERVER_SIDE_DATA_CACHE.clear()
    COMPONENT_HISTORY_DATA_CACHE.clear()
    cleanup_logger.info("DASH_APP: Server-side data caches cleared.")
    if hasattr(cv_fetcher_instance_app, 'shutdown') and callable(getattr(cv_fetcher_instance_app, 'shutdown')):
        try: cv_fetcher_instance_app.shutdown()
        except Exception as e_cv_shutdown: cleanup_logger.error(f"Error shutting down CV Fetcher: {e_cv_shutdown}")
    if hasattr(tradier_fetcher_instance_app, 'shutdown') and callable(getattr(tradier_fetcher_instance_app, 'shutdown')):
        try: tradier_fetcher_instance_app.shutdown()
        except Exception as e_tr_shutdown: cleanup_logger.error(f"Error shutting down Tradier Fetcher: {e_tr_shutdown}")
    cleanup_logger.info("DASH_APP: Application resource cleanup process finished.")

# --- Main Execution Block ---
if __name__ == "__main__":
    dashboard_app_logger.info(f"--- Running '{os.path.basename(__file__)}' directly (V3.2.0) for development ---")
    
    run_debug_mode_main = True
    run_host_main = "127.0.0.1"
    run_port_main = 8050

    if CORE_DASHBOARD_UTILS_IMPORTED_SUCCESSFULLY and ids and get_config_value:
        run_debug_mode_main = get_config_value(ids.CFG_SYSTEM_DASHBOARD_DEBUG_MODE, True, APP_CONFIG)
        run_host_main = get_config_value(ids.CFG_SYSTEM_DASHBOARD_HOST, "127.0.0.1", APP_CONFIG)
        run_port_main = get_config_value(ids.CFG_SYSTEM_DASHBOARD_PORT, 8050, APP_CONFIG)

    final_debug_mode = bool(run_debug_mode_main)
    final_host_str = str(run_host_main)
    final_port_int = 8050
    try: final_port_int = int(run_port_main)
    except (ValueError, TypeError):
        dashboard_app_logger.warning(f"DASH_APP: Invalid port '{run_port_main}'. Defaulting to 8050.")

    dashboard_app_logger.info(f"DASH_APP: Dev server starting on http://{final_host_str}:{final_port_int}/, Debug: {final_debug_mode}")
    if not BACKEND_SERVICES_IMPORTED_SUCCESSFULLY:
        dashboard_app_logger.critical("DASH_APP: CRITICAL - One or more backend services did not load. Functionality severely impaired.")
    if not CORE_DASHBOARD_UTILS_IMPORTED_SUCCESSFULLY:
        dashboard_app_logger.critical("DASH_APP: CRITICAL - Core dashboard utilities (utils, layout, styling, callbacks) did not load. Dashboard may not render correctly or be interactive.")
    
    try:
        app.run_server(
            debug=final_debug_mode, host=final_host_str, port=final_port_int, use_reloader=False
        )
    except SystemExit: dashboard_app_logger.info("DASH_APP: Dev server shutdown (SystemExit).")
    except KeyboardInterrupt: dashboard_app_logger.info("DASH_APP: Dev server shutdown (KeyboardInterrupt).")
    except Exception as e_dev_server_run:
        dashboard_app_logger.critical(f"DASH_APP: Dev server run failed: {e_dev_server_run}", exc_info=True)
    finally:
        cleanup_application_resources()
        dashboard_app_logger.info(f"DASH_APP: '{os.path.basename(__file__)}' direct run finished and cleaned up.")