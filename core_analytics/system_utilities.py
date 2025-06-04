# core_analytics/system_utilities.py
"""
General utility functions for the Integrated Trading System.
This 'enhanced v2.3' iteration is fully unabridged and integrated with ids.py.

Version: EOTS_SystemUtils_v2.3.0_Canon_IDS_Unabridged
"""
import pandas as pd
import numpy as np
import logging
import sys # For fallback ids import check
from typing import Union, Optional, List, Dict, Any, Tuple, Callable, Deque
from datetime import datetime, time, date

# --- Project-Specific Imports ---
try:
    from utils import ids # For any default column names if needed
    IMPORTS_SUCCESSFUL = True
    logger_init = logging.getLogger(__name__)
    logger_init.info("System Utilities (v2.3.0 Canon): 'ids.py' imported successfully.")
except ImportError as e_sys_util_imp:
    IMPORTS_SUCCESSFUL = False
    print(f"CRITICAL IMPORT ERROR in system_utilities.py: {e_sys_util_imp}. System utilities will use placeholder ids.")
    class ids: # type: ignore
        # Minimal set of ids for fallback if main ids.py fails
        COL_STRIKE = "strike_price" # Example

# Module-level logger
logger = logging.getLogger(__name__)
if not IMPORTS_SUCCESSFUL:
    logger.critical("System Utilities Module running with DUMMY 'ids' import. Functionality might be affected if defaults rely on it.")

# Constants
MIN_NORMALIZATION_DENOMINATOR_SYS = 1e-9
DEFAULT_ATR_FALLBACK_MIN_VALUE_SYS = 0.01
DEFAULT_ATR_FALLBACK_PERCENTAGE_SYS = 0.01


def normalize_series(
    series: pd.Series,
    series_name: str, # For logging purposes
    min_denominator: float = MIN_NORMALIZATION_DENOMINATOR_SYS
) -> pd.Series:
    """
    Normalizes a Pandas Series to the range [-1, 1] by dividing by its max absolute value.
    Handles NaN, inf, and zero/small max absolute values.
    """
    norm_logger = logger.getChild(f"NormalizeSeries.{series_name}")

    if not isinstance(series, pd.Series):
        norm_logger.error(f"Input is not a Pandas Series (type: {type(series)}). Returning empty Series.")
        return pd.Series(dtype=float, name=series_name) # Match original name if possible
    if series.empty:
        norm_logger.debug("Input Series is empty. Returning copy.")
        return series.copy()

    # Ensure numeric, coercing errors and handling potential all-NaN series after coercion
    series_numeric = pd.to_numeric(series, errors='coerce') if not pd.api.types.is_numeric_dtype(series) else series.copy()

    if series_numeric.isnull().all():
        norm_logger.warning("Series contains only NaN after numeric coercion. Returning series of zeros.")
        return pd.Series(0.0, index=series.index, name=series_name)

    # Replace inf/-inf with NaN, then fill NaNs with 0 for max_abs calculation
    series_cleaned = series_numeric.replace([np.inf, -np.inf], np.nan).fillna(0.0)
    max_abs_val = series_cleaned.abs().max()

    if pd.isna(max_abs_val) or max_abs_val < min_denominator:
        norm_logger.info(f"Max absolute value ({max_abs_val}) is too small or NaN for significant normalization. Returning series of zeros.")
        return pd.Series(0.0, index=series.index, name=series_name)

    normalized_s = (series_cleaned / max_abs_val)
    # Final fillna and clip to ensure strict [-1, 1] range and no NaNs in output
    final_normalized_s = normalized_s.fillna(0.0).clip(-1.0, 1.0)

    norm_logger.debug(f"Series normalized. MaxAbs: {max_abs_val:.4g}. Example head(2): {final_normalized_s.head(2).to_dict() if not final_normalized_s.empty else 'N/A'}")
    return final_normalized_s

