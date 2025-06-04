# /home/ubuntu/dashboard_v2/utils.py
# -*- coding: utf-8 -*-
"""
Utility functions for the Enhanced Options Dashboard V2, including
configuration management, plotting helpers, caching interaction wrappers,
formatting utilities, and data manipulation helpers.
(Version: Utils Canon V3.0.0 - Full Unabridged with Enhancements)
"""

# Standard Library Imports
import logging
import time as pytime # Alias to avoid conflict with datetime.time
import json
import copy # For deepcopy
import os
from datetime import datetime, timedelta, time as dt_time, date # dt_time and date for clarity
from typing import Optional, List, Dict, Any, Tuple, Union, Callable, Deque
from collections import deque
from dateutil import parser as date_parser # For robust date string parsing
import html as std_html # Standard Python HTML library for escaping

# Third-Party Imports
import pandas as pd
import numpy as np
import plotly.graph_objects as go # <<< --- ADD THIS IMPORT ---
from dash import html as dash_html # Dash's HTML components, aliased for clarity

# --- Module-Specific Logger Setup ---
# The logger for this utility module.
# Its level should ideally be configured by the main application script.
logger = logging.getLogger(__name__)
logger.info("utils.py (V3.0.1 Canon): Logger initialized.") # Incremented version for tracking

