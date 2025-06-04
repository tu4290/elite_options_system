# core_analytics/integrated_strategies_v2.py
# Version: EOTS_ITS_v2.3.1_Canon_IDS_Sync_Logging
"""
The Integrated Trading System (ITS) for the Elite Options Trading System.
This version is tailored for "Enhanced v2.3" functionality, focusing on
robust calculation of the core MSPI suite and v2.3-level signals/levels,
fully integrated with ids.py and enhanced_data_processor_v2.py.
Enhanced logging and strict ids.py adherence applied.
"""

# --- Standard & Third-Party Imports ---
import logging
import json
import os
import sys
import copy
from datetime import datetime, date, time as dt_time, timedelta
from typing import Optional, List, Dict, Any, Union, Tuple, Callable, Deque, Type
from collections import deque
import traceback # For detailed error logging
import pandas as pd
import numpy as np
import inspect # For potential dynamic checks, if ever needed
import time # For timing measurements


# --- Module-Specific Logger ---
# Initialize logger for this module. Configuration (level, handlers) can be
# further set by the main application importing this module.
logger_its_module = logging.getLogger(__name__) # Use __name__ for module-level logger
if not logger_its_module.hasHandlers() and not logging.getLogger().hasHandlers(): # Basic setup if not configured by main app
    logging.basicConfig(level=logging.INFO, 
                        format="[%(levelname)s] (%(name)s:%(funcName)s:%(lineno)d) %(asctime)s - %(message)s",
                        handlers=[logging.StreamHandler(sys.stdout)])
logger_its_module.info(f"core_analytics.integrated_strategies_v2.py (Version: EOTS_ITS_v2.3.1_Canon_IDS_Sync_Logging): Logger initialized.")

# --- Project-Specific Imports from within core_analytics package ---
_CORE_IMPORTS_SUCCESSFUL_ITS_V231 = False
_FAILED_MODULE_NAME_ITS_V231: str = "UnknownModule_ITS_v231_Import"
try:
    from utils import ids # Centralized IDs - CRITICAL IMPORT
    from .config_utils import DEFAULT_CONFIG as DEFAULT_ITS_CONFIG_V231, load_and_validate_config as load_and_validate_config_its
    from .system_utilities import (
        normalize_series, ensure_columns, map_score_to_stars, get_atr,
        calculate_proximity_factor, calculate_dynamic_threshold_wrapper,
        aggregate_for_levels, get_performance_metrics_stub 
    )
    # Import all v2.3 relevant metric calculation modules
    from . import mspi_orchestration_module 
    from . import level_identification_module
    from . import signal_generation_module 
    from . import fallback_recommendation_module 
    from . import recommendation_state_manager
    # These are more v2.5, but their stubs/basic versions might be called if config allows.
    # Importing them allows type hinting and checking hasattr for specific functions.
    from . import adaptive_dag_module
    from . import dynamic_tdpi_module
    from . import enhanced_sdag_module
    from . import vri_2_0_module
    from . import adaptive_trade_framework_module # For ATIF context, even if simplified in v2.3
    # from . import system_utilities # Already imported specific functions
    # from . import config_utils # Already imported specific functions/constants

    _CORE_IMPORTS_SUCCESSFUL_ITS_V231 = True
    logger_its_module.info("ITS (v2.3.1): Core analytics sibling modules and utils.ids imported successfully.")

except ImportError as e_rel_import_its_v231:
    _FAILED_MODULE_NAME_ITS_V231 = e_rel_import_its_v231.name if hasattr(e_rel_import_its_v231, 'name') else "UnknownImport_ITS_v231"
    # This print is for immediate visibility if logging isn't fully set up when this module is first imported.
    print(f"CRITICAL IMPORT ERROR in integrated_strategies_v2.py (v2.3.1): Failed to import core_analytics sibling modules or utils.ids: {e_rel_import_its_v231} (Failed Module: {_FAILED_MODULE_NAME_ITS_V231}). "
          "Dummy modules will be used. ITS functionality will be severely impaired.")
    logger_its_module.critical(
        f"ITS CRITICAL (v2.3.1): Failed to import core_analytics sibling modules: {e_rel_import_its_v231} (Failed Module: {_FAILED_MODULE_NAME_ITS_V231}). "
        "Dummy modules will be used. ITS functionality will be severely impaired.",
        exc_info=True
    )
    # Define DummyModule at the module level for fallback if critical imports fail
    class DummyModule_ITS: # Suffixed to avoid clash
        def __init__(self, module_that_failed_to_import_name="UnknownModule_ITS_Internal_v231"):
            self._module_that_failed_to_import_name = module_that_failed_to_import_name
            self.dummy_logger_its = logger_its_module.getChild(f"DummyModule_ITS.{self._module_that_failed_to_import_name}")
            self.dummy_logger_its.error(f"Instantiated DummyModule_ITS for '{self._module_that_failed_to_import_name}' due to import failures.")

        def __getattr__(self, name: str) -> Callable[..., Any]:
            def dummy_func_its(*args: Any, **kwargs: Any) -> Any:
                log_msg = (f"Dummy function '{name}' called on DummyModule_ITS (original module "
                           f"'{self._module_that_failed_to_import_name}' or its dependencies failed to import within ITS v2.3.1).")
                self.dummy_logger_its.error(log_msg)
                # Provide some default return types to prevent downstream crashes where possible
                if name == "calculate_mspi_main":
                    df_arg = next((arg for arg in args if isinstance(arg, pd.DataFrame)), pd.DataFrame())
                    # Try to use ids.py if it loaded, otherwise string literal
                    mspi_col_dummy = ids.COL_MSPI_SCORE if 'ids' in sys.modules and hasattr(sys.modules['ids'], 'COL_MSPI_SCORE') else "mspi"
                    if mspi_col_dummy not in df_arg.columns and isinstance(df_arg, pd.DataFrame): df_arg[mspi_col_dummy] = 0.0
                    df_arg["ERROR_DUMMY_ITS_MSPI_CALC_v231"] = log_msg
                    return df_arg
                if name == "identify_enhanced_key_levels_main": return {"error": log_msg, "all_levels_sorted_by_strength": []}
                if name == "generate_trading_signals": return {"error": log_msg, "signals_generated_count": 0}
                if name == "generate_adaptive_trade_ideas_main" or name == "get_strategy_recommendations_fallback": return [], 0 # (recs, next_id)
                if name == "is_immediate_exit_warranted": return None # Exit reason or None
                if name == "adjust_active_recommendation_parameters": return None # Modifies in-place
                if name == "update_symbol_adaptive_historical_context": 
                    # Try to return the context dict if passed, else empty
                    return next((arg for arg in args if isinstance(arg, dict) and "past_flow_delta" in arg), {}) 
                return {"error": log_msg, "dummy_fallback_its_internal_v231": True} # Generic fallback
            return dummy_func_its

    # Fallback assignments if specific modules failed
    # Check if 'ids' itself failed, as it's critical
    if 'utils.ids' not in sys.modules: # More robust check
        class ids: # Minimal fallback for 'ids' to allow parsing
            COL_STRIKE = "strike_price"; COL_MSPI_SCORE = "mspi"; CFG_SYSTEM_LOG_LEVEL = ["system_settings", "log_level"]
            CFG_VIZ_COL_NAMES = ["visualization_settings", "mspi_visualizer", "column_names"]
            COL_UNDERLYING_SYMBOL_CHAIN = "underlying_symbol"; COL_OPT_KIND = "opt_kind"; COL_EXPIRATION_DATE = "expiration_date"
            COL_DELTA_CONTRACT = "delta"; CFG_VIZ_COL_OPT_KIND = CFG_VIZ_COL_NAMES + ["option_kind"]
            CFG_VIZ_COL_EXPIRY_DATE = CFG_VIZ_COL_NAMES + ["expiration_date"]
            CFG_METRICS_CALC_STRIKE_COL_INTERNAL = ["metrics_calculator_v2_5_settings", "strike_column_name_internal"]
            CFG_VIZ_COL_MSPI = CFG_VIZ_COL_NAMES + ["mspi"]
            CFG_METRICS_CALC = ["metrics_calculator_v2_5_settings"]
            CV_UND_PARAM_PRICE = "price"; COL_VOLATILITY_OPTION_CONTRACT = "volatility"; COL_PRICE_OPTION_CONTRACT = "price"
            COL_CHARMXOI_CONTRACT = "charmxoi"; COL_TXOI_CONTRACT = "txoi"; COL_VANNAXOI_CONTRACT = "vannaxoi"
            COL_VXOI_CONTRACT = "vxoi"; COL_VOMMAXOI_CONTRACT = "vommaxoi"; COL_GXOI_CONTRACT = "gxoi"; COL_DXOI_CONTRACT = "dxoi"
            COL_VOLUME_OPTION_CONTRACT = "volm"; CV_CHAIN_PARAM_DELTAS_BUY_CONTRACT = "deltas_buy"
            CV_CHAIN_PARAM_DELTAS_SELL_CONTRACT = "deltas_sell"; CV_CHAIN_PARAM_DXVOLM = "dxvolm"
            CV_CHAIN_PARAM_GAMMAS_BUY_CONTRACT = "gammas_buy"; CV_CHAIN_PARAM_GAMMAS_SELL_CONTRACT = "gammas_sell"
            CV_CHAIN_PARAM_GXVOLM = "gxvolm"; CV_CHAIN_PARAM_THETAS_BUY_CONTRACT = "thetas_buy"
            CV_CHAIN_PARAM_THETAS_SELL_CONTRACT = "thetas_sell"; CV_CHAIN_PARAM_TXVOLM = "txvolm"
            CV_CHAIN_PARAM_CHARMXVOLM = "charmxvolm"; CV_CHAIN_PARAM_VEGAS_BUY_CONTRACT = "vegas_buy"
            CV_CHAIN_PARAM_VEGAS_SELL_CONTRACT = "vegas_sell"; CV_CHAIN_PARAM_VXVOLM = "vxvolm"
            CV_CHAIN_PARAM_VANNAXVOLM = "vannaxvolm"; CV_CHAIN_PARAM_VOMMAXVOLM = "vommaxvolm"
            CFG_SYSTEM_DF_HISTORY_MAXLEN_ITS = ["system_settings", "df_history_maxlen_its"]
            CFG_DAG_METHODOLOGIES_ENABLED_ITS = ["strategy_settings", "dag_methodologies", "enabled"]
            # Add more critical fallbacks if needed for parsing the rest of the file
        logger_its_module.critical("ITS CRITICAL (v2.3.1): 'utils.ids' module FAILED to import. Using minimal internal 'ids' fallback. System behavior will be unpredictable.")
        IDS_IMPORTED_SUCCESSFULLY_EDP = False # Ensure this flag is set if ids itself fails

    if 'core_analytics.config_utils' not in sys.modules:
        DEFAULT_ITS_CONFIG_V231: Dict[str, Any] = {} 
        def load_and_validate_config_its(config_path: Optional[str]=None, default_config_data: Optional[Dict[str,Any]]=None, log_instance: Optional[logging.Logger]=None) -> Dict[str,Any]: 
            if log_instance: log_instance.error(f"Using DUMMY load_and_validate_config_its (failed module: {_FAILED_MODULE_NAME_ITS_V231}).")
            return default_config_data or {}
        logger_its_module.critical("ITS CRITICAL (v2.3.1): 'core_analytics.config_utils' FAILED to import. Using DUMMY config loader.")
    
    # Assign dummy modules if their real counterparts (or dependencies) failed
    module_map_its = {
        "mspi_orchestration_module": mspi_orchestration_module, "level_identification_module": level_identification_module,
        "signal_generation_module": signal_generation_module, "fallback_recommendation_module": fallback_recommendation_module,
        "recommendation_state_manager": recommendation_state_manager, "adaptive_dag_module": adaptive_dag_module,
        "dynamic_tdpi_module": dynamic_tdpi_module, "enhanced_sdag_module": enhanced_sdag_module,
        "vri_2_0_module": vri_2_0_module, "adaptive_trade_framework_module": adaptive_trade_framework_module
    }
    for mod_name_str_its, mod_obj_its in module_map_its.items():
        if not inspect.ismodule(mod_obj_its) or mod_obj_its.__name__.startswith("core_analytics.DummyModule_ITS"): # Check if it's already a dummy
            globals()[mod_name_str_its] = DummyModule_ITS(f"{mod_name_str_its}_dep_of_{_FAILED_MODULE_NAME_ITS_V231}") # type: ignore
            logger_its_module.warning(f"ITS (v2.3.1): Using DummyModule_ITS for '{mod_name_str_its}' due to earlier import failures.")

    if 'core_analytics.system_utilities' not in sys.modules:
        def normalize_series(*args: Any, **kwargs: Any) -> pd.Series: logger_its_module.error("Using DUMMY normalize_series."); return pd.Series(dtype=float) 
        def ensure_columns(*args: Any, **kwargs: Any) -> Tuple[pd.DataFrame, bool]: logger_its_module.error("Using DUMMY ensure_columns."); return (pd.DataFrame(), False) 
        def map_score_to_stars(*args: Any, **kwargs: Any) -> int: logger_its_module.error("Using DUMMY map_score_to_stars."); return 0 
        def get_atr(*args: Any, **kwargs: Any) -> float: logger_its_module.error("Using DUMMY get_atr."); return 0.0 
        def calculate_proximity_factor(*args: Any, **kwargs: Any) -> Union[float, pd.Series]: logger_its_module.error("Using DUMMY calculate_proximity_factor."); return 0.0 
        def calculate_dynamic_threshold_wrapper(*args: Any, **kwargs: Any) -> Optional[Union[float, List[float]]]: logger_its_module.error("Using DUMMY calculate_dynamic_threshold_wrapper."); return None 
        def aggregate_for_levels(*args: Any, **kwargs: Any) -> pd.DataFrame: logger_its_module.error("Using DUMMY aggregate_for_levels."); return pd.DataFrame() 
        def get_performance_metrics_stub(*args: Any, **kwargs: Any) -> Dict[str, float]: logger_its_module.error("Using DUMMY get_performance_metrics_stub."); return {} 
        logger_its_module.critical("ITS CRITICAL (v2.3.1): 'core_analytics.system_utilities' FAILED to import. Using DUMMY system utilities.")


