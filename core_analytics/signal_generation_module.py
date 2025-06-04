# core_analytics/signal_generation_module.py
"""
Functions for generating various trading signals based on processed market metrics
for the EOTS v2.3 system. This module is designed to be called by the
IntegratedTradingSystem.

Version: EOTS_SignalGen_v2.3.0_Canon_IDS_Unabridged
"""
import pandas as pd
import numpy as np
import logging
import sys # For fallback ids import check
from typing import Union, Optional, List, Dict, Any, Callable
from datetime import datetime

# --- Project-Specific Imports ---
try:
    from utils import ids
    from .system_utilities import ensure_columns, map_score_to_stars # map_score_to_stars is crucial
    IMPORTS_SUCCESSFUL = True
    logger_init = logging.getLogger(__name__)
    logger_init.info("Signal Generation Module (v2.3.0 Canon): Core utilities and ids imported successfully.")
except ImportError as e_signal_imp:
    IMPORTS_SUCCESSFUL = False
    print(f"CRITICAL IMPORT ERROR in signal_generation_module.py: {e_signal_imp}. Signal generation will fail or use dummies.")
    class ids: # type: ignore
        COL_STRIKE = "strike_price"; COL_MSPI_SCORE = "mspi"; COL_SAI = "sai"; COL_SSI = "ssi"
        COL_ARFI = "arfi"; COL_TDPI_RAW = "tdpi"; COL_VRI_RAW = "vri"; COL_VFI = "vfi"
        COL_CTR = "ctr"; COL_TDFI = "tdfi"
        # SDAG raw columns (assuming these are the direct outputs from sdag_module)
        COL_SDAG_MULTIPLICATIVE_RAW = "sdag_multiplicative"
        COL_SDAG_DIRECTIONAL_RAW = "sdag_directional"
        COL_SDAG_WEIGHTED_RAW = "sdag_weighted"
        COL_SDAG_VOLATILITY_FOCUSED_RAW = "sdag_volatility_focused"

    def ensure_columns(df: pd.DataFrame, req_cols: List[str], name: str, log_instance: Optional[logging.Logger]=None) -> Tuple[pd.DataFrame, bool]: # type: ignore
        missing = [col for col in req_cols if col not in df.columns]; return df, not missing
    def map_score_to_stars(score: Optional[Union[float, int]], conviction_map: Dict[str, float], log_instance: Optional[logging.Logger]=None) -> int: return 0 # type: ignore

# Module-level logger
logger = logging.getLogger(__name__)
if not IMPORTS_SUCCESSFUL:
    logger.critical("Signal Generation Module running with DUMMY imports due to failure. Functionality will be severely limited.")

MIN_NORMALIZATION_DENOMINATOR_SIGNAL = 1e-9


