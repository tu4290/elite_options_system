# core_analytics/sdag_module.py
"""
Functions for calculating various Skew and Delta Adjusted Gamma Exposure (SDAG)
methodologies for the EOTS v2.3 system.
This version is refactored for full ids.py integration and to accept specific
input column names as parameters.

Version: EOTS_SDAG_Module_v2.3.0_Canon_IDS_Unabridged
"""
import pandas as pd
import numpy as np
import logging
import sys # For fallback ids import check
from typing import Union, Optional, List, Dict, Any

# --- Project-Specific Imports ---
try:
    from utils import ids
    from .system_utilities import normalize_series, ensure_columns, calculate_proximity_factor
    IMPORTS_SUCCESSFUL = True
    logger_init = logging.getLogger(__name__)
    logger_init.info("SDAG Module (v2.3.0 Canon): Core utilities and ids imported successfully.")
except ImportError as e_sdag_imp:
    IMPORTS_SUCCESSFUL = False
    print(f"CRITICAL IMPORT ERROR in sdag_module.py: {e_sdag_imp}. SDAG calculations will fail or use dummies.")
    class ids: # type: ignore
        COL_SDAG_MULTIPLICATIVE_RAW = "sdag_multiplicative"
        COL_SDAG_DIRECTIONAL_RAW = "sdag_directional"
        COL_SDAG_WEIGHTED_RAW = "sdag_weighted"
        COL_SDAG_VOLATILITY_FOCUSED_RAW = "sdag_volatility_focused"
        # Add other constants used as defaults if ids.py is missing
        COL_STRIKE = "strike_price"; COL_OPT_KIND = "opt_kind"; COL_DELTA_CONTRACT = "delta"
        COL_VOLATILITY_OPTION_CONTRACT = "volatility"; COL_VOLUME_OPTION_CONTRACT = "volm"
        COL_VOMMAXOI_CONTRACT = "vommaxoi"; IMPACT_PROXIMITY = "proximity"

    def normalize_series(series: pd.Series, series_name: str, min_denominator: float = 1e-9) -> pd.Series: return series if isinstance(series, pd.Series) else pd.Series(dtype=float) # type: ignore
    def ensure_columns(df: pd.DataFrame, req_cols: List[str], name: str, log_instance: Optional[logging.Logger]=None) -> Tuple[pd.DataFrame, bool]: # type: ignore
        missing = [col for col in req_cols if col not in df.columns]
        if missing and log_instance: log_instance.warning(f"Dummy ensure_columns: Missing {missing} in {name}")
        return df, not missing
    def calculate_proximity_factor(strikes: pd.Series, price: float, delta: Optional[pd.Series], log_instance: Optional[logging.Logger]) -> pd.Series:
        return pd.Series(1.0, index=strikes.index) if isinstance(strikes, pd.Series) else pd.Series([1.0]) # type: ignore

# Module-level logger
logger = logging.getLogger(__name__)
if not IMPORTS_SUCCESSFUL:
    logger.critical("SDAG Module running with DUMMY imports due to failure. Functionality will be severely limited.")

MIN_NORMALIZATION_DENOMINATOR_SDAG = 1e-9

