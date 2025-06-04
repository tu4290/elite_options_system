# core_analytics/adaptive_dag_module.py
"""
Functions for calculating the Adaptive Delta Adjusted Gamma Exposure (A-DAG)
and its helper components for the Integrated Trading System.
This version is refactored for full ids.py integration and to accept specific
input column names as parameters.

Version: EOTS_ADAG_Module_v2.3.0_Canon_IDS_Unabridged
"""
import pandas as pd
import numpy as np
import logging
import sys # For fallback ids import check
from typing import Union, Optional, List, Dict, Any, Callable, Deque
from datetime import date, datetime, time as dt_time # Ensure all are imported
from collections import deque

# --- Project-Specific Imports ---
try:
    from utils import ids
    from .system_utilities import (
        normalize_series,
        ensure_columns,
        get_atr,
        calculate_proximity_factor
    )
    IMPORTS_SUCCESSFUL = True
    logger_init = logging.getLogger(__name__) # Use this for initial log
    logger_init.info("Adaptive DAG Module (v2.3.0 Canon): Core utilities and ids imported successfully.")
except ImportError as e_adag_imp:
    IMPORTS_SUCCESSFUL = False
    print(f"CRITICAL IMPORT ERROR in adaptive_dag_module.py: {e_adag_imp}. A-DAG calculations will fail or use dummies.")
    # Define fallback constants and dummy functions if ids.py or system_utilities are missing
    class ids: # type: ignore
        COL_A_DAG_OUTPUT = "a_dag" # Primary output
        IMPACT_PROXIMITY = "proximity"
        COL_STRIKE = "strike_price"; COL_OPT_KIND = "opt_kind"; COL_DELTA_CONTRACT = "delta"
        COL_EXPIRATION_DATE = "expiration_date"
        # Add other constants used as defaults if ids.py is missing
        CFG_METRICS_CALC_ADAPTIVE_ADAG_SETTINGS = ["metrics_calculator_v2_5_settings", "adaptive_metric_params", "a_dag_settings"]
        CFG_METRICS_CALC_ATR_FALLBACK = ["metrics_calculator_v2_5_settings", "atr_calculation_params", "fallback_settings"]


    def normalize_series(series: pd.Series, series_name: str, min_denominator: float = 1e-9) -> pd.Series: return series if isinstance(series, pd.Series) else pd.Series(dtype=float) # type: ignore
    def ensure_columns(df: pd.DataFrame, req_cols: List[str], name: str, log_instance: Optional[logging.Logger]=None) -> Tuple[pd.DataFrame, bool]: # type: ignore
        missing = [col for col in req_cols if col not in df.columns]
        if missing and log_instance: log_instance.warning(f"Dummy ensure_columns: Missing {missing} in {name}")
        return df, not missing
    def get_atr(sym:str, price:float, cfg:Dict, hist:Optional[pd.DataFrame]=None, log_instance:Optional[logging.Logger]=None) -> float: return 0.01 * price if price else 0.5 # type: ignore
    def calculate_proximity_factor(strikes: pd.Series, price: float, delta: Optional[pd.Series], log_instance: Optional[logging.Logger]) -> pd.Series:
        return pd.Series(1.0, index=strikes.index) if isinstance(strikes, pd.Series) else pd.Series([1.0]) # type: ignore

# Module-level logger
logger = logging.getLogger(__name__)
if not IMPORTS_SUCCESSFUL:
    logger.critical("Adaptive DAG Module running with DUMMY imports due to failure. Functionality will be severely limited.")

MIN_NORMALIZATION_DENOMINATOR_ADAG = 1e-9