class IntegratedTradingSystem:
    """
    The Integrated Trading System (ITS) for the Elite Options Trading System.
    Orchestrates v2.3 analytical modules to process market data, identify opportunities,
    and generate trading insights and recommendations.
    Version: EOTS_ITS_v2.3.1_Canon_IDS_Sync_Logging
    """

    def __init__(self, config_path: Optional[str] = None, log_level: Optional[str] = None):
        # Ensure instance logger uses a unique name to avoid conflicts if multiple ITS instances were ever created (unlikely for now)
        self.instance_logger = logger_its_module.getChild(f"{self.__class__.__name__}.Instance_{datetime.now().strftime('%H%M%S%f')}")
        self.instance_logger.info(f"Initializing IntegratedTradingSystem (Version: EOTS_ITS_v2.3.1_Canon_IDS_Sync_Logging)...")
        self.instance_logger.debug(f"ITS __init__ called with config_path: '{config_path}', log_level: '{log_level}'")

        effective_config_path_for_load: str
        default_cfg_filename_its = "config_v2.json" # Standard config filename
        
        if config_path and os.path.isabs(config_path) and os.path.exists(config_path):
            effective_config_path_for_load = config_path
            self.instance_logger.debug(f"Using provided absolute config_path: '{effective_config_path_for_load}'")
        elif config_path: # Path provided but might be relative or non-existent
            path_from_cwd_its = os.path.join(os.getcwd(), config_path)
            if os.path.exists(path_from_cwd_its):
                effective_config_path_for_load = os.path.abspath(path_from_cwd_its)
                self.instance_logger.debug(f"Using provided config_path, resolved relative to CWD: '{effective_config_path_for_load}'")
            else: # Try relative to this script's project structure
                try: 
                    script_dir_its = os.path.dirname(os.path.abspath(__file__))
                    project_root_its = os.path.dirname(script_dir_its) # Assumes ITS is in core_analytics, one level down
                    path_from_project_root_its = os.path.join(project_root_its, config_path) # Try provided name relative to project root
                    if os.path.exists(path_from_project_root_its):
                        effective_config_path_for_load = os.path.abspath(path_from_project_root_its)
                        self.instance_logger.debug(f"Using provided config_path, resolved relative to project root: '{effective_config_path_for_load}'")
                    else: # Fallback to default name in project root if provided path not found
                        effective_config_path_for_load = os.path.join(project_root_its, default_cfg_filename_its)
                        self.instance_logger.warning(f"Provided config_path '{config_path}' not found. Trying default '{default_cfg_filename_its}' in project root: '{effective_config_path_for_load}'")
                except NameError: # __file__ not defined
                    project_root_its = os.getcwd()
                    effective_config_path_for_load = os.path.join(project_root_its, default_cfg_filename_its)
                    self.instance_logger.warning(f"__file__ not defined. Trying default '{default_cfg_filename_its}' in CWD: '{effective_config_path_for_load}'")
        else: # No config_path provided, use default logic
            try: 
                script_dir_its = os.path.dirname(os.path.abspath(__file__))
                project_root_its = os.path.dirname(script_dir_its)
            except NameError: project_root_its = os.getcwd()
            effective_config_path_for_load = os.path.join(project_root_its, default_cfg_filename_its)
            self.instance_logger.debug(f"No config_path provided. Using default path logic: '{effective_config_path_for_load}'")

        # Load configuration using the utility from config_utils
        try:
            self.config: Dict[str, Any] = load_and_validate_config_its( # type: ignore # Handled by fallback
                config_path=effective_config_path_for_load,
                default_config_data=DEFAULT_ITS_CONFIG_V231, # From config_utils (or its fallback)
                log_instance=self.instance_logger.getChild("ConfigLoader_ITS_v231")
            )
            self.instance_logger.info(f"ITS Configuration loaded. Source: '{self.config.get(ids.CFG_CONFIG_FILE_PATH_CACHED_AT if IDS_IMPORTED_SUCCESSFULLY_EDP else '_config_file_path_cached_at', 'ITS Defaults/Retriever/Not Found')}'")
        except Exception as e_cfg_load_its:
            self.instance_logger.critical(f"CRITICAL ERROR loading/validating ITS config from '{effective_config_path_for_load}': {e_cfg_load_its}", exc_info=True)
            self.config = copy.deepcopy(DEFAULT_ITS_CONFIG_V231) # Use a copy of the default
            self.config["_config_load_error_its_v231"] = str(e_cfg_load_its) # Store error in config

        # Set instance logger level based on config or provided level
        final_log_level_str = log_level # Prioritize direct param
        if final_log_level_str is None: # If not passed directly, get from config
            final_log_level_str = str(self._get_config_value(ids.CFG_SYSTEM_LOG_LEVEL, "INFO"))
        
        try: 
            self.instance_logger.setLevel(getattr(logging, final_log_level_str.upper()))
            # Propagate level to child loggers if this logger's level is being set more restrictively than root
            # This is complex; usually main app sets root level. For ITS, just set its own.
        except (AttributeError, ValueError): 
            self.instance_logger.setLevel(logging.INFO)
            self.instance_logger.warning(f"Invalid log level '{final_log_level_str}' specified for ITS. Defaulting to INFO.")
        self.instance_logger.info(f"ITS Instance logger level set to: {logging.getLevelName(self.instance_logger.getEffectiveLevel())}.")

        self._load_core_attributes_from_config() # Load attributes using ids.py constants

        # Max length for historical DataFrame deques, using ids.py for config path
        df_hist_maxlen_cfg_val = self._get_config_value(ids.CFG_SYSTEM_DF_HISTORY_MAXLEN_ITS, 10) 
        try: 
            self.df_history_maxlen = int(df_hist_maxlen_cfg_val)
            if self.df_history_maxlen <= 0: self.df_history_maxlen = 1 # Ensure at least 1
        except (ValueError, TypeError): 
            self.df_history_maxlen = 10 # Fallback
            self.instance_logger.warning(f"Invalid config value for df_history_maxlen_its ('{df_hist_maxlen_cfg_val}'). Defaulting to {self.df_history_maxlen}.")
        self.instance_logger.debug(f"DataFrame history maxlen set to: {self.df_history_maxlen}")

        self.processed_df_history: Dict[str, Deque[pd.DataFrame]] = {} # Stores deque of processed DFs per symbol
        self.adaptive_historical_context: Dict[str, Dict[str, Any]] = {} # Stores richer context for adaptive modules
        self.active_recommendations: List[Dict[str, Any]] = [] # List of currently active trade recommendations
        self.current_symbol_being_managed: Optional[str] = None # Tracks symbol for stateful operations like rec IDs
        self.recommendation_id_counters_by_symbol: Dict[str, int] = {} # Ensures unique rec IDs per symbol

        # Assigning actual modules (assuming imports were successful, otherwise they are dummies)
        self.mspi_orchestration_module = mspi_orchestration_module
        self.level_identification_module = level_identification_module
        self.signal_generator_module = signal_generation_module
        self.fallback_recs_module = fallback_recommendation_module 
        self.rec_state_manager_module = recommendation_state_manager
        self.system_utils_module = sys.modules.get('core_analytics.system_utilities', DummyModule_ITS("system_utilities_fallback_its")) # type: ignore

        self.instance_logger.info(f"IntegratedTradingSystem (v2.3.1 Canon IDS Sync & Logging) initialized. Strike Column: '{self.col_strike}', MSPI Output Column: '{self.mspi_col_name}'")

    def _get_config_value(self, path_keys: List[str], default_return: Any = None) -> Any:
        # Helper to safely get nested config values. Uses direct dict access.
        # Assumes self.config is already loaded.
        current_level = self.config
        try:
            for key_segment in path_keys:
                if isinstance(current_level, dict):
                    current_level = current_level[key_segment]
                else: # Path broken, key_segment not found in a non-dict
                    self.instance_logger.log(logging.DEBUG - 1, f"Config get_value: Path broken at '{key_segment}' in {path_keys}. Current level type: {type(current_level)}. Returning default: {default_return}")
                    return default_return
            return current_level
        except KeyError: # Key not found at some level
            self.instance_logger.log(logging.DEBUG -1, f"Config get_value: Key not found in path {path_keys}. Returning default: {default_return}")
            return default_return
        except Exception as e_get_cfg_unexpected: # Catch any other unexpected errors
            self.instance_logger.error(f"Config get_value: Unexpected error for path {path_keys}: {e_get_cfg_unexpected}. Returning default: {default_return}", exc_info=True)
            return default_return

    def _load_core_attributes_from_config(self) -> None:
        """Loads core attributes and column names from the configuration using ids.py constants."""
        load_attr_logger = self.instance_logger.getChild("LoadCoreAttributes_ITS_v231")
        load_attr_logger.info("Loading ITS core attributes and column names from configuration...")

        if not IDS_IMPORTED_SUCCESSFULLY_EDP: # Check if ids.py itself loaded
            load_attr_logger.critical("CRITICAL: 'utils.ids' module was not imported successfully. Cannot load attributes based on ids.py constants. ITS will likely fail or use incorrect hardcoded fallbacks.")
            # Set critical attributes to hardcoded fallbacks if ids.py is missing
            self.col_strike = "strike_price"
            self.col_opt_kind = "opt_kind"
            self.col_underlying_symbol = "underlying_symbol" # Fallback
            self.col_expiration_date = "expiration_date"
            self.col_delta_greek = "delta"
            self.mspi_col_name = "mspi"
            # ... set other critical fallbacks ...
            return # Exit early if ids.py is not available

        # --- Column Names for ITS Internal Use and Module Calls ---
        self.col_strike = str(self._get_config_value(ids.CFG_METRICS_CALC_STRIKE_COL_INTERNAL, ids.COL_STRIKE))
        self.col_opt_kind = str(self._get_config_value(ids.CFG_VIZ_COL_OPT_KIND, ids.COL_OPT_KIND))
        
        # Corrected logic for underlying_symbol based on previous fix
        _underlying_symbol_config_key_list = ids.CFG_VIZ_COL_NAMES + ["underlying_symbol"] # Path to "underlying_symbol" in viz config e.g. ['visualization_settings', ..., 'underlying_symbol']
        _default_underlying_symbol_col = ids.COL_UNDERLYING_SYMBOL_CHAIN # Default to the chain-specific column from ids.py
        self.col_underlying_symbol = str(self._get_config_value(_underlying_symbol_config_key_list, _default_underlying_symbol_col))
        load_attr_logger.debug(f"Underlying Symbol Column set to: '{self.col_underlying_symbol}' (from config path: {_underlying_symbol_config_key_list} or default: '{_default_underlying_symbol_col}')")

        self.col_expiration_date = str(self._get_config_value(ids.CFG_VIZ_COL_EXPIRY_DATE, ids.COL_EXPIRATION_DATE))
        # For delta, construct path using list addition and .lower() for the key part from config
        _delta_config_key_list = ids.CFG_VIZ_COL_NAMES + [ids.COL_DELTA_CONTRACT.lower()] # e.g. ... + ['delta']
        self.col_delta_greek = str(self._get_config_value(_delta_config_key_list, ids.COL_DELTA_CONTRACT))

        self.mspi_col_name = str(self._get_config_value(ids.CFG_VIZ_COL_MSPI, ids.COL_MSPI_SCORE))

        # Source columns for metrics_calculator (passed to mspi_orchestration_module)
        metrics_calc_cfg_base = self._get_config_value(ids.CFG_METRICS_CALC, {}) # Get the whole metrics_calculator_v2_5_settings block
        
        self.gamma_exposure_col_its = str(metrics_calc_cfg_base.get(ids.CFG_METRICS_CALC_GAMMA_COL_KEY[-1], ids.COL_GXOI_CONTRACT)) # Use last part of path as key
        self.delta_exposure_col_its = str(metrics_calc_cfg_base.get(ids.CFG_METRICS_CALC_DELTA_COL_KEY[-1], ids.COL_DXOI_CONTRACT))
        self.option_iv_col_its = str(metrics_calc_cfg_base.get(ids.CFG_METRICS_CALC_OPT_IV_COL_KEY[-1], ids.COL_VOLATILITY_OPTION_CONTRACT))
        self.option_price_col_name_for_mspi_orchestration = str(metrics_calc_cfg_base.get(ids.CFG_METRICS_CALC_OPT_PRICE_COL_KEY[-1], ids.COL_PRICE_OPTION_CONTRACT))
        self.underlying_price_key_in_bundle = str(metrics_calc_cfg_base.get(ids.CFG_METRICS_CALC_UND_PRICE_KEY[-1], ids.CV_UND_PARAM_PRICE))
        self.charmxoi_col_its = str(metrics_calc_cfg_base.get(ids.CFG_METRICS_CALC_CHARM_COL_KEY[-1], ids.COL_CHARMXOI_CONTRACT))
        self.txoi_col_its = str(metrics_calc_cfg_base.get(ids.CFG_METRICS_CALC_THETA_COL_KEY[-1], ids.COL_TXOI_CONTRACT))
        self.vannaxoi_col_its = str(metrics_calc_cfg_base.get(ids.CFG_METRICS_CALC_VANNA_COL_KEY[-1], ids.COL_VANNAXOI_CONTRACT))
        self.vxoi_col_its = str(metrics_calc_cfg_base.get(ids.CFG_METRICS_CALC_VEGA_COL_KEY[-1], ids.COL_VXOI_CONTRACT)) # Corrected from _VRI_ to _VEGA_
        self.vommaxoi_col_its = str(metrics_calc_cfg_base.get(ids.CFG_METRICS_CALC_VOMMA_COL_KEY[-1], ids.COL_VOMMAXOI_CONTRACT))
        self.volm_col_for_weighting_its = str(metrics_calc_cfg_base.get(ids.CFG_METRICS_CALC_VOLM_COL_KEY[-1], ids.COL_VOLUME_OPTION_CONTRACT))

        # Flow column names (these are expected to be direct ids.py constants representing API output names)
        self.direct_delta_buy_col_its = ids.CV_CHAIN_PARAM_DELTAS_BUY_CONTRACT
        self.direct_delta_sell_col_its = ids.CV_CHAIN_PARAM_DELTAS_SELL_CONTRACT
        self.proxy_delta_flow_col_its = ids.CV_CHAIN_PARAM_DXVOLM # Corrected from _CONTRACT
        self.direct_gamma_buy_col_its = ids.CV_CHAIN_PARAM_GAMMAS_BUY_CONTRACT
        self.direct_gamma_sell_col_its = ids.CV_CHAIN_PARAM_GAMMAS_SELL_CONTRACT
        self.proxy_gamma_flow_col_its = ids.CV_CHAIN_PARAM_GXVOLM # Corrected from _CONTRACT
        self.direct_theta_buy_col_its = ids.CV_CHAIN_PARAM_THETAS_BUY_CONTRACT
        self.direct_theta_sell_col_its = ids.CV_CHAIN_PARAM_THETAS_SELL_CONTRACT
        self.proxy_theta_flow_col_its = ids.CV_CHAIN_PARAM_TXVOLM # Corrected from _CONTRACT
        self.proxy_charm_flow_col_its = ids.CV_CHAIN_PARAM_CHARMXVOLM # Corrected from _CONTRACT
        self.direct_vega_buy_col_its = ids.CV_CHAIN_PARAM_VEGAS_BUY_CONTRACT
        self.direct_vega_sell_col_its = ids.CV_CHAIN_PARAM_VEGAS_SELL_CONTRACT
        self.proxy_vega_flow_col_its = ids.CV_CHAIN_PARAM_VXVOLM # Corrected from _CONTRACT
        self.proxy_vanna_flow_col_its = ids.CV_CHAIN_PARAM_VANNAXVOLM # Corrected from _CONTRACT
        self.proxy_vomma_flow_col_its = ids.CV_CHAIN_PARAM_VOMMAXVOLM # Corrected from _CONTRACT

        # Original SDAG settings (v2.3) - paths need to be lists of strings
        _sdag_methodologies_base_path = ids.CFG_DAG_METHODOLOGIES_ITS # This is already a list
        self.original_use_skew_adjusted_cfg_its = bool(self._get_config_value(_sdag_methodologies_base_path + ["use_skew_adjusted_gex_for_original_sdags"], False))
        self.original_skew_adjusted_gamma_col_its = str(self._get_config_value(_sdag_methodologies_base_path + ["skew_adjusted_gex_source_col_name"], "sgxoi_fallback")) # Fallback if key missing

        # For v2.3, enhanced metrics are generally off by default in ITS logic, but config paths are mapped
        self.enhanced_metrics_master_enabled = bool(self._get_config_value(ids.CFG_ENHANCED_METRICS + ["enabled"], False))
        self.a_dag_enabled_its_attr = self.enhanced_metrics_master_enabled and bool(self._get_config_value(ids.CFG_ENHANCED_METRICS + ["a_dag", "enabled"], False))
        self.d_tdpi_enabled_its_attr = self.enhanced_metrics_master_enabled and bool(self._get_config_value(ids.CFG_ENHANCED_METRICS + ["d_tdpi", "enabled"], False))
        self.vri_2_0_enabled_its_attr = self.enhanced_metrics_master_enabled and bool(self._get_config_value(ids.CFG_ENHANCED_METRICS + ["vri_2_0", "enabled"], False))
        self.e_sdag_enabled_its_attr = self.enhanced_metrics_master_enabled and bool(self._get_config_value(ids.CFG_ENHANCED_METRICS + ["e_sdag", "enabled"], False))
        
        self.a_dag_output_col_its_attr = str(self._get_config_value(ids.CFG_ENHANCED_METRICS + ["a_dag", "output_column_name"], ids.COL_A_DAG_OUTPUT))
        self.a_dag_norm_col_its_attr = str(self._get_config_value(ids.CFG_ENHANCED_METRICS + ["a_dag", "norm_column_name"], ids.COL_A_DAG_NORM))
        self.d_tdpi_output_col_its_attr = str(self._get_config_value(ids.CFG_ENHANCED_METRICS + ["d_tdpi", "output_column_name"], ids.COL_D_TDPI_OUTPUT))
        self.d_tdpi_norm_col_its_attr = str(self._get_config_value(ids.CFG_ENHANCED_METRICS + ["d_tdpi", "norm_column_name"], ids.COL_D_TDPI_NORM))
        self.vri_2_0_output_col_its_attr = str(self._get_config_value(ids.CFG_ENHANCED_METRICS + ["vri_2_0", "output_column_name"], ids.COL_VRI_2_0_OUTPUT))
        self.vri_2_0_norm_col_its_attr = str(self._get_config_value(ids.CFG_ENHANCED_METRICS + ["vri_2_0", "norm_column_name"], ids.COL_VRI_2_0_NORM))
        self.e_sdag_composite_output_col_its_attr = str(self._get_config_value(ids.CFG_ENHANCED_METRICS + ["e_sdag", "composite_output_column_name"], ids.COL_E_SDAG_COMPOSITE_OUTPUT))
        self.e_sdag_composite_norm_col_its_attr = str(self._get_config_value(ids.CFG_ENHANCED_METRICS + ["e_sdag", "composite_norm_column_name"], ids.COL_E_SDAG_COMPOSITE_NORM))
        
        # E-SDAG specific sub-configurations
        metrics_calc_e_sdag_sub_cfgs_its = self._get_config_value(ids.CFG_METRICS_CALC_ADAPTIVE_ESDAG_SETTINGS, {}) # Path from ids.py
        self.e_sdag_use_enhanced_skew_cfg_its_attr = self.e_sdag_enabled_its_attr and bool(metrics_calc_e_sdag_sub_cfgs_its.get("use_enhanced_skew_calculation_for_sgexoi", False))
        sgexoi_params_for_e_sdag_its = metrics_calc_e_sdag_sub_cfgs_its.get("sgexoi_calculation_params", {})
        self.e_sdag_enhanced_gex_out_col_its_attr = str(sgexoi_params_for_e_sdag_its.get("enhanced_gex_output_col_name", ids.COL_E_SDAG_SKEW_ADJUSTED_GEX))

        load_attr_logger.info(f"ITS Core Attributes and Column Names Loaded. Strike Column: '{self.col_strike}', MSPI Output Column: '{self.mspi_col_name}', Underlying Symbol Column: '{self.col_underlying_symbol}'")

    def _orchestrate_full_analysis(
        self,
        options_df_input: pd.DataFrame, 
        underlying_data: Dict[str, Any], # Raw underlying bundle from CV
        underlying_price_ctx: Optional[float], # Scalar current price
        current_time_ctx: Optional[dt_time], # Current time object
        current_iv_ctx: Optional[float], # Current IV (e.g., from Tradier approx)
        avg_iv_5day_ctx: Optional[float], # 5-day avg IV (e.g., from Tradier approx)
        iv_context_dict_ctx: Optional[Dict[str, Any]], # Full IV bundle from Tradier (quote, IV approx etc.)
        historical_ohlc_df_ctx: Optional[pd.DataFrame], # OHLCV data
        avg_iv_long_term_ctx: Optional[float], # For v2.5 adaptive modules
        historical_atr_normalized_vs_avg_ctx: Optional[float], # For v2.5 adaptive modules
        current_symbol_ctx: str,
        expiration_calendar_data_ctx: Optional[List[date]],
        current_market_regime_ctx: Optional[str] = None, 
        ticker_context_flags_ctx: Optional[Dict[str, Any]] = None 
    ) -> Tuple[pd.DataFrame, Dict[str, Any], Dict[str, Any], Optional[str]]: # Returns (metrics_df, key_levels_bundle, signals_bundle, error_string)
        orch_logger = self.instance_logger.getChild(f"OrchestrateFullAnalysis.{current_symbol_ctx}.ITS_v231")
        price_display_orch = f"{underlying_price_ctx:.2f}" if underlying_price_ctx is not None else "N/A"
        time_display_orch = current_time_ctx.isoformat() if current_time_ctx else datetime.now().time().isoformat()
        orch_logger.info(f"Orchestrating v2.3.1 analysis for '{current_symbol_ctx}' at {time_display_orch}. Underlying Price: {price_display_orch}. Input DF shape: {options_df_input.shape}")

        if not isinstance(options_df_input, pd.DataFrame) or options_df_input.empty:
            err_orch = f"Input options_df for '{current_symbol_ctx}' is empty or invalid. Cannot orchestrate analysis."
            orch_logger.error(err_orch)
            return pd.DataFrame(), {"error": err_orch, "all_levels_sorted_by_strength": []}, {"error": err_orch, "signals_generated_count": 0}, err_orch

        # --- For v2.3, enhanced_metrics_master_enabled is effectively False for ITS logic ---
        # The mspi_orchestration_module calculates base v2.3 metrics (MSPI, original SDAGs, base TDPI/VRI/DAG).
        # It's crucial that column names passed here match what mspi_orchestration_module expects.
        # These are derived from self attributes set in _load_core_attributes_from_config, which use ids.py
        
        orch_logger.debug(f"Calling mspi_orchestration_module.calculate_mspi_main for '{current_symbol_ctx}'...")
        df_metrics_calculated = self.mspi_orchestration_module.calculate_mspi_main( # type: ignore # Handled by dummy if import failed
            options_df=options_df_input.copy(), # Pass the df that already has raw impacts from EDP
            config_value_getter=self._get_config_value, # Pass the ITS config getter
            # Column names for source data (these are attributes of self, set from config via ids.py)
            gamma_exposure_col_mspi=self.gamma_exposure_col_its, delta_exposure_col_mspi=self.delta_exposure_col_its,
            option_iv_col_mspi=self.option_iv_col_its, strike_col_mspi=self.col_strike,
            option_price_col_name_in_df_mspi=self.option_price_col_name_for_mspi_orchestration,
            opt_kind_col_mspi=self.col_opt_kind, underlying_symbol_col_mspi=self.col_underlying_symbol,
            expiration_date_col_mspi=self.col_expiration_date,
            # Direct flow columns
            direct_delta_buy_col_mspi=self.direct_delta_buy_col_its, direct_delta_sell_col_mspi=self.direct_delta_sell_col_its,
            direct_gamma_buy_col_mspi=self.direct_gamma_buy_col_its, direct_gamma_sell_col_mspi=self.direct_gamma_sell_col_its,
            direct_theta_buy_col_mspi=self.direct_theta_buy_col_its, direct_theta_sell_col_mspi=self.direct_theta_sell_col_its,
            direct_vega_buy_col_mspi=self.direct_vega_buy_col_its, direct_vega_sell_col_mspi=self.direct_vega_sell_col_its,
            # Proxy flow columns
            proxy_delta_flow_col_mspi=self.proxy_delta_flow_col_its, proxy_gamma_flow_col_mspi=self.proxy_gamma_flow_col_its,
            proxy_theta_flow_col_mspi=self.proxy_theta_flow_col_its, proxy_charm_flow_col_mspi=self.proxy_charm_flow_col_its,
            proxy_vega_flow_col_mspi=self.proxy_vega_flow_col_its, proxy_vanna_flow_col_mspi=self.proxy_vanna_flow_col_its,
            proxy_vomma_flow_col_mspi=self.proxy_vomma_flow_col_its,
            # Greek OI columns
            charmxoi_col_mspi=self.charmxoi_col_its, txoi_col_mspi=self.txoi_col_its, 
            vannaxoi_col_mspi=self.vannaxoi_col_its, vxoi_col_mspi=self.vxoi_col_its, 
            vommaxoi_col_mspi=self.vommaxoi_col_its,
            # Output column name for MSPI
            mspi_output_col_name_cfg=self.mspi_col_name, 
            # Original SDAG settings
            original_use_skew_adjusted_cfg=self.original_use_skew_adjusted_cfg_its,
            original_skew_adjusted_gamma_col_mspi=self.original_skew_adjusted_gamma_col_its,
            volm_col_for_weighting_mspi=self.volm_col_for_weighting_its,
            # --- Explicitly control v2.5 features for a v2.3 run ---
            adaptive_system_enabled_its=False, 
            enhanced_metrics_master_enabled_its=False, 
            a_dag_enabled_its=False, a_dag_output_col_its=self.a_dag_output_col_its_attr, a_dag_norm_col_its=self.a_dag_norm_col_its_attr,
            e_sdag_enabled_its=False, e_sdag_composite_output_col_its=self.e_sdag_composite_output_col_its_attr, e_sdag_composite_norm_col_its=self.e_sdag_composite_norm_col_its_attr,
            e_sdag_use_enhanced_skew_cfg_its=False, e_sdag_enhanced_gex_out_col_its=self.e_sdag_enhanced_gex_out_col_its_attr,
            d_tdpi_enabled_its=False, d_tdpi_output_col_its=self.d_tdpi_output_col_its_attr, d_tdpi_norm_col_its=self.d_tdpi_norm_col_its_attr,
            vri_2_0_enabled_its=False, vri_2_0_output_col_its=self.vri_2_0_output_col_its_attr, vri_2_0_norm_col_its=self.vri_2_0_norm_col_its_attr,
            # Contextual data
            current_time_mspi=current_time_ctx, current_iv_mspi=current_iv_ctx, avg_iv_5day_mspi=avg_iv_5day_ctx,
            iv_context_mspi=iv_context_dict_ctx, underlying_price_mspi=underlying_price_ctx,
            historical_ohlc_df_for_atr_mspi=historical_ohlc_df_ctx,
            avg_iv_long_term_mspi=avg_iv_long_term_ctx, 
            historical_atr_normalized_vs_avg_mspi=historical_atr_normalized_vs_avg_ctx, 
            current_symbol_mspi=current_symbol_ctx,
            symbol_specific_historical_context_mspi=self.adaptive_historical_context.get(current_symbol_ctx, {}), 
            log_instance=orch_logger.getChild("MetricsCalculatorCall_ITS_v231")
        )
        orch_logger.info(f"MSPI Suite (v2.3 style) calculations complete for '{current_symbol_ctx}'. Output DF shape: {df_metrics_calculated.shape}")
        if self.mspi_col_name not in df_metrics_calculated.columns:
            orch_logger.error(f"MSPI output column '{self.mspi_col_name}' not found in DataFrame after mspi_orchestration_module. This is a critical issue.")
            # Add a dummy MSPI column to prevent downstream errors if it's missing
            df_metrics_calculated[self.mspi_col_name] = 0.0 

        # --- Aggregation of strike-level metrics (v2.3 style) ---
        orch_logger.debug(f"Aggregating strike-level metrics for '{current_symbol_ctx}'...")
        # Use system_utilities.aggregate_for_levels
        # Get enabled SDAG methods from config using ids.py constant
        enabled_sdag_methods_for_agg = self._get_config_value(ids.CFG_DAG_METHODOLOGIES_ENABLED_ITS, [])
        aggregated_df = self.system_utils_module.aggregate_for_levels( # type: ignore # Handled by dummy
            df_metrics_calculated.copy(), 
            strike_col_name=self.col_strike, # Use the attribute set from config
            enabled_sdag_methods_list=enabled_sdag_methods_for_agg, 
            log_instance=orch_logger.getChild("AggMetrics_ITS_v231")
        )
        orch_logger.info(f"Strike aggregation complete for '{current_symbol_ctx}'. Aggregated DF shape: {aggregated_df.shape}")

        # --- Key Levels Identification (v2.3 - simplified version or using EKL module if available) ---
        key_levels_bundle_out: Dict[str, Any] = {"error": "Key Levels (v2.3) not run or module unavailable.", "all_levels_sorted_by_strength": []}
        if hasattr(self.level_identification_module, 'identify_enhanced_key_levels_main'): 
            orch_logger.debug(f"Calling level_identification_module.identify_enhanced_key_levels_main for '{current_symbol_ctx}'...")
            # Get config for EKL module
            key_level_main_cfg_its = self._get_config_value(ids.CFG_KEY_LEVEL_SETTINGS, {}) # Path from ids.py
            atr_fb_cfg_ekl_its = self._get_config_value(ids.CFG_METRICS_CALC_ATR_FALLBACK, {}) # Path from ids.py
            
            key_levels_bundle_out = self.level_identification_module.identify_enhanced_key_levels_main( # type: ignore
                current_aggregated_df=aggregated_df, 
                mspi_col_name_ekl=self.mspi_col_name, # Use ITS attribute for MSPI col name
                strike_col_name_ekl=self.col_strike, # Use ITS attribute
                # Pass other column names using ITS attributes (which are from config via ids.py)
                underlying_symbol_col_ekl=self.col_underlying_symbol, 
                price_col_ekl=self.underlying_price_key_in_bundle, # Key for underlying price in underlying_data
                opt_kind_col_ekl=self.col_opt_kind, 
                delta_col_ekl=self.col_delta_greek, 
                volm_col_ekl=self.volm_col_for_weighting_its,
                # Pass EKL specific configurations from the main config dict
                ekl_mtf_dyn_mspi_base_cfg_ekl=float(key_level_main_cfg_its.get("dynamic_mspi_base_threshold_for_intraday", 0.3)),
                ekl_mtf_dyn_mspi_sens_cfg_ekl=float(key_level_main_cfg_its.get("dynamic_mspi_threshold_sensitivity_to_iv_rank", 0.2)),
                ekl_mtf_daily_lookback_dfs_cfg_ekl=int(key_level_main_cfg_its.get("daily_level_lookback_periods", 5)),
                ekl_mtf_daily_persistence_cfg_ekl=int(key_level_main_cfg_its.get("daily_level_persistence_min_count", 2)),
                ekl_mtf_daily_mspi_thresh_cfg_ekl=float(key_level_main_cfg_its.get("daily_level_mspi_strength_min", 0.25)),
                ekl_mtf_weekly_lookback_dfs_cfg_ekl=int(key_level_main_cfg_its.get("weekly_level_lookback_periods", 20)),
                ekl_mtf_weekly_persistence_cfg_ekl=int(key_level_main_cfg_its.get("weekly_level_persistence_min_count", 3)),
                ekl_mtf_weekly_mspi_thresh_cfg_ekl=float(key_level_main_cfg_its.get("weekly_level_mspi_strength_min", 0.35)),
                ekl_pi_lookback_candles_cfg_ekl=int(key_level_main_cfg_its.get("price_interaction_lookback_candles", 20)),
                ekl_pi_reaction_thresh_atr_cfg_ekl=float(key_level_main_cfg_its.get("price_interaction_reaction_threshold_atr_mult", 0.5)),
                ekl_pi_bonus_hold_cfg_ekl=float(key_level_main_cfg_its.get("level_strength_scoring_weights", {}).get("price_interaction_bonus_hold", 0.1)),
                ekl_pi_penalty_breach_cfg_ekl=float(key_level_main_cfg_its.get("level_strength_scoring_weights", {}).get("price_interaction_penalty_breach", -0.15)),
                ekl_mtf_cluster_dist_atr_cfg_ekl=float(key_level_main_cfg_its.get("level_cluster_distance_atr_factor", 0.25)),
                ekl_ls_mspi_weight_cfg_ekl=float(key_level_main_cfg_its.get("level_strength_scoring_weights", {}).get("mspi_magnitude", 0.35)),
                ekl_ls_persist_weight_cfg_ekl=float(key_level_main_cfg_its.get("level_strength_scoring_weights", {}).get("persistence", 0.25)),
                ekl_ls_price_int_weight_cfg_ekl=float(key_level_main_cfg_its.get("level_strength_scoring_weights", {}).get("price_interaction", 0.20)),
                ekl_ls_cluster_bonus_cfg_ekl=float(key_level_main_cfg_its.get("level_strength_scoring_weights", {}).get("clustering_peak_bonus", 0.10)),
                ekl_mtf_intraday_weight_cfg_ekl=float(key_level_main_cfg_its.get("level_strength_scoring_weights", {}).get("source_metric_priority_map", {}).get("Intraday_MSPI", 0.5)),
                atr_fallback_cfg_ekl=atr_fb_cfg_ekl_its, # ATR fallback config
                historical_aggregated_dfs=self.processed_df_history.get(current_symbol_ctx), # Pass historical aggregated DFs
                price_history_ohlc_df=historical_ohlc_df_ctx, # Pass OHLCV
                current_underlying_price=underlying_price_ctx, # Pass current price
                historical_context_for_dyn_thresh=self.adaptive_historical_context.get(current_symbol_ctx, {}), # Pass adaptive context
                log_instance=orch_logger.getChild("KeyLevelIdentifierCall_ITS_v231")
            )
            orch_logger.info(f"Key levels identification complete for '{current_symbol_ctx}'. Result error: '{key_levels_bundle_out.get('error', 'None')}'")
        else:
            orch_logger.warning(f"Level identification module or 'identify_enhanced_key_levels_main' function not available for '{current_symbol_ctx}'. Key levels will be empty.")

        # --- Signal Generation (v2.3 - basic signals from MSPI and SDAGs) ---
        signals_bundle_out: Dict[str, Any] = {"error": "Signals (v2.3) not run or module unavailable.", "signals_generated_count": 0}
        if hasattr(self.signal_generator_module, 'generate_trading_signals'):
            orch_logger.debug(f"Calling signal_generator_module.generate_trading_signals for '{current_symbol_ctx}'...")
            # Get v2.3 specific signal activation config
            signal_activation_v2_3_cfg_its = self._get_config_value(ids.CFG_SYSTEM_SIGNAL_ACTIVATION_V2_3, # Path from ids.py
                default_return={"directional": True, "sdag_conviction": True, "volatility_expansion": False}) # Sensible v2.3 defaults
            
            signals_bundle_out = self.signal_generator_module.generate_trading_signals( # type: ignore
                current_aggregated_df=aggregated_df,
                signal_activation_config=signal_activation_v2_3_cfg_its, # Pass the v2.3 specific config
                config_value_getter=self._get_config_value, 
                map_score_to_stars_func=map_score_to_stars, # type: ignore # Utility from system_utilities
                enabled_sdag_methods=enabled_sdag_methods_for_agg, # Use the same list as for aggregation
                min_sdag_agreement=int(self._get_config_value(_sdag_methodologies_base_path + ["min_agreement_for_conviction_signal"], 2)), # Use list addition for path
                log_instance=orch_logger.getChild("SignalGeneratorCall_ITS_v231"),
                strike_col_name=self.col_strike, # Pass active strike column name
                mspi_col_name=self.mspi_col_name # Pass MSPI column name
            )
            orch_logger.info(f"Signal generation complete for '{current_symbol_ctx}'. Signals generated: {signals_bundle_out.get('signals_generated_count', 0)}. Result error: '{signals_bundle_out.get('error', 'None')}'")
        else:
            orch_logger.warning(f"Signal generation module or 'generate_trading_signals' function not available for '{current_symbol_ctx}'. Signals will be empty.")
        
        # No internal pipeline error if we reached here, return the results
        return df_metrics_calculated, key_levels_bundle_out, signals_bundle_out, None 

    def process_market_data_and_generate_recommendations(
        self,
        symbol: str,
        raw_options_data: pd.DataFrame, # This DataFrame comes from EDP and should include raw impact columns
        underlying_data: Dict[str, Any], # Raw underlying bundle from CV fetcher
        market_context: Dict[str, Any], # Contains current_time, iv_and_quote_data from Tradier
        historical_ohlc_data: Optional[pd.DataFrame], # OHLCV data from Tradier
        expiration_calendar: Optional[List[date]] # Expiration calendar from Tradier
    ) -> Dict[str, Any]: # Returns the final bundle for this symbol
        process_logger_main = self.instance_logger.getChild(f"ProcessMarketData.{symbol}.ITS_v231")
        start_time_its_symbol = time.monotonic()
        start_time_its_symbol = pytime.monotonic()

        overall_error_msg_its: Optional[str] = None
        full_traceback_str_its: Optional[str] = None
        
        # Initialize return components with defaults
        final_metric_rich_df_its = raw_options_data.copy() if isinstance(raw_options_data, pd.DataFrame) else pd.DataFrame()
        key_levels_bundle_its: Dict[str, Any] = {"error": "ITS_EKL_NotRun_v231", "all_levels_sorted_by_strength": []}
        signals_bundle_its: Dict[str, Any] = {"error": "ITS_Signals_NotRun_v231", "signals_generated_count": 0}
        active_recommendations_list_its: List[Dict[str, Any]] = []
        mspi_weights_applied_its: Dict[str, float] = {}
        current_atr_value_its: float = 0.0 # Default to 0.0
        hist_ctx_summary_its: Dict[str, Any] = {"status": "ITS_HistCtx_NotUpdated_v231"}

        try:
            process_logger_main.debug(f"Input raw_options_data shape for '{symbol}': {raw_options_data.shape if isinstance(raw_options_data, pd.DataFrame) else 'Not DataFrame'}")
            # --- Extract and Validate Contextual Data ---
            # Underlying Price
            und_price_raw_its = underlying_data.get(self.underlying_price_key_in_bundle) # Uses attribute set from config
            und_price_val_its = float(pd.to_numeric(und_price_raw_its, errors='coerce')) if pd.notna(und_price_raw_its) else None
            if not (und_price_val_its and und_price_val_its > 0): # Check if price is valid positive number
                overall_error_msg_its = f"CRITICAL: Underlying price for '{symbol}' is missing, zero, or invalid ({und_price_raw_its}). Cannot proceed with ITS analysis."
                process_logger_main.critical(overall_error_msg_its)
                raise ValueError(overall_error_msg_its) # Raise to go to main try-except block
            process_logger_main.debug(f"Validated underlying price for '{symbol}': {und_price_val_its:.2f}")

            # Current Time
            mc_time_raw_its = market_context.get("current_time", datetime.now().time()) # Default to now if missing
            mc_time_val_its = dt_time.fromisoformat(mc_time_raw_its) if isinstance(mc_time_raw_its, str) else \
                              (mc_time_raw_its if isinstance(mc_time_raw_its, dt_time) else datetime.now().time())
            process_logger_main.debug(f"Market context time for '{symbol}': {mc_time_val_its.isoformat()}")

            # IV Context
            mc_iv_quote_bundle_its = market_context.get("iv_and_quote_data", {})
            if not isinstance(mc_iv_quote_bundle_its, dict): mc_iv_quote_bundle_its = {} # Ensure it's a dict
            
            # Use config keys (via attributes) for IV fields
            current_iv_key_its = self._get_config_value(ids.CFG_METRICS_CALC + ["current_iv_source_key_in_und_data"], ids.CV_UND_PARAM_VOLATILITY)
            mc_curr_iv_raw_its = market_context.get("current_iv", mc_iv_quote_bundle_its.get("current_iv", underlying_data.get(current_iv_key_its)))
            mc_curr_iv_val_its = float(pd.to_numeric(mc_curr_iv_raw_its, errors='coerce')) if pd.notna(mc_curr_iv_raw_its) else None
            
            avg_5d_iv_key_its = self._get_config_value(ids.CFG_METRICS_CALC + ["avg_5day_iv_source_key_in_und_data"], "avg_5day_iv_tradier_approx") 
            mc_avg5d_iv_val_its = float(pd.to_numeric(mc_iv_quote_bundle_its.get(avg_5d_iv_key_its), errors='coerce')) if pd.notna(mc_iv_quote_bundle_its.get(avg_5d_iv_key_its)) else None
            process_logger_main.debug(f"IV Context for '{symbol}': Current IV: {mc_curr_iv_val_its}, Avg 5D IV: {mc_avg5d_iv_val_its}")

            # --- Orchestrate Core Analysis (Metrics, Levels, Signals) ---
            final_metric_rich_df_its, key_levels_bundle_its, signals_bundle_its, orch_error_internal_its = \
                self._orchestrate_full_analysis(
                    options_df_input=raw_options_data, # This already has raw impacts from EDP
                    underlying_data=underlying_data, underlying_price_ctx=und_price_val_its,
                    current_time_ctx=mc_time_val_its, current_iv_ctx=mc_curr_iv_val_its,
                    avg_iv_5day_ctx=mc_avg5d_iv_val_its, iv_context_dict_ctx=mc_iv_quote_bundle_its,
                    historical_ohlc_df_ctx=historical_ohlc_data,
                    avg_iv_long_term_ctx=None, # Not used in v2.3.1 ITS
                    historical_atr_normalized_vs_avg_ctx=None, # Not used in v2.3.1 ITS
                    current_symbol_ctx=symbol, expiration_calendar_data_ctx=expiration_calendar
                )
            if orch_error_internal_its and not overall_error_msg_its: 
                overall_error_msg_its = orch_error_internal_its # Capture error from orchestration
            process_logger_main.info(f"Core analysis orchestration completed for '{symbol}'. DF shape: {final_metric_rich_df_its.shape}")

            # --- ATR Calculation for Recommendation Management ---
            atr_fb_cfg_its = self._get_config_value(ids.CFG_METRICS_CALC_ATR_FALLBACK, {}) # Path from ids.py
            current_atr_value_its = get_atr(symbol, und_price_val_its, atr_fb_cfg_its, historical_ohlc_data, process_logger_main.getChild("GetATR_ITS_v231")) # type: ignore
            process_logger_main.debug(f"Calculated ATR for '{symbol}': {current_atr_value_its:.4f}")

            # --- Recommendation State Management & New Recommendation Generation ---
            active_recommendations_list_its, state_mgmt_err_its = self.update_active_recommendations_and_manage_state(
                symbol=symbol, latest_processed_options_df=final_metric_rich_df_its,
                current_key_levels_bundle=key_levels_bundle_its, current_signals_bundle=signals_bundle_its,
                current_underlying_price=und_price_val_its, current_atr=current_atr_value_its, 
                current_time=mc_time_val_its,
                iv_context_data=mc_iv_quote_bundle_its, expiration_calendar=expiration_calendar,
                historical_ohlc_data_for_targets_param=historical_ohlc_data
            )
            if state_mgmt_err_its and not overall_error_msg_its: 
                overall_error_msg_its = state_mgmt_err_its
            process_logger_main.info(f"Recommendation state management complete for '{symbol}'. Active recommendations: {len(active_recommendations_list_its)}")
            
            # Extract MSPI weights if available (set as df.attrs by mspi_orchestration_module)
            mspi_weights_applied_its = final_metric_rich_df_its.attrs.get('current_mspi_weights_applied_in_calc', {})
            if mspi_weights_applied_its:
                 process_logger_main.debug(f"MSPI weights applied during calculation for '{symbol}': {mspi_weights_applied_its}")

        except Exception as e_main_its_processing:
            # This is the main catch-all for the process_market_data_and_generate_recommendations method
            if not overall_error_msg_its: # If no specific error was already caught
                overall_error_msg_its = f"CRITICAL Unhandled Exception in ITS main processing for '{symbol}': {type(e_main_its_processing).__name__} - {str(e_main_its_processing)}"
            full_traceback_str_its = traceback.format_exc() # Get the full traceback
            process_logger_main.critical(f"{overall_error_msg_its}\nAssociated Traceback:\n{full_traceback_str_its}")
            
            # Ensure fallbacks for return bundle components
            if not isinstance(final_metric_rich_df_its, pd.DataFrame): final_metric_rich_df_its = pd.DataFrame() 
            key_levels_bundle_its = {"error": overall_error_msg_its, "all_levels_sorted_by_strength": []}
            signals_bundle_its = {"error": overall_error_msg_its, "signals_generated_count": 0}
            if not isinstance(active_recommendations_list_its, list): active_recommendations_list_its = []

        # --- Construct Final Output Bundle ---
        # Ensure all components of the bundle are well-defined even if errors occurred
        final_bundle_to_return_its = {
            "symbol": symbol, 
            "error": overall_error_msg_its, # This will contain the first critical error encountered
            "traceback": full_traceback_str_its, # Include traceback if a major exception occurred
            "processed_options_df": final_metric_rich_df_its.to_dict(orient='records') if isinstance(final_metric_rich_df_its, pd.DataFrame) and not final_metric_rich_df_its.empty else [],
            "aggregated_strike_data": [], # Placeholder for v2.3.1; proper aggregation can be added if needed
            "key_levels": key_levels_bundle_its, 
            "signals": signals_bundle_its, 
            "recommendations": active_recommendations_list_its,
            "current_mspi_weights_applied": mspi_weights_applied_its,
            "current_adaptive_historical_context_summary": self.adaptive_historical_context.get(symbol, {}).get("summary_for_bundle", {"status":"ITS_HistCtx_NotSummarized_v231"}),
            "atr_value_used_by_its": current_atr_value_its,
            "final_metric_rich_df_obj": final_metric_rich_df_its # The main DataFrame object
        }
        
        # Perform aggregation for "aggregated_strike_data" if df is valid
        if isinstance(final_metric_rich_df_its, pd.DataFrame) and not final_metric_rich_df_its.empty:
            try:
                enabled_sdags_for_agg_final = self._get_config_value(ids.CFG_DAG_METHODOLOGIES_ENABLED_ITS, [])
                agg_df_final = aggregate_for_levels(final_metric_rich_df_its.copy(), self.col_strike, enabled_sdags_for_agg_final, process_logger_main.getChild("AggFinalBundleITS_v231")) # type: ignore
                final_bundle_to_return_its["aggregated_strike_data"] = agg_df_final.to_dict(orient='records')
                process_logger_main.debug(f"Final aggregation for bundle output successful for '{symbol}'. Shape: {agg_df_final.shape}")
            except Exception as e_final_agg:
                process_logger_main.error(f"Error during final aggregation for bundle output for '{symbol}': {e_final_agg}", exc_info=True)
                final_bundle_to_return_its["aggregated_strike_data"] = [{"error": f"Final aggregation failed: {e_final_agg}"}]


        end_time_its_symbol = pytime.monotonic()
        duration_its_symbol = end_time_its_symbol - start_time_its_symbol
        process_logger_main.info(f"===== ITS (v2.3.1) COMPLETED PROCESSING SYMBOL: {symbol}. Duration: {duration_its_symbol:.3f}s. Error: '{overall_error_msg_its or 'None'}' =====")
        return final_bundle_to_return_its

    def update_active_recommendations_and_manage_state(
        self, symbol: str, latest_processed_options_df: pd.DataFrame, # This df has all metrics including MSPI
        current_key_levels_bundle: Dict[str, Any], current_signals_bundle: Dict[str, Any],
        current_underlying_price: float, current_atr: float, current_time: Optional[dt_time], # current_time from market_context
        iv_context_data: Optional[Dict[str, Any]], # From market_context.iv_and_quote_data
        expiration_calendar: Optional[List[date]], # From Tradier context
        historical_ohlc_data_for_targets_param: Optional[pd.DataFrame] # For target recalc if needed
    ) -> Tuple[List[Dict[str, Any]], Optional[str]]: # Returns (updated_active_recs, error_message)
        rec_mgr_logger_its = self.instance_logger.getChild(f"RecStateMgr.{symbol}.ITS_v231")
        rec_mgr_logger_its.info(f"--- ITS Recommendation State Management (v2.3.1) START for '{symbol}' ---")
        state_mgmt_error_msg_its: Optional[str] = None
        newly_generated_recs_its: List[Dict[str, Any]] = []

        try:
            # Symbol context switch logic for stateful recommendation management
            if self.current_symbol_being_managed != symbol:
                rec_mgr_logger_its.info(f"Symbol context changing from '{self.current_symbol_being_managed}' to '{symbol}'. Resetting active recommendations for new symbol and initializing ID counter.")
                self.active_recommendations.clear() # Clear recommendations from previous symbol
                self.current_symbol_being_managed = symbol
                # Initialize or retrieve recommendation ID counter for the new symbol
                self.recommendation_id_counter = self.recommendation_id_counters_by_symbol.get(symbol, 0) 
            
            # Ensure adaptive historical context exists for the symbol (even if simple for v2.3)
            if symbol not in self.adaptive_historical_context:
                self.adaptive_historical_context[symbol] = {
                    "recent_atr_values": deque(maxlen=self.df_history_maxlen), # For ATR trend
                    "past_flow_delta": deque(maxlen=self.df_history_maxlen), # Simplified for v2.3
                    "past_flow_gamma": deque(maxlen=self.df_history_maxlen), # Simplified for v2.3
                    "past_iv_surfaces": deque(maxlen=self.df_history_maxlen), # Simplified for v2.3
                    "recent_recommendations_log": deque(maxlen=self.df_history_maxlen * 2) # Log more recs
                }
                rec_mgr_logger_its.debug(f"Initialized basic adaptive historical context for new symbol '{symbol}'.")
            current_sym_hist_ctx_its = self.adaptive_historical_context[symbol]

            # --- Manage Existing Active Recommendations (Exits, Adjustments) ---
            # For v2.3, this uses recommendation_state_manager module if available and correctly imported.
            # It expects specific function signatures.
            if hasattr(self.rec_state_manager_module, 'manage_active_recommendations_v2_3'): # Check for a v2.3 specific manager function
                rec_mgr_logger_its.debug(f"Calling recommendation_state_manager.manage_active_recommendations_v2_3 for '{symbol}'")
                # Aggregate the latest_processed_options_df for MSPI flip checks etc.
                aggregated_df_for_rec_mgmt = aggregate_for_levels(latest_processed_options_df.copy(), self.col_strike, [], rec_mgr_logger_its.getChild("AggForRecMgmt")) # type: ignore
                
                self.active_recommendations = self.rec_state_manager_module.manage_active_recommendations_v2_3( # type: ignore
                    active_recommendations=self.active_recommendations, # Pass current list
                    current_aggregated_mspi_df=aggregated_df_for_rec_mgmt, # Pass aggregated data
                    current_price=current_underlying_price, 
                    current_atr=current_atr, 
                    current_time=current_time, # Pass current time
                    config=self.config, # Pass the full ITS config dictionary
                    log_instance=rec_mgr_logger_its.getChild("CallManageActiveRecs_v231")
                )
                rec_mgr_logger_its.info(f"Managed active recommendations for '{symbol}'. Count after management: {len(self.active_recommendations)}")
            else: 
                # Minimal fallback exit logic if the full rec_state_manager module/function is not available
                rec_mgr_logger_its.warning(f"Recommendation state manager module or 'manage_active_recommendations_v2_3' function not available for '{symbol}'. Applying minimal exit logic.")
                active_recs_post_minimal_exit_check: List[Dict[str, Any]] = []
                for rec_item in self.active_recommendations:
                    if str(rec_item.get('status', '')).startswith("EXITED_"): 
                        active_recs_post_minimal_exit_check.append(rec_item)
                        continue # Already exited
                    # Example minimal stop loss check
                    rec_sl = rec_item.get('stop_loss')
                    rec_dir_label = str(rec_item.get('direction_label','')).lower()
                    if rec_sl and pd.notna(rec_sl):
                        if (rec_dir_label == 'bullish' and current_underlying_price <= float(rec_sl)) or \
                           (rec_dir_label == 'bearish' and current_underlying_price >= float(rec_sl)):
                            rec_item['status'] = f"EXITED_STOP_LOSS_MINIMAL ({current_underlying_price:.2f})"
                            rec_item['exit_timestamp'] = datetime.now().isoformat()
                            rec_mgr_logger_its.info(f"Minimal exit for Rec ID {rec_item.get('id')}: SL hit.")
                        # No T1 check in this minimal fallback
                    active_recs_post_minimal_exit_check.append(rec_item)
                self.active_recommendations = [r for r in active_recs_post_minimal_exit_check if not str(r.get('status','')).startswith("EXITED_")]


            # --- Generate New Recommendations (using fallback_recommendation_module for v2.3) ---
            if hasattr(self.fallback_recs_module, 'get_strategy_recommendations_fallback'):
                rec_mgr_logger_its.debug(f"Calling fallback_recs_module.get_strategy_recommendations_fallback for '{symbol}'")
                # Aggregate df again if it was modified or not passed correctly
                aggregated_df_for_new_recs = aggregate_for_levels(latest_processed_options_df.copy(), self.col_strike, [], rec_mgr_logger_its.getChild("AggForNewRecs")) # type: ignore

                # Prepare S/R levels for fallback module (simplified: use all identified levels as both S & R for now)
                # The EKL module returns a dict, extract the list of levels.
                all_identified_levels_list = current_key_levels_bundle.get("all_levels_sorted_by_strength", [])
                levels_df_for_fallback = pd.DataFrame(all_identified_levels_list) if all_identified_levels_list else pd.DataFrame()
                
                newly_generated_recs_its, self.recommendation_id_counter = self.fallback_recs_module.get_strategy_recommendations_fallback( # type: ignore
                    symbol_arg_fallback=symbol,
                    mspi_df_aggregated_fallback=aggregated_df_for_new_recs, # Pass aggregated data
                    trading_signals_fallback=current_signals_bundle, # Pass signals bundle
                    support_levels_df_fallback=levels_df_for_fallback, # Pass levels
                    resistance_levels_df_fallback=levels_df_for_fallback, # Pass same levels for R
                    current_price_fallback=current_underlying_price,
                    atr_fallback=current_atr,
                    # Get recommendation and target configs using ids.py paths
                    recommendations_config_fallback=self._get_config_value(ids.CFG_STRATEGY_SETTINGS + ["recommendations"], {}),
                    targets_config_fallback=self._get_config_value(ids.CFG_STRATEGY_SETTINGS + ["targets"], {}),
                    map_score_to_stars_utility_func=map_score_to_stars, # type: ignore
                    current_recommendation_id_counter_fallback=self.recommendation_id_counter, # Pass current counter
                    log_instance=rec_mgr_logger_its.getChild("GenFallbackRecs_ITS_v231")
                )
                rec_mgr_logger_its.info(f"Generated {len(newly_generated_recs_its)} new recommendations via fallback module for '{symbol}'. Next Rec ID: {self.recommendation_id_counter}")
            else:
                rec_mgr_logger_its.warning(f"Fallback recommendation module or 'get_strategy_recommendations_fallback' function not available for '{symbol}'. No new recommendations will be generated by this path.")

            # --- Add new, non-duplicate recommendations to the active list ---
            # Get min reissue time from config using ids.py path
            min_reissue_seconds_cfg = int(self._get_config_value(ids.CFG_ATIF_MGMT_MIN_REISSUE_TIME_SEC, 300)) # Example path
            added_recs_count = 0
            for new_rec_item in newly_generated_recs_its:
                # Basic de-duplication: check strike, direction, category, and if a similar ACTIVE one was issued recently
                is_duplicate_rec = False
                for active_rec_item in self.active_recommendations:
                    if active_rec_item.get(self.col_strike) == new_rec_item.get(self.col_strike) and \
                       str(active_rec_item.get('direction_label','')).lower() == str(new_rec_item.get('direction_label','')).lower() and \
                       active_rec_item.get('category','') == new_rec_item.get('category','') and \
                       str(active_rec_item.get('status','')).startswith("ACTIVE_"):
                        try:
                            active_rec_ts_str = str(active_rec_item.get("timestamp", "1970-01-01T00:00:00Z")).replace("Z","+00:00")
                            active_rec_dt = datetime.fromisoformat(active_rec_ts_str)
                            if (datetime.now(active_rec_dt.tzinfo) - active_rec_dt).total_seconds() < min_reissue_seconds_cfg:
                                is_duplicate_rec = True; break
                        except ValueError: # Error parsing timestamp
                            rec_mgr_logger_its.warning(f"Could not parse timestamp '{active_rec_item.get('timestamp')}' for active rec {active_rec_item.get('id')} during duplication check.")
                
                if not is_duplicate_rec:
                    self.active_recommendations.append(new_rec_item)
                    added_recs_count += 1
            if added_recs_count > 0:
                rec_mgr_logger_its.info(f"Added {added_recs_count} new, non-duplicate recommendations to active list for '{symbol}'.")
            
            # Store the updated ID counter for this symbol
            self.recommendation_id_counters_by_symbol[symbol] = self.recommendation_id_counter

            # --- Update simple historical context for v2.3 (e.g., ATR) ---
            if "recent_atr_values" in current_sym_hist_ctx_its and isinstance(current_sym_hist_ctx_its["recent_atr_values"], deque):
                current_sym_hist_ctx_its["recent_atr_values"].appendleft(current_atr) # Add to left (newest)
            # Update summary (can be expanded)
            current_sym_hist_ctx_its["summary_for_bundle"] = {
                "last_atr": current_atr, 
                "last_underlying_price": current_underlying_price,
                "last_update_ts_ctx": datetime.now().isoformat()
            }
            rec_mgr_logger_its.debug(f"Updated historical context for '{symbol}' with ATR: {current_atr:.4f}")

        except Exception as e_state_mgmt_main:
            state_mgmt_error_msg_its = f"CRITICAL unhandled error during recommendation state management for '{symbol}': {type(e_state_mgmt_main).__name__} - {e_state_mgmt_main}"
            rec_mgr_logger_its.critical(state_mgmt_error_msg_its, exc_info=True)
            # Ensure active_recommendations is still a list even on error
            if not isinstance(self.active_recommendations, list): self.active_recommendations = []

        rec_mgr_logger_its.info(f"--- ITS Recommendation State Management (v2.3.1) END for '{symbol}'. Active Recommendations: {len(self.active_recommendations)}. Error: {state_mgmt_error_msg_its or 'None'} ---")
        return self.active_recommendations.copy(), state_mgmt_error_msg_its # Return a copy

