# core_analytics/fallback_recommendation_module.py
"""
Functions for generating fallback/original strategy recommendations and targets
for the EOTS v2.3 system. This module provides a baseline recommendation engine
when more advanced adaptive frameworks are disabled or not applicable.

Version: EOTS_FallbackRecs_v2.3.0_Canon_IDS_Unabridged
"""
import pandas as pd
import numpy as np
import logging
import sys # For fallback ids import check
from typing import Union, Optional, List, Dict, Any, Tuple, Callable
from datetime import datetime, time, date # Ensure all are imported

# --- Project-Specific Imports ---
try:
    from utils import ids
    from .system_utilities import ensure_columns, map_score_to_stars
    IMPORTS_SUCCESSFUL = True
    logger_init = logging.getLogger(__name__)
    logger_init.info("Fallback Recommendation Module (v2.3.0 Canon): Core utilities and ids imported successfully.")
except ImportError as e_fallback_imp:
    IMPORTS_SUCCESSFUL = False
    print(f"CRITICAL IMPORT ERROR in fallback_recommendation_module.py: {e_fallback_imp}. Fallback recommendations will fail or use dummies.")
    class ids: # type: ignore
        COL_STRIKE = "strike_price" # Minimal fallback
    def ensure_columns(df: pd.DataFrame, req_cols: List[str], name: str, log_instance: Optional[logging.Logger]=None) -> Tuple[pd.DataFrame, bool]: # type: ignore
        missing = [col for col in req_cols if col not in df.columns]; return df, not missing
    def map_score_to_stars(score: Optional[Union[float, int]], conviction_map: Dict[str, float], log_instance: Optional[logging.Logger]=None) -> int: return 0 # type: ignore

# Module-level logger
logger = logging.getLogger(__name__)
if not IMPORTS_SUCCESSFUL:
    logger.critical("Fallback Recommendation Module running with DUMMY imports due to failure. Functionality will be severely limited.")

MIN_NORMALIZATION_DENOMINATOR_FALLBACK = 1e-9

