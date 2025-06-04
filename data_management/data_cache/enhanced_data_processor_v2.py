# enhanced_data_processor_v2.py
# (Elite Version 2.1.1 - Instrumented - CanonRewrite V2.4 Integration - NumPy 2.0 Fix)

# Standard Library Imports
import os
import json
import traceback
import logging
from datetime import datetime, date, time as dt_time, timedelta
import time as pytime # Alias
from typing import Dict, Any, Optional, List, Union, Tuple, Callable

# Third-Party Imports
import pandas as pd
import numpy as np
import copy

# --- Global Logger Setup ---
logger = logging.getLogger(__name__)

# --- Constants ---
DEFAULT_DATA_DIR_PROC: str = "data_processed_output_edp_default_instrumented_v2.3_canon_npfix" 
DEFAULT_CONFIG_PATH_PROC: str = "config_v2.json"
JSON_CONVERSION_ERROR_PLACEHOLDER_PROC = "JSON_CONVERSION_ERROR_IN_PROCESSOR_INSTRUMENTED_V2.3_CANON_NPFIX"

# --- Dummy Trading System (Fallback) ---
class IntegratedTradingSystemDummy:
    def __init__(self, config_path: str = DEFAULT_CONFIG_PATH_PROC):
        self.its_dummy_logger = logger.getChild("IntegratedTradingSystemDummy_In_Instrumented_EDP_v2.3_Canon_NPFix")
        self.its_dummy_logger.critical(f"--- EDP_ITS_DUMMY_V2.3_Canon_NPFix: Fallback ITS __init__ with config: {config_path} ---")
        self.config_path = config_path
        self.config: Dict[str, Any] = {}
        try:
            abs_config_path = config_path
            if not os.path.isabs(config_path):
                script_dir = os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else os.getcwd()
                abs_config_path = os.path.join(script_dir, config_path)
                if not os.path.exists(abs_config_path) and os.path.exists(config_path):
                    abs_config_path = os.path.abspath(config_path) 
            if os.path.exists(abs_config_path) and os.path.isfile(abs_config_path):
                with open(abs_config_path, "r", encoding="utf-8") as f: self.config = json.load(f)
                self.its_dummy_logger.debug(f"Dummy ITS: Successfully loaded config from '{abs_config_path}'.")
            else: self.its_dummy_logger.warning(f"Dummy ITS: Config file '{abs_config_path}' not found or not a file during dummy init.")
        except Exception as e: self.its_dummy_logger.error(f"Dummy ITS: Error loading config '{config_path}': {e}")


    def _get_config_value(self, path: List[str], default_override: Any = None) -> Any:
        current_level = self.config
        try:
            for key_segment in path:
                if isinstance(current_level, dict): current_level = current_level[key_segment]
                else: return default_override
            return current_level
        except (KeyError, TypeError): return default_override
        except Exception as e_get_cfg:
            self.its_dummy_logger.error(f"Dummy ITS _get_config_value error for path {path}: {e_get_cfg}")
            return default_override

    def process_market_data_and_generate_recommendations(self, *args, **kwargs) -> Dict[str, Any]:
        symbol = kwargs.get("symbol", f"DUMMY_SYM_FROM_EDP_DUMMY_ITS_V2.3_Canon_NPFix")
        raw_options_data = kwargs.get("raw_options_data")
        self.its_dummy_logger.warning(f"DUMMY ITS: process_market_data_and_generate_recommendations called for {symbol}.")
        
        dummy_df = raw_options_data.copy() if isinstance(raw_options_data, pd.DataFrame) else pd.DataFrame()
        essential_metric_cols = ['mspi', 'a_dag', 'd_tdpi', 'vri_2_0', 'e_sdag_composite', 'sai', 'ssi']
        for col in essential_metric_cols:
            if col not in dummy_df.columns: dummy_df[col] = 0.0
        
        strike_col_name_dummy = self._get_config_value(["visualization_settings", "mspi_visualizer", "column_names", "strike"], "strike_price")
        if not dummy_df.empty:
            if strike_col_name_dummy not in dummy_df.columns and "strike" in dummy_df.columns:
                dummy_df.rename(columns={'strike': strike_col_name_dummy}, inplace=True)
            elif strike_col_name_dummy not in dummy_df.columns:
                dummy_df[strike_col_name_dummy] = 100.0 
        
        dummy_aggregated_df = dummy_df.groupby(strike_col_name_dummy).first().reset_index() if strike_col_name_dummy in dummy_df.columns and not dummy_df.empty else pd.DataFrame()

        return {
            "symbol": symbol,
            "error": f"ITS DUMMY FALLBACK V2.3_Canon_NPFix (called from Instrumented EDP)",
            "processed_options_df": dummy_df.to_dict(orient='records') if not dummy_df.empty else [],
            "aggregated_strike_data": dummy_aggregated_df.to_dict(orient='records') if not dummy_aggregated_df.empty else [],
            "key_levels": {"all_levels_sorted_by_strength": [], "support_df": pd.DataFrame(), "resistance_df": pd.DataFrame()},
            "signals": {'directional': {'bullish': [], 'bearish': []}}, 
            "recommendations": [{"id": f"DUMMY_REC_V2.3_001", "symbol": symbol, "category": "Dummy Full Process Rec", "rationale": f"ITS DUMMY Used (V2.3_Canon_NPFix EDP)", "status": "NOTE"}],
            "current_mspi_weights_applied": {"dummy_metric_norm": 1.0},
            "current_adaptive_historical_context_summary": {"info": "Dummy ITS (V2.3_Canon_NPFix EDP) has no historical context"},
            "atr_value_used_by_its": 1.0, 
            "final_metric_rich_df_obj": dummy_df 
        }

# --- Real ITS Import ---
RealIntegratedTradingSystem: Optional[type] = None
ITS_IMPORT_ERROR_MSG_EDP: Optional[str] = None
try:
    logger.critical("--- EDP_FILE_LOAD_V2.3_Canon_NPFix: Attempting: from core_analytics.integrated_strategies_v2 import IntegratedTradingSystem ---")
    from core_analytics.integrated_strategies_v2 import IntegratedTradingSystem as ImportedITS
    RealIntegratedTradingSystem = ImportedITS
    logger.critical("--- EDP_FILE_LOAD_V2.3_Canon_NPFix: SUCCESSFULLY imported RealIntegratedTradingSystem from 'core_analytics'. ---")