# --- Standalone Test Block ---
if __name__ == '__main__':
    # Configure a dedicated logger for the standalone test, separate from module logger if needed
    if not logging.getLogger("ITS_Standalone_Test_v231").hasHandlers():
        test_logger_its_main = logging.getLogger("ITS_Standalone_Test_v231")
        test_handler_stdout_its = logging.StreamHandler(sys.stdout)
        test_formatter_detailed_its = logging.Formatter("[%(levelname)s] (%(name)s:%(funcName)s:%(lineno)d) %(asctime)s - %(message)s")
        test_handler_stdout_its.setFormatter(test_formatter_detailed_its)
        test_logger_its_main.addHandler(test_handler_stdout_its)
        test_logger_its_main.propagate = False 
        test_logger_its_main.setLevel(logging.DEBUG)
    else:
        test_logger_its_main = logging.getLogger("ITS_Standalone_Test_v231")

    # Also set the main ITS module logger to DEBUG for this test run
    logging.getLogger("core_analytics.integrated_strategies_v2").setLevel(logging.DEBUG)
    for handler_its_mod in logging.getLogger("core_analytics.integrated_strategies_v2").handlers:
        if handler_its_mod: handler_its_mod.setLevel(logging.DEBUG)

    test_logger_its_main.info(f"--- Running IntegratedTradingSystem Standalone Test (Version: EOTS_ITS_v2.3.1_Canon_IDS_Sync_Logging) ---")
    
    # Determine path to config_v2.json relative to this script, then project root
    script_dir_its_test = os.path.dirname(os.path.abspath(__file__))
    project_root_dir_its_test = os.path.dirname(script_dir_its_test) 
    test_config_file_path_its = os.path.join(project_root_dir_its_test, "config_v2.json")
    test_logger_its_main.info(f"Attempting to use config file for ITS test: '{test_config_file_path_its}'")

    if not os.path.exists(test_config_file_path_its):
        test_logger_its_main.critical(f"Test config file '{test_config_file_path_its}' NOT FOUND. ITS will use internal defaults, which might be insufficient.")
        test_config_file_path_its = None # Signal to ITS to use its internal default config logic

    try:
        # Instantiate ITS
        its_test_instance = IntegratedTradingSystem(config_path=test_config_file_path_its, log_level="DEBUG")
        test_logger_its_main.info(f"ITS Test Instance Initialized. Using Dummy Modules (if any critical import failed): {_CORE_IMPORTS_SUCCESSFUL_ITS_V231 == False}")

        # Prepare Sample Data (using ids.py constants for DataFrame columns)
        sample_symbol_its_test = "TESTSYM_ITS_V231"
        sample_current_price_its_test = 150.75
        sample_fetch_ts_its_test = datetime.now().isoformat()
        
        # Use ids.py for column names in sample data generation
        strike_col_name_sample = ids.COL_STRIKE if IDS_IMPORTED_SUCCESSFULLY_EDP else "strike_price" # Assuming EDP's ids load status for sample data
        opt_kind_col_name_sample = ids.COL_OPT_KIND if IDS_IMPORTED_SUCCESSFULLY_EDP else "opt_kind"
        # ... (and so on for all columns used in sample data)

        sample_options_data_list_its = []
        for strike_offset_val_its in [-10, -5, 0, 5, 10]:
            for opt_k_val_its in ['call', 'put']:
                contract_data_its = {
                    strike_col_name_sample: sample_current_price_its_test + strike_offset_val_its,
                    opt_kind_col_name_sample: opt_k_val_its,
                    (ids.COL_OPTION_SYMBOL if IDS_IMPORTED_SUCCESSFULLY_EDP else "symbol"): f".{sample_symbol_its_test}{datetime.now().strftime('%y%m%d')}{'C' if opt_k_val_its=='call' else 'P'}{int(sample_current_price_its_test + strike_offset_val_its)}000",
                    (ids.COL_UNDERLYING_SYMBOL_CHAIN if IDS_IMPORTED_SUCCESSFULLY_EDP else "underlying_symbol"): sample_symbol_its_test,
                    (ids.COL_PRICE_OPTION_CONTRACT if IDS_IMPORTED_SUCCESSFULLY_EDP else "price"): round(np.random.uniform(0.1, 5.0), 2),
                    (ids.COL_DELTA_CONTRACT if IDS_IMPORTED_SUCCESSFULLY_EDP else "delta"): round(np.random.uniform(-1,1) if opt_k_val_its == 'put' else np.random.uniform(0,1), 4),
                    (ids.COL_GAMMA_CONTRACT if IDS_IMPORTED_SUCCESSFULLY_EDP else "gamma"): round(np.random.uniform(0.01, 0.1), 4),
                    (ids.COL_VEGA_CONTRACT if IDS_IMPORTED_SUCCESSFULLY_EDP else "vega"): round(np.random.uniform(0.01, 0.2), 4),
                    (ids.COL_THETA_CONTRACT if IDS_IMPORTED_SUCCESSFULLY_EDP else "theta"): round(np.random.uniform(-0.1, -0.01), 4),
                    (ids.COL_OI_OPTION_CONTRACT if IDS_IMPORTED_SUCCESSFULLY_EDP else "oi"): np.random.randint(10, 1000),
                    (ids.COL_VOLUME_OPTION_CONTRACT if IDS_IMPORTED_SUCCESSFULLY_EDP else "volm"): np.random.randint(1, 200),
                    (ids.COL_GXOI_CONTRACT if IDS_IMPORTED_SUCCESSFULLY_EDP else "gxoi"): round(np.random.uniform(1e5, 1e7) * (1 if np.random.rand() > 0.3 else -1), 2),
                    (ids.COL_DXOI_CONTRACT if IDS_IMPORTED_SUCCESSFULLY_EDP else "dxoi"): round(np.random.uniform(1e4, 1e6) * (1 if opt_k_val_its == 'call' else -1), 2),
                    # Include raw impact columns as EDP would provide them
                    (ids.COL_IMPACT_DELTA_RAW if IDS_IMPORTED_SUCCESSFULLY_EDP else "delta_impact"): round(np.random.uniform(-1e5, 1e5),0),
                    (ids.COL_IMPACT_GAMMA_RAW if IDS_IMPORTED_SUCCESSFULLY_EDP else "gamma_impact"): round(np.random.uniform(-1e4, 1e4),0),
                    # Add other necessary columns that EDP would pass to ITS
                    (ids.COL_CURRENT_PRICE_EDP if IDS_IMPORTED_SUCCESSFULLY_EDP else "current_price"): sample_current_price_its_test,
                    (ids.COL_EXPIRATION_DATE if IDS_IMPORTED_SUCCESSFULLY_EDP else "expiration_date"): (date.today() + timedelta(days=np.random.randint(5,60))).isoformat(),

                }
                sample_options_data_list_its.append(contract_data_its)
        sample_raw_options_df_its = pd.DataFrame(sample_options_data_list_its)
        test_logger_its_main.debug(f"Generated sample raw_options_data for ITS test. Shape: {sample_raw_options_df_its.shape}")

        sample_underlying_data_its = {
            (ids.CV_UND_PARAM_PRICE if IDS_IMPORTED_SUCCESSFULLY_EDP else "price"): sample_current_price_its_test,
            (ids.CV_UND_PARAM_FETCH_TIMESTAMP if IDS_IMPORTED_SUCCESSFULLY_EDP else "fetch_timestamp"): sample_fetch_ts_its_test,
            (ids.CV_UND_PARAM_VOLATILITY if IDS_IMPORTED_SUCCESSFULLY_EDP else "volatility"): round(np.random.uniform(0.1, 0.3), 4)
        }

        sample_market_context_its = {
            "current_time": datetime.now().time(),
            "iv_and_quote_data": {
                "current_iv": round(np.random.uniform(0.15,0.25),4), 
                "avg_5day_iv_tradier_approx": round(np.random.uniform(0.14,0.23),4),
                (ids.CV_UND_PARAM_IV_PERCENTILE_30D if IDS_IMPORTED_SUCCESSFULLY_EDP else "iv_percentile_30d"): round(np.random.uniform(0,1),2)
            }
        }
        sample_ohlc_df_its = pd.DataFrame({
            'date': pd.to_datetime([datetime.now() - timedelta(days=i) for i in range(30, 0, -1)]), # 30 days of history
            'open': np.random.uniform(sample_current_price_its_test-5, sample_current_price_its_test-2, 30), 
            'high': np.random.uniform(sample_current_price_its_test, sample_current_price_its_test+3, 30), 
            'low': np.random.uniform(sample_current_price_its_test-6, sample_current_price_its_test-1, 30), 
            'close': np.random.uniform(sample_current_price_its_test-3, sample_current_price_its_test+2, 30), 
            'volume': np.random.randint(1e6,5e7,30)
        })
        sample_exp_calendar_its = [date.today() + timedelta(days=d) for d in [5, 12, 19, 26, 50, 80]]
        test_logger_its_main.debug("Sample underlying_data, market_context, ohlc_df, and expiration_calendar prepared for ITS test.")

        test_logger_its_main.info(f"Calling ITS process_market_data_and_generate_recommendations for test symbol: {sample_symbol_its_test}")
        its_test_results_bundle = its_test_instance.process_market_data_and_generate_recommendations(
            symbol=sample_symbol_its_test,
            raw_options_data=sample_raw_options_df_its,
            underlying_data=sample_underlying_data_its,
            market_context=sample_market_context_its,
            historical_ohlc_data=sample_ohlc_df_its,
            expiration_calendar=sample_exp_calendar_its
        )

        test_logger_its_main.info("--- IntegratedTradingSystem Standalone Test (v2.3.1) Processing Results ---")
        if not its_test_results_bundle: 
            test_logger_its_main.error("ITS Processing returned NO results (empty dictionary). This is unexpected.")
        
        test_logger_its_main.info(f"  --- Results for Symbol: {its_test_results_bundle.get('symbol')} ---")
        test_logger_its_main.info(f"    ITS Reported Error: {its_test_results_bundle.get('error')}")
        test_logger_its_main.info(f"    ITS Reported Traceback: {'Present' if its_test_results_bundle.get('traceback') else 'None'}")
        
        final_df_obj_its_test = its_test_results_bundle.get("final_metric_rich_df_obj")
        if isinstance(final_df_obj_its_test, pd.DataFrame):
            test_logger_its_main.info(f"    'final_metric_rich_df_obj' DataFrame Shape: {final_df_obj_its_test.shape}")
            if not final_df_obj_its_test.empty:
                test_logger_its_main.info(f"      Columns: {final_df_obj_its_test.columns.tolist()}")
                test_logger_its_main.debug(f"      Sample of final_metric_rich_df_obj (head 1):\n{final_df_obj_its_test.head(1)}")
        else:
            test_logger_its_main.warning(f"    'final_metric_rich_df_obj' is NOT a DataFrame. Type: {type(final_df_obj_its_test)}")
        
        processed_data_dict_its_test = its_test_results_bundle.get("processed_options_df", []) # This is list of dicts
        test_logger_its_main.debug(f"    Processed Options Data (list of dicts) Count: {len(processed_data_dict_its_test)}")
        key_levels_test = its_test_results_bundle.get("key_levels", {})
        test_logger_its_main.debug(f"    Key Levels Bundle Keys: {list(key_levels_test.keys())}, Levels Count: {len(key_levels_test.get('all_levels_sorted_by_strength',[]))}")
        signals_test = its_test_results_bundle.get("signals", {})
        test_logger_its_main.debug(f"    Signals Bundle Keys: {list(signals_test.keys())}, Generated Count: {signals_test.get('signals_generated_count','N/A')}")
        recommendations_test = its_test_results_bundle.get("recommendations", [])
        test_logger_its_main.info(f"    Recommendations Generated Count: {len(recommendations_test)}")
        if recommendations_test:
            test_logger_its_main.debug(f"      Sample Recommendation: {recommendations_test[0] if recommendations_test else 'None'}")

        test_logger_its_main.info("--- IntegratedTradingSystem Standalone Test (v2.3.1) Completed ---")

    except Exception as e_standalone_main_its_v231_exec:
        test_logger_its_main.critical(f"ITS Standalone Test SCRIPT CRASHED UNEXPECTEDLY: {e_standalone_main_its_v231_exec}", exc_info=True)