def calculate_sdag_multiplicative(
    df_for_context: pd.DataFrame,
    gamma_exposure_series: pd.Series, # Changed from gamma_exposure
    delta_exposure_norm_series: pd.Series, # Changed from delta_exposure_norm
    delta_weight_factor: float,
    option_iv_col: str,
    strike_col: str,
    actual_underlying_price: Optional[float],
    volm_col_for_weighting: Optional[str] = None,
    log_instance: Optional[logging.Logger] = None
) -> pd.Series:
    calc_logger = log_instance.getChild("CalculateSDAGMultiplicative_v2.3") if log_instance else logger.getChild("CalculateSDAGMultiplicative_v2.3")
    calc_logger.debug("Calculating SDAG Multiplicative (v2.3)...")

    if not isinstance(gamma_exposure_series, pd.Series) or gamma_exposure_series.empty:
        calc_logger.warning("Input gamma_exposure_series is empty or not a Series. Returning empty Series.")
        return pd.Series(dtype=float)

    gamma_exp_numeric = pd.to_numeric(gamma_exposure_series, errors='coerce').fillna(0.0)
    delta_exp_norm_numeric = pd.to_numeric(delta_exposure_norm_series, errors='coerce').fillna(0.0)

    # Ensure alignment if df_for_context is used for skew/volume factors
    if not df_for_context.empty:
        df_for_context = df_for_context.reindex(gamma_exp_numeric.index)

    skew_factor = pd.Series(1.0, index=gamma_exp_numeric.index)
    if not df_for_context.empty and option_iv_col in df_for_context.columns and \
       strike_col in df_for_context.columns and \
       pd.notna(actual_underlying_price) and actual_underlying_price > MIN_NORMALIZATION_DENOMINATOR_SDAG:
        try:
            iv_values = pd.to_numeric(df_for_context[option_iv_col], errors='coerce').fillna(0.0)
            strikes_val = pd.to_numeric(df_for_context[strike_col], errors='coerce')
            if not strikes_val.isnull().all():
                moneyness = strikes_val / actual_underlying_price - 1 # type: ignore
                atm_mask = abs(moneyness) <= 0.02 # Define ATM range (e.g., +/- 2%)
                otm_mask = ~atm_mask
                
                atm_iv_values_in_mask = iv_values[atm_mask & (iv_values > MIN_NORMALIZATION_DENOMINATOR_SDAG)]
                atm_iv = atm_iv_values_in_mask.mean() if not atm_iv_values_in_mask.empty else iv_values[iv_values > MIN_NORMALIZATION_DENOMINATOR_SDAG].mean()

                if pd.notna(atm_iv) and atm_iv > MIN_NORMALIZATION_DENOMINATOR_SDAG:
                    skew_factor_calc = np.where(otm_mask, 1 + 0.5 * (iv_values / atm_iv - 1), 1.0)
                    skew_factor = pd.Series(skew_factor_calc, index=df_for_context.index).reindex(gamma_exp_numeric.index).fillna(1.0).clip(0.5, 1.5)
                else:
                    calc_logger.debug("Could not determine valid ATM IV for skew factor. Using neutral factor.")
        except Exception as e_skew: calc_logger.warning(f"Error calculating SDAG Multiplicative skew factor: {e_skew}.", exc_info=False)
    else:
        calc_logger.debug(f"Missing elements for SDAG Multiplicative skew factor. ContextDF empty: {df_for_context.empty}, IV col: {option_iv_col in df_for_context}, Strike col: {strike_col in df_for_context}, UnderlyingP: {pd.notna(actual_underlying_price)}")

    volume_factor = pd.Series(1.0, index=gamma_exp_numeric.index)
    if not df_for_context.empty and volm_col_for_weighting and volm_col_for_weighting in df_for_context.columns:
        try:
            volume_values = pd.to_numeric(df_for_context[volm_col_for_weighting], errors='coerce').fillna(0.0)
            norm_volume = normalize_series(volume_values.abs(), 'volume_for_sdag_multiplicative', min_denominator=MIN_NORMALIZATION_DENOMINATOR_SDAG)
            volume_factor_calc = 1 + 0.3 * norm_volume # Example weighting
            volume_factor = pd.Series(volume_factor_calc, index=df_for_context.index).reindex(gamma_exp_numeric.index).fillna(1.0).clip(0.7, 1.3)
        except Exception as e_vol: calc_logger.warning(f"Error calculating SDAG Multiplicative volume factor: {e_vol}.", exc_info=False)

    calculated_sdag = (gamma_exp_numeric * (1 + delta_exp_norm_numeric * delta_weight_factor) * skew_factor * volume_factor).fillna(0.0)
    calc_logger.debug(f"SDAG Multiplicative calculated. Example: {calculated_sdag.head(1).to_string(index=False) if not calculated_sdag.empty else 'N/A'}")
    return calculated_sdag