def get_volatility_regime_factor(
    current_iv: Optional[float],
    avg_iv_long_term: Optional[float],
    historical_atr_normalized: Optional[float], # This is a ratio (e.g., current ATR / avg ATR)
    a_dag_vol_regime_sensitivity: float,
    log_instance: Optional[logging.Logger] = None
) -> float:
    vol_regime_logger = log_instance.getChild("GetVolatilityRegimeFactor") if log_instance else logger.getChild("GetVolatilityRegimeFactor")
    base_factor = 1.0
    components_used = 0

    if current_iv is not None and avg_iv_long_term is not None and \
       pd.notna(current_iv) and pd.notna(avg_iv_long_term) and avg_iv_long_term > MIN_NORMALIZATION_DENOMINATOR_ADAG:
        iv_ratio = current_iv / avg_iv_long_term
        # Sensitivity scales how much the IV ratio impacts the factor.
        # (iv_ratio - 1) gives deviation from 1. Multiply by sensitivity. Add 1 to make it a factor.
        iv_component = 1.0 + (iv_ratio - 1.0) * (a_dag_vol_regime_sensitivity / 2.0) # Split sensitivity if two components
        base_factor *= iv_component
        components_used +=1
        vol_regime_logger.debug(f"IV component for vol regime factor: {iv_component:.3f} (IV: {current_iv:.3f}, AvgIV: {avg_iv_long_term:.3f})")
    else:
        vol_regime_logger.debug("Skipping IV component for vol regime factor (missing or invalid IV data).")

    if historical_atr_normalized is not None and pd.notna(historical_atr_normalized):
        # historical_atr_normalized is already a ratio (e.g., current/avg). Deviation from 1.
        atr_component = 1.0 + (historical_atr_normalized - 1.0) * (a_dag_vol_regime_sensitivity / (1 if components_used == 0 else 2.0) ) # Full or half sensitivity
        base_factor *= atr_component
        components_used +=1
        vol_regime_logger.debug(f"ATR component for vol regime factor: {atr_component:.3f} (Normalized ATR Ratio: {historical_atr_normalized:.3f})")
    else:
        vol_regime_logger.debug("Skipping ATR component for vol regime factor (missing or invalid ATR data).")

    # If only one component was used, the sensitivity might have been halved, so adjust if needed
    # This logic might need refinement based on desired interaction of IV and ATR components.
    # For now, if only one component was used, its effect is as calculated.

    clamped_factor = np.clip(base_factor, 0.5, 2.0) # Clamp to reasonable bounds
    vol_regime_logger.info(f"Calculated Volatility Regime Factor: {clamped_factor:.3f} (Pre-clamp: {base_factor:.3f}, Components Used: {components_used})")
    return clamped_factor

def calculate_dte_scaling(
    df: pd.DataFrame,
    expiration_date_col: str, # Name of the expiration date column in df
    dte_gamma_flow_impact_scaling_dict_cfg: Dict[str, float],
    log_instance: Optional[logging.Logger] = None
) -> pd.Series:
    dte_scale_logger = log_instance.getChild("CalculateDTEScaling") if log_instance else logger.getChild("CalculateDTEScaling")
    dte_scale_logger.debug(f"Calculating DTE scaling using DTE range config: {dte_gamma_flow_impact_scaling_dict_cfg}")

    if expiration_date_col not in df.columns:
        dte_scale_logger.warning(f"DTE scaling requires '{expiration_date_col}' column. Returning neutral scaling (1.0).")
        return pd.Series(1.0, index=df.index, dtype=float)
    if df.empty:
        dte_scale_logger.debug("Input DataFrame for DTE scaling is empty. Returning empty Series.")
        return pd.Series(dtype=float)

    today = date.today()
    try:
        exp_dates = pd.to_datetime(df[expiration_date_col], errors='coerce').dt.date
    except Exception as e_conv_exp:
        dte_scale_logger.error(f"Error converting '{expiration_date_col}' to date objects: {e_conv_exp}. Returning neutral (1.0).", exc_info=True)
        return pd.Series(1.0, index=df.index, dtype=float)

    dtes = (exp_dates - today).apply(lambda x: x.days if pd.notna(x) and x.days >= 0 else -1)

    default_scale_key = "1-7DTE" # A common mid-range key
    default_scale = 1.0
    if dte_gamma_flow_impact_scaling_dict_cfg: # Check if dict is not empty
        default_scale = float(dte_gamma_flow_impact_scaling_dict_cfg.get(default_scale_key, next(iter(dte_gamma_flow_impact_scaling_dict_cfg.values()), 1.0)))
    else:
        dte_scale_logger.warning("DTE scaling config dictionary is empty. Using universal default of 1.0.")


    scaling_factors = pd.Series(default_scale, index=df.index, dtype=float)

    # Iterate through configured DTE ranges. Assumes keys like "0DTE", "1-7DTE", ">30DTE", "8-14DTE"
    for dte_range_key, scale_value in dte_gamma_flow_impact_scaling_dict_cfg.items():
        try:
            scale_val_float = float(scale_value)
            if "DTE" in dte_range_key.upper() and dte_range_key.upper() == "0DTE":
                scaling_factors.loc[dtes == 0] = scale_val_float
            elif "-" in dte_range_key: # Handles ranges like "1-7DTE"
                parts = dte_range_key.upper().replace("DTE","").split('-')
                if len(parts) == 2:
                    low_dte = int(parts[0])
                    high_dte = int(parts[1])
                    scaling_factors.loc[(dtes >= low_dte) & (dtes <= high_dte)] = scale_val_float
            elif ">" in dte_range_key: # Handles ranges like ">30DTE"
                limit_dte = int(dte_range_key.upper().replace("DTE","").replace(">",""))
                scaling_factors.loc[dtes > limit_dte] = scale_val_float
            # Add other specific key patterns if necessary
        except ValueError:
            dte_scale_logger.warning(f"Could not parse DTE range key '{dte_range_key}' or scale value '{scale_value}'. Skipping this rule.")

    scaling_factors.loc[dtes < 0] = 1.0 # Neutral for past/invalid DTEs
    dte_scale_logger.debug(f"DTE scaling factors calculated. Example DTEs: {dtes.head(3).tolist() if not dtes.empty else 'N/A'}, Scales applied: {scaling_factors.head(3).tolist() if not scaling_factors.empty else 'N/A'}")
    return scaling_factors.clip(0.1, 3.0) # Clip to reasonable bounds


