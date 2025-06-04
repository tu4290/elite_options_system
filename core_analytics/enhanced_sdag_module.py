# core_analytics/enhanced_sdag_module.py
"""
Functions for calculating the Enhanced Skew and Delta Adjusted Gamma Exposure (E-SDAG)
methodologies and their helper components for the Integrated Trading System.
This 'enhanced v2.3' iteration is fully unabridged and integrated with ids.py.

Version: EOTS_ESDAG_Module_v2.3.0_Canon_IDS_Unabridged
"""
import pandas as pd
import numpy as np
import logging
import sys # For fallback ids import check
import copy
from typing import Union, Optional, List, Dict, Any, Callable

# --- Project-Specific Imports ---
try:
    from utils import ids
    from .system_utilities import normalize_series, ensure_columns
    from .sdag_module import ( # Base SDAG methods are prerequisites
        calculate_sdag_multiplicative,
        calculate_sdag_directional,
        calculate_sdag_weighted,
        calculate_sdag_volatility_focused
    )
    IMPORTS_SUCCESSFUL = True
    logger_init = logging.getLogger(__name__)
    logger_init.info("Enhanced SDAG Module (v2.3.0 Canon): Core utilities and ids imported successfully.")
except ImportError as e_esdag_imp:
    IMPORTS_SUCCESSFUL = False
    print(f"CRITICAL IMPORT ERROR in enhanced_sdag_module.py: {e_esdag_imp}. E-SDAG calculations will fail or use dummies.")
    class ids: # type: ignore
        COL_E_SDAG_SKEW_ADJUSTED_GEX = "e_sdag_skew_adjusted_gex"
        COL_E_SDAG_COMPOSITE_OUTPUT = "e_sdag_composite"
        COL_SDAG_CONVICTION_SCORE = "sdag_conviction_score"
        # Add other constants used as defaults if ids.py is missing
        COL_STRIKE = "strike_price"; COL_OPT_KIND = "opt_kind"; COL_GAMMA_CONTRACT = "gamma"
        COL_VOLATILITY_OPTION_CONTRACT = "volatility"; CV_UND_PARAM_PRICE = "price"
        COL_SDAG_MULTIPLICATIVE_RAW = "sdag_multiplicative"; COL_SDAG_DIRECTIONAL_RAW = "sdag_directional"
        COL_SDAG_WEIGHTED_RAW = "sdag_weighted"; COL_SDAG_VOLATILITY_FOCUSED_RAW = "sdag_volatility_focused"

    def normalize_series(series: pd.Series, series_name: str, min_denominator: float = 1e-9) -> pd.Series: return series if isinstance(series, pd.Series) else pd.Series(dtype=float) # type: ignore
    def ensure_columns(df: pd.DataFrame, req_cols: List[str], name: str, log_instance: Optional[logging.Logger]=None) -> Tuple[pd.DataFrame, bool]: # type: ignore
        missing = [col for col in req_cols if col not in df.columns]; return df, not missing
    def _dummy_base_sdag_calc(*args: Any, **kwargs: Any) -> pd.Series: return pd.Series(dtype=float) # type: ignore
    calculate_sdag_multiplicative = calculate_sdag_directional = calculate_sdag_weighted = calculate_sdag_volatility_focused = _dummy_base_sdag_calc

# Module-level logger
logger = logging.getLogger(__name__)
if not IMPORTS_SUCCESSFUL:
    logger.critical("Enhanced SDAG Module running with DUMMY imports due to failure. Functionality will be severely limited.")

MIN_NORMALIZATION_DENOMINATOR_ESDAG = 1e-9

