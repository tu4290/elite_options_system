#!/usr/bin/env python3
# enhanced_data_processor_v2.py
# Elite Options Trading System - Enhanced Data Processor
# Version: EOTS EDP v3.2.1 - Timestamp Fix & IDS Sync
# Description: This version incorporates significantly enhanced logging,
#              meticulous synchronization with ids.py, and fixes for
#              COL_EDP_PREPARATION_TIMESTAMP_EDP.

# Standard Library Imports
import os
import sys
import json
import logging
import importlib.util 
import traceback
from datetime import datetime, date, time as dt_time, timedelta
import time as pytime 
from typing import Dict, Any, Optional, List, Union, Tuple, Callable, Type, Set
from concurrent.futures import ThreadPoolExecutor, as_completed
import copy

# Third-Party Imports
import pandas as pd
import numpy as np

# --- EOTS Project Imports ---
try:
    from utils import ids 
    from core_analytics import impact_calculations 
    from core_analytics import integrated_strategies_v2 

    IDS_IMPORTED_SUCCESSFULLY_EDP = True
    CORE_ANALYTICS_MODULES_AVAILABLE_EDP = True
    logger_edp_module_init = logging.getLogger("EDP_ModuleInit_v321") # Changed version
    logger_edp_module_init.info("EDP (v3.2.1): 'utils.ids' and 'core_analytics' modules imported successfully.")
except ImportError as e_module_import_edp_v321:
    print(f"CRITICAL ERROR (EnhancedDataProcessor v3.2.1): Could not import 'utils.ids' or 'core_analytics' modules. Error: {e_module_import_edp_v321}")
    IDS_IMPORTED_SUCCESSFULLY_EDP = False
    CORE_ANALYTICS_MODULES_AVAILABLE_EDP = False
    
    class ids: # type: ignore
        COL_STRIKE = "strike_price"; CV_UND_PARAM_PRICE = "price"; CV_UND_PARAM_FETCH_TIMESTAMP = "fetch_timestamp"
        COL_UNDERLYING_SYMBOL_CHAIN = "underlying_symbol"; COL_CURRENT_PRICE_EDP = "current_price"
        COL_DISTANCE_FROM_CURRENT_EDP = "distance_from_current"; COL_PCT_DISTANCE_FROM_CURRENT_EDP = "pct_distance_from_current"
        COL_FETCH_TIMESTAMP_EDP = "fetch_timestamp"; 
        COL_EDP_PREPARATION_TIMESTAMP_EDP = "edp_dataframe_preparation_timestamp" # Corrected Fallback
        COL_IMPACT_DELTA_RAW = 'delta_impact'; COL_IMPACT_GAMMA_RAW = 'gamma_impact'; COL_IMPACT_VEGA_RAW = 'vega_impact'
        COL_IMPACT_THETA_RAW = 'theta_impact'; COL_IMPACT_VOLUME_RAW = 'volume_impact'; COL_IMPACT_VALUE_RAW = 'value_impact'
        COL_CHART_HEURISTIC_NET_DELTA_PRESSURE = 'heuristic_net_delta_pressure'; COL_CHART_NET_GAMMA_FLOW = 'net_gamma_flow'
        COL_CHART_NET_VEGA_FLOW = 'net_vega_flow'; COL_CHART_NET_THETA_EXPOSURE = 'net_theta_exposure'
        COL_CHART_NET_VOLUME_PRESSURE = 'net_volume_pressure'; COL_CHART_NET_VALUE_PRESSURE = 'net_value_pressure'
        CFG_VIZ_COL_STRIKE = ["visualization_settings", "mspi_visualizer", "column_names", "strike"] 
        COL_OPTION_SYMBOL = "symbol"; COL_MSPI_SCORE = "mspi"; COL_OPT_KIND = "opt_kind"
        COL_SAI="sai"; COL_SSI="ssi"; COL_ARFI="arfi";
        COL_DAG_CUSTOM_RAW="dag_custom"; COL_TDPI_RAW="tdpi"; COL_VRI_RAW="vri";
        COL_SDAG_MULTIPLICATIVE_RAW="sdag_multiplicative"; COL_SDAG_DIRECTIONAL_RAW="sdag_directional";
        COL_SDAG_WEIGHTED_RAW="sdag_weighted"; COL_SDAG_VOLATILITY_FOCUSED_RAW="sdag_volatility_focused";
        COL_DAG_CUSTOM_NORM="dag_custom_norm"; COL_TDPI_NORM="tdpi_norm"; COL_VRI_NORM="vri_norm";
        COL_SDAG_MULTIPLICATIVE_NORM="sdag_multiplicative_norm"; COL_SDAG_DIRECTIONAL_NORM="sdag_directional_norm";
        COL_SDAG_WEIGHTED_NORM="sdag_weighted_norm"; COL_SDAG_VOLATILITY_FOCUSED_NORM="sdag_volatility_focused_norm";
        CV_CHAIN_PARAM_DXVOLM = "dxvolm"; CV_CHAIN_PARAM_GXVOLM = "gxvolm"
        CV_UND_PARAM_IV_PERCENTILE_30D = "iv_percentile_30d"
        COL_OI_CHG_TEMP = "oi_chg_temp" 
        CFG_CONFIG_FILE_PATH_CACHED_AT = "_config_file_path_cached_at" # Added fallback

    class impact_calculations: # type: ignore
        @staticmethod
        def calculate_delta_impact(df, *args, **kwargs): df[ids.COL_IMPACT_DELTA_RAW] = 0.0; return df # Use COL_ prefix
        @staticmethod
        def calculate_gamma_impact(df, *args, **kwargs): df[ids.COL_IMPACT_GAMMA_RAW] = 0.0; return df # Use COL_ prefix
        @staticmethod
        def calculate_vega_impact(df, *args, **kwargs): df[ids.COL_IMPACT_VEGA_RAW] = 0.0; return df # Use COL_ prefix
        @staticmethod
        def calculate_theta_impact(df, *args, **kwargs): df[ids.COL_IMPACT_THETA_RAW] = 0.0; return df # Use COL_ prefix
        @staticmethod
        def calculate_volume_impact(df, *args, **kwargs): df[ids.COL_IMPACT_VOLUME_RAW] = 0.0; return df # Use COL_ prefix
        @staticmethod
        def calculate_value_impact(df, *args, **kwargs): df[ids.COL_IMPACT_VALUE_RAW] = 0.0; return df # Use COL_ prefix

    class integrated_strategies_v2: # type: ignore
        class IntegratedTradingSystem: 
            def __init__(self, *args, **kwargs): 
                self.logger = logging.getLogger("DummyITS_EDP_v321")
                self.logger.warning("Initialized DUMMY IntegratedTradingSystem due to import failures in EDP.")
            def process_market_data_and_generate_recommendations(self, **kwargs) -> Dict[str, Any]:
                symbol = kwargs.get("symbol", "DUMMY_ITS_CALL_EDP_v321")
                self.logger.warning(f"DummyITS.process_market_data_and_generate_recommendations called for {symbol}")
                df_input = kwargs.get("raw_options_data", pd.DataFrame())
                if not isinstance(df_input, pd.DataFrame): df_input = pd.DataFrame()
                metric_cols_to_ensure = [
                    ids.COL_MSPI_SCORE, ids.COL_SAI, ids.COL_SSI, ids.COL_ARFI, ids.COL_DAG_CUSTOM_RAW, 
                    ids.COL_TDPI_RAW, ids.COL_VRI_RAW, ids.COL_SDAG_MULTIPLICATIVE_RAW, 
                    ids.COL_SDAG_DIRECTIONAL_RAW, ids.COL_SDAG_WEIGHTED_RAW, ids.COL_SDAG_VOLATILITY_FOCUSED_RAW,
                    ids.COL_DAG_CUSTOM_NORM, ids.COL_TDPI_NORM, ids.COL_VRI_NORM, 
                    ids.COL_SDAG_MULTIPLICATIVE_NORM, ids.COL_SDAG_DIRECTIONAL_NORM, 
                    ids.COL_SDAG_WEIGHTED_NORM, ids.COL_SDAG_VOLATILITY_FOCUSED_NORM
                ]
                for col in metric_cols_to_ensure:
                    if col not in df_input.columns: df_input[col] = 0.0
                return {"symbol": symbol, "error": "DummyITS Active in EDP v3.2.1 (Core Analytics or IDS Load Issue)",
                        "final_metric_rich_df_obj": df_input.copy(),
                        "processed_options_df": df_input.to_dict(orient='records'),
                        "aggregated_strike_data": [], "key_levels": {"error": "Dummy ITS Key Levels", "all_levels_sorted_by_strength": []},
                        "signals": {"error": "Dummy ITS Signals"}, "recommendations": [],
                        "current_mspi_weights_applied": {}, "current_adaptive_historical_context_summary": {}}

logger = logging.getLogger("EnhancedDataProcessor_v321") # Changed version
if not logger.hasHandlers(): 
    logging.basicConfig(stream=sys.stdout, 
                        level=logging.INFO, 
                        format="[%(levelname)s] (%(name)s:%(lineno)d) %(asctime)s - %(message)s",
                        datefmt="%Y-%m-%d %H:%M:%S")

if not IDS_IMPORTED_SUCCESSFULLY_EDP or not CORE_ANALYTICS_MODULES_AVAILABLE_EDP:
    logger.critical("EnhancedDataProcessor_v321: One or more critical imports failed. EDP will use fallbacks.")

DEFAULT_CONFIG_FILE_PATH_EDP: str = "config_v2.json" 
DEFAULT_OUTPUT_DATA_DIR_EDP: str = "eots_data_output/processed_data_edp_v321" # Changed version
JSON_CONVERSION_ERROR_PLACEHOLDER_EDP: str = "ERR_JSON_CONVERSION_FAILED_EDP_v321" # Changed version
DEFAULT_THREAD_POOL_SIZE_EDP: int = min(4, (os.cpu_count() or 1)) 
CONFIG_SCHEMA_VERSION_PROCESSOR_EDP: str = "EDP_v3.2.1_Timestamp_Fix_IDS_Sync" # Changed version


