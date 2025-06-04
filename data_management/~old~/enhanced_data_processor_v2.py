#!/usr/bin/env python3
# enhanced_data_processor_v2.py
# Elite Options Trading System - Enhanced Data Processor v3.1.1
# Canon Directive Version: Ensuring full integration and robustness.
# Changes:
# - ConfigurationManager: Stores actual loaded config path. get_output_directory prioritizes it.
# - EnhancedDataProcessor: Accepts explicit output_data_directory to override config-derived base path.

"""
Enhanced Data Processor for the Elite Options Trading System.

This module processes options market data, calculates advanced metrics,
identifies key levels, and generates trading signals using the Integrated
Trading System (ITS).

Version 3.1.1 features:
- More robust output directory handling in ConfigurationManager.
- EnhancedDataProcessor can accept an explicit output_data_directory.
- Modular architecture with clear separation of concerns.
- Robust ITS instantiation with multiple fallback paths and detailed logging.
- Comprehensive configuration loading prioritizing getter, then file, then defaults.
- Rigorous input data validation and preparation.
- Advanced error handling and standardized result packaging.
- Support for modern market structure metrics via ITS.
- Extensible design for AI/ML integration (via ITS).
- Performance optimizations for handling large datasets using ThreadPoolExecutor.
- Comprehensive logging and diagnostics throughout the processing pipeline.
"""

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
import copy # Added for deepcopy

# Third-Party Imports
import pandas as pd
import numpy as np

# --- Logging Configuration ---
if not logging.getLogger("EnhancedDataProcessor").hasHandlers():
    logging.basicConfig(
        level=logging.INFO, 
        format="[%(levelname)s] (%(name)s:%(lineno)d) %(asctime)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout), 
            logging.FileHandler("edp_v3_canon_fix.log", mode='a') 
        ]
    )
logger = logging.getLogger("EnhancedDataProcessor")

# --- Constants ---
DEFAULT_CONFIG_FILE_PATH: str = "config_v2.json" 
DEFAULT_OUTPUT_DATA_DIR: str = "eots_data_output/processed_data" 
JSON_CONVERSION_ERROR_PLACEHOLDER: str = "ERR_JSON_CONVERSION_FAILED"
DEFAULT_THREAD_POOL_SIZE: int = min(4, os.cpu_count() or 1) 
CONFIG_SCHEMA_VERSION_PROCESSOR: str = "EDP_v3.1.1_CanonFix"


# ===== Configuration Management =====
class ConfigurationManager:
    """
    Manages loading, validation, and access to application configuration settings
    for the EnhancedDataProcessor.
    """
    def __init__(self,
                 config_path_or_file: str = DEFAULT_CONFIG_FILE_PATH,
                 config_value_retriever: Optional[Callable[[List[str], Any], Any]] = None):
        self.logger = logger.getChild("ConfigurationManager")
        self.provided_config_path: str = config_path_or_file
        self.config_value_retriever = config_value_retriever
        self.config: Dict[str, Any] = {}
        self.loaded_config_file_actual_path: Optional[str] = None # Store path of config loaded by this instance
        self._load_configuration()

    def _resolve_config_file_path(self, config_file_name: str) -> str:
        if not config_file_name: # Handle case where None or empty string is passed
            self.logger.warning("resolve_config_file_path received an empty or None config_file_name. This might lead to issues.")
            return os.path.abspath(DEFAULT_CONFIG_FILE_PATH) # Fallback to default if name is invalid

        if os.path.isabs(config_file_name):
            return config_file_name
        
        path_from_cwd = os.path.join(os.getcwd(), config_file_name)
        if os.path.exists(path_from_cwd):
            self.logger.debug(f"Resolved config path relative to CWD: {path_from_cwd}")
            return os.path.abspath(path_from_cwd)
            
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            path_from_script_dir = os.path.join(script_dir, config_file_name)
            if os.path.exists(path_from_script_dir):
                self.logger.debug(f"Resolved config path relative to EDP script directory: {path_from_script_dir}")
                return os.path.abspath(path_from_script_dir)
        except NameError: 
            self.logger.debug("Could not resolve config path relative to script dir (__file__ undefined).")

        self.logger.warning(f"Config file '{config_file_name}' not found via CWD or script relative paths. Using original path: '{config_file_name}' for attempt.")
        return os.path.abspath(config_file_name) 

    def _load_configuration(self) -> None:
        loaded_successfully = False
        if self.config_value_retriever is not None and callable(self.config_value_retriever):
            self.logger.info("Attempting to load configuration using provided config_value_retriever.")
            try:
                retrieved_config = self.config_value_retriever([], {}) 
                if isinstance(retrieved_config, dict) and retrieved_config:
                    self.config = copy.deepcopy(retrieved_config) 
                    self.logger.info("Successfully loaded and applied configuration from config_value_retriever.")
                    # If config is from retriever, loaded_config_file_actual_path remains None unless set by retriever.
                    # The retriever might populate _config_file_path_cached_at itself.
                    self.loaded_config_file_actual_path = self.config.get("_config_file_path") or self.config.get("_config_file_path_cached_at")

                    loaded_successfully = True
                else:
                    self.logger.warning("config_value_retriever did not return a valid, non-empty dictionary. Will try file.")
            except Exception as e_getter:
                self.logger.error(f"Error loading configuration using config_value_retriever: {e_getter}. Will try file.", exc_info=True)
        
        if not loaded_successfully and self.provided_config_path: # Only try file if path was given and retriever failed/not used
            resolved_path = self._resolve_config_file_path(self.provided_config_path)
            self.logger.info(f"Attempting to load configuration from file: {resolved_path}")
            if os.path.exists(resolved_path):
                try:
                    with open(resolved_path, 'r', encoding='utf-8') as f:
                        file_config = json.load(f)
                    if isinstance(file_config, dict):
                        self.config = file_config 
                        self.loaded_config_file_actual_path = resolved_path # Store the path of the file loaded by THIS manager
                        self.logger.info(f"Successfully loaded configuration from file: {resolved_path}")
                        loaded_successfully = True
                    else:
                        self.logger.error(f"Configuration file at '{resolved_path}' did not contain a valid JSON dictionary.")
                except json.JSONDecodeError as e_json:
                    self.logger.error(f"Error decoding JSON from configuration file '{resolved_path}': {e_json}")
                except Exception as e_file:
                    self.logger.error(f"Error loading configuration file '{resolved_path}': {e_file}", exc_info=True)
            else:
                self.logger.warning(f"Configuration file not found at resolved path: {resolved_path}.")

        if not loaded_successfully or not self.config: 
            self.logger.warning("No configuration loaded from getter or file. Using internal default configuration for EDP.")
            self.config = self._get_internal_default_config()
            self.config["_config_is_internal_default"] = True
            self.loaded_config_file_actual_path = None # No file was loaded by this manager
            loaded_successfully = True 
        
        self._add_processor_metadata_to_config(loaded_successfully)
        self._validate_loaded_configuration()

    def _add_processor_metadata_to_config(self, load_status: bool) -> None:
        self.config["_edp_config_source_path_attempted"] = self.provided_config_path
        self.config["_edp_config_resolved_path_used"] = self.loaded_config_file_actual_path if self.loaded_config_file_actual_path else \
                                                       (self.config.get("_config_file_path_cached_at") if self.config_value_retriever else "Internal Defaults")
        self.config["_edp_config_load_timestamp"] = datetime.now().isoformat()
        self.config["_edp_config_schema_version"] = CONFIG_SCHEMA_VERSION_PROCESSOR
        self.config["_edp_config_loaded_successfully_external"] = load_status and not self.config.get("_config_is_internal_default", False)

    def _get_internal_default_config(self) -> Dict[str, Any]:
        self.logger.info("Generating internal default configuration for EnhancedDataProcessor.")
        return {
            "system_settings": {
                "data_directory_base": DEFAULT_OUTPUT_DATA_DIR, 
                "processed_data_subdirectory": "its_outputs", 
                "thread_pool_size": DEFAULT_THREAD_POOL_SIZE
            },
            "visualization_settings": { 
                "mspi_visualizer": {
                    "column_names": {
                        "strike": "strike_price" 
                    }
                }
            },
        }

    def _validate_loaded_configuration(self) -> None:
        self.logger.debug("Validating loaded configuration for EDP requirements.")
        errors_found: List[str] = []
        if "system_settings" not in self.config or not isinstance(self.get_value(["system_settings"]), dict):
            errors_found.append("Missing or invalid 'system_settings' section.")
        else:
            if not isinstance(self.get_value(["system_settings", "data_directory_base"]), str):
                errors_found.append("'system_settings.data_directory_base' is missing or not a string.")
            if not isinstance(self.get_value(["system_settings", "processed_data_subdirectory"]), str):
                errors_found.append("'system_settings.processed_data_subdirectory' is missing or not a string.")
            if not isinstance(self.get_value(["system_settings", "thread_pool_size"]), int):
                errors_found.append("'system_settings.thread_pool_size' is missing or not an integer.")
        
        if not isinstance(self.get_strike_column_name(), str):
            errors_found.append("Strike column name ('visualization_settings.mspi_visualizer.column_names.strike') is not configured correctly as a string.")

        if errors_found:
            self.logger.warning(f"Configuration validation issues found for EDP: {'; '.join(errors_found)}")
            self.config["_edp_config_validation_errors"] = errors_found
        else:
            self.logger.info("Loaded configuration passed EDP's essential validation checks.")
            self.config["_edp_config_validation_errors"] = []

    def get_value(self, path_keys: List[str], default_return: Any = None) -> Any:
        current_val = self.config
        try:
            for key_item in path_keys:
                if isinstance(current_val, dict):
                    current_val = current_val[key_item]
                else: 
                    return default_return
            return current_val
        except KeyError: 
            return default_return
        except Exception as e_getval: 
            self.logger.error(f"Error getting config value for path '{'.'.join(path_keys)}': {e_getval}", exc_info=False)
            return default_return

    def get_output_directory(self, output_dir_manual_override: Optional[str] = None) -> str:
        """
        Determines the absolute output directory for processed data.
        Priority:
        1. output_dir_manual_override (if absolute)
        2. output_dir_manual_override (if relative, resolved against CWD)
        3. Configured 'data_directory_base' + 'processed_data_subdirectory':
           - If 'data_directory_base' is absolute, use it.
           - If relative, try resolving against actual loaded config file's dir.
           - If config from retriever or config file path not useful, resolve against CWD.
        """
        if output_dir_manual_override and isinstance(output_dir_manual_override, str):
            if os.path.isabs(output_dir_manual_override):
                self.logger.debug(f"Using manual absolute output directory override: '{output_dir_manual_override}'")
                return output_dir_manual_override
            resolved_manual_override = os.path.abspath(output_dir_manual_override)
            self.logger.debug(f"Using manual relative output directory override (resolved to CWD): '{resolved_manual_override}'")
            return resolved_manual_override
            
        base_output_dir_from_config = self.get_value(["system_settings", "data_directory_base"], DEFAULT_OUTPUT_DATA_DIR)
        output_subdirectory_from_config = self.get_value(["system_settings", "processed_data_subdirectory"], "its_outputs")
        
        final_resolved_base_dir = base_output_dir_from_config
        if not os.path.isabs(base_output_dir_from_config):
            # Try to resolve relative to the config file that was actually loaded by this ConfigurationManager instance
            if self.loaded_config_file_actual_path and os.path.exists(os.path.dirname(self.loaded_config_file_actual_path)):
                config_parent_dir = os.path.dirname(self.loaded_config_file_actual_path)
                final_resolved_base_dir = os.path.join(config_parent_dir, base_output_dir_from_config)
                self.logger.debug(f"Output base '{base_output_dir_from_config}' resolved relative to loaded config dir '{config_parent_dir}' -> '{final_resolved_base_dir}'")
            else:
                # If config came from retriever or loaded_config_file_actual_path is not set/valid,
                # or if the config itself has a _config_file_path_cached_at (e.g. from dashboard's APP_CONFIG)
                # that might be from a different system, it's safer to default to CWD for relative paths.
                # However, if an explicit output_data_directory was passed to EnhancedDataProcessor,
                # that would have already updated data_directory_base to an absolute path.
                self.logger.info(f"No directly loaded config file path for this ConfigurationManager instance or path invalid. Resolving output base '{base_output_dir_from_config}' relative to CWD: '{os.getcwd()}'")
                final_resolved_base_dir = os.path.join(os.getcwd(), base_output_dir_from_config)
                
        full_output_path = os.path.join(final_resolved_base_dir, output_subdirectory_from_config)
        abs_full_output_path = os.path.abspath(full_output_path)
        self.logger.debug(f"Final resolved output directory for EDP: '{abs_full_output_path}'")
        return abs_full_output_path
        
    def get_thread_pool_size(self) -> int:
        size = self.get_value(["system_settings", "thread_pool_size"], DEFAULT_THREAD_POOL_SIZE)
        try: return int(size) if int(size) > 0 else DEFAULT_THREAD_POOL_SIZE
        except (ValueError, TypeError): return DEFAULT_THREAD_POOL_SIZE
        
    def get_strike_column_name(self) -> str:
        return str(self.get_value(["visualization_settings", "mspi_visualizer", "column_names", "strike"], "strike_price"))


