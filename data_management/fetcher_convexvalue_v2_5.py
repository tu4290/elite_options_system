# enhanced_data_fetcher_v2_rewrite.py
# (Elite Options Trading System - ConvexValue Data Fetcher)
# Version 3.0.0 - Full Rewrite for Enhanced Robustness, Error Handling, and Clarity

# Standard Library Imports
import os
import sys
import time as pytime # Renamed to avoid conflict
import logging
import json
import random
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional, Tuple, Union, Callable
from functools import wraps

# Third-Party Imports
import pandas as pd
import numpy as np
import requests # For specific exception type hinting in retry decorator

# Specific Third-Party Imports (API Wrapper)
try:
    from convexlib.api import ConvexApi
    CONVEXLIB_AVAILABLE = True
    _api_import_error_cv_rewrite = None
except ImportError as import_error_cv_rewrite:
    print(f"CRITICAL ERROR (Fetcher Rewrite): Could not import ConvexApi: {import_error_cv_rewrite}. Ensure 'convexlib' is installed. Fetcher will be NON-FUNCTIONAL.")
    CONVEXLIB_AVAILABLE = False
    _api_import_error_cv_rewrite = import_error_cv_rewrite
    class ConvexApi: pass # Dummy class for type hinting if import fails
except Exception as general_import_err_cv_rewrite:
    print(f"CRITICAL ERROR (Fetcher Rewrite): An unexpected error occurred during ConvexApi import: {general_import_err_cv_rewrite}. Fetcher will be NON-FUNCTIONAL.")
    CONVEXLIB_AVAILABLE = False
    _api_import_error_cv_rewrite = general_import_err_cv_rewrite
    class ConvexApi: pass