# --- Fallback Plotly Template (if styling import fails) ---
# This is used by create_empty_figure if the main styling module cannot be imported.
_PLOTLY_TEMPLATE_FALLBACK_FOR_UTILS_MODULE = {"layout": go.Layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")}
PLOTLY_TEMPLATE_EFFECTIVE_FOR_UTILS: Dict[str, Any]

try:
    # Attempt to import the primary Plotly template from the styling module
    from .styling import PLOTLY_TEMPLATE_DARK as imported_plotly_template_from_styling
    if isinstance(imported_plotly_template_from_styling, dict) and "layout" in imported_plotly_template_from_styling:
        PLOTLY_TEMPLATE_EFFECTIVE_FOR_UTILS = imported_plotly_template_from_styling
        logger.debug("UTILS.PY (V3.0.1): Successfully imported and assigned PLOTLY_TEMPLATE_DARK from .styling.")
    else:
        logger.warning("UTILS.PY (V3.0.1): Imported PLOTLY_TEMPLATE_DARK from .styling is not in the expected format. Using fallback.")
        PLOTLY_TEMPLATE_EFFECTIVE_FOR_UTILS = _PLOTLY_TEMPLATE_FALLBACK_FOR_UTILS_MODULE
except ImportError:
    logger.warning("UTILS.PY (V3.0.1): Could not import PLOTLY_TEMPLATE_DARK from .styling. Using basic plotly_dark fallback for empty figures.")
    PLOTLY_TEMPLATE_EFFECTIVE_FOR_UTILS = _PLOTLY_TEMPLATE_FALLBACK_FOR_UTILS_MODULE
except Exception as e_utils_styling_imp:
    logger.error(f"UTILS.PY (V3.0.1): Unexpected error importing PLOTLY_TEMPLATE_DARK from .styling: {e_utils_styling_imp}. Using fallback.", exc_info=True)
    PLOTLY_TEMPLATE_EFFECTIVE_FOR_UTILS = _PLOTLY_TEMPLATE_FALLBACK_FOR_UTILS_MODULE


# --- Configuration Management ---
CONFIG_CACHE_FOR_UTILS_MODULE: Optional[Dict[str, Any]] = None # Module-level cache for the app config
DEFAULT_CONFIG_FILENAME_FOR_UTILS_MODULE: str = "config_v2.json" # Default config filename

def load_app_config_into_cache(config_path_param: str = DEFAULT_CONFIG_FILENAME_FOR_UTILS_MODULE) -> Dict[str, Any]:
    """
    Loads the main application JSON configuration file into a module-level cache.
    Resolves the config path relative to the project root (parent of this utils.py's directory).
    Returns the loaded configuration dictionary (empty if an error occurs).
    """
    global CONFIG_CACHE_FOR_UTILS_MODULE
    load_config_logger = logger.getChild("LoadAppConfigIntoCache_UtilsV3")
    
    # Determine absolute path to config file
    # Assumes utils.py is in a subdirectory (e.g., dashboard_v2) of the project root
    absolute_config_path: str
    if os.path.isabs(config_path_param):
        absolute_config_path = config_path_param
    else:
        try:
            # Assumes utils.py is in a package like 'dashboard_v2'
            # Then project_root is parent of 'dashboard_v2'
            current_script_dir = os.path.dirname(os.path.abspath(__file__))
            project_root_dir = os.path.dirname(current_script_dir)
            absolute_config_path = os.path.normpath(os.path.join(project_root_dir, config_path_param))
        except NameError: # __file__ not defined (e.g. some interactive/testing contexts)
            # Fallback to CWD, hoping it's the project root
            absolute_config_path = os.path.normpath(os.path.join(os.getcwd(), config_path_param))
            load_config_logger.debug(f"Using CWD-relative path for config due to NameError: {absolute_config_path}")

    # Only reload if the cache is None or if a different config_path is explicitly requested
    # (though typically, this function is called once with the default path by the main app).
    if CONFIG_CACHE_FOR_UTILS_MODULE is not None and absolute_config_path == CONFIG_CACHE_FOR_UTILS_MODULE.get("_config_file_path_cached_at"):
        load_config_logger.debug(f"UTILS (V3.0.1): Config from '{absolute_config_path}' already cached and path matches. Skipping reload.")
        return CONFIG_CACHE_FOR_UTILS_MODULE

    load_config_logger.info(f"UTILS (V3.0.1): Attempting to load application config from: '{absolute_config_path}'")
    loaded_configuration: Dict[str, Any] = {}
    try:
        with open(absolute_config_path, "r", encoding="utf-8") as f_config:
            loaded_configuration = json.load(f_config)
        if not isinstance(loaded_configuration, dict):
            load_config_logger.error(f"UTILS (V3.0.1): Configuration file at '{absolute_config_path}' did not contain a valid JSON dictionary. Returning empty config.")
            loaded_configuration = {}
        else:
            loaded_configuration["_config_file_path_cached_at"] = absolute_config_path # Store the path used
            load_config_logger.info(f"UTILS (V3.0.1): Successfully loaded and cached application config from '{absolute_config_path}'.")
    except FileNotFoundError:
        load_config_logger.error(f"UTILS (V3.0.1): Application configuration file NOT FOUND at: '{absolute_config_path}'. Returning empty config.")
        loaded_configuration = {"_config_file_path_cached_at": absolute_config_path, "_config_load_error": "FileNotFound"}
    except json.JSONDecodeError as e_json_decode:
        load_config_logger.error(f"UTILS (V3.0.1): Error decoding JSON from config file '{absolute_config_path}': {e_json_decode}. Returning empty config.")
        loaded_configuration = {"_config_file_path_cached_at": absolute_config_path, "_config_load_error": f"JSONDecodeError: {e_json_decode}"}
    except Exception as e_load_generic:
        load_config_logger.critical(f"UTILS (V3.0.1): Unexpected CRITICAL error loading config file '{absolute_config_path}': {e_load_generic}.", exc_info=True)
        loaded_configuration = {"_config_file_path_cached_at": absolute_config_path, "_config_load_error": f"UnexpectedError: {e_load_generic}"}
    
    CONFIG_CACHE_FOR_UTILS_MODULE = loaded_configuration
    return CONFIG_CACHE_FOR_UTILS_MODULE

def get_cached_config() -> Dict[str, Any]:
    """Returns the cached application configuration, loading it if not already cached."""
    if CONFIG_CACHE_FOR_UTILS_MODULE is None:
        logger.info("UTILS (V3.0.1): get_cached_config() called but module cache was None. Triggering initial load with default path.")
        return load_app_config_into_cache() # Uses DEFAULT_CONFIG_FILENAME_FOR_UTILS_MODULE
    return CONFIG_CACHE_FOR_UTILS_MODULE

def get_config_value(
    path_keys: List[str],
    default_value_to_return: Any = None,
    config_data_source: Optional[Dict[str, Any]] = None # Allow passing a specific config dict
) -> Any:
    """
    Safely retrieves a nested value from a configuration dictionary.
    Uses the module-cached config if config_data_source is not provided.
    """
    config_lookup_logger = logger.getChild("GetConfigValue_UtilsV3")
    
    source_description = "module-cached APP_CONFIG"
    config_to_inspect: Dict[str, Any]
    if isinstance(config_data_source, dict):
        config_to_inspect = config_data_source
        source_description = "provided config_data_source"
    else:
        config_to_inspect = get_cached_config() # Ensures cache is loaded if None

    current_level: Any = config_to_inspect
    try:
        for key_segment in path_keys:
            if isinstance(current_level, dict) and key_segment in current_level:
                current_level = current_level[key_segment]
            else:
                # config_lookup_logger.debug(f"Config path '{' -> '.join(path_keys)}' not fully found. Segment '{key_segment}' missing or not in dict. Source: {source_description}. Defaulting.")
                return default_value_to_return
        # config_lookup_logger.debug(f"Config value for '{' -> '.join(path_keys)}' found in {source_description}: {type(current_level)}")
        return current_level
    except KeyError: # Should be caught by the check `key_segment in current_level`
        # config_lookup_logger.debug(f"Config path '{' -> '.join(path_keys)}' resulted in KeyError from {source_description}. Defaulting.")
        return default_value_to_return
    except TypeError: # If a segment is not a dict, but path tries to go deeper
        # config_lookup_logger.warning(f"Config path '{' -> '.join(path_keys)}' encountered TypeError (segment not a dict) in {source_description}. Defaulting.")
        return default_value_to_return
    except Exception as e_get_cfg_unexpected:
        config_lookup_logger.error(f"Unexpected error retrieving config for path '{' -> '.join(path_keys)}' from {source_description}: {e_get_cfg_unexpected}. Defaulting.", exc_info=True)
        return default_value_to_return

# Initialize config cache at module load time for subsequent get_config_value calls
if CONFIG_CACHE_FOR_UTILS_MODULE is None:
    logger.info("UTILS.PY (V3.0.1 Module Level): CONFIG_CACHE_FOR_UTILS_MODULE is None. Triggering initial load with default path to populate cache.")
    load_app_config_into_cache()

# --- Define CACHE_TIMEOUT_SECONDS_UTILS based on loaded config ---
_cache_timeout_config_path = ["system_settings", "dashboard_cache_timeout_seconds"]
_cache_timeout_default = 300 # Default 5 minutes
CACHE_TIMEOUT_SECONDS_UTILS: int = get_config_value(_cache_timeout_config_path, _cache_timeout_default)
if not (isinstance(CACHE_TIMEOUT_SECONDS_UTILS, int) and CACHE_TIMEOUT_SECONDS_UTILS >= 0): # Allow 0 for no timeout if intended
    logger.warning(f"UTILS (V3.0.1): Invalid CACHE_TIMEOUT_SECONDS_UTILS '{CACHE_TIMEOUT_SECONDS_UTILS}' from config path '{'->'.join(_cache_timeout_config_path)}'. Defaulting to {_cache_timeout_default}s.")
    CACHE_TIMEOUT_SECONDS_UTILS = _cache_timeout_default
logger.info(f"UTILS (V3.0.1): Global cache timeout (CACHE_TIMEOUT_SECONDS_UTILS) set to {CACHE_TIMEOUT_SECONDS_UTILS} seconds.")


# --- Plotting Utilities ---
def create_empty_figure(title: str = "Awaiting Data...", height: Optional[int] = None, reason: Optional[str] = "Not specified") -> go.Figure:
    """
    Creates a standardized empty Plotly figure with a message.
    Uses the effective Plotly template loaded by this module.
    """
    empty_fig_creation_logger = logger.getChild("CreateEmptyFigure_UtilsV3")
    empty_fig_creation_logger.debug(f"Creating empty figure. Title: '{title}', Reason: '{reason}', Requested Height: {height}")
    
    fig = go.Figure()
    
    # Determine effective height
    final_height: int = 600 # Default fallback height
    if isinstance(height, int) and height > 100:
        final_height = height
    else: # Try to get from config if not provided or invalid
        cfg_height = get_config_value(["visualization_settings", "dashboard", "default_graph_height"], 600)
        if isinstance(cfg_height, int) and cfg_height > 100:
            final_height = cfg_height
        # else, final_height remains the hardcoded 600

    # Apply base layout template
    # PLOTLY_TEMPLATE_EFFECTIVE_FOR_UTILS is set at module load time
    if isinstance(PLOTLY_TEMPLATE_EFFECTIVE_FOR_UTILS, dict) and "layout" in PLOTLY_TEMPLATE_EFFECTIVE_FOR_UTILS:
        fig.update_layout(PLOTLY_TEMPLATE_EFFECTIVE_FOR_UTILS["layout"])
        empty_fig_creation_logger.debug(f"Applied layout from PLOTLY_TEMPLATE_EFFECTIVE_FOR_UTILS (dict).")
    elif isinstance(PLOTLY_TEMPLATE_EFFECTIVE_FOR_UTILS, str):
        fig.update_layout(template=PLOTLY_TEMPLATE_EFFECTIVE_FOR_UTILS)
        empty_fig_creation_logger.debug(f"Applied layout template string: {PLOTLY_TEMPLATE_EFFECTIVE_FOR_UTILS}.")
    else: # Ultimate fallback if template loading failed badly
        fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        empty_fig_creation_logger.warning("PLOTLY_TEMPLATE_EFFECTIVE_FOR_UTILS was in an unexpected format. Applied basic 'plotly_dark' with transparent bg.")

    # Customize for empty figure message
    title_html = f"<i>{std_html.escape(str(title))}<br><small style='color:grey; font-size:0.8em;'>({std_html.escape(str(reason))})</small></i>"
    fig.update_layout(
        title={
            "text": title_html, "y": 0.5, "x": 0.5,
            "xanchor": "center", "yanchor": "middle",
            "font": {"size": 16, "color": "#aaaaaa"} # Ensure font color is visible on dark theme
        },
        height=final_height,
        xaxis={"visible": False, "showgrid": False, "zeroline": False},
        yaxis={"visible": False, "showgrid": False, "zeroline": False},
        annotations=[], # Clear any annotations from template
        # paper_bgcolor and plot_bgcolor already set by template or fallback above
    )
    empty_fig_creation_logger.info(f"Empty figure created with title: '{title}', reason: '{reason}', height: {final_height}px.")
    return fig

# --- Data Handling & Caching Utilities ---
def get_cached_data_bundle(
    cache_key: Optional[str],
    server_cache_storage: Dict[str, Tuple[float, Dict[str, Any]]] # Explicitly pass the cache dict
) -> Optional[Dict[str, Any]]:
    """Retrieves a data bundle from the server-side cache if valid and not expired."""
    cache_retrieve_logger = logger.getChild("GetCachedDataBundle_UtilsV3")
    if not (cache_key and isinstance(cache_key, str)):
        cache_retrieve_logger.debug(f"Attempted to retrieve data with invalid cache key: '{cache_key}'. Returning None.")
        return None
    
    cached_entry = server_cache_storage.get(cache_key)
    if cached_entry is None:
        cache_retrieve_logger.debug(f"Cache MISS for key: '{cache_key}'.")
        return None
        
    try:
        stored_timestamp, stored_data_bundle = cached_entry
        if not (isinstance(stored_timestamp, (int, float)) and isinstance(stored_data_bundle, dict)):
            raise TypeError("Cached entry has incorrect format.")
            
        # Use the module-level CACHE_TIMEOUT_SECONDS_UTILS
        if CACHE_TIMEOUT_SECONDS_UTILS > 0 and (pytime.time() - stored_timestamp) > CACHE_TIMEOUT_SECONDS_UTILS:
            cache_retrieve_logger.info(f"Cache item for key '{cache_key}' has EXPIRED (age > {CACHE_TIMEOUT_SECONDS_UTILS}s). Removing from cache.")
            server_cache_storage.pop(cache_key, None) # Remove expired item
            return None
        
        # Critical check: Ensure 'processed_options_df' is not a DataFrame in the cache
        # It should have been converted to list of dicts by set_cached_data_bundle
        if isinstance(stored_data_bundle.get("processed_options_df"), pd.DataFrame):
             cache_retrieve_logger.critical(f"CACHE CORRUPTION DETECTED for key '{cache_key}': 'processed_options_df' is a DataFrame object in cache! This should be a list of records. Invalidating and removing entry.")
             server_cache_storage.pop(cache_key, None)
             return None
        if isinstance(stored_data_bundle.get("final_metric_rich_df_obj"), pd.DataFrame):
             cache_retrieve_logger.critical(f"CACHE CORRUPTION DETECTED for key '{cache_key}': 'final_metric_rich_df_obj' is a DataFrame object in cache! This should be a list of records for 'processed_options_df' and the object itself for the app. This indicates an issue in how data was stored or what this function expects. Assuming 'final_metric_rich_df_obj' key in bundle is for the DataFrame object which is NOT JSON serializable by default. This part of cache is for data to be sent to client (JSON).")
             # This needs careful thought: if `final_metric_rich_df_obj` is the actual DataFrame for server-side use,
             # then it should NOT be deepcopied for client-side (JSON) purposes.
             # The `set_cached_data_bundle` should handle what to store for JSON.
             # For now, let's assume this function is for retrieving the JSON-serializable bundle.

        cache_retrieve_logger.info(f"Cache HIT and data VALID for key: '{cache_key}'.")
        # Return a deep copy to prevent modification of the cached object by consumers
        return copy.deepcopy(stored_data_bundle)
        
    except (TypeError, KeyError) as e_cache_format:
        cache_retrieve_logger.error(f"Corrupted cache entry format for key '{cache_key}': {e_cache_format}. Removing entry.", exc_info=True)
        server_cache_storage.pop(cache_key, None)
        return None
    except Exception as e_cache_retrieve_unexpected:
        cache_retrieve_logger.error(f"Unexpected error retrieving or validating cache for key '{cache_key}': {e_cache_retrieve_unexpected}. Removing entry.", exc_info=True)
        server_cache_storage.pop(cache_key, None)
        return None


def set_cached_data_bundle(
    cache_key: Optional[str],
    data_bundle_to_store: Dict[str, Any], # This is the full ITS output bundle
    server_cache_storage: Dict[str, Tuple[float, Dict[str, Any]]] # Explicitly pass the cache dict
):
    """
    Stores a data bundle in the server-side cache.
    Converts DataFrames within the bundle to JSON-serializable format (list of records)
    for keys like 'processed_options_df' and 'aggregated_strike_data'.
    The 'final_metric_rich_df_obj' is kept as a DataFrame object for server-side use if needed later,
    but a JSON-safe version is made for what's stored under 'processed_options_df'.
    """
    cache_store_logger = logger.getChild("SetCachedDataBundle_UtilsV3")
    if not (cache_key and isinstance(cache_key, str)):
        cache_store_logger.error(f"Invalid cache key provided: '{cache_key}'. Cannot store data.")
        return
    if not isinstance(data_bundle_to_store, dict):
        cache_store_logger.error(f"Data bundle to store for key '{cache_key}' is not a dictionary (type: {type(data_bundle_to_store)}). Cannot store.")
        return

    # Create a bundle specifically for caching, making parts JSON-safe
    # The actual DataFrame object for 'final_metric_rich_df_obj' is NOT directly stored
    # in the JSON-serializable part of the cache if it's large or complex.
    # The ITS bundle should already distinguish between the list-of-dicts version and the DataFrame object.
    
    # Create a deep copy to modify for caching, preserving original bundle
    bundle_for_json_cache = {}
    try:
        # Selectively deepcopy, be careful with large DataFrames if not handled by ITS output structure
        for key, value in data_bundle_to_store.items():
            if key == "final_metric_rich_df_obj" and isinstance(value, pd.DataFrame):
                # This DataFrame object is for server-side use (e.g., history)
                # and is NOT part of what's typically JSON serialized for client-side dcc.Store.
                # The 'processed_options_df' (list of dicts) is for that.
                # So, we don't add it to bundle_for_json_cache.
                # The ITS output structure must be clear about this.
                pass
            elif isinstance(value, pd.DataFrame):
                bundle_for_json_cache[key] = value.to_dict(orient='records')
            elif isinstance(value, (list, dict, tuple, str, int, float, bool, type(None))):
                 bundle_for_json_cache[key] = copy.deepcopy(value) # Deepcopy serializable types
            else:
                 bundle_for_json_cache[key] = str(value) # Fallback for other types
        
    except Exception as e_deepcopy_cache:
        cache_store_logger.error(f"Deepcopy or selective copy failed for data bundle key '{cache_key}': {e_deepcopy_cache}. Storing with potential issues or string conversion.", exc_info=True)
        # Fallback to a simpler string representation or risk storing mutable objects
        # For safety, let's just store a simple error representation if deepcopy fails badly.
        bundle_for_json_cache = {"error": f"Failed to prepare bundle for caching: {e_deepcopy_cache}"}

    # Ensure specific DataFrame keys are lists of records for JSON serialization
    keys_to_convert_to_records = ["processed_options_df", "aggregated_strike_data"] # Add others if needed
    for df_key in keys_to_convert_to_records:
        if df_key in bundle_for_json_cache and isinstance(bundle_for_json_cache[df_key], pd.DataFrame):
            cache_store_logger.debug(f"Converting DataFrame '{df_key}' to list of records for JSON cache (key: '{cache_key}').")
            bundle_for_json_cache[df_key] = bundle_for_json_cache[df_key].to_dict(orient='records')
        elif df_key in data_bundle_to_store and isinstance(data_bundle_to_store[df_key], pd.DataFrame) and df_key not in bundle_for_json_cache:
            # If it was skipped by selective copy but exists in original and is DataFrame, convert it for the JSON cache.
            cache_store_logger.debug(f"Converting original DataFrame '{df_key}' to list of records for JSON cache (key: '{cache_key}').")
            bundle_for_json_cache[df_key] = data_bundle_to_store[df_key].to_dict(orient='records')


    server_cache_storage[cache_key] = (pytime.time(), bundle_for_json_cache)
    cache_store_logger.info(f"Stored/Updated data bundle in server-side cache with key: '{cache_key}'. Current cache size: {len(server_cache_storage)} items.")


def update_data_bundle_history_for_symbol(
    symbol: str,
    df_for_history_storage: Optional[pd.DataFrame], # This should be the 'final_metric_rich_df_obj'
    fetch_timestamp_iso_str: Optional[str],
    component_history_storage: Dict[str, Deque[Tuple[float, pd.DataFrame]]] # Explicitly pass history cache
):
    """Updates the historical data deque for a given symbol with a new DataFrame snapshot."""
    history_update_logger = logger.getChild("UpdateDataBundleHistory_UtilsV3")
    
    app_config_for_history = get_cached_config() # Get full app config
    # Get strike column name from visualization_settings, as processor might have renamed it
    viz_cols_config = get_config_value(["visualization_settings", "mspi_visualizer", "column_names"], {}, app_config_for_history)
    history_strike_col_name = str(viz_cols_config.get("strike", "strike_price")) # Default to 'strike_price' if not found
    
    history_update_logger.debug(f"Attempting to update history for '{symbol}' using strike col: '{history_strike_col_name}'. DF for history type: {type(df_for_history_storage)}")

    if symbol not in component_history_storage:
        history_maxlen_val = get_config_value(["system_settings", "df_history_maxlen_its"], 10, app_config_for_history)
        if not (isinstance(history_maxlen_val, int) and history_maxlen_val > 0):
            history_update_logger.warning(f"Invalid df_history_maxlen_its '{history_maxlen_val}'. Defaulting to 10.")
            history_maxlen_val = 10
        component_history_storage[symbol] = deque(maxlen=history_maxlen_val)
        history_update_logger.info(f"Initialized history deque for symbol '{symbol}' with maxlen={history_maxlen_val}.")

    current_history_deque = component_history_storage[symbol]
    if not (isinstance(df_for_history_storage, pd.DataFrame) and not df_for_history_storage.empty):
        history_update_logger.debug(f"No valid DataFrame provided to store in history for '{symbol}'. Skipping update.")
        return

    # Ensure essential columns for historical comparison or ghost traces are present
    # Example: 'volmbs_5m', 'valuebs_5m' for VolVal ghosts, or other metrics.
    # This depends on what downstream functions using history expect.
    # For now, we just store the provided DataFrame.
    # It's crucial that df_for_history_storage *is* the actual DataFrame object, not a list of dicts.
    
    timestamp_unix_float: float = pytime.time() # Default to current time
    if fetch_timestamp_iso_str and isinstance(fetch_timestamp_iso_str, str):
        try:
            # Ensure proper ISO format parsing, including handling 'Z' for UTC
            dt_obj = date_parser.isoparse(fetch_timestamp_iso_str.replace("Z", "+00:00"))
            timestamp_unix_float = dt_obj.timestamp()
        except Exception as e_parse_ts_hist:
            history_update_logger.warning(f"Could not parse fetch_timestamp_iso_str '{fetch_timestamp_iso_str}' for history (Symbol: {symbol}): {e_parse_ts_hist}. Using current time for history entry.")
            
    # Store a copy to avoid modifications to the deque item affecting other parts
    current_history_deque.appendleft((timestamp_unix_float, df_for_history_storage.copy()))
    history_update_logger.info(f"History updated for symbol '{symbol}'. Current history length: {len(current_history_deque)}.")


def get_data_bundle_history_for_symbol(
    symbol: str,
    component_history_storage: Dict[str, Deque[Tuple[float, pd.DataFrame]]] # Explicitly pass history cache
) -> Deque[Tuple[float, pd.DataFrame]]:
    """Retrieves the historical data deque for a given symbol."""
    history_get_logger = logger.getChild("GetDataBundleHistory_UtilsV3")
    # Get maxlen from config to create an empty deque of the correct size if symbol not found
    app_config_for_hist_get = get_cached_config()
    history_maxlen_val_get = get_config_value(["system_settings", "df_history_maxlen_its"], 10, app_config_for_hist_get)
    if not (isinstance(history_maxlen_val_get, int) and history_maxlen_val_get > 0):
        history_maxlen_val_get = 10 # Fallback

    retrieved_deque = component_history_storage.get(symbol, deque(maxlen=history_maxlen_val_get))
    history_get_logger.debug(f"Retrieved history for '{symbol}'. Length: {len(retrieved_deque)}.")
    return retrieved_deque


def get_current_time_from_component_id(triggered_component_id: Optional[str]) -> dt_time:
    """
    Placeholder to get current time. In a real scenario, this might involve
    parsing timestamps from component IDs if they embed time information,
    or simply returning datetime.now().time().
    """
    # For now, simply return the current time.
    return datetime.now().time()


def format_status_message(message: str, is_error: bool = False, timestamp: Optional[datetime] = None) -> dash_html.Div:
    """
    Formats a status message for display in the UI, with appropriate styling for errors or success.
    """
    status_format_logger = logger.getChild("FormatStatusMessage_UtilsV3")
    
    # Fetch styles from the application config using get_config_value
    app_cfg_status = get_cached_config()
    base_style = get_config_value(["visualization_settings", "dashboard", "styles", "status_display", "base"],
                                  {"padding": "10px", "textAlign": "center", "borderRadius": "5px", "fontSize": "0.9em", "fontWeight":"500", "transition": "all 0.3s ease"},
                                  app_cfg_status)
    
    final_display_style: Dict[str, str]
    escaped_message_text = std_html.escape(str(message)) # Escape HTML sensitive characters

    if is_error:
        error_style_cfg = get_config_value(["visualization_settings", "dashboard", "styles", "status_display", "error"],
                                           {"color": "#FFFFFF", "backgroundColor": "#E74C3C", "border": "1px solid #C0392B"},
                                           app_cfg_status)
        final_display_style = {**base_style, **error_style_cfg}
        # Prepend "Error: " if not already indicated by common error keywords
        if not any(error_keyword in message.lower() for error_keyword in ["error", "failed", "critical", "exception", "invalid"]):
            escaped_message_text = f"Error: {escaped_message_text}"
    else:
        # Determine if it's a success message for distinct styling
        is_success_message = any(success_keyword in message.lower() for success_keyword in ["success", "loaded", "completed", "fetched", "processed", "ready", "✓"])
        if is_success_message:
            success_style_cfg = get_config_value(["visualization_settings", "dashboard", "styles", "status_display", "success"],
                                                 {"color": "#FFFFFF", "backgroundColor": "#2ECC71", "border": "1px solid #27AE60"},
                                                 app_cfg_status)
            final_display_style = {**base_style, **success_style_cfg}
        else: # Default to info style
            info_style_cfg = get_config_value(["visualization_settings", "dashboard", "styles", "status_display", "info"],
                                              {"color": "#FFFFFF", "backgroundColor": "#3498DB", "border": "1px solid #2980B9"},
                                              app_cfg_status)
            final_display_style = {**base_style, **info_style_cfg}
            
    # Add timestamp to the message if provided
    if timestamp:
        try:
            time_str = timestamp.strftime('%H:%M:%S')
            escaped_message_text = f"[{time_str}] {escaped_message_text}"
        except AttributeError: # If timestamp is not a datetime object
            status_format_logger.warning(f"Timestamp for status message was not a datetime object: {timestamp}")

    status_format_logger.debug(f"Formatted status message. Error: {is_error}, Style Keys Used: {list(final_display_style.keys())}, Message Snippet: '{escaped_message_text[:70]}...'")
    return dash_html.Div(escaped_message_text, style=final_display_style)

def parse_dte_input_string(dte_input_str: Optional[str]) -> Optional[List[int]]:
    """
    Parses a DTE input string (e.g., "0", "0-7", "0,1,7") into a list of integers.
    Returns None if parsing fails or input is invalid.
    """
    parse_dte_logger = logger.getChild("ParseDTEInput_UtilsV3")
    if not dte_input_str or not isinstance(dte_input_str, str):
        parse_dte_logger.debug("DTE input string is None or not a string. Returning None.")
        return None
    
    dte_input_str_cleaned = dte_input_str.strip()
    if not dte_input_str_cleaned:
        parse_dte_logger.debug("DTE input string is empty after stripping. Returning None.")
        return None
        
    try:
        if "-" in dte_input_str_cleaned: # Range
            start_dte, end_dte = map(int, dte_input_str_cleaned.split('-'))
            if start_dte < 0 or end_dte < 0 or end_dte < start_dte:
                raise ValueError("DTE range values must be non-negative and start <= end.")
            return list(range(start_dte, end_dte + 1))
        elif "," in dte_input_str_cleaned: # Comma-separated list
            dtes = [int(d.strip()) for d in dte_input_str_cleaned.split(',')]
            if any(d < 0 for d in dtes):
                raise ValueError("DTE list values must be non-negative.")
            return sorted(list(set(dtes))) # Unique, sorted
        else: # Single DTE
            dte_val = int(dte_input_str_cleaned)
            if dte_val < 0:
                raise ValueError("Single DTE value must be non-negative.")
            return [dte_val]
    except ValueError as e_dte_parse:
        parse_dte_logger.error(f"Invalid DTE input string '{dte_input_str}': {e_dte_parse}")
        return None
    except Exception as e_dte_unexpected: # Catch any other parsing errors
        parse_dte_logger.critical(f"Unexpected error parsing DTE string '{dte_input_str}': {e_dte_unexpected}", exc_info=True)
        return None

def create_hover_text_from_dict(
    data_dict: Dict[str, Any],
    title: Optional[str] = None,
    fields_to_include: Optional[List[Tuple[str, str, str]]] = None, # (key, label, type_hint)
    additional_info: Optional[Dict[str, str]] = None,
    max_value_length: int = 50 # To prevent overly long hover values
) -> str:
    """
    Generates an HTML string for Plotly hover text from a dictionary.
    Uses plot_utils._format_hover_value for formatting if available,
    otherwise uses basic string conversion.
    """
    hover_parts = []
    if title:
        hover_parts.append(f"<b>{std_html.escape(title)}</b>")

    # Attempt to import plot_utils locally for this function
    plot_utils_local = None
    try:
        from mspi_visualization import plot_utils as plot_utils_imported_for_hover
        plot_utils_local = plot_utils_imported_for_hover
    except ImportError:
        pass # plot_utils_local will remain None

    if fields_to_include: # Display specified fields in order
        for key, label, type_hint in fields_to_include:
            if key in data_dict:
                value = data_dict[key]
                formatted_value: str
                if plot_utils_local and hasattr(plot_utils_local, '_format_hover_value'):
                    try:
                        formatted_value = plot_utils_local._format_hover_value(value, type_hint)
                    except Exception: # Fallback if _format_hover_value itself errors
                        formatted_value = str(value)
                else: # Fallback if plot_utils or _format_hover_value isn't available/working
                    formatted_value = str(value)
                
                if len(formatted_value) > max_value_length and max_value_length > 3:
                    formatted_value = formatted_value[:max_value_length-3] + "..."
                hover_parts.append(f"<b>{std_html.escape(label)}:</b> {std_html.escape(formatted_value)}")
    else: # Display all items in the dictionary
        for key, value in data_dict.items():
            formatted_value: str
            if plot_utils_local and hasattr(plot_utils_local, '_format_hover_value'):
                try:
                    formatted_value = plot_utils_local._format_hover_value(value, "generic") # Assume generic if no type hint
                except Exception:
                     formatted_value = str(value)
            else:
                formatted_value = str(value)

            if len(formatted_value) > max_value_length and max_value_length > 3:
                 formatted_value = formatted_value[:max_value_length-3] + "..."
            hover_parts.append(f"<b>{std_html.escape(str(key).replace('_', ' ').title())}:</b> {std_html.escape(formatted_value)}")

    if additional_info:
        for label, info_val in additional_info.items():
            hover_parts.append(f"<i>{std_html.escape(label)}:</i> {std_html.escape(str(info_val))}")

    return "<br>".join(hover_parts) + "<extra></extra>" # <extra></extra> removes default Plotly trace info

# Final check to ensure config is loaded if module is imported and used.
if CONFIG_CACHE_FOR_UTILS_MODULE is None:
    logger.critical("UTILS.PY (V3.0.1 Module Level): CONFIG_CACHE_FOR_UTILS_MODULE is still None at the end of module. This indicates a potential issue with initial loading sequence if other modules depend on it being pre-loaded.")
    # Attempt one last load, though ideally, the main app orchestrates this.
    load_app_config_into_cache()