# core_analytics/level_identification_module.py
"""
Functions for identifying key levels, including support, resistance,
using various metrics from the Integrated Trading System for EOTS v2.3.
This version is refactored for full ids.py integration and to accept specific
input column names as parameters.

Version: EOTS_LevelID_Module_v2.3.0_Canon_IDS_Unabridged
"""
import pandas as pd
import numpy as np
import logging
import sys # For fallback ids import check
from typing import Union, Optional, List, Dict, Any, Deque, Tuple

# --- Project-Specific Imports ---
try:
    from utils import ids
    from .system_utilities import (
        ensure_columns,
        get_atr,
        # calculate_proximity_factor # Not directly used in this module's current logic
    )
    IMPORTS_SUCCESSFUL = True
    logger_init = logging.getLogger(__name__)
    logger_init.info("Level Identification Module (v2.3.0 Canon): Core utilities and ids imported successfully.")
except ImportError as e_level_imp:
    IMPORTS_SUCCESSFUL = False
    print(f"CRITICAL IMPORT ERROR in level_identification_module.py: {e_level_imp}. Level ID functions will fail or use dummies.")
    class ids: # type: ignore
        COL_STRIKE = "strike_price"; COL_LEVEL_TYPE = "level_type"; COL_LEVEL_STRENGTH = "strength_score"
        COL_MSPI_SCORE = "mspi"; COL_OPT_KIND = "opt_kind"; COL_DELTA_CONTRACT = "delta"
        COL_PRICE_OPTION_CONTRACT = "price"; COL_UNDERLYING_SYMBOL = "underlying_symbol"
        COL_VOLUME_OPTION_CONTRACT = "volm"


    def ensure_columns(df: pd.DataFrame, req_cols: List[str], name: str, log_instance: Optional[logging.Logger]=None) -> Tuple[pd.DataFrame, bool]: # type: ignore
        missing = [col for col in req_cols if col not in df.columns]; return df, not missing
    def get_atr(sym:str, price:float, cfg:Dict, hist:Optional[pd.DataFrame]=None, log_instance:Optional[logging.Logger]=None) -> float: return 0.01 * price if price else 0.5 # type: ignore

# Module-level logger
logger = logging.getLogger(__name__)
if not IMPORTS_SUCCESSFUL:
    logger.critical("Level Identification Module running with DUMMY imports due to failure. Functionality will be severely limited.")

MIN_NORMALIZATION_DENOMINATOR_LEVEL_ID = 1e-9
DEFAULT_ATR_FALLBACK_MIN_VALUE_LEVEL_ID = 1.0 # Changed from 0.01 in original, ensure this is sensible for ATR

def calculate_dynamic_mspi_thresholds(
    current_aggregated_df: pd.DataFrame, # Not directly used in this version, but kept for signature compatibility
    mspi_col_name: str, # Not directly used in this version, but kept for signature compatibility
    ekl_mtf_dyn_mspi_base_cfg: float,
    ekl_mtf_dyn_mspi_sens_cfg: float,
    historical_context: Optional[Dict] = None,
    log_instance: Optional[logging.Logger] = None
) -> Dict[str, float]:
    dyn_thresh_logger = log_instance.getChild("CalculateDynamicMSPIThresholds") if log_instance else logger.getChild("CalculateDynamicMSPIThresholds")

    base_thresh = float(ekl_mtf_dyn_mspi_base_cfg)
    sensitivity = float(ekl_mtf_dyn_mspi_sens_cfg)
    iv_rank = 0.5 # Default to neutral IV rank

    if historical_context and isinstance(historical_context.get("current_iv_rank"), (float, int)):
        iv_rank_val = historical_context["current_iv_rank"]
        if pd.notna(iv_rank_val) and 0.0 <= iv_rank_val <= 1.0:
            iv_rank = float(iv_rank_val)
        else:
            dyn_thresh_logger.debug(f"Invalid iv_rank '{iv_rank_val}' in historical_context, defaulting to 0.5.")
    else:
        dyn_thresh_logger.debug("No 'current_iv_rank' in historical_context for dynamic MSPI thresholds. Using default IV rank 0.5.")

    threshold_adjustment_factor = 1.0 + (iv_rank - 0.5) * 2.0 * sensitivity
    threshold_adjustment_factor = np.clip(threshold_adjustment_factor, 0.5, 1.5) # Clamp factor

    support_thresh = base_thresh * threshold_adjustment_factor
    resistance_thresh = -base_thresh * threshold_adjustment_factor # Negative for resistance

    dyn_thresh_logger.info(f"Dynamic MSPI Thresholds: Support={support_thresh:.4f}, Resistance={resistance_thresh:.4f} (Base={base_thresh:.3f}, IVRank={iv_rank:.2f}, AdjFactor={threshold_adjustment_factor:.3f})")
    return {"support": support_thresh, "resistance": resistance_thresh}

