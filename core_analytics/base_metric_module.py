# core_analytics/base_metric_module.py
"""
Functions for calculating core v2.3 base metrics: Custom Flow DAG, TDPI, and VRI.
This version is refactored for full ids.py integration, accepts specific
input column names as parameters, and is unabridged for v2.3 functionality.

Version: EOTS_BaseMetrics_v2.3.1_Canon_IDS_Unabridged
"""
import pandas as pd
import numpy as np
import logging
import sys # For fallback ids import check
from typing import Union, Optional, List, Dict, Any, Tuple, Callable
from datetime import datetime, time, date

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
    logger_init.info("Base Metric Module (v2.3.1 Canon): Core utilities and ids imported successfully.")
except ImportError as e_base_metric_imp:
    IMPORTS_SUCCESSFUL = False
    print(f"CRITICAL IMPORT ERROR in base_metric_module.py: {e_base_metric_imp}. Calculations will fail or use dummies.")
    # Define fallback constants and dummy functions if ids.py or system_utilities are missing
    class ids: # type: ignore
        COL_DAG_CUSTOM_RAW = "dag_custom"; COL_TDPI_RAW = "tdpi"; COL_VRI_RAW = "vri"
        COL_DAG_FLOW_RATIO_DEBUG = "dag_flow_ratio_debug"; COL_NORM_NET_GAMMA_FLOW_DAG = "norm_net_gamma_flow"
        COL_BETA_TDPI = "beta"; COL_CHARM_FLOW_TO_OI_RATIO_TDPI = "charm_flow_to_charm_oi_ratio"
        COL_NORM_NET_THETA_FLOW_TDPI = "norm_net_theta_flow"; COL_CTR = "ctr"; COL_TDFI = "tdfi"
        COL_GAMMA_COEFF_VRI = "gamma_coeff_vri"; COL_VANNA_FLOW_TO_OI_RATIO_VRI = "vanna_flow_to_vanna_oi_ratio"
        COL_NORM_NET_VOMMA_FLOW_VRI = "norm_net_vomma_flow"; COL_SKEW_FACTOR_VRI = "skew_factor"
        COL_VOL_TREND_FACTOR_VRI = "vol_trend_factor"; COL_NORM_VXOI_ABS_VRI = "norm_vxoi_abs"
        COL_VVR = "vvr"; COL_VFI = "vfi"; IMPACT_PROXIMITY = "proximity" # Though proximity is calculated internally
        # Add other constants used as defaults if ids.py is missing
        COL_STRIKE = "strike_price"; COL_OPT_KIND = "opt_kind"; COL_DELTA_CONTRACT = "delta"
        COL_OI_OPTION_CONTRACT = "oi"; COL_UNDERLYING_SYMBOL = "underlying_symbol"
        COL_EXPIRATION_DATE = "expiration_date"; COL_PRICE_OPTION_CONTRACT = "price" # Option's own price

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
    logger.critical("Base Metric Module running with DUMMY imports due to failure. Functionality will be severely limited.")

MIN_NORMALIZATION_DENOMINATOR_BASE = 1e-9 # Local constant for this module
DEFAULT_ATR_FALLBACK_MIN_VALUE_BASE = 0.01
DEFAULT_ATR_FALLBACK_PERCENTAGE_BASE = 0.01