def calculate_enhanced_skew_adjustment(
    df_input: pd.DataFrame,
    gamma_exposure_col: str, # Raw GEX (e.g., ids.COL_GXOI_CONTRACT)
    option_iv_col: str,      # Option IV (e.g., ids.COL_VOLATILITY_OPTION_CONTRACT)
    strike_col: str,         # Strike price (e.g., ids.COL_STRIKE)
    price_col: str,          # Underlying price (e.g., ids.CV_UND_PARAM_PRICE from underlying_data, or a column in df_input if per-row)
    opt_kind_col: str,       # Option kind (e.g., ids.COL_OPT_KIND)
    e_sdag_skew_adjustment_intensity_factor: float,
    output_col_name: str = ids.COL_E_SDAG_SKEW_ADJUSTED_GEX, # From ids.py
    log_instance: Optional[logging.Logger] = None
) -> pd.DataFrame:
    skew_adj_logger = log_instance.getChild("CalculateEnhancedSkewAdjustment") if log_instance else logger.getChild("CalculateEnhancedSkewAdjustment")
    df = df_input.copy()
    skew_adj_logger.debug(f"Starting enhanced skew adjustment. Input GEX col: '{gamma_exposure_col}', Output: '{output_col_name}'")

    required_cols_skew = [strike_col, opt_kind_col, gamma_exposure_col, option_iv_col, price_col]
    df, cols_ok = ensure_columns(df, required_cols_skew, "EnhancedSkewAdjustmentInput", log_instance=skew_adj_logger)

    if not cols_ok:
        skew_adj_logger.warning(f"Missing one or more required columns for enhanced skew adjustment. Returning DataFrame with unadjusted GEX as output '{output_col_name}'.")
        df[output_col_name] = pd.to_numeric(df.get(gamma_exposure_col, 0.0), errors='coerce').fillna(0.0)
        return df

    df[strike_col] = pd.to_numeric(df[strike_col], errors='coerce')
    df[option_iv_col] = pd.to_numeric(df[option_iv_col], errors='coerce')
    base_gex = pd.to_numeric(df[gamma_exposure_col], errors='coerce').fillna(0.0)
    # Assuming price_col contains a consistent underlying price for ATM reference for this batch
    atm_strike_ref_val: Optional[float] = None
    if price_col in df.columns and not df[price_col].empty:
        # If price_col has multiple values (e.g., option prices), use the first valid underlying price
        # This assumes underlying_price_mspi (scalar) is passed into options_df as price_col for this context
        first_price = pd.to_numeric(df[price_col].iloc[0], errors='coerce')
        if pd.notna(first_price) and first_price > MIN_NORMALIZATION_DENOMINATOR_ESDAG:
            atm_strike_ref_val = first_price
    if atm_strike_ref_val is None: # Fallback if price_col was not usable
        median_strike = df[strike_col].median()
        if pd.notna(median_strike): atm_strike_ref_val = median_strike
        else: skew_adj_logger.warning("ATM strike reference for skew could not be determined. Using neutral factor."); df[output_col_name] = base_gex; return df

    df['skew_adjustment_factor_esdag'] = 1.0
    call_mask = df[opt_kind_col].astype(str).str.lower() == 'call'
    put_mask = df[opt_kind_col].astype(str).str.lower() == 'put'

    if call_mask.any():
        median_call_iv = df.loc[call_mask, option_iv_col].median()
        if pd.notna(median_call_iv) and median_call_iv > MIN_NORMALIZATION_DENOMINATOR_ESDAG:
            call_iv_ratio = df.loc[call_mask, option_iv_col] / median_call_iv
            df.loc[call_mask, 'skew_adjustment_factor_esdag'] = 1.0 + (call_iv_ratio - 1.0) * e_sdag_skew_adjustment_intensity_factor
    if put_mask.any():
        median_put_iv = df.loc[put_mask, option_iv_col].median()
        if pd.notna(median_put_iv) and median_put_iv > MIN_NORMALIZATION_DENOMINATOR_ESDAG:
            put_iv_ratio = df.loc[put_mask, option_iv_col] / median_put_iv
            df.loc[put_mask, 'skew_adjustment_factor_esdag'] = 1.0 + (put_iv_ratio - 1.0) * e_sdag_skew_adjustment_intensity_factor

    df['skew_adjustment_factor_esdag'] = df['skew_adjustment_factor_esdag'].fillna(1.0).clip(lower=0.5, upper=2.0)
    df[output_col_name] = base_gex * df['skew_adjustment_factor_esdag']
    if not df.empty and output_col_name in df.columns: skew_adj_logger.debug(f"Enhanced skew adjustment applied. Example E-GEX: {df[output_col_name].iloc[0]:.0f}")
    return df