def ensure_columns(
    df: pd.DataFrame,
    required_cols: List[str],
    calculation_name: str, # For logging context
    log_instance: Optional[logging.Logger] = None
) -> Tuple[pd.DataFrame, bool]:
    ensure_logger = (log_instance or logger).getChild(f"EnsureColumns.{calculation_name}")
    ensure_logger.debug(f"Ensuring columns. Required: {required_cols}")
    df_copy = df.copy()
    all_present_and_valid_from_start = True
    actions_taken_log: List[str] = []

    string_like_cols = ['opt_kind', 'symbol', 'underlying_symbol', 'expiration_date', 'fetch_timestamp',
                        'level_category', 'level_type_original', 'strategy', 'rationale', 'type',
                        'exit_reason', 'status_update', 'direction_label', 'Category', 'status']
    datetime_special_cols = ['date', 'issued_ts', 'last_adjusted_ts', 'timestamp', 'exit_timestamp']

    for col_name in required_cols:
        col_was_initially_problematic = False
        if col_name not in df_copy.columns:
            all_present_and_valid_from_start = False; col_was_initially_problematic = True
            default_val_add: Any = 0.0
            if col_name in string_like_cols: default_val_add = 'N/A_ADDED_BY_ENSURE'
            elif col_name in datetime_special_cols: default_val_add = pd.NaT
            df_copy[col_name] = default_val_add
            actions_taken_log.append(f"Added missing '{col_name}' with default '{default_val_add}'")
        else:
            original_dtype_str = str(df_copy[col_name].dtype); nan_count_before = df_copy[col_name].isnull().sum()
            if col_name in string_like_cols:
                if not pd.api.types.is_string_dtype(df_copy[col_name]) and not pd.api.types.is_object_dtype(df_copy[col_name]):
                    col_was_initially_problematic = True; df_copy[col_name] = df_copy[col_name].astype(str)
                    actions_taken_log.append(f"Coerced '{col_name}' from {original_dtype_str} to string")
                if df_copy[col_name].isnull().any():
                    col_was_initially_problematic = True; df_copy[col_name] = df_copy[col_name].fillna('N/A_FILLED_BY_ENSURE')
                    actions_taken_log.append(f"Filled NaNs in string '{col_name}'")
            elif col_name in datetime_special_cols:
                try:
                    if not pd.api.types.is_datetime64_any_dtype(df_copy[col_name]):
                        col_was_initially_problematic = True; converted_series = pd.to_datetime(df_copy[col_name], errors='coerce')
                        if converted_series.isnull().sum() > nan_count_before: actions_taken_log.append(f"Coercion of '{col_name}' to datetime created new NaTs.")
                        else: actions_taken_log.append(f"Coerced '{col_name}' to datetime")
                        df_copy[col_name] = converted_series
                except Exception as e_dt_coerce:
                    col_was_initially_problematic = True; actions_taken_log.append(f"ERROR coercing '{col_name}' to datetime: {str(e_dt_coerce)[:50]}. Col set to NaT.")
                    ensure_logger.error(f"Error coercing '{col_name}' to datetime: {e_dt_coerce}", exc_info=True); df_copy[col_name] = pd.NaT
            else: # Assume numeric
                if not pd.api.types.is_numeric_dtype(df_copy[col_name]):
                    col_was_initially_problematic = True; df_copy[col_name] = pd.to_numeric(df_copy[col_name], errors='coerce')
                    actions_taken_log.append(f"Coerced '{col_name}' from {original_dtype_str} to numeric")
                if df_copy[col_name].isnull().any():
                    col_was_initially_problematic = True; df_copy[col_name] = df_copy[col_name].fillna(0.0)
                    actions_taken_log.append(f"Filled NaNs in numeric '{col_name}' with 0.0")
        if col_was_initially_problematic: all_present_and_valid_from_start = False

    if not all_present_and_valid_from_start: ensure_logger.info(f"Column integrity actions taken: {'; '.join(actions_taken_log) if actions_taken_log else 'Type/NaN modifications occurred.'}")
    else: ensure_logger.debug("All required columns were initially present and valid.")
    return df_copy, all_present_and_valid_from_start