def apply_temporal_decay_to_flow(
    flow_series: pd.Series,
    a_dag_temporal_decay_factor: float,
    a_dag_flow_recency_half_life_periods: int, # Max number of historical periods to consider
    historical_flow_snapshots: Optional[Deque[pd.Series]] = None,
    log_instance: Optional[logging.Logger] = None
) -> pd.Series:
    decay_logger = log_instance.getChild("ApplyTemporalDecayToFlow") if log_instance else logger.getChild("ApplyTemporalDecayToFlow")

    if not isinstance(flow_series, pd.Series) or flow_series.empty:
        decay_logger.warning("Input flow_series is invalid or empty. Returning as is.")
        return flow_series.copy() if isinstance(flow_series, pd.Series) else pd.Series(dtype=float)

    if historical_flow_snapshots is None or not historical_flow_snapshots:
        decay_logger.debug("No historical flow snapshots. Returning current flow_series without decay.")
        return flow_series.copy()

    weighted_flow = flow_series.fillna(0.0).copy() # Start with current flow, weight 1.0 implicitly
    total_weight = 1.0
    current_decay_multiplier = 1.0
    num_hist_added = 0

    # Iterate through available historical snapshots up to half-life periods
    for i in range(min(a_dag_flow_recency_half_life_periods, len(historical_flow_snapshots))):
        old_flow_snapshot = historical_flow_snapshots[i] # 0 is most recent historical, etc.
        if not isinstance(old_flow_snapshot, pd.Series) or old_flow_snapshot.empty:
            continue

        current_decay_multiplier *= a_dag_temporal_decay_factor
        aligned_old_flow = old_flow_snapshot.reindex(flow_series.index).fillna(0.0)

        weighted_flow += aligned_old_flow * current_decay_multiplier
        total_weight += current_decay_multiplier
        num_hist_added +=1
        decay_logger.debug(f"Temporal decay: Historical flow snapshot {i+1} (age {i+1}) added with weight {current_decay_multiplier:.3f}")

    if total_weight > MIN_NORMALIZATION_DENOMINATOR_ADAG:
        recency_weighted_flow_final = weighted_flow / total_weight
        decay_logger.info(f"Temporal decay applied using {num_hist_added+1} snapshots (current + {num_hist_added} historical).")
    else:
        decay_logger.warning("Total weight for temporal decay is zero. Returning original flow series.")
        recency_weighted_flow_final = flow_series.copy()

    return recency_weighted_flow_final