# ===== ITS (Integrated Trading System) Integration =====
# ITSIntegrator and DummyIntegratedTradingSystem remain largely the same as provided.
# Minor logging adjustment if needed.
class ITSIntegrator:
    def __init__(self, configuration_manager_instance: ConfigurationManager):
        self.logger = logger.getChild("ITSIntegrator")
        self.config_manager = configuration_manager_instance
        self.its_module_class: Optional[Type] = self._find_and_load_its_class()
        self.its_active_instance: Optional[Any] = None
        self.logger.info(f"ITSIntegrator initialized. ITS Class found: {self.its_module_class is not None}")

    def _find_and_load_its_class(self) -> Optional[Type]:
        self.logger.info("Attempting to locate and load IntegratedTradingSystem class...")
        try:
            self.logger.debug("ITS Load Strategy 1: Attempting direct import: 'from core_analytics.integrated_strategies_v2 import IntegratedTradingSystem'")
            from core_analytics.integrated_strategies_v2 import IntegratedTradingSystem
            self.logger.info("ITS Load Strategy 1: Successfully imported 'IntegratedTradingSystem' from 'core_analytics.integrated_strategies_v2'.")
            return IntegratedTradingSystem
        except ImportError as e_imp_direct:
            self.logger.warning(f"ITS Load Strategy 1: Failed to directly import from 'core_analytics.integrated_strategies_v2': {e_imp_direct}")
        except Exception as e_direct_other:
            self.logger.error(f"ITS Load Strategy 1: Unexpected error during direct import: {e_direct_other}", exc_info=True)

        self.logger.debug("ITS Load Strategy 2: Searching common project locations...")
        try: edp_script_dir = os.path.dirname(os.path.abspath(__file__))
        except NameError: edp_script_dir = os.getcwd() 
        
        common_search_paths = [
            os.getcwd(), edp_script_dir, os.path.join(os.getcwd(), "core_analytics"),
            os.path.join(edp_script_dir, "core_analytics"), 
            os.path.join(os.path.dirname(edp_script_dir), "core_analytics"),
            os.path.join(os.getcwd(), "upload"), os.path.join(edp_script_dir, "upload")
        ]
        if os.path.basename(edp_script_dir) != "": 
            common_search_paths.append(os.path.dirname(edp_script_dir))

        self.logger.debug(f"ITS Load Strategy 2: Common search paths: {common_search_paths}")
        for idx, loc_path in enumerate(common_search_paths):
            potential_file_path = os.path.join(loc_path, "integrated_strategies_v2.py")
            self.logger.debug(f"  Strategy 2.{idx+1}: Checking path: {potential_file_path}")
            if os.path.exists(potential_file_path):
                self.logger.info(f"ITS Load Strategy 2: Found potential ITS file at '{potential_file_path}'. Attempting to load.")
                try:
                    spec = importlib.util.spec_from_file_location("integrated_strategies_v2_dynamic", potential_file_path)
                    if spec and spec.loader:
                        module_dynamic = importlib.util.module_from_spec(spec)
                        sys.modules["integrated_strategies_v2_dynamic_instance"] = module_dynamic 
                        spec.loader.exec_module(module_dynamic)
                        if hasattr(module_dynamic, "IntegratedTradingSystem"):
                            self.logger.info(f"ITS Load Strategy 2: Successfully loaded 'IntegratedTradingSystem' class from '{potential_file_path}'.")
                            return getattr(module_dynamic, "IntegratedTradingSystem")
                        else:
                            self.logger.warning(f"ITS Load Strategy 2: File '{potential_file_path}' loaded but does not contain 'IntegratedTradingSystem' class.")
                    else:
                        self.logger.warning(f"ITS Load Strategy 2: Could not create module spec for '{potential_file_path}'.")
                except Exception as e_load_common:
                    self.logger.error(f"ITS Load Strategy 2: Error loading ITS from '{potential_file_path}': {e_load_common}", exc_info=True)

        self.logger.debug(f"ITS Load Strategy 3: Searching Python sys.path ({len(sys.path)} entries)...")
        for sys_path_entry in sys.path:
            potential_file_path_sys = os.path.join(sys_path_entry, "integrated_strategies_v2.py")
            if os.path.exists(potential_file_path_sys): 
                self.logger.info(f"ITS Load Strategy 3: Found potential ITS file in sys.path at '{potential_file_path_sys}'. Attempting to load.")
                try:
                    spec_sys = importlib.util.spec_from_file_location("integrated_strategies_v2_syspath", potential_file_path_sys)
                    if spec_sys and spec_sys.loader:
                        module_sys = importlib.util.module_from_spec(spec_sys)
                        sys.modules["integrated_strategies_v2_syspath_instance"] = module_sys
                        spec_sys.loader.exec_module(module_sys)
                        if hasattr(module_sys, "IntegratedTradingSystem"):
                            self.logger.info(f"ITS Load Strategy 3: Successfully loaded 'IntegratedTradingSystem' class from sys.path at '{potential_file_path_sys}'.")
                            return getattr(module_sys, "IntegratedTradingSystem")
                except Exception as e_load_syspath:
                    self.logger.error(f"ITS Load Strategy 3: Error loading ITS from sys.path at '{potential_file_path_sys}': {e_load_syspath}", exc_info=True)
        
        self.logger.error("ITS Load Strategies FAILED: Could not load 'IntegratedTradingSystem' class using any defined strategy.")
        return None

    def get_its_instance(self) -> Any:
        if self.its_active_instance is not None:
            self.logger.debug("Returning existing ITS instance.")
            return self.its_active_instance
            
        if self.its_module_class is not None:
            self.logger.info("Attempting to create new instance of REAL IntegratedTradingSystem.")
            try:
                # ITS uses its own ConfigurationManager, which will load based on the path.
                # Provide the path of the config file that EDP's ConfigurationManager determined/used.
                config_file_path_for_its = self.config_manager.loaded_config_file_actual_path or \
                                           self.config_manager.config.get("_config_file_path_cached_at") or \
                                           self.config_manager.provided_config_path or \
                                           DEFAULT_CONFIG_FILE_PATH # Ultimate fallback

                if not config_file_path_for_its or not os.path.exists(config_file_path_for_its):
                     self.logger.warning(f"ITS Instantiation: Config path for ITS ('{config_file_path_for_its}') is invalid or file doesn't exist. Real ITS might fail or use internal defaults.")
                
                self.logger.info(f"Creating REAL ITS instance using config_path: '{config_file_path_for_its}'")
                self.its_active_instance = self.its_module_class(config_path=config_file_path_for_its)
                self.logger.info(f"Successfully created REAL IntegratedTradingSystem instance. Type: {type(self.its_active_instance).__name__}")
                return self.its_active_instance
            except Exception as e_create_its:
                self.logger.critical(f"CRITICAL ERROR creating instance of REAL IntegratedTradingSystem: {e_create_its}. Falling back to Dummy ITS.", exc_info=True)
        else:
            self.logger.warning("Real ITS class was not loaded. Will use Dummy ITS.")
            
        self.logger.warning("Instantiating DummyIntegratedTradingSystem as fallback.")
        dummy_config_path_for_its = self.config_manager.loaded_config_file_actual_path or \
                                    self.config_manager.config.get("_config_file_path_cached_at") or \
                                    self.config_manager.provided_config_path or \
                                    DEFAULT_CONFIG_FILE_PATH
        self.its_active_instance = DummyIntegratedTradingSystem(config_path=dummy_config_path_for_its)
        return self.its_active_instance
        
    def is_using_dummy_its(self) -> bool:
        return self.its_module_class is None or isinstance(self.its_active_instance, DummyIntegratedTradingSystem)

