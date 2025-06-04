# core_analytics/adaptive_trade_framework_module.py
"""
Functions related to the Adaptive Trade Idea Framework (ATIF).
This 'enhanced v2.3' iteration provides a functional framework for generating
trade ideas by integrating signals and levels, selecting strategies, and
calculating basic entry/exit parameters. True adaptiveness and learning
are reserved for v2.5, but the structure is laid out.

Version: EOTS_ATIF_Module_v2.3.0_Canon_IDS_Unabridged
"""
import pandas as pd
import numpy as np
import logging
from typing import Union, Optional, List, Dict, Any, Deque, Tuple, Callable
from datetime import datetime, time, date
from collections import deque # Though not heavily used in this v2.3 version's logic

# --- Project-Specific Imports ---
try:
    from utils import ids
    from .system_utilities import map_score_to_stars, get_atr, ensure_columns # Added ensure_columns
    # For v2.3, get_enhanced_targets might come from fallback_recommendation_module
    from .fallback_recommendation_module import get_enhanced_targets_fallback

    IMPORTS_SUCCESSFUL = True
    logger_init = logging.getLogger(__name__)
    logger_init.info("Adaptive Trade Framework Module (v2.3.0 Canon): Core utilities and ids imported successfully.")
except ImportError as e_atif_imp:
    IMPORTS_SUCCESSFUL = False
    print(f"CRITICAL IMPORT ERROR in adaptive_trade_framework_module.py: {e_atif_imp}. ATIF calculations will fail or use dummies.")
    class ids: # type: ignore
        COL_STRIKE = "strike_price"; COL_LEVEL_TYPE = "level_type"; COL_LEVEL_STRENGTH = "strength_score" # Minimal for stubs
    def map_score_to_stars(score: Optional[Union[float, int]], default_stars: int = 0) -> int: return default_stars # type: ignore
    def get_atr(sym:str, price:float, cfg:Dict, hist:Optional[pd.DataFrame]=None, log_instance:Optional[logging.Logger]=None) -> float: return 0.01 * price if price else 0.5 # type: ignore
    def ensure_columns(df: pd.DataFrame, req_cols: List[str], name: str, log_instance: Optional[logging.Logger]=None) -> Tuple[pd.DataFrame, bool]: # type: ignore
        missing = [col for col in req_cols if col not in df.columns]; return df, not missing
    def get_enhanced_targets_fallback(*args: Any, **kwargs: Any) -> Dict[str, Optional[float]]: return {"target_1": None, "target_2": None, "stop_loss": None, "rationale": "Dummy Targets"} # type: ignore


# Module-level logger
logger = logging.getLogger(__name__)
if not IMPORTS_SUCCESSFUL:
    logger.critical("Adaptive Trade Framework Module running with DUMMY imports due to failure. Functionality will be severely limited.")

MIN_NORMALIZATION_DENOMINATOR_ATIF = 1e-9

# --- Helper Functions (Now Unabridged for v2.3) ---

def calculate_performance_based_conviction(
    signal_type: str,
    base_score: float, # Expected to be on a 0-5 scale (like stars)
    etif_perf_based_conviction_enabled_cfg: bool,
    etif_conv_perf_weight_cfg: float,
    historical_context: Optional[Dict] = None,
    log_instance: Optional[logging.Logger] = None
) -> float:
    """
    Adjusts a base conviction score. For v2.3, this is simplified:
    if performance-based conviction is disabled, it returns the base score.
    If enabled, it logs a warning that full performance adaptation is v2.5
    and returns the base score (or a very mild, non-adaptive adjustment for structure).
    """
    perf_conv_logger = log_instance.getChild("CalculatePerfBasedConviction_v2.3") if log_instance else logger.getChild("CalculatePerfBasedConviction_v2.3")

    if not etif_perf_based_conviction_enabled_cfg:
        perf_conv_logger.debug(f"Performance-based conviction disabled for signal '{signal_type}'. Returning base score: {base_score:.2f}")
        return base_score

    # For v2.3, true performance adaptation is out of scope.
    # We can simulate a minor, non-adaptive adjustment or simply return base_score.
    perf_conv_logger.warning(f"Signal '{signal_type}': Full performance-based conviction adaptation is a v2.5 feature. Using simplified v2.3 logic (minor adjustment or base score).")

    # Example of a very simple, non-adaptive adjustment if enabled:
    # This could be a placeholder for future, more complex logic.
    # For v2.3, let's make a minimal adjustment to show the structure is active.
    adjustment_factor = 1.0 # Neutral adjustment for v2.3
    if historical_context and isinstance(historical_context.get("signal_type_performance"), dict):
        signal_perf = historical_context["signal_type_performance"].get(signal_type, {})
        if isinstance(signal_perf.get("recent_accuracy"), (float, int)): # Example placeholder key
            perf_metric = np.clip(float(signal_perf["recent_accuracy"]), 0.0, 1.0)
            # Simple linear adjustment based on placeholder accuracy
            adjustment_factor = 1.0 + (perf_metric - 0.5) * (etif_conv_perf_weight_cfg * 0.2) # Reduced sensitivity for v2.3
            perf_conv_logger.debug(f"Found placeholder performance metric {perf_metric:.2f} for '{signal_type}'. Adjustment factor: {adjustment_factor:.3f}")

    adjusted_score = base_score * adjustment_factor
    final_score = np.clip(adjusted_score, 0.0, 5.0) # Assuming base_score was already 0-5

    perf_conv_logger.debug(f"Signal '{signal_type}': BaseScore={base_score:.2f} -> FinalScore={final_score:.2f} (v2.3 logic)")
    return final_score