def calculate_custom_flow_dag(
    options_df: pd.DataFrame,
    gamma_exposure_col: str,
    delta_exposure_col: str,
    direct_delta_buy_col: str,
    direct_delta_sell_col: str,
    proxy_delta_flow_col: str,
    direct_gamma_buy_col: str,
    direct_gamma_sell_col: str,
    proxy_gamma_flow_col: str,
    volm_col_for_weighting: str,
    strike_col: str,
    option_price_col_in_df: Optional[str], # Name of the option's own price column
    dag_alpha_coeffs: Dict[str, float],
    actual_underlying_price: Optional[float] = None,
    # Added option_delta_col for proximity calculation
    option_delta_col: str = ids.COL_DELTA_CONTRACT, # Default to standard option delta
    log_instance: Optional[logging.Logger] = None
) -> pd.DataFrame:
    """
    Calculates Custom Flow Delta Adjusted Gamma Exposure (DAG).
    Output columns: ids.COL_DAG_CUSTOM_RAW, ids.COL_DAG_FLOW_RATIO_DEBUG, ids.COL_NORM_NET_GAMMA_FLOW_DAG
    """
    calc_name = "CustomFlowDAG_BaseMetric_v2.3.1"
    dag_logger = log_instance.getChild(calc_name) if log_instance else logger.getChild(calc_name)
    dag_logger.info(f"Calculating {calc_name} using strike_col: '{strike_col}'...")

    df = options_df.copy()
    required_cols_dag = [
        strike_col, gamma_exposure_col, delta_exposure_col,
        direct_delta_buy_col, direct_delta_sell_col, proxy_delta_flow_col,
        direct_gamma_buy_col, direct_gamma_sell_col, proxy_gamma_flow_col,
        volm_col_for_weighting, ids.COL_OI_OPTION_CONTRACT, option_delta_col # Ensure option_delta_col is checked
    ]
    if option_price_col_in_df and option_price_col_in_df in df.columns: # Optional
        required_cols_dag.append(option_price_col_in_df)

    df, cols_ok = ensure_columns(df, required_cols_dag, calc_name, log_instance=dag_logger)
    if not cols_ok:
        dag_logger.warning(f"{calc_name}: Missing/invalid columns. Results may be impacted.")
        df[ids.COL_DAG_CUSTOM_RAW] = 0.0
        df[ids.COL_DAG_FLOW_RATIO_DEBUG] = 0.0
        df[ids.COL_NORM_NET_GAMMA_FLOW_DAG] = 0.0
        return df

    current_price_for_prox = actual_underlying_price

    alpha_aligned = float(dag_alpha_coeffs.get("aligned", 1.3))
    alpha_opposed = float(dag_alpha_coeffs.get("opposed", 0.7))
    alpha_neutral = float(dag_alpha_coeffs.get("neutral", 1.0))

    dxoi_numeric = pd.to_numeric(df[delta_exposure_col], errors='coerce').fillna(0.0)

    net_delta_flow_series = pd.Series(0.0, index=df.index, name="net_delta_flow_for_dag")
    delta_flow_source_used = f"proxy ('{proxy_delta_flow_col}')" # Default assumption
    if direct_delta_buy_col in df.columns and direct_delta_sell_col in df.columns and \
       not (df[direct_delta_buy_col].isnull().all() and df[direct_delta_sell_col].isnull().all()):
        net_delta_flow_series = pd.to_numeric(df[direct_delta_buy_col], errors='coerce').fillna(0.0) - \
                                pd.to_numeric(df[direct_delta_sell_col], errors='coerce').fillna(0.0)
        delta_flow_source_used = "direct_deltas"
    elif proxy_delta_flow_col in df.columns:
        net_delta_flow_series = pd.to_numeric(df.get(proxy_delta_flow_col, 0.0), errors='coerce').fillna(0.0)
    else:
        dag_logger.warning(f"{calc_name}: Neither direct nor proxy delta flow columns found. Net delta flow will be zero.")

    alignment_factor_sign = np.sign(net_delta_flow_series) * np.sign(dxoi_numeric.replace(0, 1e-9))
    df['alpha_applied_dag'] = np.select(
        [alignment_factor_sign > 0.3, alignment_factor_sign < -0.3],
        [alpha_aligned, alpha_opposed],
        default=alpha_neutral
    )

    dxoi_abs_for_ratio = dxoi_numeric.abs().replace(0, np.inf) # Avoid division by zero
    normalized_flow_ratio = 2 / (1 + np.exp(-3 * (net_delta_flow_series.abs() / dxoi_abs_for_ratio).fillna(0.0))) - 1
    df[ids.COL_DAG_FLOW_RATIO_DEBUG] = normalized_flow_ratio

    raw_gamma_flow_series = pd.Series(0.0, index=df.index, name="raw_gamma_flow_for_dag")
    norm_net_gamma_flow_series = pd.Series(0.0, index=df.index, name="norm_net_gamma_flow_for_dag")
    gamma_flow_source_used = f"proxy ('{proxy_gamma_flow_col}')" # Default assumption
    if direct_gamma_buy_col in df.columns and direct_gamma_sell_col in df.columns and \
       not (df[direct_gamma_buy_col].isnull().all() and df[direct_gamma_sell_col].isnull().all()):
        raw_gamma_flow_series = pd.to_numeric(df[direct_gamma_buy_col], errors='coerce').fillna(0.0) - \
                                pd.to_numeric(df[direct_gamma_sell_col], errors='coerce').fillna(0.0)
        norm_net_gamma_flow_series = normalize_series(raw_gamma_flow_series, 'net_direct_gamma_flow_for_dag', min_denominator=MIN_NORMALIZATION_DENOMINATOR_BASE)
        gamma_flow_source_used = "direct_gammas"
    elif proxy_gamma_flow_col in df.columns:
        raw_gamma_flow_series = pd.to_numeric(df.get(proxy_gamma_flow_col, 0.0), errors='coerce').fillna(0.0)
        norm_net_gamma_flow_series = normalize_series(raw_gamma_flow_series, f"{proxy_gamma_flow_col}_for_dag_proxy", min_denominator=MIN_NORMALIZATION_DENOMINATOR_BASE)
    else:
        dag_logger.warning(f"{calc_name}: Neither direct nor proxy gamma flow columns found. Net gamma flow will be zero.")
    df[ids.COL_NORM_NET_GAMMA_FLOW_DAG] = norm_net_gamma_flow_series

    gamma_exposure_values = pd.to_numeric(df[gamma_exposure_col], errors='coerce').fillna(0.0)
    volume_values = pd.to_numeric(df.get(volm_col_for_weighting, 0.0), errors='coerce').fillna(0.0)
    norm_volume = normalize_series(volume_values.abs(), 'volume_for_gamma_weight_dag', min_denominator=MIN_NORMALIZATION_DENOMINATOR_BASE)

    # Ensure volume_weight_factor_dag_cfg is fetched from config or uses a default
    # This should be passed by mspi_orchestration_module after fetching from config
    # For now, using a placeholder default if not easily available.
    # Ideally: volume_weight_factor_dag_cfg = config_value_getter(...)
    volume_weight_factor_dag_cfg = 0.3 # Placeholder default

    volume_weighted_gamma = gamma_exposure_values * (1 + volume_weight_factor_dag_cfg * norm_volume)
    dxoi_sign = np.sign(dxoi_numeric.replace(0, 1e-9))

    proximity_factor_series = pd.Series(1.0, index=df.index)
    if current_price_for_prox is not None and pd.notna(current_price_for_prox):
        delta_series_for_prox = pd.to_numeric(df.get(option_delta_col), errors='coerce') # Use passed option_delta_col
        proximity_factor_series = calculate_proximity_factor(
            pd.to_numeric(df[strike_col], errors='coerce'),
            current_price_for_prox,
            delta=delta_series_for_prox,
            log_instance=dag_logger
        )
        proximity_factor_series = proximity_factor_series.fillna(0.5)
    else:
        dag_logger.warning(f"{calc_name}: actual_underlying_price for proximity is None or NaN. Defaulting proximity_factor to 0.5.")
        proximity_factor_series.fillna(0.5, inplace=True)

    df[ids.COL_DAG_CUSTOM_RAW] = (
        volume_weighted_gamma * dxoi_sign *
        (1 + df['alpha_applied_dag'] * df[ids.COL_DAG_FLOW_RATIO_DEBUG]) *
        df[ids.COL_NORM_NET_GAMMA_FLOW_DAG] *
        proximity_factor_series
    ).fillna(0.0)

    dag_logger.info(f"{calc_name} calculation complete. DeltaFlowSrc: {delta_flow_source_used}, GammaFlowSrc: {gamma_flow_source_used}.")
    return df


