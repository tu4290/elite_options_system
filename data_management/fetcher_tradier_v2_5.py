# enhanced_tradier_fetcher_v2.py
# (Elite Options Trading System - Tradier Data Fetcher)
# Version 2.6.0 - Full Rewrite for Robustness and Clearer Data Handling

import os
import sys
import time as pytime # Renamed to avoid conflict with datetime.time
import logging
import json
import random
from datetime import datetime, date, timedelta, time as dt_time # dt_time for clarity
from typing import List, Dict, Any, Optional, Tuple, Union, Callable, Deque
from functools import wraps
import pandas as pd
import numpy as np
import requests

# --- Module-Specific Logger ---
# Fallback basicConfig. Main application should configure logging.
if not logging.getLogger(__name__).hasHandlers():
    _tradier_logger_formatter = logging.Formatter(
        '[%(levelname)s] (%(name)s:%(lineno)d) %(asctime)s - %(message)s',
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    _tradier_logger_handler = logging.StreamHandler(sys.stdout)
    _tradier_logger_handler.setFormatter(_tradier_logger_formatter)
    logging.getLogger(__name__).addHandler(_tradier_logger_handler)
    logging.getLogger(__name__).setLevel(logging.INFO) # Default if not set by main app
logger = logging.getLogger(__name__)

# --- Default Config Snippet (for standalone testing or if no settings passed) ---
DEFAULT_TRADIER_FETCHER_SETTINGS = {
    "base_url": "https://api.tradier.com/v1/",
    "access_token_env_var": "TRADIER_PRODUCTION_TOKEN",
    "access_token_direct": "YOUR_TRADIER_TOKEN_PLACEHOLDER", # Important: Replace for testing if no ENV VAR
    "retry_config": {
        "max_retries": 3,
        "base_delay_seconds": 1.5,
        "max_delay_seconds": 12.0,
        "jitter": True
    },
    "request_timeout_seconds": 20,
    "ohlcv_num_days_history_default": 90,
    "iv_approx_target_dte_default": 5,
    "historical_atr_pct_lookback_trading_days_default": 180,
    "historical_atr_pct_atr_period_default": 14,
    "historical_atr_pct_ohlcv_buffer_days_default": 60,
    "min_normalization_denominator_local": 1e-9, # Local version of this constant
}

# --- Retry Decorator ---
def tradier_retry_api_call(
    max_retries_param: int,
    base_delay_seconds_param: float,
    max_delay_seconds_param: float,
    jitter_param: bool = True,
    logger_instance_param: Optional[logging.Logger] = None,
    expected_response_container_type: type = dict, # e.g., dict for JSON, list, or 'response' for raw requests.Response
    func_name_override_param: Optional[str] = None
):
    log_dec = logger_instance_param if logger_instance_param else logging.getLogger(f"{__name__}.tradier_retry_api_call")

    def decorator(func: Callable):
        actual_func_name_dec = func_name_override_param if func_name_override_param else func.__name__

        @wraps(func)
        def wrapper(*args, **kwargs):
            attempts_dec = 0
            current_delay_dec = base_delay_seconds_param
            last_exception_dec: Optional[BaseException] = None
            
            # Default error returns based on expected type
            if expected_response_container_type == dict: error_return_val = {"error": "Max retries reached or critical API error."}
            elif expected_response_container_type == list: error_return_val = []
            elif expected_response_container_type == pd.DataFrame: error_return_val = pd.DataFrame()
            else: error_return_val = None # For raw response or other types

            while attempts_dec <= max_retries_param:
                response_content_for_error_dec: Optional[str] = "No response content captured."
                try:
                    response_obj_dec: requests.Response = func(*args, **kwargs) # Wrapped function must return requests.Response

                    if not isinstance(response_obj_dec, requests.Response):
                        log_dec.error(f"Tradier API call {actual_func_name_dec} did not return a Response object. Got: {type(response_obj_dec)}.")
                        error_return_val_internal = {"error": f"Internal error: {actual_func_name_dec} did not return Response."} if expected_response_container_type == dict else error_return_val
                        return error_return_val_internal

                    response_content_for_error_dec = str(response_obj_dec.text)[:500] # Capture text before potential raise_for_status
                    response_obj_dec.raise_for_status() # Raises HTTPError for 4xx/5xx

                    # If expected_response_container_type is 'response', return the raw response
                    if expected_response_container_type == requests.Response:
                        return response_obj_dec

                    parsed_json_response = response_obj_dec.json()

                    # Tradier specific error structure check (after successful HTTP status)
                    if isinstance(parsed_json_response, dict) and "errors" in parsed_json_response and parsed_json_response["errors"] and parsed_json_response["errors"] != "null":
                        api_errors_str = str(parsed_json_response["errors"].get("error", "Unknown API error structure in 'errors' block."))
                        log_dec.warning(f"Tradier API error(s) in {actual_func_name_dec} attempt {attempts_dec + 1} (HTTP OK): {api_errors_str}")
                        last_exception_dec = RuntimeError(f"API Error(s): {api_errors_str}")
                        # Specific non-retryable error: symbol not found
                        if "symbol not found" in api_errors_str.lower() or "not found" in api_errors_str.lower():
                             log_dec.error(f"Tradier API: Symbol/Resource not found for {actual_func_name_dec}. Not retrying. Response: {response_content_for_error_dec}")
                             error_return_val_specific = {"error": f"Symbol/Resource not found via Tradier API: {api_errors_str}"} if expected_response_container_type == dict else error_return_val
                             return error_return_val_specific
                        # Continue to retry for other API errors within 'errors' block
                        raise last_exception_dec

                    # Type check against expected_response_container_type (for JSON responses)
                    if not isinstance(parsed_json_response, expected_response_container_type) and \
                       not (expected_response_container_type == pd.DataFrame and isinstance(parsed_json_response, (dict, list))): # Allow dict/list for pd.DataFrame creation
                        log_dec.warning(f"Tradier API {actual_func_name_dec} unexpected JSON type attempt {attempts_dec + 1}. Expected {expected_response_container_type}, got {type(parsed_json_response)}. Resp: {str(parsed_json_response)[:200]}")
                        last_exception_dec = TypeError(f"Unexpected JSON type: {type(parsed_json_response)}")
                        if attempts_dec == max_retries_param: # Last attempt
                             error_return_val_type = {"error": f"API unexpected JSON type for {actual_func_name_dec}"} if expected_response_container_type == dict else error_return_val
                             return error_return_val_type
                        raise last_exception_dec # Raise to trigger retry

                    log_dec.debug(f"Tradier API call {actual_func_name_dec} successful attempt {attempts_dec + 1}.")
                    return parsed_json_response # Return parsed JSON if successful and type matches

                except requests.exceptions.HTTPError as e_http_dec:
                    status_code_dec = e_http_dec.response.status_code
                    log_dec.warning(f"Tradier API HTTP Error attempt {attempts_dec + 1} for {actual_func_name_dec}: {status_code_dec} - Content: {response_content_for_error_dec}")
                    last_exception_dec = e_http_dec
                    sleep_duration_final_dec = current_delay_dec
                    if status_code_dec in [401, 403]: # Auth errors - no retry
                        error_msg_auth_dec = f"Tradier API Authentication Error ({status_code_dec}) for {actual_func_name_dec}"
                        log_dec.error(error_msg_auth_dec)
                        error_return_val_auth = {"error": error_msg_auth_dec} if expected_response_container_type == dict else error_return_val
                        return error_return_val_auth
                    elif status_code_dec == 404: # Not found - no retry
                        error_msg_404_dec = f"Tradier API Resource not found (404) for {actual_func_name_dec}"
                        log_dec.error(error_msg_404_dec)
                        error_return_val_404 = {"error": error_msg_404_dec} if expected_response_container_type == dict else error_return_val
                        return error_return_val_404
                    elif status_code_dec == 429: # Rate limit
                        retry_after_header_dec = e_http_dec.response.headers.get('Retry-After')
                        if retry_after_header_dec and retry_after_header_dec.isdigit(): sleep_duration_final_dec = int(retry_after_header_dec)
                        else: sleep_duration_final_dec = min(current_delay_dec * 2.5, max_delay_seconds_param * 1.5) # Aggressive backoff for rate limit
                        log_dec.info(f"Rate limit hit (429). Overriding sleep to {sleep_duration_final_dec:.2f}s.")
                    # Other HTTP errors will proceed to retry logic below
                except requests.exceptions.Timeout as e_timeout_dec:
                    log_dec.warning(f"Tradier API Timeout Error attempt {attempts_dec + 1} for {actual_func_name_dec}: {type(e_timeout_dec).__name__} - {str(e_timeout_dec)[:150]}")
                    last_exception_dec = e_timeout_dec; sleep_duration_final_dec = current_delay_dec
                except requests.exceptions.RequestException as e_req_dec: # Other network/request errors
                    log_dec.warning(f"Tradier API Network/Request Error attempt {attempts_dec + 1} for {actual_func_name_dec}: {type(e_req_dec).__name__} - {str(e_req_dec)[:150]}")
                    last_exception_dec = e_req_dec; sleep_duration_final_dec = current_delay_dec
                except json.JSONDecodeError as e_json_dec: # Error parsing JSON
                    log_dec.warning(f"Tradier API JSONDecodeError attempt {attempts_dec + 1} for {actual_func_name_dec}: {e_json_dec}. Resp: {response_content_for_error_dec}")
                    last_exception_dec = e_json_dec; sleep_duration_final_dec = current_delay_dec
                except (TypeError, RuntimeError) as e_api_logic_dec: # Catch API errors reported as RuntimeError or TypeErrors from parsing
                    log_dec.warning(f"Tradier API Logic Error (TypeError/RuntimeError) attempt {attempts_dec + 1} for {actual_func_name_dec}: {e_api_logic_dec}")
                    last_exception_dec = e_api_logic_dec; sleep_duration_final_dec = current_delay_dec
                except Exception as e_gen_dec: # Catch-all for other unexpected errors during the try block
                    log_dec.error(f"Unexpected Error in API call attempt {attempts_dec + 1} for {actual_func_name_dec}: {type(e_gen_dec).__name__} - {e_gen_dec}", exc_info=log_dec.getEffectiveLevel() <= logging.DEBUG)
                    last_exception_dec = e_gen_dec; sleep_duration_final_dec = current_delay_dec
                
                attempts_dec += 1
                if attempts_dec <= max_retries_param:
                    sleep_time_actual_dec = sleep_duration_final_dec + (random.uniform(0, sleep_duration_final_dec * 0.25) if jitter_param else 0)
                    log_dec.info(f"Retrying Tradier API call {actual_func_name_dec} in {sleep_time_actual_dec:.2f}s... (Attempt {attempts_dec}/{max_retries_param})")
                    pytime.sleep(sleep_time_actual_dec)
                    current_delay_dec = min(current_delay_dec * 1.8, max_delay_seconds_param) # Exponential backoff
                else: # Max retries reached
                    error_message_final_dec = f"Tradier API call {actual_func_name_dec} failed after {max_retries_param} retries."
                    if last_exception_dec: error_message_final_dec += f" Last error: {type(last_exception_dec).__name__} - {str(last_exception_dec)[:100]}"
                    log_dec.error(error_message_final_dec)
                    # Update the error message in the default error return value if it's a dict
                    if isinstance(error_return_val, dict) and "error" in error_return_val:
                        error_return_val["error"] = error_message_final_dec
                    return error_return_val
            
            # Should not be reached if loop logic is correct
            log_dec.critical(f"Fell through Tradier retry loop for {actual_func_name_dec} - this indicates a logic error in the retry decorator.")
            return error_return_val # Fallback
        return wrapper
    return decorator

class TradierDataFetcher:
    def __init__(self, tradier_settings: Optional[Dict[str, Any]] = None, main_system_log_level: str = "INFO"):
        self.logger = logger.getChild(self.__class__.__name__)
        self.initialization_failed = False
        self.settings = tradier_settings if isinstance(tradier_settings, dict) else {}
        self._load_settings(main_system_log_level) # Loads settings and sets self.initialization_failed

        if self.initialization_failed:
            self.logger.critical("TradierDataFetcher initialization failed due to missing token or other critical setting.")
            self.headers = {}
        else:
            # self.access_token should be set by _load_settings
            self.headers = {"Authorization": f"Bearer {self.access_token}", "Accept": "application/json"} 
        
        self.logger.info(f"TradierDataFetcher V2.6.0 initialized. Target API: {self.base_url}. Token Loaded: {'Yes' if not self.initialization_failed and self.access_token else 'NO/Placeholder'}")

        if self.initialization_failed:
            self.logger.critical("TradierDataFetcher initialization failed due to missing token or other critical setting.")
            self.headers = {} # This was missing in your posted snippet, should be based on self.access_token
            self.access_token = None # Ensure access_token is also None if init failed
        else:
            # Ensure self.access_token is set by _load_settings before this
            if self.access_token: # self.access_token should be named self.api_key as per your snippet
                self.headers = {"Authorization": f"Bearer {self.access_token}", "Accept": "application/json"}
            else: # If _load_settings failed to set access_token but didn't set initialization_failed
                self.logger.critical("Tradier API token (self.access_token) is None after settings load. Headers cannot be set.")
                self.headers = {}
                self.initialization_failed = True

        self.logger.info(f"TradierDataFetcher V{self.get_version()} initialized. Target API: {self.settings.get('base_url', 'N/A')}. Token Loaded: {'Yes' if not self.initialization_failed and self.access_token else 'NO/Placeholder'}")

    def _load_settings(self, main_system_log_level: str):
        self.logger.debug("Loading TradierDataFetcher configurations...")
        
        # Deep copy default settings to avoid modifying the global default
        effective_settings = json.loads(json.dumps(DEFAULT_TRADIER_FETCHER_SETTINGS))
        if self.settings: # Merge provided settings over defaults
            for key_major, val_major in self.settings.items():
                if key_major in effective_settings and isinstance(effective_settings[key_major], dict) and isinstance(val_major, dict):
                    effective_settings[key_major].update(val_major)
                else:
                    effective_settings[key_major] = val_major
        
        self.base_url = str(effective_settings["base_url"])
        access_token_env_var = str(effective_settings["access_token_env_var"])
        self.access_token = os.getenv(access_token_env_var)
        
        if not self.access_token:
            self.access_token = str(effective_settings["access_token_direct"])
            if self.access_token and self.access_token != DEFAULT_TRADIER_FETCHER_SETTINGS["access_token_direct"]:
                self.logger.info(f"Loaded Tradier token from config 'access_token_direct' as ENV VAR '{access_token_env_var}' was empty.")
            elif not self.access_token or self.access_token == DEFAULT_TRADIER_FETCHER_SETTINGS["access_token_direct"]:
                self.logger.error(f"Tradier API Token NOT found in ENV VAR '{access_token_env_var}' or via a valid 'access_token_direct' in config. Fetcher will be NON-FUNCTIONAL.")
                self.initialization_failed = True
                self.access_token = None # Ensure it's None if invalid
        
        retry_cfg = effective_settings["retry_config"]
        self.max_retries = int(retry_cfg["max_retries"])
        self.base_retry_delay = float(retry_cfg["base_delay_seconds"])
        self.max_retry_delay = float(retry_cfg["max_delay_seconds"])
        self.retry_jitter = bool(retry_cfg["jitter"])
        self.request_timeout = int(effective_settings.get("request_timeout_seconds", 20))

        self.default_ohlcv_days_history = int(effective_settings["ohlcv_num_days_history_default"])
        self.default_iv_approx_dte = int(effective_settings["iv_approx_target_dte_default"])
        self.hist_atr_pct_lookback_days = int(effective_settings["historical_atr_pct_lookback_trading_days_default"])
        self.hist_atr_pct_atr_period = int(effective_settings["historical_atr_pct_atr_period_default"])
        self.hist_atr_pct_ohlcv_buffer = int(effective_settings["historical_atr_pct_ohlcv_buffer_days_default"])
        self.min_norm_den_local = float(effective_settings.get("min_normalization_denominator_local", 1e-9))

        try:
            effective_log_level = getattr(logging, str(main_system_log_level).upper())
            self.logger.setLevel(effective_log_level)
            # Also set level for the retry decorator's logger if it's separate
            logging.getLogger(f"{__name__}.tradier_retry_api_call").setLevel(effective_log_level)
            self.logger.info(f"TradierFetcher logger level set to: {main_system_log_level.upper()}")
        except (AttributeError, ValueError):
            self.logger.warning(f"Invalid log level '{main_system_log_level}' from main system. TradierFetcher defaulting to INFO.")
            self.logger.setLevel(logging.INFO)
            logging.getLogger(f"{__name__}.tradier_retry_api_call").setLevel(logging.INFO)
        
        self.logger.debug(f"Tradier API URL: {self.base_url}, Retries: {self.max_retries}, BaseDelay: {self.base_retry_delay}s, Timeout: {self.request_timeout}s")

    def _make_tradier_request_internal(self, endpoint_path: str, params: Optional[Dict[str, Any]] = None) -> requests.Response:
        """Internal method to make the actual HTTP request. To be wrapped by the retry decorator."""
        if self.initialization_failed:
            self.logger.error(f"API call ({endpoint_path}) attempted while fetcher initialization failed. Mocking error response.")
            error_response = requests.Response()
            error_response.status_code = 503 # Service Unavailable
            error_response.reason = "Tradier Fetcher Not Initialized or Token Missing"
            error_response._content = b'{"error": "TradierDataFetcher not initialized due to missing API token or other critical setting."}'
            return error_response
            
        full_url = f"{self.base_url.rstrip('/')}/{endpoint_path.lstrip('/')}"
        self.logger.debug(f"Making Tradier request to: {full_url} with params: {params}")
        return requests.get(full_url, headers=self.headers, params=params or {}, timeout=self.request_timeout)

    def get_underlying_quote(self, symbol: str) -> Dict[str, Any]:
        """Fetches quote for a symbol. Returns dict (can include 'error' key)."""
        self.logger.info(f"Fetching quote for symbol: {symbol}")
        
        @tradier_retry_api_call(self.max_retries, self.base_retry_delay, self.max_retry_delay, 
                                self.retry_jitter, self.logger, dict, f"get_underlying_quote_{symbol}")
        def _fetch_quote_with_retry():
            return self._make_tradier_request_internal(endpoint_path="markets/quotes", params={"symbols": symbol, "greeks": "false"})

        response_data = _fetch_quote_with_retry() # This will be a dict

        if "error" in response_data:
            self.logger.error(f"Failed to fetch quote for {symbol}: {response_data['error']}")
            return {"symbol": symbol, "error": response_data['error']}

        if 'quotes' in response_data and response_data['quotes'] and response_data['quotes'] != 'null':
            quote_data_item = response_data['quotes'].get('quote')
            if isinstance(quote_data_item, list) and quote_data_item: return quote_data_item[0]
            elif isinstance(quote_data_item, dict): return quote_data_item
            else: self.logger.warning(f"Quote data for {symbol} is present but not in expected list/dict format: {quote_data_item}")
        elif 'fault' in response_data: # Should be caught by retry decorator now
            fault_str = str(response_data.get('fault', {}).get('faultstring', 'Unknown API fault'))
            self.logger.error(f"Tradier API fault for {symbol} quote: {fault_str}")
            return {"symbol": symbol, "error": f"API Fault: {fault_str}"}
        else:
            self.logger.warning(f"Unexpected quote structure or no quote found for {symbol}: {str(response_data)[:300]}")
        
        return {"symbol": symbol, "error": f"No valid quote data found for {symbol}."}

    def get_ohlcv_data(self, symbol: str, interval: str = "daily", start_date_str: Optional[str] = None, end_date_str: Optional[str] = None, num_days_history: Optional[int] = None) -> pd.DataFrame:
        """Fetches OHLCV data. Returns DataFrame (can be empty if error or no data)."""
        eff_num_days = num_days_history if num_days_history is not None else self.default_ohlcv_days_history
        self.logger.info(f"Fetching OHLCV for {symbol}, Interval: {interval}, TargetTradingDays: {eff_num_days} (Start: {start_date_str}, End: {end_date_str})")
        
        actual_start_date_str, actual_end_date_str = start_date_str, end_date_str
        if actual_start_date_str is None and actual_end_date_str is None and eff_num_days > 0:
            end_dt = datetime.now().date()
            # Fetch more calendar days to likely get enough trading days
            calendar_days_to_fetch = int(eff_num_days * 1.7) + 10 # Buffer
            start_dt = end_dt - timedelta(days=calendar_days_to_fetch)
            actual_end_date_str, actual_start_date_str = end_dt.strftime('%Y-%m-%d'), start_dt.strftime('%Y-%m-%d')
            self.logger.debug(f"Defaulting OHLCV date range for {symbol}: {actual_start_date_str} to {actual_end_date_str} to aim for ~{eff_num_days} trading days.")
        elif actual_end_date_str is None and actual_start_date_str is not None :
             actual_end_date_str = datetime.now().strftime('%Y-%m-%d')
        elif actual_start_date_str is None and actual_end_date_str is not None and eff_num_days > 0:
            try:
                end_dt_param = datetime.strptime(actual_end_date_str, '%Y-%m-%d').date()
                calendar_days_to_fetch = int(eff_num_days * 1.7) + 10
                start_dt_param = end_dt_param - timedelta(days=calendar_days_to_fetch)
                actual_start_date_str = start_dt_param.strftime('%Y-%m-%d')
            except ValueError:
                self.logger.error(f"Invalid end_date_str format '{actual_end_date_str}' for OHLCV. Returning empty DataFrame.")
                return pd.DataFrame()
        
        if not actual_start_date_str or not actual_end_date_str :
             self.logger.error(f"Could not determine valid start/end dates for OHLCV for {symbol}. Returning empty DataFrame.")
             return pd.DataFrame()

        params = {"symbol": symbol, "interval": interval, "start": actual_start_date_str, "end": actual_end_date_str}
        
        @tradier_retry_api_call(self.max_retries, self.base_retry_delay, self.max_retry_delay, 
                                self.retry_jitter, self.logger, dict, f"get_ohlcv_data_{symbol}")
        def _fetch_ohlcv_with_retry():
            return self._make_tradier_request_internal(endpoint_path="markets/history", params=params)
            
        response_data = _fetch_ohlcv_with_retry()

        if "error" in response_data:
            self.logger.error(f"Failed to fetch OHLCV for {symbol}: {response_data['error']}")
            return pd.DataFrame()

        if response_data.get('history') and response_data['history'] != 'null' and 'day' in response_data['history']:
            days_data = response_data['history']['day']
            days_list = [days_data] if isinstance(days_data, dict) else (days_data if isinstance(days_data, list) else [])
            
            if not days_list:
                self.logger.info(f"No OHLCV data found for {symbol} in range {actual_start_date_str}-{actual_end_date_str} (API returned no 'day' data).")
                return pd.DataFrame()
            try:
                df = pd.DataFrame(days_list)
                df.rename(columns={'date': 'date_str_temp', 'open': 'open', 'high': 'high', 'low': 'low', 'close': 'close', 'volume': 'volume'}, inplace=True)
                required_cols = ['date_str_temp', 'open', 'high', 'low', 'close', 'volume']
                missing_cols = [col for col in required_cols if col not in df.columns]
                if missing_cols:
                    self.logger.warning(f"OHLCV data for {symbol} missing expected keys: {missing_cols}. Have: {df.columns.tolist()}. Returning empty DataFrame.")
                    return pd.DataFrame()

                df['date'] = pd.to_datetime(df['date_str_temp'], errors='coerce').dt.date
                df.drop(columns=['date_str_temp'], inplace=True, errors='ignore')
                for col in ['open', 'high', 'low', 'close', 'volume']:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                
                df.dropna(subset=['date', 'open', 'high', 'low', 'close', 'volume'], inplace=True)
                if df.empty:
                    self.logger.info(f"OHLCV data for {symbol} became empty after NaN drop. Range: {actual_start_date_str}-{actual_end_date_str}.")
                    return pd.DataFrame()
                
                df.sort_values(by='date', inplace=True, ascending=True)
                df.drop_duplicates(subset=['date'], keep='last', inplace=True) # Ensure unique dates

                # Trim to eff_num_days if it was originally requested via num_days_history and not specific dates
                if num_days_history is not None and start_date_str is None and end_date_str is None and len(df) > eff_num_days:
                    df = df.tail(eff_num_days)
                
                final_df = df[['date', 'open', 'high', 'low', 'close', 'volume']].copy()
                self.logger.info(f"Successfully processed {len(final_df)} OHLCV data points for {symbol}.")
                return final_df
            except Exception as e_df_proc:
                self.logger.error(f"Error processing OHLCV to DataFrame for {symbol}: {e_df_proc}", exc_info=True)
        elif response_data.get('history') == 'null' or (isinstance(response_data.get('history'), dict) and response_data['history'].get('day') is None):
            self.logger.info(f"No historical OHLCV data available for {symbol} in range {actual_start_date_str}-{actual_end_date_str} (API returned null history or no day).")
        elif 'fault' in response_data: # Should be caught by retry decorator
            self.logger.error(f"Tradier API fault for {symbol} OHLCV: {response_data.get('fault',{}).get('faultstring','Unknown')}")
        else:
            self.logger.warning(f"Unexpected OHLCV data structure for {symbol}: {str(response_data)[:300]}")
        
        return pd.DataFrame()

    def get_option_expirations(self, symbol: str) -> List[date]:
        """Fetches option expiration dates. Returns list of date objects (can be empty)."""
        self.logger.info(f"Fetching option expirations for {symbol}")
        
        @tradier_retry_api_call(self.max_retries, self.base_retry_delay, self.max_retry_delay, 
                                self.retry_jitter, self.logger, dict, f"get_expirations_{symbol}")
        def _fetch_expirations_with_retry():
            return self._make_tradier_request_internal(endpoint_path="markets/options/expirations", params={"symbol": symbol, "includeAllRoots": "true", "strikes": "false"})

        response_data = _fetch_expirations_with_retry()
        exp_dates_objects: List[date] = []

        if "error" in response_data:
            self.logger.error(f"Failed to fetch expirations for {symbol}: {response_data['error']}")
            return exp_dates_objects

        if response_data.get('expirations') and response_data['expirations'] != 'null' and 'date' in response_data['expirations']:
            dates_str_data = response_data['expirations']['date']
            date_list_str = [dates_str_data] if isinstance(dates_str_data, str) else (dates_str_data if isinstance(dates_str_data, list) else [])
            for d_str in date_list_str:
                try: exp_dates_objects.append(datetime.strptime(d_str, '%Y-%m-%d').date())
                except ValueError: self.logger.warning(f"Invalid date format '{d_str}' in expirations for {symbol}. Skipping.")
            exp_dates_objects.sort()
        elif response_data.get('expirations') == 'null':
            self.logger.info(f"No option expirations found for {symbol} (API returned null).")
        else:
            self.logger.warning(f"Unexpected expirations structure for {symbol}: {str(response_data)[:200]}")
        
        return exp_dates_objects

    def get_option_chain(self, symbol: str, expiration_date_str: str) -> List[Dict[str, Any]]:
        """Fetches option chain for a specific expiration. Returns list of option dicts (can be empty)."""
        self.logger.info(f"Fetching option chain for {symbol}, Expiration: {expiration_date_str}")
        params = {"symbol": symbol, "expiration": expiration_date_str, "greeks": "true"}

        @tradier_retry_api_call(self.max_retries, self.base_retry_delay, self.max_retry_delay, 
                                self.retry_jitter, self.logger, dict, f"get_chain_{symbol}_{expiration_date_str}")
        def _fetch_chain_with_retry():
            return self._make_tradier_request_internal(endpoint_path="markets/options/chains", params=params)
            
        response_data = _fetch_chain_with_retry()

        if "error" in response_data:
            self.logger.error(f"Failed to fetch chain for {symbol} on {expiration_date_str}: {response_data['error']}")
            return []

        if response_data.get('options') and response_data['options'] != 'null' and 'option' in response_data['options']:
            options_data = response_data['options']['option']
            return options_data if isinstance(options_data, list) else ([options_data] if isinstance(options_data, dict) else [])
        elif response_data.get('options') == 'null':
            self.logger.info(f"No option chain data found for {symbol} on {expiration_date_str} (API returned null).")
        else:
            self.logger.warning(f"Unexpected option chain structure for {symbol} on {expiration_date_str}: {str(response_data)[:200]}")
        
        return []

    def get_iv_approximation(self, symbol: str, target_dte_override: Optional[int] = None) -> Dict[str, Any]:
        """
        Approximates Implied Volatility for a target DTE.
        Returns a dictionary with IV details or an error.
        The key for the approximated IV will be f"tradier_iv{eff_target_dte}_approx_smv_avg".
        """
        eff_target_dte = target_dte_override if target_dte_override is not None else self.default_iv_approx_dte
        self.logger.info(f"Approximating IV for DTE ~{eff_target_dte} for symbol {symbol}")
        
        result_dict: Dict[str, Any] = {
            "symbol": symbol, "error": None,
            "target_dte_for_iv_approx": eff_target_dte,
            "source_expiration_for_iv_approx": None,
            "actual_dte_of_source_options": None,
            "underlying_price_at_iv_approx_calc": None,
            "atm_call_strike_iv_approx": None, "atm_call_smv_vol_iv_approx": None,
            "atm_put_strike_iv_approx": None, "atm_put_smv_vol_iv_approx": None,
            # Dynamic key will be added here
        }
        dynamic_iv_key = f"tradier_iv{eff_target_dte}_approx_smv_avg"
        result_dict[dynamic_iv_key] = None # Initialize with None

        quote = self.get_underlying_quote(symbol)
        if not quote or quote.get("error") or quote.get('last') is None:
            err_msg = quote.get("error", "Underlying price not available") if quote else "Failed to get quote"
            self.logger.error(f"Cannot get valid underlying price for {symbol} for IV approx: {err_msg}")
            result_dict["error"] = f"Underlying quote error: {err_msg}"
            return result_dict
        try:
            current_price = float(quote['last'])
            result_dict["underlying_price_at_iv_approx_calc"] = current_price
        except (TypeError, ValueError):
            self.logger.error(f"Could not convert price '{quote.get('last')}' to float for {symbol} IV approx.")
            result_dict["error"] = "Invalid underlying price format."
            return result_dict

        expirations_dates_obj = self.get_option_expirations(symbol)
        if not expirations_dates_obj:
            self.logger.warning(f"No expirations found for {symbol} for IV approx.")
            result_dict["error"] = "No option expirations found."
            return result_dict

        today = date.today()
        closest_exp_obj: Optional[date] = None
        min_dte_diff = float('inf')
        actual_dte_val = -1

        for exp_obj in expirations_dates_obj:
            if exp_obj < today: continue # Skip past expirations
            dte_val_calc = (exp_obj - today).days
            dte_diff_abs = abs(dte_val_calc - eff_target_dte)
            if dte_diff_abs < min_dte_diff:
                min_dte_diff = dte_diff_abs
                closest_exp_obj = exp_obj
                actual_dte_val = dte_val_calc
            elif dte_diff_abs == min_dte_diff: # Prefer closer to today if equidistant from target
                if closest_exp_obj is None or dte_val_calc < actual_dte_val:
                    closest_exp_obj = exp_obj
                    actual_dte_val = dte_val_calc
        
        if not closest_exp_obj:
            self.logger.warning(f"No suitable future expiration found for {symbol} for IV approx (Target DTE: {eff_target_dte}).")
            result_dict["error"] = "No suitable future expiration date found."
            return result_dict
        
        result_dict["source_expiration_for_iv_approx"] = closest_exp_obj.strftime('%Y-%m-%d')
        result_dict["actual_dte_of_source_options"] = actual_dte_val
        self.logger.info(f"Selected expiration for {symbol} IV approx: {result_dict['source_expiration_for_iv_approx']} (Actual DTE: {actual_dte_val})")

        chain = self.get_option_chain(symbol, result_dict["source_expiration_for_iv_approx"])
        if not chain: # Empty list means error or no data
            self.logger.warning(f"Could not get option chain for {symbol} exp {result_dict['source_expiration_for_iv_approx']}.")
            result_dict["error"] = "Failed to fetch option chain for selected expiration."
            return result_dict

        atm_call, atm_put = None, None
        # Find ATM call
        valid_calls = [opt for opt in chain if opt and opt.get('option_type') == 'call' and isinstance(opt.get('strike'), (int, float)) and pd.notna(opt.get('strike'))]
        if valid_calls:
            calls_ge_current_price = [opt for opt in valid_calls if opt['strike'] >= current_price]
            atm_call = min(calls_ge_current_price, key=lambda x: x['strike']) if calls_ge_current_price else (max(valid_calls, key=lambda x: x['strike']) if valid_calls else None)
        
        # Find ATM put
        valid_puts = [opt for opt in chain if opt and opt.get('option_type') == 'put' and isinstance(opt.get('strike'), (int, float)) and pd.notna(opt.get('strike'))]
        if valid_puts:
            puts_le_current_price = [opt for opt in valid_puts if opt['strike'] <= current_price]
            atm_put = max(puts_le_current_price, key=lambda x: x['strike']) if puts_le_current_price else (min(valid_puts, key=lambda x: x['strike']) if valid_puts else None)

        call_smv_val: Optional[float] = None
        if atm_call and isinstance(atm_call.get('greeks'), dict) and atm_call['greeks'].get('smv_vol') is not None:
            try: call_smv_val = float(atm_call['greeks']['smv_vol'])
            except (ValueError, TypeError): self.logger.warning(f"Could not parse smv_vol for ATM call {atm_call.get('symbol')} as float.")
        result_dict["atm_call_strike_iv_approx"] = atm_call.get('strike') if atm_call else None
        result_dict["atm_call_smv_vol_iv_approx"] = call_smv_val

        put_smv_val: Optional[float] = None
        if atm_put and isinstance(atm_put.get('greeks'), dict) and atm_put['greeks'].get('smv_vol') is not None:
            try: put_smv_val = float(atm_put['greeks']['smv_vol'])
            except (ValueError, TypeError): self.logger.warning(f"Could not parse smv_vol for ATM put {atm_put.get('symbol')} as float.")
        result_dict["atm_put_strike_iv_approx"] = atm_put.get('strike') if atm_put else None
        result_dict["atm_put_smv_vol_iv_approx"] = put_smv_val

        avg_atm_iv: Optional[float] = None
        if call_smv_val is not None and put_smv_val is not None:
            avg_atm_iv = (call_smv_val + put_smv_val) / 2.0
        elif call_smv_val is not None:
            avg_atm_iv = call_smv_val
        elif put_smv_val is not None:
            avg_atm_iv = put_smv_val
        
        if avg_atm_iv is None:
            self.logger.warning(f"Could not determine valid ATM SMV Vol for IV approximation for {symbol} on {result_dict['source_expiration_for_iv_approx']}.")
            result_dict["error"] = "Could not calculate average ATM SMV volatility."
        else:
            result_dict[dynamic_iv_key] = round(avg_atm_iv, 4) # Store the calculated average IV
            self.logger.info(f"IV approximation for {symbol} (target DTE {eff_target_dte}): {result_dict[dynamic_iv_key]:.4f} (using {actual_dte_val}-DTE options)")
            result_dict["error"] = None # Clear error if IV calculation was successful
            
        return result_dict

    def get_average_historical_atr_pct(self, symbol: str, lookback_trading_days: Optional[int] = None, atr_period: Optional[int] = None, ohlcv_buffer_calendar_days: Optional[int] = None) -> Optional[float]:
        """Calculates average historical ATR percentage."""
        atr_pct_logger = self.logger.getChild("GetAvgHistATRPct")
        eff_lookback_days = lookback_trading_days if lookback_trading_days is not None else self.hist_atr_pct_lookback_days
        eff_atr_period = atr_period if atr_period is not None else self.hist_atr_pct_atr_period
        eff_ohlcv_buffer = ohlcv_buffer_calendar_days if ohlcv_buffer_calendar_days is not None else self.hist_atr_pct_ohlcv_buffer
        
        atr_pct_logger.info(f"Calculating avg historical ATR% for {symbol}. LookbackTradDays: {eff_lookback_days}, ATRPeriod: {eff_atr_period}")
        if eff_lookback_days <= 0 or eff_atr_period <= 0:
            atr_pct_logger.error("Lookback trading days and ATR period must be positive for ATR% calculation.")
            return None
            
        # Request slightly more history to ensure enough data points after weekend/holiday gaps
        calendar_days_to_fetch_for_atr = int((eff_lookback_days + eff_atr_period) * 1.8) + eff_ohlcv_buffer
        ohlcv_df_for_atr = self.get_ohlcv_data(symbol, interval="daily", num_days_history=calendar_days_to_fetch_for_atr)

        min_data_points_for_initial_atr = eff_atr_period
        min_data_points_overall_for_avg = eff_lookback_days + eff_atr_period -1 # Need enough data for ATR period plus the lookback window
        
        if ohlcv_df_for_atr.empty or len(ohlcv_df_for_atr) < min_data_points_for_initial_atr:
            atr_pct_logger.warning(f"Not enough historical OHLCV data for {symbol} for ATR% calculation. Need at least {min_data_points_for_initial_atr} data points, got {len(ohlcv_df_for_atr)}.")
            return None
        try:
            ohlcv_df_for_atr.sort_values(by='date', ascending=True, inplace=True)
            ohlcv_df_for_atr.reset_index(drop=True, inplace=True)

            high_low_range_atr = ohlcv_df_for_atr['high'] - ohlcv_df_for_atr['low']
            high_prev_close_range_atr = abs(ohlcv_df_for_atr['high'] - ohlcv_df_for_atr['close'].shift(1))
            low_prev_close_range_atr = abs(ohlcv_df_for_atr['low'] - ohlcv_df_for_atr['close'].shift(1))
            
            true_ranges_df_atr = pd.concat([high_low_range_atr, high_prev_close_range_atr, low_prev_close_range_atr], axis=1)
            true_range_series_atr = true_ranges_df_atr.max(axis=1, skipna=False)
            # First TR is simply High - Low
            if not true_range_series_atr.empty and pd.notna(high_low_range_atr.iloc[0]):
                 true_range_series_atr.iloc[0] = high_low_range_atr.iloc[0]
            elif not true_range_series_atr.empty: # Should not happen if high_low_range_atr has data
                 true_range_series_atr.iloc[0] = np.nan # Mark as NaN if first high_low is NaN
            
            true_range_series_atr.name = 'tr'
            atr_series_calc = true_range_series_atr.ewm(span=eff_atr_period, adjust=False, min_periods=eff_atr_period).mean()
            atr_series_calc.name = 'atr'
            
            close_prices_for_atr_pct = ohlcv_df_for_atr['close'].replace(0, np.nan) # Avoid division by zero
            atr_percentage_series = (atr_series_calc / close_prices_for_atr_pct) * 100.0
            atr_percentage_series.name = 'atr_pct'
            
            combined_df_for_avg_atr = pd.concat([ohlcv_df_for_atr['date'], atr_percentage_series], axis=1)
            combined_df_for_avg_atr.dropna(subset=['atr_pct'], inplace=True) # Drop rows where ATR% couldn't be calculated

            if len(combined_df_for_avg_atr) < eff_lookback_days:
                atr_pct_logger.warning(f"Not enough valid ATR% data points ({len(combined_df_for_avg_atr)}) to average over {eff_lookback_days} days for {symbol}. Need at least {eff_lookback_days}.")
                return None
            
            average_atr_pct_final = combined_df_for_avg_atr['atr_pct'].tail(eff_lookback_days).mean()
            if pd.isna(average_atr_pct_final):
                atr_pct_logger.warning(f"Calculated average ATR% is NaN for {symbol}. This might happen with very sparse data.")
                return None
                
            atr_pct_logger.info(f"Average historical ATR% for {symbol} over last {eff_lookback_days} trading days (ATR period {eff_atr_period}): {average_atr_pct_final:.4f}%")
            return round(average_atr_pct_final, 4)
        except Exception as e_atr_pct:
            atr_pct_logger.error(f"Error calculating average historical ATR% for {symbol}: {e_atr_pct}", exc_info=True)
            return None

    def fetch_market_data_bundle(self, symbols: List[str], ohlcv_days: Optional[int] = None, iv_approx_dte: Optional[int] = None) -> Dict[str, Dict[str, Any]]:
        """
        Fetches a bundle of market data for each symbol:
        - Current Quote (raw dict from API, includes more than just price)
        - Historical OHLCV (DataFrame)
        - IV Approximation (Dict with various details including the final IV approx key)
        - Option Expirations (List of date objects)
        - Average Historical ATR % (float, added to iv_and_quote_data dict)
        Returns a dict keyed by symbol. Each symbol's value is a dict with standardized keys.
        """
        bundle_logger = self.logger.getChild("FetchMarketDataBundle")
        bundle_logger.info(f"Fetching Tradier market data bundle V2.6.0 for symbols: {symbols}")
        results_bundle: Dict[str, Dict[str, Any]] = {}

        eff_ohlcv_days = ohlcv_days if ohlcv_days is not None else self.default_ohlcv_days_history
        eff_iv_approx_dte = iv_approx_dte if iv_approx_dte is not None else self.default_iv_approx_dte

        for symbol_item in symbols:
            symbol_upper = symbol_item.strip().upper()
            if not symbol_upper:
                bundle_logger.warning(f"Skipping empty symbol string: '{symbol_item}'")
                continue

            bundle_logger.info(f"--- Fetching data for symbol: {symbol_upper} ---")
            symbol_data_bundle: Dict[str, Any] = {
                "symbol": symbol_upper,
                "iv_and_quote_data": {}, # Initialize as empty dict
                "historical_ohlcv_df": pd.DataFrame(),
                "expiration_calendar": [],
                "error": None # Overall error for this symbol's bundle
            }
            
            accumulated_errors_for_symbol: List[str] = []

            # 1. Get Quote
            quote_data_dict = self.get_underlying_quote(symbol_upper)
            if quote_data_dict and not quote_data_dict.get("error"):
                symbol_data_bundle["iv_and_quote_data"].update(quote_data_dict) # Merge quote data
            elif quote_data_dict and quote_data_dict.get("error"):
                accumulated_errors_for_symbol.append(f"Quote fetch failed: {quote_data_dict['error']}")
            else: # Should not happen if get_underlying_quote returns a dict with error
                accumulated_errors_for_symbol.append("Quote fetch returned unexpected result (None or no error key).")

            # 2. Get OHLCV Data
            if eff_ohlcv_days > 0 : # Only fetch if days > 0
                ohlcv_df_result = self.get_ohlcv_data(symbol_upper, num_days_history=eff_ohlcv_days)
                if not ohlcv_df_result.empty:
                    symbol_data_bundle["historical_ohlcv_df"] = ohlcv_df_result
                else: # get_ohlcv_data now returns empty DF on error, no error string needed here
                    accumulated_errors_for_symbol.append("OHLCV fetch returned empty DataFrame or failed.")
            else:
                bundle_logger.info(f"Skipping OHLCV fetch for {symbol_upper} as eff_ohlcv_days is {eff_ohlcv_days}.")
            
            # 3. Get IV Approximation
            iv_approximation_dict = self.get_iv_approximation(symbol_upper, target_dte_override=eff_iv_approx_dte)
            if iv_approximation_dict: # Always a dict, check for error key inside
                if iv_approximation_dict.get("error"):
                     accumulated_errors_for_symbol.append(f"IV approximation failed: {iv_approximation_dict['error']}")
                # Merge all details from iv_approximation_dict, including the dynamic IV key or error
                symbol_data_bundle["iv_and_quote_data"].update(iv_approximation_dict) 
            else: # Should not happen if get_iv_approximation always returns a dict
                accumulated_errors_for_symbol.append("IV approximation returned unexpected result (None).")
                
            # 4. Get Option Expirations
            expirations_list_dates = self.get_option_expirations(symbol_upper) # Returns List[date]
            if expirations_list_dates:
                symbol_data_bundle["expiration_calendar"] = expirations_list_dates
            else: # Empty list could mean error or genuinely no expirations
                accumulated_errors_for_symbol.append("Expirations fetch failed or returned empty list.")
            
            # 5. Get Average Historical ATR %
            avg_atr_pct_val = self.get_average_historical_atr_pct(symbol_upper) # Uses instance defaults for lookback/period
            if avg_atr_pct_val is not None:
                symbol_data_bundle["iv_and_quote_data"]["average_historical_atr_pct"] = avg_atr_pct_val
            else:
                accumulated_errors_for_symbol.append("Average Historical ATR % calculation failed or returned None.")

            if accumulated_errors_for_symbol:
                symbol_data_bundle["error"] = "; ".join(accumulated_errors_for_symbol)
                bundle_logger.warning(f"Partial data or errors encountered for {symbol_upper}: {symbol_data_bundle['error']}")
            else:
                bundle_logger.info(f"Successfully fetched all Tradier data components for {symbol_upper}.")

            results_bundle[symbol_upper] = symbol_data_bundle
            
            if len(symbols) > 1 and symbol_item != symbols[-1]: # Avoid sleep after last symbol
                inter_call_delay_cfg = self.settings.get("inter_call_delay_seconds", 0.25) # Get from effective_settings
                if inter_call_delay_cfg > 0:
                    self.logger.debug(f"Applying inter-symbol delay of {inter_call_delay_cfg:.2f}s.")
                    pytime.sleep(inter_call_delay_cfg)

        bundle_logger.info(f"Tradier market data bundle fetch process complete for {len(symbols)} symbol(s).")
        return results_bundle

    def shutdown(self):
        self.logger.info(f"TradierDataFetcher V{self.get_version()} shutdown sequence initiated.")
        # No explicit close/logout needed for Tradier token-based API typically.
        self.logger.info(f"TradierDataFetcher V{self.get_version()} shutdown complete.")

    def get_version(self) -> str:
        return "2.6.0"

# --- Main Test Block (Updated for Rewritten Fetcher) ---
if __name__ == '__main__':
    # Setup basic logging if this script is run directly
    if not logging.getLogger().hasHandlers():
        _test_formatter_main = logging.Formatter('[%(levelname)s] (%(name)s:%(lineno)d) %(asctime)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
        _test_handler_main = logging.StreamHandler(sys.stdout)
        _test_handler_main.setFormatter(_test_formatter_main)
        logging.getLogger().addHandler(_test_handler_main)
        logging.getLogger().setLevel(logging.DEBUG) # Set root logger to DEBUG for testing

    module_test_logger_tradier = logging.getLogger(f"{__name__}_TradierTestMain_V2_6_0")
    module_test_logger_tradier.setLevel(logging.DEBUG) # Ensure test logger is DEBUG
    # Ensure the fetcher's own logger also gets DEBUG level for testing
    logging.getLogger("enhanced_tradier_fetcher_v2").setLevel(logging.DEBUG) # Use actual module name

    module_test_logger_tradier.info(f"--- Starting TradierDataFetcher Standalone Test (V{TradierDataFetcher().get_version()}) ---")

    test_tradier_settings_main = {} # Start with empty to test defaults, or load from a test config
    # IMPORTANT: For live testing, ensure your TRADIER_PRODUCTION_TOKEN
    # is set in environment variables, or update "access_token_direct" in DEFAULT_TRADIER_FETCHER_SETTINGS
    # or pass it via test_tradier_settings_main for the test instance.
    # Example: test_tradier_settings_main = {"access_token_direct": "YOUR_ACTUAL_TOKEN_HERE_FOR_TEST_ONLY"}
    
    if not os.getenv(DEFAULT_TRADIER_FETCHER_SETTINGS["access_token_env_var"]) and \
       DEFAULT_TRADIER_FETCHER_SETTINGS["access_token_direct"] == "YOUR_TRADIER_TOKEN_PLACEHOLDER":
        module_test_logger_tradier.critical(
            f"Tradier API token NOT found in ENV VAR '{DEFAULT_TRADIER_FETCHER_SETTINGS['access_token_env_var']}' "
            "and placeholder not changed in script's DEFAULT_TRADIER_FETCHER_SETTINGS. "
            "Live API calls in test WILL FAIL. Please set credentials for testing."
        )
    
    tradier_fetcher_instance_test = TradierDataFetcher(
        tradier_settings=test_tradier_settings_main, # Pass empty or your specific test settings
        main_system_log_level="DEBUG" # Force DEBUG for detailed test output
    )

    if tradier_fetcher_instance_test.initialization_failed:
        module_test_logger_tradier.critical("TradierDataFetcher failed to initialize properly in test (likely missing token). Aborting further tests.")
    else:
        test_symbols_main = ["SPY", "AAPL", "NONEXISTENTXYZ"] # Test with a known bad symbol too
        test_ohlcv_days = 15 # Shorter for quicker test
        test_iv_dte = 7   # Different from default

        # Test 1: Individual component - IV Approximation for a specific DTE
        module_test_logger_tradier.info(f"\n--- Test 1: IV Approximation for {test_symbols_main[0]} (DTE={test_iv_dte}) ---")
        iv_details_single = tradier_fetcher_instance_test.get_iv_approximation(test_symbols_main[0], target_dte_override=test_iv_dte)
        if iv_details_single:
            module_test_logger_tradier.info(f"IV Approx Details for {test_symbols_main[0]}: {iv_details_single}")
            expected_iv_key_test = f"tradier_iv{test_iv_dte}_approx_smv_avg"
            if iv_details_single.get("error"):
                module_test_logger_tradier.error(f"  Error in IV approx: {iv_details_single['error']}")
            elif expected_iv_key_test in iv_details_single and iv_details_single[expected_iv_key_test] is not None:
                module_test_logger_tradier.info(f"  SUCCESS: Found IV key '{expected_iv_key_test}' with value: {iv_details_single[expected_iv_key_test]}")
            else:
                module_test_logger_tradier.error(f"  FAIL: Expected IV key '{expected_iv_key_test}' not found or is None in results.")
        else:
            module_test_logger_tradier.error(f"  IV approximation for {test_symbols_main[0]} returned None or unexpected structure.")


        # Test 2: Fetch market data bundle for multiple symbols
        module_test_logger_tradier.info(f"\n--- Test 2: Fetch Market Data Bundle for {test_symbols_main} (OHLCV Days: {test_ohlcv_days}, IV DTE: {test_iv_dte}) ---")
        full_bundle_result = tradier_fetcher_instance_test.fetch_market_data_bundle(
            symbols=test_symbols_main, 
            ohlcv_days=test_ohlcv_days, 
            iv_approx_dte=test_iv_dte
        )
        
        for sym_bundle_key_test in test_symbols_main:
            data_for_symbol_test = full_bundle_result.get(sym_bundle_key_test)
            module_test_logger_tradier.info(f"\n--- Results for Symbol: {sym_bundle_key_test} ---")
            if data_for_symbol_test:
                if data_for_symbol_test.get("error"):
                    module_test_logger_tradier.error(f"  Bundle Error: {data_for_symbol_test['error']}")
                else:
                    module_test_logger_tradier.info("  Bundle fetched (potentially with partial data if sub-components failed).")

                # Check iv_and_quote_data specifically for the dynamic IV key
                iv_quote_bundle_part = data_for_symbol_test.get("iv_and_quote_data", {})
                module_test_logger_tradier.info(f"  IV & Quote Keys: {list(iv_quote_bundle_part.keys())}")
                expected_iv_key_in_bundle = f"tradier_iv{test_iv_dte}_approx_smv_avg"
                if expected_iv_key_in_bundle in iv_quote_bundle_part and iv_quote_bundle_part[expected_iv_key_in_bundle] is not None:
                    module_test_logger_tradier.info(f"    OK: Found '{expected_iv_key_in_bundle}': {iv_quote_bundle_part[expected_iv_key_in_bundle]} in bundle.")
                elif iv_quote_bundle_part.get("error") and expected_iv_key_in_bundle not in iv_quote_bundle_part : # If an error key is present from IV approx itself
                    module_test_logger_tradier.warning(f"    WARN: IV data for '{expected_iv_key_in_bundle}' likely missing due to error: {iv_quote_bundle_part.get('error')}")
                elif not iv_quote_bundle_part.get("error") and expected_iv_key_in_bundle not in iv_quote_bundle_part:
                     module_test_logger_tradier.error(f"    FAIL: Key '{expected_iv_key_in_bundle}' MISSING from iv_and_quote_data in bundle for {sym_bundle_key_test} and no explicit IV error key.")

                ohlcv_df_test_check = data_for_symbol_test.get('historical_ohlcv_df', pd.DataFrame())
                module_test_logger_tradier.info(f"  OHLCV DF Shape: {ohlcv_df_test_check.shape}")
                if not ohlcv_df_test_check.empty:
                    module_test_logger_tradier.debug(f"  OHLCV Head:\n{ohlcv_df_test_check.head(2).to_string()}")

                exp_cal_test_check = data_for_symbol_test.get('expiration_calendar', [])
                module_test_logger_tradier.info(f"  Expirations Count: {len(exp_cal_test_check)}")
                if exp_cal_test_check:
                    module_test_logger_tradier.debug(f"  Sample Expirations: {exp_cal_test_check[:3]}")
            else:
                module_test_logger_tradier.error(f"  No data bundle returned at all for symbol {sym_bundle_key_test}")

        tradier_fetcher_instance_test.shutdown()

    module_test_logger_tradier.info(f"--- TradierDataFetcher Standalone Test (V{TradierDataFetcher().get_version()}) Finished ---")