def map_score_to_stars(score: Optional[Union[float, int]], conviction_map_config: Dict[str, float], log_instance: Optional[logging.Logger] = None) -> int:
    map_logger = (log_instance or logger).getChild("MapScoreToStars")
    score_val: float = 0.0
    if isinstance(score, (int, float)) and pd.notna(score) and np.isfinite(score): score_val = float(score)
    else: map_logger.debug(f"Invalid/non-finite score ('{score}'). Defaulting to 0.0 for star mapping.")

    # Ensure keys from ids.py are used if conviction_map_config keys are standardized
    # For now, using direct string keys as per original structure.
    conv_map_high = float(conviction_map_config.get("conviction_map_high", 0.8))
    conv_map_hm = float(conviction_map_config.get("conviction_map_high_medium", 0.6))
    conv_map_med = float(conviction_map_config.get("conviction_map_medium", 0.4))
    conv_map_ml = float(conviction_map_config.get("conviction_map_medium_low", 0.2))
    conv_map_base1 = float(conviction_map_config.get("conviction_map_base_one_star", 0.1))

    stars: int = 0
    if score_val >= conv_map_high: stars = 5
    elif score_val >= conv_map_hm: stars = 4
    elif score_val >= conv_map_med: stars = 3
    elif score_val >= conv_map_ml: stars = 2
    elif score_val >= conv_map_base1: stars = 1
    return stars

def get_atr(
    symbol: str,
    price: Optional[float],
    atr_fallback_config: Dict[str, Any], # e.g., {"period": 14, "type": "percentage_of_price", "percentage": 0.015, "min_value": 0.50}
    history_df: Optional[pd.DataFrame] = None, # Expected columns: 'date', 'high', 'low', 'close'
    log_instance: Optional[logging.Logger] = None
) -> float:
    atr_logger = (log_instance or logger).getChild(f"GetATR.{symbol}")
    atr_logger.debug(f"ATR calculation. Price: {price}, History DF provided: {history_df is not None and not history_df.empty}")

    atr_period: int = int(atr_fallback_config.get("period", 14))
    min_val_from_config = float(atr_fallback_config.get("min_value", DEFAULT_ATR_FALLBACK_MIN_VALUE_SYS))
    calculated_atr_value: float = min_val_from_config

    if isinstance(history_df, pd.DataFrame) and not history_df.empty:
        hist_df_copy = history_df.copy()
        # Using ids.py constants for expected column names in history_df
        date_col, high_col, low_col, close_col = ids.COL_DATE, ids.COL_HIGH, ids.COL_LOW, ids.COL_CLOSE
        required_ohlc_cols_for_atr = [high_col, low_col, close_col, date_col]
        hist_df_copy, cols_ok_atr = ensure_columns(hist_df_copy, required_ohlc_cols_for_atr, "ATR_HistoryInput", log_instance=atr_logger)

        if cols_ok_atr and not hist_df_copy.empty:
            try:
                hist_df_copy.dropna(subset=required_ohlc_cols_for_atr, inplace=True)
                if len(hist_df_copy) >= atr_period:
                    hist_df_copy = hist_df_copy.sort_values(by=date_col, ascending=True).reset_index(drop=True)
                    high_low_range = pd.to_numeric(hist_df_copy[high_col],errors='coerce') - pd.to_numeric(hist_df_copy[low_col],errors='coerce')
                    prev_close_shifted = pd.to_numeric(hist_df_copy[close_col],errors='coerce').shift(1)
                    high_prev_close_range = abs(pd.to_numeric(hist_df_copy[high_col],errors='coerce') - prev_close_shifted)
                    low_prev_close_range = abs(pd.to_numeric(hist_df_copy[low_col],errors='coerce') - prev_close_shifted)
                    true_ranges_df = pd.concat([high_low_range, high_prev_close_range, low_prev_close_range], axis=1)
                    true_range_series = true_ranges_df.max(axis=1, skipna=False) # Keep NaNs if all inputs are NaN for a row
                    if not true_range_series.empty:
                        if pd.notna(high_low_range.iloc[0]): true_range_series.iloc[0] = high_low_range.iloc[0]
                        else: true_range_series.iloc[0] = np.nan
                    true_range_series.dropna(inplace=True)
                    if not true_range_series.empty and len(true_range_series) >= atr_period:
                        atr_calculated_series = true_range_series.ewm(span=atr_period, adjust=False, min_periods=atr_period).mean()
                        if not atr_calculated_series.empty and pd.notna(atr_calculated_series.iloc[-1]):
                            atr_from_hist = atr_calculated_series.iloc[-1]
                            if atr_from_hist > MIN_NORMALIZATION_DENOMINATOR_SYS:
                                calculated_atr_value = max(atr_from_hist, min_val_from_config)
                                atr_logger.info(f"ATR from history_df: {calculated_atr_value:.4f} (Raw EMA: {atr_from_hist:.4f})")
                                return round(calculated_atr_value, 4)
                            else: atr_logger.warning(f"Calculated ATR from history ({atr_from_hist:.4f}) invalid/small. Using fallback.")
                        else: atr_logger.warning("ATR EMA calculation resulted in NaN/empty. Using fallback.")
                    else: atr_logger.warning(f"Insufficient True Range values ({len(true_range_series)}) for ATR{atr_period}. Using fallback.")
                else: atr_logger.warning(f"Insufficient valid rows ({len(hist_df_copy)}) in history_df for ATR{atr_period}. Using fallback.")
            except Exception as e_atr_calc: atr_logger.error(f"Error calculating ATR from history_df: {e_atr_calc}. Using fallback.", exc_info=True)
    else: atr_logger.debug("history_df not provided or invalid for ATR. Using fallback.")

    fallback_type = str(atr_fallback_config.get("type", "percentage_of_price"))
    if fallback_type == "percentage_of_price":
        percentage_val = float(atr_fallback_config.get("percentage", DEFAULT_ATR_FALLBACK_PERCENTAGE_SYS))
        if price is not None and pd.notna(price) and price > 0:
            price_based_atr = price * percentage_val
            calculated_atr_value = max(price_based_atr, min_val_from_config)
            atr_logger.info(f"ATR using fallback (Price %: {price_based_atr:.4f} vs MinConfig: {min_val_from_config:.4f}): Result = {calculated_atr_value:.4f}")
        else: atr_logger.warning(f"Fallback 'percentage_of_price' but price invalid ({price}). Using min_config_value: {min_val_from_config:.4f}.") # calculated_atr_value already holds min_val_from_config
    else: atr_logger.warning(f"Unknown ATR fallback type '{fallback_type}'. Using min_config_value: {min_val_from_config:.4f}.") # calculated_atr_value already holds min_val_from_config
    return round(max(calculated_atr_value, MIN_NORMALIZATION_DENOMINATOR_SYS), 4)

