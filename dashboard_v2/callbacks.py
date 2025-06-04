# dashboard_v2/callbacks.py
# (Elite Version 3.0.9 - IDS Integrated & Robust Logging - Canon Directive Rewrite)

# Standard Library Imports
import json
import logging
import traceback
from datetime import datetime, date, time as dt_time, timedelta
from typing import Optional, List, Dict, Any, Tuple, Union, Deque, Callable
from collections import deque

# Third-Party Imports
import dash
from dash import dcc, html, Input, Output, State, no_update, ctx as dash_ctx
import dash_bootstrap_components as dbc
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# --- EOTS Project Imports (now using central ids.py and correct relative imports) ---
try:
    from utils import ids # Import the centralized IDs
    from .utils import ( # Import from sibling utils.py
        create_empty_figure, get_config_value, format_status_message,
        get_cached_config, get_cached_data_bundle, set_cached_data_bundle,
        update_data_bundle_history_for_symbol, get_data_bundle_history_for_symbol,
        get_current_time_from_component_id, CACHE_TIMEOUT_SECONDS_UTILS,
        parse_dte_input_string
    )
    from dashboard_v2.styling import apply_card_styling # Correct: relative to project root
    
    _core_utils_layout_styling_imported_ok = True
    logger = logging.getLogger(__name__) # Logger for callbacks.py
    logger.info("callbacks.py (V3.0.9): Successfully imported IDS and core dashboard utilities.")

except ImportError as e_core_local_imp:
    # This block provides minimal fallbacks for critical functions if imports failed.
    # The dashboard can still launch but with known limitations.
    logger = logging.getLogger(__name__) # Logger for callbacks.py
    logger.critical(
        f"callbacks.py (V3.0.9) CRITICAL: Failed to import local modules: {e_core_local_imp}. Fallbacks activated.", exc_info=True
    )
    _core_utils_layout_styling_imported_ok = False
    
    # Minimal fallbacks for critical functions
    def get_config_value(path, default, app_cfg): return default
    def format_status_message(msg, is_err, **kwargs): return html.Div(msg) # Added **kwargs for timestamp
    def create_empty_figure(title="Chart Error", height=600, reason="Import Fail"): fig=go.Figure();fig.update_layout(title=f"{title} ({reason})");return fig
    def get_cached_data_bundle(key, cache): return None
    def set_cached_data_bundle(key, data, cache): pass
    def update_data_bundle_history_for_symbol(sym, df, ts, hist): pass
    def get_data_bundle_history_for_symbol(sym, hist): return deque()
    def get_current_time_from_component_id(trigger): return datetime.now().time()
    def parse_dte_input_string(dte_str): return None
    CACHE_TIMEOUT_SECONDS_UTILS = 300
    
    # Fallback IDs (these should ideally be handled by ids.py importing correctly)
    # If ids.py itself failed, these are minimal string literals to prevent NameError
    try:
        from utils import ids # Try importing ids for fallbacks if it partially worked
    except ImportError:
        class ids: # type: ignore
            ID_SYMBOL_INPUT = "fallback-symbol-input"
            ID_DTE_INPUT = "fallback-expiration-input"
            ID_RANGE_SLIDER = "fallback-price-range-slider"
            ID_REFRESH_INTERVAL_DROPDOWN = "fallback-interval-dropdown"
            ID_FETCH_DATA_BUTTON = "fallback-fetch-button"
            ID_MAIN_DATA_STORE_MEMORY = "fallback-cache-store"
            ID_APP_CONFIG_STORE = "fallback-app-config-store"
            ID_HIDDEN_INITIAL_LOAD_TRIGGER = "fallback-initial-load-trigger-callbacks"
            ID_STATUS_DISPLAY_AREA = "fallback-status-display"
            ID_ALERT_CONTAINER = "fallback-alert-container"
            ID_OVERLAY_LOADING = "fallback-overlay-loading"
            ID_AUTO_REFRESH_INTERVAL_COMPONENT = "fallback-interval-timer"
            ID_MODE_SELECTOR_TABS = "fallback-mode-tabs"
            ID_MAIN_CONTENT_AREA = "fallback-mode-content"
            ID_TAB_MAIN_DASHBOARD = "fallback-tab-main-dashboard"
            ID_TAB_SDAG_DIAGNOSTICS = "fallback-tab-sdag-diagnostics"
            ID_TAB_ENHANCED_FLOW = "fallback-tab-enhanced-flow"
            ID_TAB_VOLATILITY_DEEP_DIVE = "fallback-tab-volatility-deep-dive"
            ID_TAB_PERFORMANCE = "fallback-tab-performance"

            ID_CHART_MSPI_HEATMAP = "fallback-mspi-heatmap"
            ID_CHART_MSPI_COMPONENTS = "fallback-mspi-components"
            ID_CHART_COMBINED_ROLLING_FLOW = "fallback-combined-rolling-flow"
            ID_CHART_KEY_LEVELS = "fallback-key-levels"
            ID_CHART_TRADING_SIGNALS = "fallback-trading-signals"
            ID_CHART_RECOMMENDATIONS_TABLE = "fallback-recommendations-table"
            ID_CHART_NET_GREEK_FLOW_HEATMAP = "fallback-net-greek-flow-heatmap"
            ID_CHART_NET_VALUE_HEATMAP = "fallback-net-value-heatmap"
            ID_CHART_NET_VOLUME_PRESSURE_HEATMAP = "fallback-net-volume-pressure-heatmap"
            ID_CHART_VOLATILITY_REGIME = "fallback-volatility-regime"
            ID_CHART_TIME_DECAY = "fallback-time-decay"
            ID_CHART_SDAG_MULTIPLICATIVE = "fallback-sdag-multiplicative"
            ID_CHART_SDAG_DIRECTIONAL = "fallback-sdag-directional"
            ID_CHART_SDAG_WEIGHTED = "fallback-sdag-weighted"
            ID_CHART_SDAG_VOLATILITY_FOCUSED = "fallback-sdag-volatility-focused"

            ID_MSPI_HEATMAP_SELECTOR = "fallback-mspi-heatmap-selector"
            ID_NET_GREEK_FLOW_SELECTOR = "fallback-net-greek-flow-selector"
            ID_ROLLING_FLOW_SELECTOR = "fallback-rolling-flow-selector"
            ID_RANGE_SLIDER_OUTPUT_LABEL = "fallback-range-slider-label" # Added this

            ALL_CHART_IDS_FOR_FACTORY = [ID_CHART_MSPI_HEATMAP] # Minimal list for loop
            CFG_TRADIER_IV_APPROX_TARGET_DTE_DEFAULT = ["fallback_config_path"] # Dummy config path
            CV_UND_PARAM_IV_PERCENTILE_30D = "fallback_iv_pct_key"
            COL_TRADIER_IV_APPROX_PREFIX = "fallback_tradier_iv_prefix"
            COL_OPTION_SYMBOL = "symbol"
            COL_UND_PRICE = "price"
            COL_UND_FETCH_TIMESTAMP = "fetch_timestamp"
            COL_CURRENT_PRICE_EDP = "current_price" # Added this
            CFG_CV_FETCHER = ["fallback_cv_fetcher_cfg"]
            CFG_TRADIER_FETCHER = ["fallback_tradier_fetcher_cfg"]
            CFG_VIZ_MSPI_VISUALIZER = ["fallback_viz_mspi_viz_cfg"]
            CFG_VIZ_GREEK_FLOW_HEATMAP_OPTIONS = ["fallback_viz_greek_opts_cfg"]
            CFG_VIZ_GREEK_FLOW_HEATMAP_DEFAULT_METRIC = ["fallback_viz_greek_default_cfg"]
            CFG_VIZ_ROLLING_FLOW_CHART_OPTIONS = ["fallback_viz_roll_opts_cfg"]
            CFG_VIZ_ROLLING_FLOW_CHART_DEFAULT_OPTION = ["fallback_viz_roll_default_cfg"]
            CFG_VIZ_COL_NAMES = ["visualization_settings", "mspi_visualizer", "column_names"] # Added this
            COL_STRIKE = "strike_price"
            COL_MSPI_SCORE = "mspi"
            COL_OPT_KIND = "opt_kind"
            COL_EXPIRATION_DATE = "expiration_date"
            COL_DAG_CUSTOM_NORM = "dag_custom_norm"
            COL_TDPI_NORM = "tdpi_norm"
            COL_VRI_NORM = "vri_norm"
            COL_SDAG_MULTIPLICATIVE_NORM = "sdag_multiplicative_norm"
            COL_SDAG_DIRECTIONAL_NORM = "sdag_directional_norm"
            COL_SDAG_WEIGHTED_NORM = "sdag_weighted_norm"
            COL_SDAG_VOLATILITY_FOCUSED_NORM = "sdag_volatility_focused_norm"
            COL_CHART_NET_VOLUME_PRESSURE = "net_volume_pressure"
            COL_CHART_NET_VALUE_PRESSURE = "net_value_pressure"
            COL_CHART_HEURISTIC_NET_DELTA_PRESSURE = "heuristic_net_delta_pressure"
            COL_CHART_NET_GAMMA_FLOW = "net_gamma_flow"
            COL_CHART_NET_VEGA_FLOW = "net_vega_flow"
            COL_CHART_NET_THETA_EXPOSURE = "net_theta_exposure"
            CV_VOLM_BS_ROLLING_PREFIX = "volmbs"
            CV_VALUE_BS_ROLLING_PREFIX = "valuebs"
            CFG_VIZ_MSPI_VISUALIZER = ["visualization_settings", "mspi_visualizer"] # Added