def integrate_signals_with_levels(
    enhanced_signals_output: Dict,
    enhanced_levels_output: Dict,
    current_price: float,
    etif_min_composite_signal_score_for_idea_cfg: float, # Min signal strength to consider
    etif_min_level_strength_for_idea_cfg: float,     # Min level strength to consider
    level_relevance_proximity_atr_factor_cfg: float, # ATR factor for proximity
    current_atr_for_proximity: float,
    log_instance: Optional[logging.Logger] = None
) -> List[Dict]:
    """
    Combines strong signals with relevant (aligned and proximate) key levels
    to form preliminary trade setups for v2.3.
    """
    integrate_logger = log_instance.getChild("IntegrateSignalsWithLevels_v2.3") if log_instance else logger.getChild("IntegrateSignalsWithLevels_v2.3")
    preliminary_setups: List[Dict] = []

    if not isinstance(enhanced_signals_output, dict) or not isinstance(enhanced_levels_output, dict):
        integrate_logger.warning("Invalid signals or levels output provided. Cannot integrate.")
        return preliminary_setups

    all_levels = enhanced_levels_output.get("all_levels_sorted_by_strength", [])
    if not isinstance(all_levels, list) or not all_levels:
        integrate_logger.debug("No key levels provided to integrate with signals.")
        return preliminary_setups

    # Convert levels to a DataFrame for easier filtering if not already
    levels_df = pd.DataFrame(all_levels)
    if levels_df.empty or ids.COL_STRIKE not in levels_df.columns or ids.COL_LEVEL_TYPE not in levels_df.columns or ids.COL_LEVEL_STRENGTH not in levels_df.columns:
        integrate_logger.warning(f"Levels data is missing required columns ('{ids.COL_STRIKE}', '{ids.COL_LEVEL_TYPE}', '{ids.COL_LEVEL_STRENGTH}'). Cannot integrate.")
        return preliminary_setups

    levels_df[ids.COL_STRIKE] = pd.to_numeric(levels_df[ids.COL_STRIKE], errors='coerce')
    levels_df[ids.COL_LEVEL_STRENGTH] = pd.to_numeric(levels_df[ids.COL_LEVEL_STRENGTH], errors='coerce')
    levels_df.dropna(subset=[ids.COL_STRIKE, ids.COL_LEVEL_STRENGTH], inplace=True)


    proximity_threshold_value = current_atr_for_proximity * level_relevance_proximity_atr_factor_cfg
    integrate_logger.debug(f"Using proximity threshold: {proximity_threshold_value:.2f} (ATR: {current_atr_for_proximity:.2f}, Factor: {level_relevance_proximity_atr_factor_cfg})")

    # Iterate through signal categories (e.g., "directional", "sdag_conviction")
    for signal_category, category_data in enhanced_signals_output.items():
        if not isinstance(category_data, dict): continue
        for direction_label, signals_list in category_data.items(): # "bullish", "bearish"
            if not isinstance(signals_list, list): continue
            for signal_event in signals_list:
                if not isinstance(signal_event, dict): continue

                signal_strength = float(signal_event.get("base_conviction_score_signal_level", 0.0)) # Or other strength key
                signal_strike = pd.to_numeric(signal_event.get("strike_price_signal_level"), errors='coerce') # Or 'strike'

                if signal_strength < etif_min_composite_signal_score_for_idea_cfg:
                    continue # Signal not strong enough

                # Find relevant levels
                for _, level_row in levels_df.iterrows():
                    level_strike = level_row[ids.COL_STRIKE]
                    level_type = str(level_row[ids.COL_LEVEL_TYPE]).lower()
                    level_strength = level_row[ids.COL_LEVEL_STRENGTH]

                    if level_strength < etif_min_level_strength_for_idea_cfg:
                        continue # Level not strong enough

                    # Check alignment and proximity
                    is_aligned = (direction_label.lower() == "bullish" and level_type == "support") or \
                                 (direction_label.lower() == "bearish" and level_type == "resistance")

                    is_proximate = False
                    if pd.notna(signal_strike) and pd.notna(level_strike): # Signal is strike-specific
                        is_proximate = abs(signal_strike - level_strike) <= proximity_threshold_value
                    elif pd.notna(level_strike): # Signal is general, check level proximity to current price
                        is_proximate = abs(level_strike - current_price) <= proximity_threshold_value


                    if is_aligned and is_proximate:
                        # Simple combination for v2.3: average or weighted average
                        integrated_strength = (signal_strength + level_strength) / 2.0
                        setup_type = f"{direction_label.lower()}_signal_at_{level_type}_level"
                        preliminary_setups.append({
                            "type": setup_type,
                            "signal_data": signal_event,
                            "level_data": level_row.to_dict(),
                            "integrated_setup_strength": integrated_strength,
                            "primary_strike_focus": level_strike # The level's strike is the focus
                        })
                        integrate_logger.debug(f"Integrated setup: {setup_type} at strike {level_strike:.2f}, Strength: {integrated_strength:.2f}")

    return sorted(preliminary_setups, key=lambda x: x["integrated_setup_strength"], reverse=True)