def identify_levels_from_df(
    aggregated_df: pd.DataFrame,
    mspi_col_name: str, # Actual name of the MSPI (or equivalent metric) column
    strike_col_name: str, # Actual name of the strike price column
    mspi_thresholds: Dict[str, float], # {"support": value, "resistance": value}
    level_type_label_prefix: str, # e.g., "Intraday_MSPI", "Daily_MSPI"
    timeframe_label: str, # e.g., "intraday", "daily"
    log_instance: Optional[logging.Logger] = None
) -> List[Dict]:
    levels_logger = log_instance.getChild("IdentifyLevelsFromDF") if log_instance else logger.getChild("IdentifyLevelsFromDF")

    if not isinstance(aggregated_df, pd.DataFrame) or aggregated_df.empty:
        levels_logger.debug(f"No data for identifying {level_type_label_prefix} {timeframe_label} levels. Input DF empty/invalid.")
        return []

    required_cols = [strike_col_name, mspi_col_name]
    # Capture all columns from the aggregated_df to pass them into the level dictionary
    df_copy, cols_ok = ensure_columns(aggregated_df.copy(), required_cols, f"LevelsFromDF_{level_type_label_prefix}", log_instance=levels_logger)
    if not cols_ok:
        levels_logger.warning(f"MSPI ('{mspi_col_name}') or Strike ('{strike_col_name}') column not found or invalid for {level_type_label_prefix} {timeframe_label} levels. Cannot identify levels.")
        return []

    identified_levels: List[Dict] = []
    df_copy[mspi_col_name] = pd.to_numeric(df_copy[mspi_col_name], errors='coerce').fillna(0.0)
    df_copy[strike_col_name] = pd.to_numeric(df_copy[strike_col_name], errors='coerce')
    df_copy.dropna(subset=[strike_col_name], inplace=True) # Critical: levels need a valid strike
    if df_copy.empty: return []


    support_threshold = mspi_thresholds.get("support")
    resistance_threshold = mspi_thresholds.get("resistance")

    if support_threshold is not None and isinstance(support_threshold, (int, float)):
        support_df = df_copy[df_copy[mspi_col_name] >= support_threshold]
        for _, row in support_df.iterrows():
            level_data = row.to_dict()
            level_data[ids.COL_LEVEL_TYPE] = 'support' # Use ids.py constant
            level_data['level_category_source'] = level_type_label_prefix
            level_data['timeframe'] = timeframe_label
            level_data['mspi_at_identification'] = row[mspi_col_name]
            level_data[ids.COL_STRIKE] = row[strike_col_name] # Ensure 'strike_price' key
            identified_levels.append(level_data)
    else: levels_logger.warning(f"Invalid support threshold for {timeframe_label} {level_type_label_prefix}.")

    if resistance_threshold is not None and isinstance(resistance_threshold, (int, float)):
        resistance_df = df_copy[df_copy[mspi_col_name] <= resistance_threshold]
        for _, row in resistance_df.iterrows():
            level_data = row.to_dict()
            level_data[ids.COL_LEVEL_TYPE] = 'resistance' # Use ids.py constant
            level_data['level_category_source'] = level_type_label_prefix
            level_data['timeframe'] = timeframe_label
            level_data['mspi_at_identification'] = row[mspi_col_name]
            level_data[ids.COL_STRIKE] = row[strike_col_name] # Ensure 'strike_price' key
            identified_levels.append(level_data)
    else: levels_logger.warning(f"Invalid resistance threshold for {timeframe_label} {level_type_label_prefix}.")

    log_s_thresh = f"{support_threshold:.3f}" if support_threshold is not None else "N/A"
    log_r_thresh = f"{resistance_threshold:.3f}" if resistance_threshold is not None else "N/A"
    levels_logger.debug(f"Identified {len(identified_levels)} {timeframe_label} S/R levels (source: {level_type_label_prefix}) using thresholds S:{log_s_thresh}, R:{log_r_thresh}.")
    return identified_levels

def identify_intraday_levels(
    current_aggregated_df: pd.DataFrame,
    mspi_col_name: str,
    strike_col_name: str,
    dynamic_mspi_thresholds: Dict[str, float],
    log_instance: Optional[logging.Logger] = None
) -> List[Dict]:
    intraday_logger = log_instance.getChild("IdentifyIntradayLevels") if log_instance else logger.getChild("IdentifyIntradayLevels")
    intraday_logger.info("Identifying intraday key levels...")
    if not isinstance(dynamic_mspi_thresholds, dict) or \
       not all(k in dynamic_mspi_thresholds for k in ["support", "resistance"]):
        intraday_logger.error(f"Dynamic MSPI thresholds invalid: {dynamic_mspi_thresholds}. Cannot identify intraday levels.")
        return []
    return identify_levels_from_df(current_aggregated_df, mspi_col_name, strike_col_name, dynamic_mspi_thresholds, "Intraday_MSPI", "intraday", log_instance=intraday_logger)