# --- Dummy Backend Service Class Definitions ---
# These are identical to the Fallback classes in enhanced_dashboard_v2.py
# They are defined here to ensure the callbacks.py module always has access to them
# even if the real imports in enhanced_dashboard_v2.py fail.
class GenericDummyService:
    def __init__(self, service_name="UnknownService", *args, **kwargs): self._service_name = service_name; self._version = f"{service_name}_Dummy_v0.1"; logger.warning(f"CB_Dummy: {self._service_name} INSTANTIATED (Fallback).")
    def get_version(self) -> str: return self._version
    def __getattr__(self, name: str) -> Callable[..., Dict[str, Any]]:
        def dummy_method(*args, **kwargs) -> Dict[str, Any]:
            logger.warning(f"CB_Dummy: {self._service_name}.{name} (dummy method) called with args: {args}, kwargs: {kwargs}")
            if "symbol" in kwargs: return {"symbol": kwargs["symbol"], "error": f"{self._service_name} DUMMY FALLBACK for method {name}"}
            if args and isinstance(args[0], list) and args[0]: return {s: {"error": f"{self._service_name} DUMMY FALLBACK for method {name} (symbol: {s})"} for s in args[0]}
            return {"error": f"{self._service_name} DUMMY FALLBACK for method {name}"}
        return dummy_method

class ConvexValueDataFetcherDummy(GenericDummyService):
    def __init__(self, *args, **kwargs): super().__init__("ConvexValueDataFetcher", *args, **kwargs)
    def fetch_market_data_bundle(self, symbols: List[str], dte_list: Optional[List[int]] = None, price_range_percentage: Optional[float] = None) -> Dict[str, Dict[str, Any]]:
        logger.warning(f"CB_Dummy: CVFetcherDummy.fetch_market_data_bundle called for {symbols}. DTEs: {dte_list}, Range: {price_range_percentage}")
        return {s: {
            "options_chain": pd.DataFrame(),
            "underlying": {ids.COL_OPTION_SYMBOL: s, ids.COL_UND_PRICE: 100.0, ids.COL_UND_FETCH_TIMESTAMP: datetime.now().isoformat(), "error": f"CV_Fallback_Data for {s}"},
            "error": f"CV_Fallback_Bundle_Error for {s}"
        } for s in symbols}

class TradierDataFetcherDummy(GenericDummyService):
    def __init__(self, *args, **kwargs): 
        super().__init__("TradierDataFetcher", *args, **kwargs)
    
    def fetch_market_data_bundle(self, symbols: List[str], ohlcv_days: Optional[int] = None, iv_approx_dte: Optional[int] = None) -> Dict[str, Dict[str, Any]]:
        logger.warning(f"CB_Dummy: TradierFetcherDummy.fetch_market_data_bundle called for {symbols}. OHLCV_days: {ohlcv_days}, IV_DTE: {iv_approx_dte}")
        return {s: {
            "iv_and_quote_data": {f"{ids.COL_TRADIER_IV_APPROX_PREFIX}{iv_approx_dte}_approx_smv_avg": 0.15, ids.CV_UND_PARAM_IV_PERCENTILE_30D: 0.5, "average_historical_atr_pct": 1.5, "error": f"Tradier_Fallback_IV/ATR for {s}"},
            "historical_ohlcv_df": pd.DataFrame(),
            "expiration_calendar": [],
            "error": f"Tradier_Fallback_Bundle_Error for {s}"
        } for s in symbols}

class EnhancedDataProcessorDummy(GenericDummyService):
    def __init__(self, *args, **kwargs): super().__init__("EnhancedDataProcessor", *args, **kwargs)
    def process_market_data_bundle(self,
                                  market_data_payload: Dict[str, Dict[str, Any]],
                                  tradier_context_payload: Optional[Dict[str, Dict[str, Any]]] = None,
                                  expiration_calendars_payload: Optional[Dict[str, List[date]]] = None
                                 ) -> Dict[str, Dict[str, Any]]:
        logger.warning(f"CB_Dummy: ProcessorDummy.process_market_data_bundle called for symbols: {list(market_data_payload.keys())}")
        dummy_processed_data = {}
        for sym in market_data_payload.keys():
            dummy_df = pd.DataFrame([
                {
                    ids.COL_STRIKE: 100.0, ids.COL_OPT_KIND: 'call', ids.COL_MSPI_SCORE: 0.5,
                    ids.COL_SAI: 0.8, ids.COL_SSI: 0.9, ids.COL_ARFI: 0.5,
                    ids.COL_DAG_CUSTOM_NORM: 0.6, ids.COL_TDPI_NORM: 0.7, ids.COL_VRI_NORM: 0.8,
                    ids.COL_SDAG_MULTIPLICATIVE_NORM: 0.5, ids.COL_SDAG_DIRECTIONAL_NORM: 0.6,
                    ids.COL_SDAG_WEIGHTED_NORM: 0.7, ids.COL_SDAG_VOLATILITY_FOCUSED_NORM: 0.8,
                    ids.COL_CHART_NET_VOLUME_PRESSURE: 1000, ids.COL_CHART_NET_VALUE_PRESSURE: 100000,
                    ids.COL_CHART_HEURISTIC_NET_DELTA_PRESSURE: 500, ids.COL_CHART_NET_GAMMA_FLOW: 50,
                    ids.COL_CHART_NET_VEGA_FLOW: 20, ids.COL_CHART_NET_THETA_EXPOSURE: -10,
                    ids.COL_EXPIRATION_DATE: (date.today() + timedelta(days=1)).isoformat(),
                    ids.COL_UNDERLYING_SYMBOL_CHAIN: sym,
                    ids.COL_CURRENT_PRICE_EDP: market_data_payload.get(sym, {}).get("underlying", {}).get(ids.COL_UND_PRICE, 100.0),
                    ids.CV_VOLM_BS_ROLLING_PREFIX + "_5m": 50, ids.CV_VALUE_BS_ROLLING_PREFIX + "_5m": 5000,
                },
                {
                    ids.COL_STRIKE: 95.0, ids.COL_OPT_KIND: 'put', ids.COL_MSPI_SCORE: -0.5,
                    ids.COL_SAI: 0.8, ids.COL_SSI: 0.9, ids.COL_ARFI: 0.5,
                    ids.COL_DAG_CUSTOM_NORM: -0.6, ids.COL_TDPI_NORM: -0.7, ids.COL_VRI_NORM: -0.8,
                    ids.COL_SDAG_MULTIPLICATIVE_NORM: -0.5, ids.COL_SDAG_DIRECTIONAL_NORM: -0.6,
                    ids.COL_SDAG_WEIGHTED_NORM: -0.7, ids.COL_SDAG_VOLATILITY_FOCUSED_NORM: -0.8,
                    ids.COL_CHART_NET_VOLUME_PRESSURE: -1000, ids.COL_CHART_NET_VALUE_PRESSURE: -100000,
                    ids.COL_CHART_HEURISTIC_NET_DELTA_PRESSURE: -500, ids.COL_CHART_NET_GAMMA_FLOW: -50,
                    ids.COL_CHART_NET_VEGA_FLOW: -20, ids.COL_CHART_NET_THETA_EXPOSURE: 10,
                    ids.COL_EXPIRATION_DATE: (date.today() + timedelta(days=1)).isoformat(),
                    ids.COL_UNDERLYING_SYMBOL_CHAIN: sym,
                    ids.COL_CURRENT_PRICE_EDP: market_data_payload.get(sym, {}).get("underlying", {}).get(ids.COL_UND_PRICE, 100.0),
                    ids.CV_VOLM_BS_ROLLING_PREFIX + "_5m": -50, ids.CV_VALUE_BS_ROLLING_PREFIX + "_5m": -5000,
                }
            ])
            dummy_processed_data[sym] = {
                "processed_data": {"options_chain": dummy_df.to_dict(orient='records')},
                "final_metric_rich_df_obj": dummy_df,
                "error": f"PROCESSOR_DUMMY_FALLBACK_MSG for {sym}",
                "underlying_data_source": market_data_payload.get(sym, {}).get("underlying", {}),
                "market_context_source": tradier_context_payload.get(sym, {}) if tradier_context_payload else {},
                ids.COL_OPTION_SYMBOL: sym
            }
        return dummy_processed_data