def select_appropriate_options_strategies(
    setup_type: str,
    conviction_score: float, # The final ATIF conviction for this setup (0-5 scale)
    volatility_context: Optional[Dict], # Contains IV rank, VRI 2.0 info
    ticker_context: Optional[Dict], # Contains 0DTE flags, liquidity profile
    strategy_selection_rules_cfg: Dict[str, Any], # From config: "adaptive_trade_idea_framework_settings.strategy_selection_rules"
    log_instance: Optional[logging.Logger] = None
) -> List[Dict[str, Any]]:
    select_strat_logger = log_instance.getChild("SelectAppropriateStrategies_v2.3") if log_instance else logger.getChild("SelectAppropriateStrategies_v2.3")
    select_strat_logger.debug(f"Selecting strategy for setup '{setup_type}', conviction {conviction_score:.2f}")
    
    suggested_strategies: List[Dict[str, Any]] = []

    # For v2.3, use a simplified rule set from strategy_selection_rules_cfg
    # The config structure might be like:
    # "directional_bullish_high_conviction": { "min_conviction_stars": 3.5, "strategies": [{"name": "Long Call", "dte_range": [7,21], "delta_range": [0.4,0.7]}]}

    for rule_name, rule_details in strategy_selection_rules_cfg.items():
        if not isinstance(rule_details, dict): continue

        min_stars = float(rule_details.get("min_conviction_stars", 5.1)) # Default to a high value if not specified
        
        # Match setup_type (e.g., "directional_bullish" in rule_name should match if setup_type contains it)
        type_match = False
        if "directional_bullish" in rule_name.lower() and "bullish" in setup_type.lower(): type_match = True
        elif "directional_bearish" in rule_name.lower() and "bearish" in setup_type.lower(): type_match = True
        elif "vol_expansion" in rule_name.lower() and ("volatility" in setup_type.lower() or "expansion" in setup_type.lower()): type_match = True
        # Add more general matching if needed for v2.3

        if type_match and conviction_score >= min_stars:
            strategies_for_rule = rule_details.get("strategies", [])
            if isinstance(strategies_for_rule, list):
                for strat_detail in strategies_for_rule:
                    if isinstance(strat_detail, dict) and "name" in strat_detail:
                        suggested_strategies.append({
                            "name": str(strat_detail["name"]),
                            "target_dte_min": int(strat_detail.get("dte_range", [7, 30])[0]),
                            "target_dte_max": int(strat_detail.get("dte_range", [7, 30])[1]),
                            "target_delta_min": float(strat_detail.get("delta_range", [0.3, 0.7])[0]),
                            "target_delta_max": float(strat_detail.get("delta_range", [0.3, 0.7])[1]),
                            "source_rule": rule_name
                        })
                if suggested_strategies: # Found matching strategies for this rule
                    select_strat_logger.info(f"Matched rule '{rule_name}'. Suggested strategies: {[s['name'] for s in suggested_strategies]}")
                    return suggested_strategies # Return first set of matching strategies for simplicity in v2.3

    if not suggested_strategies: # Fallback if no specific rules matched
        select_strat_logger.debug(f"No specific strategy rule matched for '{setup_type}'. Using generic fallback.")
        if "bullish" in setup_type.lower():
            suggested_strategies.append({"name": "Long Call (ATM)", "target_dte_min": 7, "target_dte_max": 30, "target_delta_min": 0.45, "target_delta_max": 0.55, "source_rule": "Fallback Bullish"})
        elif "bearish" in setup_type.lower():
            suggested_strategies.append({"name": "Long Put (ATM)", "target_dte_min": 7, "target_dte_max": 30, "target_delta_min": -0.55, "target_delta_max": -0.45, "source_rule": "Fallback Bearish"})
        else: # Neutral or unclear
            suggested_strategies.append({"name": "Iron Condor (Neutral)", "target_dte_min": 14, "target_dte_max": 45, "target_delta_min": 0.10, "target_delta_max": 0.20, "source_rule": "Fallback Neutral"}) # Example

    return suggested_strategies