def identify_historical_levels(
    historical_aggregated_dfs: Optional[Deque[pd.DataFrame]],
    mspi_col_name: str,
    strike_col_name: str,
    lookback_count: int,
    persistence_req: int,
    mspi_strength_req: float,
    timeframe_label: str, # "daily" or "weekly"
    log_instance: Optional[logging.Logger] = None
) -> List[Dict]:
    hist_lvl_logger = log_instance.getChild(f"IdentifyHistoricalLevels_{timeframe_label}") if log_instance else logger.getChild(f"IdentifyHistoricalLevels_{timeframe_label}")
    hist_lvl_logger.info(f"Identifying {timeframe_label} levels (Lookback: {lookback_count}, PersistReq: {persistence_req}, MSPI_StrengthReq: {mspi_strength_req:.3f}).")
    if not historical_aggregated_dfs or len(historical_aggregated_dfs) < persistence_req:
        hist_lvl_logger.debug(f"Not enough historical DFs ({len(historical_aggregated_dfs) if historical_aggregated_dfs else 0}) for {timeframe_label} levels (need {persistence_req}).")
        return []

    candidate_levels_by_strike: Dict[float, List[Dict]] = {}
    dfs_to_scan = list(historical_aggregated_dfs)[:lookback_count]

    for df_idx, hist_df_raw in enumerate(dfs_to_scan):
        if not isinstance(hist_df_raw, pd.DataFrame) or hist_df_raw.empty: continue
        hist_df, cols_ok = ensure_columns(hist_df_raw.copy(), [mspi_col_name, strike_col_name], f"HistLevelScan_{timeframe_label}_{df_idx}", log_instance=hist_lvl_logger)
        if not cols_ok: continue
        hist_df[strike_col_name] = pd.to_numeric(hist_df[strike_col_name], errors='coerce')
        hist_df[mspi_col_name] = pd.to_numeric(hist_df[mspi_col_name], errors='coerce')
        hist_df.dropna(subset=[strike_col_name, mspi_col_name], inplace=True)
        if hist_df.empty: continue

        support_candidates = hist_df[hist_df[mspi_col_name] >= mspi_strength_req]
        resistance_candidates = hist_df[hist_df[mspi_col_name] <= -mspi_strength_req]
        for _, row in support_candidates.iterrows():
            level_info = row.to_dict(); level_info.update({ids.COL_LEVEL_TYPE: 'support', 'timeframe': timeframe_label, 'mspi_at_identification': row[mspi_col_name], ids.COL_STRIKE: row[strike_col_name]})
            candidate_levels_by_strike.setdefault(float(row[strike_col_name]), []).append(level_info)
        for _, row in resistance_candidates.iterrows():
            level_info = row.to_dict(); level_info.update({ids.COL_LEVEL_TYPE: 'resistance', 'timeframe': timeframe_label, 'mspi_at_identification': row[mspi_col_name], ids.COL_STRIKE: row[strike_col_name]})
            candidate_levels_by_strike.setdefault(float(row[strike_col_name]), []).append(level_info)

    persistent_levels_final: List[Dict] = []
    for strike_key_hist, levels_at_strike_list_hist in candidate_levels_by_strike.items():
        if len(levels_at_strike_list_hist) >= persistence_req:
            mspi_values = [lvl.get('mspi_at_identification', 0.0) for lvl in levels_at_strike_list_hist]
            avg_mspi_val_hist = np.mean([float(m) for m in mspi_values if pd.notna(m)]) if mspi_values else 0.0
            support_count_hist = sum(1 for lvl in levels_at_strike_list_hist if lvl.get(ids.COL_LEVEL_TYPE) == 'support')
            resistance_count_hist = sum(1 for lvl in levels_at_strike_list_hist if lvl.get(ids.COL_LEVEL_TYPE) == 'resistance')
            final_level_type_hist = 'support' if support_count_hist > resistance_count_hist else ('resistance' if resistance_count_hist > support_count_hist else ('support' if avg_mspi_val_hist >= 0 else 'resistance'))
            ref_level_base_hist = levels_at_strike_list_hist[0].copy() # Take first as base, update specific fields
            ref_level_base_hist[ids.COL_STRIKE] = strike_key_hist
            ref_level_base_hist['mspi_at_identification'] = round(avg_mspi_val_hist, 4)
            ref_level_base_hist[ids.COL_LEVEL_TYPE] = final_level_type_hist
            ref_level_base_hist['level_category_source'] = f"Historical_{timeframe_label}_MSPI"
            ref_level_base_hist['persistence_count'] = len(levels_at_strike_list_hist)
            persistent_levels_final.append(ref_level_base_hist)
    hist_lvl_logger.info(f"Identified {len(persistent_levels_final)} persistent {timeframe_label} levels.")
    return persistent_levels_final