def calculate_sdag_directional(
    df_for_context: pd.DataFrame,
    gamma_exposure_series: pd.Series,
    delta_exposure_norm_series: pd.Series,
    delta_weight_factor: float,
    strike_col: str,
    actual_underlying_price: Optional[float],
    option_delta_col: str = ids.COL_DELTA_CONTRACT, # For proximity calculation
    log_instance: Optional[logging.Logger] = None
) -> pd.Series:
    calc_logger = log_instance.getChild("CalculateSDAGDirectional_v2.3") if log_instance else logger.getChild("CalculateSDAGDirectional_v2.3")
    calc_logger.debug("Calculating SDAG Directional (v2.3)...")

    if not isinstance(gamma_exposure_series, pd.Series) or gamma_exposure_series.empty:
        calc_logger.warning("Input gamma_exposure_series is empty or not a Series. Returning empty Series.")
        return pd.Series(dtype=float)

    gamma_exp_numeric = pd.to_numeric(gamma_exposure_series, errors='coerce').fillna(0.0)
    delta_exp_norm_numeric = pd.to_numeric(delta_exposure_norm_series, errors='coerce').fillna(0.0)

    interaction_term = gamma_exp_numeric * delta_exp_norm_numeric
    smoothed_sign = np.tanh(3 * interaction_term) # Smoothed sign of interaction
    alignment_strength = abs(smoothed_sign)
    
    # Dynamic weight adjustment based on alignment strength
    dynamic_weight = delta_weight_factor * (0.8 + 0.4 * alignment_strength)
    if isinstance(dynamic_weight, pd.Series):
        dynamic_weight = dynamic_weight.fillna(delta_weight_factor).clip(0.5 * delta_weight_factor, 1.5 * delta_weight_factor)
    else: # Should be scalar if inputs are scalar, but handle if it became Series due to alignment_strength
        dynamic_weight = np.clip(dynamic_weight if pd.notna(dynamic_weight) else delta_weight_factor,
                                 0.5 * delta_weight_factor, 1.5 * delta_weight_factor)

    magnitude_enhancement_factor = 1 + abs(delta_exp_norm_numeric * dynamic_weight)

    proximity_factor = pd.Series(1.0, index=gamma_exp_numeric.index)
    if not df_for_context.empty and strike_col in df_for_context.columns and \
       option_delta_col in df_for_context.columns and \
       pd.notna(actual_underlying_price) and actual_underlying_price > 0:
        try:
            strikes_val = pd.to_numeric(df_for_context[strike_col], errors='coerce')
            delta_for_prox = pd.to_numeric(df_for_context[option_delta_col], errors='coerce')
            if not strikes_val.isnull().all():
                prox_factor_calc = calculate_proximity_factor(strikes_val, actual_underlying_price, delta=delta_for_prox, log_instance=calc_logger)
                proximity_factor = pd.Series(prox_factor_calc, index=df_for_context.index).reindex(gamma_exp_numeric.index).fillna(0.5)
        except Exception as e_prox: calc_logger.warning(f"Error SDAG Directional proximity: {e_prox}.", exc_info=False)
    else:
        calc_logger.debug(f"Missing elements for SDAG Directional proximity. ContextDF empty: {df_for_context.empty}, Strike col: {strike_col in df_for_context}, Delta col: {option_delta_col in df_for_context}, UnderlyingP: {pd.notna(actual_underlying_price)}")

    calculated_sdag = (gamma_exp_numeric * smoothed_sign * magnitude_enhancement_factor * proximity_factor).fillna(0.0)
    calc_logger.debug(f"SDAG Directional calculated. Example: {calculated_sdag.head(1).to_string(index=False) if not calculated_sdag.empty else 'N/A'}")
    return calculated_sdag


