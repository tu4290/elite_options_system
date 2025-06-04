# core_analytics/dynamic_tdpi_module.py
"""
Functions for calculating the Dynamic Time Decay Pressure Indicator (D-TDPI)
and its helper components for the Integrated Trading System.
This 'enhanced v2.3.1' iteration is fully unabridged and integrated with ids.py,
incorporating all corrections.

Version: EOTS_DTDPI_Module_v2.3.1_Canon_IDS_Unabridged_Final
"""
import pandas as pd
import numpy as np
import logging
import sys # For fallback ids import check
from typing import Union, Optional, List, Dict, Any, Deque, Callable, Tuple
from collections import deque
from datetime import datetime, time, date

# --- Project-Specific Imports ---
# Attempt to import 'ids' and 'system_utilities'
# Fallbacks are provided if imports fail, allowing the script to be parsed
# but functionality will be severely limited.
try:
    from utils import ids  # Assuming ids.py is in elite_options_system_package.utils
    from .system_utilities import (
        normalize_series,
        ensure_columns,
        get_atr,
        calculate_proximity_factor # Assuming this is also in system_utilities
    )
    IMPORTS_SUCCESSFUL_DTDPI = True
    logger_init_dtdpi = logging.getLogger(__name__) # Use a unique name to avoid conflict if logger is already configured
    logger_init_dtdpi.info("Dynamic TDPI Module (v2.3.1 Canon Final): Core utilities and ids imported successfully.")
except ImportError as e_dtdpi_imp_critical:
    IMPORTS_SUCCESSFUL_DTDPI = False
    # This print statement is for immediate visibility during startup if logging isn't fully set up yet.
    print(f"CRITICAL IMPORT ERROR in dynamic_tdpi_module.py: {e_dtdpi_imp_critical}. D-TDPI calculations will fail or use dummies.")

    # --- Fallback definitions for ids ---
    class ids: # type: ignore
        # D-TDPI specific output columns
        COL_D_TDPI_OUTPUT = "d_tdpi"
        COL_ENHANCED_CTR = "enhanced_ctr"
        COL_ENHANCED_TDFI = "enhanced_tdfi"
        # General columns used as inputs
        COL_STRIKE = "strike_price"
        COL_OPT_KIND = "opt_kind"
        COL_DELTA_CONTRACT = "delta"
        COL_EXPIRATION_DATE = "expiration_date"
        COL_UNDERLYING_SYMBOL_CHAIN = "underlying_symbol" # Corrected Fallback
        COL_PRICE_OPTION_CONTRACT = "price" # Option's own price column in options_df
        # Greek OI columns
        COL_CHARMXOI_CONTRACT = "charmxoi"
        COL_TXOI_CONTRACT = "txoi"
        # API Param style columns (used as defaults for input columns)
        CV_CHAIN_PARAM_THETAS_BUY_CONTRACT = "thetas_buy" 
        CV_CHAIN_PARAM_THETAS_SELL_CONTRACT = "thetas_sell" 
        CV_CHAIN_PARAM_TXVOLM = "txvolm" 
        CV_CHAIN_PARAM_CHARMXVOLM = "charmxvolm" 
        # Config paths (ensure these match your ids.py if it's more complete)
        CFG_MARKET_REGIME_TIME_DEFS = ["market_regime_engine_settings", "time_of_day_definitions"]
        CFG_METRICS_CALC_ATR_FALLBACK = ["metrics_calculator_v2_5_settings", "atr_calculation_params", "fallback_settings"]

    # --- Fallback definitions for system_utilities functions ---
    def normalize_series(series: pd.Series, series_name: str, min_denominator: float = 1e-9) -> pd.Series: # type: ignore
        print(f"DUMMY normalize_series called for {series_name}")
        return series if isinstance(series, pd.Series) else pd.Series(dtype=float)

    def ensure_columns(df: pd.DataFrame, req_cols: List[str], name: str, log_instance: Optional[logging.Logger]=None) -> Tuple[pd.DataFrame, bool]: # type: ignore
        missing = [col for col in req_cols if col not in df.columns]
        if log_instance: log_instance.warning(f"DUMMY ensure_columns ({name}): Missing {missing}")
        else: print(f"DUMMY ensure_columns ({name}): Missing {missing}")
        return df, not missing

    def get_atr(sym:str, price:float, cfg:Dict, history_df:Optional[pd.DataFrame]=None, log_instance:Optional[logging.Logger]=None) -> float: # type: ignore
        if log_instance: log_instance.debug(f"DUMMY get_atr called for {sym}")
        else: print(f"DUMMY get_atr called for {sym}")
        return 0.01 * price if price and price > 0 else 0.5

    def calculate_proximity_factor(strikes: pd.Series, price: float, delta: Optional[pd.Series], log_instance: Optional[logging.Logger]) -> pd.Series: # type: ignore
        if log_instance: log_instance.debug(f"DUMMY calculate_proximity_factor called")
        else: print(f"DUMMY calculate_proximity_factor called")
        return pd.Series(1.0, index=strikes.index) if isinstance(strikes, pd.Series) else pd.Series([1.0])

# Module-level logger
logger = logging.getLogger(__name__)
if not IMPORTS_SUCCESSFUL_DTDPI:
    logger.critical("Dynamic TDPI Module (v2.3.1 Canon Final) running with DUMMY imports due to failure. Functionality will be SEVERELY LIMITED.")