def calculate_volume_weighted_gamma(
    df: pd.DataFrame,
    gamma_exposure_col: str,
    volm_col_for_weighting: str,
    a_dag_volume_weight_factor: float,
    log_instance: Optional[logging.Logger] = None
) -> pd.Series:
    vol_gamma_logger = log_instance.getChild("CalculateVolumeWeightedGamma") if log_instance else logger.getChild("CalculateVolumeWeightedGamma")

    if df.empty:
        vol_gamma_logger.warning("Input DataFrame is empty for volume-weighted gamma. Returning empty Series.")
        return pd.Series(dtype=float)

    if gamma_exposure_col not in df.columns or volm_col_for_weighting not in df.columns:
        vol_gamma_logger.warning(f"Missing '{gamma_exposure_col}' or '{volm_col_for_weighting}' for volume-weighted gamma. Returning raw '{gamma_exposure_col}' or zeros.")
        return pd.to_numeric(df.get(gamma_exposure_col, pd.Series(0.0, index=df.index)), errors='coerce').fillna(0.0)

    gamma_exposure = pd.to_numeric(df[gamma_exposure_col], errors='coerce').fillna(0.0)
    recent_volume = pd.to_numeric(df[volm_col_for_weighting], errors='coerce').fillna(0.0)

    norm_recent_volume = normalize_series(recent_volume.abs(), "recent_volume_for_gamma_weight", min_denominator=MIN_NORMALIZATION_DENOMINATOR_ADAG)
    volume_weighted_gamma_series = gamma_exposure * (1 + a_dag_volume_weight_factor * norm_recent_volume)

    vol_gamma_logger.debug(f"Volume-weighted gamma calculated. Using volume from '{volm_col_for_weighting}'. Weight factor: {a_dag_volume_weight_factor}")
    return volume_weighted_gamma_series.fillna(0.0)