class IntegratedTradingSystemDummy(GenericDummyService):
    def __init__(self, *args, **kwargs): super().__init__("IntegratedTradingSystem", *args, **kwargs)
    def process_market_data_and_generate_recommendations(self,
                                                         symbol: str,
                                                         raw_options_data: pd.DataFrame,
                                                         underlying_data: Dict[str, Any],
                                                         market_context: Dict[str, Any],
                                                         historical_ohlc_data: Optional[pd.DataFrame],
                                                         expiration_calendar: Optional[List[date]]
                                                        ) -> Dict[str, Any]:
        logger.warning(f"CB_Dummy: ITSDummy.process_market_data_and_generate_recommendations called for {symbol}")
        df = raw_options_data if isinstance(raw_options_data, pd.DataFrame) else pd.DataFrame(raw_options_data if isinstance(raw_options_data, list) else [])
        for col in [ids.COL_MSPI_SCORE, ids.COL_SAI, ids.COL_SSI, ids.COL_ARFI,
                    ids.COL_DAG_CUSTOM_NORM, ids.COL_TDPI_NORM, ids.COL_VRI_NORM,
                    ids.COL_SDAG_MULTIPLICATIVE_NORM, ids.COL_SDAG_DIRECTIONAL_NORM,
                    ids.COL_SDAG_WEIGHTED_NORM, ids.COL_SDAG_VOLATILITY_FOCUSED_NORM,
                    ids.COL_CHART_HEURISTIC_NET_DELTA_PRESSURE, ids.COL_CHART_NET_GAMMA_FLOW,
                    ids.COL_CHART_NET_VEGA_FLOW, ids.COL_CHART_NET_THETA_EXPOSURE,
                    ids.COL_CHART_NET_VOLUME_PRESSURE, ids.COL_CHART_NET_VALUE_PRESSURE,
                    ids.COL_STRIKE, ids.COL_OPT_KIND, ids.COL_EXPIRATION_DATE]:
            if col not in df.columns:
                if "norm" in col or "mspi" in col or "sai" in col or "ssi" in col: df[col] = np.random.uniform(-1, 1)
                elif col == ids.COL_STRIKE: df[col] = np.random.randint(50, 150)
                elif col == ids.COL_OPT_KIND: df[col] = np.random.choice(['call', 'put'])
                elif col == ids.COL_EXPIRATION_DATE: df[col] = (date.today() + timedelta(days=np.random.randint(1, 30))).isoformat()
                elif "flow" in col or "pressure" in col: df[col] = np.random.uniform(-100000, 100000)
                else: df[col] = np.nan
        dummy_key_levels = {
            "all_levels_sorted_by_strength": [
                {"level_price": underlying_data.get(ids.COL_UND_PRICE, 100.0) * 0.95, "level_type": "Support", "strength_score": 0.8, "source_metrics": "MSPI,NVP"},
                {"level_price": underlying_data.get(ids.COL_UND_PRICE, 100.0) * 1.05, "level_type": "Resistance", "strength_score": 0.7, "source_metrics": "MSPI,SDAG"},
            ], "support_df": pd.DataFrame(), "resistance_df": pd.DataFrame(), "error": "Dummy Key Levels Data"}
        if not dummy_key_levels["support_df"].empty: dummy_key_levels["support_df"] = dummy_key_levels["support_df"].to_dict(orient='records')
        if not dummy_key_levels["resistance_df"].empty: dummy_key_levels["resistance_df"] = dummy_key_levels["resistance_df"].to_dict(orient='records')
        return {
            ids.COL_OPTION_SYMBOL: symbol, "processed_options_df": df.to_dict(orient='records'),
            "final_metric_rich_df_obj": df, "key_levels": dummy_key_levels,
            "signals": {"directional_signals": [{"type": "Dummy Bullish", "strike": 100.0}], "error": "Dummy Signals Data"},
            "recommendations": [{"id": f"DUMMY_REC_{symbol}", "Category": "Dummy", "strategy": "Dummy Strategy"}],
            "error": f"ITS_Fallback_Data for {symbol}"}

class MSPIVisualizerV2Dummy(GenericDummyService): # Renamed to avoid conflict with real one
    def __init__(self, *args, **kwargs):
        super().__init__("MSPIVisualizerV2_Dummy_Callbacks", *args, **kwargs) # Unique name
        self.config = kwargs.get('config_data', {})
        if not self.config:
            self.config = { # Minimal dummy config for visualizer methods
                "default_chart_height": 600,
                "plotly_template": "plotly_dark",
                "column_names": {
                    "strike": ids.COL_STRIKE, "mspi_score": ids.COL_MSPI_SCORE,
                    "net_volume_pressure": ids.COL_CHART_NET_VOLUME_PRESSURE,
                    "net_value_pressure": ids.COL_CHART_NET_VALUE_PRESSURE,
                    "expiration_date": ids.COL_EXPIRATION_DATE,
                    "option_kind": ids.COL_OPT_KIND
                },
                "greek_flow_heatmap_options": [{'label': 'Dummy Gamma Flow', 'value': ids.COL_CHART_NET_GAMMA_FLOW}],
                "greek_flow_heatmap_default_metric": ids.COL_CHART_NET_GAMMA_FLOW,
                "rolling_intervals": ["5m", "15m"],
                "rolling_flow_chart_options": [{'label': 'Dummy Vol/Val', 'value': 'volmbs'}],
                "rolling_flow_chart_default_option": 'volmbs'
            }
    def _create_empty_figure(self, title="Fallback Chart", height=600, reason="Fallback Visualizer", *args, **kwargs) -> go.Figure:
        fig = go.Figure(); fig.update_layout(title=f"{title} (DUMMY: {reason})", height=height, template="plotly_dark")
        fig.add_annotation(text="Chart unavailable (Dummy Visualizer active or data error)", xref="paper", yref="paper", showarrow=False, font={"size":16, "color":"gray"})
        return fig
    def create_mspi_heatmap(self, *args, **kwargs): return self._create_empty_figure("MSPI Heatmap", reason="Dummy Active")
    def create_net_value_heatmap(self, *args, **kwargs): return self._create_empty_figure("Net Value Heatmap", reason="Dummy Active")
    def create_net_volume_pressure_heatmap(self, *args, **kwargs): return self._create_empty_figure("Net Volume Heatmap", reason="Dummy Active")
    def create_component_comparison(self, *args, **kwargs): return self._create_empty_figure("MSPI Components", reason="Dummy Active")
    def create_time_decay_visualization(self, *args, **kwargs): return self._create_empty_figure("Time Decay", reason="Dummy Active")
    def create_volatility_regime_visualization(self, *args, **kwargs): return self._create_empty_figure("Volatility Regime", reason="Dummy Active")
    def create_combined_rolling_flow_chart(self, *args, **kwargs): return self._create_empty_figure("Rolling Flow", reason="Dummy Active")
    def create_key_levels_visualization(self, *args, **kwargs): return self._create_empty_figure("Key Levels", reason="Dummy Active")
    def create_trading_signals_visualization(self, *args, **kwargs): return self._create_empty_figure("Trading Signals", reason="Dummy Active")
    def create_strategy_recommendations_table(self, *args, **kwargs): return self._create_empty_figure("Recommendations Table", reason="Dummy Active")
    def create_net_greek_flow_heatmap(self, *args, **kwargs): return self._create_empty_figure("Net Greek Flow", reason="Dummy Active")
    def plot_sdag_multiplicative(self, *args, **kwargs): return self._create_empty_figure("SDAG Multiplicative", reason="Dummy Active")
    def plot_sdag_directional(self, *args, **kwargs): return self._create_empty_figure("SDAG Directional", reason="Dummy Active")
    def plot_sdag_weighted(self, *args, **kwargs): return self._create_empty_figure("SDAG Weighted", reason="Dummy Active")
    def plot_sdag_volatility_focused(self, *args, **kwargs): return self._create_empty_figure("SDAG Volatility Focused", reason="Dummy Active")


# --- Module-level references (globals for this module) ---
_CALLBACKS_CV_FETCHER: Any = None
_CALLBACKS_TRADIER_FETCHER: Any = None
_CALLBACKS_PROCESSOR: Any = None
_CALLBACKS_ITS: Any = None
_CALLBACKS_VISUALIZER: Any = None
_CALLBACKS_APP_CONFIG: Optional[Dict[str, Any]] = None
_CALLBACKS_SERVER_CACHE: Optional[Dict[str, Tuple[float, Dict[str, Any]]]] = None
_CALLBACKS_COMPONENT_HISTORY: Optional[Dict[str, Deque[Tuple[float, pd.DataFrame]]]] = None

def _generate_cache_key_default(symbol: str, dte_str: str, range_pct: float, refresh_interval: int) -> str:
    range_pct_str = f"{range_pct:.2f}"
    key_parts = [
        str(symbol).strip().upper() if symbol else "NOSYMBOL",
        str(dte_str).strip() if dte_str else "NODTE",
        str(range_pct_str).strip() if range_pct_str else "NORANGE",
        str(refresh_interval).strip() if refresh_interval is not None else "NOREFRESH"
    ]
    valid_parts = [part for part in key_parts if part]
    if not valid_parts: return "INVALID_CACHE_KEY_PARAMS"
    return "_".join(valid_parts)

def _get_data_summary_for_log(data_obj: Any, name: str) -> str:
    if isinstance(data_obj, pd.DataFrame): return f"{name}(DataFrame Shape: {data_obj.shape})"
    elif isinstance(data_obj, dict): return f"{name}(Dict Keys: {list(data_obj.keys())}, Items: {len(data_obj)})"
    elif isinstance(data_obj, list): return f"{name}(List Length: {len(data_obj)})"
    elif data_obj is None: return f"{name}(None)"
    else: return f"{name}(Type: {type(data_obj).__name__}, Value: {str(data_obj)[:50]})"