def calculate_optimized_entry_exit(
    strategy_name: str,
    primary_strike: float, # Primary strike associated with the idea (e.g., from level_data)
    current_price: float,
    current_atr: float,
    direction_label: str, # 'bullish' or 'bearish'
    get_enhanced_targets_func: Callable[..., Dict[str, Optional[float]]], # Expected: fallback_recommendation_module.get_enhanced_targets_fallback
    targets_config: Dict[str, Any], # From strategy_settings.targets
    support_levels_df: Optional[pd.DataFrame],
    resistance_levels_df: Optional[pd.DataFrame],
    strike_col_name_in_sr_df: str = ids.COL_STRIKE, # Default to standard strike column name
    log_instance: Optional[logging.Logger] = None
) -> Dict[str, Any]:
    optimize_logger = log_instance.getChild("CalculateOptimizedEntryExit_v2.3") if log_instance else logger.getChild("CalculateOptimizedEntryExit_v2.3")
    optimize_logger.debug(f"Calculating entry/exit for strategy '{strategy_name}', strike {primary_strike:.2f}, direction '{direction_label}'")

    if get_enhanced_targets_func is None:
        optimize_logger.error("get_enhanced_targets_func not provided. Cannot calculate targets/stops.")
        return {"entry_ideal": primary_strike, "stop_loss": None, "target_1": None, "target_2": None, "target_rationale": "Targeting function missing"}

    # Prepare arguments for get_enhanced_targets_fallback
    # It expects a dictionary of signal details, we can pass relevant parts
    signal_details_for_targets = {
        "strike": primary_strike, # The primary strike of the setup
        "direction_label": direction_label,
        "category": strategy_name # Use strategy name as category for targeting
    }

    targets_result = get_enhanced_targets_func(
        signal_details=signal_details_for_targets,
        current_price_for_targets=current_price,
        atr_for_targets=current_atr,
        targets_config_params=targets_config, # Pass the "targets" sub-dictionary from config
        support_df_for_targets=support_levels_df,
        resistance_df_for_targets=resistance_levels_df,
        strike_col_name_sr=strike_col_name_in_sr_df,
        log_instance=optimize_logger.getChild("EnhancedTargetsUtilCall")
    )

    return {
        "entry_ideal": round(primary_strike, 2) if pd.notna(primary_strike) else current_price, # Default entry to the level's strike
        "stop_loss": targets_result.get("stop_loss"),
        "target_1": targets_result.get("target_1"),
        "target_2": targets_result.get("target_2"),
        "target_rationale": targets_result.get("rationale", "Targets from Fallback Utility")
    }

