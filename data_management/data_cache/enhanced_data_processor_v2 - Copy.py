# enhanced_data_processor_v2.py
# (Elite Version 2.1.0 - Overhauled for v2.3+ Brain Integration - User Request 2)

# Standard Library Imports
import os
import json
import traceback
import logging
from datetime import datetime, date, time as dt_time, timedelta
import time as pytime
from typing import Dict, Any, Optional, List, Union, Tuple

# Third-Party Imports
import pandas as pd
import numpy as np
import copy

# --- Global Logger Setup ---
if not logging.getLogger().hasHandlers():
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO").upper(),
        format="[%(levelname)s] (%(name)s:%(lineno)d) %(asctime)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
logger = logging.getLogger(__name__)

# --- Constants ---
DEFAULT_DATA_DIR_PROC: str = "data_processed_output" # Changed default
DEFAULT_CONFIG_PATH_PROC: str = "config_v2.json"
JSON_CONVERSION_ERROR_PLACEHOLDER_PROC = "JSON_CONVERSION_ERROR_IN_PROCESSOR"

# --- Dummy Trading System (Fallback) ---
class IntegratedTradingSystemDummy:
    """ Dummy fallback for IntegratedTradingSystem. Provides default method implementations. """
    def __init__(self, config_path: str = DEFAULT_CONFIG_PATH_PROC):
         self.its_dummy_logger = logger.getChild("IntegratedTradingSystemDummy")
         self.its_dummy_logger.warning(f"PROCESSOR: Initializing DUMMY IntegratedTradingSystem (Config: {config_path}). Fallback.")
         self.config_path = config_path; self.config: Dict[str, Any] = {}
         # Basic config loading for dummy ITS to access simple params if needed by processor directly
         try:
            abs_config_path = config_path
            if not os.path.isabs(config_path):
                script_dir = os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else os.getcwd()
                abs_config_path = os.path.join(script_dir, config_path)
                if not os.path.exists(abs_config_path) and os.path.exists(config_path):
                    abs_config_path = os.path.abspath(config_path)
            if os.path.exists(abs_config_path):
                with open(abs_config_path, "r", encoding="utf-8") as f: self.config = json.load(f)
            else: self.its_dummy_logger.warning(f"Dummy ITS: Config file '{abs_config_path}' not found during dummy init.")
         except Exception as e: self.its_dummy_logger.error(f"Dummy ITS: Error loading config {config_path}: {e}")

    def _get_config_value(self, path: List[str], default_override: Any = None) -> Any:
        """Simplified config getter for dummy ITS."""
        current_level = self.config
        try:
            for key_segment in path:
                if isinstance(current_level, dict): current_level = current_level[key_segment]
                else: return default_override
            return current_level
        except (KeyError, TypeError): return default_override
        except Exception as e:
            self.its_dummy_logger.error(f"Dummy ITS _get_config_value error for {path}: {e}")
            return default_override

    def process_market_data_and_generate_recommendations(
        self, symbol: str, raw_options_data: pd.DataFrame,
        current_underlying_price_val: float,
        current_market_time_val: Optional[dt_time] = None,
        current_iv_val: Optional[float] = None,
        avg_iv_5day_val: Optional[float] = None,
        iv_context_dict_val: Optional[Dict[str, Any]] = None,
        historical_ohlc_data_val: Optional[pd.DataFrame] = None,
        avg_iv_long_term_val: Optional[float] = None,
        historical_atr_norm_vs_avg_val: Optional[float] = None,
        expiration_calendar_val: Optional[List[date]] = None
    ) -> Dict[str, Any]:
        self.its_dummy_logger.warning(f"DUMMY ITS: process_market_data_and_generate_recommendations called for {symbol}.")
        dummy_df = raw_options_data.copy() if isinstance(raw_options_data, pd.DataFrame) else pd.DataFrame()
        for col in ['mspi', 'a_dag', 'd_tdpi', 'vri_2_0', 'e_sdag_composite', 'sai', 'ssi']:
            if col not in dummy_df.columns: dummy_df[col] = 0.0
        
        # Use the configured strike column name for the dummy ITS
        strike_col_name_dummy = self._get_config_value(["visualization_settings", "mspi_visualizer", "column_names", "strike"], "strike")
        if strike_col_name_dummy not in dummy_df.columns and not dummy_df.empty:
             # If the configured strike column is missing, check for a generic 'strike'
             if 'strike' in dummy_df.columns and strike_col_name_dummy != 'strike':
                 dummy_df.rename(columns={'strike': strike_col_name_dummy}, inplace=True)
             elif 'strike' not in dummy_df.columns: # if neither configured nor 'strike' exists
                 dummy_df[strike_col_name_dummy] = 100.0 # Add a dummy strike column


        atr_fallback_cfg_dummy = self._get_config_value(["data_processor_settings", "approximations", "tdpi_atr_fallback"], {})
        dummy_atr = 1.0
        if isinstance(historical_ohlc_data_val, pd.DataFrame) and not historical_ohlc_data_val.empty:
            if all(c in historical_ohlc_data_val.columns for c in ['high','low','close']):
                tr = pd.concat([historical_ohlc_data_val['high'] - historical_ohlc_data_val['low'],
                                abs(historical_ohlc_data_val['high'] - historical_ohlc_data_val['close'].shift()),
                                abs(historical_ohlc_data_val['low'] - historical_ohlc_data_val['close'].shift())], axis=1).max(axis=1)
                if not tr.empty: dummy_atr = tr.ewm(span=14, adjust=False).mean().iloc[-1]

        dummy_aggregated_df = dummy_df.groupby(strike_col_name_dummy).first().reset_index() if strike_col_name_dummy in dummy_df.columns and not dummy_df.empty else pd.DataFrame()

        return {
            "symbol": symbol,
            "processed_options_df": dummy_df.to_dict(orient='records') if not dummy_df.empty else [],
            "aggregated_strike_data": dummy_aggregated_df.to_dict(orient='records') if not dummy_aggregated_df.empty else [],
            "key_levels": {"all_levels_sorted_by_strength": [], "support_df": pd.DataFrame(), "resistance_df": pd.DataFrame()},
            "signals": {'directional': {'bullish': [], 'bearish': []}},
            "recommendations": [{"id": "DUMMY_REC_001", "symbol": symbol, "category": "Dummy Full Process Rec", "rationale": "ITS DUMMY Used", "status": "NOTE"}],
            "current_mspi_weights_applied": {"dummy_metric_norm": 1.0},
            "current_adaptive_historical_context_summary": {"info": "Dummy ITS has no historical context"},
            "atr_value_used_by_processor_downstream": dummy_atr
        }

# --- Real ITS Import ---
RealIntegratedTradingSystem: Optional[type] = None
ITS_IMPORT_ERROR_MSG: Optional[str] = None
try:
    from core_analytics.integrated_strategies_v2 import IntegratedTradingSystem as ImportedITS
    RealIntegratedTradingSystem = ImportedITS
    logger.info("PROCESSOR V2.1.0: Successfully imported RealIntegratedTradingSystem from core_analytics.integrated_strategies_v2.") # Corrected path in log
except ImportError as import_error_its:
    ITS_IMPORT_ERROR_MSG = f"PROCESSOR V2.1.0 IMPORT ERROR: Could not import IntegratedTradingSystem from core_analytics.integrated_strategies_v2: {import_error_its}" # Corrected path in log
    logger.error(ITS_IMPORT_ERROR_MSG)