def calculate_sdag_weighted(
    df_for_context: pd.DataFrame, # For volume column
    gamma_exposure_series: pd.Series,
    delta_exposure_raw_series: pd.Series, # Uses raw delta exposure for this method
    w1_gamma: float,
    w2_delta: float,
    volm_col_for_weighting: Optional[str] = None,
    log_instance: Optional[logging.Logger] = None
) -> pd.Series:
    calc_logger = log_instance.getChild("CalculateSDAGWeighted_v2.3") if log_instance else logger.getChild("CalculateSDAGWeighted_v2.3")
    calc_logger.debug("Calculating SDAG Weighted (v2.3)...")

    if not isinstance(gamma_exposure_series, pd.Series) or gamma_exposure_series.empty:
        calc_logger.warning("Input gamma_exposure_series is empty or not a Series. Returning empty Series.")
        return pd.Series(dtype=float)

    gamma_exp_numeric = pd.to_numeric(gamma_exposure_series, errors='coerce').fillna(0.0)
    delta_exp_raw_numeric = pd.to_numeric(delta_exposure_raw_series, errors='coerce').fillna(0.0)

    sum_of_base_weights = w1_gamma + w2_delta
    if abs(sum_of_base_weights) < MIN_NORMALIZATION_DENOMINATOR_SDAG:
        calc_logger.warning("Sum of base weights for SDAG Weighted is near zero. Returning zeros.")
        return pd.Series(0.0, index=gamma_exp_numeric.index)

    # Dynamic adjustment of weights based on relative magnitudes (simplified)
    dynamic_w1_g, dynamic_w2_d = w1_gamma, w2_delta
    gamma_magnitude_mean = gamma_exp_numeric.abs().mean()
    delta_magnitude_mean = delta_exp_raw_numeric.abs().mean()

    if pd.notna(gamma_magnitude_mean) and gamma_magnitude_mean > MIN_NORMALIZATION_DENOMINATOR_SDAG and \
       pd.notna(delta_magnitude_mean) and delta_magnitude_mean > MIN_NORMALIZATION_DENOMINATOR_SDAG:
        magnitude_ratio = gamma_magnitude_mean / delta_magnitude_mean
        adjustment_factor = 0.0
        if magnitude_ratio > 3: # Gamma is much larger
            adjustment_factor = np.log10(magnitude_ratio) * 0.1 # Reduce gamma weight, increase delta
            dynamic_w1_g = max(0.4 * sum_of_base_weights, min(0.8 * sum_of_base_weights, w1_gamma - adjustment_factor * sum_of_base_weights))
            dynamic_w2_d = max(0.2 * sum_of_base_weights, min(0.6 * sum_of_base_weights, w2_delta + adjustment_factor * sum_of_base_weights))
        elif magnitude_ratio < 0.33: # Delta is much larger
            adjustment_factor = np.log10(1/magnitude_ratio) * 0.1 # Increase gamma weight, reduce delta
            dynamic_w1_g = max(0.4 * sum_of_base_weights, min(0.8 * sum_of_base_weights, w1_gamma + adjustment_factor * sum_of_base_weights))
            dynamic_w2_d = max(0.2 * sum_of_base_weights, min(0.6 * sum_of_base_weights, w2_delta - adjustment_factor * sum_of_base_weights))

    # Volume influence (optional)
    if not df_for_context.empty and volm_col_for_weighting and volm_col_for_weighting in df_for_context.columns:
        try:
            volume_values = pd.to_numeric(df_for_context[volm_col_for_weighting], errors='coerce').fillna(0.0)
            # Reindex norm_volume to match gamma_exp_numeric's index if df_for_context was different
            norm_volume_mean = normalize_series(volume_values.abs(), 'volume_for_sdag_weighted', min_denominator=MIN_NORMALIZATION_DENOMINATOR_SDAG).reindex(gamma_exp_numeric.index).mean()
            if pd.notna(norm_volume_mean):
                volume_adjustment_scalar = 0.1 * norm_volume_mean * sum_of_base_weights # Small influence
                dynamic_w1_g = np.clip(dynamic_w1_g + volume_adjustment_scalar, 0.4 * sum_of_base_weights, 0.8 * sum_of_base_weights) # type: ignore
                dynamic_w2_d = np.clip(dynamic_w2_d - volume_adjustment_scalar, 0.2 * sum_of_base_weights, 0.6 * sum_of_base_weights) # type: ignore
        except Exception as e_vol_adj: calc_logger.warning(f"Error SDAG Weighted Vol Adj: {e_vol_adj}", exc_info=False)

    # Ensure weights still sum to original total or re-normalize
    current_sum_dynamic = dynamic_w1_g + dynamic_w2_d
    final_w1_g, final_w2_d = (w1_gamma, w2_delta)
    if abs(current_sum_dynamic) > MIN_NORMALIZATION_DENOMINATOR_SDAG:
        final_w1_g = dynamic_w1_g * (sum_of_base_weights / current_sum_dynamic)
        final_w2_d = dynamic_w2_d * (sum_of_base_weights / current_sum_dynamic)
    else: # If sum is zero, revert to original weights to avoid division by zero
        calc_logger.warning("Dynamic weights summed to zero in SDAG Weighted. Reverting to initial weights.")

    calculated_sdag = ((final_w1_g * gamma_exp_numeric + final_w2_d * delta_exp_raw_numeric) / sum_of_base_weights).fillna(0.0)
    calc_logger.debug(f"SDAG Weighted calculated. Final weights G:{final_w1_g:.2f}, D:{final_w2_d:.2f}. Example: {calculated_sdag.head(1).to_string(index=False) if not calculated_sdag.empty else 'N/A'}")
    return calculated_sdag