class DummyIntegratedTradingSystem:
    def __init__(self, config_path: Optional[str] = None): 
        self.logger = logger.getChild("DummyITS")
        self.config_path_dummy = config_path or DEFAULT_CONFIG_FILE_PATH
        self.config_dummy: Dict[str, Any] = {}
        self.logger.warning(f"Initializing DummyIntegratedTradingSystem. Config path provided: '{self.config_path_dummy}'")
        
        try:
            if self.config_path_dummy and os.path.exists(self.config_path_dummy):
                with open(self.config_path_dummy, 'r', encoding='utf-8') as f_dummy_cfg:
                    self.config_dummy = json.load(f_dummy_cfg)
                self.logger.info(f"DummyITS: Successfully loaded configuration from '{self.config_path_dummy}' for its internal use (e.g., strike column lookup).")
            else:
                self.logger.warning(f"DummyITS: Configuration file '{self.config_path_dummy}' not found. Dummy will use hardcoded defaults for strike col etc.")
        except Exception as e_dummy_cfg:
            self.logger.error(f"DummyITS: Error loading its config from '{self.config_path_dummy}': {e_dummy_cfg}")

    def _get_dummy_config_value(self, path_keys: List[str], default_val: Any = None) -> Any:
        current = self.config_dummy
        try:
            for key_item in path_keys: current = current[key_item]
            return current
        except (KeyError, TypeError): return default_val
            
    def process_market_data_and_generate_recommendations(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        symbol = kwargs.get("symbol", "DUMMY_SYM")
        raw_options_df_input = kwargs.get("raw_options_data") 
        self.logger.warning(f"DummyITS: Executing 'process_market_data_and_generate_recommendations' for symbol '{symbol}'. This is a DUMMY operation.")
        
        output_df = pd.DataFrame()
        if isinstance(raw_options_df_input, pd.DataFrame) and not raw_options_df_input.empty:
            output_df = raw_options_df_input.copy()
        elif isinstance(raw_options_df_input, list) and raw_options_df_input: 
            output_df = pd.DataFrame(raw_options_df_input)
        
        dummy_metric_cols = [
            'mspi', 'dag_custom_norm', 'tdpi_norm', 'vri_norm', 
            'a_dag_norm', 'd_tdpi_norm', 'vri_2_0_norm', 'e_sdag_composite_norm', 
            'sai', 'ssi' 
        ]
        for metric_col_dummy in dummy_metric_cols:
            if metric_col_dummy not in output_df.columns:
                output_df[metric_col_dummy] = 0.0
        
        strike_col_name_dummy = self._get_dummy_config_value(
            ["visualization_settings", "mspi_visualizer", "column_names", "strike"], "strike_price"
        )
        if not output_df.empty:
            if strike_col_name_dummy not in output_df.columns and "strike" in output_df.columns:
                output_df.rename(columns={'strike': strike_col_name_dummy}, inplace=True)
            elif strike_col_name_dummy not in output_df.columns: 
                output_df[strike_col_name_dummy] = np.nan 
        
        aggregated_df_dummy = pd.DataFrame()
        if not output_df.empty and strike_col_name_dummy in output_df.columns:
            try:
                numeric_cols = output_df.select_dtypes(include=np.number).columns.tolist()
                string_cols = output_df.select_dtypes(exclude=np.number).columns.tolist()
                agg_spec = {col: 'mean' for col in numeric_cols if col != strike_col_name_dummy} 
                agg_spec.update({col: 'first' for col in string_cols if col != strike_col_name_dummy}) 
                if agg_spec: 
                     aggregated_df_dummy = output_df.groupby(strike_col_name_dummy).agg(agg_spec).reset_index()
            except Exception as e_agg_dummy:
                self.logger.warning(f"DummyITS: Error during dummy aggregation for {symbol}: {e_agg_dummy}")

        return {
            "symbol": symbol,
            "error": "Using DUMMY IntegratedTradingSystem (Real ITS failed to load or instantiate). Placeholder data generated.",
            "processed_options_df": output_df.to_dict(orient='records') if not output_df.empty else [],
            "aggregated_strike_data": aggregated_df_dummy.to_dict(orient='records') if not aggregated_df_dummy.empty else [],
            "key_levels": {
                "all_levels_sorted_by_strength": [], "support_df": pd.DataFrame().to_dict(orient='records'),
                "resistance_df": pd.DataFrame().to_dict(orient='records'), "error": "Dummy Levels Data"
            },
            "signals": {"directional": {"bullish": [], "bearish": []}, "error": "Dummy Signals Data"},
            "recommendations": [{
                "id": f"DUMMYREC_{symbol}_001", "symbol": symbol, "category": "Dummy Info",
                "rationale": "This is a placeholder from DummyITS. Real ITS is not operational.",
                "status": "DUMMY_PLACEHOLDER", "conviction_stars": 0
            }],
            "current_mspi_weights_applied": {"dummy_default_weight": 1.0},
            "current_adaptive_historical_context_summary": {"status": "DummyITS has no adaptive historical context."},
            "atr_value_used_by_its": 1.0, 
            "final_metric_rich_df_obj": output_df 
        }

# ===== Data Processing Core Logic =====
# DataProcessor class remains largely the same, focusing on its pipeline logic.
# It relies on ConfigurationManager for paths and ITSIntegrator for the ITS instance.
class DataProcessor:
    def __init__(self,
                 configuration_manager: ConfigurationManager,
                 its_integrator_instance: ITSIntegrator):
        self.logger = logging.getLogger("EnhancedDataProcessor.DataProcessor") 
        self.config_manager = configuration_manager
        self.its_integrator = its_integrator_instance
        
        self.output_directory_main = self.config_manager.get_output_directory() # Uses the potentially overridden path
        self._ensure_output_directory_exists() 
        self.logger.info(f"DataProcessor initialized. Output results will be directed to: '{self.output_directory_main}'")

    def _ensure_output_directory_exists(self) -> None:
        self.logger.debug(f"Ensuring output directory exists: {self.output_directory_main}")
        try:
            os.makedirs(self.output_directory_main, exist_ok=True)
            self.logger.info(f"Output directory successfully verified/created: '{self.output_directory_main}'")
        except OSError as e_dir_os_error:
            error_message = f"Operating system error creating output directory '{self.output_directory_main}': {e_dir_os_error}"
            self.logger.critical(error_message, exc_info=True)
            raise RuntimeError(error_message) from e_dir_os_error
        except Exception as e_dir_generic: 
            error_message = f"Unexpected error creating output directory '{self.output_directory_main}': {e_dir_generic}"
            self.logger.critical(error_message, exc_info=True)
            raise RuntimeError(error_message) from e_dir_generic
            
    def _validate_input_options_data(self, options_data_df: pd.DataFrame, symbol_str: str) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
        val_logger = self.logger.getChild("ValidateInputOptionsData")
        val_logger.info(f"Starting input data validation for symbol: '{symbol_str}'. Initial shape: {options_data_df.shape if isinstance(options_data_df, pd.DataFrame) else 'N/A'}")

        if not isinstance(options_data_df, pd.DataFrame) or options_data_df.empty:
            err_msg = f"Input options data for '{symbol_str}' is not a valid DataFrame or is empty."
            val_logger.error(err_msg)
            return None, err_msg
            
        df_to_validate = options_data_df.copy() 

        expected_strike_col_name = self.config_manager.get_strike_column_name()
        val_logger.debug(f"[{symbol_str}] Expecting strike column named: '{expected_strike_col_name}' as per configuration.")

        if expected_strike_col_name not in df_to_validate.columns:
            if "strike" in df_to_validate.columns:
                val_logger.info(f"[{symbol_str}] Configured strike column '{expected_strike_col_name}' not found. Found 'strike' column and will rename it to '{expected_strike_col_name}'.")
                df_to_validate.rename(columns={"strike": expected_strike_col_name}, inplace=True)
            else:
                err_msg = f"[{symbol_str}] CRITICAL VALIDATION FAILURE: Expected strike column '{expected_strike_col_name}' (nor fallback 'strike') found. Columns present: {df_to_validate.columns.tolist()}"
                val_logger.error(err_msg)
                return None, err_msg
        
        try:
            if not pd.api.types.is_numeric_dtype(df_to_validate[expected_strike_col_name]):
                val_logger.info(f"[{symbol_str}] Strike column '{expected_strike_col_name}' is not numeric (current type: {df_to_validate[expected_strike_col_name].dtype}). Attempting conversion to numeric.")
                df_to_validate[expected_strike_col_name] = pd.to_numeric(df_to_validate[expected_strike_col_name], errors='coerce')
            
            nan_strikes_count = df_to_validate[expected_strike_col_name].isna().sum()
            if nan_strikes_count > 0:
                val_logger.warning(f"[{symbol_str}] Found {nan_strikes_count} rows with NaN values in strike column '{expected_strike_col_name}'. These rows will be dropped.")
                df_to_validate.dropna(subset=[expected_strike_col_name], inplace=True)
                
                if df_to_validate.empty:
                    err_msg = f"[{symbol_str}] No valid options data remains after removing rows with NaN strike values."
                    val_logger.error(err_msg)
                    return None, err_msg
        except Exception as e_strike_conversion:
            err_msg = f"[{symbol_str}] Error during validation or conversion of strike column '{expected_strike_col_name}': {e_strike_conversion}"
            val_logger.error(err_msg, exc_info=True)
            return None, err_msg
            
        val_logger.info(f"[{symbol_str}] Input data validation successful. Shape after validation: {df_to_validate.shape}")
        return df_to_validate, None
        
    def _prepare_dataframe_for_its(self, validated_options_df: pd.DataFrame, underlying_market_info: Dict[str, Any], symbol_str: str) -> pd.DataFrame:
        prep_df_logger = self.logger.getChild("PrepareDataFrameForITS")
        prep_df_logger.info(f"Starting DataFrame preparation for ITS for symbol: '{symbol_str}'. Input DF shape: {validated_options_df.shape}")
        
        df_prepared_output = validated_options_df.copy()
        strike_column_name_in_df = self.config_manager.get_strike_column_name()

        if "underlying_symbol" not in df_prepared_output.columns:
            df_prepared_output["underlying_symbol"] = symbol_str
            prep_df_logger.debug(f"[{symbol_str}] Added 'underlying_symbol' column with value '{symbol_str}'.")
            
        current_underlying_price = underlying_market_info.get("price") 
        if current_underlying_price is not None:
            try:
                current_price_float = float(current_underlying_price)
                df_prepared_output["current_price"] = current_price_float 
                
                if strike_column_name_in_df in df_prepared_output.columns and \
                   pd.api.types.is_numeric_dtype(df_prepared_output[strike_column_name_in_df]) and \
                   pd.api.types.is_numeric_dtype(df_prepared_output["current_price"]):
                    
                    df_prepared_output["distance_from_current"] = df_prepared_output[strike_column_name_in_df] - df_prepared_output["current_price"]
                    denominator_pct_dist = df_prepared_output["current_price"].replace(0, np.nan)
                    df_prepared_output["pct_distance_from_current"] = (df_prepared_output["distance_from_current"] / denominator_pct_dist) * 100
                    prep_df_logger.debug(f"[{symbol_str}] Calculated 'distance_from_current' and 'pct_distance_from_current'.")
                else:
                    prep_df_logger.warning(f"[{symbol_str}] Could not calculate distance metrics: Strike or current_price column missing, not numeric, or current_price is zero.")
                prep_df_logger.debug(f"[{symbol_str}] Added 'current_price' column with value {current_price_float}.")
            except (ValueError, TypeError) as e_price_float:
                prep_df_logger.error(f"[{symbol_str}] Could not convert underlying price '{current_underlying_price}' to float. 'current_price' column not added/updated correctly. Error: {e_price_float}")
        else:
            prep_df_logger.warning(f"[{symbol_str}] No 'price' found in underlying_market_info. 'current_price' column will not be added to DataFrame.")
            
        fetch_ts_from_underlying = underlying_market_info.get("fetch_timestamp")
        if fetch_ts_from_underlying is not None and "fetch_timestamp" not in df_prepared_output.columns:
            df_prepared_output["fetch_timestamp"] = fetch_ts_from_underlying
            prep_df_logger.debug(f"[{symbol_str}] Added 'fetch_timestamp' column from underlying info: {fetch_ts_from_underlying}")
            
        df_prepared_output["edp_dataframe_preparation_timestamp"] = datetime.now().isoformat()
        
        prep_df_logger.info(f"[{symbol_str}] DataFrame preparation for ITS complete. Final shape: {df_prepared_output.shape}")
        return df_prepared_output
        
    def _apply_its_strategies(self,
                              prepared_options_df_for_its: pd.DataFrame,
                              underlying_info_data_for_its: Dict[str, Any],
                              market_context_data_for_its: Dict[str, Any],
                              historical_ohlc_data_for_its: Optional[pd.DataFrame],
                              symbol_str_for_its: str,
                              expiration_calendar_data_for_its: Optional[List[date]]
                             ) -> Tuple[Dict[str, Any], Optional[str]]:
        apply_its_logger = self.logger.getChild("ApplyITSStrategies")
        apply_its_logger.info(f"Applying Integrated Trading System strategies for symbol: '{symbol_str_for_its}'")

        active_its_instance = self.its_integrator.get_its_instance() 
        if active_its_instance is None:
            critical_err_msg = "CRITICAL: ITS instance could not be obtained (None was returned by ITSIntegrator)."
            apply_its_logger.critical(critical_err_msg)
            return {"error": critical_err_msg, "final_metric_rich_df_obj": pd.DataFrame(), "processed_options_df": []}, critical_err_msg

        apply_its_logger.info(f"[{symbol_str_for_its}] Using ITS instance of type: {type(active_its_instance).__name__}")

        try:
            its_output_bundle = active_its_instance.process_market_data_and_generate_recommendations(
                symbol=symbol_str_for_its,
                raw_options_data=prepared_options_df_for_its, 
                underlying_data=underlying_info_data_for_its,
                market_context=market_context_data_for_its,
                historical_ohlc_data=historical_ohlc_data_for_its,
                expiration_calendar=expiration_calendar_data_for_its 
            )
            
            if not isinstance(its_output_bundle, dict):
                err_msg_type = f"ITS instance for '{symbol_str_for_its}' returned an unexpected result type: {type(its_output_bundle)}. Expected a dictionary."
                apply_its_logger.error(err_msg_type)
                return {"error": err_msg_type, "final_metric_rich_df_obj": pd.DataFrame(), "processed_options_df": []}, err_msg_type
                
            error_reported_by_its = its_output_bundle.get("error")
            if error_reported_by_its:
                if self.its_integrator.is_using_dummy_its() or "dummy ITS" in str(error_reported_by_its).lower() or "fallback" in str(error_reported_by_its).lower():
                    apply_its_logger.warning(f"[{symbol_str_for_its}] ITS (Dummy/Fallback) reported: '{error_reported_by_its}'")
                else: 
                    apply_its_logger.error(f"[{symbol_str_for_its}] Real ITS instance reported an operational error: '{error_reported_by_its}'")
            
            if "final_metric_rich_df_obj" not in its_output_bundle or \
               not isinstance(its_output_bundle["final_metric_rich_df_obj"], pd.DataFrame):
                apply_its_logger.warning(f"[{symbol_str_for_its}] ITS result bundle is missing 'final_metric_rich_df_obj' as a DataFrame. Supplying input DataFrame or empty as fallback.")
                its_output_bundle["final_metric_rich_df_obj"] = prepared_options_df_for_its if isinstance(prepared_options_df_for_its, pd.DataFrame) else pd.DataFrame()
            
            if "processed_options_df" not in its_output_bundle: 
                df_to_conv = its_output_bundle["final_metric_rich_df_obj"]
                its_output_bundle["processed_options_df"] = df_to_conv.to_dict(orient='records') if isinstance(df_to_conv, pd.DataFrame) and not df_to_conv.empty else []
            
            its_output_df_shape = its_output_bundle["final_metric_rich_df_obj"].shape
            apply_its_logger.info(f"[{symbol_str_for_its}] ITS strategies applied. Final DataFrame shape from ITS: {its_output_df_shape}. Error status from ITS: '{error_reported_by_its or 'None'}'")
            return its_output_bundle, error_reported_by_its 

        except Exception as e_apply_its_call:
            critical_err_msg_apply = f"CRITICAL UNHANDLED EXCEPTION during ITS strategy application for '{symbol_str_for_its}': {e_apply_its_call}"
            apply_its_logger.critical(critical_err_msg_apply, exc_info=True)
            error_result_bundle = {
                "symbol": symbol_str_for_its, "error": critical_err_msg_apply,
                "traceback": traceback.format_exc(), "processed_options_df": [],
                "aggregated_strike_data": [], "key_levels": {"error": critical_err_msg_apply},
                "signals": {"error": critical_err_msg_apply}, "recommendations": [],
                "current_mspi_weights_applied": {}, "current_adaptive_historical_context_summary": {},
                "atr_value_used_by_its": 0.0, "final_metric_rich_df_obj": pd.DataFrame()
            }
            return error_result_bundle, critical_err_msg_apply
            
    def _convert_to_json_safe_format(self, data_object: Any) -> Any:
        json_safe_conversion_logger = self.logger.getChild("ConvertToJSONSafeFormat")
        if data_object is None: return None
        elif isinstance(data_object, (str, int, float, bool)): return data_object 
        elif isinstance(data_object, (datetime, date, dt_time)): return data_object.isoformat()
        elif isinstance(data_object, pd.DataFrame):
            json_safe_conversion_logger.debug(f"Converting DataFrame (shape: {data_object.shape}) to list of records for JSON.")
            return data_object.to_dict(orient='records')
        elif isinstance(data_object, pd.Series): return data_object.to_list()
        elif isinstance(data_object, np.ndarray): return data_object.tolist()
        elif isinstance(data_object, (np.integer)): return int(data_object.item())
        elif isinstance(data_object, (np.floating)): return float(data_object.item())
        elif isinstance(data_object, (np.bool_)): return bool(data_object.item())
        elif isinstance(data_object, (list, tuple, Set)): 
            return [self._convert_to_json_safe_format(item) for item in data_object]
        elif isinstance(data_object, dict):
            return {str(k): self._convert_to_json_safe_format(v) for k, v in data_object.items()}
        elif hasattr(data_object, 'to_dict') and callable(getattr(data_object, 'to_dict')):
            try:
                json_safe_conversion_logger.debug(f"Attempting custom 'to_dict()' method for object of type {type(data_object)}.")
                return self._convert_to_json_safe_format(data_object.to_dict())
            except Exception as e_custom_dict:
                json_safe_conversion_logger.warning(f"Custom 'to_dict()' call failed for {type(data_object)}: {e_custom_dict}. Defaulting to string representation.")
                return str(data_object) 
        else:
            try: return str(data_object)
            except Exception as e_str_conversion:
                json_safe_conversion_logger.error(f"Could not convert object of type {type(data_object)} to string for JSON: {e_str_conversion}. Using placeholder string.")
                return JSON_CONVERSION_ERROR_PLACEHOLDER
            
    def _package_analysis_results(self,
                                 symbol_str: str,
                                 fetch_timestamp_from_cv: Optional[str],
                                 its_output_bundle_from_apply: Dict[str, Any], 
                                 original_cv_underlying_data: Dict[str, Any],
                                 original_tradier_market_context: Dict[str, Any], 
                                 overall_processor_error_msg: Optional[str] = None 
                                 ) -> Dict[str, Any]:
        results_packager_logger = self.logger.getChild("PackageAnalysisResults")
        results_packager_logger.info(f"Starting final result packaging for symbol: '{symbol_str}'")

        final_df_object_from_its = its_output_bundle_from_apply.get("final_metric_rich_df_obj")
        if not isinstance(final_df_object_from_its, pd.DataFrame):
            results_packager_logger.warning(f"[{symbol_str}] 'final_metric_rich_df_obj' in ITS bundle is not a DataFrame (type: {type(final_df_object_from_its)}). Using empty DataFrame for this key.")
            final_df_object_from_its = pd.DataFrame()

        options_chain_for_json = its_output_bundle_from_apply.get("processed_options_df")
        if not isinstance(options_chain_for_json, list):
            results_packager_logger.debug(f"[{symbol_str}] 'processed_options_df' from ITS not a list. Converting 'final_metric_rich_df_obj' for JSON options_chain.")
            options_chain_for_json = final_df_object_from_its.to_dict(orient='records') if not final_df_object_from_its.empty else []
        
        final_error_to_report = overall_processor_error_msg or its_output_bundle_from_apply.get("error")

        final_packaged_bundle = {
            "symbol": symbol_str,
            "fetch_timestamp": fetch_timestamp_from_cv or datetime.now().isoformat(), 
            "edp_processing_timestamp": datetime.now().isoformat(), 
            "edp_processor_version": CONFIG_SCHEMA_VERSION_PROCESSOR,
            "error": final_error_to_report,
            "traceback": its_output_bundle_from_apply.get("traceback"), 
            "using_dummy_its": self.its_integrator.is_using_dummy_its(), 
            
            "processed_data": { 
                "options_chain": options_chain_for_json, 
                "aggregated_strike_data": self._convert_to_json_safe_format(its_output_bundle_from_apply.get("aggregated_strike_data", [])),
                "key_levels": self._convert_to_json_safe_format(its_output_bundle_from_apply.get("key_levels", {})),
                "signals": self._convert_to_json_safe_format(its_output_bundle_from_apply.get("signals", {})),
                "recommendations": self._convert_to_json_safe_format(its_output_bundle_from_apply.get("recommendations", [])),
                "metrics_from_its": { 
                    "current_mspi_weights_applied": self._convert_to_json_safe_format(its_output_bundle_from_apply.get("current_mspi_weights_applied", {})),
                    "current_adaptive_historical_context_summary": self._convert_to_json_safe_format(its_output_bundle_from_apply.get("current_adaptive_historical_context_summary", {})),
                    "atr_value_used_by_its": self._convert_to_json_safe_format(its_output_bundle_from_apply.get("atr_value_used_by_its", 0.0))
                }
            },
            "underlying_data_source": self._convert_to_json_safe_format(original_cv_underlying_data), 
            "market_context_source": self._convert_to_json_safe_format(original_tradier_market_context), 
            "final_metric_rich_df_obj": final_df_object_from_its
        }
        
        if not final_error_to_report or "dummy ITS" in str(final_error_to_report).lower(): 
            json_safe_content_for_file = {
                k: v for k, v in final_packaged_bundle.items() if k != "final_metric_rich_df_obj"
            }
            if isinstance(json_safe_content_for_file.get("processed_data", {}).get("key_levels"), dict):
                kl_dict = json_safe_content_for_file["processed_data"]["key_levels"]
                if isinstance(kl_dict.get("support_df"), pd.DataFrame):
                    kl_dict["support_df"] = kl_dict["support_df"].to_dict(orient='records')
                if isinstance(kl_dict.get("resistance_df"), pd.DataFrame):
                    kl_dict["resistance_df"] = kl_dict["resistance_df"].to_dict(orient='records')

            self._save_analysis_results_to_file(symbol_str, json_safe_content_for_file)
            
        results_packager_logger.info(f"[{symbol_str}] Final result packaging complete. Error status: '{final_error_to_report or 'None'}'")
        return final_packaged_bundle 
        
    def _save_analysis_results_to_file(self, symbol_str: str, json_safe_results_bundle: Dict[str, Any]) -> None:
        save_file_logger = self.logger.getChild("SaveAnalysisToFile")
        if not self.output_directory_main:
            save_file_logger.error(f"Cannot save results for '{symbol_str}': Output directory is not configured or accessible by DataProcessor.")
            return
        try:
            timestamp_for_file = datetime.now().strftime("%Y%m%d_%H%M%S_%f") 
            output_filename = f"edp_output_{symbol_str}_{timestamp_for_file}.json"
            full_output_filepath = os.path.join(self.output_directory_main, output_filename)
            
            with open(full_output_filepath, 'w', encoding='utf-8') as f_json_out:
                json.dump(json_safe_results_bundle, f_json_out, indent=2, default=str) 
                
            save_file_logger.info(f"Successfully saved analysis results for '{symbol_str}' to file: {full_output_filepath}")
        except Exception as e_save_results_file:
            save_file_logger.error(f"Error saving analysis results for '{symbol_str}' to file ('{full_output_filepath}'): {e_save_results_file}", exc_info=True)
            
    def process_market_data_bundle(self,
                                  market_data_input_bundle: Dict[str, Dict[str, Any]], 
                                  tradier_context_data_bundle: Optional[Dict[str, Dict[str, Any]]] = None,
                                  expiration_calendars_bundle_data: Optional[Dict[str, List[date]]] = None
                                 ) -> Dict[str, Dict[str, Any]]: 
        process_bundle_logger = self.logger.getChild("ProcessMarketDataBundle")
        num_symbols_to_process = len(market_data_input_bundle)
        process_bundle_logger.info(f"Starting to process market data bundle for {num_symbols_to_process} symbol(s).")
        
        effective_thread_pool_size = self.config_manager.get_thread_pool_size()
        process_bundle_logger.info(f"Using thread pool size: {effective_thread_pool_size} for bundle processing.")
        
        all_symbols_results_map: Dict[str, Dict[str, Any]] = {}
        
        safe_tradier_context = tradier_context_data_bundle or {}
        safe_expiration_calendars = expiration_calendars_bundle_data or {}

        if num_symbols_to_process > 1 and effective_thread_pool_size > 1:
            process_bundle_logger.info(f"Processing {num_symbols_to_process} symbols in parallel using {effective_thread_pool_size} workers.")
            with ThreadPoolExecutor(max_workers=effective_thread_pool_size) as thread_executor:
                future_to_symbol_mapping = {
                    thread_executor.submit(
                        self._process_single_symbol_data, 
                        symbol_key_item,                   
                        symbol_cv_data_item,             
                        safe_tradier_context.get(symbol_key_item, {}), 
                        safe_expiration_calendars.get(symbol_key_item) 
                    ): symbol_key_item
                    for symbol_key_item, symbol_cv_data_item in market_data_input_bundle.items()
                }
                
                for future_task_item in as_completed(future_to_symbol_mapping):
                    processed_symbol_key = future_to_symbol_mapping[future_task_item]
                    try:
                        all_symbols_results_map[processed_symbol_key] = future_task_item.result()
                        process_bundle_logger.debug(f"Successfully retrieved result for parallel processed symbol: '{processed_symbol_key}'")
                    except Exception as e_future_task_exc:
                        error_message_parallel = f"CRITICAL error processing symbol '{processed_symbol_key}' in parallel worker: {e_future_task_exc}"
                        process_bundle_logger.critical(error_message_parallel, exc_info=True)
                        all_symbols_results_map[processed_symbol_key] = self._create_error_bundle_for_symbol(processed_symbol_key, error_message_parallel, traceback.format_exc())
        else:
            process_bundle_logger.info("Processing symbols sequentially (single symbol provided or thread pool size <= 1).")
            for symbol_key_item, symbol_cv_data_item in market_data_input_bundle.items():
                try:
                    all_symbols_results_map[symbol_key_item] = self._process_single_symbol_data(
                        symbol_key_item,
                        symbol_cv_data_item,
                        safe_tradier_context.get(symbol_key_item, {}),
                        safe_expiration_calendars.get(symbol_key_item)
                    )
                except Exception as e_sequential_exc:
                    error_message_sequential = f"CRITICAL error processing symbol '{symbol_key_item}' sequentially: {e_sequential_exc}"
                    process_bundle_logger.critical(error_message_sequential, exc_info=True)
                    all_symbols_results_map[symbol_key_item] = self._create_error_bundle_for_symbol(symbol_key_item, error_message_sequential, traceback.format_exc())
                    
        process_bundle_logger.info(f"Completed processing market data bundle for all {num_symbols_to_process} provided symbol(s).")
        return all_symbols_results_map
        
    def _process_single_symbol_data(self,
                                   symbol_str_single_proc: str,
                                   cv_data_for_symbol: Dict[str, Any],
                                   tradier_context_for_symbol: Dict[str, Any],
                                   expiration_calendar_for_symbol: Optional[List[date]]
                                  ) -> Dict[str, Any]:
        single_symbol_pipeline_logger = self.logger.getChild(f"SingleSymbolPipeline.{symbol_str_single_proc}")
        single_symbol_pipeline_logger.info(f"Starting full data processing pipeline for symbol: '{symbol_str_single_proc}'")

        options_chain_data_raw = cv_data_for_symbol.get("options_chain") 
        underlying_info_from_cv = cv_data_for_symbol.get("underlying", {}) 
        fetcher_error_msg = cv_data_for_symbol.get("error")

        if fetcher_error_msg: 
            error_message = f"Fetcher (ConvexValue) reported an error for '{symbol_str_single_proc}': {fetcher_error_msg}"
            single_symbol_pipeline_logger.error(error_message)
            return self._create_error_bundle_for_symbol(symbol_str_single_proc, error_message)
            
        options_df_input_to_validate: pd.DataFrame
        if isinstance(options_chain_data_raw, list):
            options_df_input_to_validate = pd.DataFrame(options_chain_data_raw)
        elif isinstance(options_chain_data_raw, pd.DataFrame):
            options_df_input_to_validate = options_chain_data_raw
        else:
            options_df_input_to_validate = pd.DataFrame() 
            single_symbol_pipeline_logger.warning(f"[{symbol_str_single_proc}] 'options_chain' data received was not a list or DataFrame (type: {type(options_chain_data_raw)}). Proceeding with empty DataFrame.")

        validated_df, validation_error = self._validate_input_options_data(options_df_input_to_validate, symbol_str_single_proc)
        if validation_error or validated_df is None:
            error_message = f"Input data validation FAILED for '{symbol_str_single_proc}': {validation_error or 'Unknown validation error, DataFrame is None.'}"
            single_symbol_pipeline_logger.error(error_message)
            return self._create_error_bundle_for_symbol(symbol_str_single_proc, error_message)
            
        prepared_df_for_its_call = self._prepare_dataframe_for_its(validated_df, underlying_info_from_cv, symbol_str_single_proc)
        
        effective_market_context_for_its: Dict[str, Any] = {
            "current_time": datetime.now().time(), 
            "current_iv": underlying_info_from_cv.get("volatility"), 
        }
        tradier_iv_quote_data = tradier_context_for_symbol.get("iv_and_quote_data")
        if isinstance(tradier_iv_quote_data, dict):
            effective_market_context_for_its.update(tradier_iv_quote_data)
        
        historical_ohlc_for_its_call = tradier_context_for_symbol.get("historical_ohlcv_df")
        if historical_ohlc_for_its_call is not None and not isinstance(historical_ohlc_for_its_call, pd.DataFrame):
            single_symbol_pipeline_logger.warning(f"[{symbol_str_single_proc}] 'historical_ohlcv_df' from Tradier context is not a DataFrame (type: {type(historical_ohlc_for_its_call)}). Will pass None to ITS.")
            historical_ohlc_for_its_call = None

        its_bundle_from_analysis, its_error_from_apply = self._apply_its_strategies(
            prepared_options_df_for_its=prepared_df_for_its_call,
            underlying_info_data_for_its=underlying_info_from_cv,
            market_context_data_for_its=effective_market_context_for_its,
            historical_ohlc_data_for_its=historical_ohlc_for_its_call,
            symbol_str_for_its=symbol_str_single_proc,
            expiration_calendar_data_for_its=expiration_calendar_for_symbol 
        )
        
        final_results_bundle_for_symbol = self._package_analysis_results(
            symbol_str=symbol_str_single_proc,
            fetch_timestamp_from_cv=underlying_info_from_cv.get("fetch_timestamp"), # Corrected key
            its_output_bundle_from_apply=its_bundle_from_analysis,
            original_cv_underlying_data=underlying_info_from_cv,
            original_tradier_market_context=tradier_context_for_symbol,
            overall_processor_error_msg=its_error_from_apply # Corrected key
        )
        single_symbol_pipeline_logger.info(f"Full processing pipeline completed for symbol: '{symbol_str_single_proc}'.")
        return final_results_bundle_for_symbol
        
    def _create_error_bundle_for_symbol(self, symbol_str: str, error_msg_str: str, trace_info: Optional[str] = None) -> Dict[str, Any]:
        create_err_logger = self.logger.getChild("CreateErrorBundle")
        create_err_logger.error(f"Creating error bundle for symbol '{symbol_str}'. Error: {error_msg_str}")
        return {
            "symbol": symbol_str,
            "fetch_timestamp": datetime.now().isoformat(), 
            "edp_processing_timestamp": datetime.now().isoformat(),
            "edp_processor_version": CONFIG_SCHEMA_VERSION_PROCESSOR,
            "error": error_msg_str,
            "traceback": trace_info, 
            "using_dummy_its": self.its_integrator.is_using_dummy_its(), 
            "processed_data": { 
                "options_chain": [], "aggregated_strike_data": [],
                "key_levels": {"error": "Processing failed due to error."},
                "signals": {"error": "Processing failed due to error."},
                "recommendations": [], "metrics_from_its": {"error": "Processing failed"} # Corrected key
            },
            "underlying_data_source": {}, "market_context_source": {}, # Corrected keys
            "final_metric_rich_df_obj": pd.DataFrame() 
        }

# ===== Main Orchestrating Class (EnhancedDataProcessor) =====
class EnhancedDataProcessor:
    def __init__(self,
                 config_path: Optional[str] = DEFAULT_CONFIG_FILE_PATH, # Optional, can be None if retriever is used
                 output_data_directory: Optional[str] = None, # Explicit base output dir for this EDP instance
                 config_retriever_func: Optional[Callable[[List[str], Any], Any]] = None):
        self.main_logger = logger.getChild("EnhancedDataProcessorInstance") 
        self.main_logger.info(f"Initializing EnhancedDataProcessor System (Version: {CONFIG_SCHEMA_VERSION_PROCESSOR})...")
        self.main_logger.info(f"  Config Path (if not using getter): '{config_path}'")
        self.main_logger.info(f"  Output Directory Override for this instance: '{output_data_directory}'")
        self.main_logger.info(f"  Custom Config Retriever Provided: {config_retriever_func is not None}")
        
        self.config_manager_instance = ConfigurationManager(config_path if config_path else DEFAULT_CONFIG_FILE_PATH, config_retriever_func)
        
        # If an explicit output_data_directory is provided for this EDP instance,
        # update the configuration that DataProcessor will use.
        if output_data_directory:
            self.main_logger.info(f"EDP Init: Overriding data_directory_base with explicit output_data_directory for this instance: '{output_data_directory}'")
            if not self.config_manager_instance.config.get("system_settings"):
                self.config_manager_instance.config["system_settings"] = {}
            # This sets the BASE directory. The DataProcessor will append its configured subdirectory.
            self.config_manager_instance.config["system_settings"]["data_directory_base"] = os.path.abspath(output_data_directory)
            # Ensure a subdirectory is defined if not already
            if "processed_data_subdirectory" not in self.config_manager_instance.config["system_settings"]:
                 self.config_manager_instance.config["system_settings"]["processed_data_subdirectory"] = "edp_specific_outputs" 
            self.main_logger.info(f"  ConfigManager's data_directory_base is now: {self.config_manager_instance.config['system_settings']['data_directory_base']}")
            self.main_logger.info(f"  ConfigManager's processed_data_subdirectory is: {self.config_manager_instance.config['system_settings']['processed_data_subdirectory']}")


        self.its_integrator_instance = ITSIntegrator(self.config_manager_instance)
        self.data_processing_pipeline = DataProcessor(self.config_manager_instance, self.its_integrator_instance)
        
        if self.config_manager_instance.config.get("_edp_config_validation_errors"):
            self.main_logger.warning(f"EDP Configuration manager reported validation issues: {self.config_manager_instance.config['_edp_config_validation_errors']}")
        else:
            self.main_logger.info("EDP Configuration manager validation (for EDP essentials) passed.")
            
        self.main_logger.info("EnhancedDataProcessor System initialization complete.")
        
    def process_market_data_bundle(self,
                                  market_data_payload: Dict[str, Dict[str, Any]],
                                  tradier_context_payload: Optional[Dict[str, Dict[str, Any]]] = None,
                                  expiration_calendars_payload: Optional[Dict[str, List[date]]] = None
                                 ) -> Dict[str, Dict[str, Any]]:
        self.main_logger.info(f"EDP Main: Received request to process market data bundle for {len(market_data_payload)} symbol(s).")
        if not market_data_payload:
            self.main_logger.warning("EDP Main: process_market_data_bundle called with empty market_data_payload. Returning empty results.")
            return {}
        return self.data_processing_pipeline.process_market_data_bundle(
            market_data_input_bundle=market_data_payload,
            tradier_context_data_bundle=tradier_context_payload, # Corrected key
            expiration_calendars_bundle_data=expiration_calendars_payload
        )
        
    def get_current_config_value(self, path_keys_list: List[str], default_val: Any = None) -> Any:
        return self.config_manager_instance.get_value(path_keys_list, default_val)
        
    def is_its_dummy_active(self) -> bool:
        return self.its_integrator_instance.is_using_dummy_its()
        
    def get_active_its_instance(self) -> Any:
        return self.its_integrator_instance.get_its_instance()
        
    def get_processor_output_directory(self) -> str:
        return self.data_processing_pipeline.output_directory_main


# ===== Standalone Test Block for EnhancedDataProcessor =====
# (Remains the same as provided, no changes needed here for the fix)
def run_edp_standalone_test():
    test_logger_edp = logging.getLogger("EDP_Standalone_Test_CanonRunFix") 
    if not test_logger_edp.handlers:
        test_handler = logging.StreamHandler(sys.stdout)
        test_formatter = logging.Formatter("[%(levelname)s] (%(name)s:%(lineno)d) %(asctime)s - %(message)s")
        test_handler.setFormatter(test_formatter)
        test_logger_edp.addHandler(test_handler)
        test_logger_edp.propagate = False 
    test_logger_edp.setLevel(logging.DEBUG) 
    
    logging.getLogger("EnhancedDataProcessor").setLevel(logging.DEBUG)
    for handler in logging.getLogger("EnhancedDataProcessor").handlers: 
        handler.setLevel(logging.DEBUG)

    test_logger_edp.info("--- Starting EnhancedDataProcessor Standalone Test (Canon Directive Version with Fix) ---")
    
    try:
        script_dir_for_test = os.path.dirname(os.path.abspath(__file__))
    except NameError: 
        script_dir_for_test = os.getcwd()
        test_logger_edp.info(f"__file__ not defined, using CWD '{script_dir_for_test}' for script_dir_for_test.")

    project_root_for_test_config = os.path.dirname(script_dir_for_test)
    config_file_to_use_for_test = os.path.join(project_root_for_test_config, DEFAULT_CONFIG_FILE_PATH)

    if not os.path.exists(config_file_to_use_for_test):
        config_file_to_use_for_test = os.path.join(script_dir_for_test, DEFAULT_CONFIG_FILE_PATH)
        if not os.path.exists(config_file_to_use_for_test):
            test_logger_edp.warning(
                f"Standalone Test: Config file '{DEFAULT_CONFIG_FILE_PATH}' not found in "
                f"project root ('{project_root_for_test_config}') or script directory ('{script_dir_for_test}'). "
                f"EDP will use internal defaults."
            )
            config_file_to_use_for_test = "FORCE_EDP_INTERNAL_DEFAULTS_NONEXISTENT.json" # Force default
        else:
            test_logger_edp.info(f"Standalone Test: Found config in script directory: '{config_file_to_use_for_test}'")
    else:
        test_logger_edp.info(f"Standalone Test: Found config in project root: '{config_file_to_use_for_test}'")

    test_logger_edp.info(f"Standalone Test: Final configuration path to be used by EDP: '{config_file_to_use_for_test}'")
    
    # For standalone test, define an explicit output directory relative to this test script
    test_edp_output_dir = os.path.join(script_dir_for_test, "test_edp_outputs_canon_fix")
    test_logger_edp.info(f"Standalone Test: Explicit output directory for this EDP test run: '{test_edp_output_dir}'")


    edp_test_instance: Optional[EnhancedDataProcessor] = None
    try:
        edp_test_instance = EnhancedDataProcessor(
            config_path=config_file_to_use_for_test,
            output_data_directory=test_edp_output_dir # Provide the explicit output directory
        )
        test_logger_edp.info("EnhancedDataProcessor instance created successfully for standalone test.")
        test_logger_edp.info(f"  EDP Configured Output Directory: {edp_test_instance.get_processor_output_directory()}")
        test_logger_edp.info(f"  EDP ITS Status: {'Dummy ITS Active' if edp_test_instance.is_its_dummy_active() else 'Real ITS Expected/Loaded'}")
        
        active_its_instance_in_edp = edp_test_instance.get_active_its_instance()
        test_logger_edp.info(f"  EDP Active ITS Instance Type: {type(active_its_instance_in_edp).__name__}")

        test_logger_edp.info("Preparing comprehensive sample data for test processing...")
        strike_col_name_for_test_data = edp_test_instance.get_current_config_value(
            ["visualization_settings", "mspi_visualizer", "column_names", "strike"], "strike_price"
        )
        test_logger_edp.info(f"  Using configured strike column name for test data generation: '{strike_col_name_for_test_data}'")
        
        today_date = date.today()
        # Dummy market data payload (structure matches what CV fetcher would provide)
        dummy_market_data_payload = {
            "TESTPROC": {
                "options_chain": pd.DataFrame([
                    {strike_col_name_for_test_data: 150, "opt_kind": "call", "price": 152.50, "underlying_symbol": "TESTPROC", "expiration_date": (today_date + timedelta(days=10)).isoformat(), "delta": 0.60, "gamma": 0.025, "vega": 0.12, "theta": -0.04, "volatility": 0.22, "oi": 200, "volm": 100},
                    {strike_col_name_for_test_data: 155, "opt_kind": "call", "price": 152.50, "underlying_symbol": "TESTPROC", "expiration_date": (today_date + timedelta(days=10)).isoformat(), "delta": 0.35, "gamma": 0.035, "vega": 0.15, "theta": -0.07, "volatility": 0.24, "oi": 180, "volm": 90},
                ]),
                "underlying": {"symbol": "TESTPROC", "price": 152.50, "volatility": 0.21, "fetch_timestamp": datetime.now().isoformat()},
                "error": None
            }
        }
        sample_tradier_context_payload_test = {
            "TESTPROC": {
                "iv_and_quote_data": {"current_iv_tradier_approx": 0.215, "avg_iv_5day": 0.21, "iv_percentile_30d": 0.55},
                "historical_ohlcv_df": pd.DataFrame({'date': pd.to_datetime([today_date - timedelta(days=i) for i in range(5,0,-1)]).date, 'open': [150]*5, 'high': [152]*5, 'low': [149]*5, 'close': [151]*5, 'volume': [1e6]*5}),
            }
        }
        sample_expiration_calendars_payload_test = {"TESTPROC": [today_date + timedelta(days=d) for d in [0, 7, 10]]}

        test_logger_edp.info("Calling EnhancedDataProcessor.process_market_data_bundle with sample data...")
        edp_processing_results = edp_test_instance.process_market_data_bundle(
            market_data_payload=dummy_market_data_payload,
            tradier_context_payload=sample_tradier_context_payload_test,
            expiration_calendars_payload=sample_expiration_calendars_payload_test
        )
        
        test_logger_edp.info("--- EnhancedDataProcessor Standalone Test Processing Results ---")
        if not edp_processing_results:
            test_logger_edp.error("Processing returned no results (empty dictionary).")
        
        for symbol_key_result, result_data_bundle in edp_processing_results.items():
            test_logger_edp.info(f"  --- Results for Symbol: {symbol_key_result} ---")
            test_logger_edp.info(f"    EDP Reported Error: {result_data_bundle.get('error')}")
            test_logger_edp.info(f"    EDP Reports Using Dummy ITS: {result_data_bundle.get('using_dummy_its')}")
            final_df_object = result_data_bundle.get("final_metric_rich_df_obj")
            if isinstance(final_df_object, pd.DataFrame):
                test_logger_edp.info(f"    'final_metric_rich_df_obj' DataFrame Shape: {final_df_object.shape}")
                if not final_df_object.empty:
                    test_logger_edp.info(f"      Columns: {final_df_object.columns.tolist()}")
            else:
                test_logger_edp.warning(f"    'final_metric_rich_df_obj' is not a DataFrame in results. Type: {type(final_df_object)}")
        test_logger_edp.info("--- EnhancedDataProcessor Standalone Test Completed ---")
    except Exception as e_standalone_main:
        test_logger_edp.critical(f"CRITICAL UNHANDLED EXCEPTION in EnhancedDataProcessor Standalone Test: {e_standalone_main}", exc_info=True)
        
if __name__ == "__main__":
    run_edp_standalone_test()