except Exception as general_import_error_its:
    ITS_IMPORT_ERROR_MSG = f"PROCESSOR V2.1.0 UNEXPECTED IMPORT ERROR for IntegratedTradingSystem: {general_import_error_its}"
    logger.error(ITS_IMPORT_ERROR_MSG, exc_info=True)
if RealIntegratedTradingSystem is None:
     logger.warning("PROCESSOR V2.1.0: Processing will use the DUMMY fallback trading system due to import failure.")

class EnhancedDataProcessor:
    """
    Handles data preparation and delegates to IntegratedTradingSystem for metric calculation.
    Version 2.1.0: Overhauled for v2.3+ Brain Integration.
    """
    def __init__(self, config_path: str = DEFAULT_CONFIG_PATH_PROC, data_dir: Optional[str] = None):
        self.init_logger = logger.getChild(f"{self.__class__.__name__}.Init")
        self.init_logger.info(f"Initializing EnhancedDataProcessor V2.1.0 (Config: {config_path})...")
        
        self.config_path = config_path
        self.init_logger.debug("--- EDP: Attempting to load processor_config...")
        self.processor_config: Dict[str, Any] = self._load_main_config_for_processor()
        self.init_logger.debug(f"--- EDP: Processor_config loaded. Keys: {list(self.processor_config.keys()) if self.processor_config else 'None'}")

        system_settings_cfg = self.processor_config.get("system_settings", {})
        # Use data_directory_base and processed_data_subdirectory from system_settings
        base_data_dir_cfg_val = system_settings_cfg.get("data_directory_base")
        processed_data_subdir_cfg_val = system_settings_cfg.get("processed_data_subdirectory")

        self.init_logger.debug(f"--- EDP: Resolved processed_output_dir to: {self.processed_output_dir}")
        
        self.init_logger.debug("--- EDP: Attempting to initialize trading_system_instance via _initialize_trading_system_instance...")
        self._initialize_trading_system_instance()
        
        if hasattr(self, 'trading_system_instance'):
            self.init_logger.debug(f"--- EDP: After _initialize_trading_system_instance, self.trading_system_instance type: {type(self.trading_system_instance).__name__}")
        else:
            self.init_logger.error("--- EDP: self.trading_system_instance was NOT SET after _initialize_trading_system_instance call!")
        
        
        
        effective_output_dir_name = None
        if base_data_dir_cfg_val and processed_data_subdir_cfg_val:
            # Construct full path for processed data
            # Base dir for resolving base_data_dir_cfg_val if it's relative
            config_base_dir_for_paths = os.path.dirname(os.path.abspath(self.config_path)) if os.path.isfile(self.config_path) else os.getcwd()
            resolved_base_data_dir = os.path.join(config_base_dir_for_paths, base_data_dir_cfg_val) if not os.path.isabs(base_data_dir_cfg_val) else base_data_dir_cfg_val
            effective_output_dir_name = os.path.join(resolved_base_data_dir, processed_data_subdir_cfg_val)
        elif data_dir is not None: # Fallback to passed data_dir arg
            effective_output_dir_name = data_dir
        else: # Fallback to default if nothing else specified
            effective_output_dir_name = DEFAULT_DATA_DIR_PROC
            self.init_logger.warning(f"Data directory for processed output not fully specified in config or args, using default: '{effective_output_dir_name}'")

            self.init_logger.debug("--- EDP: Attempting to ensure processed_output_dir_exists...")
            self._ensure_processed_output_dir_exists()
            self.init_logger.info(f"--- EDP: END __init__ (Successfully Initialized: {not getattr(self, 'initialization_failed', True)}) ---") # Assuming you might add an init failed flag

        if os.path.isabs(effective_output_dir_name):
            self.processed_output_dir: str = effective_output_dir_name
        else:
            if os.path.isfile(self.config_path) and os.path.isabs(self.config_path): base_dir = os.path.dirname(self.config_path)
            elif os.path.isfile(self.config_path): base_dir = os.path.dirname(os.path.abspath(self.config_path))
            elif os.path.isdir(self.config_path) and os.path.isabs(self.config_path): base_dir = self.config_path
            elif os.path.isdir(self.config_path): base_dir = os.path.abspath(self.config_path)
            else: base_dir = os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else os.getcwd()
            self.processed_output_dir = os.path.normpath(os.path.join(base_dir, effective_output_dir_name))

        self.init_logger.debug(f"Resolved processed_output_dir to: {self.processed_output_dir}")
        self.trading_system_instance: Union[ImportedITS, IntegratedTradingSystemDummy] # Type hint for clarity
        self._initialize_trading_system_instance()
        self._ensure_processed_output_dir_exists()
        self.init_logger.info("EnhancedDataProcessor V2.1.0 Initialized.")

    def _load_main_config_for_processor(self) -> Dict[str, Any]:
        load_cfg_logger = logger.getChild(f"{self.__class__.__name__}.LoadConfig")
        load_cfg_logger.debug(f"Loading FULL application configuration from: {self.config_path}")
        abs_config_path = self.config_path
        if not os.path.isabs(self.config_path):
            script_dir = os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else os.getcwd()
            abs_config_path = os.path.join(script_dir, self.config_path)
            if not os.path.exists(abs_config_path) and os.path.exists(self.config_path):
                abs_config_path = os.path.abspath(self.config_path)
        try:
            if os.path.exists(abs_config_path):
                with open(abs_config_path, "r", encoding="utf-8") as f_cfg:
                    full_loaded_config = json.load(f_cfg)
                load_cfg_logger.info(f"Successfully loaded FULL config from {abs_config_path} for processor.")
                return full_loaded_config
            else:
                load_cfg_logger.warning(f"FULL Config file {abs_config_path} not found. Using empty dict.")
                return {}
        except Exception as e_load_cfg:
            load_cfg_logger.error(f"Error loading FULL config from '{abs_config_path}': {e_load_cfg}. Using empty dict.", exc_info=True)
            return {}

    def _ensure_processed_output_dir_exists(self) -> None:
        try:
            os.makedirs(self.processed_output_dir, exist_ok=True)
            logger.debug(f"Ensured output directory exists: {self.processed_output_dir}")
        except OSError as e_dir_create:
            logger.warning(f"Could not create output directory '{self.processed_output_dir}': {e_dir_create}")

    def _initialize_trading_system_instance(self) -> None:
        init_its_logger = logger.getChild(f"{self.__class__.__name__}.InitITS")
        if RealIntegratedTradingSystem is not None: # RealIntegratedTradingSystem is from the import at the top
            try:
                init_its_logger.info(f"Attempting to instantiate RealIntegratedTradingSystem with config: {self.config_path}") # ADD LOG
                self.trading_system_instance = RealIntegratedTradingSystem(config_path=self.config_path)
                init_its_logger.info(f"Real IntegratedTradingSystem instance created successfully. Type: {type(self.trading_system_instance).__name__}") # ADD LOG
            except Exception as e_init_its_real:
                init_its_logger.error(f"Failed to instantiate real IntegratedTradingSystem: {e_init_its_real}", exc_info=True)
                init_its_logger.warning("Processor falling back to DUMMY IntegratedTradingSystem.")
                self.trading_system_instance = IntegratedTradingSystemDummy(config_path=self.config_path)
        else:
            init_its_logger.error(f"RealIntegratedTradingSystem class not available (Import Error: {ITS_IMPORT_ERROR_MSG}). Processor forced to DUMMY ITS.")
            self.trading_system_instance = IntegratedTradingSystemDummy(config_path=self.config_path)

    def _validate_input_data(self, options_chain_df: Optional[pd.DataFrame], symbol: str) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
        val_logger = logger.getChild(f"{self.__class__.__name__}.ValidateInput")
        if options_chain_df is None or not isinstance(options_chain_df, pd.DataFrame) or options_chain_df.empty:
            error_msg = f"Input options chain data for {symbol} missing, empty, or invalid type ({type(options_chain_df)})."
            val_logger.error(error_msg); return None, error_msg

        df = options_chain_df.copy()
        
        # Get expected strike column name from config (via ITS instance if possible, or processor's own config)
        # This assumes processor_config has a similar structure or a dedicated mapping.
        # For robustness, let's assume processor_config has the visualization_settings part.
        expected_strike_col_name = self.processor_config.get("visualization_settings", {}).get("mspi_visualizer", {}).get("column_names", {}).get("strike", "strike_price")
        
        required_base_cols = [expected_strike_col_name, "opt_kind", "symbol", "expiration_date", "oi", "volm", "delta", "gamma", "vega", "theta", "volatility"]
        
        # Check if the expected strike column name is present. If not, check for a generic "strike" column.
        if expected_strike_col_name not in df.columns and "strike" in df.columns:
            val_logger.info(f"'{symbol}': Expected strike column '{expected_strike_col_name}' not found, but 'strike' column exists. Will attempt to use 'strike'.")
            # Adjust required_base_cols to use "strike" if that's what's available
            required_base_cols = ["strike" if col == expected_strike_col_name else col for col in required_base_cols]
        elif expected_strike_col_name not in df.columns and "strike" not in df.columns:
             error_msg_strike = f"'{symbol}': Neither expected strike column '{expected_strike_col_name}' nor generic 'strike' column found."
             val_logger.error(error_msg_strike); return df, error_msg_strike


        required_flow_cols_option1 = ['volm_buy', 'volm_sell', 'value_buy', 'value_sell']
        required_flow_cols_option2 = ['volm_bs', 'value_bs']
        required_greek_flows = ['deltas_buy', 'deltas_sell', 'gammas_buy', 'gammas_sell', 'vegas_buy', 'vegas_sell', 'thetas_buy', 'thetas_sell']
        
        rolling_intervals = self.processor_config.get("visualization_settings", {}).get("mspi_visualizer", {}).get("rolling_intervals", ["5m", "15m", "30m", "60m"])
        rolling_flow_bases = ['volmbs_', 'valuebs_'] # These are prefixes
        required_rolling_flows = [f"{base}{interval}" for base in rolling_flow_bases for interval in rolling_intervals]


        missing_base = [col for col in required_base_cols if col not in df.columns]
        if missing_base:
            error_msg_base = f"'{symbol}': Missing critical base columns for processing: {missing_base}. Available: {df.columns.tolist()}. Cannot proceed."
            val_logger.error(error_msg_base); return df, error_msg_base

        has_flow_set1 = all(col in df.columns for col in required_flow_cols_option1)
        has_flow_set2 = all(col in df.columns for col in required_flow_cols_option2)
        has_greek_flows = all(col in df.columns for col in required_greek_flows)
        has_rolling_flows = all(col in df.columns for col in required_rolling_flows)

        if not (has_flow_set1 or has_flow_set2 or has_greek_flows or has_rolling_flows):
            val_logger.warning(f"'{symbol}': No comprehensive set of flow columns (buy/sell, _bs, direct greek, or rolling) found. Flow-dependent metrics in ITS may be impaired or use fallbacks.")
        else:
            val_logger.info(f"'{symbol}': Found some flow columns. Set1: {has_flow_set1}, Set2: {has_flow_set2}, GreekFlows: {has_greek_flows}, RollingFlows: {has_rolling_flows}")

        return df, None

    def _prepare_dataframe(self, df_to_prepare: pd.DataFrame, underlying_data_bundle: Optional[Dict[str,Any]], symbol_str: str) -> pd.DataFrame:
        prep_logger = logger.getChild(f"{self.__class__.__name__}.PrepareDataFrame")
        df_prepared = df_to_prepare.copy()

        current_underlying_price_from_bundle = None
        if isinstance(underlying_data_bundle, dict):
            current_underlying_price_from_bundle = underlying_data_bundle.get("price")

        if current_underlying_price_from_bundle is not None and isinstance(current_underlying_price_from_bundle, (int, float)) and pd.notna(current_underlying_price_from_bundle) and current_underlying_price_from_bundle > 0:
            df_prepared["price"] = float(current_underlying_price_from_bundle)
            prep_logger.info(f"({symbol_str}): Added/Set 'price' column (underlying price for context) to: {current_underlying_price_from_bundle:.4f} from bundle.")
        elif 'price' not in df_prepared.columns:
             df_prepared["price"] = 0.0
             prep_logger.error(f"({symbol_str}): Underlying price not available from fetcher's underlying_data_bundle and no 'price' column in options_df. Setting 'price' (underlying context) to 0.0. This will impact ITS.")
        else:
            df_prepared["price"] = pd.to_numeric(df_prepared["price"], errors='coerce').fillna(0.0)
            prep_logger.warning(f"({symbol_str}): Using existing 'price' column from options_df for underlying price context. Ensure this is correct. Mean: {df_prepared['price'].mean() if not df_prepared.empty else 'N/A'}")

        # --- FIX for Strike Column Name ---
        # Determine the strike column name ITS expects from the processor's own config
        # This ensures consistency if ITS's config changes, processor's config should align.
        expected_strike_col_by_its = self.processor_config.get("visualization_settings", {}).get("mspi_visualizer", {}).get("column_names", {}).get("strike", "strike_price")
        
        current_strike_col_in_df = None
        if expected_strike_col_by_its in df_prepared.columns:
            current_strike_col_in_df = expected_strike_col_by_its
        elif "strike" in df_prepared.columns: # Fallback to generic "strike" if expected one isn't there
            current_strike_col_in_df = "strike"
        
        if current_strike_col_in_df and current_strike_col_in_df != expected_strike_col_by_its:
            prep_logger.info(f"({symbol_str}): Renaming strike column from '{current_strike_col_in_df}' to '{expected_strike_col_by_its}' for ITS compatibility.")
            df_prepared.rename(columns={current_strike_col_in_df: expected_strike_col_by_its}, inplace=True)
        elif not current_strike_col_in_df:
            prep_logger.error(f"({symbol_str}): CRITICAL - Strike column ('{expected_strike_col_by_its}' or 'strike') not found in DataFrame. ITS processing will likely fail.")
            # Optionally, add a dummy strike column to prevent immediate crashes downstream, though data will be wrong
            # df_prepared[expected_strike_col_by_its] = 0.0
        # --- END FIX for Strike Column Name ---


        if 'underlying_symbol' not in df_prepared.columns or df_prepared['underlying_symbol'].isnull().all():
            fetched_und_sym_from_bundle = (underlying_data_bundle or {}).get("symbol")
            if fetched_und_sym_from_bundle:
                df_prepared['underlying_symbol'] = str(fetched_und_sym_from_bundle).upper()
            else:
                df_prepared['underlying_symbol'] = str(symbol_str).upper()
            prep_logger.info(f"({symbol_str}): Populated 'underlying_symbol' as '{df_prepared['underlying_symbol'].iloc[0] if not df_prepared.empty else 'N/A'}'.")

        if 'expiration_date' in df_prepared.columns:
            try:
                df_prepared['expiration_date'] = pd.to_datetime(df_prepared['expiration_date']).dt.date
            except Exception as e_exp_date:
                prep_logger.error(f"({symbol_str}): Error converting 'expiration_date' to date objects: {e_exp_date}. This will impact DTE calculations.")
        else:
            prep_logger.error(f"({symbol_str}): 'expiration_date' column MISSING. DTE calculations will fail.")

        numeric_cols_for_its = [expected_strike_col_by_its, 'oi', 'volm', 'delta', 'gamma', 'vega', 'theta', 'volatility',
                                'gxoi', 'dxoi', 'txoi', 'vxoi', 'charmxoi', 'vannaxoi', 'vommaxoi']
        flow_cols_to_ensure_numeric = [
            'volm_buy', 'volm_sell', 'value_buy', 'value_sell', 'volm_bs', 'value_bs',
            'deltas_buy', 'deltas_sell', 'gammas_buy', 'gammas_sell', 'vegas_buy', 'vegas_sell', 'thetas_buy', 'thetas_sell',
            'dxvolm', 'gxvolm', 'txvolm', 'vxvolm', 'charmxvolm', 'vannaxvolm', 'vommaxvolm'
        ]
        rolling_flow_bases_prep = ['volmbs_', 'valuebs_']
        rolling_intervals_prep = self.processor_config.get("visualization_settings", {}).get("mspi_visualizer", {}).get("rolling_intervals", ["5m", "15m", "30m", "60m"])
        rolling_flows_to_ensure_numeric = [f"{base}{interval}" for base in rolling_flow_bases_prep for interval in rolling_intervals_prep]

        all_numeric_cols_needed = list(set(numeric_cols_for_its + flow_cols_to_ensure_numeric + rolling_flows_to_ensure_numeric)) # Use set to ensure unique

        for col in all_numeric_cols_needed:
            if col in df_prepared.columns:
                if not pd.api.types.is_numeric_dtype(df_prepared[col]):
                    df_prepared[col] = pd.to_numeric(df_prepared[col], errors='coerce')
                df_prepared[col] = df_prepared[col].fillna(0.0)
            else:
                if col in flow_cols_to_ensure_numeric or col in numeric_cols_for_its:
                     df_prepared[col] = 0.0
                     prep_logger.warning(f"({symbol_str}): Column '{col}' was missing and added as 0.0 for ITS compatibility.")
        return df_prepared

    def _apply_integrated_strategies(
        self,
        df_prepared_input: pd.DataFrame,
        underlying_data_bundle_from_fetcher: Dict[str, Any],
        market_context_for_its: Dict[str, Any],
        historical_ohlc_data_for_atr: Optional[pd.DataFrame],
        symbol_str_context: str,
        expiration_calendar_for_its: Optional[List[date]] = None
    ) -> Tuple[Dict[str, Any], Optional[str]]: # Changed return type to match ITS process_market_data...
        apply_strat_logger = logger.getChild(f"{self.__class__.__name__}.ApplyITS_V2.1.0")

        its_output_bundle: Optional[Dict[str, Any]] = None
        processing_error_output: Optional[str] = None

        if RealIntegratedTradingSystem is None and not isinstance(self.trading_system_instance, IntegratedTradingSystemDummy):
            apply_strat_logger.error(f"CRITICAL: Real ITS not loaded, but instance is not Dummy. Forcing Dummy ITS for safety.")
            self.trading_system_instance = IntegratedTradingSystemDummy(config_path=self.config_path)

        try:
            apply_strat_logger.info(f"Processor ({symbol_str_context}): Invoking ITS instance ({type(self.trading_system_instance).__name__}) for full analysis...")

            current_underlying_price_for_its = underlying_data_bundle_from_fetcher.get("price")
            if current_underlying_price_for_its is None:
                 apply_strat_logger.error(f"({symbol_str_context}) Missing current_underlying_price for ITS. Aborting ITS call.")
                 raise ValueError("Missing current_underlying_price for ITS processing.")

            its_kwargs = {
                "symbol": symbol_str_context,
                "raw_options_data": df_prepared_input, # This DataFrame should now have correct column names
                "current_underlying_price_val": float(current_underlying_price_for_its),
                "current_market_time_val": market_context_for_its.get("current_time"),
                "current_iv_val": market_context_for_its.get("current_iv"),
                "avg_iv_5day_val": market_context_for_its.get("avg_iv_5day"),
                "iv_context_dict_val": market_context_for_its,
                "historical_ohlc_data_val": historical_ohlc_data_for_atr,
                "avg_iv_long_term_val": market_context_for_its.get("avg_iv_90day"),
                "historical_atr_norm_vs_avg_val": market_context_for_its.get("historical_atr_normalized_vs_avg"),
                "expiration_calendar_val": expiration_calendar_for_its
            }

            its_output_bundle = self.trading_system_instance.process_market_data_and_generate_recommendations(**its_kwargs)

            if not isinstance(its_output_bundle, dict):
                raise TypeError(f"ITS instance for {symbol_str_context} returned type {type(its_output_bundle)}, expected dict.")

            apply_strat_logger.info(f"Processor ({symbol_str_context}): Analysis from ITS instance completed.")

        except Exception as e_apply_its:
            processing_error_output = f"Error during ITS processing for {symbol_str_context}: {e_apply_its}"
            apply_strat_logger.error(processing_error_output, exc_info=True)
            if its_output_bundle is None: its_output_bundle = {}
            its_output_bundle["error"] = processing_error_output
            # Ensure essential keys for downstream packaging exist, even if empty
            its_output_bundle.setdefault("processed_options_df", df_prepared_input.to_dict(orient='records') if isinstance(df_prepared_input, pd.DataFrame) else [])
            its_output_bundle.setdefault("final_metric_rich_df_obj", df_prepared_input) # For _package_results
            its_output_bundle.setdefault("key_levels", {})
            its_output_bundle.setdefault("signals", {})
            its_output_bundle.setdefault("recommendations", [])


        return its_output_bundle, processing_error_output


    def _package_results(self, symbol_str_pkg: str, fetch_ts_pkg: Optional[str],
                         its_bundle_pkg: Dict[str, Any],
                         underlying_data_pkg: Optional[Dict[str,Any]],
                         market_context_data_pkg: Optional[Dict[str,Any]],
                         processor_config_snapshot_pkg: Dict[str,Any],
                         processing_error_msg: Optional[str] = None
                         ) -> Dict[str, Any]:
        pkg_logger = logger.getChild(f"{self.__class__.__name__}.PackageResults_V2.1.0")
        pkg_logger.info(f"Processor ({symbol_str_pkg}): Packaging results bundle V2.1.0...")
        pkg_start_time = datetime.now()

        bundle:Dict[str,Any]={
            "symbol":str(symbol_str_pkg).upper(),
            "fetch_timestamp":fetch_ts_pkg,
            "processing_timestamp":pkg_start_time.isoformat(),
            "processor_version":"2.1.0-OverhauledBrainSync",
            "error": processing_error_msg or its_bundle_pkg.get("error"),
        }

        final_metric_rich_df_from_its_obj = its_bundle_pkg.get("final_metric_rich_df_obj")
        if not isinstance(final_metric_rich_df_from_its_obj, pd.DataFrame):
            df_records = its_bundle_pkg.get("processed_options_df", [])
            if isinstance(df_records, list) and df_records and isinstance(df_records[0], dict):
                final_metric_rich_df_from_its_obj = pd.DataFrame(df_records)
            else:
                final_metric_rich_df_from_its_obj = pd.DataFrame()


        if not final_metric_rich_df_from_its_obj.empty:
            pkg_logger.info(f"  Columns in final_metric_rich_df from ITS: {final_metric_rich_df_from_its_obj.columns.tolist()}")
            expected_metrics_from_its = []
            if hasattr(self.trading_system_instance, '_get_config_value'):
                _gf = self.trading_system_instance._get_config_value
                if _gf(["enhanced_metrics", "a_dag", "enabled"], False): expected_metrics_from_its.append(_gf(["enhanced_metrics", "a_dag", "output_column_name"], "a_dag"))
                if _gf(["enhanced_metrics", "d_tdpi", "enabled"], False): expected_metrics_from_its.append(_gf(["enhanced_metrics", "d_tdpi", "output_column_name"], "d_tdpi"))
                if _gf(["enhanced_metrics", "vri_2_0", "enabled"], False): expected_metrics_from_its.append(_gf(["enhanced_metrics", "vri_2_0", "output_column_name"], "vri_2_0"))
                if _gf(["enhanced_metrics", "e_sdag", "enabled"], False):
                    expected_metrics_from_its.append(_gf(["enhanced_metrics", "e_sdag", "composite_output_column_name"], "e_sdag_composite"))
                    expected_metrics_from_its.append(_gf(["enhanced_metrics", "e_sdag", "conviction_score_output_col_name"], "sdag_conviction_score"))

            present_metrics_for_log_pkg = [m for m in expected_metrics_from_its if m in final_metric_rich_df_from_its_obj.columns]
            if present_metrics_for_log_pkg:
                pkg_logger.info(f"  Sample data of key ENHANCED metrics from ITS output:\n{final_metric_rich_df_from_its_obj[present_metrics_for_log_pkg].head().to_string()}")
            else:
                pkg_logger.warning(f"  No key expected enhanced metrics from ITS config (expected: {expected_metrics_from_its}) found in DataFrame from ITS. This is OK if they are disabled.")
        else:
            pkg_logger.warning(f"  Final DataFrame object from ITS is empty or not a DataFrame.")

        json_conversion_had_errors = False
        try:
            # Ensure processed_options_df is a list of dicts, not a DataFrame object, for JSON safety
            processed_df_for_json = its_bundle_pkg.get("processed_options_df",[])
            if isinstance(processed_df_for_json, pd.DataFrame): # Convert if ITS accidentally passed DataFrame object
                processed_df_for_json = processed_df_for_json.to_dict(orient='records')
            
            bundle["processed_data"] = {"options_chain": self._convert_to_json_safe(processed_df_for_json)}
            bundle["key_levels"] = self._convert_to_json_safe(its_bundle_pkg.get("key_levels", {}))
            bundle["trading_signals"] = self._convert_to_json_safe(its_bundle_pkg.get("signals", {}))
            bundle["strategy_recommendations"] = self._convert_to_json_safe(its_bundle_pkg.get("recommendations", []))
            bundle["underlying"] = self._convert_to_json_safe(underlying_data_pkg or {})
            bundle["market_context"] = self._convert_to_json_safe(market_context_data_pkg or {})
            bundle["atr_value_used"] = self._convert_scalar_to_json_safe(its_bundle_pkg.get("atr_value_used_by_its", its_bundle_pkg.get("atr_value_used")))

            bundle["current_mspi_weights_applied"] = self._convert_to_json_safe(its_bundle_pkg.get("current_mspi_weights_applied", {}))
            bundle["current_adaptive_historical_context_summary"] = self._convert_to_json_safe(its_bundle_pkg.get("current_adaptive_historical_context_summary", {}))

            bundle["final_metric_rich_df_obj"] = final_metric_rich_df_from_its_obj # Keep the DataFrame object
            bundle["historical_ohlc_df_obj"] = market_context_data_pkg.get("historical_ohlcv_df") if isinstance(market_context_data_pkg, dict) else None
            bundle["expiration_calendar_used"] = market_context_data_pkg.get("expiration_calendar_used") if isinstance(market_context_data_pkg, dict) else None


            relevant_config_parts_snapshot = {
                "data_processor_settings": processor_config_snapshot_pkg.get("data_processor_settings"),
                "strategy_settings": processor_config_snapshot_pkg.get("strategy_settings"),
                "enhanced_metrics": processor_config_snapshot_pkg.get("enhanced_metrics"),
                "trade_idea_framework": processor_config_snapshot_pkg.get("trade_idea_framework"),
                "system_settings": {"log_level": processor_config_snapshot_pkg.get("system_settings",{}).get("log_level")}
            }
            bundle["config_snapshot"] = self._convert_to_json_safe(relevant_config_parts_snapshot)

            if JSON_CONVERSION_ERROR_PLACEHOLDER_PROC in str(bundle.get("processed_data")) or \
               JSON_CONVERSION_ERROR_PLACEHOLDER_PROC in str(bundle.get("key_levels")) or \
               JSON_CONVERSION_ERROR_PLACEHOLDER_PROC in str(bundle.get("trading_signals")) or \
               JSON_CONVERSION_ERROR_PLACEHOLDER_PROC in str(bundle.get("strategy_recommendations")):
                json_conversion_had_errors = True
                pkg_logger.error(f"Packaging Error ({symbol_str_pkg}): {JSON_CONVERSION_ERROR_PLACEHOLDER_PROC} detected in final bundle string representation after JSON conversion.")

        except Exception as e_package_final:
            packaging_error_text = f"Unexpected error during results packaging: {e_package_final}"
            pkg_logger.error(f"Processor ({symbol_str_pkg}): {packaging_error_text}", exc_info=True)
            current_bundle_error = bundle.get("error")
            bundle["error"] = f"{current_bundle_error} | Packaging Error: {packaging_error_text}".strip(" | ") if current_bundle_error else f"Packaging Error: {packaging_error_text}"
            if "final_metric_rich_df_obj" not in bundle: bundle["final_metric_rich_df_obj"] = final_metric_rich_df_from_its_obj

        packaging_duration_seconds = (datetime.now() - pkg_start_time).total_seconds()
        log_func_final = pkg_logger.error if json_conversion_had_errors or bundle["error"] else pkg_logger.info
        log_func_final(f"Processor ({symbol_str_pkg}): Packaging complete in {packaging_duration_seconds:.3f}s.{' Errors encountered during packaging.' if json_conversion_had_errors or bundle['error'] else ''}")
        return bundle

    def _convert_scalar_to_json_safe(self, scalar_data: Any) -> Any:
        if pd.isna(scalar_data) or scalar_data is None: return None
        if isinstance(scalar_data, (np.integer, int)): return int(scalar_data)
        if isinstance(scalar_data, (np.floating, float)):
            if np.isinf(scalar_data): return "Infinity" if scalar_data > 0 else "-Infinity"
            if np.isnan(scalar_data): return None
            return float(scalar_data)
        if isinstance(scalar_data, (np.bool_, bool)): return bool(scalar_data)
        if isinstance(scalar_data, (datetime, date, pd.Timestamp)):
            try: return scalar_data.isoformat()
            except Exception: return str(scalar_data)
        if isinstance(scalar_data, timedelta): return scalar_data.total_seconds()
        if isinstance(scalar_data, (list, tuple, set)): return self._convert_to_json_safe(list(scalar_data))
        if isinstance(scalar_data, dict): return self._convert_to_json_safe(scalar_data)
        try:
            return str(scalar_data)
        except TypeError:
            logger.getChild(f"{self.__class__.__name__}._ConvertScalar").error(f"Failed to convert scalar type '{type(scalar_data)}' to a JSON-safe string. Returning placeholder.")
            return f"{JSON_CONVERSION_ERROR_PLACEHOLDER_PROC}: Unserializable_Scalar_{type(scalar_data).__name__}"


    def _convert_to_json_safe(self, data_to_convert: Any) -> Any:
        json_safe_logger = logger.getChild(f"{self.__class__.__name__}._ConvertToJSONSafe")
        try:
            if isinstance(data_to_convert, pd.DataFrame):
                if data_to_convert.empty: return []
                df_copy = data_to_convert.copy(deep=True)

                for col in df_copy.select_dtypes(include=['datetime64[ns]', 'datetime64[ns, UTC]', 'datetimetz']).columns:
                    try: df_copy[col] = df_copy[col].dt.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
                    except AttributeError:
                        df_copy[col] = df_copy[col].apply(lambda x: x.isoformat() if hasattr(x, 'isoformat') else (str(x) if pd.notna(x) else None))
                    df_copy[col] = df_copy[col].replace({pd.NaT: None})


                for col in df_copy.columns:
                    if not df_copy[col].empty:
                        first_valid_element = df_copy[col].dropna().iloc[0] if not df_copy[col].dropna().empty else None
                        if isinstance(first_valid_element, date) and not isinstance(first_valid_element, datetime):
                            df_copy[col] = df_copy[col].apply(lambda x: x.isoformat() if isinstance(x, date) and pd.notna(x) else None)

                for col in df_copy.columns:
                    if pd.api.types.is_numeric_dtype(df_copy[col]):
                        df_copy[col] = df_copy[col].replace([np.inf, -np.inf], ["Infinity", "-Infinity"])
                        df_copy[col] = df_copy[col].astype(object).where(pd.notna(df_copy[col]) & (df_copy[col] != "Infinity") & (df_copy[col] != "-Infinity"),
                                                                    df_copy[col].where((df_copy[col] == "Infinity") | (df_copy[col] == "-Infinity"), None))


                list_of_records = df_copy.to_dict(orient='records')
                return [self._convert_to_json_safe(record) for record in list_of_records]

            elif isinstance(data_to_convert, pd.Series):
                 if data_to_convert.empty: return []
                 return self._convert_to_json_safe(data_to_convert.to_list())
            elif isinstance(data_to_convert, np.ndarray):
                return self._convert_to_json_safe(data_to_convert.tolist())
            elif isinstance(data_to_convert, dict):
                return { self._convert_scalar_to_json_safe(key): self._convert_to_json_safe(value) for key, value in data_to_convert.items() }
            elif isinstance(data_to_convert, (list, tuple, set)):
                return [self._convert_to_json_safe(item) for item in list(data_to_convert)]
            elif pd.isna(data_to_convert) or data_to_convert is None:
                return None
            return self._convert_scalar_to_json_safe(data_to_convert)
        except Exception as e_json_safe:
            json_safe_logger.error(f"Error in _convert_to_json_safe for data of type {type(data_to_convert)}: {e_json_safe}", exc_info=True)
            return f"{JSON_CONVERSION_ERROR_PLACEHOLDER_PROC}: Conversion_Failed_{type(data_to_convert).__name__}"

    def process_market_data_bundle(
        self,
        market_data_from_fetcher: Dict[str, Dict[str, Any]],
        tradier_context_data: Optional[Dict[str, Any]] = None,
        expiration_calendars_by_symbol: Optional[Dict[str, List[date]]] = None
    ) -> Dict[str, Dict[str, Any]]:
        bundle_proc_logger = logger.getChild(f"{self.__class__.__name__}.ProcessMarketDataBundle_V2.1.0")
        bundle_proc_logger.info(f"Starting to process market data bundle for {len(market_data_from_fetcher)} symbols (V2.1.0 Overhaul)...")

        all_symbols_processed_output: Dict[str, Dict[str, Any]] = {}

        for symbol_str, symbol_data_bundle in market_data_from_fetcher.items():
            symbol_proc_start_time_py = pytime.time()
            bundle_proc_logger.info(f"\n--- Processing Symbol: {symbol_str} ---")

            options_df_input: Optional[pd.DataFrame] = symbol_data_bundle.get("options_chain")
            underlying_info_input: Optional[Dict[str, Any]] = symbol_data_bundle.get("underlying")
            fetcher_error_for_symbol: Optional[str] = symbol_data_bundle.get("error")

            symbol_tradier_iv_quote_context: Optional[Dict[str, Any]] = None
            symbol_hist_ohlc_df: Optional[pd.DataFrame] = None
            symbol_expiration_calendar: Optional[List[date]] = None

            if isinstance(tradier_context_data, dict) and symbol_str in tradier_context_data:
                symbol_specific_tradier_bundle = tradier_context_data[symbol_str]
                if isinstance(symbol_specific_tradier_bundle, dict):
                    symbol_tradier_iv_quote_context = symbol_specific_tradier_bundle.get("iv_and_quote_data")
                    symbol_hist_ohlc_df = symbol_specific_tradier_bundle.get("historical_ohlcv_df")

            if isinstance(expiration_calendars_by_symbol, dict):
                symbol_expiration_calendar = expiration_calendars_by_symbol.get(symbol_str)

            current_market_context_for_pkg = {
                "iv_and_quote_data": symbol_tradier_iv_quote_context,
                "historical_ohlcv_df": symbol_hist_ohlc_df,
                "expiration_calendar_used": symbol_expiration_calendar
            }

            if fetcher_error_for_symbol:
                bundle_proc_logger.error(f"Fetcher error for {symbol_str}: {fetcher_error_for_symbol}. Packaging error result.")
                empty_its_bundle = {"error": fetcher_error_for_symbol, "processed_options_df": []}
                all_symbols_processed_output[symbol_str] = self._package_results(
                    symbol_str_pkg=symbol_str,
                    fetch_ts_pkg=(underlying_info_input or {}).get("fetch_timestamp", datetime.now().isoformat()),
                    its_bundle_pkg=empty_its_bundle,
                    underlying_data_pkg=underlying_info_input,
                    market_context_data_pkg=current_market_context_for_pkg,
                    processor_config_snapshot_pkg=self.processor_config,
                    processing_error_msg=fetcher_error_for_symbol
                )
                continue

            df_validated, validation_error_msg = self._validate_input_data(options_df_input, symbol_str)
            if validation_error_msg:
                bundle_proc_logger.error(f"Input data validation failed for {symbol_str}: {validation_error_msg}")
                empty_its_bundle_val_err = {"error": validation_error_msg, "processed_options_df": (df_validated.to_dict(orient='records') if isinstance(df_validated, pd.DataFrame) else [])}
                all_symbols_processed_output[symbol_str] = self._package_results(
                    symbol_str, (underlying_info_input or {}).get("fetch_timestamp"),
                    empty_its_bundle_val_err, underlying_info_input, current_market_context_for_pkg,
                    self.processor_config, validation_error_msg)
                continue

            df_prepared = self._prepare_dataframe(df_validated, underlying_info_input, symbol_str)

            market_context_for_its_call: Dict[str, Any] = {
                "current_time": datetime.now().time(),
                "current_iv": (underlying_info_input or {}).get("volatility"),
                **(symbol_tradier_iv_quote_context or {})
            }

            its_bundle, its_processing_error = self._apply_integrated_strategies(
                df_prepared_input=df_prepared,
                underlying_data_bundle_from_fetcher=underlying_info_input,
                market_context_for_its=market_context_for_its_call,
                historical_ohlc_data_for_atr=symbol_hist_ohlc_df,
                symbol_str_context=symbol_str,
                expiration_calendar_for_its=symbol_expiration_calendar
            )

            all_symbols_processed_output[symbol_str] = self._package_results(
                symbol_str_pkg=symbol_str,
                fetch_ts_pkg=(underlying_info_input or {}).get("fetch_timestamp"),
                its_bundle_pkg=its_bundle,
                underlying_data_pkg=underlying_info_input,
                market_context_data_pkg=current_market_context_for_pkg,
                processor_config_snapshot_pkg=self.processor_config,
                processing_error_msg=its_processing_error
            )
            bundle_proc_logger.info(f"--- Finished processing {symbol_str} in {pytime.time() - symbol_proc_start_time_py:.3f}s ---")

        bundle_proc_logger.info(f"--- Market Data Bundle Processing Complete for {len(all_symbols_processed_output)} symbols. ---")
        return all_symbols_processed_output

