# core_analytics/mspi_orchestration_module.py
"""
Main orchestrator for calculating the Multi-Strategy Pressure Indicator (MSPI)
and its constituent metrics. This version focuses on v2.3 base metrics (DAG, TDPI, VRI, original SDAGs)
and their normalization and combination into MSPI, SAI, SSI, ARFI.
Enhanced v2.5 metrics are conditionally calculated based on flags.

Version: EOTS_MSPI_Orch_v2.3.1_Canon_IDS_Unabridged
"""
import pandas as pd
import numpy as np
import logging
import sys # For fallback ids import check
from typing import Union, Optional, List, Dict, Any, Callable, Deque
from datetime import datetime, time, date

# --- Project-Specific Imports from within core_analytics package ---
try:
    from utils import ids # Centralized IDs
    from .system_utilities import normalize_series, ensure_columns, get_atr
    from .base_metric_module import calculate_custom_flow_dag, calculate_tdpi, calculate_vri
    from .sdag_module import (
        calculate_sdag_multiplicative,
        calculate_sdag_directional,
        calculate_sdag_weighted,
        calculate_sdag_volatility_focused
    )
    # Import v2.5 modules for conditional execution, though they won't run in a pure v2.3 setup
    # Their functions will only be called if corresponding enable flags are True.
    from . import adaptive_dag_module
    from . import dynamic_tdpi_module
    from . import enhanced_sdag_module
    from . import vri_2_0_module
    _SUB_MODULE_IMPORTS_OK = True
    logger_init = logging.getLogger(__name__)
    logger_init.info("MSPI Orchestration (v2.3.1 Canon): Core metric modules imported successfully.")
except ImportError as e_mspi_orch_imp:
    _SUB_MODULE_IMPORTS_OK = False
    print(f"CRITICAL IMPORT ERROR in mspi_orchestration_module.py: {e_mspi_orch_imp}. MSPI calculations will fail or use dummies.")
    # Define dummy functions if imports fail
    def _dummy_metric_calculator(*args: Any, **kwargs: Any) -> pd.DataFrame:
        df_arg = next((arg for arg in args if isinstance(arg, pd.DataFrame)), None)
        if df_arg is None: df_arg = pd.DataFrame()
        if 'ids' in sys.modules:
            for col_const_name in dir(sys.modules['elite_options_system_package.utils.ids']):
                 if col_const_name.startswith("COL_") and ("_RAW" in col_const_name or "_NORM" in col_const_name or col_const_name in ["COL_MSPI_SCORE", "COL_SAI", "COL_SSI", "COL_ARFI"]): # Added more
                    col_name = getattr(sys.modules['elite_options_system_package.utils.ids'], col_const_name)
                    if col_name not in df_arg.columns: df_arg[col_name] = 0.0
        return df_arg.copy()

    calculate_custom_flow_dag = calculate_tdpi = calculate_vri = _dummy_metric_calculator # type: ignore
    calculate_sdag_multiplicative = calculate_sdag_directional = calculate_sdag_weighted = calculate_sdag_volatility_focused = _dummy_metric_calculator # type: ignore
    adaptive_dag_module = dynamic_tdpi_module = enhanced_sdag_module = vri_2_0_module = type('DummyAdvancedModule', (), {
        'calculate_adaptive_dag': _dummy_metric_calculator,
        'calculate_dynamic_tdpi': _dummy_metric_calculator,
        'calculate_enhanced_sdag': _dummy_metric_calculator,
        'calculate_vri_2_0': _dummy_metric_calculator
    })() # type: ignore

    if 'ids' not in sys.modules: # Fallback for ids itself
        class ids: # type: ignore
            COL_MSPI_SCORE="mspi"; COL_SAI="sai"; COL_SSI="ssi"; COL_ARFI="arfi";
            COL_DAG_CUSTOM_RAW="dag_custom"; COL_TDPI_RAW="tdpi"; COL_VRI_RAW="vri";
            COL_SDAG_MULTIPLICATIVE_RAW="sdag_multiplicative"; COL_SDAG_DIRECTIONAL_RAW="sdag_directional";
            COL_SDAG_WEIGHTED_RAW="sdag_weighted"; COL_SDAG_VOLATILITY_FOCUSED_RAW="sdag_volatility_focused";
            COL_DAG_CUSTOM_NORM="dag_custom_norm"; COL_TDPI_NORM="tdpi_norm"; COL_VRI_NORM="vri_norm";
            COL_SDAG_MULTIPLICATIVE_NORM="sdag_multiplicative_norm"; COL_SDAG_DIRECTIONAL_NORM="sdag_directional_norm";
            COL_SDAG_WEIGHTED_NORM="sdag_weighted_norm"; COL_SDAG_VOLATILITY_FOCUSED_NORM="sdag_volatility_focused_norm";
            COL_CTR="ctr"; COL_TDFI="tdfi"; COL_VVR="vvr"; COL_VFI="vfi";
            CFG_DATA_PROCESSOR_SETTINGS_BASE_KEY = "data_processor_settings"; CFG_WEIGHTS_KEY = "weights";
            CFG_WEIGHTS_SELECTION_LOGIC_KEY = "selection_logic"; CFG_WEIGHTS_TIME_BASED_DEFS_KEY = "time_based_definitions";
            CFG_WEIGHTS_MORNING_END_KEY = "morning_end"; CFG_WEIGHTS_MIDDAY_END_KEY = "midday_end";
            CFG_WEIGHTS_SESSION_FINAL_KEY = "final"; CFG_WEIGHTS_SESSION_MIDDAY_KEY = "midday";
            CFG_WEIGHTS_SESSION_MORNING_KEY = "morning"; CFG_WEIGHTS_TIME_BASED_KEY = "time_based";
            COL_A_DAG_NORM = "a_dag_norm"; COL_D_TDPI_NORM = "d_tdpi_norm";
            COL_VRI_2_0_NORM = "vri_2_0_norm"; COL_E_SDAG_COMPOSITE_NORM = "e_sdag_composite_norm";
            COL_A_DAG_OUTPUT = "a_dag"; COL_D_TDPI_OUTPUT = "d_tdpi"; COL_VRI_2_0_OUTPUT = "vri_2_0";
            COL_E_SDAG_COMPOSITE_OUTPUT = "e_sdag_composite"; COL_SDAG_CONVICTION_SCORE = "sdag_conviction_score";
            COL_E_SDAG_SKEW_ADJUSTED_GEX = "e_sdag_skew_adjusted_gex";

    def normalize_series(series: pd.Series, series_name: str, min_denominator: float = 1e-9) -> pd.Series: return series if isinstance(series, pd.Series) else pd.Series(dtype=float) # type: ignore
    def ensure_columns(df: pd.DataFrame, req_cols: List[str], name: str, log_instance: Optional[logging.Logger]=None) -> Tuple[pd.DataFrame, bool]: # type: ignore
        missing = [col for col in req_cols if col not in df.columns]
        if missing and log_instance: log_instance.warning(f"Dummy ensure_columns: Missing {missing} in {name}")
        return df, not missing
    def get_atr(sym:str, price:float, cfg:Dict, hist:Optional[pd.DataFrame]=None, log_instance:Optional[logging.Logger]=None) -> float: return 0.01 * price if price else 0.5 # type: ignore