def calculate_proximity_factor(
    strike: Union[float, pd.Series],
    current_price: float,
    delta: Optional[Union[float, pd.Series]] = None, # Option delta(s)
    log_instance: Optional[logging.Logger] = None,
    min_norm_denominator: float = MIN_NORMALIZATION_DENOMINATOR_SYS # Use local constant
) -> Union[float, pd.Series]:
    proximity_logger = (log_instance or logger).getChild("ProximityFactor")
    if not pd.notna(current_price) or current_price <= 0:
        proximity_logger.warning(f"Current price ({current_price}) is invalid. Proximity factor will be 0.")
        return 0.0 if not isinstance(strike, pd.Series) else pd.Series(0.0, index=strike.index, dtype=float)

    is_strike_series = isinstance(strike, pd.Series)
    strike_numeric = pd.to_numeric(strike, errors='coerce')
    strike_series_for_calc = strike_numeric.fillna(current_price) if is_strike_series else pd.Series([strike_numeric if pd.notna(strike_numeric) else current_price])

    price_range_for_scaling = current_price * 0.075
    denominator = max(price_range_for_scaling, min_norm_denominator)
    scaled_distance = (strike_series_for_calc - current_price).abs() / denominator
    basic_proximity = (1 - np.minimum(1.0, scaled_distance)).clip(0, 1)

    final_proximity = basic_proximity
    if delta is not None:
        delta_numeric = pd.to_numeric(delta, errors='coerce')
        delta_series_aligned: Optional[pd.Series] = None
        if isinstance(delta_numeric, pd.Series):
            delta_series_aligned = delta_numeric.reindex(strike_series_for_calc.index).fillna(0.0) if is_strike_series and not delta_numeric.index.equals(strike_series_for_calc.index) else delta_numeric.fillna(0.0)
        elif pd.notna(delta_numeric): delta_series_aligned = pd.Series(delta_numeric, index=strike_series_for_calc.index)
        if delta_series_aligned is not None and not delta_series_aligned.empty:
            delta_weight = (0.5 + delta_series_aligned.abs().clip(0, 1) * 0.5).clip(0.5, 1.0)
            final_proximity = basic_proximity * delta_weight
    final_proximity = final_proximity.fillna(0.0).clip(0.0, 1.0)
    return final_proximity if is_strike_series else (final_proximity.iloc[0] if not final_proximity.empty else 0.0)

