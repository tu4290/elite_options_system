# core_analytics/vri_2_0_module.py
"""
Functions for calculating the Volatility Risk Indicator Version 2.0 (VRI 2.0)
and its helper components for the Integrated Trading System.
This 'enhanced v2.3' iteration is fully unabridged and integrated with ids.py.
For a v2.3 run, these metrics are typically disabled by flags in the orchestrator.

Version: EOTS_VRI2_Module_v2.3.0_Canon_IDS_Unabridged
"""
import pandas as pd
import numpy as np
import logging
import sys # For fallback ids import check
from typing import Union, Optional, List, Dict, Any, Deque, Tuple
import datetime

# --- Project-Specific Imports ---
try:
    from utils import ids
    from .system_utilities import normalize_series, ensure_columns
    IMPORTS_SUCCESSFUL = True
    logger_init = logging.getLogger(__name__)
    logger_init.info("VRI 2.0 Module (v2.3.0 Canon): Core utilities and ids imported successfully.")
except ImportError as e_vri2_imp:
    IMPORTS_SUCCESSFUL = False
    print(f"CRITICAL IMPORT ERROR in vri_2_0_module.py: {e_vri2_imp}. VRI 2.0 calculations will fail or use dummies.")
    class ids: # type: ignore
        COL_VRI_2_0_OUTPUT = "vri_2_0"; COL_ENHANCED_VVR_SENS = "enhanced_vvr_sens"; COL_ENHANCED_VFI_SENS = "enhanced_vfi_sens"
        COL_STRIKE = "strike_price"; COL_OPT_KIND = "opt_kind"; COL_VOLATILITY_OPTION_CONTRACT = "volatility"
        COL_EXPIRATION_DATE = "expiration_date"; COL_VANNAXOI_CONTRACT = "vannaxoi"; COL_VXOI_CONTRACT = "vxoi"
        COL_VOMMAXOI_CONTRACT = "vommaxoi"; CV_CHAIN_PARAM_VEGAS_BUY_CONTRACT = "vegas_buy"
        CV_CHAIN_PARAM_VEGAS_SELL_CONTRACT = "vegas_sell"; CV_CHAIN_PARAM_VXVOLM_CONTRACT = "vxvolm"
        CV_CHAIN_PARAM_VANNAXVOLM_CONTRACT = "vannaxvolm"; CV_CHAIN_PARAM_VOMMAXVOLM_CONTRACT = "vommaxvolm"

    def normalize_series(series: pd.Series, series_name: str, min_denominator: float = 1e-9) -> pd.Series: return series if isinstance(series, pd.Series) else pd.Series(dtype=float) # type: ignore
    def ensure_columns(df: pd.DataFrame, req_cols: List[str], name: str, log_instance: Optional[logging.Logger]=None) -> Tuple[pd.DataFrame, bool]: # type: ignore
        missing = [col for col in req_cols if col not in df.columns]; return df, not missing

# Module-level logger
logger = logging.getLogger(__name__)
if not IMPORTS_SUCCESSFUL:
    logger.critical("VRI 2.0 Module running with DUMMY imports due to failure. Functionality will be severely limited.")

MIN_DENOMINATOR_VRI2 = 1e-9