if __name__ == "__main__":
    test_proc_logger_main = logging.getLogger("ProcessorStandaloneTest_V2.1.0")
    if not test_proc_logger_main.hasHandlers():
        console_handler_proc_main = logging.StreamHandler()
        console_handler_proc_main.setLevel(logging.DEBUG)
        formatter_proc_main = logging.Formatter('[%(levelname)s] (%(name)s:%(lineno)d) %(asctime)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
        console_handler_proc_main.setFormatter(formatter_proc_main)
        test_proc_logger_main.addHandler(console_handler_proc_main)
        test_proc_logger_main.setLevel(logging.DEBUG)
        logging.getLogger("EnhancedDataProcessor").setLevel(logging.DEBUG)
        if RealIntegratedTradingSystem:
            logging.getLogger("core_analytics.integrated_strategies_v2").setLevel(logging.DEBUG) # Corrected logger name
        else:
             logging.getLogger("IntegratedTradingSystemDummy").setLevel(logging.DEBUG)


    test_proc_logger_main.info("--- EnhancedDataProcessor Standalone Test (V2.1.0 - Overhauled Brain Sync) --- ")

    script_dir_proc_test = os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else os.getcwd()
    test_config_path_proc_main = os.path.join(script_dir_proc_test, DEFAULT_CONFIG_PATH_PROC)
    test_proc_logger_main.info(f"Attempting to use config path: {test_config_path_proc_main}")


    if not os.path.exists(test_config_path_proc_main):
        test_proc_logger_main.error(f"Config file '{test_config_path_proc_main}' not found! Cannot run full processor test.")
    elif RealIntegratedTradingSystem is None:
        test_proc_logger_main.critical(f"RealIntegratedTradingSystem not imported ({ITS_IMPORT_ERROR_MSG}). Processor will use DUMMY ITS. Test will be limited.")
        processor_instance_test = EnhancedDataProcessor(config_path=test_config_path_proc_main)
        test_proc_logger_main.info("Processor initialized with DUMMY ITS. Continuing test with dummy behavior.")
    else:
        try:
            processor_instance_test = EnhancedDataProcessor(config_path=test_config_path_proc_main)

            test_proc_logger_main.info("Creating sample data for processor test...")
            test_symbol_proc = "TESTPROC"
            current_price_proc = 150.0; current_iv_proc = 0.25; avg_5day_iv_proc = 0.23
            fetch_timestamp_proc = datetime.now().isoformat()
            import random
            sample_options_data_list_proc = []
            # Use the configured strike column name for sample data generation
            strike_col_name_sample = processor_instance_test.processor_config.get("visualization_settings", {}).get("mspi_visualizer", {}).get("column_names", {}).get("strike", "strike_price")

            for strike_val in np.arange(current_price_proc - 10, current_price_proc + 11, 2.5):
                for opt_kind_val in ['call', 'put']:
                    sample_options_data_list_proc.append({
                        'symbol': f".{test_symbol_proc}{int(datetime.now().timestamp())}{opt_kind_val[0].upper()}{strike_val}",
                        strike_col_name_sample: strike_val, # Use configured strike column name
                        'opt_kind': opt_kind_val,
                        'option_price': round(max(0.05, np.random.normal(2.5, 1.0)),2),
                        'volatility': current_iv_proc + np.random.uniform(-0.02, 0.02),
                        'fetch_timestamp': fetch_timestamp_proc,
                        'expiration_date': (date.today() + timedelta(days=random.choice([0, 1, 5, 10]))).isoformat(),
                        'volmbs_5m': np.random.randint(-50, 50), 'valuebs_5m': np.random.randint(-5000, 5000),
                        'volmbs_15m': np.random.randint(-100, 100), 'valuebs_15m': np.random.randint(-10000, 10000),
                        'volmbs_30m': np.random.randint(-70,70), 'valuebs_30m': np.random.randint(-7000,7000),
                        'volmbs_60m': np.random.randint(-60,60), 'valuebs_60m': np.random.randint(-6000,6000),
                        'gxoi': np.random.uniform(100, 1000), 'dxoi': np.random.uniform(-500, 500),
                        'txoi': np.random.uniform(-100,-10),'vxoi': np.random.uniform(50,500),
                        'charmxoi': np.random.uniform(-50,50),'vannaxoi':np.random.uniform(-100,100),
                        'vommaxoi': np.random.uniform(10,50),
                        'volm': np.random.randint(10,200), 'oi': np.random.randint(50,500), 'delta': np.random.uniform(-1,1), 'gamma': np.random.uniform(0,0.1), 'vega': np.random.uniform(0,0.5), 'theta': np.random.uniform(-0.1,0),
                        'deltas_buy':np.random.uniform(-100,100),'deltas_sell':np.random.uniform(-100,100),
                        'gammas_buy':np.random.uniform(0,50),'gammas_sell':np.random.uniform(0,50),
                        'thetas_buy':np.random.uniform(-50,0),'thetas_sell':np.random.uniform(-50,0),
                        'vegas_buy':np.random.uniform(0,100),'vegas_sell':np.random.uniform(0,100),
                        'volm_buy': np.random.randint(0,100), 'volm_sell':np.random.randint(0,100),
                        'value_buy':np.random.randint(0,10000),'value_sell':np.random.randint(0,10000),
                        'volm_bs': np.random.randint(-50,50), 'value_bs': np.random.randint(-5000,5000),
                        'dxvolm':np.random.uniform(-100,100), 'gxvolm':np.random.uniform(-50,50),
                        'vxvolm':np.random.uniform(-100,100), 'txvolm':np.random.uniform(-50,50),
                        'charmxvolm':np.random.uniform(-20,20), 'vannaxvolm':np.random.uniform(-30,30),
                        'vommaxvolm':np.random.uniform(-10,10)
                    })
            sample_options_df_proc = pd.DataFrame(sample_options_data_list_proc)

            sample_underlying_data_proc = {
                "symbol": test_symbol_proc, "price": current_price_proc, "fetch_timestamp": fetch_timestamp_proc,
                "volatility": current_iv_proc,
                "iv_percentile_30d": 0.60,
                "avg_iv_90day": 0.22,
                "historical_atr_normalized_vs_avg": 1.05
            }
            sample_market_context_tradier_proc = {
                "current_iv": current_iv_proc,
                "avg_iv_5day": avg_5day_iv_proc,
                "iv_percentile_30d": 0.60,
                "average_historical_atr_pct": 0.015,
                "avg_iv_90day": 0.22,
                "historical_atr_normalized_vs_avg": 1.05
            }
            ohlc_dates_proc = [date.today() - timedelta(days=i) for i in range(45,0,-1)]
            sample_ohlc_df_proc = pd.DataFrame({
                'date': pd.to_datetime(ohlc_dates_proc),
                'open': current_price_proc - 5 + np.random.randn(45).cumsum()*0.1,
                'high': current_price_proc - 5 + np.random.randn(45).cumsum()*0.1 + np.random.rand(45)*2,
                'low':  current_price_proc - 5 + np.random.randn(45).cumsum()*0.1 - np.random.rand(45)*2,
                'close':current_price_proc - 5 + np.random.randn(45).cumsum()*0.1,
                'volume': np.random.randint(1e6, 1e7, 45)
            })
            sample_ohlc_df_proc['high'] = np.maximum(sample_ohlc_df_proc['high'], sample_ohlc_df_proc['open'])
            sample_ohlc_df_proc['high'] = np.maximum(sample_ohlc_df_proc['high'], sample_ohlc_df_proc['close'])
            sample_ohlc_df_proc['low'] = np.minimum(sample_ohlc_df_proc['low'], sample_ohlc_df_proc['open'])
            sample_ohlc_df_proc['low'] = np.minimum(sample_ohlc_df_proc['low'], sample_ohlc_df_proc['close'])


            sample_exp_calendar_proc = [date.today() + timedelta(days=d) for d in [0,1,2,7,14,21,30]]


            test_proc_logger_main.info(f"Sample Options DF shape: {sample_options_df_proc.shape}")

            mock_market_data_fetcher_bundle = {
                test_symbol_proc: {
                    "options_chain": sample_options_df_proc,
                    "underlying": sample_underlying_data_proc,
                    "error": None
                }
            }
            mock_tradier_context_bundle = {
                test_symbol_proc: {
                    "iv_and_quote_data": sample_market_context_tradier_proc,
                    "historical_ohlcv_df": sample_ohlc_df_proc
                }
            }
            mock_expiration_calendars = {
                test_symbol_proc: sample_exp_calendar_proc
            }

            processed_bundle_test_from_bundle_method = processor_instance_test.process_market_data_bundle(
                market_data_from_fetcher=mock_market_data_fetcher_bundle,
                tradier_context_data=mock_tradier_context_bundle,
                expiration_calendars_by_symbol=mock_expiration_calendars
            )

            single_symbol_output_bundle_test = processed_bundle_test_from_bundle_method.get(test_symbol_proc)

            if single_symbol_output_bundle_test and not single_symbol_output_bundle_test.get("error"):
                test_proc_logger_main.info(f"OK: Processing for {test_symbol_proc} via bundle method completed.")
                final_df_test_obj = single_symbol_output_bundle_test.get("final_metric_rich_df_obj")
                if isinstance(final_df_test_obj, pd.DataFrame) and not final_df_test_obj.empty:
                    test_proc_logger_main.info(f"  Final DataFrame object shape: {final_df_test_obj.shape}")
                    test_proc_logger_main.info(f"  Columns in final DF from ITS: {final_df_test_obj.columns.tolist()}")
                    # Check for a key v2.3 metric that should be present
                    # Use the configured mspi_col_name for checking
                    mspi_col_to_check = processor_instance_test.trading_system_instance.mspi_col_name if hasattr(processor_instance_test.trading_system_instance, 'mspi_col_name') else 'mspi'

                    if mspi_col_to_check in final_df_test_obj.columns:
                        test_proc_logger_main.info(f"  SUCCESS: Metric '{mspi_col_to_check}' is PRESENT. Mean: {final_df_test_obj[mspi_col_to_check].mean():.3f}")
                    else:
                        test_proc_logger_main.error(f"  ERROR: Metric '{mspi_col_to_check}' is MISSING from final DataFrame from ITS.")

                    if hasattr(processor_instance_test.trading_system_instance, 'a_dag_enabled_its_attr') and \
                       processor_instance_test.trading_system_instance.a_dag_enabled_its_attr and \
                       hasattr(processor_instance_test.trading_system_instance, 'a_dag_output_col_its_attr') and \
                       processor_instance_test.trading_system_instance.a_dag_output_col_its_attr in final_df_test_obj.columns:
                        a_dag_col_name = processor_instance_test.trading_system_instance.a_dag_output_col_its_attr
                        test_proc_logger_main.info(f"  SUCCESS: Metric '{a_dag_col_name}' is PRESENT. Mean: {final_df_test_obj[a_dag_col_name].mean():.3f}")
                    elif hasattr(processor_instance_test.trading_system_instance, 'a_dag_enabled_its_attr') and processor_instance_test.trading_system_instance.a_dag_enabled_its_attr:
                         test_proc_logger_main.warning(f"  NOTE: Metric A-DAG seems enabled in ITS, but column '{getattr(processor_instance_test.trading_system_instance, 'a_dag_output_col_its_attr', 'a_dag')}' not found in output.")


                else:
                    test_proc_logger_main.warning("  Final DataFrame object is empty or not a DataFrame in the bundle.")

                recs_list = single_symbol_output_bundle_test.get("strategy_recommendations", [])
                if recs_list:
                    test_proc_logger_main.info(f"  Generated {len(recs_list)} recommendations. First one: {recs_list[0]}")
                else:
                    test_proc_logger_main.info("  No recommendations generated in this test run.")

            else:
                error_msg_bundle_test = (single_symbol_output_bundle_test or {}).get("error", "Output bundle was None or no error key")
                test_proc_logger_main.error(f"FAIL: Processing for {test_symbol_proc} via bundle method. Error: {error_msg_bundle_test}")

        except Exception as e_main_proc_test:
            test_proc_logger_main.critical(f"Critical error during EnhancedDataProcessor test execution: {e_main_proc_test}", exc_info=True)

    test_proc_logger_main.info("--- EnhancedDataProcessor Standalone Test (V2.1.0 Overhaul) Finished ---")