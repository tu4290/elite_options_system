# core_analytics/recommendation_state_manager.py
"""
Manages the state of active trade recommendations, including exits, adjustments,
and interactions with new signals.
This 'enhanced v2.3.0' iteration is fully unabridged and integrated with ids.py,
incorporating all identified corrections.

Version: EOTS_RecStateMgr_v2.3.0_Canon_IDS_Unabridged_Final
"""
import pandas as pd
import numpy as np
import logging
import sys # For fallback ids import check
from typing import Union, Optional, List, Dict, Any, Deque, Callable, Tuple
from datetime import datetime, time, date, timedelta
from collections import deque

# --- Project-Specific Imports ---
# Attempt to import 'ids' and 'system_utilities'
# Fallbacks are provided if imports fail, allowing the script to be parsed
# but functionality will be severely limited.
try:
    from utils import ids # Assuming ids.py is in elite_options_system_package.utils
    from .system_utilities import ensure_columns, map_score_to_stars, get_atr
    IMPORTS_SUCCESSFUL_RSM = True
    logger_init_rsm = logging.getLogger(__name__) # Use a unique name
    logger_init_rsm.info("Recommendation State Manager (v2.3.0 Canon Final): Core utilities and ids imported successfully.")
except ImportError as e_rsm_imp_critical:
    IMPORTS_SUCCESSFUL_RSM = False
    print(f"CRITICAL IMPORT ERROR in recommendation_state_manager.py: {e_rsm_imp_critical}. RSM functions will fail or use dummies.")

    # --- Fallback definitions for ids ---
    class ids: # type: ignore
        COL_STRIKE = "strike_price"
        COL_MSPI_SCORE = "mspi"
        # For update_symbol_adaptive_historical_context defaults
        CV_CHAIN_PARAM_DXVOLM = "dxvolm" # Corrected
        CV_CHAIN_PARAM_GXVOLM = "gxvolm" # Corrected
        CV_UND_PARAM_IV_PERCENTILE_30D = "iv_percentile_30d" # Example, ensure it matches your actual ids.py
        # Add any other ids constants used directly in this file if their absence would break parsing
        # For example, if COL_TIMESTAMP or similar are used directly.
        # For this version, focusing on the ones directly in function signatures.

    # --- Fallback definitions for system_utilities functions ---
    def ensure_columns(df: pd.DataFrame, req_cols: List[str], name: str, log_instance: Optional[logging.Logger]=None) -> Tuple[pd.DataFrame, bool]: # type: ignore
        missing = [col for col in req_cols if col not in df.columns]
        if log_instance: log_instance.warning(f"DUMMY ensure_columns ({name}): Missing {missing}")
        else: print(f"DUMMY ensure_columns ({name}): Missing {missing}")
        # For dummy, let's assume columns are present to allow parsing
        return df, not missing

    def map_score_to_stars(score: Optional[Union[float, int]], conviction_map: Dict[str, float], log_instance: Optional[logging.Logger]=None) -> int: # type: ignore
        if log_instance: log_instance.debug("DUMMY map_score_to_stars called")
        else: print("DUMMY map_score_to_stars called")
        return 0

    def get_atr(sym:str, price:float, cfg:Dict, history_df:Optional[pd.DataFrame]=None, log_instance:Optional[logging.Logger]=None) -> float: # type: ignore
        if log_instance: log_instance.debug(f"DUMMY get_atr called for {sym}")
        else: print(f"DUMMY get_atr called for {sym}")
        return 0.01 * price if price and price > 0 else 0.5

# Module-level logger
logger = logging.getLogger(__name__)
if not IMPORTS_SUCCESSFUL_RSM:
    logger.critical("Recommendation State Manager (v2.3.0 Canon Final) running with DUMMY imports due to failure. Functionality will be SEVERELY LIMITED.")

MIN_NORMALIZATION_DENOMINATOR_RSM = 1e-9