MIN_NORMALIZATION_DENOMINATOR_DTDPI = 1e-9

def calculate_adaptive_time_weight(
    current_time_obj: time,
    is_expiration_day: bool,
    time_based_definitions_cfg: Dict[str, str],
    d_tdpi_time_weight_profiles_cfg: Dict[str, List[float]],
    log_instance: Optional[logging.Logger] = None
) -> float:
    time_weight_logger = log_instance.getChild("CalculateAdaptiveTimeWeight") if log_instance else logger.getChild("CalculateAdaptiveTimeWeight")
    try:
        morning_end_str = time_based_definitions_cfg.get("morning_end", "11:00:00")
        midday_end_str = time_based_definitions_cfg.get("midday_end", "14:00:00")
        market_open_str = time_based_definitions_cfg.get("market_open", "09:30:00")
        market_close_str = time_based_definitions_cfg.get("market_close", "16:00:00")

        morning_end_t = datetime.strptime(morning_end_str, "%H:%M:%S").time()
        midday_end_t = datetime.strptime(midday_end_str, "%H:%M:%S").time()
        market_open_t = datetime.strptime(market_open_str, "%H:%M:%S").time()
        market_close_t = datetime.strptime(market_close_str, "%H:%M:%S").time()

        session_part: str
        if current_time_obj < market_open_t: session_part = "pre" # Handle pre-market case
        elif current_time_obj < morning_end_t: session_part = "open"
        elif current_time_obj < midday_end_t: session_part = "mid"
        elif current_time_obj <= market_close_t: session_part = "close"
        else: session_part = "post" # Handle post-market case

        profile_key = f"{'expiration' if is_expiration_day else 'normal'}_{session_part}"
        time_profile = d_tdpi_time_weight_profiles_cfg.get(profile_key)

        if isinstance(time_profile, list) and len(time_profile) == 2:
            start_weight, end_weight = float(time_profile[0]), float(time_profile[1])
            period_start_t: time; period_end_t: time

            if session_part == "open": period_start_t, period_end_t = market_open_t, morning_end_t
            elif session_part == "mid": period_start_t, period_end_t = morning_end_t, midday_end_t
            elif session_part == "close": period_start_t, period_end_t = midday_end_t, market_close_t
            elif session_part == "pre": return np.clip(start_weight, 0.5, 2.5) # Use start weight for pre-market
            elif session_part == "post": return np.clip(end_weight, 0.5, 2.5) # Use end weight for post-market
            else: # Should not happen
                time_weight_logger.warning(f"Unexpected session_part '{session_part}'. Using default 1.0.")
                return 1.0


            period_start_secs = period_start_t.hour * 3600 + period_start_t.minute * 60 + period_start_t.second
            period_end_secs = period_end_t.hour * 3600 + period_end_t.minute * 60 + period_end_t.second
            current_secs_abs = current_time_obj.hour * 3600 + current_time_obj.minute * 60 + current_time_obj.second
            
            # Ensure current_secs_abs is within the defined market day for interpolation
            current_secs_abs = max(period_start_secs, min(period_end_secs, current_secs_abs))
            current_secs_in_period = current_secs_abs - period_start_secs
            period_duration_secs = period_end_secs - period_start_secs

            if period_duration_secs > 0:
                progress_in_period = current_secs_in_period / period_duration_secs
                adaptive_weight = start_weight + (end_weight - start_weight) * progress_in_period
                time_weight_logger.debug(f"Adaptive time weight for profile '{profile_key}' at {current_time_obj}: {adaptive_weight:.3f}")
                return np.clip(adaptive_weight, 0.5, 2.5)
            else: # Single point in time (e.g. morning_end == midday_start)
                time_weight_logger.debug(f"Zero duration for session part '{profile_key}'. Using start_weight {start_weight}.")
                return np.clip(start_weight, 0.5, 2.5)
        else:
            time_weight_logger.warning(f"Invalid or missing time_weight_profile for '{profile_key}'. Using default 1.0 + quadratic term based on overall market progress.")
            market_open_total_seconds = market_open_t.hour*3600 + market_open_t.minute*60 + market_open_t.second
            market_close_total_seconds = market_close_t.hour*3600 + market_close_t.minute*60 + market_close_t.second
            current_total_seconds = current_time_obj.hour*3600 + current_time_obj.minute*60 + current_time_obj.second
            
            total_market_secs = market_close_total_seconds - market_open_total_seconds
            if total_market_secs > 0:
                elapsed_secs = current_total_seconds - market_open_total_seconds
                time_progress_fraction = max(0, min(1, elapsed_secs / total_market_secs))
                # Default quadratic scaling if specific profile is missing
                return np.clip(1.0 + time_progress_fraction**2, 0.5, 2.5) 
            return 1.0 # Fallback if market duration is zero or negative
    except Exception as e_time_weight:
        time_weight_logger.error(f"Error calculating adaptive time weight: {e_time_weight}. Defaulting to 1.0.", exc_info=True)
        return 1.0