class ConfigurationManager_EDP: 
    def __init__(self, config_path_or_file: str = DEFAULT_CONFIG_FILE_PATH_EDP,
                 config_value_retriever: Optional[Callable[[List[str], Any], Any]] = None):
        self.logger = logger.getChild("ConfigurationManager.EDP_v321") # Changed version
        self.provided_config_path: str = config_path_or_file
        self.config_value_retriever = config_value_retriever
        self.config: Dict[str, Any] = {}
        self.loaded_config_file_actual_path: Optional[str] = None
        self._load_configuration()

    def _resolve_config_file_path(self, config_file_name: str) -> str:
        self.logger.debug(f"Attempting to resolve config file path for: '{config_file_name}'")
        if not config_file_name: 
            script_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(script_dir) 
            resolved = os.path.abspath(os.path.join(project_root, DEFAULT_CONFIG_FILE_PATH_EDP))
            self.logger.debug(f"Empty config_file_name, resolved to default relative to project root: {resolved}")
            return resolved
        
        if os.path.isabs(config_file_name):
            self.logger.debug(f"Config file path is absolute: {config_file_name}")
            return config_file_name
        
        path_from_cwd = os.path.join(os.getcwd(), config_file_name)
        if os.path.exists(path_from_cwd):
            self.logger.debug(f"Config file found relative to CWD: {os.path.abspath(path_from_cwd)}")
            return os.path.abspath(path_from_cwd)
        
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            path_from_script_dir = os.path.join(script_dir, config_file_name)
            if os.path.exists(path_from_script_dir):
                self.logger.debug(f"Config file found relative to script directory: {os.path.abspath(path_from_script_dir)}")
                return os.path.abspath(path_from_script_dir)

            project_root = os.path.dirname(script_dir) 
            path_from_project_root = os.path.join(project_root, config_file_name)
            if os.path.exists(path_from_project_root):
                self.logger.debug(f"Config file found relative to project root: {os.path.abspath(path_from_project_root)}")
                return os.path.abspath(path_from_project_root)
        except NameError: 
            self.logger.warning("__file__ not defined, cannot resolve path relative to script/project directory.")
            
        final_resolved_path = os.path.abspath(config_file_name)
        self.logger.debug(f"Config file path resolution fallback to: {final_resolved_path}")
        return final_resolved_path

    def _load_configuration(self) -> None:
        self.logger.info(f"Initiating configuration loading. Provided path/retriever: '{self.provided_config_path}' / {self.config_value_retriever is not None}")
        loaded_successfully = False
        if self.config_value_retriever and callable(self.config_value_retriever):
            self.logger.debug("Attempting to load configuration via provided retriever function.")
            try:
                retrieved_config = self.config_value_retriever([], {}) 
                if isinstance(retrieved_config, dict) and retrieved_config:
                    self.config = copy.deepcopy(retrieved_config) 
                    self.loaded_config_file_actual_path = self.config.get(ids.CFG_CONFIG_FILE_PATH_CACHED_AT if IDS_IMPORTED_SUCCESSFULLY_EDP else "_config_file_path_cached_at")
                    self.logger.info(f"Configuration successfully loaded via provided retriever. Original source hint: '{self.loaded_config_file_actual_path or 'Not specified by retriever'}'")
                    loaded_successfully = True
                else:
                    self.logger.warning("Config retriever returned empty or non-dict data. Will attempt file load if path provided.")
            except Exception as e_retriever_load:
                self.logger.error(f"Error using config_value_retriever: {e_retriever_load}", exc_info=True)

        if not loaded_successfully and self.provided_config_path:
            resolved_path = self._resolve_config_file_path(self.provided_config_path)
            self.logger.info(f"Attempting to load configuration from file: {resolved_path}")
            if os.path.exists(resolved_path):
                try:
                    with open(resolved_path, 'r', encoding='utf-8') as f_config:
                        self.config = json.load(f_config)
                    self.loaded_config_file_actual_path = resolved_path
                    self.logger.info(f"Configuration successfully loaded from file: {resolved_path}")
                    loaded_successfully = True
                except json.JSONDecodeError as e_json_decode:
                    self.logger.error(f"JSONDecodeError loading config from '{resolved_path}': {e_json_decode}", exc_info=True)
                except Exception as e_file_generic_load:
                    self.logger.error(f"Generic error loading config from '{resolved_path}': {e_file_generic_load}", exc_info=True)
            else:
                self.logger.warning(f"Config file NOT FOUND at resolved path: {resolved_path}. This may lead to using internal defaults.")

        if not loaded_successfully or not self.config: 
            self.logger.warning("No valid configuration loaded from retriever or file. Using minimal internal defaults for EDP.")
            self.config = self._get_internal_default_config()
            self.config["_config_is_internal_default_edp_v321"] = True # Changed version
            self.loaded_config_file_actual_path = "INTERNAL_DEFAULTS_EDP_v321" # Changed version

        self._add_processor_metadata_to_config(loaded_successfully)
        self._validate_loaded_configuration() 

    def _get_internal_default_config(self) -> Dict[str, Any]:
        self.logger.debug("Generating internal default configuration for EDP.")
        strike_col_default_val = ids.COL_STRIKE if IDS_IMPORTED_SUCCESSFULLY_EDP else "strike_price"
        cfg_viz_col_strike_path_list = ids.CFG_VIZ_COL_STRIKE if IDS_IMPORTED_SUCCESSFULLY_EDP else ["visualization_settings", "mspi_visualizer", "column_names", "strike"]
        
        default_config = {
            "system_settings": {
                "log_level": "INFO", 
                "thread_pool_size": DEFAULT_THREAD_POOL_SIZE_EDP,
                "data_directory_base": DEFAULT_OUTPUT_DATA_DIR_EDP,
                "processed_data_subdirectory": "its_outputs_edp_default_v321" # Changed version
            },
            "initial_processor_v2_5_settings": { 
                "perform_strict_column_validation": False,
                "calculate_base_net_greek_flows_from_chain": True,
                "calculate_heuristic_pressures_from_chain": True
            }
        }
        current_level = default_config
        for key_part in cfg_viz_col_strike_path_list[:-1]:
            current_level = current_level.setdefault(key_part, {})
        current_level[cfg_viz_col_strike_path_list[-1]] = strike_col_default_val
        self.logger.debug(f"Internal default config generated with strike column '{strike_col_default_val}' at path {cfg_viz_col_strike_path_list}.")
        return default_config

    def _add_processor_metadata_to_config(self, load_status: bool) -> None:
        self.config["_edp_v321_config_load_timestamp"] = datetime.now().isoformat() # Changed version
        self.config["_edp_v321_config_schema_version"] = CONFIG_SCHEMA_VERSION_PROCESSOR_EDP # Changed version
        self.config["_edp_v321_config_load_successful"] = load_status # Changed version
        self.config["_edp_v321_config_actual_source_path"] = self.loaded_config_file_actual_path # Changed version
        self.logger.debug(f"Processor metadata added to config. Load success: {load_status}, Source: {self.loaded_config_file_actual_path}")

    def _validate_loaded_configuration(self) -> None:
        self.logger.debug("Performing basic validation of loaded configuration.")
        strike_col_path = ids.CFG_VIZ_COL_STRIKE if IDS_IMPORTED_SUCCESSFULLY_EDP else ["visualization_settings", "mspi_visualizer", "column_names", "strike"]
        retrieved_strike_col = self.get_value(strike_col_path, None)
        if not isinstance(retrieved_strike_col, str) or not retrieved_strike_col:
            self.logger.warning(f"Config validation: Strike column name (expected at path: {strike_col_path}) is not a valid string ('{retrieved_strike_col}'). Downstream errors may occur.")
            self.config.setdefault("_edp_v321_config_validation_errors", []).append(f"Invalid strike column name at {strike_col_path}") # Changed version
        else:
            self.logger.debug(f"Config validation: Strike column name '{retrieved_strike_col}' found at path {strike_col_path}.")

    def get_value(self, path_keys: List[str], default_return: Any = None) -> Any:
        current_level = self.config
        try:
            for key_part in path_keys:
                if isinstance(current_level, dict):
                    current_level = current_level[key_part]
                else: 
                    self.logger.debug(f"Config get_value: Path broken at '{key_part}' in {path_keys}. Current level type: {type(current_level)}. Returning default.")
                    return default_return
            return current_level
        except KeyError:
            self.logger.debug(f"Config get_value: Key not found in path {path_keys}. Returning default.")
            return default_return
        except Exception as e_get_val_unexpected:
            self.logger.error(f"Config get_value: Unexpected error for path {path_keys}: {e_get_val_unexpected}. Returning default.", exc_info=True)
            return default_return

    def get_strike_column_name(self) -> str:
        strike_col_config_path = ids.CFG_VIZ_COL_STRIKE if IDS_IMPORTED_SUCCESSFULLY_EDP else ["visualization_settings", "mspi_visualizer", "column_names", "strike"]
        default_strike_col_val = ids.COL_STRIKE if IDS_IMPORTED_SUCCESSFULLY_EDP else "strike_price"
        retrieved_name = str(self.get_value(strike_col_config_path, default_strike_col_val))
        self.logger.debug(f"Retrieved strike column name from config (path: {strike_col_config_path}, default: '{default_strike_col_val}'): '{retrieved_name}'")
        return retrieved_name

    def get_output_directory(self, output_dir_manual_override: Optional[str] = None) -> str:
        if output_dir_manual_override:
            abs_override_path = os.path.abspath(output_dir_manual_override)
            self.logger.info(f"Using manually overridden output directory: {abs_override_path}")
            return abs_override_path
        
        base_dir_path_keys = ["system_settings", "data_directory_base"] 
        sub_dir_path_keys = ["system_settings", "processed_data_subdirectory"] 
        
        base_dir = self.get_value(base_dir_path_keys, DEFAULT_OUTPUT_DATA_DIR_EDP)
        sub_dir = self.get_value(sub_dir_path_keys, "its_outputs_edp_default_v321_subdir") # Changed version
        
        final_base_path: str
        if os.path.isabs(base_dir):
            final_base_path = base_dir
        elif self.loaded_config_file_actual_path and os.path.exists(os.path.dirname(self.loaded_config_file_actual_path)):
            final_base_path = os.path.join(os.path.dirname(self.loaded_config_file_actual_path), base_dir)
        else:
            final_base_path = os.path.join(os.getcwd(), base_dir)
            
        resolved_output_dir = os.path.abspath(os.path.join(final_base_path, sub_dir))
        self.logger.debug(f"Resolved output directory: {resolved_output_dir} (Base: '{base_dir}', Sub: '{sub_dir}')")
        return resolved_output_dir

    def get_thread_pool_size(self) -> int:
        pool_size_path_keys = ["system_settings", "thread_pool_size"] 
        size_val = self.get_value(pool_size_path_keys, DEFAULT_THREAD_POOL_SIZE_EDP)
        try:
            size_int = int(size_val)
            final_size = size_int if size_int > 0 else DEFAULT_THREAD_POOL_SIZE_EDP
            self.logger.debug(f"Thread pool size configured to: {final_size} (Raw config value: '{size_val}')")
            return final_size
        except (ValueError, TypeError):
            self.logger.warning(f"Invalid thread_pool_size '{size_val}' in config. Defaulting to {DEFAULT_THREAD_POOL_SIZE_EDP}.")
            return DEFAULT_THREAD_POOL_SIZE_EDP