def calculate_dynamic_threshold(
    threshold_config: Dict,
    data_series: Optional[pd.Series],
    comparison_mode: str = 'above', # 'above', 'below', 'above_abs', 'below_abs'
    log_instance: Optional[logging.Logger] = None
) -> Optional[Union[float, List[float]]]:
    dyn_thresh_logger = (log_instance or logger).getChild("DynamicThresholdCalc")
    threshold_type = str(threshold_config.get('type', 'fixed'))
    calculated_val: Optional[Union[float, List[float]]] = None
    try:
        if threshold_type == 'fixed':
            value = threshold_config.get('value'); tiers = threshold_config.get('tiers')
            if value is not None: calculated_val = float(value)
            elif isinstance(tiers, list) and all(isinstance(t, (int, float)) for t in tiers): calculated_val = [float(t) for t in tiers]
        elif threshold_type.startswith('relative_'):
            if data_series is None or data_series.empty: return threshold_config.get('fallback_value')
            cleaned_series = pd.to_numeric(data_series, errors='coerce').replace([np.inf, -np.inf], np.nan).dropna()
            if cleaned_series.empty: return threshold_config.get('fallback_value')
            if threshold_type == 'relative_percentile':
                percentile = float(threshold_config.get('percentile', 50.0)); percentile = max(0.0, min(100.0, percentile))
                calculated_val = np.percentile(cleaned_series, percentile)
            elif threshold_type == 'relative_mean_factor':
                factor = float(threshold_config.get('factor', 1.0))
                series_for_mean = cleaned_series.abs() if comparison_mode.endswith('_abs') else cleaned_series
                if series_for_mean.empty: return threshold_config.get('fallback_value')
                calculated_val = factor * series_for_mean.mean()
            else: dyn_thresh_logger.error(f"Unknown 'relative_' type: '{threshold_type}'."); return threshold_config.get('fallback_value')
        else: dyn_thresh_logger.error(f"Unsupported threshold type: '{threshold_type}'."); return threshold_config.get('fallback_value')
        if calculated_val is None: return threshold_config.get('fallback_value')
        if isinstance(calculated_val, list):
             if not all(isinstance(t, (int,float)) and pd.notna(t) and np.isfinite(t) for t in calculated_val): return threshold_config.get('fallback_value')
        elif not (isinstance(calculated_val, (int,float)) and pd.notna(calculated_val) and np.isfinite(calculated_val)): return threshold_config.get('fallback_value')
        return calculated_val
    except Exception as e_dyn_calc: dyn_thresh_logger.error(f"Error during dynamic threshold calc (Type: '{threshold_type}'): {e_dyn_calc}", exc_info=True); return threshold_config.get('fallback_value')

def calculate_dynamic_threshold_wrapper(
    config_object_or_getter: Union[Dict[str, Any], Callable[[List[str], Any], Any]],
    config_path_to_threshold_definition: List[str],
    data_series: Optional[pd.Series],
    comparison_mode: str = 'above',
    log_instance: Optional[logging.Logger] = None
) -> Optional[Union[float, List[float]]]:
    dt_wrap_logger = (log_instance or logger).getChild("DynamicThresholdWrapper")
    threshold_config: Optional[Dict] = None
    if isinstance(config_object_or_getter, dict):
        current_level = config_object_or_getter
        try:
            for key_segment in config_path_to_threshold_definition: current_level = current_level[key_segment] # type: ignore
            if isinstance(current_level, dict): threshold_config = current_level
        except (KeyError, TypeError): threshold_config = {}
    elif callable(config_object_or_getter): threshold_config = config_object_or_getter(config_path_to_threshold_definition, {})
    if not isinstance(threshold_config, dict) or not threshold_config:
        dt_wrap_logger.error(f"Invalid/empty threshold config at '{'/'.join(config_path_to_threshold_definition)}'."); return None
    calculated_thresh = calculate_dynamic_threshold(threshold_config, data_series, comparison_mode, log_instance=dt_wrap_logger)
    if calculated_thresh is None:
        fallback_val = threshold_config.get('fallback_value')
        dt_wrap_logger.warning(f"Dynamic calculation failed for '{'/'.join(config_path_to_threshold_definition)}'. Using its fallback: '{fallback_val}'")
        if fallback_val is not None:
            try: return [float(tier) for tier in fallback_val] if isinstance(fallback_val, list) else float(fallback_val)
            except (ValueError, TypeError): dt_wrap_logger.error(f"Fallback value '{fallback_val}' invalid. Returning None."); return None
        return None
    return calculated_thresh