def apply_spy_spx_optimizations(
    trade_ideas: List[Dict[str, Any]],
    sso_exp_calendar_enabled_cfg: bool,
    sso_exp_focus_dte_range_cfg: List[int],
    sso_exp_pin_risk_factor_cfg: float,
    sso_apply_behavior_patterns_cfg: bool,
    sso_behavior_pattern_confidence_thresh_cfg: float,
    sso_intraday_pattern_enabled_cfg: bool,
    sso_intraday_pattern_influence_cfg: float,
    sso_adjust_auction_impact_cfg: bool,
    sso_auction_impact_window_min_cfg: int,
    time_based_definitions_for_auction_cfg: Dict[str, str],
    map_score_to_stars_func_for_sso: Callable[[Optional[Union[float, int]]], int],
    min_stars_after_opt_cfg: int,
    current_time: Optional[time] = None,
    expiration_calendar: Optional[List[date]] = None,
    historical_context: Optional[Dict] = None, # For future behavioral patterns
    log_instance: Optional[logging.Logger] = None
) -> List[Dict[str, Any]]:
    sso_logger = log_instance.getChild("ApplySPYSPXOptimizations") if log_instance else logger.getChild("ApplySPYSPXOptimizations")
    if not trade_ideas: return []
    sso_logger.info(f"Applying SPY/SPX Optimizations to {len(trade_ideas)} trade ideas...")
    optimized_ideas: List[Dict] = []

    market_open_time_sso: Optional[time] = None
    market_close_time_sso: Optional[time] = None
    try:
        market_open_time_sso = datetime.strptime(time_based_definitions_for_auction_cfg.get("market_open","09:30:00"),"%H:%M:%S").time()
        market_close_time_sso = datetime.strptime(time_based_definitions_for_auction_cfg.get("market_close","16:00:00"),"%H:%M:%S").time()
    except ValueError:
        sso_logger.error("Invalid market open/close times in config for SPY/SPX auction logic. Skipping auction impact.")
        sso_adjust_auction_impact_cfg = False

    for idea in trade_ideas:
        original_conviction_sso = float(idea.get("raw_conviction_score_adaptive", idea.get("raw_conviction_score", 0.0)))
        current_adj_conviction_sso = original_conviction_sso
        adjustments_log_sso: List[str] = idea.get("sso_adjustments_log", []) # Preserve previous logs if any

        # 1. Expiration Calendar Integration
        if sso_exp_calendar_enabled_cfg and expiration_calendar and current_time:
            idea_dte_min_sso = idea.get("target_dte_min")
            is_expiry_day_for_idea_sso = False
            if isinstance(idea_dte_min_sso, int) and idea_dte_min_sso in sso_exp_focus_dte_range_cfg:
                today_date_sso = date.today()
                if any(exp_date_item == today_date_sso for exp_date_item in expiration_calendar if isinstance(exp_date_item, date)):
                    is_expiry_day_for_idea_sso = True
            if is_expiry_day_for_idea_sso:
                current_adj_conviction_sso *= sso_exp_pin_risk_factor_cfg
                adjustments_log_sso.append(f"ExpFocusPinRisk(Factor:{sso_exp_pin_risk_factor_cfg:.2f})")

        # 2. Apply SPY/SPX Behavioral Patterns (Placeholder for v2.3 - no change)
        if sso_apply_behavior_patterns_cfg:
            # In v2.5, this would involve complex pattern matching from historical_context
            adjustments_log_sso.append("SPXBehavior(v2.3_NoOp)")

        # 3. Intraday Pattern Adjustments (Placeholder for v2.3 - no change)
        if sso_intraday_pattern_enabled_cfg and current_time:
            adjustments_log_sso.append("IntradayPattern(v2.3_NoOp)")

        # 4. Adjust for Opening/Closing Auction Impact
        if sso_adjust_auction_impact_cfg and current_time and market_open_time_sso and market_close_time_sso:
            time_to_open_sec_sso = (datetime.combine(date.min, current_time) - datetime.combine(date.min, market_open_time_sso)).total_seconds()
            time_before_close_sec_sso = (datetime.combine(date.min, market_close_time_sso) - datetime.combine(date.min, current_time)).total_seconds()
            if (0 <= time_to_open_sec_sso <= sso_auction_impact_window_min_cfg * 60) or \
               (0 <= time_before_close_sec_sso <= sso_auction_impact_window_min_cfg * 60):
                auction_penalty_factor_sso = 0.90 # Example penalty
                current_adj_conviction_sso *= auction_penalty_factor_sso
                adjustments_log_sso.append(f"AuctionImpact(Penalty:{auction_penalty_factor_sso:.2f})")

        idea["raw_conviction_score_final_adj"] = round(current_adj_conviction_sso, 3)
        idea["conviction_stars"] = map_score_to_stars_func_for_sso(current_adj_conviction_sso)
        if adjustments_log_sso and "sso_adjustments_log" not in idea: # Avoid appending to same list multiple times if reprocessed
             idea["rationale"] = idea.get("rationale", "") + "; SPXOpt: " + ", ".join(list(set(adjustments_log_sso))) # Use set to avoid duplicate log entries
             idea["sso_adjustments_log"] = list(set(adjustments_log_sso))


        if idea["conviction_stars"] >= min_stars_after_opt_cfg:
            optimized_ideas.append(idea)
        else:
            sso_logger.info(f"Trade idea ID {idea.get('id')} filtered out after SPY/SPX optimizations (final stars: {idea['conviction_stars']} < {min_stars_after_opt_cfg}).")
    sso_logger.info(f"SPY/SPX Optimizations applied. {len(optimized_ideas)} ideas remain from {len(trade_ideas)}.")
    return optimized_ideas