class ITSIntegrator_EDP: 
    def __init__(self, config_manager: ConfigurationManager_EDP):
        self.logger = logger.getChild("ITSIntegrator.EDP_v321") # Changed version
        self.config_manager = config_manager
        self.its_instance: Any = None 
        self._load_its_instance()

    def _load_its_instance(self):
        self.logger.info("Attempting to load and instantiate IntegratedTradingSystem.")
        if not CORE_ANALYTICS_MODULES_AVAILABLE_EDP:
            self.logger.critical("ITSIntegrator: Core analytics modules (integrated_strategies_v2) failed to import. Using Dummy ITS.")
            self.its_instance = DummyIntegratedTradingSystem_EDP(config_path=self.config_manager.provided_config_path, edp_logger=self.logger, ids_imported_successfully=IDS_IMPORTED_SUCCESSFULLY_EDP)
            return

        try:
            config_path_for_its = self.config_manager.loaded_config_file_actual_path or self.config_manager.provided_config_path
            if not config_path_for_its: 
                 config_path_for_its = DEFAULT_CONFIG_FILE_PATH_EDP
                 self.logger.warning(f"No explicit config path for ITS, defaulting to EDP's default: {config_path_for_its}")

            self.its_instance = integrated_strategies_v2.IntegratedTradingSystem(config_path=config_path_for_its, ids_imported_successfully=IDS_IMPORTED_SUCCESSFULLY_EDP)
            self.logger.info(f"Successfully instantiated 'IntegratedTradingSystem' using config: '{config_path_for_its}'.")
        except Exception as e_its_load:
            self.logger.critical(f"Failed to instantiate real 'IntegratedTradingSystem': {e_its_load}. Using Dummy ITS.", exc_info=True)
            self.its_instance = DummyIntegratedTradingSystem_EDP(config_path=self.config_manager.provided_config_path, edp_logger=self.logger)

    def get_its_instance(self) -> Any: 
        if self.its_instance is None: 
            self.logger.error("ITSIntegrator.get_its_instance() called but self.its_instance is None. Re-attempting load.")
            self._load_its_instance() 
        return self.its_instance 

    def is_using_dummy_its(self) -> bool:
        return isinstance(self.its_instance, DummyIntegratedTradingSystem_EDP)

class DummyIntegratedTradingSystem_EDP: 
    def __init__(self, config_path: Optional[str] = None, edp_logger: Optional[logging.Logger] = None):
        self.logger = (edp_logger or logger).getChild("DummyITS.EDP_v321_Fallback") # Changed version
        self.config_path_used = config_path
        self.logger.warning(f"Initializing DummyIntegratedTradingSystem_EDP (EDP Fallback). Config path: '{config_path}'")
        self.dummy_config: Dict[str, Any] = {}
        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f_dummy_cfg_load: 
                    self.dummy_config = json.load(f_dummy_cfg_load)
                self.logger.debug(f"DummyITS loaded config from {config_path} for reference.")
            except Exception as e_dummy_cfg:
                 self.logger.error(f"DummyITS could not load config from {config_path}: {e_dummy_cfg}")

    def process_market_data_and_generate_recommendations(self, **kwargs) -> Dict[str, Any]:
        symbol = kwargs.get("symbol", "DUMMY_SYMBOL_ITS_EDP_v321") # Changed version
        self.logger.warning(f"DummyITS_EDP_v321: Executing DUMMY 'process_market_data_and_generate_recommendations' for symbol '{symbol}'.")
        
        df_input = kwargs.get("raw_options_data", pd.DataFrame())
        if not isinstance(df_input, pd.DataFrame): 
            self.logger.warning(f"DummyITS received non-DataFrame input for raw_options_data (type: {type(df_input)}). Using empty DataFrame.")
            df_input = pd.DataFrame()

        df_output = df_input.copy() 
        mspi_col_name = ids.COL_MSPI_SCORE if IDS_IMPORTED_SUCCESSFULLY_EDP else "mspi"
        its_output_metric_cols = [
            ids.COL_SAI, ids.COL_SSI, ids.COL_ARFI, ids.COL_DAG_CUSTOM_RAW, ids.COL_TDPI_RAW, ids.COL_VRI_RAW,
            ids.COL_SDAG_MULTIPLICATIVE_RAW, ids.COL_SDAG_DIRECTIONAL_RAW, ids.COL_SDAG_WEIGHTED_RAW,
            ids.COL_SDAG_VOLATILITY_FOCUSED_RAW, ids.COL_DAG_CUSTOM_NORM, ids.COL_TDPI_NORM, ids.COL_VRI_NORM,
            ids.COL_SDAG_MULTIPLICATIVE_NORM, ids.COL_SDAG_DIRECTIONAL_NORM, ids.COL_SDAG_WEIGHTED_NORM,
            ids.COL_SDAG_VOLATILITY_FOCUSED_NORM
        ] if IDS_IMPORTED_SUCCESSFULLY_EDP else [ 
            "sai", "ssi", "arfi", "dag_custom", "tdpi", "vri", "sdag_multiplicative", "sdag_directional", 
            "sdag_weighted", "sdag_volatility_focused", "dag_custom_norm", "tdpi_norm", "vri_norm", 
            "sdag_multiplicative_norm", "sdag_directional_norm", "sdag_weighted_norm", "sdag_volatility_focused_norm"
        ]

        if mspi_col_name not in df_output.columns: df_output[mspi_col_name] = 0.0
        for col_name_its in its_output_metric_cols:
            if col_name_its not in df_output.columns: df_output[col_name_its] = 0.0
        
        self.logger.debug(f"DummyITS for {symbol}: Input DF shape {df_input.shape}, Output DF shape {df_output.shape}. Ensuring ITS columns exist.")

        return {
            "symbol": symbol,
            "error": "Using DUMMY IntegratedTradingSystem (Real ITS failed to load or instantiate in EDP v3.2.1). Placeholder data generated.", # Changed version
            "traceback": None, 
            "final_metric_rich_df_obj": df_output, 
            "processed_options_df": df_output.to_dict(orient='records'), 
            "aggregated_strike_data": [], 
            "key_levels": {"error": "Dummy ITS Key Levels (EDP v3.2.1)", "all_levels_sorted_by_strength": []}, # Changed version
            "signals": {"error": "Dummy ITS Signals (EDP v3.2.1)"},  # Changed version
            "recommendations": [], 
            "current_mspi_weights_applied": {"error": "Dummy ITS Weights (EDP v3.2.1)"},  # Changed version
            "current_adaptive_historical_context_summary": {"error": "Dummy ITS Hist Context (EDP v3.2.1)"} # Changed version
        }