def get_adaptive_methodology_weights(
    e_sdag_methodology_weights_initial_cfg: Dict[str, float],
    e_sdag_performance_adaptation_enabled_cfg: bool,
    enabled_sdag_methods_list: List[str], # List of base SDAG method keys (e.g., "multiplicative")
    historical_context: Optional[Dict] = None,
    log_instance: Optional[logging.Logger] = None
) -> Dict[str, float]:
    adaptive_weights_logger = log_instance.getChild("GetAdaptiveSDAGWeights") if log_instance else logger.getChild("GetAdaptiveSDAGWeights")
    current_weights = copy.deepcopy(e_sdag_methodology_weights_initial_cfg)

    if not e_sdag_performance_adaptation_enabled_cfg:
        adaptive_weights_logger.debug("Performance adaptation for SDAG weights is disabled. Using initial config weights.")
    elif historical_context is None or "sdag_method_performance" not in historical_context: # Key for performance data
        adaptive_weights_logger.warning("No historical_context or sdag_method_performance found. Using initial config weights for SDAG.")
    else:
        adaptive_weights_logger.warning("Performance-based SDAG weight adaptation logic is a v2.5 feature and NOT YET IMPLEMENTED in this v2.3 module. Using initial config weights.")
        # Placeholder for future performance adaptation logic
        # For v2.3, this will effectively use the initial_weights.

    final_adaptive_weights: Dict[str, float] = {}
    current_sum_of_weights = 0.0
    for method_name_key in enabled_sdag_methods_list: # Iterate through *enabled* methods
        weight_val = float(current_weights.get(method_name_key, 0.0)) # Get weight for this method from config
        if weight_val != 0.0: # Only consider methods with non-zero initial weight
            final_adaptive_weights[method_name_key] = weight_val
            current_sum_of_weights += weight_val

    if current_sum_of_weights > MIN_NORMALIZATION_DENOMINATOR_ESDAG and abs(current_sum_of_weights - 1.0) > 0.01:
        adaptive_weights_logger.debug(f"Normalizing E-SDAG methodology weights from sum {current_sum_of_weights:.2f} to 1.0")
        for method_key_norm in final_adaptive_weights:
            final_adaptive_weights[method_key_norm] /= current_sum_of_weights
    elif current_sum_of_weights <= MIN_NORMALIZATION_DENOMINATOR_ESDAG and final_adaptive_weights:
         adaptive_weights_logger.warning("Sum of weights for E-SDAG is zero or too small. Resulting composite will be zero.")
         # Keep weights as they are (will result in zero composite) or set all to zero
         final_adaptive_weights = {k: 0.0 for k in final_adaptive_weights}


    adaptive_weights_logger.info(f"Final E-SDAG methodology weights: {final_adaptive_weights}")
    return final_adaptive_weights