def analyze_price_interaction(
    all_identified_levels: List[Dict],
    price_history_df: Optional[pd.DataFrame],
    current_atr: float,
    strike_col_name_in_levels: str, # Name of the strike key in level dicts (e.g., ids.COL_STRIKE)
    ekl_pi_lookback_candles_cfg: int,
    ekl_pi_reaction_thresh_atr_cfg: float,
    ekl_pi_bonus_hold_cfg: float,
    ekl_pi_penalty_breach_cfg: float,
    log_instance: Optional[logging.Logger] = None
) -> List[Dict]:
    pi_logger = log_instance.getChild("AnalyzePriceInteraction") if log_instance else logger.getChild("AnalyzePriceInteraction")
    if not all_identified_levels: return []
    if not isinstance(price_history_df, pd.DataFrame) or price_history_df.empty or not (isinstance(current_atr, (float, int)) and pd.notna(current_atr) and current_atr > MIN_NORMALIZATION_DENOMINATOR_LEVEL_ID):
        pi_logger.debug("Price history DF empty/invalid or ATR invalid. Skipping price interaction.")
        for level in all_identified_levels: level.update({'interaction_score': 0.0, 'tests': 0, 'holds': 0, 'breaches': 0})
        return all_identified_levels

    required_ohlc_cols = ['open', 'high', 'low', 'close'] # Date not strictly needed for interaction logic
    price_history, cols_ok = ensure_columns(price_history_df.copy(), required_ohlc_cols, "PriceInteractionHistory", log_instance=pi_logger)
    if not cols_ok:
        for level in all_identified_levels: level.update({'interaction_score': 0.0, 'tests': 0, 'holds': 0, 'breaches': 0})
        return all_identified_levels

    price_history_lookback = price_history.tail(ekl_pi_lookback_candles_cfg)
    if price_history_lookback.empty:
        for level in all_identified_levels: level.update({'interaction_score': 0.0, 'tests': 0, 'holds': 0, 'breaches': 0})
        return all_identified_levels

    reaction_dist_val = current_atr * ekl_pi_reaction_thresh_atr_cfg
    for level_dict in all_identified_levels:
        level_strike_raw = level_dict.get(strike_col_name_in_levels)
        level_type_str = str(level_dict.get(ids.COL_LEVEL_TYPE, '')).lower()
        interaction_score_val = 0.0; tests_count = 0; holds_count = 0; breaches_count = 0
        if level_strike_raw is None or level_type_str not in ['support', 'resistance']:
            level_dict.update({'interaction_score': 0.0, 'tests': 0, 'holds': 0, 'breaches': 0}); continue
        try: level_strike_flt = float(level_strike_raw)
        except (ValueError, TypeError): level_dict.update({'interaction_score': 0.0, 'tests': 0, 'holds': 0, 'breaches': 0}); continue

        for _, candle_row in price_history_lookback.iterrows():
            candle_low = pd.to_numeric(candle_row.get('low'), errors='coerce')
            candle_high = pd.to_numeric(candle_row.get('high'), errors='coerce')
            candle_close = pd.to_numeric(candle_row.get('close'), errors='coerce')
            candle_open = pd.to_numeric(candle_row.get('open'), errors='coerce')
            if any(pd.isna(v) for v in [candle_low, candle_high, candle_close, candle_open]): continue

            touched = (candle_low <= level_strike_flt <= candle_high)
            if touched: tests_count += 1
            if touched:
                reacted = (candle_high - candle_low) > reaction_dist_val
                if level_type_str == 'support':
                    if candle_close > level_strike_flt and reacted and candle_close > candle_open: holds_count +=1; interaction_score_val += ekl_pi_bonus_hold_cfg
                    elif candle_close < level_strike_flt: breaches_count +=1; interaction_score_val += ekl_pi_penalty_breach_cfg
                elif level_type_str == 'resistance':
                    if candle_close < level_strike_flt and reacted and candle_close < candle_open: holds_count +=1; interaction_score_val += ekl_pi_bonus_hold_cfg
                    elif candle_close > level_strike_flt: breaches_count +=1; interaction_score_val += ekl_pi_penalty_breach_cfg
        level_dict['interaction_score'] = round(interaction_score_val, 3)
        level_dict['tests'] = tests_count; level_dict['holds'] = holds_count; level_dict['breaches'] = breaches_count
    return all_identified_levels