def calculate_tdpi(
    options_df: pd.DataFrame,
    charmxoi_col: str,
    txoi_col: str,
    direct_theta_buy_col: str,
    direct_theta_sell_col: str,
    proxy_theta_flow_col: str,
    proxy_charm_flow_col: str,
    expiration_date_col: str,
    strike_col: str,
    option_price_col_in_df: Optional[str],
    underlying_symbol_col: str,
    tdpi_beta_coeffs: Dict[str, float],
    base_gaussian_width: float,
    atr_fallback_config: Dict[str, Any],
    actual_underlying_price: Optional[float] = None,
    current_time: Optional[time] = None,
    historical_ohlc_df_for_atr: Optional[pd.DataFrame] = None,
    log_instance: Optional[logging.Logger] = None
) -> pd.DataFrame:
    calc_name = "TDPI_BaseMetric_v2.3.1"
    tdpi_logger = log_instance.getChild(calc_name) if log_instance else logger.getChild(calc_name)
    tdpi_logger.info(f"Calculating {calc_name} using strike_col: '{strike_col}'...")

    df = options_df.copy()
    required_cols_tdpi = [
        strike_col, underlying_symbol_col, ids.COL_OPT_KIND, # Standardized
        charmxoi_col, txoi_col,
        direct_theta_buy_col, direct_theta_sell_col, proxy_theta_flow_col,
        proxy_charm_flow_col, expiration_date_col, ids.COL_DELTA_CONTRACT # Standardized
    ]
    if option_price_col_in_df and option_price_col_in_df in df.columns:
        required_cols_tdpi.append(option_price_col_in_df)

    df, cols_ok = ensure_columns(df, required_cols_tdpi, calc_name, log_instance=tdpi_logger)
    if not cols_ok:
        tdpi_logger.warning(f"{calc_name}: Missing/invalid columns. Results may be impacted.")
        df[ids.COL_TDPI_RAW] = 0.0; df[ids.COL_CTR] = 0.0; df[ids.COL_TDFI] = 0.0
        return df

    current_price_for_atr_and_gaussian = actual_underlying_price

    beta_aligned = float(tdpi_beta_coeffs.get("aligned",1.3))
    beta_opposed = float(tdpi_beta_coeffs.get("opposed",0.7))
    beta_neutral = float(tdpi_beta_coeffs.get("neutral",1.0))

    charmxoi_numeric = pd.to_numeric(df[charmxoi_col], errors='coerce').fillna(0.0)
    charm_flow_proxy_series = pd.to_numeric(df.get(proxy_charm_flow_col, 0.0), errors='coerce').fillna(0.0)
    alignment_beta_sign = np.sign(charm_flow_proxy_series) * np.sign(charmxoi_numeric.replace(0,1e-9))
    df[ids.COL_BETA_TDPI] = np.select([alignment_beta_sign > 0.3, alignment_beta_sign < -0.3], [beta_aligned, beta_opposed], default=beta_neutral)
    df[ids.COL_CHARM_FLOW_TO_OI_RATIO_TDPI] = (charm_flow_proxy_series.abs() / charmxoi_numeric.abs().replace(0,np.inf)).fillna(0.0)

    norm_net_theta_flow_series = pd.Series(0.0, index=df.index, name="norm_net_theta_flow_for_tdpi")
    raw_theta_flow_for_sub_metrics = pd.Series(0.0, index=df.index)
    theta_flow_source_used = f"proxy ('{proxy_theta_flow_col}')"
    if direct_theta_buy_col in df.columns and direct_theta_sell_col in df.columns and \
       not (df[direct_theta_buy_col].isnull().all() and df[direct_theta_sell_col].isnull().all()):
        raw_theta_flow_for_sub_metrics = pd.to_numeric(df[direct_theta_buy_col], errors='coerce').fillna(0.0) - \
                                         pd.to_numeric(df[direct_theta_sell_col], errors='coerce').fillna(0.0)
        norm_net_theta_flow_series = normalize_series(raw_theta_flow_for_sub_metrics, 'net_direct_theta_flow_for_tdpi', min_denominator=MIN_NORMALIZATION_DENOMINATOR_BASE)
        theta_flow_source_used = "direct_thetas"
    elif proxy_theta_flow_col in df.columns:
        raw_theta_flow_for_sub_metrics = pd.to_numeric(df.get(proxy_theta_flow_col, 0.0), errors='coerce').fillna(0.0)
        norm_net_theta_flow_series = normalize_series(raw_theta_flow_for_sub_metrics, f"{proxy_theta_flow_col}_for_tdpi_proxy", min_denominator=MIN_NORMALIZATION_DENOMINATOR_BASE)
    else:
        tdpi_logger.warning(f"{calc_name}: Neither direct nor proxy theta flow columns found. Net theta flow will be zero.")
    df[ids.COL_NORM_NET_THETA_FLOW_TDPI] = norm_net_theta_flow_series

    atr_val = 0.0
    if current_price_for_atr_and_gaussian is not None and pd.notna(current_price_for_atr_and_gaussian):
        und_sym_for_atr_calc = df[underlying_symbol_col].iloc[0] if not df.empty and underlying_symbol_col in df.columns and pd.notna(df[underlying_symbol_col].iloc[0]) else "UNKNOWN_SYM_TDPI"
        atr_val = get_atr(und_sym_for_atr_calc, current_price_for_atr_and_gaussian, atr_fallback_config, history_df=historical_ohlc_df_for_atr, log_instance=tdpi_logger)

    strike_numeric = pd.to_numeric(df[strike_col], errors='coerce')
    gaussian_weight_factor = pd.Series(1.0, index=df.index)
    if atr_val > MIN_NORMALIZATION_DENOMINATOR_BASE and current_price_for_atr_and_gaussian is not None and not strike_numeric.isnull().all():
        strike_diff_sq = ((strike_numeric.fillna(current_price_for_atr_and_gaussian) - current_price_for_atr_and_gaussian) / atr_val)**2
        gaussian_weight_factor = np.exp(base_gaussian_width * strike_diff_sq).fillna(0.0)
    else:
        tdpi_logger.debug(f"{calc_name}: Conditions for Gaussian weight not met (ATR: {atr_val}, Price: {current_price_for_atr_and_gaussian}). Using neutral factor.")

    dte_weight = pd.Series(1.0, index=df.index)
    if expiration_date_col in df.columns:
        try:
            today = date.today()
            exp_dates = pd.to_datetime(df[expiration_date_col], errors='coerce').dt.date
            dtes = (exp_dates - today).apply(lambda x: x.days if pd.notna(x) and x.days >= 0 else -1) # Treat past/NaT as -1
            dte_weight_raw = np.exp(-0.05 * dtes.fillna(365).astype(float))
            dte_weight_final = np.where(dtes <= 1, 2.0 * dte_weight_raw, dte_weight_raw)
            dte_weight = pd.Series(dte_weight_final, index=df.index).fillna(1.0).clip(0.1, 3.0)
            dte_weight.loc[dtes < 0] = 1.0 # Neutral for past/invalid DTEs
        except Exception as e_dte: tdpi_logger.warning(f"TDPI: Error DTE weights: {e_dte}. Using neutral.", exc_info=False)

    time_of_day_factor = 1.0
    if current_time is not None:
        try:
            current_hour_float = current_time.hour + current_time.minute / 60.0
            if 15.0 <= current_hour_float < 16.0: time_of_day_factor = 1.5
            elif 9.5 <= current_hour_float < 10.5: time_of_day_factor = 1.2
        except Exception as e_tod: tdpi_logger.warning(f"TDPI: Error TOD factor: {e_tod}", exc_info=False)

    txoi_numeric = pd.to_numeric(df[txoi_col], errors='coerce').fillna(0.0)
    txoi_sign = np.sign(txoi_numeric.replace(0,1e-9))

    df[ids.COL_TDPI_RAW] = (
        gaussian_weight_factor *
        (charmxoi_numeric * txoi_sign) *
        (1 + df[ids.COL_BETA_TDPI] * df[ids.COL_CHARM_FLOW_TO_OI_RATIO_TDPI]) *
        df[ids.COL_NORM_NET_THETA_FLOW_TDPI] *
        dte_weight *
        time_of_day_factor
    ).fillna(0.0)

    df[ids.COL_CTR] = (charm_flow_proxy_series.abs() / (raw_theta_flow_for_sub_metrics.abs().replace(0, np.inf) + MIN_NORMALIZATION_DENOMINATOR_BASE)).fillna(0.0)
    norm_txoi_abs = normalize_series(txoi_numeric.abs(), 'txoi_abs_for_tdfi', min_denominator=MIN_NORMALIZATION_DENOMINATOR_BASE)
    norm_raw_theta_flow_abs_for_tdfi = normalize_series(raw_theta_flow_for_sub_metrics.abs(), 'raw_theta_flow_abs_for_tdfi', min_denominator=MIN_NORMALIZATION_DENOMINATOR_BASE)
    df[ids.COL_TDFI] = (norm_raw_theta_flow_abs_for_tdfi / (norm_txoi_abs.replace(0, np.inf) + MIN_NORMALIZATION_DENOMINATOR_BASE)).fillna(0.0)

    tdpi_logger.info(f"{calc_name} calculation complete. ThetaFlowSrc: {theta_flow_source_used}.")
    return df