class DataProcessor_EDP: 
    def __init__(self, config_manager: ConfigurationManager_EDP, its_integrator: ITSIntegrator_EDP):
        self.logger = logger.getChild("DataProcessor.EDP_v321") # Changed version
        self.config_manager = config_manager
        self.its_integrator = its_integrator
        self.output_directory_main: Optional[str] = None 
        self.logger.info("DataProcessor_EDP (v3.2.1) initialized.") # Changed version

    def _ensure_output_directory_exists(self) -> bool:
        if self.output_directory_main is None:
            self.output_directory_main = self.config_manager.get_output_directory()
        
        if not self.output_directory_main: 
            self.logger.critical("Output directory path is None or empty. Cannot ensure or use for saving.")
            return False
        try:
            os.makedirs(self.output_directory_main, exist_ok=True)
            self.logger.info(f"Output directory '{self.output_directory_main}' ensured/exists.")
            return True
        except OSError as e_dir_create_os_err:
            self.logger.critical(f"CRITICAL: Cannot create or access output directory '{self.output_directory_main}': {e_dir_create_os_err}", exc_info=True)
            return False
        except Exception as e_dir_create_generic:
            self.logger.critical(f"CRITICAL: Unexpected error ensuring output directory '{self.output_directory_main}': {e_dir_create_generic}", exc_info=True)
            return False

    def _validate_input_options_data(self, options_df: pd.DataFrame, symbol: str) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
        val_logger = self.logger.getChild(f"ValidateInputOptionsData.{symbol}.EDP_v321") # Changed version
        val_logger.info(f"Validating input options data for symbol '{symbol}'. Initial shape: {options_df.shape if isinstance(options_df, pd.DataFrame) else 'Not a DataFrame'}")

        if not isinstance(options_df, pd.DataFrame) or options_df.empty:
            err_msg = f"Input options_df for symbol '{symbol}' is empty or not a DataFrame (type: {type(options_df)})."
            val_logger.error(err_msg)
            return None, err_msg
        
        df = options_df.copy() 
        expected_strike_col_name = ids.COL_STRIKE if IDS_IMPORTED_SUCCESSFULLY_EDP else "strike_price"
        if expected_strike_col_name not in df.columns:
            if "strike" in df.columns:
                val_logger.info(f"Found 'strike' column for '{symbol}', renaming to standard '{expected_strike_col_name}'.")
                df.rename(columns={"strike": expected_strike_col_name}, inplace=True)
            else:
                err_msg = f"Required strike column '{expected_strike_col_name}' (or 'strike') not found for '{symbol}'. Columns: {df.columns.tolist()}"
                val_logger.error(err_msg)
                return None, err_msg
        
        try:
            df[expected_strike_col_name] = pd.to_numeric(df[expected_strike_col_name], errors='coerce')
            initial_rows = len(df)
            df.dropna(subset=[expected_strike_col_name], inplace=True) 
            rows_after_dropna = len(df)
            if initial_rows > rows_after_dropna:
                val_logger.warning(f"Dropped {initial_rows - rows_after_dropna} rows for '{symbol}' due to non-numeric strike prices.")
            if df.empty:
                err_msg = f"No valid numeric strike prices found for symbol '{symbol}' after NaN drop. DataFrame became empty."
                val_logger.error(err_msg)
                return None, err_msg
        except Exception as e_strike_conversion_err:
            err_msg = f"Error converting strike column '{expected_strike_col_name}' to numeric for '{symbol}': {e_strike_conversion_err}"
            val_logger.error(err_msg, exc_info=True)
            return None, err_msg
            
        val_logger.info(f"Input data validation successful for '{symbol}'. Shape after validation: {df.shape}")
        return df, None

    def _prepare_dataframe_for_its_and_metrics(self, validated_df: pd.DataFrame,
                                               underlying_info: Dict[str, Any], symbol: str) -> pd.DataFrame:
        prep_logger = self.logger.getChild(f"PrepareDataFrame.{symbol}.EDP_v321") # Changed version
        prep_logger.info(f"Preparing DataFrame for ITS and metrics for '{symbol}'. Input shape: {validated_df.shape}")
        df = validated_df.copy()

        underlying_sym_col = ids.COL_UNDERLYING_SYMBOL_CHAIN if IDS_IMPORTED_SUCCESSFULLY_EDP else "underlying_symbol"
        df[underlying_sym_col] = symbol
        prep_logger.debug(f"Added '{underlying_sym_col}' column with value '{symbol}'.")

        current_price_param_key = ids.CV_UND_PARAM_PRICE if IDS_IMPORTED_SUCCESSFULLY_EDP else "price"
        current_price_val = underlying_info.get(current_price_param_key)
        
        current_price_col_edp = ids.COL_CURRENT_PRICE_EDP if IDS_IMPORTED_SUCCESSFULLY_EDP else "current_price"
        dist_from_current_col_edp = ids.COL_DISTANCE_FROM_CURRENT_EDP if IDS_IMPORTED_SUCCESSFULLY_EDP else "distance_from_current"
        pct_dist_col_edp = ids.COL_PCT_DISTANCE_FROM_CURRENT_EDP if IDS_IMPORTED_SUCCESSFULLY_EDP else "pct_distance_from_current"
        strike_col_for_dist = ids.COL_STRIKE if IDS_IMPORTED_SUCCESSFULLY_EDP else "strike_price"

        if pd.notna(current_price_val):
            try:
                current_price_float = float(current_price_val)
                df[current_price_col_edp] = current_price_float
                prep_logger.debug(f"Added '{current_price_col_edp}' with value {current_price_float}.")
                if strike_col_for_dist in df.columns:
                    df[dist_from_current_col_edp] = df[strike_col_for_dist] - current_price_float
                    df[pct_dist_col_edp] = (df[dist_from_current_col_edp] / (current_price_float if current_price_float != 0 else np.nan)) * 100
                    prep_logger.debug(f"Calculated distance metrics: '{dist_from_current_col_edp}', '{pct_dist_col_edp}'.")
                else:
                    prep_logger.warning(f"Strike column '{strike_col_for_dist}' missing. Cannot calculate distance metrics for '{symbol}'.")
                    df[dist_from_current_col_edp] = np.nan
                    df[pct_dist_col_edp] = np.nan
            except ValueError:
                prep_logger.error(f"Could not convert underlying price '{current_price_val}' to float for '{symbol}'. Distance metrics will be NaN.")
                df[current_price_col_edp] = np.nan; df[dist_from_current_col_edp] = np.nan; df[pct_dist_col_edp] = np.nan
        else:
            prep_logger.warning(f"Underlying price not available or NaN for '{symbol}'. Distance metrics will be NaN.")
            df[current_price_col_edp] = np.nan; df[dist_from_current_col_edp] = np.nan; df[pct_dist_col_edp] = np.nan

        fetch_ts_param_key = ids.CV_UND_PARAM_FETCH_TIMESTAMP if IDS_IMPORTED_SUCCESSFULLY_EDP else "fetch_timestamp"
        fetch_ts_val = underlying_info.get(fetch_ts_param_key)
        fetch_ts_col_edp = ids.COL_FETCH_TIMESTAMP_EDP if IDS_IMPORTED_SUCCESSFULLY_EDP else "fetch_timestamp" 
        
        if fetch_ts_val:
            if fetch_ts_col_edp not in df.columns: 
                 df[fetch_ts_col_edp] = fetch_ts_val
                 prep_logger.debug(f"Added '{fetch_ts_col_edp}' from underlying info: {fetch_ts_val}.")
            else:
                 prep_logger.debug(f"Column '{fetch_ts_col_edp}' already exists in DataFrame, not overwriting from underlying info.")
        else:
            prep_logger.warning(f"Fetch timestamp not found in underlying info for '{symbol}'.")

        # Corrected constant name here
        edp_prep_ts_col = ids.COL_EDP_PREPARATION_TIMESTAMP_EDP if IDS_IMPORTED_SUCCESSFULLY_EDP else "edp_dataframe_preparation_timestamp"
        df[edp_prep_ts_col] = datetime.now().isoformat()
        prep_logger.debug(f"Added '{edp_prep_ts_col}'.")
        
        prep_logger.info(f"DataFrame preparation for ITS and metrics complete for '{symbol}'. Final shape: {df.shape}. Columns: {df.columns.tolist()}")
        return df

    def _rename_impact_columns_for_charts(self, df_metrics: pd.DataFrame, symbol: str) -> pd.DataFrame:
        rename_logger = self.logger.getChild(f"RenameImpactCols.{symbol}.EDP_v321") # Changed version
        df_renamed = df_metrics.copy()
        
        if not IDS_IMPORTED_SUCCESSFULLY_EDP:
            rename_logger.error("Cannot rename impact columns: ids.py module not loaded. Chart data may be incorrect.")
            return df_renamed

        impact_to_chart_map = {
            ids.COL_IMPACT_DELTA_RAW: ids.COL_CHART_HEURISTIC_NET_DELTA_PRESSURE,
            ids.COL_IMPACT_GAMMA_RAW: ids.COL_CHART_NET_GAMMA_FLOW,
            ids.COL_IMPACT_VEGA_RAW: ids.COL_CHART_NET_VEGA_FLOW,
            ids.COL_IMPACT_THETA_RAW: ids.COL_CHART_NET_THETA_EXPOSURE,
            ids.COL_IMPACT_VOLUME_RAW: ids.COL_CHART_NET_VOLUME_PRESSURE,
            ids.COL_IMPACT_VALUE_RAW: ids.COL_CHART_NET_VALUE_PRESSURE
        }
        columns_renamed_count = 0
        rename_logger.debug(f"Attempting to rename columns for charts. Map: {impact_to_chart_map}")
        for raw_col_name, chart_col_name in impact_to_chart_map.items():
            if raw_col_name in df_renamed.columns:
                if chart_col_name not in df_renamed.columns or raw_col_name == chart_col_name: 
                    df_renamed.rename(columns={raw_col_name: chart_col_name}, inplace=True)
                    columns_renamed_count +=1
                    rename_logger.debug(f"Renamed '{raw_col_name}' to '{chart_col_name}'.")
                elif raw_col_name != chart_col_name : 
                     rename_logger.warning(f"Target chart column '{chart_col_name}' already exists. Skipping rename of '{raw_col_name}'. Ensure consistency.")
            else:
                rename_logger.debug(f"Source impact column '{raw_col_name}' not found in DataFrame. Cannot rename.")
        
        if columns_renamed_count > 0:
            rename_logger.info(f"Renaming impact columns for chart compatibility complete for {columns_renamed_count} columns for '{symbol}'.")
        else:
            rename_logger.info(f"No impact columns were renamed for charts for '{symbol}'.")
        return df_renamed

    def _apply_its_strategies(self, df_with_all_metrics: pd.DataFrame,
                              underlying_info: Dict[str, Any],
                              market_ctx: Dict[str, Any], 
                              hist_ohlc: Optional[pd.DataFrame],
                              symbol: str,
                              exp_cal: Optional[List[date]]) -> Tuple[Dict[str, Any], Optional[str]]: 
        its_logger = self.logger.getChild(f"ApplyITSStrategies.{symbol}.EDP_v321") # Changed version
        its_instance = self.its_integrator.get_its_instance() 
        its_logger.info(f"Applying ITS strategies using instance of type: '{type(its_instance).__name__}' for symbol '{symbol}'. Input DF shape: {df_with_all_metrics.shape}")
        its_logger.debug(f"ITS Input - Underlying Info Keys: {list(underlying_info.keys())}")
        its_logger.debug(f"ITS Input - Market Context Keys: {list(market_ctx.keys())}")
        its_logger.debug(f"ITS Input - Historical OHLC DF is None: {hist_ohlc is None}, Shape if not None: {hist_ohlc.shape if hist_ohlc is not None else 'N/A'}")
        its_logger.debug(f"ITS Input - Expiration Calendar is None: {exp_cal is None}, Len if not None: {len(exp_cal) if exp_cal is not None else 'N/A'}")

        try:
            its_output_bundle = its_instance.process_market_data_and_generate_recommendations(
                symbol=symbol, 
                raw_options_data=df_with_all_metrics, 
                underlying_data=underlying_info,
                market_context=market_ctx, 
                historical_ohlc_data=hist_ohlc, 
                expiration_calendar=exp_cal
            )
            
            if not isinstance(its_output_bundle, dict):
                err_msg = f"ITS for '{symbol}' returned an invalid type: {type(its_output_bundle)}. Expected a dictionary."
                its_logger.error(err_msg)
                return {"error": err_msg, "final_metric_rich_df_obj": df_with_all_metrics.copy(), "traceback": None}, err_msg

            reported_error_from_its = its_output_bundle.get("error")
            if reported_error_from_its:
                if "DUMMY" not in str(reported_error_from_its).upper() and "FALLBACK" not in str(reported_error_from_its).upper() :
                    its_logger.error(f"Error reported by IntegratedTradingSystem for '{symbol}': {reported_error_from_its}")
                else: 
                    its_logger.warning(f"ITS (Dummy/Fallback) for '{symbol}' reported: {reported_error_from_its}")
            
            if "final_metric_rich_df_obj" not in its_output_bundle or not isinstance(its_output_bundle["final_metric_rich_df_obj"], pd.DataFrame):
                its_logger.warning(f"'final_metric_rich_df_obj' missing or not a DataFrame in ITS bundle for '{symbol}'. Using input metrics DataFrame as fallback.")
                its_output_bundle["final_metric_rich_df_obj"] = df_with_all_metrics.copy() 
            
            if "processed_options_df" not in its_output_bundle:
                its_logger.debug(f"'processed_options_df' (list of dicts) missing from ITS bundle for '{symbol}'. Creating from 'final_metric_rich_df_obj'.")
                its_output_bundle["processed_options_df"] = its_output_bundle["final_metric_rich_df_obj"].to_dict(orient='records')

            its_logger.info(f"ITS strategies applied for '{symbol}'. Final DataFrame shape from ITS: {its_output_bundle['final_metric_rich_df_obj'].shape}. Error status from ITS: '{reported_error_from_its or 'None'}'")
            return its_output_bundle, reported_error_from_its 

        except Exception as e_its_application_call:
            critical_error_msg = f"CRITICAL Exception during ITS strategy application for '{symbol}': {type(e_its_application_call).__name__} - {e_its_application_call}"
            its_logger.critical(critical_error_msg, exc_info=True) 
            return {
                "error": critical_error_msg, 
                "traceback": traceback.format_exc(), 
                "final_metric_rich_df_obj": df_with_all_metrics.copy() 
            }, critical_error_msg

    def _package_analysis_results(self, symbol: str,
                                  cv_fetch_timestamp: Optional[str], 
                                  its_output_bundle: Dict[str, Any], 
                                  cv_underlying_data_bundle: Dict[str, Any], 
                                  tradier_context_bundle: Dict[str, Any], 
                                  overall_processing_error: Optional[str] 
                                 ) -> Dict[str, Any]:
        pkg_logger = self.logger.getChild(f"PackageAnalysisResults.{symbol}.EDP_v321") # Changed version
        pkg_logger.info(f"Packaging analysis results for symbol '{symbol}'.")

        final_df_from_its_obj = its_output_bundle.get("final_metric_rich_df_obj")
        if not isinstance(final_df_from_its_obj, pd.DataFrame):
            pkg_logger.warning(f"'final_metric_rich_df_obj' from ITS for '{symbol}' was not a DataFrame (type: {type(final_df_from_its_obj)}). Using empty DataFrame.")
            final_df_from_its_obj = pd.DataFrame()
        
        df_renamed_for_charts = self._rename_impact_columns_for_charts(final_df_from_its_obj.copy(), symbol)
        pkg_logger.debug(f"DataFrame shape after renaming for charts: {df_renamed_for_charts.shape}")

        final_error_msg = overall_processing_error or its_output_bundle.get("error")
        final_traceback = its_output_bundle.get("traceback") 

        option_symbol_key_final = ids.COL_OPTION_SYMBOL if IDS_IMPORTED_SUCCESSFULLY_EDP else "symbol" 
        fetch_ts_key_final = ids.COL_FETCH_TIMESTAMP_EDP if IDS_IMPORTED_SUCCESSFULLY_EDP else "fetch_timestamp" 

        final_bundle_to_return = {
            option_symbol_key_final: symbol, 
            fetch_ts_key_final: cv_fetch_timestamp or datetime.now().isoformat(), 
            "edp_processing_timestamp": datetime.now().isoformat(),
            "edp_processor_version": CONFIG_SCHEMA_VERSION_PROCESSOR_EDP,
            "error": final_error_msg, 
            "traceback": final_traceback, 
            "using_dummy_its": self.its_integrator.is_using_dummy_its(),
            "processed_data": { 
                "options_chain": its_output_bundle.get("processed_options_df", df_renamed_for_charts.to_dict(orient='records')),
                "aggregated_strike_data": its_output_bundle.get("aggregated_strike_data", []), 
                "key_levels": its_output_bundle.get("key_levels", {"error": "Key levels not generated by ITS", "all_levels_sorted_by_strength": []}),
                "signals": its_output_bundle.get("signals", {"error": "Signals not generated by ITS"}), 
                "recommendations": its_output_bundle.get("recommendations", []) 
            },
            "underlying_data_source": cv_underlying_data_bundle, 
            "market_context_source": tradier_context_bundle, 
            "final_metric_rich_df_obj": df_renamed_for_charts 
        }
        pkg_logger.debug(f"Final bundle structure for '{symbol}': Keys: {list(final_bundle_to_return.keys())}")

        is_error_significant_for_save = final_bundle_to_return["error"] and \
                                       "DUMMY" not in str(final_bundle_to_return["error"]).upper() and \
                                       "FALLBACK" not in str(final_bundle_to_return["error"]).upper()
        
        if not is_error_significant_for_save:
            json_safe_content_for_file = {k: v for k, v in final_bundle_to_return.items() if k != "final_metric_rich_df_obj"}
            if "processed_data" in json_safe_content_for_file and \
               isinstance(json_safe_content_for_file["processed_data"].get("aggregated_strike_data"), pd.DataFrame) :
                json_safe_content_for_file["processed_data"]["aggregated_strike_data"] = \
                    json_safe_content_for_file["processed_data"]["aggregated_strike_data"].to_dict(orient='records')
            
            self._save_analysis_results_to_file(symbol, json_safe_content_for_file)
        else:
            pkg_logger.warning(f"Skipping file save for '{symbol}' due to significant error: {final_bundle_to_return['error']}")
        
        pkg_logger.info(f"Result packaging complete for '{symbol}'. Final error status: '{final_bundle_to_return['error'] or 'None'}'")
        return final_bundle_to_return

    def _save_analysis_results_to_file(self, symbol: str, data_to_save: Dict[str, Any]) -> None:
        save_logger = self.logger.getChild(f"SaveResultsToFile.{symbol}.EDP_v321") # Changed version
        if not self._ensure_output_directory_exists(): 
            save_logger.error(f"Cannot save analysis results for '{symbol}': Output directory problem.")
            return
        
        try:
            ts_str_file = datetime.now().strftime("%Y%m%d_%H%M%S_%f") 
            filename = f"edp_output_{symbol.upper()}_{ts_str_file}.json"
            filepath = os.path.join(self.output_directory_main, filename) # type: ignore 
            
            save_logger.info(f"Attempting to save analysis results for '{symbol}' to: {filepath}")
            with open(filepath, 'w', encoding='utf-8') as f_json_out:
                json.dump(data_to_save, f_json_out, indent=4, default=str) 
            save_logger.info(f"Successfully saved analysis results for '{symbol}' to: {filepath}")
        except Exception as e_save_file:
            save_logger.error(f"Error saving analysis results to file for '{symbol}' at '{filepath if 'filepath' in locals() else 'Unknown Path'}': {e_save_file}", exc_info=True)

    def _process_single_symbol_data(self, symbol: str,
                                    cv_data_for_symbol: Dict[str, Any], 
                                    tradier_context_for_symbol: Dict[str, Any], 
                                    expiration_calendar_for_symbol: Optional[List[date]] 
                                   ) -> Dict[str, Any]: 
        single_pipeline_logger = self.logger.getChild(f"SingleSymbolPipeline.{symbol}.EDP_v321") # Changed version
        single_pipeline_logger.info(f"STARTING full data processing pipeline for symbol: '{symbol}'")
        
        processing_error_msg: Optional[str] = None 
        full_traceback_for_error_bundle: Optional[str] = None

        try:
            single_pipeline_logger.debug(f"CV data keys for '{symbol}': {list(cv_data_for_symbol.keys())}")
            options_chain_raw_data = cv_data_for_symbol.get("options_chain") 
            cv_underlying_info_bundle = cv_data_for_symbol.get("underlying", {}) 
            cv_fetch_error = cv_data_for_symbol.get("error")
            
            cv_fetch_ts_key = ids.CV_UND_PARAM_FETCH_TIMESTAMP if IDS_IMPORTED_SUCCESSFULLY_EDP else "fetch_timestamp"
            cv_fetch_timestamp_val = cv_underlying_info_bundle.get(cv_fetch_ts_key, datetime.now().isoformat()) 

            if cv_fetch_error:
                processing_error_msg = f"ConvexValue fetcher reported an error for '{symbol}': {cv_fetch_error}"
                single_pipeline_logger.error(processing_error_msg)
                return self._create_error_bundle_for_symbol(symbol, processing_error_msg) 

            options_df_for_validation: pd.DataFrame
            if isinstance(options_chain_raw_data, list):
                options_df_for_validation = pd.DataFrame(options_chain_raw_data)
                single_pipeline_logger.debug(f"Converted options_chain from list to DataFrame for '{symbol}'. Shape: {options_df_for_validation.shape}")
            elif isinstance(options_chain_raw_data, pd.DataFrame):
                options_df_for_validation = options_chain_raw_data 
                single_pipeline_logger.debug(f"options_chain is already a DataFrame for '{symbol}'. Shape: {options_df_for_validation.shape}")
            else:
                processing_error_msg = f"Invalid options_chain_raw_data type for '{symbol}': {type(options_chain_raw_data)}. Expected List[Dict] or pd.DataFrame."
                single_pipeline_logger.error(processing_error_msg)
                return self._create_error_bundle_for_symbol(symbol, processing_error_msg)

            validated_options_df, validation_err_msg = self._validate_input_options_data(options_df_for_validation, symbol)
            if validation_err_msg or validated_options_df is None: 
                processing_error_msg = validation_err_msg or f"Data validation returned None DataFrame for '{symbol}'."
                single_pipeline_logger.error(f"Input data validation FAILED for '{symbol}': {processing_error_msg}")
                return self._create_error_bundle_for_symbol(symbol, processing_error_msg)
            single_pipeline_logger.info(f"Input data successfully validated for '{symbol}'. Shape: {validated_options_df.shape}")

            df_prepared_for_metrics = self._prepare_dataframe_for_its_and_metrics(validated_options_df, cv_underlying_info_bundle, symbol)
            single_pipeline_logger.info(f"DataFrame prepared for metrics calculation for '{symbol}'. Shape: {df_prepared_for_metrics.shape}")

            current_price_param_key_impact = ids.CV_UND_PARAM_PRICE if IDS_IMPORTED_SUCCESSFULLY_EDP else "price"
            current_price_for_impacts_val = cv_underlying_info_bundle.get(current_price_param_key_impact)
            df_with_impacts = df_prepared_for_metrics.copy() 

            if pd.notna(current_price_for_impacts_val) and CORE_ANALYTICS_MODULES_AVAILABLE_EDP and hasattr(impact_calculations, 'calculate_delta_impact'):
                current_price_float_for_impacts = float(current_price_for_impacts_val)
                single_pipeline_logger.info(f"Applying raw impact calculations from 'impact_calculations' module for '{symbol}' with current price: {current_price_float_for_impacts:.2f}")
                
                df_with_impacts = impact_calculations.calculate_delta_impact(df_with_impacts, current_price_float_for_impacts, log_instance=single_pipeline_logger)
                df_with_impacts = impact_calculations.calculate_gamma_impact(df_with_impacts, current_price_float_for_impacts, log_instance=single_pipeline_logger)
                df_with_impacts = impact_calculations.calculate_vega_impact(df_with_impacts, current_price_float_for_impacts, log_instance=single_pipeline_logger)
                df_with_impacts = impact_calculations.calculate_theta_impact(df_with_impacts, current_price_float_for_impacts, log_instance=single_pipeline_logger)
                df_with_impacts = impact_calculations.calculate_volume_impact(df_with_impacts, current_price_float_for_impacts, log_instance=single_pipeline_logger)
                df_with_impacts = impact_calculations.calculate_value_impact(df_with_impacts, current_price_float_for_impacts, log_instance=single_pipeline_logger)
                single_pipeline_logger.info(f"Raw impact calculations applied for '{symbol}'. DF shape: {df_with_impacts.shape}")
            elif not CORE_ANALYTICS_MODULES_AVAILABLE_EDP:
                processing_error_msg = f"Skipping impact calculations for '{symbol}': core_analytics.impact_calculations module not loaded."
                single_pipeline_logger.error(processing_error_msg) 
            elif not pd.notna(current_price_for_impacts_val):
                processing_error_msg = f"Skipping impact calculations for '{symbol}': current underlying price is invalid or NaN ({current_price_for_impacts_val})."
                single_pipeline_logger.error(processing_error_msg)
            
            single_pipeline_logger.debug(f"Tradier context keys for '{symbol}': {list(tradier_context_for_symbol.keys())}")
            tradier_iv_quote_bundle = tradier_context_for_symbol.get("iv_and_quote_data", {})
            tradier_ohlcv_df = tradier_context_for_symbol.get("historical_ohlcv_df") 
            tradier_fetch_error = tradier_context_for_symbol.get("error")
            if tradier_fetch_error and not processing_error_msg: 
                single_pipeline_logger.warning(f"Tradier fetcher reported an error for '{symbol}': {tradier_fetch_error}. Market context for ITS may be incomplete.")

            market_context_for_its = {
                "current_time": dt_time.fromisoformat(tradier_iv_quote_bundle.get("time", datetime.now().time().isoformat())), 
                "iv_and_quote_data": tradier_iv_quote_bundle 
            }
            single_pipeline_logger.debug(f"Market context prepared for ITS for '{symbol}'.")

            its_bundle_result, its_processing_error_msg = self._apply_its_strategies(
                df_with_impacts, 
                cv_underlying_info_bundle, 
                market_context_for_its,
                tradier_ohlcv_df, 
                symbol, 
                expiration_calendar_for_symbol
            )
            if its_processing_error_msg and not processing_error_msg: 
                processing_error_msg = its_processing_error_msg
                if "CRITICAL" in its_processing_error_msg.upper(): 
                    full_traceback_for_error_bundle = its_bundle_result.get("traceback")

            final_symbol_bundle = self._package_analysis_results(
                symbol, cv_fetch_timestamp_val, its_bundle_result,
                cv_underlying_info_bundle, tradier_context_for_symbol, 
                processing_error_msg 
            )
            single_pipeline_logger.info(f"COMPLETED full data processing pipeline for symbol: '{symbol}'.")
            return final_symbol_bundle

        except Exception as e_single_sym_pipeline:
            critical_pipeline_error_msg = f"UNHANDLED CRITICAL Exception in _process_single_symbol_data for '{symbol}': {type(e_single_sym_pipeline).__name__} - {e_single_sym_pipeline}"
            single_pipeline_logger.critical(critical_pipeline_error_msg, exc_info=True)
            full_traceback_for_error_bundle = traceback.format_exc()
            return self._create_error_bundle_for_symbol(symbol, critical_pipeline_error_msg, full_traceback_for_error_bundle)

    def _create_error_bundle_for_symbol(self, symbol: str, error_message: str,
                                        traceback_info: Optional[str] = None) -> Dict[str, Any]:
        error_logger = self.logger.getChild(f"CreateErrorBundle.{symbol}.EDP_v321") # Changed version
        error_logger.error(f"Creating error bundle for symbol '{symbol}': {error_message}")
        if traceback_info:
             error_logger.debug(f"Associated Traceback for '{symbol}':\n{traceback_info}")

        option_symbol_key_err = ids.COL_OPTION_SYMBOL if IDS_IMPORTED_SUCCESSFULLY_EDP else "symbol"
        fetch_ts_key_err = ids.COL_FETCH_TIMESTAMP_EDP if IDS_IMPORTED_SUCCESSFULLY_EDP else "fetch_timestamp"
        
        return {
            option_symbol_key_err: symbol,
            fetch_ts_key_err: datetime.now().isoformat(), 
            "edp_processing_timestamp": datetime.now().isoformat(),
            "edp_processor_version": CONFIG_SCHEMA_VERSION_PROCESSOR_EDP,
            "error": error_message, 
            "traceback": traceback_info, 
            "using_dummy_its": self.its_integrator.is_using_dummy_its(), 
            "processed_data": { 
                "options_chain": [], "aggregated_strike_data": [],
                "key_levels": {"error": "Processing error prevented key level generation", "all_levels_sorted_by_strength": []},
                "signals": {"error": "Processing error prevented signal generation"}, 
                "recommendations": []
            },
            "underlying_data_source": {"error": "Data unavailable due to processing error for this symbol"},
            "market_context_source": {"error": "Data unavailable due to processing error for this symbol"},
            "final_metric_rich_df_obj": pd.DataFrame() 
        }

    def process_market_data_bundle(self,
                                   market_data_payload: Dict[str, Dict[str, Any]], 
                                   tradier_context_payload: Optional[Dict[str, Dict[str, Any]]] = None, 
                                   expiration_calendars_payload: Optional[Dict[str, List[date]]] = None 
                                  ) -> Dict[str, Dict[str, Any]]: 
        bundle_proc_logger = self.logger.getChild("ProcessMarketDataBundle.EDP_v321") # Changed version
        num_symbols = len(market_data_payload)
        start_time_bundle_proc = pytime.monotonic()
        bundle_proc_logger.info(f"Starting to process market data bundle for {num_symbols} symbol(s). EDP Version: {CONFIG_SCHEMA_VERSION_PROCESSOR_EDP}")

        results_map: Dict[str, Dict[str, Any]] = {}
        thread_pool_size = self.config_manager.get_thread_pool_size()
        
        effective_tradier_context = tradier_context_payload if tradier_context_payload is not None else {}
        effective_expiration_calendars = expiration_calendars_payload if expiration_calendars_payload is not None else {}

        if num_symbols > 1 and thread_pool_size > 1:
            bundle_proc_logger.info(f"Using ThreadPoolExecutor with up to {thread_pool_size} worker threads for {num_symbols} symbols.")
            with ThreadPoolExecutor(max_workers=thread_pool_size) as executor:
                future_to_symbol_map = {
                    executor.submit(self._process_single_symbol_data, 
                                    sym_key, 
                                    cv_data, 
                                    effective_tradier_context.get(sym_key, {}), 
                                    effective_expiration_calendars.get(sym_key) 
                                   ): sym_key
                    for sym_key, cv_data in market_data_payload.items()
                }
                
                for future_item in as_completed(future_to_symbol_map):
                    sym_completed = future_to_symbol_map[future_item]
                    try:
                        results_map[sym_completed] = future_item.result()
                        bundle_proc_logger.info(f"Successfully completed processing for symbol '{sym_completed}' in thread.")
                    except Exception as e_thread_execution:
                        err_msg = f"Unhandled exception in worker thread for symbol '{sym_completed}': {type(e_thread_execution).__name__} - {e_thread_execution}"
                        bundle_proc_logger.critical(err_msg, exc_info=True)
                        results_map[sym_completed] = self._create_error_bundle_for_symbol(sym_completed, err_msg, traceback.format_exc())
        else:
            bundle_proc_logger.info(f"Processing {num_symbols} symbol(s) sequentially.")
            for sym_key, cv_data in market_data_payload.items():
                bundle_proc_logger.debug(f"Starting sequential processing for symbol: '{sym_key}'")
                try:
                    results_map[sym_key] = self._process_single_symbol_data(
                        sym_key, 
                        cv_data, 
                        effective_tradier_context.get(sym_key, {}),
                        effective_expiration_calendars.get(sym_key)
                    )
                    bundle_proc_logger.info(f"Successfully completed sequential processing for symbol '{sym_key}'.")
                except Exception as e_sequential_execution:
                    err_msg = f"Unhandled exception during sequential processing for '{sym_key}': {type(e_sequential_execution).__name__} - {e_sequential_execution}"
                    bundle_proc_logger.critical(err_msg, exc_info=True)
                    results_map[sym_key] = self._create_error_bundle_for_symbol(sym_key, err_msg, traceback.format_exc())
        
        end_time_bundle_proc = pytime.monotonic()
        total_duration_bundle_proc = end_time_bundle_proc - start_time_bundle_proc
        bundle_proc_logger.info(f"Completed processing market data bundle for all {num_symbols} symbols. Total duration: {total_duration_bundle_proc:.3f} seconds.")
        return results_map