def calculate_dynamic_gaussian_width(
    d_tdpi_dynamic_gaussian_width_enabled_cfg: bool,
    d_tdpi_gaussian_width_base_cfg: float,
    d_tdpi_gaussian_width_vol_sensitivity_cfg: float,
    d_tdpi_gaussian_width_range_cfg: List[float],
    historical_context: Optional[Dict] = None,
    log_instance: Optional[logging.Logger] = None
) -> float:
    gauss_logger = log_instance.getChild("CalculateDynamicGaussianWidth") if log_instance else logger.getChild("CalculateDynamicGaussianWidth")
    if not d_tdpi_dynamic_gaussian_width_enabled_cfg:
        gauss_logger.debug(f"Dynamic Gaussian width disabled. Using base: {d_tdpi_gaussian_width_base_cfg}")
        return float(d_tdpi_gaussian_width_base_cfg)

    vol_metric_change = 0.0 # Default to no change
    if historical_context:
        # Prioritize 'recent_atr_pct_change' if available and valid
        atr_pct_change = historical_context.get("recent_atr_pct_change")
        if isinstance(atr_pct_change, (int, float)) and pd.notna(atr_pct_change):
            vol_metric_change = float(atr_pct_change)
            gauss_logger.debug(f"Using 'recent_atr_pct_change': {vol_metric_change:.4f} for Gaussian width.")
        else: # Fallback to 'realized_vol_vs_avg_pct'
            realized_vol_change = historical_context.get("realized_vol_vs_avg_pct")
            if isinstance(realized_vol_change, (int, float)) and pd.notna(realized_vol_change):
                vol_metric_change = float(realized_vol_change) / 100.0 # Assuming it's a percentage
                gauss_logger.debug(f"Using 'realized_vol_vs_avg_pct': {realized_vol_change} (converted to {vol_metric_change:.4f}) for Gaussian width.")
            else:
                 gauss_logger.debug("Neither 'recent_atr_pct_change' nor 'realized_vol_vs_avg_pct' found or valid in historical_context.")

    if vol_metric_change == 0.0: # Handles case where no valid metric was found or metric indicates no change
        gauss_logger.debug("No suitable volatility metric change found or change is zero. Using base Gaussian width.")
        return float(d_tdpi_gaussian_width_base_cfg)

    width_adjustment = vol_metric_change * float(d_tdpi_gaussian_width_vol_sensitivity_cfg)
    dynamic_width = float(d_tdpi_gaussian_width_base_cfg) + width_adjustment
    
    min_w, max_w = 0.1, 5.0 # Default safety range
    if isinstance(d_tdpi_gaussian_width_range_cfg, list) and len(d_tdpi_gaussian_width_range_cfg) == 2:
        try:
            min_w = float(d_tdpi_gaussian_width_range_cfg[0])
            max_w = float(d_tdpi_gaussian_width_range_cfg[1])
        except ValueError:
            gauss_logger.warning(f"Could not parse gaussian_width_range_cfg: {d_tdpi_gaussian_width_range_cfg}. Using default range [{min_w}, {max_w}].")

    final_width = np.clip(dynamic_width, min_w, max_w)
    gauss_logger.info(f"Dynamic Gaussian width calculated: {final_width:.4f} (Base: {d_tdpi_gaussian_width_base_cfg:.4f}, Adj: {width_adjustment:.4f} from VolMetricChg: {vol_metric_change:.4f})")
    return final_width

def analyze_expiration_clustering(
    df: pd.DataFrame,
    expiration_date_col: str,
    d_tdpi_exp_clustering_dte_lookaround_cfg: int,
    d_tdpi_expiration_clustering_sensitivity_cfg: float,
    historical_context: Optional[Dict] = None, # Expected to contain 'options_oi_by_dte': Dict[int, float]
    log_instance: Optional[logging.Logger] = None
) -> pd.Series:
    cluster_logger = log_instance.getChild("AnalyzeExpirationClustering") if log_instance else logger.getChild("AnalyzeExpirationClustering")
    if df.empty:
        cluster_logger.debug("Input DataFrame is empty for expiration clustering analysis.")
        return pd.Series(dtype=float, index=df.index)
    if expiration_date_col not in df.columns:
        cluster_logger.warning(f"Missing expiration date column '{expiration_date_col}' for clustering analysis. Returning neutral factor (1.0).")
        return pd.Series(1.0, index=df.index)

    options_oi_by_dte: Optional[Dict[int, float]] = (historical_context or {}).get("options_oi_by_dte")
    if not options_oi_by_dte or not isinstance(options_oi_by_dte, dict):
        cluster_logger.debug("No valid 'options_oi_by_dte' data in historical_context. Returning neutral factor (1.0).")
        return pd.Series(1.0, index=df.index)

    # Filter out non-numeric OI values and calculate average
    valid_oi_values = [oi for oi in options_oi_by_dte.values() if isinstance(oi, (int, float)) and pd.notna(oi)]
    avg_oi_across_dtes = np.mean(valid_oi_values) if valid_oi_values else 0.0

    if not pd.notna(avg_oi_across_dtes) or avg_oi_across_dtes <= MIN_NORMALIZATION_DENOMINATOR_DTDPI:
        cluster_logger.debug(f"Average OI across DTEs is zero, NaN, or too small ({avg_oi_across_dtes}). Returning neutral factor (1.0).")
        return pd.Series(1.0, index=df.index)

    today_date = date.today() # Use a consistent 'today' for all DTE calculations
    factors = []

    for exp_str_val in df[expiration_date_col]:
        try:
            if pd.isna(exp_str_val): factors.append(1.0); continue
            exp_date_val = pd.to_datetime(exp_str_val, errors='coerce').date() if isinstance(exp_str_val, str) else (exp_str_val if isinstance(exp_str_val, (date, datetime)) else None)
            if exp_date_val is None: factors.append(1.0); continue
            if isinstance(exp_date_val, datetime): exp_date_val = exp_date_val.date() # Ensure it's a date object

            dte_val = (exp_date_val - today_date).days
            is_clustered = False
            if dte_val >= 0: # Only consider current or future expirations for clustering impact
                current_dte_oi = float(options_oi_by_dte.get(dte_val, 0.0))
                # Check if current DTE is significantly above average
                if current_dte_oi > avg_oi_across_dtes * 1.5: # Threshold 1: Strong clustering at current DTE
                    is_clustered = True
                else: # Check surrounding DTEs for moderate clustering
                    for look_dte_offset in range(-d_tdpi_exp_clustering_dte_lookaround_cfg, d_tdpi_exp_clustering_dte_lookaround_cfg + 1):
                        if look_dte_offset == 0: continue # Skip the current DTE itself
                        check_dte = dte_val + look_dte_offset
                        if check_dte >=0 and float(options_oi_by_dte.get(check_dte, 0.0)) > avg_oi_across_dtes * 1.2: # Threshold 2: Moderate clustering nearby
                            is_clustered = True; break
            factors.append(float(d_tdpi_expiration_clustering_sensitivity_cfg) if is_clustered else 1.0)
        except Exception as e_cluster_row_proc:
            cluster_logger.warning(f"Error processing row for expiration clustering (exp_val: '{exp_str_val}'): {e_cluster_row_proc}", exc_info=False) # Keep log concise
            factors.append(1.0) # Default to neutral on error for this row
            
    return pd.Series(factors, index=df.index).fillna(1.0)