def identify_level_clusters(
    all_levels_list: List[Dict],
    current_atr: float,
    strike_col_name_in_levels: str, # Name of the strike key in level dicts (e.g., ids.COL_STRIKE)
    ekl_mtf_cluster_dist_atr_cfg: float,
    mspi_at_identification_col: str = 'mspi_at_identification', # Key for MSPI value in level dicts
    log_instance: Optional[logging.Logger] = None
) -> List[Dict]:
    lc_logger = log_instance.getChild("IdentifyLevelClusters") if log_instance else logger.getChild("IdentifyLevelClusters")
    if not all_levels_list: return []
    if not (isinstance(current_atr, (float, int)) and pd.notna(current_atr) and current_atr > MIN_NORMALIZATION_DENOMINATOR_LEVEL_ID):
        lc_logger.warning(f"Current ATR ({current_atr}) invalid. Clustering ineffective.")
        for lvl_item in all_levels_list: lvl_item.update({'cluster_id': -1, 'is_cluster_peak': False})
        return all_levels_list

    try: df_levels_cluster = pd.DataFrame(all_levels_list)
    except Exception as e_df_create: lc_logger.error(f"Could not create DataFrame for clustering: {e_df_create}."); return all_levels_list
    if strike_col_name_in_levels not in df_levels_cluster.columns:
        lc_logger.warning(f"Missing strike column '{strike_col_name_in_levels}' for clustering."); return all_levels_list

    temp_numeric_strike_col = "_temp_numeric_strike_for_cluster"
    df_levels_cluster[temp_numeric_strike_col] = pd.to_numeric(df_levels_cluster[strike_col_name_in_levels], errors='coerce')
    df_levels_cluster.dropna(subset=[temp_numeric_strike_col], inplace=True)
    if df_levels_cluster.empty: return []

    df_levels_cluster = df_levels_cluster.sort_values(by=temp_numeric_strike_col).reset_index(drop=True)
    cluster_distance_val_abs = current_atr * ekl_mtf_cluster_dist_atr_cfg
    lc_logger.debug(f"Clustering with distance threshold: {cluster_distance_val_abs:.2f}")

    df_levels_cluster['cluster_id'] = -1; current_cluster_id_val = 0
    for i in range(len(df_levels_cluster)):
        if df_levels_cluster.loc[i, 'cluster_id'] == -1:
            current_cluster_id_val += 1; df_levels_cluster.loc[i, 'cluster_id'] = current_cluster_id_val
            for j in range(i + 1, len(df_levels_cluster)):
                if abs(df_levels_cluster.loc[j, temp_numeric_strike_col] - df_levels_cluster.loc[i, temp_numeric_strike_col]) <= cluster_distance_val_abs:
                    df_levels_cluster.loc[j, 'cluster_id'] = current_cluster_id_val
                else: break # Since sorted, further elements will also be too far

    df_levels_cluster['is_cluster_peak'] = False
    if mspi_at_identification_col in df_levels_cluster.columns:
        df_levels_cluster['_mspi_abs_for_peak'] = pd.to_numeric(df_levels_cluster[mspi_at_identification_col], errors='coerce').abs().fillna(0.0)
        if not df_levels_cluster.empty and 'cluster_id' in df_levels_cluster.columns and (df_levels_cluster['cluster_id'] != -1).any():
            try: peak_indices = df_levels_cluster.loc[df_levels_cluster['cluster_id'] != -1].groupby('cluster_id')['_mspi_abs_for_peak'].idxmax()
            except KeyError: # Handles empty groups if all cluster_id are -1
                peak_indices = pd.Series(dtype='int64')
            if not peak_indices.empty: df_levels_cluster.loc[peak_indices, 'is_cluster_peak'] = True
        df_levels_cluster.drop(columns=['_mspi_abs_for_peak'], inplace=True, errors='ignore')
    else: lc_logger.warning(f"MSPI column ('{mspi_at_identification_col}') not available for cluster peak identification.")

    df_levels_cluster.drop(columns=[temp_numeric_strike_col], inplace=True, errors='ignore')
    lc_logger.info(f"Identified {df_levels_cluster['cluster_id'][df_levels_cluster['cluster_id'] != -1].nunique()} level clusters.")
    return df_levels_cluster.to_dict('records')