# Module-level logger
logger = logging.getLogger(__name__)
if not _SUB_MODULE_IMPORTS_OK:
    logger.critical("MSPI Orchestration running with DUMMY metric calculation modules due to import failures.")

MIN_NORMALIZATION_DENOMINATOR = 1e-9

def get_mspi_weights(
    config_value_getter: Callable[[List[str], Any], Any],
    a_dag_enabled_its: bool, a_dag_norm_col_its: str,
    d_tdpi_enabled_its: bool, d_tdpi_norm_col_its: str,
    vri_2_0_enabled_its: bool, vri_2_0_norm_col_its: str,
    e_sdag_enabled_its: bool, e_sdag_composite_norm_col_its: str,
    current_time_for_weights: Optional[time] = None,
    iv_context_for_weights: Optional[Dict[str, Any]] = None,
    adaptive_system_enabled_its: bool = False,
    log_instance: Optional[logging.Logger] = None
) -> Dict[str, float]:
    weights_logger = (log_instance or logger).getChild("GetMSPIWeights_v2.3.1")
    weights_logger.info("Determining MSPI weights (v2.3 focus)...")

    weights_config_base_path = [ids.CFG_DATA_PROCESSOR_SETTINGS_BASE_KEY, ids.CFG_WEIGHTS_KEY]
    weights_selection_logic = config_value_getter(weights_config_base_path + [ids.CFG_WEIGHTS_SELECTION_LOGIC_KEY], "time_based")
    weights_logger.debug(f"MSPI Weighting Logic: '{weights_selection_logic}'")

    raw_weights_from_config: Dict[str, Any] = {}
    session_key_for_weights = ids.CFG_WEIGHTS_SESSION_MIDDAY_KEY # Default session key from ids.py

    if weights_selection_logic == "time_based":
        if current_time_for_weights:
            time_defs_path = weights_config_base_path + [ids.CFG_WEIGHTS_TIME_BASED_DEFS_KEY]
            time_defs = config_value_getter(time_defs_path, {})
            if not isinstance(time_defs, dict): time_defs = {}
            try:
                morning_end_t = datetime.strptime(str(time_defs.get(ids.CFG_WEIGHTS_MORNING_END_KEY, "11:00:00")), "%H:%M:%S").time()
                midday_end_t = datetime.strptime(str(time_defs.get(ids.CFG_WEIGHTS_MIDDAY_END_KEY, "14:00:00")), "%H:%M:%S").time()

                if current_time_for_weights >= midday_end_t: session_key_for_weights = ids.CFG_WEIGHTS_SESSION_FINAL_KEY
                elif current_time_for_weights >= morning_end_t: session_key_for_weights = ids.CFG_WEIGHTS_SESSION_MIDDAY_KEY
                else: session_key_for_weights = ids.CFG_WEIGHTS_SESSION_MORNING_KEY
            except ValueError as e_time_fmt:
                weights_logger.error(f"Invalid time format in weight config: {e_time_fmt}. Defaulting session to '{session_key_for_weights}'.", exc_info=True)
        raw_weights_path = weights_config_base_path + [ids.CFG_WEIGHTS_TIME_BASED_KEY, session_key_for_weights]
        raw_weights_from_config = config_value_getter(raw_weights_path, {})
    else:
        fallback_path = weights_config_base_path + [ids.CFG_WEIGHTS_TIME_BASED_KEY, ids.CFG_WEIGHTS_SESSION_MIDDAY_KEY]
        raw_weights_from_config = config_value_getter(fallback_path, {})

    if not isinstance(raw_weights_from_config, dict): raw_weights_from_config = {}
    weights_logger.debug(f"MSPI Weighting: Raw weights for session '{session_key_for_weights}': {raw_weights_from_config}")

    active_metric_weights: Dict[str, float] = {}
    v2_3_metric_norm_cols = [
        ids.COL_DAG_CUSTOM_NORM, ids.COL_TDPI_NORM, ids.COL_VRI_NORM,
        ids.COL_SDAG_MULTIPLICATIVE_NORM, ids.COL_SDAG_DIRECTIONAL_NORM,
        ids.COL_SDAG_WEIGHTED_NORM, ids.COL_SDAG_VOLATILITY_FOCUSED_NORM
    ]
    config_key_to_df_col_map = { # Maps config keys (often shorter) to full ids.py constants
        "dag_custom_norm": ids.COL_DAG_CUSTOM_NORM, "tdpi_norm": ids.COL_TDPI_NORM, "vri_norm": ids.COL_VRI_NORM,
        "sdag_multiplicative_norm": ids.COL_SDAG_MULTIPLICATIVE_NORM, "sdag_directional_norm": ids.COL_SDAG_DIRECTIONAL_NORM,
        "sdag_weighted_norm": ids.COL_SDAG_WEIGHTED_NORM, "sdag_volatility_focused_norm": ids.COL_SDAG_VOLATILITY_FOCUSED_NORM,
        # v2.5 metric mappings (will only be used if their respective *_enabled_its flags are True)
        a_dag_norm_col_its: a_dag_norm_col_its if a_dag_enabled_its else None,
        d_tdpi_norm_col_its: d_tdpi_norm_col_its if d_tdpi_enabled_its else None,
        vri_2_0_norm_col_its: vri_2_0_norm_col_its if vri_2_0_enabled_its else None,
        e_sdag_composite_norm_col_its: e_sdag_composite_norm_col_its if e_sdag_enabled_its else None,
    }

    for config_key_in_json, weight_value_from_json in raw_weights_from_config.items():
        actual_df_col_name = config_key_to_df_col_map.get(config_key_in_json)
        if actual_df_col_name:
            # For v2.3, only consider weights for v2.3 base metrics.
            # Enhanced metric flags (a_dag_enabled_its etc.) will be False for v2.3.
            is_v2_3_metric = actual_df_col_name in v2_3_metric_norm_cols
            is_enabled_v2_5_metric = (
                (actual_df_col_name == a_dag_norm_col_its and a_dag_enabled_its) or
                (actual_df_col_name == d_tdpi_norm_col_its and d_tdpi_enabled_its) or
                (actual_df_col_name == vri_2_0_norm_col_its and vri_2_0_enabled_its) or
                (actual_df_col_name == e_sdag_composite_norm_col_its and e_sdag_enabled_its)
            )
            if is_v2_3_metric or is_enabled_v2_5_metric: # Include if it's a v2.3 metric OR an enabled v2.5 metric
                try:
                    weight_val_float = float(weight_value_from_json)
                    if weight_val_float != 0.0: active_metric_weights[actual_df_col_name] = weight_val_float
                except (ValueError, TypeError): weights_logger.error(f"Could not convert weight for '{config_key_in_json}' (value: {weight_value_from_json}) to float.")
    if not active_metric_weights:
        weights_logger.critical(f"{symbol_log_prefix if 'symbol_log_prefix' in locals() else ''}NO active MSPI weights determined. MSPI will be zero.")
        return {}
    total_weight = sum(active_metric_weights.values())
    if abs(total_weight) > MIN_NORMALIZATION_DENOMINATOR:
        normalized_weights = {k: v / total_weight for k, v in active_metric_weights.items()}
        weights_logger.info(f"Final normalized MSPI weights: {normalized_weights}")
        return normalized_weights
    weights_logger.warning(f"{symbol_log_prefix if 'symbol_log_prefix' in locals() else ''}Total active MSPI weight is zero. MSPI will be zero.")
    return {}