def calculate_vri(
    options_df: pd.DataFrame,
    vannaxoi_col: str,
    vxoi_col: str,
    vommaxoi_col: str,
    direct_vega_buy_col: str,
    direct_vega_sell_col: str,
    proxy_vega_flow_col: str,
    proxy_vanna_flow_col: str,
    proxy_vomma_flow_col: str,
    expiration_date_col: str,
    opt_kind_col: str,
    option_iv_col_in_df: str,
    vri_gamma_coeffs: Dict[str, float],
    vol_trend_fallback_factor: float,
    strike_col: str,
    current_underlying_iv: Optional[float] = None,
    avg_5day_underlying_iv: Optional[float] = None,
    log_instance: Optional[logging.Logger] = None
) -> pd.DataFrame:
    calc_name = "VRI_BaseMetric_v2.3.1"
    vri_logger = log_instance.getChild(calc_name) if log_instance else logger.getChild(calc_name)
    vri_logger.info(f"Calculating {calc_name} using strike_col: '{strike_col}'...")

    df = options_df.copy()
    required_cols_vri = [
        strike_col, opt_kind_col, option_iv_col_in_df,
        vannaxoi_col, vxoi_col, vommaxoi_col,
        direct_vega_buy_col, direct_vega_sell_col, proxy_vega_flow_col,
        proxy_vanna_flow_col, proxy_vomma_flow_col, expiration_date_col
    ]
    df, cols_ok = ensure_columns(df, required_cols_vri, calc_name, log_instance=vri_logger)
    if not cols_ok:
        vri_logger.warning(f"{calc_name}: Missing/invalid columns. Results may be affected.")
        df[ids.COL_VRI_RAW] = 0.0; df[ids.COL_VVR] = 0.0; df[ids.COL_VFI] = 0.0
        return df

    gamma_aligned = float(vri_gamma_coeffs.get("aligned",1.3))
    gamma_opposed = float(vri_gamma_coeffs.get("opposed",0.7))
    gamma_neutral = float(vri_gamma_coeffs.get("neutral",1.0))

    vannaxoi_numeric = pd.to_numeric(df[vannaxoi_col], errors='coerce').fillna(0.0)
    vanna_flow_proxy_series = pd.to_numeric(df.get(proxy_vanna_flow_col,0.0), errors='coerce').fillna(0.0)
    alignment_gamma_sign = np.sign(vanna_flow_proxy_series) * np.sign(vannaxoi_numeric.replace(0,1e-9))
    df[ids.COL_GAMMA_COEFF_VRI] = np.select([alignment_gamma_sign > 0.3, alignment_gamma_sign < -0.3], [gamma_aligned, gamma_opposed], default=gamma_neutral)
    df[ids.COL_VANNA_FLOW_TO_OI_RATIO_VRI] = (vanna_flow_proxy_series.abs() / vannaxoi_numeric.abs().replace(0,np.inf)).fillna(0.0)

    vomma_flow_proxy_series = pd.to_numeric(df.get(proxy_vomma_flow_col,0.0), errors='coerce').fillna(0.0)
    df[ids.COL_NORM_NET_VOMMA_FLOW_VRI] = normalize_series(vomma_flow_proxy_series, f"{proxy_vomma_flow_col}_for_vri", min_denominator=MIN_NORMALIZATION_DENOMINATOR_BASE)

    skew_factor_val = 1.0
    if opt_kind_col in df.columns and vxoi_col in df.columns and not df.empty:
        calls_df_vri = df[df[opt_kind_col].astype(str).str.lower()=='call']
        puts_df_vri = df[df[opt_kind_col].astype(str).str.lower()=='put']
        sum_call_vxoi_vri = pd.to_numeric(calls_df_vri.get(vxoi_col,0.0),errors='coerce').sum(skipna=True)
        sum_put_vxoi_vri = pd.to_numeric(puts_df_vri.get(vxoi_col,0.0),errors='coerce').sum(skipna=True)
        total_market_vxoi_vri = sum_call_vxoi_vri + sum_put_vxoi_vri
        if pd.notna(total_market_vxoi_vri) and abs(total_market_vxoi_vri) > MIN_NORMALIZATION_DENOMINATOR_BASE:
            skew_factor_val = 1.0 + ((sum_put_vxoi_vri - sum_call_vxoi_vri) / total_market_vxoi_vri)
            skew_factor_val = np.clip(skew_factor_val, 0.5, 1.5)
    df[ids.COL_SKEW_FACTOR_VRI] = skew_factor_val

    vol_trend_factor_val = 1.0
    if current_underlying_iv is not None and avg_5day_underlying_iv is not None and \
       pd.notna(current_underlying_iv) and pd.notna(avg_5day_underlying_iv) and avg_5day_underlying_iv > MIN_NORMALIZATION_DENOMINATOR_BASE:
        vol_trend_factor_val = 1.0 + (current_underlying_iv - avg_5day_underlying_iv) / avg_5day_underlying_iv
    elif option_iv_col_in_df in df.columns and not df[option_iv_col_in_df].isnull().all():
        mean_opt_iv_vri = pd.to_numeric(df[option_iv_col_in_df], errors='coerce').mean()
        if pd.notna(mean_opt_iv_vri) and mean_opt_iv_vri > MIN_NORMALIZATION_DENOMINATOR_BASE:
            approx_5d_avg_iv_vri = mean_opt_iv_vri * vol_trend_fallback_factor
            if approx_5d_avg_iv_vri > MIN_NORMALIZATION_DENOMINATOR_BASE:
                vol_trend_factor_val = 1.0 + (mean_opt_iv_vri - approx_5d_avg_iv_vri) / approx_5d_avg_iv_vri
    df[ids.COL_VOL_TREND_FACTOR_VRI] = np.clip(vol_trend_factor_val, 0.5, 1.5)

    vxoi_numeric = pd.to_numeric(df[vxoi_col], errors='coerce').fillna(0.0)
    vxoi_sign = np.sign(vxoi_numeric.replace(0, 1e-9))
    df[ids.COL_VRI_RAW] = (
        vannaxoi_numeric * vxoi_sign *
        (1 + df[ids.COL_GAMMA_COEFF_VRI] * df[ids.COL_VANNA_FLOW_TO_OI_RATIO_VRI]) *
        df[ids.COL_NORM_NET_VOMMA_FLOW_VRI] *
        df[ids.COL_SKEW_FACTOR_VRI] *
        df[ids.COL_VOL_TREND_FACTOR_VRI]
    ).fillna(0.0)

    df[ids.COL_VVR] = (vanna_flow_proxy_series.abs() / (vomma_flow_proxy_series.abs().replace(0, np.inf) + MIN_NORMALIZATION_DENOMINATOR_BASE)).fillna(0.0)
    norm_net_abs_vega_flow_series = pd.Series(0.0, index=df.index, name="norm_net_abs_vega_flow_for_vfi")
    raw_vega_flow_for_log = pd.Series(0.0, index=df.index) # For logging source
    vfi_vega_flow_source_log = f"proxy ('{proxy_vega_flow_col}')" # Default assumption

    if direct_vega_buy_col in df.columns and direct_vega_sell_col in df.columns and \
       not (df[direct_vega_buy_col].isnull().all() and df[direct_vega_sell_col].isnull().all()):
        raw_vega_flow_for_log = pd.to_numeric(df[direct_vega_buy_col], errors='coerce').fillna(0.0) - \
                                pd.to_numeric(df[direct_vega_sell_col], errors='coerce').fillna(0.0)
        norm_net_abs_vega_flow_series = normalize_series(raw_vega_flow_for_log.abs(), 'net_direct_abs_vega_flow_for_vfi', min_denominator=MIN_NORMALIZATION_DENOMINATOR_BASE)
        vfi_vega_flow_source_log = "direct_vegas"
    elif proxy_vega_flow_col in df.columns:
        raw_vega_flow_for_log = pd.to_numeric(df.get(proxy_vega_flow_col,0.0), errors='coerce').fillna(0.0)
        norm_net_abs_vega_flow_series = normalize_series(raw_vega_flow_for_log.abs(), f"{proxy_vega_flow_col}_abs_for_vfi_proxy", min_denominator=MIN_NORMALIZATION_DENOMINATOR_BASE)
    else:
        vri_logger.warning(f"{calc_name}: Neither direct nor proxy vega flow columns found. VFI will be based on zero flow.")


    df[ids.COL_NORM_VXOI_ABS_VRI] = normalize_series(vxoi_numeric.abs(), 'vxoi_abs_for_vfi', min_denominator=MIN_NORMALIZATION_DENOMINATOR_BASE)
    df[ids.COL_VFI] = (norm_net_abs_vega_flow_series / (df[ids.COL_NORM_VXOI_ABS_VRI].replace(0, np.inf) + MIN_NORMALIZATION_DENOMINATOR_BASE)).fillna(0.0)

    vri_logger.info(f"{calc_name} calculation complete. VFI VegaFlowSrc: {vfi_vega_flow_source_log}.")
    return df