def calculate_sdag_volatility_focused(
    df_for_context: pd.DataFrame,
    gamma_exposure_series: pd.Series,
    delta_exposure_norm_series: pd.Series,
    delta_weight_factor: float,
    option_iv_col: str,
    strike_col: str,
    actual_underlying_price: Optional[float],
    vomma_oi_col: Optional[str] = None, # Vomma Open Interest column name
    log_instance: Optional[logging.Logger] = None
) -> pd.Series:
    calc_logger = log_instance.getChild("CalculateSDAGVolFocused_v2.3") if log_instance else logger.getChild("CalculateSDAGVolFocused_v2.3")
    calc_logger.debug(f"Calculating SDAG Volatility Focused (v2.3)...")

    if not isinstance(gamma_exposure_series, pd.Series) or gamma_exposure_series.empty:
        calc_logger.warning("Input gamma_exposure_series is empty or not a Series. Returning empty Series.")
        return pd.Series(dtype=float)

    gamma_exp_numeric = pd.to_numeric(gamma_exposure_series, errors='coerce').fillna(0.0)
    delta_exp_norm_numeric = pd.to_numeric(delta_exposure_norm_series, errors='coerce').fillna(0.0)
    gamma_sign_smooth = np.tanh(3 * gamma_exp_numeric) # Smoothed sign of gamma exposure

    # Reindex df_for_context to match gamma_exp_numeric if necessary
    if not df_for_context.empty and not df_for_context.index.equals(gamma_exp_numeric.index):
        df_for_context = df_for_context.reindex(gamma_exp_numeric.index)


    vol_context_factor = pd.Series(1.0, index=gamma_exp_numeric.index)
    if not df_for_context.empty and option_iv_col in df_for_context.columns and \
       strike_col in df_for_context.columns and \
       pd.notna(actual_underlying_price) and actual_underlying_price > MIN_NORMALIZATION_DENOMINATOR_SDAG:
        try:
            iv_values = pd.to_numeric(df_for_context[option_iv_col], errors='coerce').fillna(0.0)
            if iv_values[iv_values > MIN_NORMALIZATION_DENOMINATOR_SDAG].any():
                avg_iv_of_context_chain = iv_values[iv_values > MIN_NORMALIZATION_DENOMINATOR_SDAG].mean()
                if pd.notna(avg_iv_of_context_chain) and avg_iv_of_context_chain > MIN_NORMALIZATION_DENOMINATOR_SDAG:
                    relative_iv = iv_values / avg_iv_of_context_chain
                    vol_context_factor_calc = 1 + 0.3 * (relative_iv - 1) # Example: Amplify effect if IV is high
                    vol_context_factor = pd.Series(vol_context_factor_calc, index=df_for_context.index).reindex(gamma_exp_numeric.index).fillna(1.0).clip(0.7, 1.5)
        except Exception as e_vol_ctx: calc_logger.warning(f"Error SDAG VolFoc VolCtx: {e_vol_ctx}.", exc_info=False)
    else:
        calc_logger.debug(f"Missing elements for SDAG VolFoc VolCtx. ContextDF empty: {df_for_context.empty}, IV col: {option_iv_col in df_for_context.columns}, Strike col: {strike_col in df_for_context.columns}, UnderlyingP: {pd.notna(actual_underlying_price)}")

    vomma_factor = pd.Series(1.0, index=gamma_exp_numeric.index)
    if not df_for_context.empty and vomma_oi_col and vomma_oi_col in df_for_context.columns:
        try:
            vomma_values = pd.to_numeric(df_for_context[vomma_oi_col], errors='coerce').fillna(0.0)
            norm_vomma = normalize_series(vomma_values.abs(), 'vomma_for_sdag_volatility', min_denominator=MIN_NORMALIZATION_DENOMINATOR_SDAG)
            vomma_factor_calc = 1 + 0.4 * norm_vomma # Amplify effect of Vomma
            vomma_factor = pd.Series(vomma_factor_calc, index=df_for_context.index).reindex(gamma_exp_numeric.index).fillna(1.0).clip(0.6, 1.4)
        except Exception as e_vomma: calc_logger.warning(f"Error SDAG VolFoc Vomma: {e_vomma}.", exc_info=False)
    else:
        calc_logger.debug(f"VommaOI col '{vomma_oi_col}' missing or not specified for SDAG VolFoc. Neutral vomma_factor.")

    calculated_sdag = (
        gamma_exp_numeric *
        (1 + delta_exp_norm_numeric * gamma_sign_smooth * delta_weight_factor) *
        vol_context_factor *
        vomma_factor
    ).fillna(0.0)
    calc_logger.debug(f"SDAG Volatility Focused calculated. Example: {calculated_sdag.head(1).to_string(index=False) if not calculated_sdag.empty else 'N/A'}")
    return calculated_sdag