def is_immediate_exit_warranted(
    recommendation: Dict[str, Any],
    current_aggregated_mspi_df: pd.DataFrame, # DataFrame containing strike-level MSPI scores
    current_price: float, # Current underlying price
    current_atr: float, # Current ATR of the underlying
    exit_mspi_flip_thresh_cfg: float, # Config: MSPI threshold for flip exit
    exit_atr_stop_factor_cfg: float, # Config: ATR multiplier for stop loss
    exit_profit_target_factor_cfg: float, # Config: Factor of ATR for profit target (T1 used here)
    exit_max_hold_time_cfg: Dict[str, int], # Config: Max hold time e.g. {"days": D, "hours": H, "minutes": M}
    strike_col_df: str = ids.COL_STRIKE, # Column name for strike in current_aggregated_mspi_df
    mspi_col_df: str = ids.COL_MSPI_SCORE, # Column name for MSPI in current_aggregated_mspi_df
    historical_context: Optional[Dict] = None, # For future use, e.g., adaptive exits
    log_instance: Optional[logging.Logger] = None
) -> Optional[str]: # Returns exit reason string or None
    exit_logger = log_instance.getChild("IsImmediateExitWarranted_v2.3") if log_instance else logger.getChild("IsImmediateExitWarranted_v2.3")

    rec_id = recommendation.get('id', 'UnknownRec')
    rec_strike_raw = recommendation.get('strike')
    rec_direction = str(recommendation.get('direction_label', '')).lower()
    rec_status = str(recommendation.get('status', 'UNKNOWN')) # e.g., "ACTIVE_NEW", "ACTIVE_ADJUSTED"
    rec_entry_price_raw = recommendation.get('entry_ideal', rec_strike_raw) # Use strike if entry_ideal not set
    rec_stop_loss_raw = recommendation.get('stop_loss')
    rec_target_1_raw = recommendation.get('target_1')
    rec_timestamp_str = recommendation.get('timestamp') # ISO format string

    if rec_status.startswith("EXITED_"):
        exit_logger.debug(f"Rec ID {rec_id}: Already exited ({rec_status}). No further exit checks.")
        return None # Already exited, no action

    # Convert critical numeric fields, handling potential errors
    try:
        rec_strike = float(rec_strike_raw) if pd.notna(rec_strike_raw) else None
        rec_entry_price = float(rec_entry_price_raw) if pd.notna(rec_entry_price_raw) else None
        rec_stop_loss = float(rec_stop_loss_raw) if pd.notna(rec_stop_loss_raw) else None
        rec_target_1 = float(rec_target_1_raw) if pd.notna(rec_target_1_raw) else None
    except (ValueError, TypeError) as e_conv:
        exit_logger.warning(f"Rec ID {rec_id}: Could not convert critical numeric fields (strike, entry, SL, T1) to float: {e_conv}. Skipping exit check.")
        return None

    if rec_strike is None or rec_direction not in ['bullish', 'bearish'] or rec_entry_price is None or not pd.notna(current_price):
        exit_logger.debug(f"Rec ID {rec_id}: Insufficient core data (strike, direction, entry_price, or current_price invalid) for exit check. Skipping.")
        return None
    
    atr_is_valid = pd.notna(current_atr) and current_atr > MIN_NORMALIZATION_DENOMINATOR_RSM

    # 1. ATR Stop Loss Check (Only if stop loss is defined and ATR is valid)
    if rec_stop_loss is not None: # Check if an explicit SL was set for the recommendation
        if rec_direction == 'bullish' and current_price <= rec_stop_loss:
            return f"Stop Loss Hit ({current_price:.2f} <= SL {rec_stop_loss:.2f})"
        if rec_direction == 'bearish' and current_price >= rec_stop_loss:
            return f"Stop Loss Hit ({current_price:.2f} >= SL {rec_stop_loss:.2f})"
    elif atr_is_valid : # Fallback to dynamic ATR stop if no explicit SL and ATR is valid
        # This section implies a dynamic ATR stop if no SL was set, which might be desired.
        # If explicit SL is always set, this 'elif' might not be needed or should be conditional.
        # For now, assuming if rec_stop_loss is None, we might still check a dynamic one.
        # However, the original logic seems to rely on rec_stop_loss being pre-calculated.
        # Let's stick to checking only if rec_stop_loss is defined.
        pass


    # 2. MSPI Flip Check
    if not current_aggregated_mspi_df.empty and strike_col_df in current_aggregated_mspi_df.columns and mspi_col_df in current_aggregated_mspi_df.columns:
        try:
            # Ensure strikes are numeric for matching
            temp_df_mspi = current_aggregated_mspi_df.copy()
            temp_df_mspi['_numeric_strike_exit_check'] = pd.to_numeric(temp_df_mspi[strike_col_df], errors='coerce')
            temp_df_mspi.dropna(subset=['_numeric_strike_exit_check'], inplace=True) # Drop rows where strike couldn't be converted
            
            strike_mspi_series = temp_df_mspi.set_index('_numeric_strike_exit_check')[mspi_col_df]

            if rec_strike in strike_mspi_series.index: # Check if the recommendation's strike exists in current MSPI data
                current_mspi_at_strike = pd.to_numeric(strike_mspi_series.loc[rec_strike], errors='coerce')
                if pd.notna(current_mspi_at_strike):
                    # Ensure exit_mspi_flip_thresh_cfg is positive for comparison
                    positive_flip_thresh = abs(exit_mspi_flip_thresh_cfg)
                    if rec_direction == 'bullish' and current_mspi_at_strike < -positive_flip_thresh:
                        return f"MSPI Flip Against Bullish ({current_mspi_at_strike:.2f} < -{positive_flip_thresh:.2f})"
                    if rec_direction == 'bearish' and current_mspi_at_strike > positive_flip_thresh:
                        return f"MSPI Flip Against Bearish ({current_mspi_at_strike:.2f} > {positive_flip_thresh:.2f})"
                else:
                    exit_logger.debug(f"Rec ID {rec_id}: MSPI value at strike {rec_strike} is NaN. Cannot perform MSPI flip check.")
            else:
                exit_logger.debug(f"Rec ID {rec_id}: Strike {rec_strike} not found in current MSPI data for MSPI flip check.")
        except KeyError: # Handles case where rec_strike might not be in index after all checks
             exit_logger.debug(f"Rec ID {rec_id}: Strike {rec_strike} (KeyError) not found in current MSPI data index for MSPI flip check.")
        except Exception as e_mspi_flip_check:
            exit_logger.warning(f"Rec ID {rec_id}: Error during MSPI flip check: {e_mspi_flip_check}", exc_info=False)


    # 3. Max Hold Time Check
    if rec_timestamp_str:
        try:
            # Attempt to parse ISO format, handling potential 'Z' for UTC
            issued_dt = datetime.fromisoformat(str(rec_timestamp_str).replace("Z", "+00:00"))
            
            days_hold = int(exit_max_hold_time_cfg.get("days", 0))
            hours_hold = int(exit_max_hold_time_cfg.get("hours", 0)) # Default hours to 0 if not specified
            minutes_hold = int(exit_max_hold_time_cfg.get("minutes", 0))

            # If all are zero, use a sensible default (e.g., 3 days = 72 hours)
            if days_hold == 0 and hours_hold == 0 and minutes_hold == 0:
                max_hold_delta = timedelta(hours=72) # Default to 72 hours
                exit_logger.debug(f"Rec ID {rec_id}: Max hold time config resulted in zero delta. Using fallback {max_hold_delta}.")
            else:
                max_hold_delta = timedelta(days=days_hold, hours=hours_hold, minutes=minutes_hold)

            # Ensure timezone-aware comparison if issued_dt is timezone-aware
            now_dt = datetime.now(issued_dt.tzinfo if issued_dt.tzinfo else None)

            if now_dt > (issued_dt + max_hold_delta):
                return f"Max Hold Time Exceeded (>{max_hold_delta})"
        except ValueError as e_time_parse: # Specific error for parsing
            exit_logger.warning(f"Rec ID {rec_id}: Error parsing recommendation timestamp '{rec_timestamp_str}': {e_time_parse}. Max hold time check skipped.", exc_info=False)
        except Exception as e_time_calc: # Catch other potential errors
            exit_logger.warning(f"Rec ID {rec_id}: Error calculating max hold time from timestamp '{rec_timestamp_str}': {e_time_calc}. Max hold time check skipped.", exc_info=False)

    # 4. Target 1 Hit Check (Profit Target)
    if rec_target_1 is not None: # Check if Target 1 is defined for the recommendation
        if rec_direction == 'bullish' and current_price >= rec_target_1:
            return f"Target 1 Hit ({current_price:.2f} >= T1 {rec_target_1:.2f})"
        if rec_direction == 'bearish' and current_price <= rec_target_1:
            return f"Target 1 Hit ({current_price:.2f} <= T1 {rec_target_1:.2f})"
            
    return None # No immediate exit condition met