# --- Callback Registration Function ---
def register_callbacks(
    app_instance: dash.Dash,
    cv_fetcher_instance: Any,
    tradier_fetcher_instance: Any,
    processor_instance: Any,
    its_instance: Any,
    visualizer_instance: Any,
    server_cache_ref: Dict[str, Tuple[float, Dict[str, Any]]],
    component_history_ref: Dict[str, Deque[Tuple[float, pd.DataFrame]]],
    application_config: Dict[str, Any]
):
    reg_cb_logger = logging.getLogger("RegisterCallbacks_V3.0.9_IDS_Rewrite") # More specific logger
    reg_cb_logger.info("Registering dashboard callbacks (V3.0.9 IDS Rewrite - Enhanced Logging Focus)...")

    global _CALLBACKS_CV_FETCHER, _CALLBACKS_TRADIER_FETCHER, _CALLBACKS_PROCESSOR, \
           _CALLBACKS_ITS, _CALLBACKS_VISUALIZER, _CALLBACKS_APP_CONFIG, \
           _CALLBACKS_SERVER_CACHE, _CALLBACKS_COMPONENT_HISTORY

    _CALLBACKS_CV_FETCHER = cv_fetcher_instance # No longer instantiating dummies here, just using passed instances
    _CALLBACKS_TRADIER_FETCHER = tradier_fetcher_instance
    _CALLBACKS_PROCESSOR = processor_instance
    _CALLBACKS_ITS = its_instance
    _CALLBACKS_VISUALIZER = visualizer_instance
    _CALLBACKS_APP_CONFIG = application_config
    _CALLBACKS_SERVER_CACHE = server_cache_ref
    _CALLBACKS_COMPONENT_HISTORY = component_history_ref
    
    reg_cb_logger.info(f"  Callback System Using: CVF={type(_CALLBACKS_CV_FETCHER).__name__}, TRF={type(_CALLBACKS_TRADIER_FETCHER).__name__}, PROC={type(_CALLBACKS_PROCESSOR).__name__}, ITS={type(_CALLBACKS_ITS).__name__}, VIZ={type(_CALLBACKS_VISUALIZER).__name__}")
    if not _core_utils_layout_styling_imported_ok:
        reg_cb_logger.error("Core local modules (.utils, .layout, .styling) had import issues. Callbacks might not function as expected.")

    # --- Callback for Initial Data Load ---
    @app_instance.callback(
        Output(ids.ID_HIDDEN_INITIAL_LOAD_TRIGGER, 'children'), # Use ID constant
        Input(ids.ID_APP_CONFIG_STORE, 'data'), # Use ID constant
        prevent_initial_call=False
    )
    def trigger_initial_load_via_hidden_div(app_config_data: Optional[Dict]) -> str:
        initial_load_trigger_logger = logging.getLogger("InitialLoadTriggerCallback_V3.0.9_IDS_Rewrite")
        if app_config_data is not None:
            timestamp_trigger = f"InitialLoadTriggered_CallbacksV309_{datetime.now().isoformat()}"
            initial_load_trigger_logger.info(f"App config loaded. Orchestration Trigger: {timestamp_trigger}")
            return timestamp_trigger
        initial_load_trigger_logger.debug("App config not yet available for initial load trigger.")
        return no_update # type: ignore

    # --- Main Data Orchestration Callback ---
    @app_instance.callback(
        Output(ids.ID_MAIN_DATA_STORE_MEMORY, 'data'), # Use ID constant
        Output(ids.ID_STATUS_DISPLAY_AREA, 'children'), # Use ID constant
        Output(ids.ID_ALERT_CONTAINER, 'children'), # Use ID constant
        Output(ids.ID_OVERLAY_LOADING, 'children'), # Use ID constant
        Input(ids.ID_FETCH_DATA_BUTTON, 'n_clicks'), # Use ID constant
        Input(ids.ID_AUTO_REFRESH_INTERVAL_COMPONENT, 'n_intervals'), # Use ID constant
        Input(ids.ID_HIDDEN_INITIAL_LOAD_TRIGGER, 'children'), # Use ID constant
        State(ids.ID_SYMBOL_INPUT, 'value'), State(ids.ID_DTE_INPUT, 'value'), # Use ID constants
        State(ids.ID_RANGE_SLIDER, 'value'), State(ids.ID_REFRESH_INTERVAL_DROPDOWN, 'value'), # Use ID constants
        prevent_initial_call=True # Prevent initial on app load before hidden div triggers it
    )
    def orchestrate_data_fetch_and_process(
        n_clicks: Optional[int], n_intervals: Optional[int], initial_load_trigger_val: Optional[str],
        symbol_input: Optional[str], dte_input: Optional[str],
        range_percentage_input: Optional[float], refresh_interval_ms: Optional[int]
    ) -> Tuple[Any, Any, Any, Any]:
        orch_logger = logging.getLogger("OrchestrateDataFetchProcess_V3.0.9_IDS_Rewrite")
        orch_logger.info(f"--- ORCHESTRATION START (V3.0.9 IDS Rewrite) ---")
        orch_logger.debug(f"  Inputs: n_clicks={n_clicks}, n_intervals={n_intervals}, initial_trigger_val='{initial_load_trigger_val}', "
                          f"symbol='{symbol_input}', dte='{dte_input}', range%={range_percentage_input}, refresh_ms={refresh_interval_ms}")

        cache_key_to_store: Any = no_update
        status_message_div: Any = no_update
        alert_div_children: List[Any] = []
        loading_overlay_children: Any = no_update # Initially no overlay

        # Determine Trigger
        triggered_input_id_str = 'unknown_trigger_orchestration'
        actual_trigger_is_initial_load_orch = False
        actual_trigger_is_button_click_orch = False
        actual_trigger_is_timer_action_orch = False

        try:
            if dash_ctx.triggered and isinstance(dash_ctx.triggered, list) and len(dash_ctx.triggered) > 0:
                first_trigger_info_orch = dash_ctx.triggered[0]
                if isinstance(first_trigger_info_orch, dict) and 'prop_id' in first_trigger_info_orch and isinstance(first_trigger_info_orch['prop_id'], str):
                    triggered_input_id_str = first_trigger_info_orch['prop_id'].split('.')[0]
            orch_logger.info(f"  Trigger Evaluation: Component that fired (from dash_ctx.triggered): '{triggered_input_id_str}'")

            if triggered_input_id_str == ids.ID_HIDDEN_INITIAL_LOAD_TRIGGER and initial_load_trigger_val and "InitialLoadTriggered_" in initial_load_trigger_val:
                actual_trigger_is_initial_load_orch = True
                orch_logger.info(f"  Trigger Type: INITIAL_LOAD (via {ids.ID_HIDDEN_INITIAL_LOAD_TRIGGER} value '{initial_load_trigger_val}')")
            elif triggered_input_id_str == ids.ID_FETCH_DATA_BUTTON and n_clicks is not None and n_clicks > 0:
                actual_trigger_is_button_click_orch = True
                orch_logger.info(f"  Trigger Type: BUTTON_CLICK (n_clicks={n_clicks})")
            elif triggered_input_id_str == ids.ID_AUTO_REFRESH_INTERVAL_COMPONENT and refresh_interval_ms is not None and refresh_interval_ms > 0:
                actual_trigger_is_timer_action_orch = True
                orch_logger.info(f"  Trigger Type: TIMER_ACTION (n_intervals={n_intervals})")
            else: # Fallback for cases where dash_ctx.triggered might not be as expected for initial load
                if initial_load_trigger_val and "InitialLoadTriggered_" in initial_load_trigger_val and not (actual_trigger_is_button_click_orch or actual_trigger_is_timer_action_orch):
                    actual_trigger_is_initial_load_orch = True
                    orch_logger.info(f"  Trigger Type (Fallback Check): INITIAL_LOAD (based on initial_load_trigger_val='{initial_load_trigger_val}' and no other primary trigger)")


            if not (actual_trigger_is_initial_load_orch or actual_trigger_is_button_click_orch or actual_trigger_is_timer_action_orch):
                orch_logger.info("  No valid trigger for data fetch. Exiting orchestration early.")
                return no_update, format_status_message("Idle. Select parameters and click 'Fetch Data' or wait for refresh.", False), [], no_update
            orch_logger.debug(f"  Valid Trigger Confirmed: Initial={actual_trigger_is_initial_load_orch}, Button={actual_trigger_is_button_click_orch}, Timer={actual_trigger_is_timer_action_orch}")

        except Exception as e_trigger_eval:
            error_msg_trigger = f"Critical error during trigger evaluation: {type(e_trigger_eval).__name__} - {str(e_trigger_eval)}"
            orch_logger.critical(error_msg_trigger, exc_info=True)
            alert_div_children = [dbc.Alert(html.Pre(error_msg_trigger), color="danger", duration=None, dismissable=True, className="mt-2")]
            return no_update, format_status_message(error_msg_trigger, True), alert_div_children, no_update # type: ignore

        # Proceed with data fetch if a valid trigger occurred
        loading_overlay_children = html.Div(dbc.Spinner(size="xl", color="info", fullscreen=True, delay_show=100, delay_hide=100), id="main-orch-spinner-dynamic-v309")
        status_message_div = format_status_message(f"Fetching & Processing Market Data for {symbol_input or 'N/A'}...", False, timestamp=datetime.now())
        orch_logger.debug("  Loading overlay and initial status message set for active data processing.")

        if not (symbol_input and isinstance(symbol_input, str) and
                dte_input and isinstance(dte_input, str) and
                range_percentage_input is not None):
            err_msg_inputs = "Symbol, DTE, and Strike Range % are required."
            orch_logger.error(f"  Input validation failed: {err_msg_inputs}. Inputs: sym='{symbol_input}', dte='{dte_input}', range%={range_percentage_input}")
            alert_div_children = [dbc.Alert(err_msg_inputs, color="warning", duration=5000, dismissable=True, className="mt-2")]
            return no_update, format_status_message(err_msg_inputs, True), alert_div_children, no_update # type: ignore
        orch_logger.debug(f"  Passed main input validation (Symbol, DTE, Range%).")

        symbol_clean = symbol_input.strip().upper()
        dte_str_clean = dte_input.strip()
        selected_dtes_list = parse_dte_input_string(dte_str_clean) # from .utils

        orch_logger.info(f"  Parameters for this run: Symbol='{symbol_clean}', DTE_String='{dte_str_clean}', ParsedDTEs={selected_dtes_list}, Range%={range_percentage_input:.2f}, RefreshIntervalMS={refresh_interval_ms or 0}")

        if selected_dtes_list is None:
            err_msg_dte = f"Invalid DTE format: '{dte_str_clean}'. Use single (0), range (0-7), or list (0,1,7)."
            orch_logger.error(f"  DTE parsing error: {err_msg_dte}")
            alert_div_children = [dbc.Alert(err_msg_dte, color="danger", duration=6000, dismissable=True, className="mt-2")]
            return no_update, format_status_message(err_msg_dte, True), alert_div_children, no_update # type: ignore
        
        cache_key = _generate_cache_key_default(symbol_clean, dte_str_clean, range_percentage_input, refresh_interval_ms or 0)
        orch_logger.info(f"  Generated CacheKey: '{cache_key}'")
        
        # Initialize local copies of global service instances and config
        cv_fetcher = _CALLBACKS_CV_FETCHER
        tradier_fetcher = _CALLBACKS_TRADIER_FETCHER
        processor = _CALLBACKS_PROCESSOR
        its = _CALLBACKS_ITS
        app_cfg_orch = _CALLBACKS_APP_CONFIG

        if not all([cv_fetcher, tradier_fetcher, processor, its, app_cfg_orch]):
            crit_err_services = "One or more backend services or app_config is None in callbacks module."
            orch_logger.critical(crit_err_services)
            alert_div_children = [dbc.Alert(html.Pre(crit_err_services), color="danger", duration=None, dismissable=True)]
            return no_update, format_status_message(crit_err_services, True), alert_div_children, no_update # type: ignore
        
        # Use ids.CFG_... constants for fetching config
        cv_und_params_fetch = get_config_value(ids.CFG_CV_UND_PARAMS_TO_FETCH, [], app_cfg_orch)
        cv_opt_params_fetch = get_config_value(ids.CFG_CV_OPT_PARAMS_TO_FETCH, [], app_cfg_orch)
        ohlcv_days_tradier_fetch = get_config_value(ids.CFG_TRADIER_OHLCV_NUM_DAYS_HISTORY_DEFAULT, 90, app_cfg_orch)
        iv_dte_target_tradier_fetch = get_config_value(ids.CFG_TRADIER_IV_APPROX_TARGET_DTE_DEFAULT, 5, app_cfg_orch)
        orch_logger.debug(f"  Fetcher Params: CV Und {len(cv_und_params_fetch)}, CV Opt {len(cv_opt_params_fetch)}, Tradier OHLCV Days {ohlcv_days_tradier_fetch}, Tradier IV DTE {iv_dte_target_tradier_fetch}")

        # Use ids.COL_UND_PRICE and ids.COL_UND_FETCH_TIMESTAMP
        current_cv_underlying_info_orch = {ids.COL_OPTION_SYMBOL: symbol_clean, ids.COL_UND_PRICE: None, "error": "CV underlying data not yet fetched", ids.COL_UND_FETCH_TIMESTAMP: datetime.now().isoformat()}

        try:
            orch_logger.info(f"  [{symbol_clean}] CV Fetch START. DTEs: {selected_dtes_list}, Range%={range_percentage_input:.2f}")
            cv_fetch_start_time = datetime.now()
            cv_bundle_data_orch = cv_fetcher.fetch_market_data_bundle(
                symbols=[symbol_clean], dte_list=selected_dtes_list, price_range_percentage=range_percentage_input
            )
            cv_fetch_duration_orch = (datetime.now() - cv_fetch_start_time).total_seconds()
            orch_logger.info(f"  [{symbol_clean}] CV Fetch END. Duration: {cv_fetch_duration_orch:.3f}s. ResponseSummary: {_get_data_summary_for_log(cv_bundle_data_orch, 'CV_Bundle')}")

            cv_sym_data_orch = cv_bundle_data_orch.get(symbol_clean, {"error": f"Symbol '{symbol_clean}' not found in CV bundle."}) if isinstance(cv_bundle_data_orch, dict) else {"error": "CV bundle invalid type."}
            if cv_sym_data_orch.get('error'): raise RuntimeError(f"ConvexValue Fetch Error for {symbol_clean}: {cv_sym_data_orch['error']}")
            
            cv_options_df_orch = cv_sym_data_orch.get('options_chain')
            current_cv_underlying_info_orch = cv_sym_data_orch.get('underlying', current_cv_underlying_info_orch)
            # Use ids.COL_UND_PRICE for checking price presence
            if not (isinstance(cv_options_df_orch, pd.DataFrame) and not cv_options_df_orch.empty and isinstance(current_cv_underlying_info_orch, dict) and current_cv_underlying_info_orch.get(ids.COL_UND_PRICE) is not None):
                raise ValueError(f"CV data for {symbol_clean} incomplete after fetch.")
            orch_logger.info(f"  [{symbol_clean}] CV Data OK. UnderlyingPrice: {current_cv_underlying_info_orch.get(ids.COL_UND_PRICE)}")

            orch_logger.info(f"  [{symbol_clean}] Tradier Fetch START. OHLCVDays: {ohlcv_days_tradier_fetch}, IV_DTE_Target: {iv_dte_target_tradier_fetch}")
            tradier_fetch_start_time = datetime.now()
            tradier_bundle_data_orch = tradier_fetcher.fetch_market_data_bundle(
                symbols=[symbol_clean], ohlcv_days=ohlcv_days_tradier_fetch, iv_approx_dte=iv_dte_target_tradier_fetch
            )
            tradier_fetch_duration_orch = (datetime.now() - tradier_fetch_start_time).total_seconds()
            orch_logger.info(f"  [{symbol_clean}] Tradier Fetch END. Duration: {tradier_fetch_duration_orch:.3f}s. ResponseSummary: {_get_data_summary_for_log(tradier_bundle_data_orch, 'Tradier_Bundle')}")
            tradier_sym_data_orch = tradier_bundle_data_orch.get(symbol_clean, {"error": f"Symbol '{symbol_clean}' missing from Tradier bundle."}) if isinstance(tradier_bundle_data_orch, dict) else {"error": "Tradier bundle invalid type."}
            if tradier_sym_data_orch.get("error"): orch_logger.warning(f"  [{symbol_clean}] Tradier Fetch Warning/Error: {tradier_sym_data_orch['error']}")
            current_exp_cal_orch = tradier_sym_data_orch.get("expiration_calendar")

            orch_logger.info(f"  [{symbol_clean}] EDP Processing START.")
            proc_market_data = {symbol_clean: cv_sym_data_orch}
            proc_tradier_ctx = {symbol_clean: tradier_sym_data_orch} if tradier_sym_data_orch and not tradier_sym_data_orch.get("error") else None
            proc_exp_cal = {symbol_clean: current_exp_cal_orch} if current_exp_cal_orch else None
            processor_start_time = datetime.now()
            processed_map_result_orch = processor.process_market_data_bundle(
                market_data_payload=proc_market_data, tradier_context_payload=proc_tradier_ctx, expiration_calendars_payload=proc_exp_cal
            )
            processor_duration_orch = (datetime.now() - processor_start_time).total_seconds()
            orch_logger.info(f"  [{symbol_clean}] EDP Processing END. Duration: {processor_duration_orch:.3f}s. ResultSummary: {_get_data_summary_for_log(processed_map_result_orch, 'EDP_ResultMap')}")
            processed_data_bundle_orch = processed_map_result_orch.get(symbol_clean) if isinstance(processed_map_result_orch, dict) else None
            if not processed_data_bundle_orch or processed_data_bundle_orch.get('error'):
                raise RuntimeError(f"EnhancedDataProcessor Error for {symbol_clean}: {processed_data_bundle_orch.get('error', 'No bundle returned')}")

            its_input_df_orch = pd.DataFrame()
            final_metrics_df_from_proc_orch = processed_data_bundle_orch.get("final_metric_rich_df_obj")
            if isinstance(final_metrics_df_from_proc_orch, pd.DataFrame): its_input_df_orch = final_metrics_df_from_proc_orch
            elif isinstance(processed_data_bundle_orch.get("processed_options_df"), list):
                processed_opts_list_orch = processed_data_bundle_orch.get("processed_options_df", [])
                if processed_opts_list_orch: its_input_df_orch = pd.DataFrame(processed_opts_list_orch)
            
            orch_logger.info(f"  [{symbol_clean}] ITS Analysis START. {_get_data_summary_for_log(its_input_df_orch, 'ITS_InputDF')}")
            its_market_ctx_orch = {
                "current_time": get_current_time_from_component_id(triggered_input_id_str),
                # Use ids.COL_TRADIER_IV_APPROX_PREFIX
                "current_iv": tradier_sym_data_orch.get("iv_and_quote_data", {}).get(f"{ids.COL_TRADIER_IV_APPROX_PREFIX}{iv_dte_target_tradier_fetch}_approx_smv_avg", current_cv_underlying_info_orch.get(ids.CV_UND_PARAM_VOLATILITY)),
                "iv_and_quote_data": tradier_sym_data_orch.get("iv_and_quote_data", {}),
            }
            its_start_time = datetime.now()
            its_final_bundle_orch = its.process_market_data_and_generate_recommendations(
                symbol=symbol_clean, raw_options_data=its_input_df_orch,
                underlying_data=current_cv_underlying_info_orch, market_context=its_market_ctx_orch,
                historical_ohlc_data=tradier_sym_data_orch.get("historical_ohlcv_df"), expiration_calendar=current_exp_cal_orch
            )
            its_duration_orch = (datetime.now() - its_start_time).total_seconds()
            orch_logger.info(f"  [{symbol_clean}] ITS Analysis END. Duration: {its_duration_orch:.3f}s. ResultSummary: {_get_data_summary_for_log(its_final_bundle_orch, 'ITS_Bundle')}")
            if not its_final_bundle_orch or its_final_bundle_orch.get('error'):
                raise RuntimeError(f"ITS Error for {symbol_clean}: {its_final_bundle_orch.get('error', 'No ITS bundle')}")

            orch_logger.info(f"  [{symbol_clean}] Caching START. Key='{cache_key}'.")
            set_cached_data_bundle(cache_key, its_final_bundle_orch, _CALLBACKS_SERVER_CACHE) # type: ignore
            cache_key_to_store = cache_key

            df_hist_update = its_final_bundle_orch.get('final_metric_rich_df_obj', pd.DataFrame())
            fetch_ts_hist = current_cv_underlying_info_orch.get(ids.COL_UND_FETCH_TIMESTAMP, datetime.now().isoformat())
            orch_logger.info(f"  [{symbol_clean}] Updating Component History. {_get_data_summary_for_log(df_hist_update, 'DFHist')}, TS: {fetch_ts_hist}")
            update_data_bundle_history_for_symbol(symbol_clean, df_hist_update, fetch_ts_hist, _CALLBACKS_COMPONENT_HISTORY) # type: ignore

            final_status_text = f"Data processed for {symbol_clean} at {datetime.now().strftime('%H:%M:%S')}. Errors: {its_final_bundle_orch.get('error', 'None')}"
            status_message_div = format_status_message(final_status_text, bool(its_final_bundle_orch.get('error')), timestamp=datetime.now())
            orch_logger.info(f"--- ORCHESTRATION END ({symbol_clean}) - SUCCESS ---")
            return cache_key_to_store, status_message_div, [], no_update # type: ignore

        except Exception as e_orch_main_fatal:
            err_trace_fatal = traceback.format_exc()
            sym_err_ctx = symbol_clean if 'symbol_clean' in locals() and symbol_clean else (symbol_input or "N/A_SYM_FATAL")
            short_err_msg_fatal = f"Orchestration Critical Failure ({sym_err_ctx}): {type(e_orch_main_fatal).__name__} - {str(e_orch_main_fatal)[:200]}"
            orch_logger.critical(f"{short_err_msg_fatal}\nFull Traceback:\n{err_trace_fatal}")
            alert_children_fatal = [dbc.Alert(html.Pre(f"{short_err_msg_fatal}\n{err_trace_fatal}"), color="danger", duration=None, dismissable=True)]
            status_msg_fatal = format_status_message(short_err_msg_fatal, True, timestamp=datetime.now())
            
            cache_key_err = cache_key if 'cache_key' in locals() and cache_key else _generate_cache_key_default(sym_err_ctx, dte_input or "ERR_DTE", range_percentage_input or 0.0, refresh_interval_ms or 0)
            error_bundle_cache = {
                ids.COL_OPTION_SYMBOL: sym_err_ctx, "error": short_err_msg_fatal, "traceback": err_trace_fatal,
                "processed_options_df": [], "final_metric_rich_df_obj": pd.DataFrame(), # Ensure this key exists for safety
                "underlying_data": current_cv_underlying_info_orch if 'current_cv_underlying_info_orch' in locals() else {"error":"Data unavailable"},
                "last_updated_iso": datetime.now().isoformat()
            }
            orch_logger.info(f"  Storing ERROR bundle to cache. Key='{cache_key_err}'.")
            if _CALLBACKS_SERVER_CACHE is not None: set_cached_data_bundle(cache_key_err, error_bundle_cache, _CALLBACKS_SERVER_CACHE)
            else: orch_logger.error("  _CALLBACKS_SERVER_CACHE is None! Cannot store error bundle.")
            
            return cache_key_err, status_msg_fatal, alert_children_fatal, no_update # type: ignore

    # --- Chart Update Factory ---
    def create_chart_update_callback_factory(
        chart_id_param: str, chart_method_name_param: str,
        requires_range_slider: bool = False, requires_greek_mspi_selector: bool = False,
        requires_rolling_flow_selector: bool = False, requires_figure_state: bool = False
    ):
        # NOTE: Using a more detailed logger name format for easier filtering
        chart_factory_cb_logger = logging.getLogger(f"ChartFactory.{chart_id_param.replace('-', '_')}.V3_0_9_IDS_Integrated")

        # Define inputs based on requirements
        callback_inputs = [Input(ids.ID_MAIN_DATA_STORE_MEMORY, 'data')] # Use ID constant
        if requires_range_slider:
            callback_inputs.append(Input(ids.ID_RANGE_SLIDER, 'value')) # Use ID constant
            chart_factory_cb_logger.debug(f"Factory for '{chart_id_param}': REQUIRES range_slider INPUT.")
        else:
            callback_inputs.append(State(ids.ID_RANGE_SLIDER, 'value')) # Use ID constant
            chart_factory_cb_logger.debug(f"Factory for '{chart_id_param}': State for range_slider.")

        if requires_greek_mspi_selector:
            callback_inputs.append(Input(ids.ID_NET_GREEK_FLOW_SELECTOR, 'value')) # Use ID constant
            chart_factory_cb_logger.debug(f"Factory for '{chart_id_param}': REQUIRES greek_mspi_selector INPUT.")
        else:
            callback_inputs.append(State(ids.ID_NET_GREEK_FLOW_SELECTOR, 'value')) # Use ID constant
            chart_factory_cb_logger.debug(f"Factory for '{chart_id_param}': State for greek_mspi_selector.")

        if requires_rolling_flow_selector:
            callback_inputs.append(Input(ids.ID_ROLLING_FLOW_SELECTOR, 'value')) # Use ID constant
            chart_factory_cb_logger.debug(f"Factory for '{chart_id_param}': REQUIRES rolling_flow_selector INPUT.")
        else:
            callback_inputs.append(State(ids.ID_ROLLING_FLOW_SELECTOR, 'value')) # Use ID constant
            chart_factory_cb_logger.debug(f"Factory for '{chart_id_param}': State for rolling_flow_selector.")

        callback_inputs.extend([State(ids.ID_SYMBOL_INPUT, 'value'), State(ids.ID_DTE_INPUT, 'value')]) # Use ID constants

        if requires_figure_state:
            callback_inputs.append(Input(chart_id_param, 'figure')) # Current figure state
            chart_factory_cb_logger.debug(f"Factory for '{chart_id_param}': REQUIRES figure_state INPUT.")
        else:
            callback_inputs.append(State(ids.ID_FETCH_DATA_BUTTON, 'n_clicks')) # Dummy state for consistent arg count, Use ID constant
            chart_factory_cb_logger.debug(f"Factory for '{chart_id_param}': State for fetch_button_n_clicks (placeholder).")

        chart_factory_cb_logger.debug(f"Factory created for '{chart_id_param}'. Method to call: '{chart_method_name_param}'. Inputs: RangeSlider(Input={requires_range_slider}), GreekSel(Input={requires_greek_mspi_selector}), RollSel(Input={requires_rolling_flow_selector}), FigState(Input={requires_figure_state})")

        @app_instance.callback(Output(chart_id_param, 'figure'), *callback_inputs, prevent_initial_call=True)
        def update_chart_dynamically_generated(*callback_args):
            # Log entry point of the callback execution
            chart_factory_cb_logger.info(f"--- CHART UPDATE START for '{chart_id_param}' (Method: {chart_method_name_param}) ---")

            try:
                cache_key_store_val, range_slider_val, greek_sel_val, roll_sel_val, sym_state_val, dte_state_val, fig_state_or_nclicks_val = callback_args
                chart_factory_cb_logger.debug(f"  Args Received: key='{cache_key_store_val}', range={range_slider_val}, greek='{greek_sel_val}', roll='{roll_sel_val}', sym='{sym_state_val}', dte='{dte_state_val}', fig/n_clicks type='{type(fig_state_or_nclicks_val).__name__}'")
            except Exception as e_unpack_chart_args:
                chart_factory_cb_logger.error(f"  ERROR unpacking chart args for '{chart_id_param}': {e_unpack_chart_args}", exc_info=True)
                return create_empty_figure(title=f"Err: {chart_id_param.replace('-', ' ').title()}", reason="Arg Unpack Error")

            triggered_id_chart = dash_ctx.triggered_id if dash_ctx.triggered_id else 'initial_or_programmatic_chart_update'
            chart_factory_cb_logger.info(f"  Triggered by: '{triggered_id_chart}'. Cache Key from Store: '{cache_key_store_val or 'None'}'")

            visualizer_inst = _CALLBACKS_VISUALIZER
            app_cfg_chart_cb = _CALLBACKS_APP_CONFIG
            server_cache_cb = _CALLBACKS_SERVER_CACHE

            if not all([visualizer_inst, app_cfg_chart_cb, server_cache_cb]):
                chart_factory_cb_logger.critical("  CRITICAL: Backend instances None in chart callback. Cannot proceed.")
                return create_empty_figure(title=f"Err: {chart_id_param.replace('-', ' ').title()}", reason="Backend Missing")
            
            # Use ids.CFG_VIZ_MSPI_VISUALIZER to get visualizer config
            viz_cfg_chart = getattr(visualizer_inst, 'config', get_config_value(ids.CFG_VIZ_MSPI_VISUALIZER, {}, app_cfg_chart_cb))
            def_height_chart = int(viz_cfg_chart.get("default_chart_height", 600))
            chart_title_empty = chart_id_param.replace('-', ' ').title()

            if not (cache_key_store_val and isinstance(cache_key_store_val, str)):
                chart_factory_cb_logger.warning(f"  No valid cache key ('{cache_key_store_val}'). Returning empty for '{chart_title_empty}'.")
                return create_empty_figure(title=f"{chart_title_empty} (No Cache Key)", height=def_height_chart, reason=f"Cache key invalid or '{triggered_id_chart}'")
            
            its_bundle = get_cached_data_bundle(cache_key_store_val, server_cache_cb) # type: ignore
            if its_bundle is None:
                chart_factory_cb_logger.warning(f"  CACHE MISS for '{cache_key_store_val}'. Empty fig for '{chart_title_empty}'.")
                return create_empty_figure(title=f"{chart_title_empty} (Cache Miss)", height=def_height_chart, reason=f"Cache miss for '{cache_key_store_val}'")
            
            bundle_err = its_bundle.get("error")
            if bundle_err:
                chart_factory_cb_logger.error(f"  Bundle for '{cache_key_store_val}' has ERROR: '{bundle_err}'. Traceback: {its_bundle.get('traceback')}")
                return create_empty_figure(title=f"{chart_title_empty} (Data Bundle Error)", height=def_height_chart, reason=str(bundle_err)[:150])

            df_plot_obj = its_bundle.get('final_metric_rich_df_obj')
            df_plot_records = its_bundle.get("processed_options_df", [])

            df_plot_final: pd.DataFrame
            if isinstance(df_plot_obj, pd.DataFrame): df_plot_final = df_plot_obj
            elif isinstance(df_plot_records, list) and df_plot_records: df_plot_final = pd.DataFrame(df_plot_records)
            else: df_plot_final = pd.DataFrame()
            chart_factory_cb_logger.info(f"  DataFrame for plotting ('df_plot_final') ready. Shape: {df_plot_final.shape}. Is empty: {df_plot_final.empty}")
            if not df_plot_final.empty: chart_factory_cb_logger.debug(f"    Columns: {df_plot_final.columns.tolist()}")

            # Enhanced column inspection logging
            if not df_plot_final.empty:
                # Use ids.CFG_VIZ_COL_NAMES for column name lookups
                viz_col_names_cfg = get_config_value(ids.CFG_VIZ_COL_NAMES, {}, app_cfg_chart_cb)
                critical_chart_cols = [ # This list should be comprehensive for your charts
                    viz_col_names_cfg.get("strike", ids.COL_STRIKE),
                    viz_col_names_cfg.get("mspi_score", ids.COL_MSPI_SCORE),
                    viz_col_names_cfg.get("option_kind", ids.COL_OPT_KIND),
                    viz_col_names_cfg.get("expiration_date", ids.COL_EXPIRATION_DATE),
                    ids.COL_DAG_CUSTOM_NORM, ids.COL_TDPI_NORM, ids.COL_VRI_NORM,
                    ids.COL_SDAG_MULTIPLICATIVE_NORM, ids.COL_SDAG_DIRECTIONAL_NORM,
                    ids.COL_SDAG_WEIGHTED_NORM, ids.COL_SDAG_VOLATILITY_FOCUSED_NORM,
                    # Renamed heuristic pressures
                    ids.COL_CHART_NET_VOLUME_PRESSURE, ids.COL_CHART_NET_VALUE_PRESSURE,
                    ids.COL_CHART_HEURISTIC_NET_DELTA_PRESSURE,
                    ids.COL_CHART_NET_GAMMA_FLOW, ids.COL_CHART_NET_VEGA_FLOW, ids.COL_CHART_NET_THETA_EXPOSURE
                ]
                for col_inspect in list(set(critical_chart_cols)): # Use set to remove duplicates
                    if col_inspect in df_plot_final.columns:
                        chart_factory_cb_logger.debug(f"    DF Data Check: Col '{col_inspect}' - Present. Non-NaN: {df_plot_final[col_inspect].notna().sum()}/{len(df_plot_final)}. Dtype: {df_plot_final[col_inspect].dtype}. Sample: {df_plot_final[col_inspect].head(2).tolist()}")
                    else:
                        chart_factory_cb_logger.warning(f"    DF Data Check: Col '{col_inspect}' - MISSING in df_plot_final for chart '{chart_id_param}'.")
            else:
                 chart_factory_cb_logger.warning(f"  'df_plot_final' is EMPTY for chart '{chart_id_param}'.")

            # Check if dataframe is empty, handle tables differently
            if df_plot_final.empty and chart_id_param not in [ids.ID_CHART_RECOMMENDATIONS_TABLE]:
                chart_factory_cb_logger.warning(f"  df_plot_final empty. Returning empty fig for '{chart_title_empty}'.")
                return create_empty_figure(title=f"{chart_title_empty} (Empty Data)", height=def_height_chart, reason="Processed DF empty")

            chart_method = getattr(visualizer_inst, chart_method_name_param, None)
            if not callable(chart_method):
                chart_factory_cb_logger.error(f"  Visualizer method '{chart_method_name_param}' not found/callable. Empty fig for '{chart_title_empty}'.")
                return create_empty_figure(title=f"Err: {chart_title_empty} (Viz Logic Error)", height=def_height_chart, reason=f"Method '{chart_method_name_param}' error")
            
            kwargs_for_chart: Dict[str, Any] = {
                ids.COL_OPTION_SYMBOL: sym_state_val, # Use ID constant
                ids.COL_CURRENT_PRICE_EDP: its_bundle.get('underlying_data_source', {}).get(ids.COL_UND_PRICE), # Use ID constant
                ids.COL_UND_FETCH_TIMESTAMP: its_bundle.get('underlying_data_source', {}).get(ids.COL_UND_FETCH_TIMESTAMP) # Use ID constant
            }
            # Populate kwargs based on chart type
            if chart_id_param == ids.ID_CHART_KEY_LEVELS:
                key_lvls_raw = its_bundle.get('processed_data', {}).get('key_levels', {}).get('all_levels_sorted_by_strength', [])
                kwargs_for_chart["key_levels_data"] = pd.DataFrame(key_lvls_raw) if isinstance(key_lvls_raw, list) else pd.DataFrame()
                kwargs_for_chart["base_metric_data_for_line"] = df_plot_final
            elif chart_id_param == ids.ID_CHART_TRADING_SIGNALS:
                kwargs_for_chart["trading_signals_data"] = df_plot_final
                kwargs_for_chart["raw_signal_events"] = its_bundle.get('processed_data', {}).get('signals', {})
            elif chart_id_param == ids.ID_CHART_RECOMMENDATIONS_TABLE:
                kwargs_for_chart["recommendations_list"] = its_bundle.get('processed_data', {}).get('recommendations', [])
            else: # Default for most charts
                kwargs_for_chart["processed_data"] = df_plot_final

            if requires_range_slider: kwargs_for_chart["selected_price_range_pct_override"] = range_slider_val
            
            if chart_id_param == ids.ID_CHART_NET_GREEK_FLOW_HEATMAP and requires_greek_mspi_selector:
                # Use ids.CFG_VIZ_GREEK_FLOW_HEATMAP_OPTIONS and ids.CFG_VIZ_GREEK_FLOW_HEATMAP_DEFAULT_METRIC
                greek_opts = get_config_value(ids.CFG_VIZ_GREEK_FLOW_HEATMAP_OPTIONS, [], app_cfg_chart_cb)
                sel_greek = next((opt for opt in greek_opts if opt.get('value') == greek_sel_val), greek_opts[0] if greek_opts else {})
                kwargs_for_chart.update({
                    'metric_column_to_plot': sel_greek.get('value', get_config_value(ids.CFG_VIZ_GREEK_FLOW_HEATMAP_DEFAULT_METRIC, ids.COL_MSPI_SCORE, app_cfg_chart_cb)),
                    'chart_main_title_prefix': sel_greek.get('label', 'Selected Metric'),
                    'colorscale_config_key': sel_greek.get('cs_key', 'default_greek_cs'),
                    'colorbar_title_text': sel_greek.get('cb_title', 'Value')
                })
            
            if chart_id_param == ids.ID_CHART_COMBINED_ROLLING_FLOW and requires_rolling_flow_selector:
                kwargs_for_chart["component_history"] = get_data_bundle_history_for_symbol(sym_state_val, _CALLBACKS_COMPONENT_HISTORY) # type: ignore
                # Use ids.CFG_VIZ_ROLLING_FLOW_CHART_OPTIONS and ids.CFG_VIZ_ROLLING_FLOW_CHART_DEFAULT_OPTION
                flow_opts = get_config_value(ids.CFG_VIZ_ROLLING_FLOW_CHART_OPTIONS, [], app_cfg_chart_cb)
                sel_flow = next((opt for opt in flow_opts if opt.get('value') == roll_sel_val), flow_opts[0] if flow_opts else {})
                kwargs_for_chart['bar_metric_prefix'] = sel_flow.get('bar_metric_prefix', ids.CV_VOLM_BS_ROLLING_PREFIX)
                kwargs_for_chart['area_metric_prefix'] = sel_flow.get('area_metric_prefix', ids.CV_VALUE_BS_ROLLING_PREFIX)
            
            if requires_figure_state and fig_state_or_nclicks_val is not None and triggered_id_chart != ids.ID_HIDDEN_INITIAL_LOAD_TRIGGER:
                kwargs_for_chart["figure_state"] = fig_state_or_nclicks_val
                chart_factory_cb_logger.debug("    Passing existing 'figure_state' to visualizer.")
            
            chart_factory_cb_logger.info(f"  Calling '{chart_method_name_param}'. Kwarg keys: {list(kwargs_for_chart.keys())}")
            fig_result = chart_method(**kwargs_for_chart)
            chart_factory_cb_logger.info(f"  Chart '{chart_id_param}' by '{chart_method_name_param}' returned type: {type(fig_result).__name__}")

            if not isinstance(fig_result, go.Figure):
                chart_factory_cb_logger.error("  Visualizer method did not return Plotly Figure. Empty fig.")
                return create_empty_figure(title=f"Plot Error: {chart_title_empty}", height=def_height_chart, reason="Viz method non-Figure")
            
            chart_factory_cb_logger.info(f"--- CHART UPDATE END for '{chart_id_param}' - SUCCESS ---")
            return fig_result
        
        update_chart_dynamically_generated.__name__ = f"update_chart_for_{chart_id_param.replace('-', '_')}_V309_IDS_Integrated"
        chart_factory_cb_logger.debug(f"Callback function '{update_chart_dynamically_generated.__name__}' created for '{chart_id_param}'.")
        # End of dynamically generated function
    
    # Loop through all chart IDs and create a callback for each
    # Use ids.ALL_CHART_IDS_FOR_FACTORY
    if not ids.ALL_CHART_IDS_FOR_FACTORY or not isinstance(ids.ALL_CHART_IDS_FOR_FACTORY, list):
        reg_cb_logger.error("ids.ALL_CHART_IDS_FOR_FACTORY is empty or not a list. Cannot create chart update callbacks.")
    else:
        reg_cb_logger.info(f"Creating chart update callbacks for {len(ids.ALL_CHART_IDS_FOR_FACTORY)} chart IDs using integrated method name logic...")
        for chart_id_iter in ids.ALL_CHART_IDS_FOR_FACTORY:
            if not isinstance(chart_id_iter, str):
                reg_cb_logger.warning(f"Skipping non-string chart ID in factory loop: {chart_id_iter}")
                continue

            method_name_base = chart_id_iter.replace('-', '_').replace('_chart', '').replace('_cb', '')
            method_name_viz: str # Ensure it's declared

            # Explicit mapping from Chart ID to MSPIVisualizerV2 method name (using ID constants)
            if chart_id_iter == ids.ID_CHART_MSPI_HEATMAP:
                method_name_viz = "create_mspi_heatmap"
            elif chart_id_iter == ids.ID_CHART_MSPI_COMPONENTS:
                method_name_viz = "create_component_comparison"
            elif chart_id_iter == ids.ID_CHART_COMBINED_ROLLING_FLOW:
                method_name_viz = "create_combined_rolling_flow_chart"
            elif chart_id_iter == ids.ID_CHART_KEY_LEVELS:
                method_name_viz = "create_key_levels_visualization"
            elif chart_id_iter == ids.ID_CHART_TRADING_SIGNALS:
                method_name_viz = "create_trading_signals_visualization"
            elif chart_id_iter == ids.ID_CHART_RECOMMENDATIONS_TABLE:
                method_name_viz = "create_strategy_recommendations_table"
            elif chart_id_iter == ids.ID_CHART_NET_GREEK_FLOW_HEATMAP:
                method_name_viz = "create_net_greek_flow_heatmap"
            elif chart_id_iter == ids.ID_CHART_NET_VALUE_HEATMAP:
                method_name_viz = "create_net_value_heatmap"
            elif chart_id_iter == ids.ID_CHART_NET_VOLUME_PRESSURE_HEATMAP:
                method_name_viz = "create_net_volume_pressure_heatmap"
            elif chart_id_iter == ids.ID_CHART_VOLATILITY_REGIME:
                method_name_viz = "create_volatility_regime_visualization"
            elif chart_id_iter == ids.ID_CHART_TIME_DECAY:
                method_name_viz = "create_time_decay_visualization"
            elif chart_id_iter == ids.ID_CHART_SDAG_MULTIPLICATIVE:
                method_name_viz = "plot_sdag_multiplicative"
            elif chart_id_iter == ids.ID_CHART_SDAG_DIRECTIONAL:
                method_name_viz = "plot_sdag_directional"
            elif chart_id_iter == ids.ID_CHART_SDAG_WEIGHTED:
                method_name_viz = "plot_sdag_weighted"
            elif chart_id_iter == ids.ID_CHART_SDAG_VOLATILITY_FOCUSED:
                method_name_viz = "plot_sdag_volatility_focused"
            else: # Fallback if any other chart ID doesn't match the specific cases
                method_name_viz = f"create_{method_name_base}"
                reg_cb_logger.warning(f"  For Chart ID '{chart_id_iter}', using default method name convention: '{method_name_viz}'. Verify this is correct if chart fails.")
            
            reg_cb_logger.debug(f"  For Chart ID '{chart_id_iter}': Determined Visualizer Method='{method_name_viz}'")
            
            # Use ID constants for selectors
            req_range = chart_id_iter not in [ids.ID_CHART_RECOMMENDATIONS_TABLE]
            req_greek_sel = chart_id_iter == ids.ID_CHART_NET_GREEK_FLOW_HEATMAP
            req_roll_sel = chart_id_iter == ids.ID_CHART_COMBINED_ROLLING_FLOW
            
            charts_needing_figure_state_from_config = get_config_value(
                ids.CFG_VIZ_MSPI_VISUALIZER + ["charts_needing_figure_state_in_callbacks"], [], _CALLBACKS_APP_CONFIG
            )
            req_fig_state = any(fig_state_chart_key in chart_id_iter for fig_state_chart_key in charts_needing_figure_state_from_config)
            
            create_chart_update_callback_factory(
                chart_id_param=chart_id_iter, chart_method_name_param=method_name_viz,
                requires_range_slider=req_range, requires_greek_mspi_selector=req_greek_sel,
                requires_rolling_flow_selector=req_roll_sel, requires_figure_state=req_fig_state
            )
        reg_cb_logger.info("All chart update callbacks created via factory with integrated method name logic.")

    # --- Other Callbacks (Refresh Interval, Slider Label, Tab Content) ---
    # These remain the same as your V3.0.8 Canon Rewrite version, now using ids.py constants.

    @app_instance.callback(
        Output(ids.ID_AUTO_REFRESH_INTERVAL_COMPONENT, 'interval'), # Use ID constant
        Output(ids.ID_AUTO_REFRESH_INTERVAL_COMPONENT, 'disabled'), # Use ID constant
        Input(ids.ID_REFRESH_INTERVAL_DROPDOWN, 'value') # Use ID constant
    )
    def update_refresh_interval(selected_interval_ms: Optional[int]) -> Tuple[int, bool]:
        interval_update_logger = logging.getLogger("UpdateRefreshIntervalCallback_V3.0.9_IDS_Rewrite")
        interval_update_logger.debug(f"Refresh interval dropdown changed to: {selected_interval_ms} ms")
        if selected_interval_ms is not None and selected_interval_ms > 0:
            interval_update_logger.info(f"Setting refresh interval to {selected_interval_ms} ms. Timer ENABLED.")
            return selected_interval_ms, False
        interval_update_logger.info("Setting refresh interval to max (effectively disabled). Timer DISABLED.")
        return 24 * 60 * 60 * 1000, True

    @app_instance.callback(
        Output(ids.ID_RANGE_SLIDER_OUTPUT_LABEL, 'children'), # Use ID constant
        Input(ids.ID_RANGE_SLIDER, 'value') # Use ID constant
    )
    def update_range_slider_label(value: Optional[float]) -> str:
        return f"Strike Range % (+/-): {value:.1f}%" if value is not None else "Strike Range % (+/-): N/A"

    @app_instance.callback(
        Output(ids.ID_MAIN_CONTENT_AREA, 'children'), # Use ID constant
        Input(ids.ID_MODE_SELECTOR_TABS, 'active_tab') # Use ID constant
    )
    def render_tab_content(active_tab_id: Optional[str]) -> html.Div:
        tab_render_logger = logging.getLogger("RenderTabContentCallback_V3.0.9_IDS_Rewrite")
        tab_render_logger.info(f"Rendering content for active tab: '{active_tab_id}'")
        # Ensure these layout functions are available
        from .layout import get_main_dashboard_mode_layout, get_sdag_diagnostics_mode_layout, \
                            get_enhanced_flow_mode_layout, get_volatility_deep_dive_mode_layout
        
        if active_tab_id == ids.ID_TAB_MAIN_DASHBOARD: return get_main_dashboard_mode_layout()
        elif active_tab_id == ids.ID_TAB_SDAG_DIAGNOSTICS: return get_sdag_diagnostics_mode_layout()
        elif active_tab_id == ids.ID_TAB_ENHANCED_FLOW: return get_enhanced_flow_mode_layout()
        elif active_tab_id == ids.ID_TAB_VOLATILITY_DEEP_DIVE: return get_volatility_deep_dive_mode_layout()
        elif active_tab_id == ids.ID_TAB_PERFORMANCE: return html.Div(dbc.Alert("Performance Analytics - Coming Soon!", color="info", className="m-3 text-center"))
        tab_render_logger.warning(f"Unknown active_tab_id: '{active_tab_id}'. Defaulting to Main Dashboard layout.")
        return get_main_dashboard_mode_layout()

    reg_cb_logger.info("All dashboard callbacks successfully registered (V3.0.9 IDS Rewrite with integrated method name logic).")