def _create_signal_event(
    signal_type: str,
    strike_price: float,
    direction: str, # "bullish" or "bearish"
    base_conviction_score: float, # Raw score before star conversion
    mspi_value_at_signal: Optional[float],
    sai_value_at_signal: Optional[float],
    # Add other relevant metric values at the time of signal
    rationale: str,
    log_instance: logging.Logger,
    additional_details: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Helper to create a standardized signal event dictionary."""
    event = {
        "type": signal_type,
        "strike_price_signal_level": round(strike_price, 2), # Using a consistent key
        "direction_label": direction.capitalize(),
        "base_conviction_score_signal_level": round(base_conviction_score, 3),
        "mspi_value_at_signal": round(mspi_value_at_signal, 3) if pd.notna(mspi_value_at_signal) else None,
        "sai_value_at_signal": round(sai_value_at_signal, 3) if pd.notna(sai_value_at_signal) else None,
        "rationale": rationale,
        "timestamp_generated": datetime.now().isoformat()
    }
    if additional_details:
        event.update(additional_details)
    log_instance.debug(f"Created signal event: {event}")
    return event

def _generate_directional_signal(
    df_agg: pd.DataFrame,
    mspi_col: str, sai_col: str, strike_col: str,
    mspi_threshold_bullish: float, mspi_threshold_bearish: float,
    sai_confirmation_threshold: float,
    log_instance: logging.Logger
) -> List[Dict[str, Any]]:
    signals = []
    if not all(col in df_agg.columns for col in [mspi_col, sai_col, strike_col]):
        log_instance.warning(f"Directional Signal: Missing one or more required columns: {mspi_col}, {sai_col}, {strike_col}.")
        return signals

    bullish_candidates = df_agg[(pd.to_numeric(df_agg[mspi_col], errors='coerce') >= mspi_threshold_bullish) &
                                (pd.to_numeric(df_agg[sai_col], errors='coerce') >= sai_confirmation_threshold)]
    for _, row in bullish_candidates.iterrows():
        signals.append(_create_signal_event(
            "Directional_MSPI_SAI", float(row[strike_col]), "bullish",
            float(row[mspi_col]), float(row[mspi_col]), float(row[sai_col]),
            f"MSPI ({row[mspi_col]:.2f} >= {mspi_threshold_bullish:.2f}) and SAI ({row[sai_col]:.2f} >= {sai_confirmation_threshold:.2f}) indicate bullish pressure.",
            log_instance
        ))

    bearish_candidates = df_agg[(pd.to_numeric(df_agg[mspi_col], errors='coerce') <= mspi_threshold_bearish) &
                                (pd.to_numeric(df_agg[sai_col], errors='coerce') >= sai_confirmation_threshold)] # High SAI still indicates alignment
    for _, row in bearish_candidates.iterrows():
        signals.append(_create_signal_event(
            "Directional_MSPI_SAI", float(row[strike_col]), "bearish",
            abs(float(row[mspi_col])), float(row[mspi_col]), float(row[sai_col]), # Use abs for score consistency
            f"MSPI ({row[mspi_col]:.2f} <= {mspi_threshold_bearish:.2f}) and SAI ({row[sai_col]:.2f} >= {sai_confirmation_threshold:.2f}) indicate bearish pressure.",
            log_instance
        ))
    return signals

def _generate_sdag_conviction_signal(
    df_agg: pd.DataFrame,
    enabled_sdag_methods: List[str], # e.g., ["multiplicative", "directional"]
    base_sdag_cols_map: Dict[str, str], # Maps method key to its raw column name, e.g., {"multiplicative": ids.COL_SDAG_MULTIPLICATIVE_RAW}
    min_agreement_count: int,
    sdag_strength_threshold: float, # Threshold for individual SDAG magnitude
    strike_col: str, mspi_col: str, sai_col: str, # For context
    log_instance: logging.Logger
) -> List[Dict[str, Any]]:
    signals = []
    if not enabled_sdag_methods or not base_sdag_cols_map:
        log_instance.debug("SDAG Conviction: No SDAG methods enabled or map is empty.")
        return signals
    
    active_sdag_cols = [base_sdag_cols_map[method] for method in enabled_sdag_methods if method in base_sdag_cols_map and base_sdag_cols_map[method] in df_agg.columns]
    if len(active_sdag_cols) < min_agreement_count: # Need at least min_agreement_count methods to agree
        log_instance.debug(f"SDAG Conviction: Not enough active SDAG columns ({len(active_sdag_cols)}) to meet min agreement ({min_agreement_count}).")
        return signals

    # Create a sub-DataFrame with only the active, numeric SDAG columns
    try:
        sdag_values_df = df_agg[active_sdag_cols].apply(pd.to_numeric, errors='coerce').fillna(0.0)
    except KeyError as e:
        log_instance.error(f"SDAG Conviction: KeyError accessing SDAG columns: {e}. Active cols: {active_sdag_cols}, DF cols: {df_agg.columns.tolist()}")
        return signals


    # Determine bullish/bearish agreement
    positive_sdags = (sdag_values_df > sdag_strength_threshold).sum(axis=1)
    negative_sdags = (sdag_values_df < -sdag_strength_threshold).sum(axis=1)

    bullish_conviction_mask = (positive_sdags >= min_agreement_count)
    bearish_conviction_mask = (negative_sdags >= min_agreement_count)

    for idx, row in df_agg[bullish_conviction_mask].iterrows():
        avg_strength = sdag_values_df.loc[idx, sdag_values_df.loc[idx] > sdag_strength_threshold].mean()
        signals.append(_create_signal_event(
            "SDAG_Conviction_Bullish", float(row[strike_col]), "bullish",
            avg_strength, float(row.get(mspi_col,0.0)), float(row.get(sai_col,0.0)),
            f"{positive_sdags.loc[idx]} SDAGs bullishly aligned (avg strength: {avg_strength:.2f}).",
            log_instance, additional_details={"agreeing_methods": positive_sdags.loc[idx]}
        ))

    for idx, row in df_agg[bearish_conviction_mask].iterrows():
        avg_strength = abs(sdag_values_df.loc[idx, sdag_values_df.loc[idx] < -sdag_strength_threshold].mean())
        signals.append(_create_signal_event(
            "SDAG_Conviction_Bearish", float(row[strike_col]), "bearish",
            avg_strength, float(row.get(mspi_col,0.0)), float(row.get(sai_col,0.0)),
            f"{negative_sdags.loc[idx]} SDAGs bearishly aligned (avg strength: {avg_strength:.2f}).",
            log_instance, additional_details={"agreeing_methods": negative_sdags.loc[idx]}
        ))
    return signals

def _generate_volatility_expansion_signal(
    df_agg: pd.DataFrame, vri_col: str, vfi_col: str, strike_col: str,
    vri_threshold_expansion: float, vfi_threshold_expansion: float,
    log_instance: logging.Logger
) -> List[Dict[str, Any]]:
    signals = []
    if not all(col in df_agg.columns for col in [vri_col, vfi_col, strike_col]):
        log_instance.warning(f"Volatility Expansion: Missing one or more required columns: {vri_col}, {vfi_col}, {strike_col}.")
        return signals
    
    expansion_candidates = df_agg[
        (pd.to_numeric(df_agg[vri_col], errors='coerce') >= vri_threshold_expansion) &
        (pd.to_numeric(df_agg[vfi_col], errors='coerce') >= vfi_threshold_expansion)
    ]
    for _, row in expansion_candidates.iterrows():
        conviction = (float(row[vri_col]) + float(row[vfi_col])) / 2.0 # Simple average for conviction
        signals.append(_create_signal_event(
            "Volatility_Expansion", float(row[strike_col]), "neutral", # Volatility signals are often neutral directionally
            conviction, float(row.get(ids.COL_MSPI_SCORE,0.0)), float(row.get(ids.COL_SAI,0.0)), # Add MSPI/SAI context
            f"VRI ({row[vri_col]:.2f} >= {vri_threshold_expansion:.2f}) & VFI ({row[vfi_col]:.2f} >= {vfi_threshold_expansion:.2f}) suggest vol expansion.",
            log_instance, additional_details={"vri": row[vri_col], "vfi": row[vfi_col]}
        ))
    return signals

def _generate_volatility_contraction_signal(
    df_agg: pd.DataFrame, vri_col: str, vfi_col: str, ssi_col: str, strike_col: str,
    vri_threshold_contraction: float, vfi_threshold_contraction: float, ssi_threshold_contraction: float,
    log_instance: logging.Logger
) -> List[Dict[str, Any]]:
    signals = []
    if not all(col in df_agg.columns for col in [vri_col, vfi_col, ssi_col, strike_col]):
        log_instance.warning(f"Volatility Contraction: Missing required columns: {vri_col}, {vfi_col}, {ssi_col}, {strike_col}.")
        return signals

    contraction_candidates = df_agg[
        (pd.to_numeric(df_agg[vri_col], errors='coerce') <= vri_threshold_contraction) &
        (pd.to_numeric(df_agg[vfi_col], errors='coerce') <= vfi_threshold_contraction) &
        (pd.to_numeric(df_agg[ssi_col], errors='coerce') >= ssi_threshold_contraction) # High SSI indicates stability for contraction
    ]
    for _, row in contraction_candidates.iterrows():
        # Conviction could be inverse of VRI/VFI plus SSI
        conviction = ( (1-abs(float(row[vri_col]))) + (1-abs(float(row[vfi_col]))) + float(row[ssi_col]) ) / 3.0
        signals.append(_create_signal_event(
            "Volatility_Contraction", float(row[strike_col]), "neutral",
            conviction, float(row.get(ids.COL_MSPI_SCORE,0.0)), float(row.get(ids.COL_SAI,0.0)),
            f"VRI ({row[vri_col]:.2f} <= {vri_threshold_contraction:.2f}), VFI ({row[vfi_col]:.2f} <= {vfi_threshold_contraction:.2f}), & SSI ({row[ssi_col]:.2f} >= {ssi_threshold_contraction:.2f}) suggest vol contraction.",
            log_instance, additional_details={"vri": row[vri_col], "vfi": row[vfi_col], "ssi": row[ssi_col]}
        ))
    return signals

def _generate_time_decay_pin_risk_signal(
    df_agg: pd.DataFrame, tdpi_col: str, strike_col: str, current_price: float,
    tdpi_pin_risk_threshold: float, atr_for_pin_proximity: float,
    log_instance: logging.Logger
) -> List[Dict[str, Any]]:
    signals = []
    if tdpi_col not in df_agg.columns or strike_col not in df_agg.columns:
        log_instance.warning(f"Time Decay Pin Risk: Missing required columns: {tdpi_col}, {strike_col}.")
        return signals
    if not pd.notna(current_price) or not (pd.notna(atr_for_pin_proximity) and atr_for_pin_proximity > MIN_NORMALIZATION_DENOMINATOR_SIGNAL):
        log_instance.warning(f"Time Decay Pin Risk: Invalid current_price ({current_price}) or ATR ({atr_for_pin_proximity}).")
        return signals

    # Identify strikes with high TDPI that are close to current price
    pin_candidates = df_agg[
        (pd.to_numeric(df_agg[tdpi_col], errors='coerce').abs() >= tdpi_pin_risk_threshold) &
        (abs(pd.to_numeric(df_agg[strike_col], errors='coerce') - current_price) <= (1.0 * atr_for_pin_proximity)) # e.g., within 1 ATR
    ]
    for _, row in pin_candidates.iterrows():
        conviction = abs(float(row[tdpi_col])) # Use TDPI magnitude as conviction
        signals.append(_create_signal_event(
            "TimeDecay_PinRisk", float(row[strike_col]), "neutral", # Pin risk is about price gravitating to strike
            conviction, float(row.get(ids.COL_MSPI_SCORE,0.0)), float(row.get(ids.COL_SAI,0.0)),
            f"High TDPI ({row[tdpi_col]:.2f}) near current price suggests pin risk at strike {row[strike_col]:.2f}.",
            log_instance, additional_details={"tdpi": row[tdpi_col]}
        ))
    return signals

def _generate_time_decay_charm_cascade_signal(
    df_agg: pd.DataFrame, ctr_col: str, tdfi_col: str, strike_col: str,
    ctr_cascade_threshold: float, tdfi_cascade_threshold: float,
    log_instance: logging.Logger
) -> List[Dict[str, Any]]:
    signals = []
    if not all(col in df_agg.columns for col in [ctr_col, tdfi_col, strike_col]):
        log_instance.warning(f"Time Decay Charm Cascade: Missing required columns: {ctr_col}, {tdfi_col}, {strike_col}.")
        return signals

    cascade_candidates = df_agg[
        (pd.to_numeric(df_agg[ctr_col], errors='coerce') >= ctr_cascade_threshold) &
        (pd.to_numeric(df_agg[tdfi_col], errors='coerce') >= tdfi_cascade_threshold)
    ]
    for _, row in cascade_candidates.iterrows():
        conviction = (float(row[ctr_col]) + float(row[tdfi_col])) / 2.0
        # Charm cascade can be directional depending on net charm/theta, but simplified here
        direction = "neutral" # Or could infer from sign of TDFI/CTR if they were signed
        signals.append(_create_signal_event(
            "TimeDecay_CharmCascade", float(row[strike_col]), direction,
            conviction, float(row.get(ids.COL_MSPI_SCORE,0.0)), float(row.get(ids.COL_SAI,0.0)),
            f"High CTR ({row[ctr_col]:.2f}) & TDFI ({row[tdfi_col]:.2f}) suggest Charm Cascade potential around strike {row[strike_col]:.2f}.",
            log_instance, additional_details={"ctr": row[ctr_col], "tdfi": row[tdfi_col]}
        ))
    return signals

def _generate_complex_structure_change_signal(
    df_agg: pd.DataFrame, ssi_col: str, strike_col: str, # Use strike_col for context, though SSI is market-wide
    ssi_structure_change_threshold: float, # Low SSI indicates instability
    log_instance: logging.Logger
) -> List[Dict[str, Any]]:
    signals = []
    if ssi_col not in df_agg.columns or strike_col not in df_agg.columns or df_agg.empty:
        log_instance.warning(f"Complex Structure Change: Missing '{ssi_col}' or '{strike_col}', or DF empty.")
        return signals

    # SSI is typically a single value for the market, or an average if per-strike
    # For this, we'll assume it's present per strike or take the first value if it's market-wide
    ssi_series = pd.to_numeric(df_agg[ssi_col], errors='coerce')
    if ssi_series.isnull().all(): log_instance.warning("SSI column has no valid numeric data."); return signals
    
    # If SSI is market-wide, check the first value. Otherwise, check each strike.
    # For simplicity, let's check if *any* strike shows low SSI, or if an average SSI is low.
    avg_ssi = ssi_series.mean()
    if pd.notna(avg_ssi) and avg_ssi <= ssi_structure_change_threshold:
        # Signal is market-wide, but associate with ATM strike for convention
        atm_strike = df_agg.iloc[(df_agg[strike_col] - df_agg[ids.COL_PRICE_OPTION_CONTRACT].iloc[0]).abs().argsort()[:1]][strike_col].values[0] if ids.COL_PRICE_OPTION_CONTRACT in df_agg.columns and not df_agg.empty else df_agg[strike_col].iloc[0]

        conviction = 1.0 - avg_ssi # Higher conviction for lower SSI
        signals.append(_create_signal_event(
            "Complex_Structure_Change", float(atm_strike), "neutral",
            conviction, float(df_agg.get(ids.COL_MSPI_SCORE, pd.Series(0.0)).mean()), float(df_agg.get(ids.COL_SAI, pd.Series(0.0)).mean()),
            f"Low average SSI ({avg_ssi:.2f} <= {ssi_structure_change_threshold:.2f}) indicates potential market structure change.",
            log_instance, additional_details={"avg_ssi": avg_ssi}
        ))
    return signals

def _generate_complex_flow_divergence_signal(
    df_agg: pd.DataFrame, arfi_col: str, strike_col: str, # Use strike_col for context
    arfi_divergence_threshold: float, # High ARFI indicates divergence
    log_instance: logging.Logger
) -> List[Dict[str, Any]]:
    signals = []
    if arfi_col not in df_agg.columns or strike_col not in df_agg.columns or df_agg.empty:
        log_instance.warning(f"Complex Flow Divergence: Missing '{arfi_col}' or '{strike_col}', or DF empty.")
        return signals

    # ARFI might be market-wide or per-strike. Assume per-strike for now.
    divergence_candidates = df_agg[pd.to_numeric(df_agg[arfi_col], errors='coerce').abs() >= arfi_divergence_threshold]
    for _, row in divergence_candidates.iterrows():
        conviction = abs(float(row[arfi_col]))
        # Direction of divergence might be inferred from MSPI or price action context (not done here)
        signals.append(_create_signal_event(
            "Complex_Flow_Divergence", float(row[strike_col]), "neutral",
            conviction, float(row.get(ids.COL_MSPI_SCORE,0.0)), float(row.get(ids.COL_SAI,0.0)),
            f"Significant ARFI ({row[arfi_col]:.2f}) at strike {row[strike_col]:.2f} indicates flow/price divergence.",
            log_instance, additional_details={"arfi": row[arfi_col]}
        ))
    return signals

def generate_trading_signals(
    current_aggregated_df: pd.DataFrame, # Strike-aggregated DataFrame with all metrics
    signal_activation_config: Dict[str, bool], # From config: system_settings.signal_activation_v2_3
    config_value_getter: Callable[[List[str], Any], Any], # To fetch thresholds
    map_score_to_stars_func: Callable[[Optional[Union[float, int]], Dict[str, float], Optional[logging.Logger]], int], # Utility
    # Parameters for individual signal functions (column names)
    enabled_sdag_methods: List[str], # From config
    min_sdag_agreement: int,         # From config
    strike_col_name: str,            # e.g., ids.COL_STRIKE
    mspi_col_name: str,              # e.g., ids.COL_MSPI_SCORE
    sai_col_name: str,               # e.g., ids.COL_SAI
    ssi_col_name: str,               # e.g., ids.COL_SSI
    arfi_col_name: str,              # e.g., ids.COL_ARFI
    tdpi_col_name: str,              # e.g., ids.COL_TDPI_RAW
    vri_col_name: str,               # e.g., ids.COL_VRI_RAW
    vfi_col_name: str,               # e.g., ids.COL_VFI
    ctr_col_name: str,               # e.g., ids.COL_CTR
    tdfi_col_name: str,              # e.g., ids.COL_TDFI
    base_sdag_cols_map_param: Dict[str,str], # Maps sdag method key to its raw output column name
    # Contextual
    current_price_for_signals: Optional[float],
    current_atr_for_signals: Optional[float],
    log_instance: Optional[logging.Logger] = None
) -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
    signal_gen_logger = log_instance.getChild("GenerateTradingSignals_v2.3.1") if log_instance else logger.getChild("GenerateTradingSignals_v2.3.1")
    signal_gen_logger.info("Generating v2.3 Trading Signals...")
    output_signals: Dict[str, Dict[str, List[Dict[str, Any]]]] = {
        "directional": {"bullish": [], "bearish": []},
        "sdag_conviction": {"bullish": [], "bearish": []},
        "volatility": {"expansion": [], "contraction": []}, # Note: "expansion"/"contraction" not "bullish"/"bearish"
        "time_decay": {"pin_risk": [], "charm_cascade": []},
        "complex": {"structure_change": [], "flow_divergence": []}
    }

    if not isinstance(current_aggregated_df, pd.DataFrame) or current_aggregated_df.empty:
        signal_gen_logger.warning("Aggregated DataFrame is empty. No signals can be generated.")
        return output_signals
    if not (pd.notna(current_price_for_signals) and pd.notna(current_atr_for_signals)):
        signal_gen_logger.warning(f"Current price ({current_price_for_signals}) or ATR ({current_atr_for_signals}) is invalid. Some signals may not generate.")
        # Allow signals that don't strictly need price/ATR to attempt generation

    # Fetch thresholds from config using config_value_getter
    # Example: thresholds_cfg = config_value_getter(["strategy_settings", "thresholds"], {})
    # For brevity, direct use of config_value_getter in calls below.

    if signal_activation_config.get("directional", False):
        output_signals["directional"]["bullish"].extend(_generate_directional_signal(
            current_aggregated_df, mspi_col_name, sai_col_name, strike_col_name,
            float(config_value_getter(["strategy_settings","thresholds","mspi_bullish_entry_directional"], 0.3)),
            float(config_value_getter(["strategy_settings","thresholds","mspi_bearish_entry_directional"], -0.3)),
            float(config_value_getter(["strategy_settings","thresholds","sai_high_conviction"], 0.6)),
            signal_gen_logger))
        # Bearish signals are captured by the same call due to mspi_threshold_bearish

    if signal_activation_config.get("sdag_conviction", False):
        output_signals["sdag_conviction"]["bullish"].extend(_generate_sdag_conviction_signal(
            current_aggregated_df, enabled_sdag_methods, base_sdag_cols_map_param, min_sdag_agreement,
            float(config_value_getter(["strategy_settings","thresholds","sdag_strength_individual"], 0.5)),
            strike_col_name, mspi_col_name, sai_col_name, signal_gen_logger))
        # Bearish signals are captured by the same call

    if signal_activation_config.get("volatility_expansion", False):
        output_signals["volatility"]["expansion"].extend(_generate_volatility_expansion_signal(
            current_aggregated_df, vri_col_name, vfi_col_name, strike_col_name,
            float(config_value_getter(["strategy_settings","thresholds","vri_vol_expansion"], 0.7)),
            float(config_value_getter(["strategy_settings","thresholds","vfi_vol_expansion"], 0.7)),
            signal_gen_logger))

    if signal_activation_config.get("volatility_contraction", False):
        output_signals["volatility"]["contraction"].extend(_generate_volatility_contraction_signal(
            current_aggregated_df, vri_col_name, vfi_col_name, ssi_col_name, strike_col_name,
            float(config_value_getter(["strategy_settings","thresholds","vri_vol_contraction"], -0.5)),
            float(config_value_getter(["strategy_settings","thresholds","vfi_vol_contraction"], -0.5)),
            float(config_value_getter(["strategy_settings","thresholds","ssi_vol_contraction"], 0.6)),
            signal_gen_logger))

    if signal_activation_config.get("time_decay_pin_risk", False) and pd.notna(current_price_for_signals) and pd.notna(current_atr_for_signals):
        output_signals["time_decay"]["pin_risk"].extend(_generate_time_decay_pin_risk_signal(
            current_aggregated_df, tdpi_col_name, strike_col_name, current_price_for_signals,
            float(config_value_getter(["strategy_settings","thresholds","tdpi_pin_risk"], 50000.0)), # Example, may need adjustment
            current_atr_for_signals, signal_gen_logger))

    if signal_activation_config.get("time_decay_charm_cascade", False):
        output_signals["time_decay"]["charm_cascade"].extend(_generate_time_decay_charm_cascade_signal(
            current_aggregated_df, ctr_col_name, tdfi_col_name, strike_col_name,
            float(config_value_getter(["strategy_settings","thresholds","ctr_charm_cascade"], 1.2)),
            float(config_value_getter(["strategy_settings","thresholds","tdfi_charm_cascade"], 1.2)),
            signal_gen_logger))

    if signal_activation_config.get("complex_structure_change", False):
        output_signals["complex"]["structure_change"].extend(_generate_complex_structure_change_signal(
            current_aggregated_df, ssi_col_name, strike_col_name,
            float(config_value_getter(["strategy_settings","thresholds","ssi_structure_change"], 0.3)), # Low SSI
            signal_gen_logger))

    if signal_activation_config.get("complex_flow_divergence", False):
        output_signals["complex"]["flow_divergence"].extend(_generate_complex_flow_divergence_signal(
            current_aggregated_df, arfi_col_name, strike_col_name,
            float(config_value_getter(["strategy_settings","thresholds","arfi_flow_divergence"], 1.5)), # High ARFI
            signal_gen_logger))

    signal_gen_logger.info("Trading signal generation complete for v2.3 signals.")
    return output_signals