except ImportError as import_error_its_edp:
    ITS_IMPORT_ERROR_MSG_EDP = f"EDP_FILE_LOAD_V2.3_Canon_NPFix: IMPORT ERROR for ITS (from core_analytics): {import_error_its_edp}"
    logger.critical(f"--- {ITS_IMPORT_ERROR_MSG_EDP} ---", exc_info=True)
except Exception as general_import_error_its_edp:
    ITS_IMPORT_ERROR_MSG_EDP = f"EDP_FILE_LOAD_V2.3_Canon_NPFix: UNEXPECTED IMPORT ERROR for ITS (from core_analytics): {general_import_error_its_edp}"
    logger.critical(f"--- {ITS_IMPORT_ERROR_MSG_EDP} ---", exc_info=True)

if RealIntegratedTradingSystem is None:
    logger.critical("--- EDP_FILE_LOAD_V2.3_Canon_NPFix: RealIntegratedTradingSystem IS STILL NONE after import attempt. This EDP will use DUMMY ITS if instantiated. ---")

class EnhancedDataProcessor:
    def __init__(self, 
                 config_path: str = DEFAULT_CONFIG_PATH_PROC, 
                 data_dir: Optional[str] = None,
                 config_value_getter: Optional[Callable[[List[str], Any], Any]] = None):
        self.init_logger = logger.getChild(f"{self.__class__.__name__}.EDP_Init_Instrumented_v2.3_Canon_NPFix_{id(self)}")
        self.init_logger.critical(f"--- EDP.__INIT__ CALLED --- Version: Instrumented_v2.3_Canon_NPFix")
        self.init_logger.critical(f"--- EDP.__INIT__ [LOG 01_v2]: Received config_path: '{config_path}'")
        self.init_logger.critical(f"--- EDP.__INIT__ [LOG 02_v2]: Received data_dir: '{data_dir}'")
        self.init_logger.critical(f"--- EDP.__INIT__ [LOG 02a_v2_CanonRewrite]: Received config_value_getter type: '{type(config_value_getter).__name__}'")

        self.config_path = config_path 
        self.config_value_getter = config_value_getter 
        self.processor_config: Dict[str, Any] = {}
        self.processed_output_dir: Optional[str] = None
        self.initialization_failed_flag_edp = False

        try:
            if self.config_value_getter is not None and callable(self.config_value_getter):
                self.init_logger.critical(f"--- EDP.__INIT__ [LOG 03a_v2_CanonRewrite]: Attempting to load config using provided 'config_value_getter'. ---")
                try:
                    entire_app_config_from_getter = self.config_value_getter([], None) 
                    if isinstance(entire_app_config_from_getter, dict) and entire_app_config_from_getter:
                        self.processor_config = entire_app_config_from_getter
                        self.init_logger.critical(f"--- EDP.__INIT__ [LOG 03b_v2_CanonRewrite]: Successfully populated processor_config using config_value_getter. Keys: {list(self.processor_config.keys())}")
                        if "_config_file_path" not in self.processor_config and self.config_path and os.path.exists(self.config_path):
                             self.processor_config["_config_file_path"] = os.path.abspath(self.config_path)
                             self.init_logger.debug(f"--- EDP.__INIT__: Ensured _config_file_path in getter-loaded config using original config_path: {self.processor_config['_config_file_path']}")
                    else:
                        self.init_logger.warning(f"--- EDP.__INIT__ [LOG 03c_v2_CanonRewrite]: 'config_value_getter' did not return a valid dictionary (got {type(entire_app_config_from_getter)}). Falling back to _load_main_config_for_processor(). ---")
                        self.processor_config = self._load_main_config_for_processor()
                except Exception as e_getter:
                    self.init_logger.error(f"--- EDP.__INIT__ [LOG 03d_v2_CanonRewrite]: Error using 'config_value_getter': {e_getter}. Falling back to _load_main_config_for_processor(). ---", exc_info=True)
                    self.processor_config = self._load_main_config_for_processor()
            else:
                self.init_logger.critical(f"--- EDP.__INIT__ [LOG 03_v2]: No 'config_value_getter' provided or not callable. Calling _load_main_config_for_processor() with self.config_path = '{self.config_path}' ---")
                self.processor_config = self._load_main_config_for_processor()
            
            self.init_logger.critical(f"--- EDP.__INIT__ [LOG 04_v2]: Config loading done. Processor config loaded: {bool(self.processor_config)}. Keys: {list(self.processor_config.keys()) if self.processor_config else 'None/Empty'}")

            if not self.processor_config:
                self.init_logger.critical("--- EDP.__INIT__ [LOG 04a_v2]: Processor config is empty. This is a critical failure for EDP. Initialization cannot proceed safely. ---")
                self.initialization_failed_flag_edp = True
            
            self.init_logger.critical(f"--- EDP.__INIT__ [LOG 05_v2]: Calculating processed_output_dir. data_dir arg was: '{data_dir}' ---")
            system_settings_cfg = self.processor_config.get("system_settings", {})
            base_data_dir_cfg_val = system_settings_cfg.get("data_directory_base")
            processed_data_subdir_cfg_val = system_settings_cfg.get("processed_data_subdirectory")
            self.init_logger.critical(f"--- EDP.__INIT__ [LOG 06_v2]: From config: base_data_dir='{base_data_dir_cfg_val}', processed_subdir='{processed_data_subdir_cfg_val}'")

            effective_output_dir_name: Optional[str] = None
            config_source_path_for_resolution = self.processor_config.get("_config_file_path", self.config_path) # Use path from loaded config if available

            if base_data_dir_cfg_val and processed_data_subdir_cfg_val:
                config_abs_path_for_resolve = os.path.abspath(config_source_path_for_resolution)
                if os.path.isdir(config_abs_path_for_resolve):
                     config_base_dir_for_paths = config_abs_path_for_resolve
                elif os.path.isfile(config_abs_path_for_resolve):
                     config_base_dir_for_paths = os.path.dirname(config_abs_path_for_resolve)
                else: 
                     config_base_dir_for_paths = os.path.dirname(os.path.abspath(self.config_path))
                     self.init_logger.warning(f"--- EDP.__INIT__ [LOG 07a_v2_CanonRewrite]: config_source_path_for_resolution '{config_source_path_for_resolution}' is not a valid file/dir. Using dirname of initial config_path '{self.config_path}'. Base: '{config_base_dir_for_paths}'")

                self.init_logger.critical(f"--- EDP.__INIT__ [LOG 07_v2]: Base dir for resolving data_directory_base: '{config_base_dir_for_paths}'")
                resolved_base_data_dir = os.path.join(config_base_dir_for_paths, base_data_dir_cfg_val) if not os.path.isabs(base_data_dir_cfg_val) else base_data_dir_cfg_val
                effective_output_dir_name = os.path.join(resolved_base_data_dir, processed_data_subdir_cfg_val)
                self.init_logger.critical(f"--- EDP.__INIT__ [LOG 08_v2]: Path constructed from config: '{effective_output_dir_name}'")
            elif data_dir is not None:
                effective_output_dir_name = data_dir
                self.init_logger.critical(f"--- EDP.__INIT__ [LOG 09_v2]: Using provided data_dir arg for effective_output_dir_name: '{effective_output_dir_name}'")
            else:
                effective_output_dir_name = DEFAULT_DATA_DIR_PROC
                self.init_logger.warning(f"--- EDP.__INIT__ [LOG 10_v2]: Using DEFAULT_DATA_DIR_PROC: '{effective_output_dir_name}'")

            if effective_output_dir_name and os.path.isabs(effective_output_dir_name):
                self.processed_output_dir = effective_output_dir_name
            elif effective_output_dir_name: 
                if base_data_dir_cfg_val and 'config_base_dir_for_paths' in locals() and os.path.isdir(config_base_dir_for_paths):
                    self.processed_output_dir = os.path.abspath(effective_output_dir_name) 
                else: 
                    script_dir_local_eff = os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else os.getcwd()
                    self.processed_output_dir = os.path.join(script_dir_local_eff, effective_output_dir_name)
                    self.processed_output_dir = os.path.abspath(self.processed_output_dir)
            else:
                 self.processed_output_dir = os.path.abspath(DEFAULT_DATA_DIR_PROC)
            self.init_logger.critical(f"--- EDP.__INIT__ [LOG 11_v2]: Final self.processed_output_dir: '{self.processed_output_dir}' ---")

            self.init_logger.critical(f"--- EDP.__INIT__ [LOG 12_v2]: Calling _initialize_trading_system_instance(). Config path for ITS: '{self.config_path}' ---")
            self._initialize_trading_system_instance() 
            self.init_logger.critical(f"--- EDP.__INIT__ [LOG 13_v2]: _initialize_trading_system_instance() DONE. self.trading_system_instance type: {type(getattr(self, 'trading_system_instance', None)).__name__} ---")

            self.init_logger.critical(f"--- EDP.__INIT__ [LOG 14_v2]: Calling _ensure_processed_output_dir_exists() for dir: {self.processed_output_dir} ---")
            self._ensure_processed_output_dir_exists() # This might set initialization_failed_flag_edp
            self.init_logger.critical(f"--- EDP.__INIT__ [LOG 15_v2]: _ensure_processed_output_dir_exists() DONE. ---")

            if self.initialization_failed_flag_edp:
                 self.init_logger.error(f"--- EDP.__INIT__ [LOG 15a_ERROR_v2]: EDP initialization_failed_flag_edp is TRUE. EDP did not fully initialize. ---")
            else:
                self.init_logger.critical(f"--- EDP.__INIT__ [LOG 16_v2]: EnhancedDataProcessor __init__ COMPLETED SUCCESSFULLY. Instance ID: {id(self)} ---")

        except Exception as e_init_edp_outer:
            self.init_logger.critical(f"--- EDP.__INIT__ [LOG 17_CRITICAL_EXCEPTION_OUTER_v2]: Unhandled exception during EnhancedDataProcessor initialization: {e_init_edp_outer} ---", exc_info=True)
            self.initialization_failed_flag_edp = True
            if not hasattr(self, 'trading_system_instance') or self.trading_system_instance is None:
                self.trading_system_instance = IntegratedTradingSystemDummy(config_path=self.config_path)
                self.init_logger.critical("--- EDP.__INIT__ [LOG 17a_ERROR_v2]: Assigned DUMMY ITS due to outer EXCEPTION in EDP __init__. ---")
    
    def _load_main_config_for_processor(self) -> Dict[str, Any]:
        load_cfg_logger = self.init_logger.getChild("LoadConfig_EDP_Internal_v2.3_Canon_NPFix")
        load_cfg_logger.critical(f"--- EDP.LoadConfig_Internal_v2.3_Canon_NPFix [LC_INT 1]: Attempting to load FULL app config from: '{self.config_path}' ---")
        abs_config_path = self.config_path 
        
        if not os.path.isabs(self.config_path):
            script_dir_edp_lc = os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else os.getcwd()
            cwd_path = os.getcwd()
            path_from_script_dir = os.path.join(script_dir_edp_lc, self.config_path)
            path_from_cwd = os.path.join(cwd_path, self.config_path)
            
            if os.path.exists(path_from_cwd) and os.path.isfile(path_from_cwd):
                abs_config_path = path_from_cwd
                load_cfg_logger.critical(f"--- EDP.LoadConfig_Internal_v2.3_Canon_NPFix [LC_INT 2]: Resolved relative config_path via CWD to: '{abs_config_path}'")
            elif os.path.exists(path_from_script_dir) and os.path.isfile(path_from_script_dir):
                abs_config_path = path_from_script_dir
                load_cfg_logger.critical(f"--- EDP.LoadConfig_Internal_v2.3_Canon_NPFix [LC_INT 3]: Resolved relative config_path via script's directory to: '{abs_config_path}'")
            else: 
                abs_config_path = os.path.abspath(self.config_path)
                load_cfg_logger.critical(f"--- EDP.LoadConfig_Internal_v2.3_Canon_NPFix [LC_INT 4]: Could not resolve relatively to existing file, using os.path.abspath on original path: '{abs_config_path}'")
        else:
             load_cfg_logger.critical(f"--- EDP.LoadConfig_Internal_v2.3_Canon_NPFix [LC_INT 5]: config_path is already absolute: '{abs_config_path}'")

        if not os.path.exists(abs_config_path) or not os.path.isfile(abs_config_path):
            load_cfg_logger.critical(f"--- EDP.LoadConfig_Internal_v2.3_Canon_NPFix [LC_INT 6_ERROR]: FULL Config file NOT FOUND or not a file at '{abs_config_path}'. Returning empty dict. ---")
            return {}
        try:
            with open(abs_config_path, "r", encoding="utf-8") as f_cfg:
                full_loaded_config = json.load(f_cfg)
            full_loaded_config["_config_file_path"] = abs_config_path # Store the actual path
            load_cfg_logger.critical(f"--- EDP.LoadConfig_Internal_v2.3_Canon_NPFix [LC_INT 7]: Successfully loaded FULL config from '{abs_config_path}'. ---")
            return full_loaded_config
        except Exception as e_load_cfg_edp:
            load_cfg_logger.critical(f"--- EDP.LoadConfig_Internal_v2.3_Canon_NPFix [LC_INT 8_ERROR]: Error loading FULL config from '{abs_config_path}': {e_load_cfg_edp}. Returning empty dict. ---", exc_info=True)
            return {}

    def _ensure_processed_output_dir_exists(self) -> None:
        ensure_dir_logger = self.init_logger.getChild("EnsureDir_EDP_Internal_v2.3_Canon_NPFix")
        target_dir = self.processed_output_dir
        ensure_dir_logger.critical(f"--- EDP.EnsureDir_Internal_v2.3_Canon_NPFix [ED_INT 1]: Ensuring output directory exists: '{target_dir}'")
        try:
            if target_dir: 
                os.makedirs(target_dir, exist_ok=True)
                ensure_dir_logger.critical(f"--- EDP.EnsureDir_Internal_v2.3_Canon_NPFix [ED_INT 2]: Output directory ensured: '{target_dir}'")
            else:
                ensure_dir_logger.critical(f"--- EDP.EnsureDir_Internal_v2.3_Canon_NPFix [ED_INT 3_ERROR]: self.processed_output_dir is None or empty. Cannot create. ---")
                self.initialization_failed_flag_edp = True 
        except OSError as e_dir_create_edp:
            ensure_dir_logger.critical(f"--- EDP.EnsureDir_Internal_v2.3_Canon_NPFix [ED_INT 4_ERROR]: OSError creating '{target_dir}': {e_dir_create_edp} ---", exc_info=True)
            self.initialization_failed_flag_edp = True
        except Exception as e_ensure_generic:
            ensure_dir_logger.critical(f"--- EDP.EnsureDir_Internal_v2.3_Canon_NPFix [ED_INT 5_ERROR]: Generic Exception creating '{target_dir}': {e_ensure_generic} ---", exc_info=True)
            self.initialization_failed_flag_edp = True

    def _initialize_trading_system_instance(self) -> None:
        init_its_logger = self.init_logger.getChild("InitITS_EDP_Internal_v2.3_Canon_NPFix")
        init_its_logger.critical(f"--- EDP.InitITS_Internal_v2.3_Canon_NPFix [ITS_INT 1]: START - Attempting to initialize self.trading_system_instance ---")

        if RealIntegratedTradingSystem is None:
            init_its_logger.critical(f"--- EDP.InitITS_Internal_v2.3_Canon_NPFix [ITS_INT 2]: RealIntegratedTradingSystem class IS NONE (Import Error: {ITS_IMPORT_ERROR_MSG_EDP}). EDP forced to DUMMY ITS. ---")
            self.trading_system_instance = IntegratedTradingSystemDummy(config_path=self.config_path)
            init_its_logger.critical(f"--- EDP.InitITS_Internal_v2.3_Canon_NPFix [ITS_INT 2a]: Assigned DUMMY ITS. Type: {type(self.trading_system_instance).__name__} ---")
            self.initialization_failed_flag_edp = True 
            return

        init_its_logger.critical(f"--- EDP.InitITS_Internal_v2.3_Canon_NPFix [ITS_INT 3]: RealIntegratedTradingSystem class IS available (Type: {type(RealIntegratedTradingSystem)}). ---")
        try:
            init_its_logger.critical(f"--- EDP.InitITS_Internal_v2.3_Canon_NPFix [ITS_INT 4]: Attempting to instantiate RealIntegratedTradingSystem with config_path: '{self.config_path}' ---")
            self.trading_system_instance = RealIntegratedTradingSystem(config_path=self.config_path)
            init_its_logger.critical(f"--- EDP.InitITS_Internal_v2.3_Canon_NPFix [ITS_INT 5]: RealIntegratedTradingSystem INSTANCE CREATED successfully by EDP. Type: {type(self.trading_system_instance).__name__} ---")
        except Exception as e_init_its_real_edp:
            init_its_logger.critical(f"--- EDP.InitITS_Internal_v2.3_Canon_NPFix [ITS_INT 6_ERROR]: FAILED to instantiate RealIntegratedTradingSystem within EDP: {e_init_its_real_edp} ---", exc_info=True)
            init_its_logger.warning("--- EDP.InitITS_Internal_v2.3_Canon_NPFix [ITS_INT 6a]: Processor falling back to DUMMY ITS due to Real ITS instantiation failure.")
            self.trading_system_instance = IntegratedTradingSystemDummy(config_path=self.config_path)
            self.initialization_failed_flag_edp = True 
        
        init_its_logger.critical(f"--- EDP.InitITS_Internal_v2.3_Canon_NPFix [ITS_INT 7]: END _initialize_trading_system_instance. Final ITS type: {type(getattr(self, 'trading_system_instance', None)).__name__} ---")

    def _validate_input_data(self, options_chain_df: Optional[pd.DataFrame], symbol: str) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
        val_logger = logger.getChild(f"{self.__class__.__name__}.ValidateInput_EDP_v2.3_Canon_NPFix")
        val_logger.critical(f"--- EDP._validate_input_data for {symbol} CALLED ---")
        if options_chain_df is None or not isinstance(options_chain_df, pd.DataFrame) or options_chain_df.empty:
            error_msg = f"Input options chain data for {symbol} missing, empty, or invalid type ({type(options_chain_df)})."
            val_logger.critical(f"--- EDP._validate_input_data ERROR: {error_msg} ---")
            return None, error_msg
        val_logger.critical(f"--- EDP._validate_input_data for {symbol} PASSED (basic check) ---")
        return options_chain_df.copy(), None

    def _prepare_dataframe(self, df_to_prepare: pd.DataFrame, underlying_data_bundle: Optional[Dict[str,Any]], symbol_str: str) -> pd.DataFrame:
        prep_logger = logger.getChild(f"{self.__class__.__name__}.PrepareDataFrame_EDP_v2.3_Canon_NPFix")
        prep_logger.critical(f"--- EDP._prepare_dataframe for {symbol_str} CALLED ---")
        df_prepared = df_to_prepare.copy()
        
        expected_strike_col_by_its = self.processor_config.get("visualization_settings", {}).get("mspi_visualizer", {}).get("column_names", {}).get("strike", "strike_price")
        prep_logger.critical(f"--- EDP._prepare_dataframe ({symbol_str}): Expected strike col by ITS config (from processor_config): '{expected_strike_col_by_its}' ---")

        current_strike_col_in_df = None
        if expected_strike_col_by_its in df_prepared.columns:
            current_strike_col_in_df = expected_strike_col_by_its
        elif "strike" in df_prepared.columns: 
            current_strike_col_in_df = "strike"
            prep_logger.info(f"--- EDP._prepare_dataframe ({symbol_str}): Expected strike column '{expected_strike_col_by_its}' not found. Found and using generic 'strike' column. ---")
        
        if current_strike_col_in_df and current_strike_col_in_df != expected_strike_col_by_its:
            prep_logger.critical(f"--- EDP._prepare_dataframe ({symbol_str}): Renaming DataFrame column '{current_strike_col_in_df}' to ITS expected '{expected_strike_col_by_its}'. ---")
            df_prepared.rename(columns={current_strike_col_in_df: expected_strike_col_by_its}, inplace=True)
        elif not current_strike_col_in_df:
            prep_logger.critical(f"--- EDP._prepare_dataframe ERROR ({symbol_str}): CRITICAL - Strike column ('{expected_strike_col_by_its}' or 'strike') not found in DataFrame! Adding dummy '{expected_strike_col_by_its}'. ---")
            df_prepared[expected_strike_col_by_its] = 0.0 
        
        prep_logger.critical(f"--- EDP._prepare_dataframe for {symbol_str} COMPLETED. Columns: {df_prepared.columns.tolist()} ---")
        return df_prepared

    def _apply_integrated_strategies(
        self,
        df_prepared_input: pd.DataFrame,
        underlying_data_bundle_from_fetcher: Dict[str, Any],
        market_context_for_its: Dict[str, Any],
        historical_ohlc_data_for_atr: Optional[pd.DataFrame],
        symbol_str_context: str,
        expiration_calendar_for_its: Optional[List[date]] = None
    ) -> Tuple[Dict[str, Any], Optional[str]]:
        apply_strat_logger = logger.getChild(f"{self.__class__.__name__}.ApplyITS_EDP_Instrumented_v2.3_Canon_NPFix")
        apply_strat_logger.critical(f"--- EDP.ApplyITS_Internal_v2.3_Canon_NPFix [AIS01] ({symbol_str_context}): START. Using ITS Type: {type(self.trading_system_instance).__name__} ---")
        its_output_bundle: Optional[Dict[str, Any]] = None
        processing_error_output: Optional[str] = None
        try:
            current_underlying_price_for_its = underlying_data_bundle_from_fetcher.get("price")
            if current_underlying_price_for_its is None:
                apply_strat_logger.critical(f"--- EDP.ApplyITS_Internal_v2.3_Canon_NPFix [AIS02_ERROR] ({symbol_str_context}): Missing current_underlying_price for ITS. ---")
                raise ValueError("Missing current_underlying_price for ITS processing.")

            its_kwargs = {
                "symbol": symbol_str_context, "raw_options_data": df_prepared_input,
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
            apply_strat_logger.critical(f"--- EDP.ApplyITS_Internal_v2.3_Canon_NPFix [AIS03] ({symbol_str_context}): Calling ITS process_market_data_and_generate_recommendations... ---")
            if not hasattr(self.trading_system_instance, 'process_market_data_and_generate_recommendations') or \
               not callable(getattr(self.trading_system_instance, 'process_market_data_and_generate_recommendations')):
                raise AttributeError(f"ITS instance of type {type(self.trading_system_instance).__name__} does not have a callable 'process_market_data_and_generate_recommendations' method.")

            its_output_bundle = self.trading_system_instance.process_market_data_and_generate_recommendations(**its_kwargs)
            apply_strat_logger.critical(f"--- EDP.ApplyITS_Internal_v2.3_Canon_NPFix [AIS04] ({symbol_str_context}): ITS call completed. Error in bundle: {its_output_bundle.get('error') if isinstance(its_output_bundle, dict) else 'ITS returned non-dict'} ---")

            if not isinstance(its_output_bundle, dict):
                raise TypeError(f"ITS instance for {symbol_str_context} returned type {type(its_output_bundle)}, expected dict.")
        except Exception as e_apply_its_internal:
            processing_error_output = f"Error during ITS processing for {symbol_str_context}: {type(e_apply_its_internal).__name__} - {e_apply_its_internal}"
            apply_strat_logger.critical(f"--- EDP.ApplyITS_Internal_v2.3_Canon_NPFix [AIS05_ERROR] ({symbol_str_context}): Exception: {processing_error_output} ---", exc_info=True)
            if its_output_bundle is None: its_output_bundle = {}
            its_output_bundle["error"] = processing_error_output 
            its_output_bundle.setdefault("processed_options_df", df_prepared_input.to_dict(orient='records') if isinstance(df_prepared_input, pd.DataFrame) and not df_prepared_input.empty else [])
            its_output_bundle.setdefault("final_metric_rich_df_obj", df_prepared_input) 
            its_output_bundle.setdefault("key_levels", {})
            its_output_bundle.setdefault("signals", {})
            its_output_bundle.setdefault("recommendations", [])
        apply_strat_logger.critical(f"--- EDP.ApplyITS_Internal_v2.3_Canon_NPFix [AIS06] ({symbol_str_context}): END ---")
        return its_output_bundle, processing_error_output

    def _package_results(self, symbol_str_pkg: str, fetch_ts_pkg: Optional[str],
                         its_bundle_pkg: Dict[str, Any],
                         underlying_data_pkg: Optional[Dict[str,Any]],
                         market_context_data_pkg: Optional[Dict[str,Any]],
                         processor_config_snapshot_pkg: Dict[str,Any], 
                         processing_error_msg: Optional[str] = None
                         ) -> Dict[str, Any]:
        pkg_logger = logger.getChild(f"{self.__class__.__name__}.PackageResults_EDP_v2.3_Canon_NPFix")
        pkg_logger.critical(f"--- EDP._package_results_v2.3_Canon_NPFix for {symbol_str_pkg} CALLED ---")
        bundle:Dict[str,Any]={
            "symbol":str(symbol_str_pkg).upper(), "fetch_timestamp":fetch_ts_pkg,
            "processing_timestamp":datetime.now().isoformat(), "processor_version":"2.3.0-CanonRewrite_NPFix", 
            "error": processing_error_msg or its_bundle_pkg.get("error"),
            "processed_data": {"options_chain": self._convert_to_json_safe(its_bundle_pkg.get("processed_options_df",[]))},
            "key_levels": self._convert_to_json_safe(its_bundle_pkg.get("key_levels", {})),
            "trading_signals": self._convert_to_json_safe(its_bundle_pkg.get("signals", {})),
            "strategy_recommendations": self._convert_to_json_safe(its_bundle_pkg.get("recommendations", [])),
            "underlying": self._convert_to_json_safe(underlying_data_pkg or {}),
            "market_context": self._convert_to_json_safe(market_context_data_pkg or {}),
            "atr_value_used": self._convert_scalar_to_json_safe(its_bundle_pkg.get("atr_value_used_by_its", its_bundle_pkg.get("atr_value_used"))),
            "current_mspi_weights_applied": self._convert_to_json_safe(its_bundle_pkg.get("current_mspi_weights_applied", {})),
            "current_adaptive_historical_context_summary": self._convert_to_json_safe(its_bundle_pkg.get("current_adaptive_historical_context_summary", {})),
            "final_metric_rich_df_obj": its_bundle_pkg.get("final_metric_rich_df_obj", pd.DataFrame()),
            "historical_ohlc_df_obj": (market_context_data_pkg or {}).get("historical_ohlcv_df"),
            "expiration_calendar_used": (market_context_data_pkg or {}).get("expiration_calendar_used")
        }
        pkg_logger.critical(f"--- EDP._package_results_v2.3_Canon_NPFix for {symbol_str_pkg} COMPLETED ---")
        return bundle

    def _convert_scalar_to_json_safe(self, scalar_data: Any) -> Any:
        if pd.isna(scalar_data) or scalar_data is None: return None
        if isinstance(scalar_data, (datetime, date, pd.Timestamp)): return scalar_data.isoformat()
        
        if isinstance(scalar_data, np.integer): return int(scalar_data) 
        if isinstance(scalar_data, np.floating): # Use np.floating for all NumPy float types
            if np.isinf(scalar_data): return "Infinity" if scalar_data > 0 else "-Infinity"
            if np.isnan(scalar_data): return None
            return float(scalar_data)
        if isinstance(scalar_data, np.bool_): return bool(scalar_data) 
        
        # Check for Python native float after NumPy specific checks
        if isinstance(scalar_data, float):
            if np.isinf(scalar_data): return "Infinity" if scalar_data > 0 else "-Infinity"
            if np.isnan(scalar_data): return None
            return float(scalar_data)
            
        if isinstance(scalar_data, (int, bool, str)): # Python native int, bool, str
            return scalar_data
        
        if isinstance(scalar_data, timedelta): return scalar_data.total_seconds()
        
        # Fallback for other types, attempt to convert to string if direct JSON dump fails
        try:
            json.dumps(scalar_data) # Test serializability
            return scalar_data
        except (TypeError, OverflowError):
            try:
                return str(scalar_data)
            except Exception:
                logger.getChild(f"{self.__class__.__name__}._ConvertScalar").error(f"Failed to convert scalar type '{type(scalar_data)}' to a JSON-safe string. Returning placeholder.")
                return f"{JSON_CONVERSION_ERROR_PLACEHOLDER_PROC}: Unserializable_Scalar_{type(scalar_data).__name__}"

    def _convert_to_json_safe(self, data_to_convert: Any) -> Any:
        json_safe_logger = logger.getChild(f"{self.__class__.__name__}._ConvertToJSONSafe_v2.3_Canon_NPFix")
        try:
            if isinstance(data_to_convert, pd.DataFrame):
                if data_to_convert.empty: return []
                df_copy = data_to_convert.copy(deep=True)
                for col in df_copy.select_dtypes(include=['datetime64[ns]', 'datetime64[ns, UTC]', 'datetimetz']).columns:
                    try: df_copy[col] = df_copy[col].dt.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
                    except AttributeError: df_copy[col] = df_copy[col].apply(lambda x: x.isoformat() if hasattr(x, 'isoformat') else (str(x) if pd.notna(x) else None))
                    df_copy[col] = df_copy[col].replace({pd.NaT: None})
                for col in df_copy.columns:
                    if not df_copy[col].empty:
                        first_valid_element = df_copy[col].dropna().iloc[0] if not df_copy[col].dropna().empty else None
                        if isinstance(first_valid_element, date) and not isinstance(first_valid_element, datetime):
                            df_copy[col] = df_copy[col].apply(lambda x: x.isoformat() if isinstance(x, date) and pd.notna(x) else None)
                for col in df_copy.select_dtypes(include=np.number).columns:
                    df_copy[col] = df_copy[col].replace([np.inf, -np.inf], ["Infinity", "-Infinity"])
                    df_copy[col] = df_copy[col].astype(object).where(pd.notna(df_copy[col]) & (df_copy[col] != "Infinity") & (df_copy[col] != "-Infinity"),
                                                                    df_copy[col].where((df_copy[col] == "Infinity") | (df_copy[col] == "-Infinity"), None))
                return [self._convert_to_json_safe(record) for record in df_copy.to_dict(orient='records')]
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
        bundle_proc_logger = logger.getChild(f"{self.__class__.__name__}.ProcessBundle_EDP_Instrumented_v2.3_Canon_NPFix")
        bundle_proc_logger.critical(f"--- EDP.PROCESS_MARKET_DATA_BUNDLE_V2.3_Canon_NPFix --- START --- Symbols: {list(market_data_from_fetcher.keys())}")
        
        if self.initialization_failed_flag_edp:
            bundle_proc_logger.critical("--- EDP.PROCESS_BUNDLE_V2.3_Canon_NPFix [PB02_ERROR]: EDP initialization failed earlier. Returning error bundle for all symbols. ---")
            return {sym: {"error": "EnhancedDataProcessor failed to initialize properly.", "symbol":sym} for sym in market_data_from_fetcher.keys()}
        
        if not hasattr(self, 'trading_system_instance') or self.trading_system_instance is None:
            bundle_proc_logger.critical("--- EDP.PROCESS_BUNDLE_V2.3_Canon_NPFix [PB03_ERROR]: self.trading_system_instance is not set (None). This is critical. Cannot process. ---")
            self._initialize_trading_system_instance() 
            if not hasattr(self, 'trading_system_instance') or self.trading_system_instance is None:
                 bundle_proc_logger.critical("--- EDP.PROCESS_BUNDLE_V2.3_Canon_NPFix [PB03a_ERROR]: Re-init of ITS also failed to set instance. Returning error bundle. ---")
                 return {sym: {"error": "EDP's trading_system_instance is critically uninitialized.", "symbol":sym} for sym in market_data_from_fetcher.keys()}
            bundle_proc_logger.warning(f"--- EDP.PROCESS_BUNDLE_V2.3_Canon_NPFix [PB03b_WARN]: self.trading_system_instance was None, re-initialized to: {type(self.trading_system_instance).__name__}. Proceeding. ---")

        all_symbols_processed_output: Dict[str, Dict[str, Any]] = {}
        for symbol_str, symbol_data_bundle in market_data_from_fetcher.items():
            bundle_proc_logger.critical(f"--- EDP.PROCESS_BUNDLE_V2.3_Canon_NPFix [PB04]: Processing symbol '{symbol_str}' ---")
            symbol_proc_start_time_py = pytime.time()
            try:
                options_data_raw = symbol_data_bundle.get("options_chain")
                if isinstance(options_data_raw, pd.DataFrame): options_df_input = options_data_raw
                elif isinstance(options_data_raw, list) and (not options_data_raw or isinstance(options_data_raw[0], dict)): options_df_input = pd.DataFrame(options_data_raw)
                else: options_df_input = pd.DataFrame() 
                
                underlying_info_input = symbol_data_bundle.get("underlying", {})
                fetcher_error_msg = symbol_data_bundle.get("error")

                if fetcher_error_msg:
                    bundle_proc_logger.error(f"--- EDP.PROCESS_BUNDLE_V2.3_Canon_NPFix ({symbol_str}): Error from fetcher: {fetcher_error_msg}. Skipping processing, packaging error. ---")
                    its_bundle_err = {"error": fetcher_error_msg, "processed_options_df": []} 
                    all_symbols_processed_output[symbol_str] = self._package_results(symbol_str, (underlying_info_input or {}).get("fetch_timestamp"), its_bundle_err, underlying_info_input, {}, self.processor_config, fetcher_error_msg)
                    continue

                df_validated, validation_error_msg = self._validate_input_data(options_df_input, symbol_str)
                if validation_error_msg or df_validated is None: 
                    bundle_proc_logger.critical(f"--- EDP.PROCESS_BUNDLE_V2.3_Canon_NPFix [PB_VALIDATE_FAIL] ({symbol_str}): Validation failed: {validation_error_msg} ---")
                    validated_df_list = df_validated.to_dict(orient='records') if isinstance(df_validated, pd.DataFrame) and not df_validated.empty else []
                    its_bundle_err = {"error": validation_error_msg, "processed_options_df": validated_df_list}
                    all_symbols_processed_output[symbol_str] = self._package_results(symbol_str, (underlying_info_input or {}).get("fetch_timestamp"), its_bundle_err, underlying_info_input, {}, self.processor_config, validation_error_msg)
                    continue

                df_prepared = self._prepare_dataframe(df_validated, underlying_info_input, symbol_str)
                
                current_market_context_for_its_call: Dict[str, Any] = {"current_time": datetime.now().time(), "current_iv": (underlying_info_input or {}).get("volatility")}
                symbol_tradier_iv_quote_specific = (tradier_context_data or {}).get(symbol_str, {}).get("iv_and_quote_data", {})
                if isinstance(symbol_tradier_iv_quote_specific, dict): current_market_context_for_its_call.update(symbol_tradier_iv_quote_specific)

                bundle_proc_logger.critical(f"--- EDP.PROCESS_BUNDLE_V2.3_Canon_NPFix [PB05] ({symbol_str}): Calling _apply_integrated_strategies. self.trading_system_instance is {type(self.trading_system_instance).__name__} ---")
                its_bundle, its_processing_error = self._apply_integrated_strategies(
                    df_prepared_input=df_prepared, 
                    underlying_data_bundle_from_fetcher=underlying_info_input, 
                    market_context_for_its=current_market_context_for_its_call, 
                    historical_ohlc_data_for_atr=(tradier_context_data or {}).get(symbol_str, {}).get("historical_ohlcv_df"), 
                    symbol_str_context=symbol_str,
                    expiration_calendar_for_its=(expiration_calendars_by_symbol or {}).get(symbol_str) 
                )
                bundle_proc_logger.critical(f"--- EDP.PROCESS_BUNDLE_V2.3_Canon_NPFix [PB06] ({symbol_str}): _apply_integrated_strategies DONE. Error in ITS bundle: {its_bundle.get('error')} ---")
                
                market_context_for_packaging = {
                    "iv_and_quote_data": (tradier_context_data or {}).get(symbol_str, {}).get("iv_and_quote_data"),
                    "historical_ohlcv_df": (tradier_context_data or {}).get(symbol_str, {}).get("historical_ohlcv_df"), 
                    "expiration_calendar_used": (expiration_calendars_by_symbol or {}).get(symbol_str) 
                }
                all_symbols_processed_output[symbol_str] = self._package_results(
                    symbol_str_pkg=symbol_str, fetch_ts_pkg=(underlying_info_input or {}).get("fetch_timestamp"),
                    its_bundle_pkg=its_bundle, underlying_data_pkg=underlying_info_input,
                    market_context_data_pkg=market_context_for_packaging,
                    processor_config_snapshot_pkg=self.processor_config, 
                    processing_error_msg=its_bundle.get("error") 
                )
                bundle_proc_logger.info(f"--- Finished processing {symbol_str} in {pytime.time() - symbol_proc_start_time_py:.3f}s. Packaged error: {all_symbols_processed_output[symbol_str].get('error')} ---")
            except Exception as e_sym_proc:
                bundle_proc_logger.critical(f"--- EDP.PROCESS_BUNDLE_V2.3_Canon_NPFix [PB07_ERROR] ({symbol_str}): Unhandled Exception in symbol processing loop: {type(e_sym_proc).__name__} - {e_sym_proc} ---", exc_info=True)
                all_symbols_processed_output[symbol_str] = {
                    "symbol":symbol_str, "error": f"Major exception processing {symbol_str}: {type(e_sym_proc).__name__} - {str(e_sym_proc)[:150]}",
                    "fetch_timestamp": symbol_data_bundle.get("underlying", {}).get("fetch_timestamp", datetime.now().isoformat()),
                    "processing_timestamp": datetime.now().isoformat(), "processor_version":f"2.3.0-CanonRewrite_NPFix_ErrorState",
                    "processed_data": {"options_chain": []}, "final_metric_rich_df_obj": pd.DataFrame() 
                }
        bundle_proc_logger.critical(f"--- EDP.PROCESS_MARKET_DATA_BUNDLE_V2.3_Canon_NPFix --- END ---")
        return all_symbols_processed_output

# --- Standalone Test Block ---
if __name__ == "__main__":
    if not logging.getLogger().hasHandlers():
        logging.basicConfig(level=logging.DEBUG, format="[%(levelname)s] (%(name)s:%(filename)s:%(lineno)d) %(asctime)s - %(message)s")
    
    standalone_test_logger_edp = logging.getLogger("EDP_Standalone_Test_Instrumented_v2.3_Canon_NPFix")
    standalone_test_logger_edp.setLevel(logging.DEBUG) 
    logger.setLevel(logging.DEBUG) 
    logging.getLogger("EnhancedDataProcessor.Init").setLevel(logging.DEBUG)
    logging.getLogger("EnhancedDataProcessor.LoadConfig_EDP_Internal_v2.3_Canon_NPFix").setLevel(logging.DEBUG)
    logging.getLogger("EnhancedDataProcessor.EnsureDir_EDP_Internal_v2.3_Canon_NPFix").setLevel(logging.DEBUG)
    logging.getLogger("EnhancedDataProcessor.InitITS_EDP_Internal_v2.3_Canon_NPFix").setLevel(logging.DEBUG)
    logging.getLogger("EnhancedDataProcessor.ValidateInput_EDP_v2.3_Canon_NPFix").setLevel(logging.DEBUG)
    logging.getLogger("EnhancedDataProcessor.PrepareDataFrame_EDP_v2.3_Canon_NPFix").setLevel(logging.DEBUG)
    logging.getLogger("EnhancedDataProcessor.ApplyITS_EDP_Instrumented_v2.3_Canon_NPFix").setLevel(logging.DEBUG)
    logging.getLogger("EnhancedDataProcessor.PackageResults_EDP_v2.3_Canon_NPFix").setLevel(logging.DEBUG)
    logging.getLogger("EnhancedDataProcessor._ConvertToJSONSafe_v2.3_Canon_NPFix").setLevel(logging.DEBUG)
    logging.getLogger("EnhancedDataProcessor._ConvertScalar").setLevel(logging.DEBUG)

    standalone_test_logger_edp.critical("--- EDP Standalone Test (Instrumented_v2.3_Canon_NPFix) START ---")
    
    script_dir_edp_main = os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else os.getcwd()
    project_root_from_script = os.path.dirname(script_dir_edp_main) 
    config_path_for_standalone_test_edp = os.path.join(project_root_from_script, "config_v2.json")
    if not os.path.exists(config_path_for_standalone_test_edp):
        config_path_for_standalone_test_edp = os.path.join(script_dir_edp_main, "config_v2.json")

    standalone_test_logger_edp.critical(f"--- EDP Standalone Test: Using config path: {config_path_for_standalone_test_edp}")

    if not os.path.exists(config_path_for_standalone_test_edp):
        standalone_test_logger_edp.critical(f"--- EDP Standalone Test: Config file '{config_path_for_standalone_test_edp}' NOT FOUND. ---")
    
    try:
        standalone_test_logger_edp.critical("--- EDP Standalone Test: Attempting to instantiate Instrumented EnhancedDataProcessor ---")
        edp_instance_standalone = EnhancedDataProcessor(config_path=config_path_for_standalone_test_edp, config_value_getter=None)
        
        standalone_test_logger_edp.critical(
            f"--- EDP Standalone Test: Instrumented EnhancedDataProcessor instantiated. "
            f"InitFailFlag: {getattr(edp_instance_standalone, 'initialization_failed_flag_edp', 'FlagMissing')}. "
            f"ITS type: {type(getattr(edp_instance_standalone, 'trading_system_instance', None)).__name__} ---"
        )
        
        if not getattr(edp_instance_standalone, 'initialization_failed_flag_edp', True): 
            standalone_test_logger_edp.critical("--- EDP Standalone Test: EDP instance seems OK. Proceeding with dummy data processing test. ---")
            
            strike_col_from_config = edp_instance_standalone.processor_config.get("visualization_settings", {}).get("mspi_visualizer", {}).get("column_names", {}).get("strike", "strike_price")

            dummy_cv_data = { 
                "options_chain": pd.DataFrame([{
                    strike_col_from_config: 100, 
                    'opt_kind': 'call', 'price': 10.0, 'underlying_symbol': 'DUMMY', 
                    'expiration_date': date.today().isoformat(), 
                    'delta': 0.5, 'oi': 100, 'volm': 50, 'gamma':0.02, 'vega':0.1, 'theta':-0.05, 'volatility':0.30
                }]), 
                "underlying": {"symbol": "DUMMY", "price": 100.0, "fetch_timestamp": datetime.now().isoformat()}, "error": None 
            }
            mock_market_data = {"DUMMY": dummy_cv_data}
            
            standalone_test_logger_edp.critical("--- EDP Standalone Test: Calling process_market_data_bundle with dummy data... ---")
            result_bundle = edp_instance_standalone.process_market_data_bundle(mock_market_data)
            
            dummy_output = result_bundle.get('DUMMY', {})
            standalone_test_logger_edp.critical(f"--- EDP Standalone Test: process_market_data_bundle result for DUMMY: Error='{dummy_output.get('error', 'No error key')}' ---")
            
            final_df_obj_test = dummy_output.get('final_metric_rich_df_obj')
            if isinstance(final_df_obj_test, pd.DataFrame):
                standalone_test_logger_edp.critical(f"--- EDP Standalone Test: final_metric_rich_df_obj shape: {final_df_obj_test.shape} ---")
                if not final_df_obj_test.empty:
                     standalone_test_logger_edp.critical(f"  Columns in final DF: {final_df_obj_test.columns.tolist()}")
            else:
                standalone_test_logger_edp.warning(f"--- EDP Standalone Test: final_metric_rich_df_obj is not a DataFrame (type: {type(final_df_obj_test)}). ---")
        else:
            standalone_test_logger_edp.error("--- EDP Standalone Test: EDP instance initialization failed. Cannot proceed with processing test. ---")

    except Exception as e_standalone_test:
        standalone_test_logger_edp.critical(f"--- EDP Standalone Test: CRITICAL EXCEPTION during test: {e_standalone_test} ---", exc_info=True)
    standalone_test_logger_edp.critical("--- EDP Standalone Test (Instrumented_v2.3_Canon_NPFix) END ---")