def get_enhanced_targets_fallback(
    recommendation_type_direction: str,
    entry_price_target_base: float,
    atr_val_target: float,
    sl_atr_mult_cfg_target: float,
    t1_atr_mult_no_sr_cfg_target: float,
    t2_atr_mult_no_sr_entry_cfg_target: float,
    t2_atr_mult_from_t1_sr_cfg_target: float,
    min_target_atr_dist_mult_cfg_target: float,
    support_levels_df_target: Optional[pd.DataFrame] = None,
    resistance_levels_df_target: Optional[pd.DataFrame] = None,
    strike_col_name_in_sr_df_target: str = ids.COL_STRIKE, # Default to ids.COL_STRIKE
    log_instance: Optional[logging.Logger] = None
) -> Dict[str, Optional[Union[float, str]]]: # Added str for rationale
    target_logger = log_instance.getChild("GetEnhancedTargetsFallback") if log_instance else logger.getChild("GetEnhancedTargetsFallback")
    target_logger.debug(f"Calculating fallback targets for {recommendation_type_direction} rec. EntryBase: {entry_price_target_base:.2f}, ATR: {atr_val_target:.4f}")

    sl_final: Optional[float] = None
    t1_final: Optional[float] = None
    t2_final: Optional[float] = None
    rationale_parts: List[str] = ["FallbackTargets:"]

    if not pd.notna(atr_val_target) or atr_val_target <= MIN_NORMALIZATION_DENOMINATOR_FALLBACK:
        target_logger.warning("ATR is zero, NaN, or invalid for target calculation. Returning None for targets/SL.")
        return {"stop_loss": None, "target_1": None, "target_2": None, "target_rationale": "ATR Invalid (Fallback)"}
    if not pd.notna(entry_price_target_base):
        target_logger.warning("Entry price base is NaN or invalid. Cannot calculate targets.")
        return {"stop_loss": None, "target_1": None, "target_2": None, "target_rationale": "Entry Price Invalid (Fallback)"}


    # Initial ATR-based SL and Targets
    if recommendation_type_direction.lower() == 'bullish':
        sl_atr = entry_price_target_base - (sl_atr_mult_cfg_target * atr_val_target)
        t1_atr = entry_price_target_base + (t1_atr_mult_no_sr_cfg_target * atr_val_target)
        t2_atr = entry_price_target_base + (t2_atr_mult_no_sr_entry_cfg_target * atr_val_target)
        rationale_parts.append(f"ATR(SL:{sl_atr_mult_cfg_target:.1f}x,T1:{t1_atr_mult_no_sr_cfg_target:.1f}x,T2:{t2_atr_mult_no_sr_entry_cfg_target:.1f}x).")
    elif recommendation_type_direction.lower() == 'bearish':
        sl_atr = entry_price_target_base + (sl_atr_mult_cfg_target * atr_val_target)
        t1_atr = entry_price_target_base - (t1_atr_mult_no_sr_cfg_target * atr_val_target)
        t2_atr = entry_price_target_base - (t2_atr_mult_no_sr_entry_cfg_target * atr_val_target)
        rationale_parts.append(f"ATR(SL:{sl_atr_mult_cfg_target:.1f}x,T1:{t1_atr_mult_no_sr_cfg_target:.1f}x,T2:{t2_atr_mult_no_sr_entry_cfg_target:.1f}x).")
    else:
        target_logger.warning(f"Unknown recommendation_type_direction: {recommendation_type_direction}. Cannot calculate targets.")
        return {"stop_loss": None, "target_1": None, "target_2": None, "target_rationale": "Unknown Direction (Fallback)"}

    sl_final = sl_atr
    t1_final = t1_atr
    t2_final = t2_atr # Initial T2 based on entry + ATR multiple

    min_dist_from_entry_for_sr = atr_val_target * min_target_atr_dist_mult_cfg_target

    # Refine T1 with S/R levels
    relevant_sr_for_t1: Optional[pd.DataFrame] = None
    if recommendation_type_direction.lower() == 'bullish' and isinstance(resistance_levels_df_target, pd.DataFrame) and not resistance_levels_df_target.empty:
        if strike_col_name_in_sr_df_target in resistance_levels_df_target.columns:
            resistance_levels_df_target[strike_col_name_in_sr_df_target] = pd.to_numeric(resistance_levels_df_target[strike_col_name_in_sr_df_target], errors='coerce')
            relevant_sr_for_t1 = resistance_levels_df_target[
                (resistance_levels_df_target[strike_col_name_in_sr_df_target] > entry_price_target_base + min_dist_from_entry_for_sr) &
                (resistance_levels_df_target[strike_col_name_in_sr_df_target] <= t1_atr)
            ].sort_values(by=strike_col_name_in_sr_df_target, ascending=True)
    elif recommendation_type_direction.lower() == 'bearish' and isinstance(support_levels_df_target, pd.DataFrame) and not support_levels_df_target.empty:
        if strike_col_name_in_sr_df_target in support_levels_df_target.columns:
            support_levels_df_target[strike_col_name_in_sr_df_target] = pd.to_numeric(support_levels_df_target[strike_col_name_in_sr_df_target], errors='coerce')
            relevant_sr_for_t1 = support_levels_df_target[
                (support_levels_df_target[strike_col_name_in_sr_df_target] < entry_price_target_base - min_dist_from_entry_for_sr) &
                (support_levels_df_target[strike_col_name_in_sr_df_target] >= t1_atr)
            ].sort_values(by=strike_col_name_in_sr_df_target, ascending=False)

    if relevant_sr_for_t1 is not None and not relevant_sr_for_t1.empty:
        sr_t1_val = pd.to_numeric(relevant_sr_for_t1[strike_col_name_in_sr_df_target].iloc[0], errors='coerce')
        if pd.notna(sr_t1_val):
            t1_final = sr_t1_val
            rationale_parts.append(f"T1@S/R:{t1_final:.2f}.")
            if recommendation_type_direction.lower() == 'bullish': t2_final = t1_final + (t2_atr_mult_from_t1_sr_cfg_target * atr_val_target)
            else: t2_final = t1_final - (t2_atr_mult_from_t1_sr_cfg_target * atr_val_target)
            rationale_parts.append(f"T2ReCalc(Factor:{t2_atr_mult_from_t1_sr_cfg_target:.1f}x).")

    # Refine T2 with S/R levels (if T1 was not S/R based or if T2 is still beyond next S/R)
    relevant_sr_for_t2: Optional[pd.DataFrame] = None
    if recommendation_type_direction.lower() == 'bullish' and isinstance(resistance_levels_df_target, pd.DataFrame) and not resistance_levels_df_target.empty and pd.notna(t1_final):
        if strike_col_name_in_sr_df_target in resistance_levels_df_target.columns: # Ensure column exists
            relevant_sr_for_t2 = resistance_levels_df_target[
                (resistance_levels_df_target[strike_col_name_in_sr_df_target] > t1_final + min_dist_from_entry_for_sr) &
                (resistance_levels_df_target[strike_col_name_in_sr_df_target] <= t2_final) # t2_final is current T2
            ].sort_values(by=strike_col_name_in_sr_df_target, ascending=True)
    elif recommendation_type_direction.lower() == 'bearish' and isinstance(support_levels_df_target, pd.DataFrame) and not support_levels_df_target.empty and pd.notna(t1_final):
        if strike_col_name_in_sr_df_target in support_levels_df_target.columns: # Ensure column exists
            relevant_sr_for_t2 = support_levels_df_target[
                (support_levels_df_target[strike_col_name_in_sr_df_target] < t1_final - min_dist_from_entry_for_sr) &
                (support_levels_df_target[strike_col_name_in_sr_df_target] >= t2_final) # t2_final is current T2
            ].sort_values(by=strike_col_name_in_sr_df_target, ascending=False)

    if relevant_sr_for_t2 is not None and not relevant_sr_for_t2.empty:
        sr_t2_val = pd.to_numeric(relevant_sr_for_t2[strike_col_name_in_sr_df_target].iloc[0], errors='coerce')
        if pd.notna(sr_t2_val):
            t2_final = sr_t2_val
            rationale_parts.append(f"T2@S/R:{t2_final:.2f}.")

    if sl_final is not None and t1_final is not None:
        if (recommendation_type_direction.lower() == 'bullish' and sl_final >= t1_final) or \
           (recommendation_type_direction.lower() == 'bearish' and sl_final <= t1_final):
            sl_final = None; rationale_parts.append("SL Invalid(>T1).")
            target_logger.warning("SL invalidated as it was beyond T1 after S/R adjustments.")

    return {
        "stop_loss": round(sl_final, 2) if pd.notna(sl_final) else None,
        "target_1": round(t1_final, 2) if pd.notna(t1_final) else None,
        "target_2": round(t2_final, 2) if pd.notna(t2_final) else None,
        "target_rationale": " ".join(rationale_parts)
    }