class EnhancedDataProcessor: 
    def __init__(self, config_path: Optional[str] = None,
                 output_data_directory: Optional[str] = None, 
                 config_retriever_func: Optional[Callable[[List[str], Any], Any]] = None): 
        self.main_logger = logger.getChild("EnhancedDataProcessor_MainInstance_v321") # Changed version
        self.main_logger.info(f"Initializing EnhancedDataProcessor System (Version: {CONFIG_SCHEMA_VERSION_PROCESSOR_EDP})...")
        
        effective_config_path_for_cfg_mgr = config_path
        if config_retriever_func is not None and config_path is not None:
            self.main_logger.info("Both 'config_path' and 'config_retriever_func' provided. Retriever will be prioritized.")
        elif config_retriever_func is None and config_path is None:
            self.main_logger.info(f"Neither 'config_path' nor 'config_retriever_func' provided. Using EDP default: '{DEFAULT_CONFIG_FILE_PATH_EDP}'.")
            effective_config_path_for_cfg_mgr = DEFAULT_CONFIG_FILE_PATH_EDP

        self.config_manager_instance = ConfigurationManager_EDP( # Use suffixed class
            config_path_or_file=effective_config_path_for_cfg_mgr if effective_config_path_for_cfg_mgr else DEFAULT_CONFIG_FILE_PATH_EDP, 
            config_value_retriever=config_retriever_func
        )
        
        if output_data_directory:
            self.main_logger.info(f"EDP Init: Overriding 'data_directory_base' with explicit path: '{output_data_directory}'")
            if "system_settings" not in self.config_manager_instance.config:
                self.config_manager_instance.config["system_settings"] = {} 
            self.config_manager_instance.config["system_settings"]["data_directory_base"] = os.path.abspath(output_data_directory)
            if "processed_data_subdirectory" not in self.config_manager_instance.config["system_settings"]:
                 self.config_manager_instance.config["system_settings"]["processed_data_subdirectory"] = "edp_instance_outputs_override_v321" # Changed version
            self.main_logger.debug(f"Config 'data_directory_base' updated to: {self.config_manager_instance.config['system_settings']['data_directory_base']}")

        self.its_integrator_instance = ITSIntegrator_EDP(self.config_manager_instance) # Use suffixed class
        self.data_processing_pipeline = DataProcessor_EDP(self.config_manager_instance, self.its_integrator_instance) # Use suffixed class
        
        if self.config_manager_instance.config.get("_edp_v321_config_validation_errors"): # Changed version
            self.main_logger.warning(f"EDP Configuration validation reported issues: {self.config_manager_instance.config['_edp_v321_config_validation_errors']}") # Changed version
        else:
            self.main_logger.info("EDP Configuration essential validation passed.")
        
        self.main_logger.info(f"EnhancedDataProcessor System (v3.2.1) initialization complete. Output directory target: '{self.get_processor_output_directory()}'") # Changed version

    def process_market_data_bundle(self,
                                   market_data_payload: Dict[str, Dict[str, Any]], 
                                   tradier_context_payload: Optional[Dict[str, Dict[str, Any]]] = None,
                                   expiration_calendars_payload: Optional[Dict[str, List[date]]] = None
                                  ) -> Dict[str, Dict[str, Any]]: 
        self.main_logger.info(f"EDP Main Instance (v3.2.1): Received request to process market data bundle for {len(market_data_payload)} symbol(s).") # Changed version
        if not market_data_payload:
            self.main_logger.warning("EDP Main Instance: process_market_data_bundle called with an empty or None market_data_payload. Returning empty results.")
            return {}
        
        for sym, data in market_data_payload.items():
            options_info = "DataFrame" if isinstance(data.get("options_chain"), pd.DataFrame) else f"type {type(data.get('options_chain'))}"
            options_len = len(data.get("options_chain")) if isinstance(data.get("options_chain"), (list, pd.DataFrame)) else "N/A"
            self.main_logger.debug(f"  Symbol '{sym}': CV options data is {options_info} with {options_len} items. Underlying keys: {list(data.get('underlying', {}).keys())}")
        if tradier_context_payload:
             self.main_logger.debug(f"Tradier context provided for symbols: {list(tradier_context_payload.keys())}")
        if expiration_calendars_payload:
             self.main_logger.debug(f"Expiration calendars provided for symbols: {list(expiration_calendars_payload.keys())}")

        try:
            processed_results = self.data_processing_pipeline.process_market_data_bundle(
                market_data_payload, tradier_context_payload, expiration_calendars_payload
            )
            self.main_logger.info(f"EDP Main Instance: Successfully completed processing for {len(processed_results)} symbol(s).")
            return processed_results
        except Exception as e_process_bundle_fatal:
            self.main_logger.critical(f"FATAL UNHANDLED EXCEPTION in EDP process_market_data_bundle top level: {e_process_bundle_fatal}", exc_info=True)
            error_results: Dict[str, Dict[str, Any]] = {}
            for symbol_key_fatal in market_data_payload.keys():
                error_results[symbol_key_fatal] = self.data_processing_pipeline._create_error_bundle_for_symbol( 
                    symbol_key_fatal, 
                    f"FATAL EDP BUNDLE PROCESSING ERROR: {e_process_bundle_fatal}",
                    traceback.format_exc()
                )
            return error_results

    def get_current_config_value(self, path_keys_list: List[str], default_val: Any = None) -> Any:
        return self.config_manager_instance.get_value(path_keys_list, default_val)

    def is_its_dummy_active(self) -> bool:
        return self.its_integrator_instance.is_using_dummy_its()

    def get_active_its_instance(self) -> Any:
        return self.its_integrator_instance.get_its_instance()

    def get_processor_output_directory(self) -> str:
        if self.data_processing_pipeline.output_directory_main is None:
            self.data_processing_pipeline._ensure_output_directory_exists() 
        return self.data_processing_pipeline.output_directory_main or DEFAULT_OUTPUT_DATA_DIR_EDP