def calculate_adaptive_dag(
    options_df: pd.DataFrame,
    gamma_exposure_col: str, delta_exposure_col: str, expiration_date_col: str,
    volm_col_for_weighting: str, direct_delta_buy_col: str, direct_delta_sell_col: str,
    proxy_delta_flow_col: str, direct_gamma_buy_col: str, direct_gamma_sell_col: str,
    proxy_gamma_flow_col: str, strike_col: str, price_col: str, option_iv_col: str, # price_col is underlying price in options_df
    underlying_symbol_col: str, a_dag_output_col_name: str, # This should be ids.COL_A_DAG_OUTPUT
    current_iv_context: Optional[float],
    avg_iv_long_term_context: Optional[float],
    historical_atr_normalized_vs_avg_context: Optional[float],
    historical_flow_snapshots_delta: Optional[Deque[pd.Series]],
    historical_flow_snapshots_gamma: Optional[Deque[pd.Series]],
    current_price_for_prox: Optional[float], # Scalar current underlying price for proximity
    historical_ohlc_for_atr: Optional[pd.DataFrame],
    a_dag_vol_regime_sensitivity_cfg: float,
    a_dag_adaptive_alpha_base_cfg: Dict[str, float],
    a_dag_temporal_decay_factor_cfg: float,
    a_dag_flow_recency_half_life_periods_cfg: int,
    a_dag_volume_weight_factor_cfg: float,
    dte_gamma_flow_impact_scaling_dict_cfg: Dict[str, float],
    atr_fallback_cfg: Dict[str, Any],
    option_delta_col: str = ids.COL_DELTA_CONTRACT, # For proximity calculation
    log_instance: Optional[logging.Logger] = None
) -> pd.DataFrame:
    a_dag_logger = log_instance.getChild("CalculateAdaptiveDAG_Main") if log_instance else logger.getChild("CalculateAdaptiveDAG_Main")
    a_dag_logger.info(f"Calculating Adaptive DAG (A-DAG) for symbol '{options_df[underlying_symbol_col].iloc[0] if not options_df.empty and underlying_symbol_col in options_df.columns else 'Unknown'}'. Output to: {a_dag_output_col_name}")
    df = options_df.copy()

    required_cols_a_dag = [
        strike_col, gamma_exposure_col, delta_exposure_col, expiration_date_col, volm_col_for_weighting,
        direct_delta_buy_col, direct_delta_sell_col, proxy_delta_flow_col,
        direct_gamma_buy_col, direct_gamma_sell_col, proxy_gamma_flow_col,
        underlying_symbol_col, price_col, option_iv_col, option_delta_col # Ensure option_delta_col is checked
    ]
    df, cols_ok = ensure_columns(df, required_cols_a_dag, "A-DAG_Input", log_instance=a_dag_logger)
    if not cols_ok:
        a_dag_logger.warning("A-DAG: One or more input columns missing/invalid. Returning input df with zero A-DAG.")
        df[a_dag_output_col_name] = 0.0
        return df

    vol_regime_factor = get_volatility_regime_factor(
        current_iv_context, avg_iv_long_term_context, historical_atr_normalized_vs_avg_context,
        a_dag_vol_regime_sensitivity_cfg, log_instance=a_dag_logger)

    adaptive_alpha_aligned = float(a_dag_adaptive_alpha_base_cfg.get("aligned", 1.3)) * vol_regime_factor
    adaptive_alpha_opposed = float(a_dag_adaptive_alpha_base_cfg.get("opposed", 0.7)) / vol_regime_factor if vol_regime_factor != 0 else float(a_dag_adaptive_alpha_base_cfg.get("opposed", 0.7))
    adaptive_alpha_neutral = float(a_dag_adaptive_alpha_base_cfg.get("neutral", 1.0)) # Neutral usually stays 1.0

    net_delta_flow_current = pd.Series(0.0, index=df.index)
    if direct_delta_buy_col in df.columns and direct_delta_sell_col in df.columns and not (df[direct_delta_buy_col].isnull().all() and df[direct_delta_sell_col].isnull().all()):
        net_delta_flow_current = pd.to_numeric(df[direct_delta_buy_col],errors='coerce').fillna(0) - pd.to_numeric(df[direct_delta_sell_col],errors='coerce').fillna(0)
    elif proxy_delta_flow_col in df.columns: net_delta_flow_current = pd.to_numeric(df[proxy_delta_flow_col], errors='coerce').fillna(0.0)

    recency_weighted_net_delta_flow = apply_temporal_decay_to_flow(net_delta_flow_current, a_dag_temporal_decay_factor_cfg, a_dag_flow_recency_half_life_periods_cfg, historical_flow_snapshots_delta, log_instance=a_dag_logger)
    dxoi_numeric = pd.to_numeric(df[delta_exposure_col], errors='coerce').fillna(0.0)
    alignment_sign_a_dag = np.tanh(3 * recency_weighted_net_delta_flow * dxoi_numeric)
    df['a_dag_alpha_applied'] = np.select([alignment_sign_a_dag > 0.3, alignment_sign_a_dag < -0.3], [adaptive_alpha_aligned, adaptive_alpha_opposed], default=adaptive_alpha_neutral)
    dxoi_abs_a_dag = dxoi_numeric.abs().replace(0, np.inf)
    raw_flow_ratio_a_dag = (recency_weighted_net_delta_flow.abs() / dxoi_abs_a_dag).fillna(0.0)
    df['a_dag_flow_ratio_applied'] = 2 / (1 + np.exp(-3 * raw_flow_ratio_a_dag)) - 1

    net_gamma_flow_current = pd.Series(0.0, index=df.index)
    if direct_gamma_buy_col in df.columns and direct_gamma_sell_col in df.columns and not (df[direct_gamma_buy_col].isnull().all() and df[direct_gamma_sell_col].isnull().all()):
        net_gamma_flow_current = pd.to_numeric(df[direct_gamma_buy_col],errors='coerce').fillna(0) - pd.to_numeric(df[direct_gamma_sell_col],errors='coerce').fillna(0)
    elif proxy_gamma_flow_col in df.columns: net_gamma_flow_current = pd.to_numeric(df[proxy_gamma_flow_col], errors='coerce').fillna(0.0)

    recency_weighted_net_gamma_flow = apply_temporal_decay_to_flow(net_gamma_flow_current, a_dag_temporal_decay_factor_cfg, a_dag_flow_recency_half_life_periods_cfg, historical_flow_snapshots_gamma, log_instance=a_dag_logger)
    df['a_dag_norm_net_gamma_flow_applied'] = normalize_series(recency_weighted_net_gamma_flow, 'recency_w_net_gamma_flow_for_a_dag', min_denominator=MIN_NORMALIZATION_DENOMINATOR_ADAG)

    volume_weighted_gamma_exposure = calculate_volume_weighted_gamma(df, gamma_exposure_col, volm_col_for_weighting, a_dag_volume_weight_factor_cfg, log_instance=a_dag_logger)
    dte_scaling_values = calculate_dte_scaling(df, expiration_date_col, dte_gamma_flow_impact_scaling_dict_cfg, log_instance=a_dag_logger)

    skew_factor_a_dag = pd.Series(1.0, index=df.index) # Default to neutral
    if option_iv_col in df.columns and strike_col in df.columns and price_col in df.columns and not df.empty:
        try:
            iv_values_a_dag = pd.to_numeric(df[option_iv_col], errors='coerce').fillna(0.0)
            # Use current_price_for_prox if available, else fallback to price_col from df
            price_for_skew = current_price_for_prox if pd.notna(current_price_for_prox) else (pd.to_numeric(df[price_col].iloc[0], errors='coerce') if not df[price_col].empty else None)
            strikes_ctx_a_dag = pd.to_numeric(df[strike_col], errors='coerce')
            if pd.notna(price_for_skew) and price_for_skew > 0 and not strikes_ctx_a_dag.isnull().all():
                moneyness_a_dag = strikes_ctx_a_dag / price_for_skew - 1 # type: ignore
                atm_mask_a_dag = abs(moneyness_a_dag) <= 0.02
                otm_mask_a_dag = ~atm_mask_a_dag
                atm_iv_a_dag = iv_values_a_dag[atm_mask_a_dag & (iv_values_a_dag > MIN_NORMALIZATION_DENOMINATOR_ADAG)].mean() if atm_mask_a_dag.any() else iv_values_a_dag[iv_values_a_dag > MIN_NORMALIZATION_DENOMINATOR_ADAG].mean()
                if pd.notna(atm_iv_a_dag) and atm_iv_a_dag > MIN_NORMALIZATION_DENOMINATOR_ADAG:
                    skew_factor_calc_a_dag = np.where(otm_mask_a_dag, 1 + 0.3 * (iv_values_a_dag / atm_iv_a_dag - 1), 1.0)
                    skew_factor_a_dag = pd.Series(skew_factor_calc_a_dag, index=df.index).fillna(1.0).clip(0.5, 1.5)
        except Exception as e_skew_a_dag: a_dag_logger.warning(f"Error calculating skew factor for A-DAG: {e_skew_a_dag}. Using neutral factor.", exc_info=False)

    price_for_final_prox = current_price_for_prox if current_price_for_prox is not None else pd.to_numeric(df[price_col].iloc[0], errors='coerce') if not df.empty else None
    proximity_factor_final_a_dag = pd.Series(1.0, index=df.index)
    if price_for_final_prox is not None and price_for_final_prox > 0:
        delta_for_final_prox = pd.to_numeric(df.get(option_delta_col), errors='coerce')
        proximity_factor_final_a_dag = calculate_proximity_factor(pd.to_numeric(df[strike_col], errors='coerce'), price_for_final_prox, delta=delta_for_final_prox, log_instance=a_dag_logger)
        proximity_factor_final_a_dag = proximity_factor_final_a_dag.fillna(0.5)
    else: a_dag_logger.warning(f"Invalid current price ({price_for_final_prox}) for final proximity in A-DAG. Using neutral proximity.")

    dxoi_sign_a_dag = np.sign(dxoi_numeric.replace(0, 1e-9)) # Use 1e-9 to avoid issues with exact zero
    df[a_dag_output_col_name] = (
        volume_weighted_gamma_exposure * dxoi_sign_a_dag *
        (1 + df['a_dag_alpha_applied'] * df['a_dag_flow_ratio_applied']) *
        df['a_dag_norm_net_gamma_flow_applied'] *
        dte_scaling_values *
        skew_factor_a_dag *
        vol_regime_factor * # This is the scalar factor
        proximity_factor_final_a_dag
    ).fillna(0.0)

    a_dag_logger.info(f"Adaptive DAG (A-DAG) calculation complete. Output column: '{a_dag_output_col_name}'. Example: {df[a_dag_output_col_name].head(1).to_string(index=False) if not df.empty and a_dag_output_col_name in df.columns else 'N/A'}")
    return df