# --- Main Orchestrator for Adaptive Trade Ideas ---
def generate_adaptive_trade_ideas_main(
    symbol_arg: str,
    enhanced_signals_output_arg: Dict,
    enhanced_levels_output_arg: Dict,
    current_price_arg: float,
    atr_arg: float,
    trade_idea_framework_cfg: Dict[str, Any], # Top-level ATIF config
    strategy_selection_cfg: Dict[str, Any],   # From ATIF.strategy_selection_rules
    recommendations_cfg_for_stars: Dict[str, Any], # From ATIF.conviction_mapping_params or strategy_settings.recommendations
    sso_config: Dict[str, Any], # From ATIF.spy_spx_optimizations
    time_defs_config_for_sso: Dict[str, str], # From market_regime_engine_settings.time_of_day_definitions
    map_score_to_stars_external_func: Callable[[Optional[Union[float, int]]], int],
    get_enhanced_targets_external_func: Callable[..., Dict[str, Optional[float]]], # Expected: fallback_recommendation_module.get_enhanced_targets_fallback
    current_recommendation_id_counter: int,
    current_time_arg: Optional[time] = None,
    volatility_context_arg: Optional[Dict] = None, # For v2.3, this might be basic IV info
    historical_context_arg: Optional[Dict] = None, # For v2.3, performance adaptation is off
    expiration_calendar_arg: Optional[List[date]] = None,
    log_instance: Optional[logging.Logger] = None
) -> Tuple[List[Dict[str, Any]], int]:
    ati_logger = log_instance.getChild("GenerateAdaptiveTradeIdeas_Main_v2.3") if log_instance else logger.getChild("GenerateAdaptiveTradeIdeas_Main_v2.3")
    ati_logger.info(f"Generating Trade Ideas for {symbol_arg} (v2.3 Orchestrator)...")
    final_trade_ideas_list: List[Dict[str, Any]] = []
    next_rec_id_counter = current_recommendation_id_counter

    # For v2.3, "adaptive_trade_generation" might be off, or its sub-components simplified.
    # We proceed assuming the structure is called, but internal logic is v2.3 appropriate.
    adaptive_trade_gen_cfg = trade_idea_framework_cfg.get("adaptive_trade_generation", {})
    etif_enabled = adaptive_trade_gen_cfg.get("enabled", False) # Check master ATIF toggle

    if not etif_enabled: # If ATIF itself is disabled in config, use fallback directly.
        ati_logger.info("Adaptive Trade Idea Generation (ATIF) is disabled by main config. Using Fallback Recommendation Module directly.")
        if hasattr(fallback_recommendation_module, 'get_strategy_recommendations_fallback'):
            # Pass necessary configs for fallback
            fallback_recs_cfg = trade_idea_framework_cfg.get("fallback_recommendation_settings", recommendations_cfg_for_stars) # Use ATIF's fallback or general recs
            fallback_targets_cfg = trade_idea_framework_cfg.get("fallback_target_settings", strategy_selection_cfg.get("targets", {}))

            final_trade_ideas_list, next_rec_id_counter = fallback_recommendation_module.get_strategy_recommendations_fallback( # type: ignore
                symbol_arg_fallback=symbol_arg,
                mspi_df_aggregated_fallback=pd.DataFrame(), # Fallback might not need full MSPI df, but signals/levels
                trading_signals_fallback=enhanced_signals_output_arg,
                support_levels_df_fallback=pd.DataFrame(enhanced_levels_output_arg.get("all_levels_sorted_by_strength", [])),
                resistance_levels_df_fallback=pd.DataFrame(enhanced_levels_output_arg.get("all_levels_sorted_by_strength", [])),
                current_price_fallback=current_price_arg,
                atr_fallback=atr_arg,
                recommendations_config_fallback=fallback_recs_cfg,
                targets_config_fallback=fallback_targets_cfg,
                map_score_to_stars_utility_func=map_score_to_stars_external_func,
                current_recommendation_id_counter_fallback=next_rec_id_counter,
                log_instance=ati_logger.getChild("FallbackRecsViaATIF")
            )
            ati_logger.info(f"Generated {len(final_trade_ideas_list)} ideas via Fallback directly as ATIF is disabled.")
            return final_trade_ideas_list, next_rec_id_counter
        else:
            ati_logger.error("ATIF disabled and Fallback Recommendation Module not available. No trade ideas generated.")
            return [], next_rec_id_counter


    # If ATIF is enabled, proceed with its (simplified for v2.3) logic
    etif_perf_based_conv_enabled = bool(adaptive_trade_gen_cfg.get("performance_based_conviction_enabled", False))
    etif_min_composite_score_idea = float(adaptive_trade_gen_cfg.get("min_composite_signal_score_for_idea", 0.4)) # Adjusted default
    etif_min_level_strength_idea = float(adaptive_trade_gen_cfg.get("min_level_strength_for_idea", 0.3)) # Adjusted default
    etif_conv_perf_weight = float(adaptive_trade_gen_cfg.get("conviction_performance_weight", 0.3)) # Adjusted default
    level_relevance_prox_atr_factor = float(strategy_selection_cfg.get("level_relevance_proximity_atr_factor", 0.5)) # Example path

    preliminary_setups_list = integrate_signals_with_levels(
        enhanced_signals_output_arg, enhanced_levels_output_arg, current_price_arg,
        etif_min_composite_score_idea, etif_min_level_strength_idea,
        level_relevance_prox_atr_factor, current_atr_for_proximity=atr_arg,
        log_instance=ati_logger
    )
    ati_logger.debug(f"Generated {len(preliminary_setups_list)} preliminary setups.")

    all_levels_df_for_targets = pd.DataFrame(enhanced_levels_output_arg.get("all_levels_sorted_by_strength", []))
    support_df_for_targets = pd.DataFrame()
    resistance_df_for_targets = pd.DataFrame()
    if not all_levels_df_for_targets.empty and ids.COL_LEVEL_TYPE in all_levels_df_for_targets.columns:
        support_df_for_targets = all_levels_df_for_targets[all_levels_df_for_targets[ids.COL_LEVEL_TYPE] == 'support'].copy()
        resistance_df_for_targets = all_levels_df_for_targets[all_levels_df_for_targets[ids.COL_LEVEL_TYPE] == 'resistance'].copy()

    for setup_item in preliminary_setups_list:
        signal_data_item = setup_item.get("signal_data", {})
        level_data_item = setup_item.get("level_data", {})
        setup_type_str = setup_item.get("type", "unknown_setup")
        integrated_setup_strength_val = setup_item.get("integrated_setup_strength", 0.0)
        base_score_for_conv_calc = integrated_setup_strength_val * 5.0

        conviction_score_after_perf_val = calculate_performance_based_conviction(
            signal_type=signal_data_item.get('type', 'generic_signal'),
            base_score=base_score_for_conv_calc,
            etif_perf_based_conviction_enabled_cfg=etif_perf_based_conv_enabled,
            etif_conv_perf_weight_cfg=etif_conv_perf_weight,
            historical_context=historical_context_arg,
            log_instance=ati_logger
        )
        final_stars_val = map_score_to_stars_external_func(conviction_score_after_perf_val)

        min_stars_to_issue_cfg = int(recommendations_cfg_for_stars.get("min_directional_stars_to_issue", 2))
        if final_stars_val < min_stars_to_issue_cfg:
            ati_logger.debug(f"Setup '{setup_type_str}' skipped due to low conviction: {final_stars_val} stars < {min_stars_to_issue_cfg}.")
            continue

        suggested_strats_list = select_appropriate_options_strategies(
            setup_type_str, conviction_score_after_perf_val, volatility_context_arg, historical_context_arg, # Pass hist_ctx as ticker_ctx for v2.3
            strategy_selection_rules_cfg=strategy_selection_cfg, # Pass the whole sub-dict
            log_instance=ati_logger
        )
        if not suggested_strats_list: continue

        direction_for_targets_str = "bullish" if "bullish" in setup_type_str.lower() else ("bearish" if "bearish" in setup_type_str.lower() else "neutral")
        primary_strike_for_targets = float(level_data_item.get(ids.COL_STRIKE, current_price_arg))


        entry_exit_params_dict = calculate_optimized_entry_exit(
            strategy_name=suggested_strats_list[0].get("name", "UnknownStrategy"),
            primary_strike=primary_strike_for_targets,
            current_price=current_price_arg,
            current_atr=atr_arg,
            direction_label=direction_for_targets_str,
            get_enhanced_targets_func=get_enhanced_targets_fallback, # Explicitly use fallback for v2.3
            targets_config=self._get_config_value(["strategy_settings", "targets"], {}), # Use general targets config
            support_levels_df=support_df_for_targets,
            resistance_levels_df=resistance_df_for_targets,
            strike_col_name_in_sr_df=ids.COL_STRIKE,
            log_instance=ati_logger
        )

        next_rec_id_counter += 1
        rec_id_str = f"AREC_{symbol_arg[:3].upper()}{next_rec_id_counter:03d}"

        trade_idea_dict = {
            "id": rec_id_str, "symbol": symbol_arg, "timestamp": datetime.now().isoformat(),
            "category": f"ATIF_{setup_type_str.split('_')[0].capitalize()}", # Simplified category
            "signal_type_source": signal_data_item.get('type', 'unknown_signal_source'),
            "strike": primary_strike_for_targets,
            "direction_label": direction_for_targets_str.capitalize(),
            "strategy_suggestions": [s.get("name") for s in suggested_strats_list if s.get("name")],
            "target_dte_min": suggested_strats_list[0].get("target_dte_min"),
            "target_dte_max": suggested_strats_list[0].get("target_dte_max"),
            "target_delta_min": suggested_strats_list[0].get("target_delta_min"),
            "target_delta_max": suggested_strats_list[0].get("target_delta_max"),
            "conviction_stars": final_stars_val,
            "raw_conviction_score_adaptive": round(conviction_score_after_perf_val, 3),
            "status": "NEW_CANDIDATE_ATIF_V2.3", **entry_exit_params_dict,
            "rationale": f"ATIF v2.3 Signal: {signal_data_item.get('type','N/A')[:25]} at Level: {level_data_item.get(ids.COL_STRIKE, 'N/A')} ({level_data_item.get(ids.COL_LEVEL_TYPE,'N/A')}, Str: {level_data_item.get(ids.COL_LEVEL_STRENGTH,0):.2f}). PerfConv: {conviction_score_after_perf_val:.2f}.",
            "underlying_price_at_signal": current_price_arg, "atr_at_signal": atr_arg,
            "source_signal_detail": {k:v for k,v in signal_data_item.items() if isinstance(v, (int,float,str,bool))},
            "source_level_detail": {k:v for k,v in level_data_item.items() if isinstance(v, (int,float,str,bool))}
        }
        final_trade_ideas_list.append(trade_idea_dict)
        ati_logger.debug(f"Generated ATIF v2.3 Trade Idea ID {rec_id_str} for {symbol_arg}.")

    if symbol_arg.upper() in ["SPY", "SPX", "/ES", "/ES:XCME"] and sso_config.get("enabled", False):
        final_trade_ideas_list = apply_spy_spx_optimizations(
            trade_ideas=final_trade_ideas_list,
            sso_exp_calendar_enabled_cfg=bool(sso_config.get("expiration_calendar_integration_enabled", False)),
            sso_exp_focus_dte_range_cfg=sso_config.get("expiration_focus_dte_range", [0,1,2]),
            sso_exp_pin_risk_factor_cfg=float(sso_config.get("expiration_pin_risk_sensitivity_factor", 1.2)),
            sso_apply_behavior_patterns_cfg=bool(sso_config.get("apply_spy_spx_behavior_patterns", False)),
            sso_behavior_pattern_confidence_thresh_cfg=float(sso_config.get("behavior_pattern_confidence_threshold", 0.65)),
            sso_intraday_pattern_enabled_cfg=bool(sso_config.get("intraday_pattern_recognition_enabled", False)),
            sso_intraday_pattern_influence_cfg=float(sso_config.get("intraday_pattern_influence_factor", 0.15)),
            sso_adjust_auction_impact_cfg=bool(sso_config.get("adjust_for_auction_impact", True)),
            sso_auction_impact_window_min_cfg=int(sso_config.get("auction_impact_time_window_minutes", 15)),
            time_based_definitions_for_auction_cfg=time_defs_config_for_sso,
            map_score_to_stars_func_for_sso=map_score_to_stars_external_func,
            min_stars_after_opt_cfg=int(recommendations_cfg_for_stars.get("min_directional_stars_to_issue", 2)),
            current_time=current_time_arg,
            expiration_calendar=expiration_calendar_arg,
            historical_context=historical_context_arg,
            log_instance=ati_logger
        )

    ati_logger.info(f"Generated {len(final_trade_ideas_list)} final trade ideas for {symbol_arg} (v2.3 Orchestrator).")
    return final_trade_ideas_list, next_rec_id_counter