def get_strategy_recommendations_fallback(
    symbol_arg_fallback: str,
    mspi_df_aggregated_fallback: pd.DataFrame,
    trading_signals_fallback: Dict[str, Dict[str, list]],
    support_levels_df_fallback: Optional[pd.DataFrame],
    resistance_levels_df_fallback: Optional[pd.DataFrame],
    current_price_fallback: float,
    atr_fallback: float,
    recommendations_config_fallback: Dict[str, Any],
    targets_config_fallback: Dict[str, Any],
    map_score_to_stars_utility_func: Callable[[Optional[Union[float, int]], Dict[str, float], Optional[logging.Logger]], int],
    current_recommendation_id_counter_fallback: int,
    log_instance: Optional[logging.Logger] = None
) -> Tuple[List[Dict[str, Any]], int]:
    rec_logger_fb = log_instance.getChild("GetStrategyRecsFallback_v2.3.1") if log_instance else logger.getChild("GetStrategyRecsFallback_v2.3.1")
    rec_logger_fb.info(f"Generating FALLBACK strategy recommendations for {symbol_arg_fallback}...")
    recommendations_generated_list_fb: List[Dict[str, Any]] = []
    next_rec_id_counter_fb = current_recommendation_id_counter_fallback

    min_dir_stars_fb = int(recommendations_config_fallback.get("min_directional_stars_to_issue", 1))
    conviction_map_for_stars_util_fb = {
        k_map: float(v_map) for k_map, v_map in recommendations_config_fallback.items() if "conviction_map" in k_map
    }
    if not conviction_map_for_stars_util_fb:
        conviction_map_for_stars_util_fb = {"conviction_map_high":0.75, "conviction_map_high_medium":0.55, "conviction_map_medium":0.35, "conviction_map_medium_low":0.15, "conviction_map_base_one_star":0.05}
        rec_logger_fb.debug("Using default conviction map for stars as none found in config.")

    processed_strikes_fb: set[Union[float,str]] = set()
    signals_to_process_list_fb: List[Dict] = []

    directional_signals_dict_fb = trading_signals_fallback.get('directional', {})
    if isinstance(directional_signals_dict_fb, dict):
        signals_to_process_list_fb.extend(directional_signals_dict_fb.get('bullish', []))
        signals_to_process_list_fb.extend(directional_signals_dict_fb.get('bearish', []))
    if not signals_to_process_list_fb: rec_logger_fb.debug("No 'directional' signals found to process in fallback.")

    signals_to_process_list_fb.sort(key=lambda x_fb_sort: float(x_fb_sort.get('conviction_stars', 0.0)), reverse=True)

    for signal_data_item_fb_loop in signals_to_process_list_fb:
        if not isinstance(signal_data_item_fb_loop, dict): continue
        strike_val_from_signal_fb = signal_data_item_fb_loop.get('strike', signal_data_item_fb_loop.get('strike_price')) # Accept 'strike' or 'strike_price'
        if strike_val_from_signal_fb is None or strike_val_from_signal_fb in processed_strikes_fb: continue
        try: strike_val_float_from_signal_fb = float(strike_val_from_signal_fb)
        except (ValueError, TypeError): rec_logger_fb.warning(f"Could not convert strike '{strike_val_from_signal_fb}' to float."); continue

        base_stars_from_signal_fb = int(signal_data_item_fb_loop.get('conviction_stars', 0))
        if base_stars_from_signal_fb < min_dir_stars_fb: continue

        original_signal_type_lc_fb_loop = str(signal_data_item_fb_loop.get('type', 'UnknownSignal')).lower()
        mspi_val_at_signal_fb = pd.to_numeric(signal_data_item_fb_loop.get('mspi_value_at_signal', signal_data_item_fb_loop.get('mspi')), errors='coerce')

        bias_fb_loop = "neutral"
        if "bullish" in original_signal_type_lc_fb_loop: bias_fb_loop = "bullish"
        elif "bearish" in original_signal_type_lc_fb_loop: bias_fb_loop = "bearish"
        elif pd.notna(mspi_val_at_signal_fb): bias_fb_loop = "bullish" if mspi_val_at_signal_fb > 0.1 else ("bearish" if mspi_val_at_signal_fb < -0.1 else "neutral")
        if bias_fb_loop == "neutral": continue

        processed_strikes_fb.add(strike_val_from_signal_fb)
        # For fallback, use the signal's own star rating as the base for mapping, or its raw score if stars not present
        conviction_score_input_for_stars = float(signal_data_item_fb_loop.get('raw_conviction_score', base_stars_from_signal_fb))

        final_stars_val_fb_loop = map_score_to_stars_utility_func(conviction_score_input_for_stars, conviction_map_for_stars_util_fb, rec_logger_fb)
        if final_stars_val_fb_loop < min_dir_stars_fb: continue

        sl_atr_mult_cfg = float(targets_config_fallback.get("target_atr_stop_loss_multiplier", 1.5))
        t1_atr_no_sr_cfg = float(targets_config_fallback.get("target_atr_target1_multiplier_no_sr", 1.5))
        t2_atr_entry_cfg = float(targets_config_fallback.get("target_atr_target2_multiplier_no_sr", 3.0))
        t2_atr_t1_sr_cfg = float(targets_config_fallback.get("target_atr_target2_multiplier_from_t1", 1.8))
        min_dist_atr_cfg = float(targets_config_fallback.get("min_target_atr_distance", 0.5))

        targets_dict_fb = get_enhanced_targets_fallback(
            recommendation_type_direction=bias_fb_loop, entry_price_target_base=strike_val_float_from_signal_fb,
            atr_val_target=atr_fallback, sl_atr_mult_cfg_target=sl_atr_mult_cfg,
            t1_atr_mult_no_sr_cfg_target=t1_atr_no_sr_cfg, t2_atr_mult_no_sr_entry_cfg_target=t2_atr_entry_cfg,
            t2_atr_mult_from_t1_sr_cfg_target=t2_atr_t1_sr_cfg, min_target_atr_dist_mult_cfg_target=min_dist_atr_cfg,
            support_levels_df_target=support_levels_df_fallback, resistance_levels_df_target=resistance_levels_df_fallback,
            strike_col_name_in_sr_df_target=ids.COL_STRIKE, # Use ids constant
            log_instance=rec_logger_fb)

        next_rec_id_counter_fb += 1
        rec_id_val_fb_loop = f"SREC_{symbol_arg_fallback[:3].upper()}{next_rec_id_counter_fb:03d}"
        rec_details_dict_fb = {
            'id': rec_id_val_fb_loop, 'symbol': symbol_arg_fallback, 'timestamp': datetime.now().isoformat(),
            'category': "Directional (Fallback v2.3)", 'signal_type_source': original_signal_type_lc_fb_loop,
            'strike': strike_val_float_from_signal_fb, 'direction_label': bias_fb_loop.capitalize(),
            'conviction_stars': final_stars_val_fb_loop,
            'raw_conviction_score': round(conviction_score_input_for_stars,3),
            'entry_ideal': round(strike_val_float_from_signal_fb,2),
            **targets_dict_fb,
            'underlying_price_at_signal': current_price_fallback, 'atr_at_signal': atr_fallback,
            'mspi_at_signal': round(mspi_val_at_signal_fb,3) if pd.notna(mspi_val_at_signal_fb) else None,
            'sai_at_signal': round(float(signal_data_item_fb_loop.get('sai',0.0)),3) if pd.notna(signal_data_item_fb_loop.get('sai')) else None,
            'status': 'NEW_CANDIDATE_FALLBACK_V2.3',
            'rationale': targets_dict_fb.get("target_rationale", "Fallback ATR/SR Targets") + f" Signal: {original_signal_type_lc_fb_loop}."
        }
        recommendations_generated_list_fb.append(rec_details_dict_fb)
    rec_logger_fb.info(f"Generated {len(recommendations_generated_list_fb)} fallback recommendations for {symbol_arg_fallback}.")
    return recommendations_generated_list_fb, next_rec_id_counter_fb