def assign_level_strength(
    all_levels_with_interactions_clusters: List[Dict],
    ekl_ls_mspi_weight_cfg: float, ekl_ls_persist_weight_cfg: float,
    ekl_ls_price_int_weight_cfg: float, ekl_ls_cluster_bonus_cfg: float,
    ekl_mtf_intraday_weight_cfg: float,
    ekl_mtf_daily_lookback_dfs_cfg: int,
    ekl_mtf_weekly_lookback_dfs_cfg: int,
    log_instance: Optional[logging.Logger] = None
) -> List[Dict]:
    ls_logger = log_instance.getChild("AssignLevelStrength") if log_instance else logger.getChild("AssignLevelStrength")
    if not all_levels_with_interactions_clusters: return []

    for level_dict in all_levels_with_interactions_clusters:
        if not isinstance(level_dict, dict): continue
        mspi_val = pd.to_numeric(level_dict.get('mspi_at_identification', 0.0), errors='coerce'); mspi_mag = abs(mspi_val) if pd.notna(mspi_val) else 0.0
        pers_score = 0.0; timeframe = str(level_dict.get('timeframe', 'intraday')).lower()
        pers_count = int(pd.to_numeric(level_dict.get('persistence_count', 0 if timeframe != 'intraday' else 1), errors='coerce').fillna(0 if timeframe != 'intraday' else 1))
        if timeframe == 'daily': pers_score = 0.5 + (pers_count / max(1, ekl_mtf_daily_lookback_dfs_cfg * 0.5)) * 0.5
        elif timeframe == 'weekly': pers_score = 0.7 + (pers_count / max(1, ekl_mtf_weekly_lookback_dfs_cfg * 0.5)) * 0.3
        elif timeframe == 'intraday': pers_score = float(ekl_mtf_intraday_weight_cfg)
        pers_score = np.clip(pers_score, 0.0, 1.0)
        inter_score_raw = pd.to_numeric(level_dict.get('interaction_score', 0.0), errors='coerce'); inter_score_norm = np.clip((inter_score_raw * 0.5 + 0.5) if pd.notna(inter_score_raw) else 0.5, 0.0, 1.0)
        cluster_bonus = float(ekl_ls_cluster_bonus_cfg) if level_dict.get('is_cluster_peak', False) else 0.0
        strength = (mspi_mag * float(ekl_ls_mspi_weight_cfg) + pers_score * float(ekl_ls_persist_weight_cfg) + inter_score_norm * float(ekl_ls_price_int_weight_cfg) + cluster_bonus)
        level_dict[ids.COL_LEVEL_STRENGTH] = round(np.clip(strength, 0.0, 1.0), 3) # Use ids.py constant
    ls_logger.debug(f"Assigned strength scores to {len(all_levels_with_interactions_clusters)} levels.")
    return all_levels_with_interactions_clusters