def calculate_volatility_term_structure_slope(
    options_df: pd.DataFrame,
    option_iv_col: str,      # e.g., ids.COL_VOLATILITY_OPTION_CONTRACT
    expiration_date_col: str, # e.g., ids.COL_EXPIRATION_DATE
    strike_col: str,         # e.g., ids.COL_STRIKE
    current_price: Optional[float], # Scalar underlying price for ATM determination
    short_dte_for_slope_cfg: int,
    mid_dte_for_slope_cfg: int,
    log_instance: Optional[logging.Logger] = None
) -> float:
    term_logger = log_instance.getChild("CalcVolTermStructureSlope") if log_instance else logger.getChild("CalcVolTermStructureSlope")
    slope = 0.0 # Default to flat

    if options_df.empty or not all(c in options_df.columns for c in [option_iv_col, expiration_date_col, strike_col]):
        term_logger.warning("Missing required columns or empty DataFrame for term structure slope. Returning 0.0.")
        return slope
    if not (pd.notna(current_price) and current_price > 0):
        term_logger.warning(f"Invalid current price ({current_price}) for ATM determination in term structure. Returning 0.0.")
        return slope

    df = options_df.copy()
    df[option_iv_col] = pd.to_numeric(df[option_iv_col], errors='coerce')
    df[strike_col] = pd.to_numeric(df[strike_col], errors='coerce')
    df[expiration_date_col] = pd.to_datetime(df[expiration_date_col], errors='coerce')
    df.dropna(subset=[option_iv_col, expiration_date_col, strike_col], inplace=True)
    if df.empty: return slope
    today = datetime.datetime.now().date()
    today = datetime.now().date()
    df['dte_calc'] = (df[expiration_date_col].dt.date - today).apply(lambda x: x.days)
    df = df[df['dte_calc'] >= 0] # Filter out past expirations

    # Filter for near-ATM options (e.g., within 5% of current price)
    atm_lower_bound = current_price * 0.95
    atm_upper_bound = current_price * 1.05
    df_atm = df[(df[strike_col] >= atm_lower_bound) & (df[strike_col] <= atm_upper_bound)]
    if df_atm.empty: df_atm = df # Fallback to all if no ATM options

    # Short-term IV (e.g., DTE <= 7)
    df_short_term = df_atm[(df_atm['dte_calc'] >= 0) & (df_atm['dte_calc'] <= short_dte_for_slope_cfg)]
    avg_iv_short = df_short_term[option_iv_col].mean() if not df_short_term.empty else np.nan

    # Mid-term IV (e.g., DTE between 20 and 40, centered around 30)
    mid_dte_lower = max(short_dte_for_slope_cfg + 1, mid_dte_for_slope_cfg - (mid_dte_for_slope_cfg - short_dte_for_slope_cfg)//2) # Ensure distinct range
    mid_dte_upper = mid_dte_for_slope_cfg + (mid_dte_for_slope_cfg - short_dte_for_slope_cfg)//2
    df_mid_term = df_atm[(df_atm['dte_calc'] >= mid_dte_lower) & (df_atm['dte_calc'] <= mid_dte_upper)]
    avg_iv_mid = df_mid_term[option_iv_col].mean() if not df_mid_term.empty else np.nan

    if pd.notna(avg_iv_short) and pd.notna(avg_iv_mid):
        # Slope: (IV_mid - IV_short) / (DTE_mid_avg - DTE_short_avg)
        # Approximate DTEs for slope calculation
        dte_mid_approx = (mid_dte_lower + mid_dte_upper) / 2.0
        dte_short_approx = short_dte_for_slope_cfg / 2.0 # Crude center of short DTEs
        dte_diff = dte_mid_approx - dte_short_approx
        if dte_diff > MIN_DENOMINATOR_VRI2:
            slope = (avg_iv_mid - avg_iv_short) / dte_diff
            term_logger.debug(f"Term structure slope: {slope:.4f} (IV_mid: {avg_iv_mid:.3f} @ DTE~{dte_mid_approx:.0f}, IV_short: {avg_iv_short:.3f} @ DTE~{dte_short_approx:.0f})")
        else:
            term_logger.debug("DTE difference for slope calculation too small. Slope remains 0.")
    else:
        term_logger.debug(f"Could not calculate valid avg IV for short ({avg_iv_short}) or mid ({avg_iv_mid}) term. Slope remains 0.")
    return slope if pd.notna(slope) else 0.0


def analyze_volatility_surface_dynamics(
    historical_iv_surface_snapshots: Optional[Deque[Dict[str, float]]], # List of {"timestamp": iso, "avg_atm_iv": float, "skew_metric": float}
    surface_change_lookback_cfg: int,
    surface_change_sensitivity_cfg: float,
    log_instance: Optional[logging.Logger] = None
) -> float:
    surf_logger = log_instance.getChild("AnalyzeVolSurfaceDynamics") if log_instance else logger.getChild("AnalyzeVolSurfaceDynamics")
    surface_change_factor = 1.0 # Neutral

    if not historical_iv_surface_snapshots or len(historical_iv_surface_snapshots) < 2:
        surf_logger.debug("Not enough historical IV surface snapshots for dynamic analysis. Returning neutral factor.")
        return surface_change_factor

    # Simplified: Compare current avg ATM IV to average of last N snapshots
    # A more complex version would look at changes in skew, kurtosis, etc.
    try:
        snapshots_to_consider = list(historical_iv_surface_snapshots)[:surface_change_lookback_cfg]
        current_snapshot_iv = snapshots_to_consider[0].get("avg_atm_iv") # Newest
        
        if len(snapshots_to_consider) > 1:
            past_ivs = [s.get("avg_atm_iv") for s in snapshots_to_consider[1:] if isinstance(s,dict) and pd.notna(s.get("avg_atm_iv"))]
            if past_ivs and pd.notna(current_snapshot_iv):
                avg_past_iv = np.mean(past_ivs)
                if avg_past_iv > MIN_DENOMINATOR_VRI2:
                    iv_change_ratio = current_snapshot_iv / avg_past_iv
                    # If current IV is higher, factor > 1 (amplifies VRI); if lower, factor < 1 (dampens)
                    surface_change_factor = 1.0 + (iv_change_ratio - 1.0) * surface_change_sensitivity_cfg
                    surface_change_factor = np.clip(surface_change_factor, 0.5, 1.5) # Clamp
                    surf_logger.debug(f"Vol surface dynamics factor: {surface_change_factor:.3f} (CurrentIV: {current_snapshot_iv:.3f}, AvgPastIV: {avg_past_iv:.3f})")
                else: surf_logger.debug("Average past IV is too small for surface dynamics. Neutral factor.")
            else: surf_logger.debug("Not enough valid past IVs or current IV for surface dynamics. Neutral factor.")
        else: surf_logger.debug("Only one snapshot for surface dynamics. Neutral factor.")
    except Exception as e_surf:
        surf_logger.error(f"Error analyzing volatility surface dynamics: {e_surf}", exc_info=True)
    return surface_change_factor


def enhance_vomma_impact(
    df: pd.DataFrame,
    vommaxoi_col: str, # e.g., ids.COL_VOMMAXOI_CONTRACT
    oi_col: str,       # e.g., ids.COL_OI_OPTION_CONTRACT
    vomma_oi_min_for_enhancement_cfg: float,
    vomma_enhancement_factor_cfg: float,
    log_instance: Optional[logging.Logger] = None
) -> pd.Series:
    vomma_logger = log_instance.getChild("EnhanceVommaImpact") if log_instance else logger.getChild("EnhanceVommaImpact")
    if vommaxoi_col not in df.columns or oi_col not in df.columns:
        vomma_logger.warning(f"Missing '{vommaxoi_col}' or '{oi_col}' for Vomma enhancement. Returning original VommaxOI.")
        return pd.to_numeric(df.get(vommaxoi_col, 0.0), errors='coerce').fillna(0.0)

    vommaxoi_numeric = pd.to_numeric(df[vommaxoi_col], errors='coerce').fillna(0.0)
    oi_numeric = pd.to_numeric(df[oi_col], errors='coerce').fillna(0.0)

    # Enhance Vomma impact where OI is high
    enhancement_multiplier = pd.Series(1.0, index=df.index)
    high_oi_mask = oi_numeric >= vomma_oi_min_for_enhancement_cfg
    enhancement_multiplier.loc[high_oi_mask] = vomma_enhancement_factor_cfg
    
    enhanced_vommaxoi = vommaxoi_numeric * enhancement_multiplier
    vomma_logger.debug(f"Vomma impact enhanced for {high_oi_mask.sum()} contracts with OI >= {vomma_oi_min_for_enhancement_cfg}.")
    return enhanced_vommaxoi


def calculate_vri_2_0(
    options_df: pd.DataFrame,
    # Column Names
    vannaxoi_col: str, vxoi_col: str, vommaxoi_col: str,
    direct_vega_buy_col: str, direct_vega_sell_col: str, proxy_vega_flow_col: str,
    proxy_vanna_flow_col: str, proxy_vomma_flow_col: str,
    expiration_date_col: str, opt_kind_col: str, option_iv_col_in_df: str,
    strike_col: str, price_col: str, # price_col is underlying price from options_df
    vri_2_0_output_col_name: str, # This will be ids.COL_VRI_2_0_OUTPUT
    option_delta_col: str, # For proximity
    # Config values
    vri_gamma_coeffs_cfg: Dict[str, float],
    term_structure_short_dte_cfg: int, term_structure_mid_dte_cfg: int, term_structure_slope_weight_cfg: float,
    surface_dynamics_lookback_cfg: int, surface_dynamics_sensitivity_cfg: float,
    vomma_enhancement_oi_min_cfg: float, vomma_enhancement_factor_cfg: float,
    adaptive_iv_thresholds_enabled_cfg: bool,
    iv_context_percentile_key_cfg: str, # Key in iv_context_for_vri2 for IV Rank
    adaptive_iv_low_percentile_base_cfg: float, adaptive_iv_high_percentile_base_cfg: float,
    adaptive_iv_shift_factor_cfg: float,
    vol_context_weight_low_iv_cfg: float, vol_context_weight_high_iv_cfg: float,
    # Contextual Data
    current_underlying_price_for_vri2: Optional[float], # Scalar current price
    current_underlying_iv_for_vri2: Optional[float], # Scalar current underlying IV
    avg_5day_underlying_iv_for_vri2: Optional[float], # Scalar 5D Avg IV
    iv_context_for_vri2: Optional[Dict[str, Any]], # Contains IV Rank, etc.
    historical_iv_surface_snapshots_for_vri2: Optional[Deque[Dict[str, float]]], # For surface dynamics
    log_instance: Optional[logging.Logger] = None
) -> pd.DataFrame:
    vri2_logger = log_instance.getChild("CalculateVRI2_0_Main") if log_instance else logger.getChild("CalculateVRI2_0_Main")
    vri2_logger.info(f"Calculating VRI 2.0. Output to: {vri_2_0_output_col_name}")
    df = options_df.copy()

    required_cols_vri2 = [
        vannaxoi_col, vxoi_col, vommaxoi_col, direct_vega_buy_col, direct_vega_sell_col,
        proxy_vega_flow_col, proxy_vanna_flow_col, proxy_vomma_flow_col,
        expiration_date_col, opt_kind_col, option_iv_col_in_df, strike_col, price_col, option_delta_col,
        ids.COL_OI_OPTION_CONTRACT # Needed for vomma enhancement
    ]
    df, cols_ok = ensure_columns(df, required_cols_vri2, "VRI2_0_Input", log_instance=vri2_logger)
    if not cols_ok:
        vri2_logger.warning("VRI 2.0: Missing required columns. Returning DataFrame with zero VRI 2.0.")
        df[vri_2_0_output_col_name] = 0.0
        df[ids.COL_ENHANCED_VVR_SENS] = 0.0; df[ids.COL_ENHANCED_VFI_SENS] = 0.0
        return df

    # 1. Calculate base VRI components (similar to v1.6)
    gamma_aligned = float(vri_gamma_coeffs_cfg.get("aligned",1.3))
    gamma_opposed = float(vri_gamma_coeffs_cfg.get("opposed",0.7))
    gamma_neutral = float(vri_gamma_coeffs_cfg.get("neutral",1.0))
    vannaxoi_numeric = pd.to_numeric(df[vannaxoi_col], errors='coerce').fillna(0.0)
    vanna_flow_proxy = pd.to_numeric(df.get(proxy_vanna_flow_col,0.0), errors='coerce').fillna(0.0)
    alignment_gamma_sign = np.sign(vanna_flow_proxy) * np.sign(vannaxoi_numeric.replace(0,1e-9))
    df['gamma_coeff_vri2'] = np.select([alignment_gamma_sign > 0.3, alignment_gamma_sign < -0.3], [gamma_aligned, gamma_opposed], default=gamma_neutral)
    df['vanna_flow_to_oi_ratio_vri2'] = (vanna_flow_proxy.abs() / (vannaxoi_numeric.abs().replace(0,np.inf) + MIN_DENOMINATOR_VRI2)).fillna(0.0)
    
    # Use enhanced vomma if enabled, otherwise raw vommaxoi
    enhanced_vommaxoi = enhance_vomma_impact(df, vommaxoi_col, ids.COL_OI_OPTION_CONTRACT, vomma_enhancement_oi_min_cfg, vomma_enhancement_factor_cfg, log_instance=vri2_logger)
    vomma_flow_proxy = pd.to_numeric(df.get(proxy_vomma_flow_col,0.0), errors='coerce').fillna(0.0)
    df['norm_net_vomma_flow_vri2'] = normalize_series(vomma_flow_proxy, f"{proxy_vomma_flow_col}_for_vri2", MIN_DENOMINATOR_VRI2) # Using proxy flow

    # 2. Volatility Term Structure Slope
    term_structure_slope_val = calculate_volatility_term_structure_slope(df, option_iv_col_in_df, expiration_date_col, strike_col, current_underlying_price_for_vri2, term_structure_short_dte_cfg, term_structure_mid_dte_cfg, log_instance=vri2_logger)
    term_structure_factor = 1.0 + term_structure_slope_val * float(term_structure_slope_weight_cfg) # Example: slope of 0.01 * weight 0.2 = 1.002
    term_structure_factor = np.clip(term_structure_factor, 0.7, 1.3)
    df['term_structure_factor_vri2'] = term_structure_factor

    # 3. Volatility Surface Dynamics
    surface_dynamics_factor_val = analyze_volatility_surface_dynamics(historical_iv_surface_snapshots_for_vri2, surface_dynamics_lookback_cfg, surface_dynamics_sensitivity_cfg, log_instance=vri2_logger)
    df['surface_dynamics_factor_vri2'] = surface_dynamics_factor_val

    # 4. Adaptive IV Thresholds & Context Weighting
    iv_context_weight = 1.0
    if adaptive_iv_thresholds_enabled_cfg and iv_context_for_vri2:
        iv_rank_vri2 = iv_context_for_vri2.get(iv_context_percentile_key_cfg) # e.g., "iv_percentile_30d"
        if pd.notna(iv_rank_vri2) and isinstance(iv_rank_vri2, (float, int)):
            iv_rank_vri2 = float(iv_rank_vri2)
            if iv_rank_vri2 < (float(adaptive_iv_low_percentile_base_cfg) / 100.0): # Low IV
                iv_context_weight = float(vol_context_weight_low_iv_cfg)
            elif iv_rank_vri2 > (float(adaptive_iv_high_percentile_base_cfg) / 100.0): # High IV
                iv_context_weight = float(vol_context_weight_high_iv_cfg)
            # Could add logic for mid-range IV if needed
            vri2_logger.debug(f"IV Context Weight for VRI 2.0: {iv_context_weight:.2f} (IV Rank: {iv_rank_vri2:.2f})")
    df['iv_context_weight_vri2'] = iv_context_weight

    vxoi_numeric = pd.to_numeric(df[vxoi_col], errors='coerce').fillna(0.0)
    vxoi_sign = np.sign(vxoi_numeric.replace(0, 1e-9))

    # Combine all factors for VRI 2.0
    df[vri_2_0_output_col_name] = (
        enhanced_vommaxoi * vxoi_sign * # Using enhanced vomma
        (1 + df['gamma_coeff_vri2'] * df['vanna_flow_to_oi_ratio_vri2']) *
        df['norm_net_vomma_flow_vri2'] *
        df['term_structure_factor_vri2'] *
        df['surface_dynamics_factor_vri2'] *
        df['iv_context_weight_vri2']
    ).fillna(0.0)
    vri2_logger.info(f"VRI 2.0 calculation complete. Output: '{vri_2_0_output_col_name}'. Example: {df[vri_2_0_output_col_name].head(1).item() if not df.empty and vri_2_0_output_col_name in df.columns else 'N/A'}")

    # Calculate Enhanced VVR and VFI (as per original module structure)
    df = calculate_enhanced_vvr_sensitivity(df, proxy_vanna_flow_col, proxy_vomma_flow_col, log_instance=vri2_logger)
    df = calculate_enhanced_vfi_sensitivity(df, direct_vega_buy_col, direct_vega_sell_col, proxy_vega_flow_col, vxoi_col, log_instance=vri2_logger)

    return df

def calculate_enhanced_vvr_sensitivity(
    df_input: pd.DataFrame,
    proxy_vanna_flow_col: str,
    proxy_vomma_flow_col: str,
    log_instance: Optional[logging.Logger] = None
) -> pd.DataFrame:
    evvr_logger = log_instance.getChild("CalculateEnhancedVVR") if log_instance else logger.getChild("CalculateEnhancedVVR")
    df = df_input.copy()
    if not all(c in df.columns for c in [proxy_vanna_flow_col, proxy_vomma_flow_col]):
        evvr_logger.warning("Missing Vanna/Vomma flow columns for E-VVR. Setting to zero.")
        df[ids.COL_ENHANCED_VVR_SENS] = 0.0
        return df
    vanna_flow = pd.to_numeric(df[proxy_vanna_flow_col], errors='coerce').fillna(0.0)
    vomma_flow = pd.to_numeric(df[proxy_vomma_flow_col], errors='coerce').fillna(0.0)
    df[ids.COL_ENHANCED_VVR_SENS] = (vanna_flow.abs() / (vomma_flow.abs().replace(0, np.inf) + MIN_DENOMINATOR_VRI2)).fillna(0.0)
    evvr_logger.debug("Enhanced VVR Sensitivity calculated.")
    return df

def calculate_enhanced_vfi_sensitivity(
    df_input: pd.DataFrame,
    direct_vega_buy_col: str, direct_vega_sell_col: str, proxy_vega_flow_col: str, # Vega flow sources
    vxoi_col: str, # Vega Open Interest
    log_instance: Optional[logging.Logger] = None
) -> pd.DataFrame:
    evfi_logger = log_instance.getChild("CalculateEnhancedVFI") if log_instance else logger.getChild("CalculateEnhancedVFI")
    df = df_input.copy()
    if vxoi_col not in df.columns:
        evfi_logger.warning(f"Missing VXOI column '{vxoi_col}' for E-VFI. Setting to zero.")
        df[ids.COL_ENHANCED_VFI_SENS] = 0.0
        return df

    net_abs_vega_flow = pd.Series(0.0, index=df.index)
    if direct_vega_buy_col in df.columns and direct_vega_sell_col in df.columns and not (df[direct_vega_buy_col].isnull().all() and df[direct_vega_sell_col].isnull().all()):
        raw_vega_flow = pd.to_numeric(df[direct_vega_buy_col],errors='coerce').fillna(0) - pd.to_numeric(df[direct_vega_sell_col],errors='coerce').fillna(0)
        net_abs_vega_flow = normalize_series(raw_vega_flow.abs(), 'net_direct_abs_vega_flow_for_e_vfi', MIN_DENOMINATOR_VRI2)
    elif proxy_vega_flow_col in df.columns:
        raw_vega_flow = pd.to_numeric(df.get(proxy_vega_flow_col,0.0), errors='coerce').fillna(0.0)
        net_abs_vega_flow = normalize_series(raw_vega_flow.abs(), f"{proxy_vega_flow_col}_abs_for_e_vfi_proxy", MIN_DENOMINATOR_VRI2)
    else:
        evfi_logger.debug("Neither direct nor proxy vega flow columns found for E-VFI. Net vega flow will be zero.")


    vxoi_numeric = pd.to_numeric(df[vxoi_col], errors='coerce').fillna(0.0)
    norm_vxoi_abs = normalize_series(vxoi_numeric.abs(), 'vxoi_abs_for_e_vfi', MIN_DENOMINATOR_VRI2)
    df[ids.COL_ENHANCED_VFI_SENS] = (net_abs_vega_flow / (norm_vxoi_abs.replace(0, np.inf) + MIN_DENOMINATOR_VRI2)).fillna(0.0)
    evfi_logger.debug("Enhanced VFI Sensitivity calculated.")
    return df