def adjust_active_recommendation_parameters(
    recommendation: Dict[str, Any],
    support_levels_df_adj: Optional[pd.DataFrame], # Optional: DataFrame of support levels
    resistance_levels_df_adj: Optional[pd.DataFrame], # Optional: DataFrame of resistance levels
    strike_col_name_in_sr_df_adj: str, # Column name for strike in S/R DataFrames (e.g., ids.COL_STRIKE)
    current_price_adj: float, # Current underlying price
    current_atr_adj: float, # Current ATR of the underlying
    adj_trailing_stop_enabled_cfg: bool, # Config: Enable/disable trailing stop
    adj_trailing_stop_atr_mult_cfg: float, # Config: ATR multiplier for trailing stop
    adj_move_sl_to_be_pct_cfg: float, # Config: Pct of (Entry to T1) distance to trigger SL move to BreakEven
    targets_config_for_recalc_cfg: Dict[str, Any], # Config for get_enhanced_targets if TSL needs new targets
    get_enhanced_targets_utility_func: Optional[Callable[..., Dict[str, Optional[float]]]], # Utility to recalc targets
    historical_context_adj: Optional[Dict] = None, # For future, more adaptive adjustments
    log_instance: Optional[logging.Logger] = None
) -> None: # Modifies recommendation dictionary in-place
    adj_logger = log_instance.getChild("AdjustActiveRecParams_v2.3.1") if log_instance else logger.getChild("AdjustActiveRecParams_v2.3.1")

    rec_id = recommendation.get('id', 'UnknownRec')
    rec_status = str(recommendation.get('status', ''))
    if rec_status.startswith("EXITED_") or not rec_status.startswith("ACTIVE_"):
        adj_logger.debug(f"Rec ID {rec_id}: Skipping adjustments, status is '{rec_status}'.")
        return

    original_sl_raw = recommendation.get('stop_loss'); original_t1_raw = recommendation.get('target_1')
    entry_price_raw = recommendation.get('entry_ideal', recommendation.get('strike')) # Fallback to strike if entry_ideal missing
    direction = str(recommendation.get('direction_label', '')).lower()

    try:
        original_sl = float(original_sl_raw) if pd.notna(original_sl_raw) else None
        original_t1 = float(original_t1_raw) if pd.notna(original_t1_raw) else None
        entry_price = float(entry_price_raw) if pd.notna(entry_price_raw) else None
    except (ValueError, TypeError) as e_conv_adj:
        adj_logger.warning(f"Rec ID {rec_id}: Error converting SL/T1/Entry to float for adjustment: {e_conv_adj}. Skipping.")
        return

    if entry_price is None or direction not in ['bullish', 'bearish'] or not (pd.notna(current_atr_adj) and current_atr_adj > MIN_NORMALIZATION_DENOMINATOR_RSM):
        adj_logger.warning(f"Rec ID {rec_id}: Insufficient data for adjustment (entry, direction, or ATR invalid: {current_atr_adj}). Skipping.")
        return

    new_sl = original_sl # Initialize new_sl with the current stop_loss
    adjustment_notes: List[str] = []

    # 1. Trailing Stop Loss (Simple ATR based)
    if adj_trailing_stop_enabled_cfg and original_sl is not None: # Only trail if an initial SL exists
        potential_trailing_sl: Optional[float] = None
        if direction == 'bullish':
            potential_trailing_sl = current_price_adj - (adj_trailing_stop_atr_mult_cfg * current_atr_adj)
            # Only trail if the new SL is higher (better for a bullish trade) than the current SL
            if new_sl is None or (potential_trailing_sl is not None and potential_trailing_sl > new_sl):
                new_sl = potential_trailing_sl
                adjustment_notes.append(f"TrailingSL->{new_sl:.2f if new_sl is not None else 'None'}")
        elif direction == 'bearish':
            potential_trailing_sl = current_price_adj + (adj_trailing_stop_atr_mult_cfg * current_atr_adj)
            # Only trail if the new SL is lower (better for a bearish trade) than the current SL
            if new_sl is None or (potential_trailing_sl is not None and potential_trailing_sl < new_sl):
                new_sl = potential_trailing_sl
                adjustment_notes.append(f"TrailingSL->{new_sl:.2f if new_sl is not None else 'None'}")

    # 2. Move SL to Break-Even (or slightly better based on config)
    # This triggers if price moves a certain percentage of the distance from entry to Target 1.
    if adj_move_sl_to_be_pct_cfg > 0 and original_t1 is not None and entry_price is not None:
        # Define breakeven slightly in profit to cover potential slippage/commissions (e.g., 0.05 * ATR)
        # For simplicity here, BE is exactly entry_price. Configurable BE offset can be added.
        breakeven_sl_target = entry_price 
        
        profit_to_t1 = abs(original_t1 - entry_price)
        if profit_to_t1 > MIN_NORMALIZATION_DENOMINATOR_RSM: # Ensure T1 is meaningfully different from entry
            trigger_price_for_be: Optional[float] = None
            if direction == 'bullish':
                trigger_price_for_be = entry_price + (adj_move_sl_to_be_pct_cfg * profit_to_t1)
            elif direction == 'bearish':
                trigger_price_for_be = entry_price - (adj_move_sl_to_be_pct_cfg * profit_to_t1)

            moved_to_be = False
            if trigger_price_for_be is not None:
                if direction == 'bullish' and current_price_adj >= trigger_price_for_be:
                    # Move SL to BE if current SL is below BE
                    if new_sl is None or new_sl < breakeven_sl_target:
                        new_sl = breakeven_sl_target; moved_to_be = True
                elif direction == 'bearish' and current_price_adj <= trigger_price_for_be:
                    # Move SL to BE if current SL is above BE
                    if new_sl is None or new_sl > breakeven_sl_target:
                        new_sl = breakeven_sl_target; moved_to_be = True
            
            if moved_to_be:
                adjustment_notes.append(f"SLtoBE@{breakeven_sl_target:.2f}")

    # Final check: Ensure adjusted SL is not beyond T1 (if T1 exists and SL was adjusted)
    if new_sl is not None and original_t1 is not None and new_sl != original_sl : # Check if SL was actually changed
        atr_buffer_for_sl_cap = 0.1 * current_atr_adj # Small buffer from T1
        if direction == 'bullish' and new_sl >= original_t1:
            adj_logger.debug(f"Rec ID {rec_id}: New SL ({new_sl:.2f}) would exceed/equal T1 ({original_t1:.2f}). Capping SL to T1 - buffer.")
            new_sl = original_t1 - atr_buffer_for_sl_cap
            # Ensure capped SL is still better than original SL if possible, or at least not worse than entry for BE moves
            if original_sl is not None and new_sl < original_sl and not any("SLtoBE" in note for note in adjustment_notes):
                 new_sl = original_sl # Revert if capping makes it worse than original non-BE SL
            elif any("SLtoBE" in note for note in adjustment_notes) and new_sl < entry_price:
                 new_sl = entry_price # Ensure BE move at least stays at BE
            adjustment_notes.append(f"SL_Capped<T1@{new_sl:.2f}")

        elif direction == 'bearish' and new_sl <= original_t1:
            adj_logger.debug(f"Rec ID {rec_id}: New SL ({new_sl:.2f}) would exceed/equal T1 ({original_t1:.2f}). Capping SL to T1 + buffer.")
            new_sl = original_t1 + atr_buffer_for_sl_cap
            if original_sl is not None and new_sl > original_sl and not any("SLtoBE" in note for note in adjustment_notes):
                 new_sl = original_sl
            elif any("SLtoBE" in note for note in adjustment_notes) and new_sl > entry_price:
                 new_sl = entry_price
            adjustment_notes.append(f"SL_Capped>T1@{new_sl:.2f}")


    # Apply updates if SL has meaningfully changed
    if new_sl is not None and (original_sl is None or abs(new_sl - original_sl) > MIN_NORMALIZATION_DENOMINATOR_RSM):
        recommendation['stop_loss'] = round(new_sl, 2)
        if not rec_status.endswith("_ADJUSTED"): # Avoid appending _ADJUSTED multiple times
            recommendation['status'] = "ACTIVE_ADJUSTED"
        recommendation['last_adjusted_ts'] = datetime.now().isoformat() # Update timestamp of adjustment
        
        existing_adj_log = recommendation.get('adjustment_log', [])
        if isinstance(existing_adj_log, list):
            # Add new unique notes
            for note in adjustment_notes:
                if note not in existing_adj_log: existing_adj_log.append(note)
            recommendation['adjustment_log'] = existing_adj_log
        else: # If not a list (e.g. first adjustment), overwrite with new notes
            recommendation['adjustment_log'] = adjustment_notes
        adj_logger.info(f"Rec ID {rec_id}: Adjusted. New SL: {recommendation['stop_loss']:.2f}. Notes: {recommendation['adjustment_log']}")
    elif adjustment_notes and (new_sl is None or (original_sl is not None and abs(new_sl - original_sl) <= MIN_NORMALIZATION_DENOMINATOR_RSM)) : 
        # Logic was run, notes were generated, but SL didn't change significantly from original
        adj_logger.debug(f"Rec ID {rec_id}: Adjustment logic run, SL ({original_sl}) effectively unchanged. Notes attempted: {', '.join(adjustment_notes)}")