def identify_enhanced_key_levels_main(
    current_aggregated_df: pd.DataFrame, # Strike-aggregated df with MSPI and other metrics
    # Column name parameters (to be passed by ITS, fetched from config using ids.py CFG_ constants)
    mspi_col_name_ekl: str, strike_col_name_ekl: str, underlying_symbol_col_ekl: str,
    price_col_ekl: str, # Column in current_aggregated_df holding underlying price (if per-row) or used for ATR context
    opt_kind_col_ekl: str, delta_col_ekl: str, volm_col_ekl: str, # For context, if needed by helpers
    # Configuration parameters (fetched by ITS from config and passed)
    ekl_mtf_dyn_mspi_base_cfg_ekl: float, ekl_mtf_dyn_mspi_sens_cfg_ekl: float,
    ekl_mtf_daily_lookback_dfs_cfg_ekl: int, ekl_mtf_daily_persistence_cfg_ekl: int, ekl_mtf_daily_mspi_thresh_cfg_ekl: float,
    ekl_mtf_weekly_lookback_dfs_cfg_ekl: int, ekl_mtf_weekly_persistence_cfg_ekl: int, ekl_mtf_weekly_mspi_thresh_cfg_ekl: float,
    ekl_pi_enabled_cfg_ekl: bool, # Added flag to enable/disable price interaction
    ekl_pi_lookback_candles_cfg_ekl: int, ekl_pi_reaction_thresh_atr_cfg_ekl: float,
    ekl_pi_bonus_hold_cfg_ekl: float, ekl_pi_penalty_breach_cfg_ekl: float,
    ekl_clustering_enabled_cfg_ekl: bool, # Added flag to enable/disable clustering
    ekl_mtf_cluster_dist_atr_cfg_ekl: float,
    ekl_ls_mspi_weight_cfg_ekl: float, ekl_ls_persist_weight_cfg_ekl: float,
    ekl_ls_price_int_weight_cfg_ekl: float, ekl_ls_cluster_bonus_cfg_ekl: float,
    ekl_mtf_intraday_weight_cfg_ekl: float,
    atr_fallback_cfg_ekl: Dict[str, Any],
    # Contextual Data (passed by ITS)
    historical_aggregated_dfs: Optional[Deque[pd.DataFrame]] = None,
    price_history_ohlc_df: Optional[pd.DataFrame] = None,
    current_underlying_price: Optional[float] = None, # Scalar current price
    historical_context_for_dyn_thresh: Optional[Dict] = None, # For IV rank etc.
    log_instance: Optional[logging.Logger] = None
) -> Dict[str, Any]:
    enh_levels_logger = log_instance.getChild("IdentifyEnhancedKeyLevels_Main") if log_instance else logger.getChild("IdentifyEnhancedKeyLevels_Main")
    enh_levels_logger.info("Identifying Enhanced Key Levels (v2.3 Orchestrator)...")
    empty_return = {"all_levels_sorted_by_strength": [], "intraday_levels": [], "daily_levels": [], "weekly_levels": [], "level_clusters_info": {}, "levels_with_strength_and_context": [], "error": None}

    if not isinstance(current_aggregated_df, pd.DataFrame) or current_aggregated_df.empty:
        empty_return["error"] = "Input aggregated data was empty or invalid."; enh_levels_logger.warning(empty_return["error"]); return empty_return

    current_price_ekl = current_underlying_price
    if not (isinstance(current_price_ekl, (int, float)) and pd.notna(current_price_ekl) and current_price_ekl > MIN_NORMALIZATION_DENOMINATOR_LEVEL_ID):
        enh_levels_logger.warning(f"Current underlying price ({current_price_ekl}) invalid for EKL. Attempting fallback from DataFrame's '{price_col_ekl}'.")
        if price_col_ekl in current_aggregated_df.columns and not current_aggregated_df[price_col_ekl].dropna().empty:
            first_valid_price = pd.to_numeric(current_aggregated_df[price_col_ekl].dropna().iloc[0], errors='coerce')
            if pd.notna(first_valid_price) and first_valid_price > MIN_NORMALIZATION_DENOMINATOR_LEVEL_ID: current_price_ekl = first_valid_price
            else: current_price_ekl = None
        else: current_price_ekl = None
        if current_price_ekl is None: empty_return["error"] = "Missing valid current underlying price for EKL."; enh_levels_logger.error(empty_return["error"]); return empty_return
        enh_levels_logger.info(f"Using derived current price for EKL: {current_price_ekl:.2f}")

    current_symbol_for_atr = current_aggregated_df[underlying_symbol_col_ekl].iloc[0] if underlying_symbol_col_ekl in current_aggregated_df.columns and not current_aggregated_df.empty and pd.notna(current_aggregated_df[underlying_symbol_col_ekl].iloc[0]) else "UNKNOWN_EKL"
    current_atr_val_ekl = get_atr(current_symbol_for_atr, current_price_ekl, atr_fallback_cfg_ekl, price_history_ohlc_df, log_instance=enh_levels_logger)
    enh_levels_logger.debug(f"ATR for EKL (Symbol: {current_symbol_for_atr}, Price: {current_price_ekl:.2f}): {current_atr_val_ekl:.3f}")

    all_potential_levels_list: List[Dict] = []
    dynamic_mspi_thresholds_ekl = calculate_dynamic_mspi_thresholds(current_aggregated_df, mspi_col_name_ekl, ekl_mtf_dyn_mspi_base_cfg_ekl, ekl_mtf_dyn_mspi_sens_cfg_ekl, historical_context_for_dyn_thresh, log_instance=enh_levels_logger)
    all_potential_levels_list.extend(identify_intraday_levels(current_aggregated_df, mspi_col_name_ekl, strike_col_name_ekl, dynamic_mspi_thresholds_ekl, log_instance=enh_levels_logger))
    if historical_aggregated_dfs:
        all_potential_levels_list.extend(identify_historical_levels(historical_aggregated_dfs, mspi_col_name_ekl, strike_col_name_ekl, ekl_mtf_daily_lookback_dfs_cfg_ekl, ekl_mtf_daily_persistence_cfg_ekl, ekl_mtf_daily_mspi_thresh_cfg_ekl, "daily", log_instance=enh_levels_logger))
        all_potential_levels_list.extend(identify_historical_levels(historical_aggregated_dfs, mspi_col_name_ekl, strike_col_name_ekl, ekl_mtf_weekly_lookback_dfs_cfg_ekl, ekl_mtf_weekly_persistence_cfg_ekl, ekl_mtf_weekly_mspi_thresh_cfg_ekl, "weekly", log_instance=enh_levels_logger))

    if ekl_pi_enabled_cfg_ekl: # Check flag before analyzing price interaction
        if price_history_ohlc_df is not None and not price_history_ohlc_df.empty and current_atr_val_ekl > MIN_NORMALIZATION_DENOMINATOR_LEVEL_ID:
            all_potential_levels_list = analyze_price_interaction(all_potential_levels_list, price_history_ohlc_df, current_atr_val_ekl, strike_col_name_ekl, ekl_pi_lookback_candles_cfg_ekl, ekl_pi_reaction_thresh_atr_cfg_ekl, ekl_pi_bonus_hold_cfg_ekl, ekl_pi_penalty_breach_cfg_ekl, log_instance=enh_levels_logger)
        else: enh_levels_logger.debug("Price interaction analysis skipped due to missing data or invalid ATR.")
    else: enh_levels_logger.info("Price interaction analysis disabled by config.")
    for lvl_dict_pi_default in all_potential_levels_list: # Ensure interaction keys exist
        lvl_dict_pi_default.setdefault('interaction_score', 0.0); lvl_dict_pi_default.setdefault('tests', 0); lvl_dict_pi_default.setdefault('holds', 0); lvl_dict_pi_default.setdefault('breaches', 0)

    if not all_potential_levels_list: empty_return["error"] = "No potential levels identified."; enh_levels_logger.info(empty_return["error"]); return empty_return

    levels_for_strength_assignment = all_potential_levels_list
    if ekl_clustering_enabled_cfg_ekl: # Check flag before clustering
        levels_for_strength_assignment = identify_level_clusters(all_potential_levels_list, current_atr_val_ekl, strike_col_name_ekl, ekl_mtf_cluster_dist_atr_cfg_ekl, mspi_at_identification_col='mspi_at_identification', log_instance=enh_levels_logger)
    else: enh_levels_logger.info("Level clustering disabled by config.")
    for lvl_dict_cl_default in levels_for_strength_assignment: # Ensure cluster keys exist
        lvl_dict_cl_default.setdefault('cluster_id', -1); lvl_dict_cl_default.setdefault('is_cluster_peak', False)


    final_levels_with_strength_list = assign_level_strength(levels_for_strength_assignment, ekl_ls_mspi_weight_cfg_ekl, ekl_ls_persist_weight_cfg_ekl, ekl_ls_price_int_weight_cfg_ekl, ekl_ls_cluster_bonus_cfg_ekl, ekl_mtf_intraday_weight_cfg_ekl, ekl_mtf_daily_lookback_dfs_cfg_ekl, ekl_mtf_weekly_lookback_dfs_cfg_ekl, log_instance=enh_levels_logger)
    final_levels_sorted_list = sorted(final_levels_with_strength_list, key=lambda x_sort: x_sort.get(ids.COL_LEVEL_STRENGTH, 0.0), reverse=True)

    level_clusters_info_output_dict = {} # Default to empty
    if ekl_clustering_enabled_cfg_ekl and final_levels_with_strength_list: # Only attempt if clustering was done
        try:
            df_for_cluster_info_final = pd.DataFrame(final_levels_with_strength_list)
            strike_col_for_agg_final = strike_col_name_ekl # Assume it's already numeric after validation
            if 'cluster_id' in df_for_cluster_info_final.columns and strike_col_for_agg_final in df_for_cluster_info_final.columns:
                 df_for_cluster_info_final.dropna(subset=[strike_col_for_agg_final, 'cluster_id'], inplace=True)
                 if not df_for_cluster_info_final.empty and (df_for_cluster_info_final['cluster_id'] != -1).any():
                    cluster_agg_final = df_for_cluster_info_final.groupby('cluster_id').agg(
                        min_strike=(strike_col_for_agg_final, 'min'), max_strike=(strike_col_for_agg_final, 'max'),
                        count=(strike_col_for_agg_final, 'count'), total_strength=(ids.COL_LEVEL_STRENGTH, 'sum'),
                        avg_strength=(ids.COL_LEVEL_STRENGTH, 'mean')).reset_index()
                    level_clusters_info_output_dict = cluster_agg_final.set_index('cluster_id').to_dict('index')
        except Exception as e_cluster_info_final: enh_levels_logger.error(f"Error generating level_clusters_info_dict: {e_cluster_info_final}", exc_info=True)

    enh_levels_logger.info(f"Enhanced key level identification complete. Total unique levels with strength: {len(final_levels_sorted_list)}")
    empty_return["all_levels_sorted_by_strength"] = final_levels_sorted_list
    empty_return["intraday_levels"] = [lvl for lvl in final_levels_with_strength_list if lvl.get('timeframe') == 'intraday']
    empty_return["daily_levels"] = [lvl for lvl in final_levels_with_strength_list if lvl.get('timeframe') == 'daily']
    empty_return["weekly_levels"] = [lvl for lvl in final_levels_with_strength_list if lvl.get('timeframe') == 'weekly']
    empty_return["level_clusters_info"] = level_clusters_info_output_dict
    empty_return["levels_with_strength_and_context"] = final_levels_with_strength_list
    return empty_return

# --- Stubs for Advanced v2.5+ Features (Not part of v2.3 core EKL) ---
def detect_advanced_walls_and_triggers_stub(*args: Any, **kwargs: Any) -> Dict[str, Any]:
    logger_stub = kwargs.get('log_instance', logging.getLogger(__name__)).getChild("DetectAdvancedWallsStub")
    logger_stub.warning("Using STUB for detect_advanced_walls_and_triggers. Returning empty structure.")
    return {"wall_levels": [], "vol_trigger_levels": [], "wall_strength_data": [], "trigger_strength_data": []}

def identify_conviction_based_levels_specific_stub(*args: Any, **kwargs: Any) -> Dict[str, Any]:
    logger_stub = kwargs.get('log_instance', logging.getLogger(__name__)).getChild("IdentifyConvictionLevelsSpecificStub")
    logger_stub.warning("Using STUB for identify_conviction_based_levels_specific. Returning empty structure.")
    return {"high_conviction_levels_specific": [], "metric_weights_debug": {}}