def calculate_charm_acceleration(
    df: pd.DataFrame,
    charmxoi_col: str,
    d_tdpi_charm_acceleration_sensitivity_cfg: float,
    d_tdpi_charm_accel_lookback_periods_cfg: int,
    historical_context: Optional[Dict] = None, # Expected: 'past_charmxoi_snapshots_per_contract': Deque[pd.Series]
    log_instance: Optional[logging.Logger] = None
) -> pd.Series:
    charm_accel_logger = log_instance.getChild("CalculateCharmAcceleration") if log_instance else logger.getChild("CalculateCharmAcceleration")
    if df.empty:
        charm_accel_logger.debug("Input DataFrame is empty for charm acceleration.")
        return pd.Series(dtype=float, index=df.index)
    if charmxoi_col not in df.columns:
        charm_accel_logger.warning(f"Missing charm OI column '{charmxoi_col}' for acceleration calculation. Returning neutral factor (1.0).")
        return pd.Series(1.0, index=df.index)

    current_charm_series = pd.to_numeric(df[charmxoi_col], errors='coerce').fillna(0.0)
    past_charm_snapshots: Optional[Deque[pd.Series]] = (historical_context or {}).get("past_charmxoi_snapshots_per_contract")

    if not past_charm_snapshots or not isinstance(past_charm_snapshots, deque) or len(past_charm_snapshots) < d_tdpi_charm_accel_lookback_periods_cfg:
        charm_accel_logger.debug(f"Not enough historical charm snapshots for acceleration (found {len(past_charm_snapshots) if past_charm_snapshots else 0}, need {d_tdpi_charm_accel_lookback_periods_cfg}). Returning neutral factor (1.0).")
        return pd.Series(1.0, index=df.index)
    try:
        # Align past snapshots to current DataFrame's index (contracts might change)
        relevant_past_charms: List[pd.Series] = []
        for i in range(min(len(past_charm_snapshots), d_tdpi_charm_accel_lookback_periods_cfg)):
            snap = past_charm_snapshots[i] # Get from the deque
            if isinstance(snap, pd.Series):
                aligned_snap = snap.reindex(df.index).fillna(0.0) # Align and fill NaNs for missing contracts
                relevant_past_charms.append(aligned_snap)
        
        if not relevant_past_charms:
            charm_accel_logger.debug("No valid aligned past charm data after processing snapshots. Neutral factor.")
            return pd.Series(1.0, index=df.index)

        # Calculate average magnitude of past charm values for each contract
        avg_past_charm_magnitude = pd.concat([s.abs() for s in relevant_past_charms], axis=1).mean(axis=1).fillna(0.0)
        current_charm_magnitude = current_charm_series.abs()
        
        # Calculate acceleration ratio (current magnitude vs. average past magnitude)
        acceleration_ratio = current_charm_magnitude / (avg_past_charm_magnitude + MIN_NORMALIZATION_DENOMINATOR_DTDPI) # Add epsilon to avoid div by zero
        
        acceleration_factor = pd.Series(1.0, index=df.index) # Default to neutral
        # Apply sensitivity only if current magnitude is significantly greater than average past (e.g., > 10% increase)
        is_accelerating_mask = (acceleration_ratio > 1.1) 
        acceleration_factor.loc[is_accelerating_mask] = 1.0 + (acceleration_ratio[is_accelerating_mask] - 1.0) * float(d_tdpi_charm_acceleration_sensitivity_cfg)
        
        acceleration_factor = acceleration_factor.clip(0.5, 2.0) # Clamp factor to a reasonable range
        charm_accel_logger.debug(f"Charm acceleration factor calculated. Example values: {acceleration_factor.head(3).tolist() if not acceleration_factor.empty else 'N/A'}")
        return acceleration_factor.fillna(1.0)
        
    except Exception as e_charm_accel_calc:
        charm_accel_logger.error(f"Error calculating charm acceleration: {e_charm_accel_calc}", exc_info=True)
        return pd.Series(1.0, index=df.index) # Fallback to neutral on error