def calculate_sdag_conviction_score(
    df: pd.DataFrame,
    calculated_e_sdag_cols: List[str], # List of actual column names in df, e.g., ["e_sdag_multiplicative", "e_sdag_directional"]
    e_sdag_min_agreement_for_conviction_bonus_cfg: int,
    log_instance: Optional[logging.Logger] = None
) -> pd.Series:
    conv_score_logger = log_instance.getChild("CalculateSDAGConvictionScore") if log_instance else logger.getChild("CalculateSDAGConvictionScore")
    if df.empty:
        conv_score_logger.warning("Input DataFrame is empty for SDAG conviction score. Returning empty Series.")
        return pd.Series(dtype=float)

    valid_e_sdag_cols_in_df = [col for col in calculated_e_sdag_cols if col in df.columns]
    if not valid_e_sdag_cols_in_df:
        conv_score_logger.warning("No valid E-SDAG component columns found for conviction score. Returning zeros.")
        return pd.Series(0.0, index=df.index, dtype=float)

    # Normalize each individual E-SDAG component before combining for conviction
    normalized_sdags_df = pd.DataFrame(index=df.index)
    for sdag_col_name in valid_e_sdag_cols_in_df:
        numeric_series = pd.to_numeric(df[sdag_col_name], errors='coerce').fillna(0.0)
        # Use a unique name for normalization to avoid conflicts if original col was already "_norm"
        normalized_sdags_df[f"{sdag_col_name}_norm_for_conv"] = normalize_series(numeric_series, f"{sdag_col_name}_for_conviction", min_denominator=MIN_NORMALIZATION_DENOMINATOR_ESDAG)

    sum_norm_sdags = normalized_sdags_df.sum(axis=1)
    signs_df = np.sign(normalized_sdags_df).replace(0, np.nan) # Treat zeros as non-votes for sign
    num_positive = signs_df[signs_df > 0].count(axis=1)
    num_negative = signs_df[signs_df < 0].count(axis=1)
    num_methods_available = len(valid_e_sdag_cols_in_df) # Count of methods actually used

    agreement_score = pd.Series(0.0, index=df.index, dtype=float)
    if num_methods_available > 0:
        # Max count of same-signed signals minus count of oppositely-signed signals, normalized by total methods
        agreement_score = (num_positive.combine(num_negative, max) - num_positive.combine(num_negative, min)) / num_methods_available
    agreement_score = agreement_score.fillna(0.0)

    avg_abs_magnitude = normalized_sdags_df.abs().mean(axis=1).fillna(0.0)
    # Conviction is product of agreement and average magnitude, preserving overall sign
    conviction_score_base = agreement_score * avg_abs_magnitude * np.sign(sum_norm_sdags.replace(0,1e-9))

    bonus_condition = (num_positive >= e_sdag_min_agreement_for_conviction_bonus_cfg) | \
                      (num_negative >= e_sdag_min_agreement_for_conviction_bonus_cfg)
    all_agree_condition = (num_positive == num_methods_available) | (num_negative == num_methods_available)

    bonus_values = pd.Series(0.0, index=df.index, dtype=float)
    bonus_values = np.select([all_agree_condition, bonus_condition], [0.2, 0.1], default=0.0) # Bonus amounts
    conviction_score_final = conviction_score_base + bonus_values * np.sign(conviction_score_base.replace(0,1e-9))
    conviction_score_final = conviction_score_final.clip(-1.0, 1.0).fillna(0.0)

    conv_score_logger.debug(f"SDAG conviction score calculated. Example: {conviction_score_final.head(1).item() if not conviction_score_final.empty else 'N/A'}")
    return conviction_score_final