# --- Logging Setup ---
if not logging.getLogger(__name__).hasHandlers(): # Fallback if main app doesn't configure
    _cv_fetcher_log_formatter_rewrite = logging.Formatter(
        '[%(levelname)s] (%(name)s:%(lineno)d) %(asctime)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    _cv_fetcher_log_handler_rewrite = logging.StreamHandler(sys.stdout)
    _cv_fetcher_log_handler_rewrite.setFormatter(_cv_fetcher_log_formatter_rewrite)
    logging.getLogger(__name__).addHandler(_cv_fetcher_log_handler_rewrite)
    logging.getLogger(__name__).setLevel(logging.INFO)
logger = logging.getLogger(__name__)

if not CONVEXLIB_AVAILABLE:
    logger.critical(f"Convexlib is not available (Import Error: {_api_import_error_cv_rewrite}). ConvexValueDataFetcher (Rewrite) cannot function.")

# --- Constants & Default Configuration ---
# These parameter lists define what the fetcher requests.
# The parsing logic will rely on the order and number of these parameters matching the API's response.
# NOTE: These lists should be kept in sync with the ConvexValue API capabilities and EOTS system requirements.
#       Consider moving these to the configuration file (config_v2.json) for easier updates.
CV_UNDERLYING_DEFAULT_PARAMS: List[str] = [
    "price", "volatility", "day_volume", "call_gxoi", "put_gxoi",
    "gammas_call_buy", "gammas_call_sell", "gammas_put_buy", "gammas_put_sell",
    "deltas_call_buy", "deltas_call_sell", "deltas_put_buy", "deltas_put_sell",
    "vegas_call_buy", "vegas_call_sell", "vegas_put_buy", "vegas_put_sell",
    "thetas_call_buy", "thetas_call_sell", "thetas_put_buy", "thetas_put_sell",
    "call_vxoi", "put_vxoi", "value_bs", "volm_bs", "deltas_buy", "deltas_sell",
    "vegas_buy", "vegas_sell", "thetas_buy", "thetas_sell", "volm_call_buy",
    "volm_put_buy", "volm_call_sell", "volm_put_sell", "value_call_buy",
    "value_put_buy", "value_call_sell", "value_put_sell", "vflowratio",
    "dxoi", "gxoi", "vxoi", "txoi", "call_dxoi", "put_dxoi", "charmxoi", "vannaxoi", "vommaxoi",
    # Consider adding IV percentiles directly if ConvexValue API supports them efficiently
    # "iv_percentile_30d", "iv_percentile_60d", etc.
]
logger.info(f"ConvexValueFetcher (Rewrite): Default UNDERLYING_PARAMS set to {len(CV_UNDERLYING_DEFAULT_PARAMS)} items.")

CV_OPTIONS_CHAIN_DEFAULT_PARAMS: List[str] = [
  "price", "volatility", "multiplier", "oi", "delta", "gamma", "theta", "vega",
  "vanna", "vomma", "charm", "dxoi", "gxoi", "vxoi", "txoi", "vannaxoi", "vommaxoi", "charmxoi",
  "dxvolm", "gxvolm", "vxvolm", "txvolm", "vannaxvolm", "vommaxvolm", "charmxvolm",
  "value_bs", "volm_bs", "deltas_buy", "deltas_sell", "gammas_buy", "gammas_sell",
  "vegas_buy", "vegas_sell", "thetas_buy", "thetas_sell",
  "valuebs_5m", "volmbs_5m", "valuebs_15m", "volmbs_15m",
  "valuebs_30m", "volmbs_30m", "valuebs_60m", "volmbs_60m",
  "volm", "volm_buy", "volm_sell", "value_buy", "value_sell",
  "bid_price", "ask_price", "bid_size", "ask_size"
]
logger.info(f"ConvexValueFetcher (Rewrite): Default OPTIONS_CHAIN_PARAMS set to {len(CV_OPTIONS_CHAIN_DEFAULT_PARAMS)} items.")

# Columns that should be treated as numeric in the options chain DataFrame
CV_NUMERIC_COLUMNS_OPTIONS_REWRITE: List[str] = [
    'strike', 'price', 'volatility', 'multiplier', 'oi', 'delta', 'gamma', 'theta', 'vega',
    'vanna', 'vomma', 'charm', 'dxoi', 'gxoi', 'vxoi', 'txoi', 'vannaxoi', 'vommaxoi',
    'charmxoi', 'dxvolm', 'gxvolm', 'vxvolm', 'txvolm',
    'vannaxvolm', 'vommaxvolm', 'charmxvolm',
    'value_bs', 'volm_bs', 'deltas_buy', 'deltas_sell',
    'gammas_buy', 'gammas_sell', 'vegas_buy', 'vegas_sell', 'thetas_buy', 'thetas_sell',
    'valuebs_5m', 'volmbs_5m', 'valuebs_15m', 'volmbs_15m',
    'valuebs_30m', 'volmbs_30m', 'valuebs_60m', 'volmbs_60m',
    'volm', 'volm_buy', 'volm_sell', 'value_buy', 'value_sell',
    'bid_price', 'ask_price', 'bid_size', 'ask_size'
]
# For underlying, most params are numeric. Exceptions could be 'symbol', 'last_trade_time', etc.
CV_NUMERIC_COLUMNS_UNDERLYING_REWRITE: List[str] = [
    item for item in CV_UNDERLYING_DEFAULT_PARAMS if item not in ['symbol'] # Example
]


DEFAULT_CV_FETCHER_SETTINGS_REWRITE = {
    "email_env_var": "CONVEX_EMAIL",
    "password_env_var": "CONVEX_PASSWORD",
    "email_direct": "YOUR_CV_EMAIL_PLACEHOLDER_REWRITE",
    "password_direct": "YOUR_CV_PASSWORD_PLACEHOLDER_REWRITE",
    "retry_config": {
        "max_retries": 3,
        "base_delay_seconds": 1.2, # Slightly adjusted
        "max_delay_seconds": 10.0, # Slightly adjusted
        "jitter": True
    },
    "inter_call_delay_seconds": 0.30, # Slightly adjusted
    "default_dte_range": [0, 1, 7, 14, 30, 45, 60], # Expanded default
    "default_price_range_pct": 0.12, # Slightly adjusted, assuming it's a percentage like 12 for 12%
    "underlying_params_to_fetch": CV_UNDERLYING_DEFAULT_PARAMS, # Use the new constant
    "options_chain_params_to_fetch": CV_OPTIONS_CHAIN_DEFAULT_PARAMS # Use the new constant
}

# --- Retry Decorator (More specific to ConvexLib's potential errors) ---
def convexvalue_retry_api_call_rewrite(
    retries_param: int,
    base_delay_seconds_param: float,
    max_delay_seconds_param: float,
    jitter_param: bool = True,
    logger_instance_param: Optional[logging.Logger] = None,
    func_name_override_param: Optional[str] = None
):
    log_cv_dec = logger_instance_param if logger_instance_param else logging.getLogger(f"{__name__}.convexvalue_retry_api_call_rewrite")

    def decorator(func: Callable):
        actual_func_name_cv_dec = func_name_override_param if func_name_override_param else func.__name__
        @wraps(func)
        def wrapper(*args, **kwargs):
            attempts_cv_dec = 0
            current_delay_cv_dec = base_delay_seconds_param
            last_exception_cv_dec: Optional[BaseException] = None

            while attempts_cv_dec < retries_param:
                try:
                    return func(*args, **kwargs)
                except (requests.exceptions.RequestException, requests.exceptions.Timeout, ConnectionError,
                        ConvexApi.MaxRetriesExceeded, ConvexApi.CVError) as e_cv_api: # Common API/Network errors
                    attempts_cv_dec += 1
                    last_exception_cv_dec = e_cv_api
                    log_cv_dec.warning(
                        f"ConvexValue API Error in {actual_func_name_cv_dec} (Attempt {attempts_cv_dec}/{retries_param}): "
                        f"{type(e_cv_api).__name__} - {str(e_cv_api)[:250]}"
                    )
                    if attempts_cv_dec < retries_param:
                        sleep_time_actual_cv_dec = current_delay_cv_dec + (random.uniform(0, current_delay_cv_dec * 0.15) if jitter_param else 0) # Increased jitter range slightly
                        log_cv_dec.info(f"Retrying {actual_func_name_cv_dec} in {sleep_time_actual_cv_dec:.2f} seconds...")
                        pytime.sleep(sleep_time_actual_cv_dec)
                        current_delay_cv_dec = min(current_delay_cv_dec * 2.0, max_delay_seconds_param) # Slightly more aggressive backoff
                    else:
                        log_cv_dec.error(f"Max retries ({retries_param}) reached for {actual_func_name_cv_dec} due to API/Network error.")
                        if isinstance(last_exception_cv_dec, Exception):
                             raise last_exception_cv_dec from e_cv_api
                        else:
                             raise RuntimeError(f"Max retries reached for {actual_func_name_cv_dec}, last error: {last_exception_cv_dec}") from e_cv_api
                except Exception as e_cv_gen:
                    log_cv_dec.error(f"Unexpected non-API error during {actual_func_name_cv_dec} attempt {attempts_cv_dec + 1}: {type(e_cv_gen).__name__} - {e_cv_gen}", exc_info=True)
                    # Depending on the error, might not be worth retrying. Re-raise immediately.
                    raise # Re-raise other unexpected errors immediately
            # This part should ideally not be reached if the loop correctly re-raises on final attempt failure.
            log_cv_dec.critical(f"Exited retry loop for {actual_func_name_cv_dec} unexpectedly. This indicates a logic flaw in the decorator. Raising last known error or RuntimeError.")
            if last_exception_cv_dec and isinstance(last_exception_cv_dec, Exception):
                raise last_exception_cv_dec
            raise RuntimeError(f"Retry loop for {actual_func_name_cv_dec} exited without success or explicit error propagation.")
        return wrapper
    return decorator


class ConvexValueDataFetcher:
    """
    Handles data fetching from the ConvexValue API for EOTS.
    Version 3.0.0: Full Rewrite for Enhanced Robustness, Error Handling, and Clarity.
    """
    def __init__(self, cv_settings: Optional[Dict[str, Any]] = None, main_system_log_level: str = "INFO"):
        self.logger = logger.getChild(self.__class__.__name__)
        self.initialization_failed: bool = False
        self.api: Optional[ConvexApi] = None
        self.settings: Dict[str, Any] = {} # Will be populated by _load_settings

        self._load_settings(cv_settings or {}, main_system_log_level)

        if not CONVEXLIB_AVAILABLE:
            self.logger.critical("Convexlib library is not available. ConvexValueDataFetcher cannot function.")
            self.initialization_failed = True # Critical failure
            return # Stop initialization

        if self.initialization_failed: # Check if _load_settings already set it due to creds
            self.logger.critical("Fetcher initialization failed during settings load (likely missing credentials). API will be unavailable.")
            return

        self._connect_to_api() # Attempt connection, may set initialization_failed

        self.logger.info(f"ConvexValueDataFetcher V{self.get_version()} initialized. API Connected: {self.api is not None and not self.initialization_failed}")

    def _load_settings(self, user_cv_settings: Dict[str, Any], main_system_log_level: str):
        self.logger.debug("Loading ConvexValueDataFetcher configurations (Rewrite)...")
        
        # Start with a deep copy of defaults, then merge user settings
        self.settings = json.loads(json.dumps(DEFAULT_CV_FETCHER_SETTINGS_REWRITE))
        for key_major, val_major in user_cv_settings.items():
            if key_major in self.settings and isinstance(self.settings[key_major], dict) and isinstance(val_major, dict):
                self.settings[key_major].update(val_major) # Merge dictionaries
            else:
                self.settings[key_major] = val_major # Overwrite/add other types

        self.email_env_var = str(self.settings["email_env_var"])
        self.password_env_var = str(self.settings["password_env_var"])
        self.email = os.getenv(self.email_env_var)
        self.password = os.getenv(self.password_env_var)

        if not (self.email and self.password):
            self.logger.warning(f"CV API credentials not in ENV VARS ('{self.email_env_var}', PW REDACTED). Trying direct config.")
            self.email = str(self.settings["email_direct"])
            self.password = str(self.settings["password_direct"])
            if self.email and self.password and \
               self.email != DEFAULT_CV_FETCHER_SETTINGS_REWRITE["email_direct"] and \
               self.password != DEFAULT_CV_FETCHER_SETTINGS_REWRITE["password_direct"]:
                self.logger.info("Loaded CV API credentials from direct config settings.")
            else:
                self.logger.error("CV API credentials NOT found in ENV VARS or valid direct config. Fetcher will be non-functional.")
                self.initialization_failed = True; self.email, self.password = None, None # Critical

        retry_cfg = self.settings["retry_config"]
        self.max_retries = int(retry_cfg.get("max_retries", 3))
        self.base_retry_delay = float(retry_cfg.get("base_delay_seconds", 1.0))
        self.max_retry_delay = float(retry_cfg.get("max_delay_seconds", 8.0))
        self.retry_jitter = bool(retry_cfg.get("jitter", True))

        self.inter_call_delay = float(self.settings.get("inter_call_delay_seconds", 0.25))
        self.default_dte_range = self.settings.get("default_dte_range", [0,1,7,14,30])
        self.default_price_range_pct = float(self.settings.get("default_price_range_pct", 0.10)) # Interpreted as 0.10 for 10% by API
        
        # Use params from settings if provided, else the module-level defaults
        self.underlying_params_to_fetch = self.settings.get("underlying_params_to_fetch", list(CV_UNDERLYING_DEFAULT_PARAMS))
        self.options_chain_params_to_fetch = self.settings.get("options_chain_params_to_fetch", list(CV_OPTIONS_CHAIN_DEFAULT_PARAMS))
        
        # Ensure these are lists and not accidentally something else from config
        if not isinstance(self.underlying_params_to_fetch, list):
            self.logger.warning(f"underlying_params_to_fetch from config was not a list (type: {type(self.underlying_params_to_fetch)}). Using default.")
            self.underlying_params_to_fetch = list(CV_UNDERLYING_DEFAULT_PARAMS)
        if not isinstance(self.options_chain_params_to_fetch, list):
            self.logger.warning(f"options_chain_params_to_fetch from config was not a list (type: {type(self.options_chain_params_to_fetch)}). Using default.")
            self.options_chain_params_to_fetch = list(CV_OPTIONS_CHAIN_DEFAULT_PARAMS)


        try:
            effective_log_level = getattr(logging, str(main_system_log_level).upper())
            self.logger.setLevel(effective_log_level)
            logging.getLogger(f"{__name__}.convexvalue_retry_api_call_rewrite").setLevel(effective_log_level)
            self.logger.info(f"ConvexValueFetcher (Rewrite) logger level set to: {main_system_log_level.upper()}")
        except (AttributeError, ValueError):
            self.logger.warning(f"Invalid log level '{main_system_log_level}' provided. Fetcher (Rewrite) defaulting to INFO.")
            self.logger.setLevel(logging.INFO)
            logging.getLogger(f"{__name__}.convexvalue_retry_api_call_rewrite").setLevel(logging.INFO)

    def _connect_to_api(self):
        if self.initialization_failed: # Already failed (e.g. missing creds)
            self.logger.error("Cannot connect to ConvexValue API: Fetcher initialization previously failed.")
            self.api = None
            return
        if not CONVEXLIB_AVAILABLE: # Should have been caught earlier, but double check
            self.logger.error("Cannot connect to ConvexValue API: convexlib is unavailable.")
            self.api = None; self.initialization_failed = True
            return

        @convexvalue_retry_api_call_rewrite( # Use the rewritten decorator
            retries_param=self.max_retries, base_delay_seconds_param=self.base_retry_delay,
            max_delay_seconds_param=self.max_retry_delay, jitter_param=self.retry_jitter,
            logger_instance_param=self.logger, func_name_override_param="_connect_cv_api_attempt_rewrite"
        )
        def _connect_attempt_internal():
            # Ensure email and password are not None before attempting connection
            if not self.email or not self.password:
                self.logger.error("API email or password is not set. Cannot attempt connection.")
                raise ValueError("API credentials not set for ConvexApi connection.") # This will be caught by retry

            self.logger.info(f"Attempting ConvexValue API connection for user: {self.email[:3]}***...")
            # ConvexApi constructor itself might raise exceptions on auth failure or network issues
            api_instance = ConvexApi(self.email, self.password)
            # Perform a lightweight test call to confirm API is responsive and auth is valid
            # This helps catch issues not raised by the constructor itself.
            # Using a common, small symbol for test.
            test_symbol_connect = "SPY"
            test_params_connect = ["price"] # Minimal data
            self.logger.debug(f"Performing lightweight test call to ConvexAPI with symbol '{test_symbol_connect}' and params {test_params_connect} to verify connection...")
            api_instance.get_und([test_symbol_connect], params=test_params_connect)
            self.logger.debug("ConvexAPI lightweight test call successful.")
            return api_instance

        try:
            self.api = _connect_attempt_internal()
            if self.api:
                self.logger.info("ConvexValue API instance created and connection appears successful.")
                self.initialization_failed = False # Explicitly mark as not failed
            else: # Should ideally be caught by an exception from the retry decorator
                self.logger.error("ConvexValue API connection failed after retries (_connect_attempt_internal returned None). This is unexpected.")
                self.initialization_failed = True
        except Exception as connect_err:
            self.logger.error(f"ConvexValue API initial connection failed definitively: {type(connect_err).__name__} - {connect_err}", exc_info=True)
            self.api = None
            self.initialization_failed = True

    def _parse_cv_underlying_response(self, symbol: str, raw_response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parses the raw dictionary response from ConvexApi.get_und() for a single symbol.
        More robust parsing and error handling.
        """
        symbol_upper = symbol.upper()
        fetch_timestamp = datetime.now().isoformat()
        # Use the instance-specific list of parameters expected
        params_requested = self.underlying_params_to_fetch

        parsed_result: Dict[str, Any] = {
            'symbol': symbol_upper,
            'error': None,
            'fetch_timestamp': fetch_timestamp
        }
        # Initialize all expected params with None for complete output structure
        for param_name in params_requested:
            parsed_result[param_name] = None

        if not isinstance(raw_response, dict):
            msg = f"Invalid raw_response format for {symbol_upper}. Expected dict, got {type(raw_response)}."
            self.logger.error(msg); parsed_result['error'] = msg; return parsed_result

        data_container = raw_response.get('data')
        symbol_data_row_list: Optional[List[Any]] = None

        # API can return data in slightly different nested list structures
        if isinstance(data_container, list) and len(data_container) > 0:
            first_element = data_container[0]
            if isinstance(first_element, list) and len(first_element) > 0:
                # Structure: [[['SYMB', v1, v2, ...]]]
                if isinstance(first_element[0], list) and len(first_element[0]) > 0 and \
                   isinstance(first_element[0][0], str) and first_element[0][0].upper() == symbol_upper:
                    symbol_data_row_list = first_element[0]
                    self.logger.debug(f"Underlying Parse ({symbol_upper}): Matched structure [[['{symbol_upper}', ...]]]")
                # Structure: [['SYMB', v1, v2, ...]]
                elif isinstance(first_element[0], str) and first_element[0].upper() == symbol_upper:
                    symbol_data_row_list = first_element
                    self.logger.debug(f"Underlying Parse ({symbol_upper}): Matched structure [['{symbol_upper}', ...]]]")
        
        if symbol_data_row_list is None:
            msg = f"Underlying data for {symbol_upper} not found or in unexpected format within 'data' container. Raw data_container: {str(data_container)[:300]}"
            self.logger.warning(msg)
            parsed_result['error'] = msg
            return parsed_result
        
        # The actual values start from the second element (index 1), symbol name is at index 0
        if len(symbol_data_row_list) < 1: # Should have at least symbol name
            msg = f"Underlying data row for {symbol_upper} is too short (len {len(symbol_data_row_list)}). Expected at least symbol name. Content: {str(symbol_data_row_list)[:100]}"
            self.logger.error(msg)
            parsed_result['error'] = msg
            return parsed_result

        actual_values_from_api = symbol_data_row_list[1:]
        num_actual_values = len(actual_values_from_api)
        num_expected_params = len(params_requested)

        if num_actual_values != num_expected_params:
            param_mismatch_msg = (
                f"Underlying Parse ({symbol_upper}): Positional mapping issue. "
                f"Requested {num_expected_params} params (e.g., {params_requested[:3]}...), API returned {num_actual_values} values. "
                f"Data may be misaligned or incomplete. Raw values: {str(actual_values_from_api)[:200]}"
            )
            self.logger.warning(param_mismatch_msg)
            parsed_result['error'] = f"{parsed_result.get('error', '')}. {param_mismatch_msg}".strip('. ')

        # Parse available values, up to the minimum of expected or actual count
        max_len_to_parse = min(num_actual_values, num_expected_params)
        for i in range(max_len_to_parse):
            param_name = params_requested[i]
            raw_val = actual_values_from_api[i]
            try:
                # Use the predefined list of numeric columns for underlying data
                if param_name in CV_NUMERIC_COLUMNS_UNDERLYING_REWRITE:
                    # pd.to_numeric is robust: handles None, strings that are numbers, actual numbers
                    num_val = pd.to_numeric(raw_val, errors='coerce')
                    # Ensure it's float or None (for np.nan)
                    parsed_result[param_name] = float(num_val) if pd.notna(num_val) else None
                else: # Assume string if not in numeric list or for other specific non-numeric types
                    parsed_result[param_name] = str(raw_val) if raw_val is not None else None
            except (ValueError, TypeError) as e_conv:
                self.logger.warning(f"Underlying Parse ({symbol_upper}): Conversion error for '{param_name}', raw value '{raw_val}': {e_conv}. Setting to None.")
                parsed_result[param_name] = None # Ensure it's None on conversion error

        # Post-parsing validation for essential fields
        price_val = parsed_result.get('price')
        if price_val is None or not isinstance(price_val, (int, float)) or price_val <= 0:
            err_price_msg = f"Essential 'price' for {symbol_upper} is invalid, missing, or non-positive after parsing (value: {price_val})."
            self.logger.error(f"Underlying Parse ({symbol_upper}): {err_price_msg}")
            current_err = parsed_result.get('error', "")
            parsed_result['error'] = f"{current_err}. {err_price_msg}".strip('. ') if current_err else err_price_msg
        
        if parsed_result['error']:
             self.logger.error(f"Underlying Parse ({symbol_upper}): Completed with errors: '{parsed_result['error']}'")
        else:
            self.logger.debug(f"Underlying Parse ({symbol_upper}): Complete. Price: {price_val}, Errors: None")
        return parsed_result

    def fetch_underlying_data(self, symbol: str) -> Dict[str, Any]:
        """Fetches underlying aggregate data for a single symbol using ConvexApi.get_und()."""
        symbol_upper = symbol.strip().upper()
        fetch_timestamp_start = datetime.now().isoformat()
        self.logger.info(f"Fetching underlying data for: {symbol_upper} (Params: {self.underlying_params_to_fetch})")

        if self.initialization_failed or not self.api:
            self.logger.error(f"Fetch Underlying ({symbol_upper}): API not connected or init failed. Cannot fetch.")
            return {'symbol': symbol_upper, 'error': "API not connected or fetcher initialization failed.", 'fetch_timestamp': fetch_timestamp_start}

        # Decorate the internal API call for retry logic
        @convexvalue_retry_api_call_rewrite( # Use rewritten decorator
            retries_param=self.max_retries, base_delay_seconds_param=self.base_retry_delay,
            max_delay_seconds_param=self.max_retry_delay, jitter_param=self.retry_jitter,
            logger_instance_param=self.logger, func_name_override_param=f"_get_und_rewrite_{symbol_upper}"
        )
        def _call_api_get_und_internal():
            if self.api is None: # Should not happen if initialization_failed is false
                raise ConnectionError("ConvexAPI instance is None during _call_api_get_und_internal.")
            return self.api.get_und(symbols=[symbol_upper], params=self.underlying_params_to_fetch)

        try:
            raw_data = _call_api_get_und_internal()
            if raw_data is None: # Should be caught by an exception from the decorator if retries failed
                 self.logger.error(f"Fetch Underlying ({symbol_upper}): API call returned None unexpectedly after retries.")
                 return {'symbol': symbol_upper, 'error': "API call failed and returned None after retries.", 'fetch_timestamp': fetch_timestamp_start}

            self.logger.debug(f"Fetch Underlying ({symbol_upper}): Raw API response received: {str(raw_data)[:500]}")
            parsed_data = self._parse_cv_underlying_response(symbol_upper, raw_data)
            # parsed_data already contains symbol and its own fetch_timestamp (from parsing start)
            # If we want to override with the timestamp of this specific fetch op's start:
            parsed_data['fetch_timestamp'] = fetch_timestamp_start 
            return parsed_data

        except Exception as e_fetch_und:
            self.logger.error(f"Fetch Underlying ({symbol_upper}): Exception during API call or parsing: {type(e_fetch_und).__name__} - {e_fetch_und}", exc_info=True)
            return {
                'symbol': symbol_upper,
                'error': f"Exception during fetch/parse: {type(e_fetch_und).__name__} - {str(e_fetch_und)[:150]}",
                'fetch_timestamp': fetch_timestamp_start
            }

    def _parse_cv_options_chain_response(self, symbol: str, raw_rows: List[List[Any]], current_underlying_price: Optional[float]) -> pd.DataFrame:
        """
        Parses the raw list of lists from ConvexApi.get_chain_as_rows() into a DataFrame.
        More robust parsing and error handling.
        """
        symbol_upper = symbol.upper()
        self.logger.info(f"Parsing options chain for {symbol_upper}. Received {len(raw_rows)} raw rows.")
        
        if not isinstance(raw_rows, list):
            self.logger.error(f"Options Chain Parse ({symbol_upper}): Expected list of rows, got {type(raw_rows)}. Returning empty DataFrame.")
            return pd.DataFrame()
        if not raw_rows:
            self.logger.info(f"Options Chain Parse ({symbol_upper}): No raw rows received. Returning empty DataFrame.")
            return pd.DataFrame()

        # Define column names based on instance's options_chain_params_to_fetch
        # The API returns 4 prefix columns: [ContractSymbol, ExpirationDaysEpoch, Strike, OptionType]
        # followed by the values for options_chain_params_to_fetch in order.
        prefix_columns_api = ["contract_symbol_api", "expiration_days_epoch_api", "strike_api", "opt_kind_api"]
        df_column_names = prefix_columns_api + self.options_chain_params_to_fetch
        num_expected_total_cols = len(df_column_names)

        processed_rows: List[List[Any]] = []
        for i, row_tuple_or_list in enumerate(raw_rows):
            # Ensure row is a list
            row_list = list(row_tuple_or_list) if isinstance(row_tuple_or_list, tuple) else \
                       (row_tuple_or_list if isinstance(row_tuple_or_list, list) else [])
            
            if not row_list:
                self.logger.warning(f"Chain Parse ({symbol_upper}): Row {i} is empty or invalid. Skipping.")
                continue

            current_row_len = len(row_list)

            if current_row_len != num_expected_total_cols:
                self.logger.warning(
                    f"Chain Parse ({symbol_upper}): Row {i} has {current_row_len} values, expected {num_expected_total_cols}. "
                    f"Raw content (first 100 chars): {str(row_list)[:100]}. Will attempt to pad/truncate."
                )
                if current_row_len < num_expected_total_cols:
                    row_list.extend([None] * (num_expected_total_cols - current_row_len)) # Pad with None
                else:
                    row_list = row_list[:num_expected_total_cols] # Truncate

            processed_rows.append(row_list)

        if not processed_rows:
            self.logger.warning(f"Options Chain ({symbol_upper}): No valid rows after length adjustment. Returning empty DataFrame.")
            return pd.DataFrame()

        try:
            options_df = pd.DataFrame(processed_rows, columns=df_column_names)
        except Exception as e_df_create:
            self.logger.error(f"Options Chain ({symbol_upper}): Failed to create DataFrame from processed rows: {e_df_create}. Raw rows sample: {str(processed_rows[:2])[:300]}", exc_info=True)
            return pd.DataFrame()
            
        self.logger.debug(f"Options Chain ({symbol_upper}): Initial DataFrame created. Shape: {options_df.shape}")

        # --- Data Cleaning and Type Conversion ---
        options_df["fetch_timestamp"] = datetime.now().isoformat()
        options_df["underlying_price_at_fetch"] = float(current_underlying_price) if pd.notna(current_underlying_price) else np.nan
        options_df["underlying_symbol"] = symbol_upper

        # Convert expiration from days since epoch (1970-01-01) to YYYY-MM-DD string
        epoch_date = datetime(1970, 1, 1)
        options_df["expiration_days_epoch_api"] = pd.to_numeric(options_df["expiration_days_epoch_api"], errors='coerce')
        
        def convert_days_to_date(days_since_epoch):
            if pd.isna(days_since_epoch): return None
            try: return (epoch_date + timedelta(days=int(days_since_epoch))).strftime('%Y-%m-%d')
            except (ValueError, TypeError, OverflowError) as e_date_conv:
                self.logger.warning(f"Chain Parse ({symbol_upper}): Error converting days '{days_since_epoch}' to date: {e_date_conv}. Setting to None.")
                return None
        options_df["expiration_date"] = options_df["expiration_days_epoch_api"].apply(convert_days_to_date)

        # Rename API prefix columns to standard names
        options_df.rename(columns={
            "contract_symbol_api": "symbol", # This is the option contract symbol
            "strike_api": "strike",
            "opt_kind_api": "opt_kind"
        }, inplace=True)

        # Standardize opt_kind and symbol
        options_df["opt_kind"] = options_df["opt_kind"].astype(str).str.lower().fillna('unknown')
        options_df["symbol"] = options_df["symbol"].astype(str).str.upper().fillna(f"{symbol_upper}_OPTION_UNKNOWN")

        # Convert numeric columns using the predefined list
        for col_name in CV_NUMERIC_COLUMNS_OPTIONS_REWRITE: # Use the specific list for options
            if col_name in options_df.columns:
                options_df[col_name] = pd.to_numeric(options_df[col_name], errors='coerce')
                # Fill NaNs in numeric columns, typically with 0.0 or np.nan depending on metric.
                # For many financial metrics, 0.0 is a common fill, but np.nan might be better for averages.
                # For simplicity here, let's use 0.0 for values that should exist but might be missing from a free API tier.
                options_df[col_name] = options_df[col_name].fillna(0.0)
            else:
                # If an expected numeric column is completely missing, add it and fill with 0.0
                # This ensures downstream processes expecting the column don't break.
                self.logger.warning(f"Options Chain Clean ({symbol_upper}): Expected numeric column '{col_name}' was MISSING. Adding as 0.0.")
                options_df[col_name] = 0.0
        
        # Ensure 'strike' is float after numeric conversion if it exists
        if 'strike' in options_df.columns:
            options_df['strike'] = options_df['strike'].astype(float)

        self.logger.info(f"Options Chain ({symbol_upper}): Successfully parsed and cleaned. Final DataFrame shape: {options_df.shape}. Columns: {options_df.columns.tolist()}")
        if options_df.empty:
             self.logger.warning(f"Options Chain ({symbol_upper}): Resulting DataFrame is empty after processing.")
        return options_df

    def fetch_options_chain_data(self, symbol: str,
                                 dte_list: Optional[List[int]] = None,
                                 price_range_pct_for_api: Optional[float] = None # Expects decimal, e.g., 0.10 for 10%
                                 ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Fetches and processes options chain data for a single symbol.
        Returns a DataFrame for the options chain and a Dict for the underlying data bundle.
        `price_range_pct_for_api` should be a decimal (e.g., 0.10 for 10%).
        """
        symbol_upper = symbol.strip().upper()
        fetch_op_timestamp = datetime.now().isoformat()
        
        eff_dte_list = dte_list if dte_list is not None else self.default_dte_range
        # Ensure price_range_pct_for_api is correctly interpreted as decimal for the API
        eff_price_range_decimal = price_range_pct_for_api if price_range_pct_for_api is not None else self.default_price_range_pct
        
        self.logger.info(f"Fetching options chain for {symbol_upper}. DTEs: {eff_dte_list}, Price Range (API decimal): {eff_price_range_decimal:.3f}")

        # Initialize underlying_data_result with an error state
        underlying_data_result: Dict[str, Any] = {
            "symbol": symbol_upper, 
            "error": "Underlying data fetch not yet attempted.", 
            "fetch_timestamp": fetch_op_timestamp
        }
        # Initialize options_df as empty
        options_df = pd.DataFrame()

        if self.initialization_failed or not self.api:
            self.logger.error(f"Options Chain Fetch ({symbol_upper}): API not connected or init failed. Aborting.")
            underlying_data_result["error"] = "API not connected or fetcher initialization failed."
            return options_df, underlying_data_result

        # 1. Fetch Underlying Data First
        underlying_data_result = self.fetch_underlying_data(symbol_upper) # This method handles its own errors
        
        current_underlying_price = underlying_data_result.get("price") # Should be float or None
        if underlying_data_result.get("error") or not (isinstance(current_underlying_price, (int, float)) and current_underlying_price > 0):
            error_msg_und = underlying_data_result.get("error", "Unknown underlying data error.")
            if not (isinstance(current_underlying_price, (int, float)) and current_underlying_price > 0):
                price_err_msg = f"Underlying price invalid or missing (price: {current_underlying_price})."
                error_msg_und = f"{error_msg_und}. {price_err_msg}".strip(". ") if error_msg_und else price_err_msg
            self.logger.error(f"Options Chain ({symbol_upper}): Cannot proceed with chain fetch. {error_msg_und}")
            underlying_data_result["error"] = error_msg_und # Ensure this is set in the returned bundle
            return options_df, underlying_data_result # Return empty DF and the error-marked underlying bundle
        
        self.logger.debug(f"Options Chain ({symbol_upper}): Underlying data fetched successfully. Price: {current_underlying_price:.4f}.")

        # 2. Fetch Options Chain Data
        @convexvalue_retry_api_call_rewrite( # Use rewritten decorator
            retries_param=self.max_retries, base_delay_seconds_param=self.base_retry_delay,
            max_delay_seconds_param=self.max_retry_delay, jitter_param=self.retry_jitter,
            logger_instance_param=self.logger, func_name_override_param=f"_get_chain_as_rows_rewrite_{symbol_upper}"
        )
        def _call_api_get_chain_as_rows_internal():
            if self.api is None: raise ConnectionError("ConvexAPI instance is None during _call_api_get_chain_as_rows_internal.")
            api_chain_params = {
                "params": self.options_chain_params_to_fetch, # Use instance configured params
                "exps": eff_dte_list,
                "rng": eff_price_range_decimal # API expects decimal range
            }
            self.logger.debug(f"Options Chain Fetch ({symbol_upper}): Calling API.get_chain_as_rows with: {api_chain_params}")
            return self.api.get_chain_as_rows(symbol_upper, **api_chain_params)

        try:
            # The API call returns a list of lists (rows)
            raw_options_rows: Optional[List[List[Any]]] = _call_api_get_chain_as_rows_internal()

            if raw_options_rows is None: # Decorator might return None if it caught and handled all errors internally
                chain_err_msg = f"Options chain fetch for {symbol_upper} returned None after retries (get_chain_as_rows)."
                self.logger.error(chain_err_msg)
                underlying_data_result["error"] = f"{underlying_data_result.get('error', '')}. {chain_err_msg}".strip('. ')
                return options_df, underlying_data_result
            
            if not isinstance(raw_options_rows, list):
                chain_format_err_msg = f"Options chain fetch for {symbol_upper} returned unexpected format (Type: {type(raw_options_rows)}). Expected list."
                self.logger.error(chain_format_err_msg)
                underlying_data_result["error"] = f"{underlying_data_result.get('error', '')}. {chain_format_err_msg}".strip('. ')
                return options_df, underlying_data_result

            # Parse the raw rows into a DataFrame
            options_df = self._parse_cv_options_chain_response(symbol_upper, raw_options_rows, float(current_underlying_price))
            
            # Add multiplier to underlying_data_result if found in chain and not already there
            # This assumes the 'multiplier' column exists and is consistent in the options_df
            if 'multiplier' not in underlying_data_result and 'multiplier' in options_df.columns and not options_df.empty:
                first_valid_multiplier = options_df['multiplier'].dropna().iloc[0] if not options_df['multiplier'].dropna().empty else 100.0
                underlying_data_result['multiplier'] = float(first_valid_multiplier)
            
            # Clear error from underlying_data_result if chain fetch and parse was successful and no prior error
            if not options_df.empty and underlying_data_result.get("error") == "Underlying data fetch not yet attempted.":
                 underlying_data_result["error"] = None # Indicate success if only this default error was present

            return options_df, underlying_data_result

        except Exception as e_chain_fetch:
            chain_proc_err_msg = f"Options chain processing for {symbol_upper} failed: {type(e_chain_fetch).__name__} - {str(e_chain_fetch)[:150]}"
            self.logger.error(chain_proc_err_msg, exc_info=True)
            underlying_data_result['error'] = f"{underlying_data_result.get('error', '')}. {chain_proc_err_msg}".strip('. ')
            return options_df, underlying_data_result # Return empty DF and updated underlying bundle


    def fetch_market_data_bundle(self, symbols: List[str],
                                 dte_list: Optional[List[int]] = None,
                                 price_range_percentage: Optional[float] = None # e.g., 10 for 10%
                                 ) -> Dict[str, Dict[str, Any]]:
        """
        Fetches all required market data (underlying aggregates and options chain)
        for a list of symbols.
        `price_range_percentage` is e.g., 10 for 10%, will be converted to decimal for API.
        Returns a dictionary where keys are symbols and values are dicts
        containing 'options_chain' (DataFrame) and 'underlying' (Dict).
        """
        self.logger.info(f"\n--- Starting ConvexValue Market Data Bundle Fetch (V{self.get_version()}) for Symbols: {symbols} ---")
        market_fetch_start_time = pytime.time()
        market_data_results_bundle: Dict[str, Dict[str, Any]] = {}
        num_symbols_to_fetch = len(symbols)

        # Convert percentage to decimal for API call (e.g., 10.0 to 0.10)
        price_range_decimal_for_api: Optional[float] = None
        if price_range_percentage is not None:
            try:
                price_range_decimal_for_api = float(price_range_percentage) / 100.0
            except ValueError:
                self.logger.warning(f"Invalid price_range_percentage '{price_range_percentage}'. Using fetcher default.")
                price_range_decimal_for_api = self.default_price_range_pct


        for i, symbol_item in enumerate(symbols):
            current_symbol_upper = symbol_item.strip().upper()
            if not current_symbol_upper:
                self.logger.warning(f"Skipping empty symbol string at index {i}.")
                continue

            symbol_fetch_start_time = pytime.time()
            self.logger.info(f"\nProcessing symbol: '{current_symbol_upper}' ({i+1}/{num_symbols_to_fetch})...")
            
            # Call fetch_options_chain_data which now handles both underlying and chain
            options_df_result, underlying_info_result = self.fetch_options_chain_data(
                current_symbol_upper,
                dte_list, # Pass through user-specified or use class defaults via fetch_options_chain_data
                price_range_decimal_for_api # Pass the already converted decimal value
            )

            # Ensure 'fetch_timestamp' is in underlying_info_result, add if missing (should be set by fetch_underlying_data)
            if 'fetch_timestamp' not in underlying_info_result:
                underlying_info_result['fetch_timestamp'] = datetime.now().isoformat() # Fallback
            
            # Consolidate error messages: If underlying fetch had an error, and chain fetch added to it or had its own
            combined_error = underlying_info_result.get("error")


            market_data_results_bundle[current_symbol_upper] = {
                "options_chain": options_df_result, # This is a DataFrame object
                "underlying": underlying_info_result, # This is a Dict from fetch_underlying_data
                "error": combined_error, # Propagate combined error from underlying/chain fetch
                "symbol": current_symbol_upper,
                "fetch_timestamp_bundle_creation": datetime.now().isoformat()
            }

            status_msg = "Failed" if combined_error else \
                         ("Empty Chain" if options_df_result.empty and not combined_error else "Success")
            self.logger.info(f"Finished processing '{current_symbol_upper}' in {pytime.time() - symbol_fetch_start_time:.3f}s. Status: {status_msg}. Error: '{combined_error}'")

            if i < num_symbols_to_fetch - 1 and self.inter_call_delay > 0:
                self.logger.debug(f"Applying inter-call delay of {self.inter_call_delay:.2f}s before next symbol.")
                pytime.sleep(self.inter_call_delay)

        total_market_fetch_duration = pytime.time() - market_fetch_start_time
        self.logger.info(f"\n--- Finished All ConvexValue Market Data Fetch in {total_market_fetch_duration:.3f} seconds ---")

        errors_encountered_count = sum(1 for symbol_bundle in market_data_results_bundle.values() if symbol_bundle.get("error"))
        self.logger.info(f"    Total symbols processed: {len(market_data_results_bundle)} / {num_symbols_to_fetch}. Total errors encountered: {errors_encountered_count}")

        return market_data_results_bundle

    def get_version(self) -> str:
        return "3.0.0-Rewrite" # Updated version

    def shutdown(self):
        self.logger.info(f"ConvexValueDataFetcher V{self.get_version()} shutdown. (No explicit ConvexApi close/logout is typically needed).")


# --- Main Test Block (Updated for Rewritten Fetcher) ---
if __name__ == "__main__":
    if not logging.getLogger().hasHandlers():
        _test_formatter_main_rewrite = logging.Formatter('[%(levelname)s] (%(name)s:%(lineno)d) %(asctime)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
        _test_handler_main_rewrite = logging.StreamHandler(sys.stdout)
        _test_handler_main_rewrite.setFormatter(_test_formatter_main_rewrite)
        logging.getLogger().addHandler(_test_handler_main_rewrite)
        logging.getLogger().setLevel(logging.DEBUG) # Set root to DEBUG for comprehensive test output

    module_test_logger_cv_rewrite = logging.getLogger(f"{__name__}_CVFetcherTestMain_V3_0_0")
    module_test_logger_cv_rewrite.setLevel(logging.DEBUG)
    # Ensure the fetcher's own logger (and retry decorator logger) also gets DEBUG level for testing
    logging.getLogger(__name__).setLevel(logging.DEBUG) # Main module logger for the fetcher
    logging.getLogger(f"{__name__}.convexvalue_retry_api_call_rewrite").setLevel(logging.DEBUG)


    module_test_logger_cv_rewrite.info(f"--- Starting ConvexValueDataFetcher Standalone Test (V{ConvexValueDataFetcher().get_version()}) ---")

    # Create a temporary copy of default settings to potentially modify for testing
    # The fetcher will load its underlying_params and options_chain_params from these settings
    # or use its internal defaults if not provided.
    test_cv_settings_rewrite = json.loads(json.dumps(DEFAULT_CV_FETCHER_SETTINGS_REWRITE))
    
    # IMPORTANT: For live testing, ensure your CONVEX_EMAIL and CONVEX_PASSWORD
    # are set in environment variables, OR update placeholders in test_cv_settings_rewrite for test instance
    # test_cv_settings_rewrite["email_direct"] = "YOUR_ACTUAL_EMAIL_HERE_FOR_TEST_ONLY"
    # test_cv_settings_rewrite["password_direct"] = "YOUR_ACTUAL_PASSWORD_HERE_FOR_TEST_ONLY"

    if not CONVEXLIB_AVAILABLE:
        module_test_logger_cv_rewrite.critical("Convexlib not available. Cannot run meaningful standalone test for ConvexValueDataFetcher.")
    elif (os.getenv(test_cv_settings_rewrite["email_env_var"]) is None and test_cv_settings_rewrite["email_direct"] == DEFAULT_CV_FETCHER_SETTINGS_REWRITE["email_direct"]) or \
         (os.getenv(test_cv_settings_rewrite["password_env_var"]) is None and test_cv_settings_rewrite["password_direct"] == DEFAULT_CV_FETCHER_SETTINGS_REWRITE["password_direct"]):
        module_test_logger_cv_rewrite.critical(
            f"CV API credentials not set via ENV VARS ('{test_cv_settings_rewrite['email_env_var']}') "
            f"and placeholders not changed in test_cv_settings. Tests WILL LIKELY FAIL or use no auth. Please set credentials for testing."
        )
        # Initialize to see initialization_failed status
        fetcher_instance_cv_test_rewrite = ConvexValueDataFetcher(
            cv_settings=test_cv_settings_rewrite, # Pass potentially modified test settings
            main_system_log_level="DEBUG"
        )
        module_test_logger_cv_rewrite.warning(f"Proceeding with test, but fetcher expected to be non-functional: InitFailed={fetcher_instance_cv_test_rewrite.initialization_failed}")
    else:
        fetcher_instance_cv_test_rewrite = ConvexValueDataFetcher(
            cv_settings=test_cv_settings_rewrite, # Pass potentially modified test settings
            main_system_log_level="DEBUG"
        )

        if fetcher_instance_cv_test_rewrite.initialization_failed:
            module_test_logger_cv_rewrite.critical("ConvexValueDataFetcher failed to initialize properly in test (likely missing credentials or API connection failure). Aborting further tests.")
        else:
            test_symbols_cv_rewrite = ["AAPL", "MSFT", "NONEXISTENTSYMBOL"] # Test with a known bad symbol too

            # Test 1: Fetch underlying data for a single symbol
            module_test_logger_cv_rewrite.info(f"\n--- Test 1: Fetch Underlying Data for {test_symbols_cv_rewrite[0]} ---")
            underlying_data_test = fetcher_instance_cv_test_rewrite.fetch_underlying_data(test_symbols_cv_rewrite[0])
            if underlying_data_test and not underlying_data_test.get("error"):
                module_test_logger_cv_rewrite.info(
                    f"OK: Underlying for {test_symbols_cv_rewrite[0]}: Price={underlying_data_test.get('price')}, "
                    f"Volatility={underlying_data_test.get('volatility')}, "
                    f"FetchTS='{underlying_data_test.get('fetch_timestamp')}'"
                )
                assert isinstance(underlying_data_test.get("price"), (float, int)), "Price should be float/int"
                assert underlying_data_test.get("price", -1) > 0, "Price should be positive"
            else:
                module_test_logger_cv_rewrite.error(f"FAIL: Underlying fetch for {test_symbols_cv_rewrite[0]}: {underlying_data_test.get('error', 'Unknown error')}")

            # Test 2: Fetch options chain for a single symbol (this now includes underlying fetch internally)
            module_test_logger_cv_rewrite.info(f"\n--- Test 2: Fetch Options Chain Data for {test_symbols_cv_rewrite[1]} (DTEs: [0,1], Range Decimal for API: 0.025) ---")
            options_df_test, underlying_info_for_chain_test = fetcher_instance_cv_test_rewrite.fetch_options_chain_data(
                test_symbols_cv_rewrite[1], dte_list=[0, 1], price_range_pct_for_api=0.025 # Pass decimal directly
            )
            if underlying_info_for_chain_test.get("error"):
                 module_test_logger_cv_rewrite.error(f"FAIL: Options chain fetch for {test_symbols_cv_rewrite[1]} failed due to underlying error: {underlying_info_for_chain_test.get('error')}")
            elif options_df_test.empty:
                module_test_logger_cv_rewrite.warning(f"WARN: Options chain fetch for {test_symbols_cv_rewrite[1]} returned empty DF but no explicit error in underlying_info.")
            else:
                module_test_logger_cv_rewrite.info(f"OK: Options chain for {test_symbols_cv_rewrite[1]} fetched. Shape: {options_df_test.shape}. Underlying Price Used: {underlying_info_for_chain_test.get('price')}")
                module_test_logger_cv_rewrite.info(f"Sample (head 2):\n{options_df_test.head(2).to_string()}")
                assert "strike" in options_df_test.columns, "Strike column missing"
                assert "volmbs_5m" in options_df_test.columns, "volmbs_5m column missing" # Check for a rolling flow column
            
            # Test 3: Fetch market data bundle for multiple symbols
            module_test_logger_cv_rewrite.info(f"\n--- Test 3: Fetch Market Data Bundle for {test_symbols_cv_rewrite} (DTEs: [0], Price Range Pct: 1.5%) ---")
            market_bundle_test = fetcher_instance_cv_test_rewrite.fetch_market_data_bundle(
                test_symbols_cv_rewrite, dte_list=[0], price_range_percentage=1.5 # Pass percentage here
            )
            for sym_bundle_test_key in test_symbols_cv_rewrite:
                bundle_item_test = market_bundle_test.get(sym_bundle_test_key)
                if bundle_item_test:
                    if bundle_item_test.get("error"):
                        module_test_logger_cv_rewrite.error(f"Bundle item for {sym_bundle_test_key} has error: {bundle_item_test['error']}")
                    else:
                        options_chain_in_bundle = bundle_item_test.get('options_chain', pd.DataFrame())
                        underlying_in_bundle = bundle_item_test.get('underlying', {})
                        module_test_logger_cv_rewrite.info(
                            f"OK: Bundle item for {sym_bundle_test_key} processed. "
                            f"Options DF shape: {options_chain_in_bundle.shape if isinstance(options_chain_in_bundle, pd.DataFrame) else 'N/A'}. "
                            f"Underlying Price: {underlying_in_bundle.get('price')}, "
                            f"Underlying FetchTS: {underlying_in_bundle.get('fetch_timestamp')}, "
                            f"Bundle CreationTS: {bundle_item_test.get('fetch_timestamp_bundle_creation')}"
                        )
                else:
                    module_test_logger_cv_rewrite.error(f"Bundle item for {sym_bundle_test_key} MISSING.")

            fetcher_instance_cv_test_rewrite.shutdown()

    module_test_logger_cv_rewrite.info(f"--- ConvexValueDataFetcher Standalone Test (V{ConvexValueDataFetcher().get_version()}) Finished ---")