def calculate_mspi_main(
    options_df: pd.DataFrame,
    config_value_getter: Callable[[List[str], Any], Any],
    gamma_exposure_col_mspi: str, delta_exposure_col_mspi: str,
    option_iv_col_mspi: str, strike_col_mspi: str,
    option_price_col_name_in_df_mspi: Optional[str],
    opt_kind_col_mspi: str,
    underlying_symbol_col_mspi: str, expiration_date_col_mspi: str,
    direct_delta_buy_col_mspi: str, direct_delta_sell_col_mspi: str, proxy_delta_flow_col_mspi: str,
    direct_gamma_buy_col_mspi: str, direct_gamma_sell_col_mspi: str, proxy_gamma_flow_col_mspi: str,
    direct_theta_buy_col_mspi: str, direct_theta_sell_col_mspi: str, proxy_theta_flow_col_mspi: str,
    proxy_charm_flow_col_mspi: str,
    direct_vega_buy_col_mspi: str, direct_vega_sell_col_mspi: str, proxy_vega_flow_col_mspi: str,
    proxy_vanna_flow_col_mspi: str, proxy_vomma_flow_col_mspi: str,
    charmxoi_col_mspi: str, txoi_col_mspi: str, vannaxoi_col_mspi: str, vxoi_col_mspi: str, vommaxoi_col_mspi: str,
    mspi_output_col_name_cfg: str,
    original_use_skew_adjusted_cfg: bool,
    original_skew_adjusted_gamma_col_mspi: str,
    volm_col_for_weighting_mspi: str,
    adaptive_system_enabled_its: bool,
    enhanced_metrics_master_enabled_its: bool, # This flag controls if v2.5 metrics are even considered
    a_dag_enabled_its: bool, a_dag_output_col_its: str, a_dag_norm_col_its: str,
    e_sdag_enabled_its: bool, e_sdag_composite_output_col_its: str, e_sdag_composite_norm_col_its: str,
    e_sdag_use_enhanced_skew_cfg_its: bool, e_sdag_enhanced_gex_out_col_its: str,
    d_tdpi_enabled_its: bool, d_tdpi_output_col_its: str, d_tdpi_norm_col_its: str,
    vri_2_0_enabled_its: bool, vri_2_0_output_col_its: str, vri_2_0_norm_col_its: str,
    current_time_mspi: Optional[time] = None,
    current_iv_mspi: Optional[float] = None,
    avg_iv_5day_mspi: Optional[float] = None,
    iv_context_mspi: Optional[Dict[str, Any]] = None,
    underlying_price_mspi: Optional[float] = None,
    historical_ohlc_df_for_atr_mspi: Optional[pd.DataFrame] = None,
    avg_iv_long_term_mspi: Optional[float] = None,
    historical_atr_normalized_vs_avg_mspi: Optional[float] = None,
    current_symbol_mspi: Optional[str] = None,
    symbol_specific_historical_context_mspi: Optional[Dict[str, Any]] = None,
    log_instance: Optional[logging.Logger] = None
) -> pd.DataFrame:
    mspi_calc_logger = (log_instance or logger).getChild("MSPIOrchestrator_v2.3.1")
    symbol_log_prefix = f"[{current_symbol_mspi or 'UnknownSymbol'}] "
    mspi_calc_logger.info(f"{symbol_log_prefix}Starting MSPI Orchestration (v2.3.1 Focus). Input DF shape: {options_df.shape if isinstance(options_df, pd.DataFrame) else 'N/A'}")
    mspi_calc_logger.debug(f"{symbol_log_prefix}Underlying Price for context: {underlying_price_mspi}")

    if not _SUB_MODULE_IMPORTS_OK:
        mspi_calc_logger.critical(f"{symbol_log_prefix}Sub-module imports failed. Cannot calculate MSPI.")
        err_df = options_df.copy() if isinstance(options_df, pd.DataFrame) else pd.DataFrame()
        err_df[mspi_output_col_name_cfg] = 0.0; err_df["ERROR_MSPI_ORCH"] = "Sub-module import failure."
        return err_df
    if not isinstance(options_df, pd.DataFrame) or options_df.empty:
        mspi_calc_logger.error(f"{symbol_log_prefix}Input options_df empty/invalid. Cannot calculate MSPI.")
        err_df = options_df.copy() if isinstance(options_df, pd.DataFrame) else pd.DataFrame()
        err_df[mspi_output_col_name_cfg] = 0.0; return err_df

    df = options_df.copy()
    essential_cols_check = [
        strike_col_mspi, opt_kind_col_mspi, underlying_symbol_col_mspi, expiration_date_col_mspi,
        gamma_exposure_col_mspi, delta_exposure_col_mspi, option_iv_col_mspi, ids.COL_DELTA_CONTRACT
    ]
    if option_price_col_name_in_df_mspi: essential_cols_check.append(option_price_col_name_in_df_mspi)

    df, all_cols_ok = ensure_columns(df, essential_cols_check, "MSPI_EssentialInput_Orch", log_instance=mspi_calc_logger)
    if not all_cols_ok:
        mspi_calc_logger.error(f"{symbol_log_prefix}Essential columns missing/invalid. Aborting MSPI calculations.")
        df[mspi_output_col_name_cfg] = 0.0
        return df

    # Initialize v2.3 output columns
    v2_3_raw_metrics = [ids.COL_DAG_CUSTOM_RAW, ids.COL_TDPI_RAW, ids.COL_VRI_RAW,
                        ids.COL_SDAG_MULTIPLICATIVE_RAW, ids.COL_SDAG_DIRECTIONAL_RAW,
                        ids.COL_SDAG_WEIGHTED_RAW, ids.COL_SDAG_VOLATILITY_FOCUSED_RAW]
    v2_3_norm_metrics = [ids.COL_DAG_CUSTOM_NORM, ids.COL_TDPI_NORM, ids.COL_VRI_NORM,
                         ids.COL_SDAG_MULTIPLICATIVE_NORM, ids.COL_SDAG_DIRECTIONAL_NORM,
                         ids.COL_SDAG_WEIGHTED_NORM, ids.COL_SDAG_VOLATILITY_FOCUSED_NORM]
    v2_3_final_indices = [ids.COL_MSPI_SCORE, ids.COL_SAI, ids.COL_SSI, ids.COL_ARFI,
                          ids.COL_CTR, ids.COL_TDFI, ids.COL_VVR, ids.COL_VFI]
    for col_list in [v2_3_raw_metrics, v2_3_norm_metrics, v2_3_final_indices]:
        for col_id_const in col_list:
            if col_id_const not in df.columns: df[col_id_const] = 0.0

    # Initialize v2.5 output columns (they will remain 0.0 if enhanced_metrics_master_enabled_its is False)
    if enhanced_metrics_master_enabled_its: # This flag acts as a master switch for considering v2.5
        v2_5_metrics_to_init = []
        if a_dag_enabled_its: v2_5_metrics_to_init.extend([a_dag_output_col_its, a_dag_norm_col_its])
        if d_tdpi_enabled_its: v2_5_metrics_to_init.extend([d_tdpi_output_col_its, d_tdpi_norm_col_its])
        if vri_2_0_enabled_its: v2_5_metrics_to_init.extend([vri_2_0_output_col_its, vri_2_0_norm_col_its])
        if e_sdag_enabled_its: v2_5_metrics_to_init.extend([e_sdag_composite_output_col_its, e_sdag_composite_norm_col_its, config_value_getter(["enhanced_metrics", "e_sdag", "conviction_score_output_col_name"], ids.COL_SDAG_CONVICTION_SCORE)])
        for col in v2_5_metrics_to_init:
            if col and col not in df.columns: df[col] = 0.0
    df.attrs['current_mspi_weights_applied_in_calc'] = {}

    mspi_calc_logger.info(f"{symbol_log_prefix}Calculating Base v2.3 Metrics (DAG, TDPI, VRI)...")
    try:
        dag_alpha_coeffs = config_value_getter(ids.CFG_METRICS_CALC_ADAPTIVE_ADAG_BASE_ALPHA, {})
        df = calculate_custom_flow_dag(df.copy(), gamma_exposure_col_mspi, delta_exposure_col_mspi,
            direct_delta_buy_col_mspi, direct_delta_sell_col_mspi, proxy_delta_flow_col_mspi,
            direct_gamma_buy_col_mspi, direct_gamma_sell_col_mspi, proxy_gamma_flow_col_mspi,
            volm_col_for_weighting_mspi, strike_col_mspi, option_price_col_name_in_df_mspi,
            dag_alpha_coeffs, actual_underlying_price=underlying_price_mspi,
            log_instance=mspi_calc_logger.getChild("BaseDAG"))
        df[ids.COL_DAG_CUSTOM_NORM] = normalize_series(df.get(ids.COL_DAG_CUSTOM_RAW, 0.0), ids.COL_DAG_CUSTOM_NORM)
    except Exception as e_dag: mspi_calc_logger.error(f"{symbol_log_prefix}Error Base DAG: {e_dag}", exc_info=True)

    try:
        tdpi_beta_coeffs = config_value_getter(ids.CFG_METRICS_CALC_ADAPTIVE_DTDPI_BASE_BETA, {})
        tdpi_gauss_width = config_value_getter(ids.CFG_METRICS_CALC_ADAPTIVE_DTDPI_BASE_GAUSS, -0.45)
        atr_fb_cfg = config_value_getter(ids.CFG_METRICS_CALC_ATR_FALLBACK, {})
        df = calculate_tdpi(df.copy(), charmxoi_col_mspi, txoi_col_mspi,
            direct_theta_buy_col_mspi, direct_theta_sell_col_mspi, proxy_theta_flow_col_mspi, proxy_charm_flow_col_mspi,
            expiration_date_col_mspi, strike_col_mspi, option_price_col_name_in_df_mspi, underlying_symbol_col_mspi,
            tdpi_beta_coeffs, tdpi_gauss_width, atr_fb_cfg,
            actual_underlying_price=underlying_price_mspi, current_time=current_time_mspi,
            historical_ohlc_df_for_atr=historical_ohlc_df_for_atr_mspi,
            log_instance=mspi_calc_logger.getChild("BaseTDPI"))
        df[ids.COL_TDPI_NORM] = normalize_series(df.get(ids.COL_TDPI_RAW, 0.0), ids.COL_TDPI_NORM)
    except Exception as e_tdpi: mspi_calc_logger.error(f"{symbol_log_prefix}Error Base TDPI: {e_tdpi}", exc_info=True)

    try:
        vri_gamma_coeffs = config_value_getter(ids.CFG_METRICS_CALC_ADAPTIVE_VRI2_BASE_GAMMA, {})
        vri_vol_trend_fb = config_value_getter(ids.CFG_METRICS_CALC_VRI_VOL_TREND_FALLBACK, 0.9)
        df = calculate_vri(df.copy(), vannaxoi_col_mspi, vxoi_col_mspi, vommaxoi_col_mspi,
            direct_vega_buy_col_mspi, direct_vega_sell_col_mspi, proxy_vega_flow_col_mspi,
            proxy_vanna_flow_col_mspi, proxy_vomma_flow_col_mspi, expiration_date_col_mspi,
            opt_kind_col_mspi, option_iv_col_mspi, vri_gamma_coeffs, vri_vol_trend_fb, strike_col_mspi,
            current_underlying_iv=current_iv_mspi, avg_5day_underlying_iv=avg_iv_5day_mspi,
            log_instance=mspi_calc_logger.getChild("BaseVRI"))
        df[ids.COL_VRI_NORM] = normalize_series(df.get(ids.COL_VRI_RAW, 0.0), ids.COL_VRI_NORM)
    except Exception as e_vri: mspi_calc_logger.error(f"{symbol_log_prefix}Error Base VRI: {e_vri}", exc_info=True)

    mspi_calc_logger.info(f"{symbol_log_prefix}Calculating Original SDAG Metrics (v2.3)...")
    try:
        gex_source_for_sdags_str = gamma_exposure_col_mspi
        if original_use_skew_adjusted_cfg and original_skew_adjusted_gamma_col_mspi in df.columns:
            skew_gex_series = pd.to_numeric(df[original_skew_adjusted_gamma_col_mspi], errors='coerce')
            if not skew_gex_series.isnull().all(): gex_source_for_sdags_str = original_skew_adjusted_gamma_col_mspi
        gex_series_for_sdags = pd.to_numeric(df.get(gex_source_for_sdags_str, 0.0), errors='coerce').fillna(0.0)
        delta_exposure_raw_for_sdags = pd.to_numeric(df.get(delta_exposure_col_mspi, 0.0), errors='coerce').fillna(0.0)
        norm_delta_exposure_for_sdags = normalize_series(delta_exposure_raw_for_sdags, f"{delta_exposure_col_mspi}_norm_for_sdags")

        enabled_sdags_list = config_value_getter(ids.CFG_DAG_METHODOLOGIES_ENABLED_ITS, [])
        all_sdags_configs = config_value_getter(ids.CFG_DAG_METHODOLOGIES_ITS, {})

        sdag_functions_map = {
            "multiplicative": (calculate_sdag_multiplicative, ids.COL_SDAG_MULTIPLICATIVE_RAW, ids.COL_SDAG_MULTIPLICATIVE_NORM),
            "directional": (calculate_sdag_directional, ids.COL_SDAG_DIRECTIONAL_RAW, ids.COL_SDAG_DIRECTIONAL_NORM),
            "weighted": (calculate_sdag_weighted, ids.COL_SDAG_WEIGHTED_RAW, ids.COL_SDAG_WEIGHTED_NORM),
            "volatility_focused": (calculate_sdag_volatility_focused, ids.COL_SDAG_VOLATILITY_FOCUSED_RAW, ids.COL_SDAG_VOLATILITY_FOCUSED_NORM)
        }
        for sdag_type_key, (sdag_func, raw_out_col, norm_out_col) in sdag_functions_map.items():
            if sdag_type_key in enabled_sdags_list:
                method_cfg = all_sdags_configs.get(sdag_type_key, {})
                delta_wf = float(method_cfg.get("delta_weight_factor", 0.5))
                common_args_for_sdag = {
                    "df_for_context": df.copy(), "gamma_exposure": gex_series_for_sdags,
                    "delta_exposure_norm": norm_delta_exposure_for_sdags, "delta_weight_factor": delta_wf,
                    "strike_col": strike_col_mspi, "actual_underlying_price": underlying_price_mspi,
                    "log_instance": mspi_calc_logger.getChild(f"SDAG_{sdag_type_key.capitalize()}")}
                if sdag_type_key == "multiplicative":
                    common_args_for_sdag["option_iv_col"] = option_iv_col_mspi
                    common_args_for_sdag["volm_col_for_weighting"] = volm_col_for_weighting_mspi
                elif sdag_type_key == "weighted":
                    common_args_for_sdag["delta_exposure_raw"] = delta_exposure_raw_for_sdags
                    common_args_for_sdag["w1_gamma"] = float(method_cfg.get("w1_gamma",0.6))
                    common_args_for_sdag["w2_delta"] = float(method_cfg.get("w2_delta",0.4))
                    common_args_for_sdag["volm_col_for_weighting"] = volm_col_for_weighting_mspi
                    common_args_for_sdag.pop("delta_exposure_norm", None)
                elif sdag_type_key == "volatility_focused":
                    common_args_for_sdag["option_iv_col"] = option_iv_col_mspi
                    common_args_for_sdag["vomma_oi_col"] = vommaxoi_col_mspi
                df[raw_out_col] = sdag_func(**common_args_for_sdag).fillna(0.0) # type: ignore
                df[norm_out_col] = normalize_series(df.get(raw_out_col, 0.0), norm_out_col)
        mspi_calc_logger.info(f"{symbol_log_prefix}Base Original SDAGs (v2.3) calculated.")
    except Exception as e_sdag: mspi_calc_logger.error(f"{symbol_log_prefix}Error Original SDAGs: {e_sdag}", exc_info=True)

    # --- Enhanced v2.5 Metrics ---
    # For v2.3, enhanced_metrics_master_enabled_its will be False, so this block is skipped.
    if enhanced_metrics_master_enabled_its:
        mspi_calc_logger.info(f"{symbol_log_prefix}Calculating Enhanced v2.5 Metrics (A-DAG, D-TDPI, VRI 2.0, E-SDAG)...")
        if a_dag_enabled_its:
            try:
                a_dag_cfgs = config_value_getter(ids.CFG_METRICS_CALC_ADAPTIVE_ADAG_SETTINGS, {})
                df = adaptive_dag_module.calculate_adaptive_dag(df.copy(), gamma_exposure_col_mspi, delta_exposure_col_mspi, expiration_date_col_mspi, volm_col_for_weighting_mspi,
                                            direct_delta_buy_col_mspi, direct_delta_sell_col_mspi, proxy_delta_flow_col_mspi,
                                            direct_gamma_buy_col_mspi, direct_gamma_sell_col_mspi, proxy_gamma_flow_col_mspi,
                                            strike_col_mspi, option_price_col_name_in_df_mspi,
                                            option_iv_col_mspi, underlying_symbol_col_mspi, a_dag_output_col_its,
                                            current_iv_mspi, avg_iv_long_term_mspi, historical_atr_normalized_vs_avg_mspi,
                                            (symbol_specific_historical_context_mspi or {}).get("past_flow_delta"),
                                            (symbol_specific_historical_context_mspi or {}).get("past_flow_gamma"),
                                            underlying_price_mspi, historical_ohlc_df_for_atr_mspi,
                                            float(a_dag_cfgs.get("vol_regime_sensitivity", 1.0)), a_dag_cfgs.get("base_dag_alpha_coeffs", {}),
                                            float(a_dag_cfgs.get("temporal_decay_factor_flow", 0.85)), int(a_dag_cfgs.get("flow_recency_half_life_periods", 5)),
                                            float(a_dag_cfgs.get("volume_weight_factor_gex", 0.7)), config_value_getter(ids.CFG_METRICS_CALC_ADAPTIVE_ADAG_DTE_SCALING, {}), # Pass DTE scaling dict
                                            config_value_getter(ids.CFG_METRICS_CALC_ATR_FALLBACK, {}),
                                            log_instance=mspi_calc_logger.getChild("AdaptiveDAG"))
                df[a_dag_norm_col_its] = normalize_series(df.get(a_dag_output_col_its, 0.0), a_dag_norm_col_its)
            except Exception as e_adag: mspi_calc_logger.error(f"{symbol_log_prefix}Error A-DAG: {e_adag}", exc_info=True)

        if e_sdag_enabled_its:
            try:
                e_sdag_cfgs = config_value_getter(ids.CFG_METRICS_CALC_ADAPTIVE_ESDAG_SETTINGS, {})
                sgexoi_params = e_sdag_cfgs.get("sgexoi_calculation_params", {})
                enabled_orig_sdags_list_for_esdag = config_value_getter(ids.CFG_DAG_METHODOLOGIES_ENABLED_ITS, [])
                all_orig_sdag_method_configs_for_esdag = config_value_getter(ids.CFG_DAG_METHODOLOGIES_ITS, {})
                df.attrs['e_sdag_composite_norm_col_name_ITS'] = e_sdag_composite_norm_col_its # Pass target norm col name
                df = enhanced_sdag_module.calculate_enhanced_sdag(df.copy(), gamma_exposure_col_mspi, delta_exposure_col_mspi, option_iv_col_mspi, strike_col_mspi,
                                             option_price_col_name_in_df_mspi, opt_kind_col_mspi, volm_col_for_weighting_mspi, vommaxoi_col_mspi,
                                             e_sdag_use_enhanced_skew_cfg_its, float(sgexoi_params.get("skew_sensitivity_to_vri2", 0.1)),
                                             e_sdag_enhanced_gex_out_col_its, enabled_orig_sdags_list_for_esdag, all_orig_sdag_method_configs_for_esdag,
                                             e_sdag_cfgs.get("methodology_weights_initial", {}), e_sdag_cfgs.get("performance_adaptation_enabled", False),
                                             int(e_sdag_cfgs.get("min_agreement_for_conviction_bonus", 2)), e_sdag_composite_output_col_its,
                                             config_value_getter(ids.CFG_ENHANCED_METRICS_ESDAG_CONVICTION_COL, ids.COL_SDAG_CONVICTION_SCORE),
                                             actual_underlying_price=underlying_price_mspi,
                                             historical_context=symbol_specific_historical_context_mspi,
                                             log_instance=mspi_calc_logger.getChild("EnhancedSDAG"))
            except Exception as e_esdag: mspi_calc_logger.error(f"{symbol_log_prefix}Error E-SDAG: {e_esdag}", exc_info=True)

        if d_tdpi_enabled_its:
            try:
                d_tdpi_cfgs = config_value_getter(ids.CFG_METRICS_CALC_ADAPTIVE_DTDPI_SETTINGS, {})
                df = dynamic_tdpi_module.calculate_dynamic_tdpi(df.copy(), charmxoi_col_mspi, txoi_col_mspi, direct_theta_buy_col_mspi, direct_theta_sell_col_mspi,
                                            proxy_theta_flow_col_mspi, proxy_charm_flow_col_mspi, expiration_date_col_mspi, strike_col_mspi,
                                            option_price_col_name_in_df_mspi, underlying_symbol_col_mspi, d_tdpi_output_col_its,
                                            d_tdpi_cfgs.get("base_tdpi_beta_coeffs", {}),
                                            bool(d_tdpi_cfgs.get("adaptive_time_weighting_enabled", True)),
                                            config_value_getter(ids.CFG_MARKET_REGIME_TIME_DEFS, {}), # Pass time_based_definitions
                                            d_tdpi_cfgs.get("regime_time_weight_profiles", {}),
                                            bool(d_tdpi_cfgs.get("dynamic_gaussian_width_enabled", True)),
                                            float(d_tdpi_cfgs.get("base_tdpi_gaussian_width", -0.45)),
                                            float(d_tdpi_cfgs.get("gaussian_width_vol_sensitivity", 0.05)),
                                            d_tdpi_cfgs.get("gaussian_width_range", [-0.7, -0.2]),
                                            int(d_tdpi_cfgs.get("expiration_clustering_dte_lookaround", 2)),
                                            float(d_tdpi_cfgs.get("expiration_clustering_sensitivity", 1.1)),
                                            float(d_tdpi_cfgs.get("charm_acceleration_sensitivity", 1.05)),
                                            int(d_tdpi_cfgs.get("charm_acceleration_lookback_periods", 3)),
                                            config_value_getter(ids.CFG_METRICS_CALC_ATR_FALLBACK, {}),
                                            current_time_mspi, symbol_specific_historical_context_mspi, historical_ohlc_df_for_atr_mspi,
                                            underlying_price_mspi,
                                            log_instance=mspi_calc_logger.getChild("DynamicTDPI"))
                df[d_tdpi_norm_col_its] = normalize_series(df.get(d_tdpi_output_col_its, 0.0), d_tdpi_norm_col_its)
            except Exception as e_dtdpi: mspi_calc_logger.error(f"{symbol_log_prefix}Error D-TDPI: {e_dtdpi}", exc_info=True)

        if vri_2_0_enabled_its:
            try:
                vri_2_0_cfgs = config_value_getter(ids.CFG_METRICS_CALC_ADAPTIVE_VRI2_SETTINGS, {})
                df = vri_2_0_module.calculate_vri_2_0(df.copy(), vannaxoi_col_mspi, vxoi_col_mspi, vommaxoi_col_mspi,
                                       direct_vega_buy_col_mspi, direct_vega_sell_col_mspi, proxy_vega_flow_col_mspi,
                                       proxy_vanna_flow_col_mspi, proxy_vomma_flow_col_mspi, expiration_date_col_mspi,
                                       opt_kind_col_mspi, option_iv_col_mspi, strike_col_mspi,
                                       option_price_col_name_in_df_mspi, vri_2_0_output_col_its,
                                       vri_2_0_cfgs.get("base_vri_gamma_coeffs", {}),
                                       vri_2_0_cfgs.get("term_structure_integration_params",{}),
                                       vri_2_0_cfgs.get("volatility_surface_dynamics_params",{}),
                                       vri_2_0_cfgs.get("vomma_enhancement_params",{}),
                                       vri_2_0_cfgs.get("adaptive_iv_thresholds_enabled", False),
                                       vri_2_0_cfgs.get("iv_context_percentile_key_for_adaptive_thresh", ids.CV_UND_PARAM_IV_PERCENTILE_30D), # Use constant
                                       float(vri_2_0_cfgs.get("adaptive_iv_low_percentile_base", 30.0)),
                                       float(vri_2_0_cfgs.get("adaptive_iv_high_percentile_base", 70.0)),
                                       float(vri_2_0_cfgs.get("adaptive_iv_shift_factor", 0.1)),
                                       float(vri_2_0_cfgs.get("vol_context_weight_low_iv", 0.9)),
                                       float(vri_2_0_cfgs.get("vol_context_weight_high_iv", 1.1)),
                                       current_iv_mspi, avg_iv_5day_mspi, # Pass current and 5day avg IV
                                       iv_context_mspi, # Pass the full iv_context dict
                                       symbol_specific_historical_context_mspi,
                                       log_instance=mspi_calc_logger.getChild("VRI_2_0"))
                df[vri_2_0_norm_col_its] = normalize_series(df.get(vri_2_0_output_col_its, 0.0), vri_2_0_norm_col_its)
            except Exception as e_vri2: mspi_calc_logger.error(f"{symbol_log_prefix}Error VRI 2.0: {e_vri2}", exc_info=True)
    else:
        mspi_calc_logger.info(f"{symbol_log_prefix}Enhanced Metrics Master Toggle is OFF. Skipping all v2.5 metric calculations.")


    # --- Final MSPI Score Calculation (v2.3 focus ensures only v2.3 components are weighted if v2.5 flags are False) ---
    mspi_calc_logger.info(f"{symbol_log_prefix}Calculating final MSPI score ('{mspi_output_col_name_cfg}')...")
    current_mspi_weights = get_mspi_weights(
        config_value_getter,
        a_dag_enabled_its, a_dag_norm_col_its, # These will be False for v2.3
        d_tdpi_enabled_its, d_tdpi_norm_col_its, # False for v2.3
        vri_2_0_enabled_its, vri_2_0_norm_col_its, # False for v2.3
        e_sdag_enabled_its, e_sdag_composite_norm_col_its, # False for v2.3
        current_time_mspi, iv_context_mspi,
        adaptive_system_enabled_its, # False for v2.3
        log_instance=mspi_calc_logger.getChild("MSPIWeightingFinal_v2.3.1")
    )
    df[mspi_output_col_name_cfg] = 0.0
    if not current_mspi_weights:
        mspi_calc_logger.warning(f"{symbol_log_prefix}No active MSPI weights determined. Final MSPI will be 0.")
    else:
        for component_norm_col, weight in current_mspi_weights.items():
            if component_norm_col in df.columns:
                try: df[mspi_output_col_name_cfg] += pd.to_numeric(df[component_norm_col], errors='coerce').fillna(0.0) * weight
                except Exception as e_w_apply: mspi_calc_logger.error(f"Error applying weight for {component_norm_col}: {e_w_apply}", exc_info=True)
            else: mspi_calc_logger.warning(f"Weighted component '{component_norm_col}' not in DataFrame for MSPI calculation.")

    df[mspi_output_col_name_cfg] = normalize_series(df.get(mspi_output_col_name_cfg, 0.0), "final_mspi_score_normalized_v2.3.1")
    df.attrs['current_mspi_weights_applied_in_calc'] = current_mspi_weights
    mspi_calc_logger.info(f"{symbol_log_prefix}Final MSPI ('{mspi_output_col_name_cfg}') calculated. Mean: {df[mspi_output_col_name_cfg].mean():.4f if not df.empty else 'N/A'}")

    # --- Calculate SAI, SSI, ARFI (v2.3) ---
    mspi_calc_logger.info(f"{symbol_log_prefix}Calculating SAI, SSI, ARFI (v2.3)...")
    try:
        v2_3_norm_cols_for_sai_ssi = [ids.COL_DAG_CUSTOM_NORM, ids.COL_TDPI_NORM, ids.COL_VRI_NORM,
                                      ids.COL_SDAG_MULTIPLICATIVE_NORM, ids.COL_SDAG_DIRECTIONAL_NORM,
                                      ids.COL_SDAG_WEIGHTED_NORM, ids.COL_SDAG_VOLATILITY_FOCUSED_NORM]
        weighted_component_values = [df[cn].fillna(0.0) * current_mspi_weights.get(cn, 0.0) for cn in v2_3_norm_cols_for_sai_ssi if cn in df.columns and cn in current_mspi_weights]
        if len(weighted_component_values) >= 2:
            pairwise_sum = pd.Series(0.0, index=df.index); num_pairs = 0
            for i in range(len(weighted_component_values)):
                for j in range(i + 1, len(weighted_component_values)):
                    pairwise_sum += np.tanh(weighted_component_values[i] * weighted_component_values[j] * 10).fillna(0.0); num_pairs += 1
            df[ids.COL_SAI] = (pairwise_sum / num_pairs if num_pairs > 0 else 0.0).fillna(0.0)
            std_dev = pd.concat(weighted_component_values, axis=1).std(axis=1, skipna=True).fillna(0.0)
            df[ids.COL_SSI] = (1 - np.minimum(1, std_dev / 0.5)).fillna(0.5)
        else: df[ids.COL_SAI], df[ids.COL_SSI] = 0.0, 0.5; mspi_calc_logger.warning(f"{symbol_log_prefix}Not enough weighted components for SAI/SSI.")
    except Exception as e_sai_ssi: mspi_calc_logger.error(f"{symbol_log_prefix}Error SAI/SSI: {e_sai_ssi}", exc_info=True); df[ids.COL_SAI], df[ids.COL_SSI] = 0.0, 0.5

    try:
        dxv = pd.to_numeric(df.get(proxy_delta_flow_col_mspi,0.0),errors='coerce').fillna(0.0)
        dxoi_val = pd.to_numeric(df.get(delta_exposure_col_mspi,0.0),errors='coerce').fillna(0.0)
        cxv = pd.to_numeric(df.get(proxy_charm_flow_col_mspi,0.0),errors='coerce').fillna(0.0)
        cxoi_val = pd.to_numeric(df.get(charmxoi_col_mspi,0.0),errors='coerce').fillna(0.0)
        vxv = pd.to_numeric(df.get(proxy_vanna_flow_col_mspi,0.0),errors='coerce').fillna(0.0)
        vxoi_val = pd.to_numeric(df.get(vannaxoi_col_mspi,0.0),errors='coerce').fillna(0.0)
        arfi_comp1 = (dxv.abs()/(dxoi_val.abs() + MIN_NORMALIZATION_DENOMINATOR)).fillna(0.0)
        arfi_comp2 = (cxv.abs()/(cxoi_val.abs() + MIN_NORMALIZATION_DENOMINATOR)).fillna(0.0)
        arfi_comp3 = (vxv.abs()/(vxoi_val.abs() + MIN_NORMALIZATION_DENOMINATOR)).fillna(0.0)
        df[ids.COL_ARFI] = (arfi_comp1 + arfi_comp2 + arfi_comp3 ) / 3.0
        df[ids.COL_ARFI] = normalize_series(df[ids.COL_ARFI], ids.COL_ARFI)
    except Exception as e_arfi: mspi_calc_logger.error(f"{symbol_log_prefix}Error ARFI: {e_arfi}", exc_info=True); df[ids.COL_ARFI] = 0.0

    mspi_calc_logger.info(f"{symbol_log_prefix}MSPI Orchestration (v2.3.1 Focus) complete. Final DF shape: {df.shape}")
    return df