def update_symbol_adaptive_historical_context(
    symbol: str,
    current_adaptive_historical_context: Dict[str, Any], # This dict is modified in-place
    raw_per_contract_df: pd.DataFrame, # DataFrame with detailed per-contract data
    aggregated_strike_df: pd.DataFrame, # DataFrame with data aggregated at strike level
    current_signals: Dict[str, Any], # Current cycle's generated signals (not directly used for context update in v2.3)
    current_levels: Dict[str, Any], # Current cycle's identified key levels (not directly used for context update in v2.3)
    new_recommendations_this_cycle: List[Dict[str, Any]], # For performance tracking stub
    current_iv_context_snapshot: Optional[Dict[str, Any]], # Snapshot of IV metrics (e.g., from TradierFetcher)
    current_atr_value: float, # Current ATR value for the symbol
    # Configs
    flow_recency_maxlen_cfg: int, # Max length for flow deques
    surface_dynamics_maxlen_cfg: int, # Max length for IV surface snapshots deque
    perf_track_window_cfg: int, # Max length for ATR history and recommendation log
    # Column name parameters for data extraction (ensure these match actual column names in provided DataFrames)
    strike_col_name_hist: str = ids.COL_STRIKE,
    proxy_delta_flow_col_hist: str = ids.CV_CHAIN_PARAM_DXVOLM, # Corrected
    proxy_gamma_flow_col_hist: str = ids.CV_CHAIN_PARAM_GXVOLM, # Corrected
    iv_context_percentile_key_hist: str = ids.CV_UND_PARAM_IV_PERCENTILE_30D, # Key in current_iv_context_snapshot
    log_instance: Optional[logging.Logger] = None
) -> Dict[str, Any]: # Returns the modified context dictionary
    hist_ctx_logger = log_instance.getChild("UpdateSymbolAdaptiveHistoricalContext_v2.3") if log_instance else logger.getChild("UpdateSymbolAdaptiveHistoricalContext_v2.3")
    hist_ctx_logger.debug(f"Updating adaptive historical context for symbol: {symbol}")

    # Ensure deques exist and have the correct maxlen, initializing if necessary
    # For v2.3, focus on ATR history and basic IV context. Flow/surface tracking is more v2.5.
    # These deques store snapshots over time.
    
    # Ensure 'past_flow_delta' deque exists with correct maxlen
    past_flow_delta_deque = current_adaptive_historical_context.get("past_flow_delta")
    if not isinstance(past_flow_delta_deque, deque) or getattr(past_flow_delta_deque, 'maxlen', None) != flow_recency_maxlen_cfg:
        current_adaptive_historical_context["past_flow_delta"] = deque(maxlen=flow_recency_maxlen_cfg)
        hist_ctx_logger.debug(f"Initialized 'past_flow_delta' deque with maxlen {flow_recency_maxlen_cfg} for {symbol}.")

    # Ensure 'past_flow_gamma' deque exists with correct maxlen
    past_flow_gamma_deque = current_adaptive_historical_context.get("past_flow_gamma")
    if not isinstance(past_flow_gamma_deque, deque) or getattr(past_flow_gamma_deque, 'maxlen', None) != flow_recency_maxlen_cfg:
        current_adaptive_historical_context["past_flow_gamma"] = deque(maxlen=flow_recency_maxlen_cfg)
        hist_ctx_logger.debug(f"Initialized 'past_flow_gamma' deque with maxlen {flow_recency_maxlen_cfg} for {symbol}.")

    # Ensure 'past_iv_surfaces' deque exists with correct maxlen (stores dicts of IV context)
    past_iv_surfaces_deque = current_adaptive_historical_context.get("past_iv_surfaces")
    if not isinstance(past_iv_surfaces_deque, deque) or getattr(past_iv_surfaces_deque, 'maxlen', None) != surface_dynamics_maxlen_cfg:
        current_adaptive_historical_context["past_iv_surfaces"] = deque(maxlen=surface_dynamics_maxlen_cfg)
        hist_ctx_logger.debug(f"Initialized 'past_iv_surfaces' deque with maxlen {surface_dynamics_maxlen_cfg} for {symbol}.")

    # Ensure 'recent_atr_values' deque exists with correct maxlen
    recent_atr_values_deque = current_adaptive_historical_context.get("recent_atr_values")
    if not isinstance(recent_atr_values_deque, deque) or getattr(recent_atr_values_deque, 'maxlen', None) != perf_track_window_cfg:
        current_adaptive_historical_context["recent_atr_values"] = deque(maxlen=perf_track_window_cfg)
        hist_ctx_logger.debug(f"Initialized 'recent_atr_values' deque with maxlen {perf_track_window_cfg} for {symbol}.")

    # 1. Update Flow Snapshots (Using aggregated_strike_df for delta and gamma flows)
    if isinstance(aggregated_strike_df, pd.DataFrame) and not aggregated_strike_df.empty:
        # Ensure required columns for flow snapshots are present
        required_flow_cols = [strike_col_name_hist, proxy_delta_flow_col_hist, proxy_gamma_flow_col_hist]
        current_df_for_hist, cols_ok_hist = ensure_columns(aggregated_strike_df.copy(), # Work on a copy
                                                           required_flow_cols,
                                                           "HistFlowSnapshotInput", hist_ctx_logger)
        if cols_ok_hist:
            current_df_for_hist[strike_col_name_hist] = pd.to_numeric(current_df_for_hist[strike_col_name_hist], errors='coerce')
            current_df_for_hist.dropna(subset=[strike_col_name_hist], inplace=True) # Remove rows where strike is not numeric
            
            if not current_df_for_hist.empty:
                # Create Series for delta and gamma flows, indexed by strike
                current_delta_flow_snapshot = pd.to_numeric(current_df_for_hist.set_index(strike_col_name_hist)[proxy_delta_flow_col_hist], errors='coerce').fillna(0.0)
                current_adaptive_historical_context["past_flow_delta"].appendleft(current_delta_flow_snapshot.copy()) 
                
                current_gamma_flow_snapshot = pd.to_numeric(current_df_for_hist.set_index(strike_col_name_hist)[proxy_gamma_flow_col_hist], errors='coerce').fillna(0.0)
                current_adaptive_historical_context["past_flow_gamma"].appendleft(current_gamma_flow_snapshot.copy())
                hist_ctx_logger.debug(f"[{symbol}] Added delta/gamma flow snapshots to historical context.")
            else:
                 hist_ctx_logger.debug(f"[{symbol}] HistFlowSnapshot: DataFrame became empty after strike conversion/dropna for flow snapshots.")
        else:
            hist_ctx_logger.warning(f"[{symbol}] HistFlowSnapshot: Missing one or more required columns ({required_flow_cols}) in aggregated_strike_df. Flow snapshots not updated.")
    else:
        hist_ctx_logger.debug(f"[{symbol}] HistFlowSnapshot: aggregated_strike_df is empty or not a DataFrame. Flow snapshots not updated.")


    # 2. Update IV Surface Snapshots (Stores key IV context metrics over time)
    if isinstance(current_iv_context_snapshot, dict):
        # Construct a snapshot dict with relevant IV metrics
        iv_snapshot_data = {
            "timestamp": datetime.now().isoformat(), # Timestamp of this snapshot
            "current_iv": current_iv_context_snapshot.get("current_iv"), 
            "avg_iv_5day": current_iv_context_snapshot.get("avg_5day_iv_tradier_approx", current_iv_context_snapshot.get("avg_iv_5day")), # Check common key variations
            iv_context_percentile_key_hist: current_iv_context_snapshot.get(iv_context_percentile_key_hist) # e.g., "iv_percentile_30d"
        }
        current_adaptive_historical_context["past_iv_surfaces"].appendleft(iv_snapshot_data)
        hist_ctx_logger.debug(f"[{symbol}] Added IV context snapshot to historical context: {iv_snapshot_data}")

        # Store the most recent overall IV rank (percentile) directly for easier access by other modules
        current_iv_rank = iv_snapshot_data.get(iv_context_percentile_key_hist)
        if pd.notna(current_iv_rank):
             current_adaptive_historical_context["current_iv_rank"] = float(current_iv_rank)
        elif pd.notna(iv_snapshot_data["current_iv"]) and pd.notna(iv_snapshot_data["avg_iv_5day"]) and \
             isinstance(iv_snapshot_data["avg_iv_5day"], (int,float)) and iv_snapshot_data["avg_iv_5day"] > MIN_NORMALIZATION_DENOMINATOR_RSM:
            # Fallback IV rank estimate if percentile key is missing or invalid
            # Crude estimate: (current_iv / avg_iv - 0.5) / 1.5 + 0.5, scaled to roughly 0-1 range assuming current_iv can be 0.5x to 2x avg_iv
            crude_rank = (float(iv_snapshot_data["current_iv"]) / float(iv_snapshot_data["avg_iv_5day"]) - 0.5) / 1.5 + 0.5
            current_adaptive_historical_context["current_iv_rank"] = np.clip(crude_rank, 0.0, 1.0)
            hist_ctx_logger.debug(f"[{symbol}] Used fallback IV rank estimation: {current_adaptive_historical_context['current_iv_rank']:.3f}")
        else:
            current_adaptive_historical_context.pop("current_iv_rank", None) # Remove if not updatable
            hist_ctx_logger.debug(f"[{symbol}] Could not determine current_iv_rank from snapshot.")

    # 3. Update Recent ATR Values and Calculate Percentage Change
    if pd.notna(current_atr_value):
        current_adaptive_historical_context["recent_atr_values"].appendleft(float(current_atr_value)) # Newest is at index 0
        
        # Calculate ATR percentage change if enough history exists
        atr_history_list = list(current_adaptive_historical_context["recent_atr_values"])
        if len(atr_history_list) >= 2:
            # Newest ATR is atr_history_list[0] (which is current_atr_value)
            # Previous ATR is atr_history_list[1]
            prev_atr = atr_history_list[1] 
            if pd.notna(prev_atr) and prev_atr > MIN_NORMALIZATION_DENOMINATOR_RSM:
                current_adaptive_historical_context["recent_atr_pct_change"] = (float(current_atr_value) - prev_atr) / prev_atr
            else:
                current_adaptive_historical_context["recent_atr_pct_change"] = 0.0 # Previous ATR invalid for calc
                hist_ctx_logger.debug(f"[{symbol}] Previous ATR invalid ({prev_atr}) for pct_change calculation.")
        else:
            current_adaptive_historical_context["recent_atr_pct_change"] = 0.0 # Not enough history for pct_change
            hist_ctx_logger.debug(f"[{symbol}] Not enough ATR history ({len(atr_history_list)}) for pct_change calculation.")
    else: # current_atr_value is NaN
        current_adaptive_historical_context.pop("recent_atr_pct_change", None) # Remove if current ATR is invalid
        hist_ctx_logger.warning(f"[{symbol}] Current ATR value is NaN. Cannot update recent_atr_values or pct_change.")


    # 4. Placeholder for Performance Tracking (v2.3 stub - simply log new recommendations)
    if new_recommendations_this_cycle:
        # For v2.3, this is a simple log. Future versions might do more complex performance analysis.
        # Ensure 'recent_recommendations_log' deque exists
        recent_recs_log_deque = current_adaptive_historical_context.get("recent_recommendations_log")
        if not isinstance(recent_recs_log_deque, deque) or getattr(recent_recs_log_deque, 'maxlen', None) != (perf_track_window_cfg * 5): # Example longer history for recs
            current_adaptive_historical_context["recent_recommendations_log"] = deque(maxlen=(perf_track_window_cfg * 5)) # Store more recs than ATR values
            hist_ctx_logger.debug(f"Initialized 'recent_recommendations_log' deque for {symbol}.")
        
        # Add new recommendations to the left (newest)
        for rec in reversed(new_recommendations_this_cycle): # Add in order they were generated if multiple
             current_adaptive_historical_context["recent_recommendations_log"].appendleft(rec.copy()) # Store a copy
        hist_ctx_logger.debug(f"[{symbol}] Added {len(new_recommendations_this_cycle)} new recommendation(s) to historical context log.")

    # 5. Prepare a summary for the bundle (optional, but can be useful for quick access by other modules)
    current_adaptive_historical_context["summary_for_bundle"] = {
        "last_updated_ts": datetime.now().isoformat(),
        "last_atr": current_atr_value if pd.notna(current_atr_value) else None,
        "atr_pct_change": current_adaptive_historical_context.get("recent_atr_pct_change"),
        "current_iv_rank": current_adaptive_historical_context.get("current_iv_rank"),
        "num_past_flow_delta_snapshots": len(current_adaptive_historical_context.get("past_flow_delta", [])),
        "num_past_flow_gamma_snapshots": len(current_adaptive_historical_context.get("past_flow_gamma", [])),
        "num_past_iv_surface_snapshots": len(current_adaptive_historical_context.get("past_iv_surfaces", []))
    }

    hist_ctx_logger.info(f"Adaptive historical context successfully updated for symbol: {symbol}.")
    return current_adaptive_historical_context