def calculate_enhanced_sdag(
    options_df: pd.DataFrame,
    # Column Names
    gamma_exposure_col: str, delta_exposure_col: str, option_iv_col: str,
    strike_col: str, price_col: str, opt_kind_col: str,
    volm_col_for_weighting: Optional[str], # For some base SDAGs
    vommaxoi_col_name_for_vol_focused_sdag: str, # For SDAG Volatility Focused
    option_delta_col_for_prox: str, # Option delta for proximity in base SDAGs
    # Config values for E-SDAG components
    e_sdag_use_enhanced_skew_adjustment_cfg: bool,
    e_sdag_skew_adjustment_intensity_factor_cfg: float,
    e_sdag_enhanced_gex_output_col_name_cfg: str,
    enabled_sdag_methods_cfg: List[str],
    base_sdag_method_configs_cfg: Dict[str, Dict[str, Any]],
    e_sdag_methodology_weights_initial_cfg: Dict[str, float],
    e_sdag_performance_adaptation_enabled_cfg: bool, # For v2.3, this will be False
    e_sdag_min_agreement_for_conviction_bonus_cfg: int,
    e_sdag_composite_output_col_cfg: str, # ids.COL_E_SDAG_COMPOSITE_OUTPUT
    sdag_conviction_output_col_cfg: str,  # ids.COL_SDAG_CONVICTION_SCORE
    # Contextual Data
    actual_underlying_price: Optional[float], # Scalar current underlying price
    historical_context: Optional[Dict] = None, # For performance adaptation (v2.5)
    log_instance: Optional[logging.Logger] = None
) -> pd.DataFrame:
    e_sdag_logger = log_instance.getChild("CalculateEnhancedSDAG_Main") if log_instance else logger.getChild("CalculateEnhancedSDAG_Main")
    e_sdag_logger.info("Calculating Enhanced SDAG (E-SDAG) - v2.3 Orchestration Focus...")
    df = options_df.copy()

    # 1. Enhanced Skew Adjustment (conditionally applied)
    current_gex_source_for_sdag_calcs = pd.to_numeric(df.get(gamma_exposure_col, 0.0), errors='coerce').fillna(0.0)
    if e_sdag_use_enhanced_skew_adjustment_cfg:
        e_sdag_logger.info("Applying Enhanced Skew Adjustment for E-SDAG...")
        df = calculate_enhanced_skew_adjustment(
            df_input=df, gamma_exposure_col=gamma_exposure_col, option_iv_col=option_iv_col,
            strike_col=strike_col, price_col=price_col, opt_kind_col=opt_kind_col,
            e_sdag_skew_adjustment_intensity_factor=e_sdag_skew_adjustment_intensity_factor_cfg,
            output_col_name=e_sdag_enhanced_gex_output_col_name_cfg, log_instance=e_sdag_logger)
        if e_sdag_enhanced_gex_output_col_name_cfg in df.columns:
            current_gex_source_for_sdag_calcs = pd.to_numeric(df[e_sdag_enhanced_gex_output_col_name_cfg], errors='coerce').fillna(0.0)
    else:
        e_sdag_logger.debug(f"Using raw '{gamma_exposure_col}' as GEX source for SDAG methods (Enhanced Skew Adjustment disabled).")

    # 2. Prepare Normalized Delta Exposure
    raw_delta_exposure = pd.to_numeric(df.get(delta_exposure_col, 0.0), errors='coerce').fillna(0.0)
    norm_delta_col_name_for_e_sdag = f"{delta_exposure_col}_norm_for_e_sdag" # Internal unique name
    df[norm_delta_col_name_for_e_sdag] = normalize_series(raw_delta_exposure, norm_delta_col_name_for_e_sdag, min_denominator=MIN_NORMALIZATION_DENOMINATOR_ESDAG)
    norm_delta_exposure_for_methods = df[norm_delta_col_name_for_e_sdag]

    # 3. Calculate Individual Base SDAG Methodologies
    calculated_individual_e_sdag_cols: List[str] = []
    for method_name_e in enabled_sdag_methods_cfg:
        e_sdag_method_output_col = f"e_sdag_{method_name_e}" # Internal column name
        method_specific_config = base_sdag_method_configs_cfg.get(method_name_e, {})
        calculated_e_sdag_series: Optional[pd.Series] = None
        common_args_for_base_sdag = {
            "df_for_context": df, "gamma_exposure_series": current_gex_source_for_sdag_calcs,
            "delta_exposure_norm_series": norm_delta_exposure_for_methods,
            "delta_weight_factor": float(method_specific_config.get("delta_weight_factor", 0.5)),
            "strike_col": strike_col, "actual_underlying_price": actual_underlying_price,
            "option_delta_col": option_delta_col, # Pass option_delta_col for proximity
            "log_instance": e_sdag_logger.getChild(f"BaseSDAG_{method_name_e.capitalize()}")
        }
        if method_name_e == "multiplicative":
            calculated_e_sdag_series = calculate_sdag_multiplicative(**common_args_for_base_sdag, option_iv_col=option_iv_col, volm_col_for_weighting=volm_col_for_weighting)
        elif method_name_e == "directional":
            calculated_e_sdag_series = calculate_sdag_directional(**common_args_for_base_sdag)
        elif method_name_e == "weighted":
            calculated_e_sdag_series = calculate_sdag_weighted(
                df_for_context=df, gamma_exposure_series=current_gex_source_for_sdag_calcs,
                delta_exposure_raw_series=raw_delta_exposure, # Weighted uses raw delta
                w1_gamma=float(method_specific_config.get("w1_gamma", 0.6)),
                w2_delta=float(method_specific_config.get("w2_delta", 0.4)),
                volm_col_for_weighting=volm_col_for_weighting,
                log_instance=e_sdag_logger.getChild("BaseSDAG_Weighted"))
        elif method_name_e == "volatility_focused":
            calculated_e_sdag_series = calculate_sdag_volatility_focused(**common_args_for_base_sdag, option_iv_col=option_iv_col, vomma_oi_col=vommaxoi_col_name_for_vol_focused_sdag)

        if calculated_e_sdag_series is not None:
            df[e_sdag_method_output_col] = calculated_e_sdag_series.fillna(0.0)
            calculated_individual_e_sdag_cols.append(e_sdag_method_output_col)
        else: df[e_sdag_method_output_col] = 0.0

    # 4. Determine and Apply Methodology Weights for Composite Score
    current_methodology_weights = get_adaptive_methodology_weights(e_sdag_methodology_weights_initial_cfg, e_sdag_performance_adaptation_enabled_cfg, enabled_sdag_methods_cfg, historical_context, log_instance=e_sdag_logger)
    df[e_sdag_composite_output_col_cfg] = 0.0
    sum_of_weights_used = 0.0
    for method_name_comp, weight_comp in current_methodology_weights.items():
        e_sdag_col_for_composite = f"e_sdag_{method_name_comp}"
        if e_sdag_col_for_composite in df.columns and weight_comp > 0:
            normalized_component = normalize_series(df[e_sdag_col_for_composite], f"{e_sdag_col_for_composite}_norm_for_composite", min_denominator=MIN_NORMALIZATION_DENOMINATOR_ESDAG)
            df[e_sdag_composite_output_col_cfg] += normalized_component * weight_comp
            sum_of_weights_used += weight_comp
    if sum_of_weights_used > MIN_NORMALIZATION_DENOMINATOR_ESDAG and abs(sum_of_weights_used - 1.0) > 0.01:
        df[e_sdag_composite_output_col_cfg] /= sum_of_weights_used
    elif sum_of_weights_used <= MIN_NORMALIZATION_DENOMINATOR_ESDAG: df[e_sdag_composite_output_col_cfg] = 0.0

    composite_norm_col_name_target = options_df.attrs.get("e_sdag_composite_norm_col_name_ITS", ids.COL_E_SDAG_COMPOSITE_NORM) # Use passed attribute or default
    df[composite_norm_col_name_target] = normalize_series(df.get(e_sdag_composite_output_col_cfg, 0.0), composite_norm_col_name_target, min_denominator=MIN_NORMALIZATION_DENOMINATOR_ESDAG)
    e_sdag_logger.debug(f"Calculated E-SDAG Composite ('{e_sdag_composite_output_col_cfg}'). Normalized to '{composite_norm_col_name_target}'.")

    # 5. Calculate SDAG Conviction Score
    df[sdag_conviction_output_col_cfg] = calculate_sdag_conviction_score(df, calculated_individual_e_sdag_cols, e_sdag_min_agreement_for_conviction_bonus_cfg, log_instance=e_sdag_logger)

    e_sdag_logger.info("Enhanced SDAG (E-SDAG) calculations complete.")
    return df