if __name__ == "__main__":
    test_logger_edp_main = logging.getLogger("EDP_Standalone_Test_v321") # Changed version
    if not test_logger_edp_main.handlers: 
        test_handler_stdout = logging.StreamHandler(sys.stdout)
        test_formatter_detailed = logging.Formatter("[%(levelname)s] (%(name)s:%(funcName)s:%(lineno)d) %(asctime)s - %(message)s")
        test_handler_stdout.setFormatter(test_formatter_detailed)
        test_logger_edp_main.addHandler(test_handler_stdout)
        test_logger_edp_main.propagate = False 
    test_logger_edp_main.setLevel(logging.DEBUG) 

    logging.getLogger("EnhancedDataProcessor_v321").setLevel(logging.DEBUG) # Changed version
    for handler in logging.getLogger("EnhancedDataProcessor_v321").handlers: # Changed version
        if handler: handler.setLevel(logging.DEBUG) 

    def run_edp_standalone_test_v321(): # Changed version
        test_logger_edp_main.info(f"--- Starting EDP Standalone Test (Version: {CONFIG_SCHEMA_VERSION_PROCESSOR_EDP}) ---")
        
        script_dir_test = os.path.dirname(os.path.abspath(__file__))
        project_root_dir_test = os.path.dirname(script_dir_test) 
        test_config_file_path = os.path.join(project_root_dir_test, "config_v2.json")
        test_logger_edp_main.info(f"Attempting to use config file for test: '{test_config_file_path}'")

        if not os.path.exists(test_config_file_path):
            test_logger_edp_main.critical(f"Test config file '{test_config_file_path}' NOT FOUND. EDP will use internal defaults.")
            test_config_file_path = None 

        edp_test_instance = EnhancedDataProcessor(config_path=test_config_file_path)
        test_logger_edp_main.info(f"EDP Test Instance Initialized. Using Dummy ITS: {edp_test_instance.is_its_dummy_active()}")
        test_logger_edp_main.info(f"EDP Test Configured Output Directory: '{edp_test_instance.get_processor_output_directory()}'")

        sample_symbol_test = "TESTSYM_EDP_V321" # Changed version
        sample_current_price_test = 150.75
        sample_fetch_ts_test = datetime.now().isoformat()
        sample_cv_options_data_list = []

        strike_col_sample = ids.COL_STRIKE if IDS_IMPORTED_SUCCESSFULLY_EDP else "strike_price" 
        opt_kind_col_sample = ids.COL_OPT_KIND if IDS_IMPORTED_SUCCESSFULLY_EDP else "opt_kind"
        
        for strike_offset_val_its in [-10, -5, 0, 5, 10]:
            for opt_k_val_its in ['call', 'put']:
                contract_data_sample = {
                    strike_col_sample: sample_current_price_test + strike_offset_val_its,
                    opt_kind_col_sample: opt_k_val_its,
                    (ids.COL_OPTION_SYMBOL if IDS_IMPORTED_SUCCESSFULLY_EDP else "symbol"): f".{sample_symbol_test}{datetime.now().strftime('%y%m%d')}{'C' if opt_k_val_its=='call' else 'P'}{int(sample_current_price_test + strike_offset_val_its)}000",
                    (ids.COL_UNDERLYING_SYMBOL_CHAIN if IDS_IMPORTED_SUCCESSFULLY_EDP else "underlying_symbol"): sample_symbol_test,
                    (ids.COL_PRICE_OPTION_CONTRACT if IDS_IMPORTED_SUCCESSFULLY_EDP else "price"): round(np.random.uniform(0.1, 5.0), 2),
                    (ids.COL_DELTA_CONTRACT if IDS_IMPORTED_SUCCESSFULLY_EDP else "delta"): round(np.random.uniform(-1,1) if opt_k_val_its == 'put' else np.random.uniform(0,1), 4),
                    (ids.COL_GAMMA_CONTRACT if IDS_IMPORTED_SUCCESSFULLY_EDP else "gamma"): round(np.random.uniform(0.01, 0.1), 4),
                    (ids.COL_VEGA_CONTRACT if IDS_IMPORTED_SUCCESSFULLY_EDP else "vega"): round(np.random.uniform(0.01, 0.2), 4),
                    (ids.COL_THETA_CONTRACT if IDS_IMPORTED_SUCCESSFULLY_EDP else "theta"): round(np.random.uniform(-0.1, -0.01), 4),
                    (ids.COL_OI_OPTION_CONTRACT if IDS_IMPORTED_SUCCESSFULLY_EDP else "oi"): np.random.randint(10, 1000),
                    (ids.COL_VOLUME_OPTION_CONTRACT if IDS_IMPORTED_SUCCESSFULLY_EDP else "volm"): np.random.randint(1, 200),
                    (ids.COL_GXOI_CONTRACT if IDS_IMPORTED_SUCCESSFULLY_EDP else "gxoi"): round(np.random.uniform(1e5, 1e7) * (1 if np.random.rand() > 0.3 else -1), 2),
                    (ids.COL_DXOI_CONTRACT if IDS_IMPORTED_SUCCESSFULLY_EDP else "dxoi"): round(np.random.uniform(1e4, 1e6) * (1 if opt_k_val_its == 'call' else -1), 2),
                    (ids.CV_CHAIN_PARAM_DELTAS_BUY_CONTRACT if IDS_IMPORTED_SUCCESSFULLY_EDP else "deltas_buy"): round(np.random.uniform(0, 100),2),
                    (ids.CV_CHAIN_PARAM_DELTAS_SELL_CONTRACT if IDS_IMPORTED_SUCCESSFULLY_EDP else "deltas_sell"): round(np.random.uniform(0, 100),2),
                }
                sample_cv_options_data_list.append(contract_data_sample)
        test_logger_edp_main.debug(f"Generated {len(sample_cv_options_data_list)} sample option contracts.")

        sample_cv_underlying_data_dict = {
            (ids.CV_UND_PARAM_PRICE if IDS_IMPORTED_SUCCESSFULLY_EDP else "price"): sample_current_price_test,
            (ids.CV_UND_PARAM_FETCH_TIMESTAMP if IDS_IMPORTED_SUCCESSFULLY_EDP else "fetch_timestamp"): sample_fetch_ts_test,
            (ids.CV_UND_PARAM_VOLATILITY if IDS_IMPORTED_SUCCESSFULLY_EDP else "volatility"): round(np.random.uniform(0.1, 0.3), 4)
        }
        cv_payload_for_edp_test = {sample_symbol_test: {"options_chain": sample_cv_options_data_list, 
                                                        "underlying": sample_cv_underlying_data_dict, "error": None}}

        sample_tradier_ohlcv_df = pd.DataFrame({
            'date': pd.to_datetime([datetime.now() - timedelta(days=i) for i in range(5, 0, -1)]), 
            'open': np.random.uniform(145,148,5), 'high': np.random.uniform(150,153,5), 
            'low': np.random.uniform(144,149,5), 'close': np.random.uniform(147,152,5), 
            'volume': np.random.randint(1e6,5e6,5)
        })
        iv_percentile_key_sample = ids.CV_UND_PARAM_IV_PERCENTILE_30D if IDS_IMPORTED_SUCCESSFULLY_EDP else "iv_percentile_30d"
        sample_tradier_iv_quote_data_dict = {
            "symbol": sample_symbol_test, "time": datetime.now().time().isoformat(), 
            "current_iv": round(np.random.uniform(0.15,0.25),4), 
            "avg_5day_iv_tradier_approx": round(np.random.uniform(0.14,0.23),4), 
            iv_percentile_key_sample: round(np.random.uniform(0,1),2)
        }
        sample_exp_calendar = [date.today() + timedelta(days=d) for d in [7,14,21,30,60,90]]
        tradier_payload_for_edp_test = {
            sample_symbol_test: {
                "iv_and_quote_data": sample_tradier_iv_quote_data_dict, 
                "historical_ohlcv_df": sample_tradier_ohlcv_df, 
                "expiration_calendar": sample_exp_calendar, 
                "error": None
            }
        }
        exp_cal_payload_for_edp_test = {sample_symbol_test: sample_exp_calendar}
        test_logger_edp_main.debug("Sample CV and Tradier payloads prepared for EDP test.")

        test_logger_edp_main.info(f"Calling EDP process_market_data_bundle for test symbol: {sample_symbol_test}")
        edp_test_results = edp_test_instance.process_market_data_bundle(
            cv_payload_for_edp_test, 
            tradier_payload_for_edp_test, 
            exp_cal_payload_for_edp_test
        )

        test_logger_edp_main.info(f"--- EnhancedDataProcessor Standalone Test (v3.2.1) Processing Results ---") # Changed version
        if not edp_test_results: 
            test_logger_edp_main.error("Processing returned NO results (empty dictionary). This is unexpected.")
        
        for symbol_key_res, result_data_bundle_res in edp_test_results.items():
            test_logger_edp_main.info(f"  --- Results for Symbol: {symbol_key_res} ---")
            test_logger_edp_main.info(f"    EDP Reported Error: {result_data_bundle_res.get('error')}")
            test_logger_edp_main.info(f"    EDP Reported Traceback: {'Present' if result_data_bundle_res.get('traceback') else 'None'}")
            test_logger_edp_main.info(f"    EDP Reports Using Dummy ITS: {result_data_bundle_res.get('using_dummy_its')}")
            
            final_df_object_res = result_data_bundle_res.get("final_metric_rich_df_obj")
            if isinstance(final_df_object_res, pd.DataFrame):
                test_logger_edp_main.info(f"    'final_metric_rich_df_obj' DataFrame Shape: {final_df_object_res.shape}")
                if not final_df_object_res.empty:
                    test_logger_edp_main.info(f"      Columns: {final_df_object_res.columns.tolist()}")
                    test_logger_edp_main.debug(f"      Sample of final_metric_rich_df_obj (head 1):\n{final_df_object_res.head(1)}")
            else:
                test_logger_edp_main.warning(f"    'final_metric_rich_df_obj' is NOT a DataFrame. Type: {type(final_df_object_res)}")
            
            processed_data_dict = result_data_bundle_res.get("processed_data", {})
            test_logger_edp_main.debug(f"    Processed Data Keys: {list(processed_data_dict.keys())}")
            test_logger_edp_main.debug(f"    Recommendations Count: {len(processed_data_dict.get('recommendations', []))}")

        test_logger_edp_main.info(f"--- EnhancedDataProcessor Standalone Test (v3.2.1) Completed ---") # Changed version

    try:
        run_edp_standalone_test_v321() # Changed version
    except Exception as e_standalone_main_v321_exec: # Changed version
        test_logger_edp_main.critical(f"EDP Standalone Test SCRIPT CRASHED UNEXPECTEDLY: {e_standalone_main_v321_exec}", exc_info=True)