def aggregate_for_levels(
    df: pd.DataFrame,
    group_col: str = ids.COL_STRIKE, # Default to ids.COL_STRIKE
    enabled_sdag_methods: Optional[List[str]] = None, # e.g., ["multiplicative", "directional"]
    log_instance: Optional[logging.Logger] = None,
    min_norm_denominator_agg: float = MIN_NORMALIZATION_DENOMINATOR_SYS
) -> pd.DataFrame:
    agg_logger = (log_instance or logger).getChild(f"AggregateForLevels.{group_col}")
    if not isinstance(df, pd.DataFrame) or df.empty: agg_logger.warning("Input DF for aggregation empty/invalid."); return pd.DataFrame()
    if group_col not in df.columns: agg_logger.error(f"Grouping column '{group_col}' not in DF. Cols: {df.columns.tolist()}."); return pd.DataFrame()

    df_agg_copy = df.copy()
    if group_col == ids.COL_STRIKE: df_agg_copy[group_col] = pd.to_numeric(df_agg_copy[group_col], errors='coerce')
    df_agg_copy.dropna(subset=[group_col], inplace=True)
    if df_agg_copy.empty: agg_logger.warning(f"DF empty after ensuring valid grouping column '{group_col}'."); return pd.DataFrame()

    base_agg_logic: Dict[str, Union[str, Callable]] = {
        ids.COL_MSPI_SCORE:'sum', ids.COL_DAG_CUSTOM_RAW:'sum', ids.COL_TDPI_RAW:'sum', ids.COL_VRI_RAW:'sum',
        ids.COL_A_DAG_OUTPUT: 'sum', ids.COL_D_TDPI_OUTPUT: 'sum', ids.COL_VRI_2_0_OUTPUT: 'sum', ids.COL_E_SDAG_COMPOSITE_OUTPUT: 'sum',
        ids.COL_SSI:'first', ids.COL_ARFI:'first', # These are often single values or representative
        ids.COL_CTR:'first', ids.COL_TDFI:'first', ids.COL_VFI:'first', ids.COL_VVR:'first',
        ids.COL_ENHANCED_CTR:'first', ids.COL_ENHANCED_TDFI:'first', # From D-TDPI
        ids.COL_PRICE_OPTION_CONTRACT:'first', # Underlying price if it was on option rows
        ids.COL_UNDERLYING_PRICE_AT_FETCH_EDP: 'first',
        ids.COL_CHART_NET_VOLUME_PRESSURE: 'sum', ids.COL_CHART_NET_VALUE_PRESSURE: 'sum',
        ids.COL_CHART_HEURISTIC_NET_DELTA_PRESSURE: 'sum', ids.COL_CHART_NET_GAMMA_FLOW: 'sum',
        ids.COL_CHART_NET_VEGA_FLOW: 'sum', ids.COL_CHART_NET_THETA_EXPOSURE: 'sum',
        ids.COL_SDAG_CONVICTION_SCORE: 'first',
        ids.COL_GXOI_CONTRACT: "sum", ids.COL_DXOI_CONTRACT: "sum", ids.COL_VXOI_CONTRACT: "sum",
        ids.COL_TXOI_CONTRACT: "sum", ids.COL_CHARMXOI_CONTRACT: "sum",
        ids.COL_VANNAXOI_CONTRACT: "sum", ids.COL_VOMMAXOI_CONTRACT: "sum",
    }
    active_sdag_methods = enabled_sdag_methods if isinstance(enabled_sdag_methods, list) else []
    for sdag_method_name in active_sdag_methods: # Add raw and norm SDAGs based on ids.py
        raw_col = getattr(ids, f"COL_SDAG_{sdag_method_name.upper()}_RAW", None)
        norm_col = getattr(ids, f"COL_SDAG_{sdag_method_name.upper()}_NORM", None)
        if raw_col: base_agg_logic[raw_col] = 'sum'
        if norm_col: base_agg_logic[norm_col] = 'first' # Normalized are usually taken as is

    final_agg_logic = {col: agg_func for col, agg_func in base_agg_logic.items() if col in df_agg_copy.columns}
    def agg_custom_sai(series_sai: pd.Series) -> Any: # Custom SAI agg
        if not isinstance(series_sai, pd.Series) or series_sai.empty: return np.nan
        numeric_sai = pd.to_numeric(series_sai, errors='coerce');
        if numeric_sai.isnull().all(): return 0.0
        return numeric_sai.loc[numeric_sai.abs().idxmax()] if pd.notna(numeric_sai.abs().idxmax()) else 0.0
    if ids.COL_SAI in df_agg_copy.columns: final_agg_logic[ids.COL_SAI] = agg_custom_sai

    if not final_agg_logic: agg_logger.warning("No valid columns for aggregation."); return df_agg_copy.groupby(group_col, as_index=False).first().reset_index(drop=True) if not df_agg_copy.empty else pd.DataFrame()
    try:
        for col_agg, agg_f in final_agg_logic.items():
            if col_agg != group_col and not callable(agg_f) and agg_f != 'first':
                if col_agg in df_agg_copy.columns and not pd.api.types.is_numeric_dtype(df_agg_copy[col_agg]):
                    df_agg_copy[col_agg] = pd.to_numeric(df_agg_copy[col_agg], errors='coerce')
        aggregated_df = df_agg_copy.groupby(group_col, as_index=False).agg(final_agg_logic)
        fill_vals = {col: 0.0 for col in aggregated_df.columns if col != group_col and col != ids.COL_SSI}
        if ids.COL_SSI in aggregated_df.columns: fill_vals[ids.COL_SSI] = 0.5
        aggregated_df = aggregated_df.fillna(value=fill_vals)
        for col_flt in [ids.COL_PRICE_OPTION_CONTRACT, ids.COL_MSPI_SCORE, ids.COL_DAG_CUSTOM_RAW, ids.COL_TDPI_RAW, ids.COL_VRI_RAW, ids.COL_A_DAG_OUTPUT, ids.COL_D_TDPI_OUTPUT, ids.COL_VRI_2_0_OUTPUT, ids.COL_E_SDAG_COMPOSITE_OUTPUT]:
            if col_flt in aggregated_df.columns: aggregated_df[col_flt] = pd.to_numeric(aggregated_df[col_flt], errors='coerce').fillna(0.0)
        agg_logger.info(f"Aggregation by '{group_col}' complete. Output shape: {aggregated_df.shape}")
        return aggregated_df.reset_index(drop=True)
    except Exception as e_agg: agg_logger.critical(f"Critical error during aggregation for '{group_col}': {e_agg}", exc_info=True); return pd.DataFrame()

def get_performance_metrics_stub(log_instance: Optional[logging.Logger] = None, **kwargs_metrics: Any) -> Dict[str, float]:
    perf_stub_logger = (log_instance or logger).getChild("PerformanceMetricsStub")
    perf_stub_logger.warning("Using STUB for get_performance_metrics. Adaptive weights may be based on neutral performance (0.5).")
    stub_performance: Dict[str, float] = {
        ids.COL_DAG_CUSTOM_RAW: 0.5, ids.COL_TDPI_RAW: 0.5, ids.COL_VRI_RAW: 0.5, # Using RAW constants from ids.py
        ids.COL_SDAG_MULTIPLICATIVE_NORM: 0.5, ids.COL_SDAG_DIRECTIONAL_NORM:0.5,
        ids.COL_SDAG_WEIGHTED_NORM: 0.5, ids.COL_SDAG_VOLATILITY_FOCUSED_NORM: 0.5
    }
    for metric_key_arg, metric_val_arg_name in kwargs_metrics.items(): # metric_val_arg_name is the column name string
        if isinstance(metric_val_arg_name, str):
            stub_performance[metric_val_arg_name] = 0.5 # Store performance against the actual column name
    return stub_performance