def calculate_enhanced_strike_proximity(
    df: pd.DataFrame,
    strike_col: str,
    underlying_symbol_col_for_atr: str, # Column name in df for underlying symbol
    dynamic_gaussian_width: float, # Pre-calculated dynamic width
    current_underlying_price: float, # Scalar current price of the underlying for proximity center
    atr_fallback_config: Dict[str, Any], # Config for ATR calculation
    historical_ohlc_df_for_atr: Optional[pd.DataFrame], # OHLCV data for ATR
    log_instance: Optional[logging.Logger] = None
) -> pd.Series:
    prox_logger = log_instance.getChild("CalculateEnhancedStrikeProximity") if log_instance else logger.getChild("CalculateEnhancedStrikeProximity")
    if df.empty:
        prox_logger.debug("Input DataFrame is empty for enhanced strike proximity.")
        return pd.Series(dtype=float, index=df.index)

    required_cols_prox = [strike_col, underlying_symbol_col_for_atr]
    # Option delta might be useful for context but not directly used in this Gaussian formulation
    # If it were, it should be added to required_cols_prox. For now, assume it's not strictly needed here.

    df_checked, cols_ok_prox = ensure_columns(df.copy(), required_cols_prox, "EnhancedStrikeProximityInput", log_instance=prox_logger)
    if not cols_ok_prox:
        prox_logger.warning(f"Missing required columns for enhanced proximity. Returning neutral factor (1.0).")
        return pd.Series(1.0, index=df_checked.index)

    atr_val = 0.0
    if pd.notna(current_underlying_price) and current_underlying_price > 0:
        # Get a representative underlying symbol (assuming it's mostly the same in the df for this batch)
        und_sym_series = df_checked[underlying_symbol_col_for_atr]
        und_sym = und_sym_series.mode()[0] if not und_sym_series.mode().empty else "UNKNOWN_SYM_PROX"
        
        atr_val = get_atr(und_sym, current_underlying_price, atr_fallback_config, 
                          history_df=historical_ohlc_df_for_atr, log_instance=prox_logger)
    else:
        prox_logger.warning(f"Current underlying price is invalid ({current_underlying_price}) for ATR calculation in proximity. ATR will be 0.")


    strike_numeric = pd.to_numeric(df_checked[strike_col], errors='coerce')
    proximity_series = pd.Series(0.0, index=df_checked.index) # Default to 0 if ATR is invalid

    if atr_val > MIN_NORMALIZATION_DENOMINATOR_DTDPI and pd.notna(current_underlying_price) and not strike_numeric.isnull().all():
        # Gaussian proximity: exp(- ( (K - S) / ATR )^2 / (2 * width^2) )
        # The 'dynamic_gaussian_width' here is more like a 'variance' or 'spread' factor.
        # A common Gaussian form is exp(-x^2 / (2*sigma^2)). If width is sigma, then it's 2*width^2 in denominator.
        # If width is already 2*sigma^2, then it's just width.
        # Given the previous simpler exp(width * diff_sq), let's assume width is a direct coefficient.
        # To make it a decaying exponential (proximity decreases as distance increases), width should be negative, or the term inverted.
        # Let's use: exp( - ( (K-S)/ATR )^2 / (dynamic_gaussian_width) ) assuming dynamic_gaussian_width is > 0 and acts like 2*sigma^2
        # If dynamic_gaussian_width is small, proximity drops off faster. If large, it's wider.
        
        strike_diff_norm_sq = ((strike_numeric.fillna(current_underlying_price) - current_underlying_price) / atr_val)**2
        if dynamic_gaussian_width > MIN_NORMALIZATION_DENOMINATOR_DTDPI: # Ensure width is positive
             proximity_series = np.exp(-strike_diff_norm_sq / dynamic_gaussian_width).fillna(0.0)
        else:
            prox_logger.warning(f"Dynamic Gaussian width ({dynamic_gaussian_width}) is too small or non-positive. Proximity will be 0.")
            proximity_series = pd.Series(0.0, index=df_checked.index)

        prox_logger.debug(f"Enhanced strike proximity calculated. Dynamic width: {dynamic_gaussian_width:.4f}, ATR: {atr_val:.3f}. Example proximity: {proximity_series.head(1).item() if not proximity_series.empty else 'N/A'}")
    else:
        prox_logger.warning(f"Could not calculate enhanced strike proximity (ATR: {atr_val:.3f}, Price: {current_underlying_price}, DynamicWidth: {dynamic_gaussian_width:.4f}). Defaulting to 0.0 proximity.")
        proximity_series = pd.Series(0.0, index=df_checked.index) # Default to 0 if ATR is bad

    return proximity_series.fillna(0.0).clip(0.0, 1.0) # Proximity factor should be between 0 and 1


def calculate_dynamic_tdpi(
    options_df: pd.DataFrame,
    tdpi_beta_coeffs_cfg: Dict[str, float], # e.g., {"aligned": 1.3, "opposed": 0.7, "neutral": 1.0}
    # Adaptive Time Weighting Config
    d_tdpi_adaptive_time_weighting_enabled_cfg: bool,
    time_based_definitions_cfg_for_time_weight: Dict[str, str], # From ids.CFG_MARKET_REGIME_TIME_DEFS
    d_tdpi_time_weight_profiles_cfg: Dict[str, List[float]], # e.g. {"normal_open": [1.0, 1.5], "expiration_close": [1.5, 2.0]}
    # Dynamic Gaussian Width Config
    d_tdpi_dynamic_gaussian_width_enabled_cfg: bool,
    d_tdpi_gaussian_width_base_cfg: float,
    d_tdpi_gaussian_width_vol_sensitivity_cfg: float,
    d_tdpi_gaussian_width_range_cfg: List[float], # [min_width, max_width]
    # Expiration Clustering Config
    d_tdpi_exp_clustering_dte_lookaround_cfg: int, # Days before/after to check for OI clusters
    d_tdpi_expiration_clustering_sensitivity_cfg: float, # Multiplier if clustered
    # Charm Acceleration Config
    d_tdpi_charm_acceleration_sensitivity_cfg: float,
    d_tdpi_charm_accel_lookback_periods_cfg: int,
    # ATR Config (for proximity and potentially Gaussian width context)
    atr_fallback_config_for_proximity_and_gauss: Dict[str, Any], # From ids.CFG_METRICS_CALC_ATR_FALLBACK
    # Contextual Data (Real-time and Historical)
    current_time_dt: Optional[time], # Current market time object
    historical_context_for_enhancements: Optional[Dict], # Contains 'recent_atr_pct_change', 'options_oi_by_dte', 'past_charmxoi_snapshots_per_contract'
    historical_ohlc_df_for_atr_prox: Optional[pd.DataFrame], # OHLCV data for ATR calculation
    underlying_price_for_prox_gauss: Optional[float], # Scalar current underlying price for proximity & Gaussian width context
    # Input Column Names (expected to be passed by orchestrator, defaulting to ids.py constants)
    charmxoi_col: str = ids.COL_CHARMXOI_CONTRACT,
    txoi_col: str = ids.COL_TXOI_CONTRACT,
    direct_theta_buy_col: str = ids.CV_CHAIN_PARAM_THETAS_BUY_CONTRACT, 
    direct_theta_sell_col: str = ids.CV_CHAIN_PARAM_THETAS_SELL_CONTRACT, 
    proxy_theta_flow_col: str = ids.CV_CHAIN_PARAM_TXVOLM, 
    proxy_charm_flow_col: str = ids.CV_CHAIN_PARAM_CHARMXVOLM, 
    expiration_date_col: str = ids.COL_EXPIRATION_DATE,
    strike_col: str = ids.COL_STRIKE,
    option_price_col: str = ids.COL_PRICE_OPTION_CONTRACT, 
    underlying_symbol_col: str = ids.COL_UNDERLYING_SYMBOL_CHAIN, # Corrected to _CHAIN
    option_delta_col: str = ids.COL_DELTA_CONTRACT, 
    # Output Column Name (from ids.py, passed by orchestrator)
    d_tdpi_output_col_name: str = ids.COL_D_TDPI_OUTPUT,
    log_instance: Optional[logging.Logger] = None
) -> pd.DataFrame:
    d_tdpi_logger = log_instance.getChild("CalculateDynamicTDPI_Main_v2.3.1") if log_instance else logger.getChild("CalculateDynamicTDPI_Main_v2.3.1")
    d_tdpi_logger.info(f"Calculating Dynamic TDPI (D-TDPI v2.3.1) for {len(options_df)} options. Output to: {d_tdpi_output_col_name}")
    df = options_df.copy()

    required_cols_d_tdpi = [
        strike_col, option_price_col, ids.COL_OPT_KIND, underlying_symbol_col, expiration_date_col,
        charmxoi_col, txoi_col, direct_theta_buy_col, direct_theta_sell_col,
        proxy_theta_flow_col, proxy_charm_flow_col, option_delta_col
    ]
    df, cols_ok = ensure_columns(df, required_cols_d_tdpi, "D-TDPI_Input_v2.3.1", log_instance=d_tdpi_logger)
    if not cols_ok:
        d_tdpi_logger.error("D-TDPI: CRITICAL - One or more essential input columns missing. Cannot proceed. Returning empty D-TDPI.")
        df[d_tdpi_output_col_name] = 0.0; df[ids.COL_ENHANCED_CTR] = 0.0; df[ids.COL_ENHANCED_TDFI] = 0.0
        return df

    # --- 1. Base TDPI Components ---
    beta_aligned = float(tdpi_beta_coeffs_cfg.get("aligned",1.3)); beta_opposed = float(tdpi_beta_coeffs_cfg.get("opposed",0.7)); beta_neutral = float(tdpi_beta_coeffs_cfg.get("neutral",1.0))
    charmxoi_numeric = pd.to_numeric(df[charmxoi_col], errors='coerce').fillna(0.0)
    # Use proxy_charm_flow_col for charm flow proxy
    charm_flow_proxy_series = pd.to_numeric(df.get(proxy_charm_flow_col, 0.0), errors='coerce').fillna(0.0)
    
    # Alignment factor based on sign of charm flow vs charm OI
    alignment_beta_sign = np.sign(charm_flow_proxy_series) * np.sign(charmxoi_numeric.replace(0,1e-9)) # Avoid div by zero if charmxoi is 0
    df['beta_applied_dtdpi'] = np.select(
        [alignment_beta_sign > 0.3, alignment_beta_sign < -0.3], # Thresholds for clear alignment/opposition
        [beta_aligned, beta_opposed], 
        default=beta_neutral
    )
    # Charm flow to OI ratio (magnitude based)
    df['charm_flow_to_oi_ratio_dtdpi'] = (charm_flow_proxy_series.abs() / (charmxoi_numeric.abs() + MIN_NORMALIZATION_DENOMINATOR_DTDPI)).fillna(0.0).clip(0,5) # Clip to prevent extreme values

    # Net Theta Flow (prioritize direct, fallback to proxy)
    norm_net_theta_flow_series = pd.Series(0.0, index=df.index); raw_theta_flow_for_sub_metrics = pd.Series(0.0, index=df.index)
    if direct_theta_buy_col in df.columns and direct_theta_sell_col in df.columns and \
       not (df[direct_theta_buy_col].isnull().all() and df[direct_theta_sell_col].isnull().all()):
        raw_theta_flow_for_sub_metrics = pd.to_numeric(df[direct_theta_buy_col],errors='coerce').fillna(0) - pd.to_numeric(df[direct_theta_sell_col],errors='coerce').fillna(0)
        norm_net_theta_flow_series = normalize_series(raw_theta_flow_for_sub_metrics, 'net_direct_theta_flow_for_d_tdpi', MIN_NORMALIZATION_DENOMINATOR_DTDPI)
        d_tdpi_logger.debug("Using DIRECT theta flow for D-TDPI.")
    elif proxy_theta_flow_col in df.columns and not df[proxy_theta_flow_col].isnull().all():
        raw_theta_flow_for_sub_metrics = pd.to_numeric(df[proxy_theta_flow_col], errors='coerce').fillna(0.0)
        norm_net_theta_flow_series = normalize_series(raw_theta_flow_for_sub_metrics, f"{proxy_theta_flow_col}_for_d_tdpi_proxy", MIN_NORMALIZATION_DENOMINATOR_DTDPI)
        d_tdpi_logger.debug(f"Using PROXY theta flow ({proxy_theta_flow_col}) for D-TDPI.")
    else:
        d_tdpi_logger.warning("Neither direct nor proxy theta flow columns found or are all NaNs for D-TDPI. Net theta flow will be zero.")
    df['norm_net_theta_flow_applied_dtdpi'] = norm_net_theta_flow_series
    
    txoi_numeric = pd.to_numeric(df[txoi_col], errors='coerce').fillna(0.0)
    txoi_sign = np.sign(txoi_numeric.replace(0, 1e-9)) # Sign of Theta OI, avoid div by zero if txoi is 0

    # --- 2. Adaptive Components ---
    effective_current_time = current_time_dt if current_time_dt is not None else datetime.now().time()
    is_exp_day_series = pd.Series(False, index=df.index) # Default to False
    if expiration_date_col in df.columns and not df[expiration_date_col].isnull().all():
        try: 
            exp_dates_dt = pd.to_datetime(df[expiration_date_col], errors='coerce').dt.date
            is_exp_day_series = (exp_dates_dt == date.today())
        except Exception as e_exp_conv_adap: 
            d_tdpi_logger.warning(f"Could not parse expiration_date for is_expiration_day check in DTDPI adaptive: {e_exp_conv_adap}")
    
    # For adaptive time weight, use a single boolean for the whole batch (is it generally expiration day for this symbol?)
    is_current_snapshot_for_expiration_day_overall = is_exp_day_series.any() if not is_exp_day_series.empty else False

    df['d_tdpi_time_weight_applied'] = 1.0 # Default
    if d_tdpi_adaptive_time_weighting_enabled_cfg:
        df['d_tdpi_time_weight_applied'] = calculate_adaptive_time_weight(
            effective_current_time, 
            is_current_snapshot_for_expiration_day_overall, 
            time_based_definitions_cfg_for_time_weight, 
            d_tdpi_time_weight_profiles_cfg, 
            log_instance=d_tdpi_logger
        )
    
    dynamic_gaussian_width_val = calculate_dynamic_gaussian_width(
        d_tdpi_dynamic_gaussian_width_enabled_cfg, d_tdpi_gaussian_width_base_cfg, 
        d_tdpi_gaussian_width_vol_sensitivity_cfg, d_tdpi_gaussian_width_range_cfg, 
        historical_context_for_enhancements, log_instance=d_tdpi_logger
    )
    
    # Ensure underlying_price_for_prox_gauss is a float for calculate_enhanced_strike_proximity
    current_und_price_scalar = underlying_price_for_prox_gauss if isinstance(underlying_price_for_prox_gauss, float) else 0.0
    if current_und_price_scalar == 0.0:
        d_tdpi_logger.warning("Underlying price for proximity/Gaussian width is 0 or not provided. Proximity might be inaccurate.")

    df['d_tdpi_strike_proximity_applied'] = calculate_enhanced_strike_proximity(
        df, strike_col, underlying_symbol_col, 
        dynamic_gaussian_width_val, 
        current_und_price_scalar, 
        atr_fallback_config_for_proximity_and_gauss, 
        historical_ohlc_df_for_atr_prox, 
        log_instance=d_tdpi_logger
    )
    
    df['d_tdpi_exp_clustering_factor_applied'] = analyze_expiration_clustering(
        df, expiration_date_col, d_tdpi_exp_clustering_dte_lookaround_cfg, 
        d_tdpi_expiration_clustering_sensitivity_cfg, historical_context_for_enhancements, 
        log_instance=d_tdpi_logger
    )
    
    df['d_tdpi_charm_acceleration_factor_applied'] = calculate_charm_acceleration(
        df, charmxoi_col, d_tdpi_charm_acceleration_sensitivity_cfg, 
        d_tdpi_charm_accel_lookback_periods_cfg, historical_context_for_enhancements, 
        log_instance=d_tdpi_logger
    )

    # --- 3. Final D-TDPI Calculation ---
    # D-TDPI = (CharmxOI * sign(TxOI)) * (1 + Beta_applied * CharmFlow/CharmOI_Ratio) * NormNetThetaFlow * TimeWeight * Proximity * Clustering * CharmAccel
    df[d_tdpi_output_col_name] = (
        charmxoi_numeric * txoi_sign * # Base decay pressure direction
        (1 + df['beta_applied_dtdpi'] * df['charm_flow_to_oi_ratio_dtdpi']) * # Modulated by charm flow alignment
        df['norm_net_theta_flow_applied_dtdpi'] * # Scaled by normalized net theta flow
        df['d_tdpi_time_weight_applied'] * # Weighted by time of day / expiration proximity
        df['d_tdpi_strike_proximity_applied'] * # Weighted by strike proximity (Gaussian)
        df['d_tdpi_exp_clustering_factor_applied'] * # Adjusted for OI clustering around expirations
        df['d_tdpi_charm_acceleration_factor_applied'] # Adjusted for recent charm acceleration
    ).fillna(0.0)
    
    d_tdpi_logger.info(f"D-TDPI final calculation complete. Output column: '{d_tdpi_output_col_name}'. Example value: {df[d_tdpi_output_col_name].head(1).item() if not df.empty and d_tdpi_output_col_name in df.columns and not df[d_tdpi_output_col_name].empty else 'N/A'}")

    # --- 4. Enhanced Sub-Metrics: CTR and TDFI ---
    # Enhanced Charm-Theta Ratio (CTR): |Charm Flow Proxy| / (|Raw Theta Flow| + epsilon)
    df[ids.COL_ENHANCED_CTR] = (charm_flow_proxy_series.abs() / (raw_theta_flow_for_sub_metrics.abs() + MIN_NORMALIZATION_DENOMINATOR_DTDPI)).fillna(0.0).clip(0, 10) # Clip to reasonable upper bound

    # Enhanced Time Decay Flow Imbalance (TDFI): Norm(|Raw Theta Flow|) / (Norm(|Theta OI|) + epsilon)
    norm_txoi_abs_enh = normalize_series(txoi_numeric.abs(), 'txoi_abs_for_enh_tdfi', MIN_NORMALIZATION_DENOMINATOR_DTDPI)
    norm_raw_theta_flow_abs_enh = normalize_series(raw_theta_flow_for_sub_metrics.abs(), 'raw_theta_flow_abs_for_enh_tdfi', MIN_NORMALIZATION_DENOMINATOR_DTDPI)
    df[ids.COL_ENHANCED_TDFI] = (norm_raw_theta_flow_abs_enh / (norm_txoi_abs_enh + MIN_NORMALIZATION_DENOMINATOR_DTDPI)).fillna(0.0).clip(0,10) # Clip
    
    d_tdpi_logger.debug(f"Enhanced CTR & TDFI calculated. CTR example: {df[ids.COL_ENHANCED_CTR].head(1).item() if not df.empty and ids.COL_ENHANCED_CTR in df.columns and not df[ids.COL_ENHANCED_CTR].empty else 'N/A'}. TDFI example: {df[ids.COL_ENHANCED_TDFI].head(1).item() if not df.empty and ids.COL_ENHANCED_TDFI in df.columns and not df[ids.COL_ENHANCED_TDFI].empty else 'N/A'}")

    # Select and return only necessary output columns to avoid passing through all intermediate calculations unless configured
    output_columns = [d_tdpi_output_col_name, ids.COL_ENHANCED_CTR, ids.COL_ENHANCED_TDFI]
    # Keep original df index and add these new columns
    final_df = options_df.copy() # Start with a fresh copy of the original DataFrame
    
    # Add or update the calculated columns in this fresh copy
    for col in output_columns:
        if col in df.columns: # df is the working copy with all intermediate columns
            final_df[col] = df[col]
        else: 
            final_df[col] = 0.0 # Should not happen if logic is correct
            d_tdpi_logger.error(f"Output column {col} was expected but not found in intermediate DTDPI dataframe. Setting to 0 in final_df.")
            
    # Return the original DataFrame (options_df) with the new output columns added/updated.
    # This ensures that any columns originally in options_df that were not used or modified by this function are preserved.
    # And the new calculations are present.
    # The orchestrator (e.g., EDP) expects the function to return a DataFrame that includes the original columns plus the new ones.
    return final_df
