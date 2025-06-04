# core_analytics/config_utils.py
# Version: EOTS_ConfigUtils_v2.3.0_Canon_IDS_Unabridged
"""
Configuration loading and utility functions for the IntegratedTradingSystem.
This module defines the default configuration structure expected by the ITS
and provides functions to load and merge external configurations, fully
integrating with ids.py for default column names and configuration keys.
"""
import json
import os
import logging
import copy # For deepcopy
import sys # For fallback ids import check
from typing import Optional, List, Dict, Any
from datetime import datetime

# --- Project-Specific Imports ---
try:
    from utils import ids
    IMPORTS_SUCCESSFUL = True
    logger_init = logging.getLogger(__name__)
    logger_init.info("Config Utils (v2.3.0 Canon): 'ids.py' imported successfully.")
except ImportError as e_config_utils_imp:
    IMPORTS_SUCCESSFUL = False
    print(f"CRITICAL IMPORT ERROR in config_utils.py: {e_config_utils_imp}. Config utils will use placeholder ids.")
    class ids: # type: ignore
        # Minimal set of ids for DEFAULT_CONFIG structure if main ids.py fails
        COL_STRIKE = "strike_price"; COL_GXOI_CONTRACT = "gxoi"; COL_DXOI_CONTRACT = "dxoi"
        COL_CHARMXOI_CONTRACT = "charmxoi"; COL_TXOI_CONTRACT = "txoi"; COL_VANNAXOI_CONTRACT = "vannaxoi"
        COL_VXOI_CONTRACT = "vxoi"; COL_VOMMAXOI_CONTRACT = "vommaxoi"; COL_VOLATILITY_OPTION_CONTRACT = "volatility"
        COL_VOLUME_OPTION_CONTRACT = "volm"; CV_UND_PARAM_PRICE = "price"; CV_UND_PARAM_VOLATILITY = "volatility"
        CV_UND_PARAM_IV_PERCENTILE_30D = "iv_percentile_30d" # Example
        COL_MSPI_SCORE = "mspi"; COL_A_DAG_OUTPUT = "a_dag"; COL_A_DAG_NORM = "a_dag_norm"
        COL_D_TDPI_OUTPUT = "d_tdpi"; COL_D_TDPI_NORM = "d_tdpi_norm"; COL_VRI_2_0_OUTPUT = "vri_2_0"
        COL_VRI_2_0_NORM = "vri_2_0_norm"; COL_E_SDAG_COMPOSITE_OUTPUT = "e_sdag_composite"
        COL_E_SDAG_COMPOSITE_NORM = "e_sdag_composite_norm"; COL_SDAG_CONVICTION_SCORE = "sdag_conviction_score"
        COL_E_SDAG_SKEW_ADJUSTED_GEX = "e_sdag_skew_adjusted_gex"
        # Config path constants (these are lists of strings)
        CFG_SYSTEM_LOG_LEVEL = ["system_settings", "log_level"]
        CFG_SYSTEM_DF_HISTORY_MAXLEN = ["system_settings", "df_history_maxlen_its"]
        CFG_METRICS_CALC_STRIKE_COL_INTERNAL = ["metrics_calculator_v2_5_settings", "strike_column_name_internal"]
        CFG_METRICS_CALC_GAMMA_COL_KEY = ["metrics_calculator_v2_5_settings", "gamma_exposure_source_col_config_key"]
        CFG_METRICS_CALC_DELTA_COL_KEY = ["metrics_calculator_v2_5_settings", "delta_exposure_source_col_config_key"]
        CFG_METRICS_CALC_OPT_IV_COL_KEY = ["metrics_calculator_v2_5_settings", "option_iv_source_col_config_key"]
        CFG_METRICS_CALC_OPT_PRICE_COL_KEY = ["metrics_calculator_v2_5_settings", "option_price_source_col_config_key"] # Assuming this key exists
        CFG_METRICS_CALC_UND_PRICE_KEY = ["metrics_calculator_v2_5_settings", "underlying_price_source_key_in_und_data"]
        CFG_METRICS_CALC_CHARM_COL_KEY = ["metrics_calculator_v2_5_settings", "charm_exposure_source_col_config_key"]
        CFG_METRICS_CALC_THETA_COL_KEY = ["metrics_calculator_v2_5_settings", "theta_exposure_source_col_config_key"]
        CFG_METRICS_CALC_VANNA_COL_KEY = ["metrics_calculator_v2_5_settings", "vanna_exposure_source_col_config_key"]
        CFG_METRICS_CALC_VEGA_COL_KEY = ["metrics_calculator_v2_5_settings", "vega_exposure_source_col_config_key"]
        CFG_METRICS_CALC_VOMMA_COL_KEY = ["metrics_calculator_v2_5_settings", "vomma_exposure_source_col_config_key"]
        CFG_METRICS_CALC_VOLM_COL_KEY = ["metrics_calculator_v2_5_settings", "volume_source_col_config_key"]
        CFG_METRICS_CALC_ADAPTIVE_ADAG_SETTINGS = ["metrics_calculator_v2_5_settings", "adaptive_metric_params", "a_dag_settings"]
        CFG_METRICS_CALC_ADAPTIVE_ADAG_BASE_ALPHA = CFG_METRICS_CALC_ADAPTIVE_ADAG_SETTINGS + ["base_dag_alpha_coeffs"]
        CFG_METRICS_CALC_ADAPTIVE_ADAG_DTE_SCALING = CFG_METRICS_CALC_ADAPTIVE_ADAG_SETTINGS + ["dte_gamma_flow_impact_scaling"]
        CFG_METRICS_CALC_ADAPTIVE_DTDPI_SETTINGS = ["metrics_calculator_v2_5_settings", "adaptive_metric_params", "d_tdpi_settings"]
        CFG_METRICS_CALC_ADAPTIVE_DTDPI_BASE_BETA = CFG_METRICS_CALC_ADAPTIVE_DTDPI_SETTINGS + ["base_tdpi_beta_coeffs"]
        CFG_METRICS_CALC_ADAPTIVE_DTDPI_BASE_GAUSS = CFG_METRICS_CALC_ADAPTIVE_DTDPI_SETTINGS + ["base_tdpi_gaussian_width"]
        CFG_METRICS_CALC_ADAPTIVE_VRI2_SETTINGS = ["metrics_calculator_v2_5_settings", "adaptive_metric_params", "vri_2_0_settings"]
        CFG_METRICS_CALC_ADAPTIVE_VRI2_BASE_GAMMA = CFG_METRICS_CALC_ADAPTIVE_VRI2_SETTINGS + ["base_vri_gamma_coeffs"]
        CFG_METRICS_CALC_VRI_VOL_TREND_FALLBACK = CFG_METRICS_CALC_ADAPTIVE_VRI2_SETTINGS + ["vol_trend_fallback_factor"] # Example, adjust path
        CFG_METRICS_CALC_ATR_FALLBACK = ["metrics_calculator_v2_5_settings", "atr_calculation_params", "fallback_settings"]
        CFG_MARKET_REGIME_TIME_DEFS = ["market_regime_engine_settings", "time_of_day_definitions"]

# --- Module-Specific Logger ---
logger = logging.getLogger(__name__)
if not IMPORTS_SUCCESSFUL:
    logger.critical("Config Utils module running with DUMMY 'ids' import. Functionality will be based on limited fallbacks.")
logger.info("core_analytics.config_utils.py (Version: EOTS_ConfigUtils_v2.3.0_Canon_IDS_Unabridged): Logger initialized.")


# --- Canonical Default Configuration for IntegratedTradingSystem (v2.3 Focus) ---
DEFAULT_CONFIG: Dict[str, Any] = {
    "module_version_its_default": "ITS_Default_Config_v2.3.0_Canon",
    "system_settings": {
        "log_level": "INFO",
        "df_history_maxlen_its": 10,
        "signal_activation_v2_3": { # v2.3 specific signal activation
            "master_enable_all_raw_signals": True,
            "directional": True, "sdag_conviction": True,
            "volatility_expansion": True, "volatility_contraction": True,
            "time_decay_pin_risk": True, "time_decay_charm_cascade": True,
            "complex_structure_change": True, "complex_flow_divergence": True
        },
        # Adaptive settings are conceptually v2.5 but can have defaults
        "adaptive_settings": {"enabled": False, "performance_tracking_window": 20, "learning_rate": 0.01}
    },
    "metrics_calculator_v2_5_settings": { # Naming kept for compatibility, content is v2.3 focused
        "strike_column_name_internal": ids.COL_STRIKE,
        "gamma_exposure_source_col_config_key": ids.COL_GXOI_CONTRACT,
        "delta_exposure_source_col_config_key": ids.COL_DXOI_CONTRACT,
        "charm_exposure_source_col_config_key": ids.COL_CHARMXOI_CONTRACT,
        "theta_exposure_source_col_config_key": ids.COL_TXOI_CONTRACT,
        "vanna_exposure_source_col_config_key": ids.COL_VANNAXOI_CONTRACT,
        "vega_exposure_source_col_config_key": ids.COL_VXOI_CONTRACT,
        "vomma_exposure_source_col_config_key": ids.COL_VOMMAXOI_CONTRACT,
        "option_iv_source_col_config_key": ids.COL_VOLATILITY_OPTION_CONTRACT,
        "volume_source_col_config_key": ids.COL_VOLUME_OPTION_CONTRACT,
        "option_price_source_col_config_key": ids.COL_PRICE_OPTION_CONTRACT, # Option's own price
        "underlying_price_source_key_in_und_data": ids.CV_UND_PARAM_PRICE,
        "current_iv_source_key_in_und_data": ids.CV_UND_PARAM_VOLATILITY, # For current underlying IV
        "iv_rank_30d_source_key_in_und_data": ids.CV_UND_PARAM_IV_PERCENTILE_30D, # Example, may not be in CV direct
        "avg_5day_iv_source_key_in_und_data": "avg_5day_iv_tradier_approx", # Example, from Tradier
        "avg_90day_iv_source_key_in_und_data": "avg_iv_90day_tradier_approx", # Example
        "historical_atr_value_source_key_in_und_data": "atr_14d_current_value", # Example

        "atr_calculation_params": {
            "period": 14,
            "fallback_settings": {"type": "percentage_of_price", "percentage": 0.015, "min_value": 0.50}
        },
        # Adaptive metric params are included for structure but will be disabled for v2.3 by ITS flags
        "adaptive_metric_params": {
            "a_dag_settings": {"base_dag_alpha_coeffs": {"aligned": 1.3, "opposed": 0.7, "neutral": 1.0}, "dte_gamma_flow_impact_scaling": {"0DTE": 1.2, "1-7DTE": 1.0, ">30DTE": 0.8}, "temporal_decay_factor_flow": 0.9, "volume_weight_factor_gex": 0.2, "flow_recency_half_life_periods": 3, "vol_regime_sensitivity": 0.5},
            "e_sdag_settings": {"use_enhanced_skew_calculation_for_sgexoi": False, "sgexoi_calculation_params": {"skew_sensitivity_to_vri2": 0.1, "enhanced_gex_output_col_name": ids.COL_E_SDAG_SKEW_ADJUSTED_GEX}, "methodology_weights_initial": {"multiplicative": 0.25, "directional": 0.25, "weighted": 0.25, "volatility_focused": 0.25}, "performance_adaptation_enabled": False, "min_agreement_for_conviction_bonus": 3},
            "d_tdpi_settings": {"base_tdpi_beta_coeffs": {"aligned": 1.2, "opposed": 0.8, "neutral": 1.0}, "base_tdpi_gaussian_width": -0.5, "adaptive_time_weighting_enabled": False, "regime_time_weight_profiles": {}, "dynamic_gaussian_width_enabled": False, "gaussian_width_vol_sensitivity": 0.05, "gaussian_width_range": [-0.75, -0.25], "expiration_clustering_dte_lookaround": 1, "expiration_clustering_sensitivity": 1.05, "charm_acceleration_sensitivity": 1.0, "charm_acceleration_lookback_periods": 2},
            "vri_2_0_settings": {"base_vri_gamma_coeffs": {"aligned": 1.2, "opposed": 0.8, "neutral": 1.0}, "term_structure_integration_params": {"slope_weight": 0.1}, "volatility_surface_dynamics_params": {"surface_change_sensitivity": 0.1}, "vomma_enhancement_params": {"enhancement_factor": 1.1}, "adaptive_iv_thresholds_enabled": False}
        }
    },
    "strategy_settings": {
        "mspi_col_name_in_aggregated_df": ids.COL_MSPI_SCORE, # How ITS refers to its main output
        "dag_methodologies": { # For original SDAGs (v2.3)
            "enabled": ["multiplicative", "directional", "weighted", "volatility_focused"],
            "use_skew_adjusted_gex_for_original_sdags": False, # v2.3 typically uses raw GEX for original SDAGs
            "skew_adjusted_gex_source_col_name": "sgxoi", # Fallback if above is true
            "multiplicative": {"delta_weight_factor": 0.5}, "directional": {"delta_weight_factor": 0.5},
            "weighted": {"w1_gamma":0.6, "w2_delta":0.4}, "volatility_focused": {"delta_weight_factor": 0.5}
        },
        "recommendations": { # For fallback_recommendation_module.py
            "min_directional_stars_to_issue": 2,
            "conviction_map_high": 0.75, "conviction_map_high_medium": 0.55,
            "conviction_map_medium": 0.35, "conviction_map_medium_low": 0.15,
            "conviction_map_base_one_star": 0.05
        },
        "targets": { # For fallback_recommendation_module.py
            "target_atr_stop_loss_multiplier": 1.5,
            "target_atr_target1_multiplier_no_sr": 1.5,
            "target_atr_target2_multiplier_no_sr": 3.0,
            "target_atr_target2_multiplier_from_t1": 1.8,
            "min_target_atr_distance": 0.5
        }
    },
    "enhanced_metrics": { # Defines ITS output column names for enhanced metrics (disabled for v2.3)
        "enabled": False,
        "a_dag": {"enabled": False, "output_column_name": ids.COL_A_DAG_OUTPUT, "norm_column_name": ids.COL_A_DAG_NORM},
        "e_sdag": {"enabled": False, "composite_output_column_name": ids.COL_E_SDAG_COMPOSITE_OUTPUT, "composite_norm_column_name": ids.COL_E_SDAG_COMPOSITE_NORM, "conviction_score_output_col_name": ids.COL_SDAG_CONVICTION_SCORE},
        "d_tdpi": {"enabled": False, "output_column_name": ids.COL_D_TDPI_OUTPUT, "norm_column_name": ids.COL_D_TDPI_NORM},
        "vri_2_0": {"enabled": False, "output_column_name": ids.COL_VRI_2_0_OUTPUT, "norm_column_name": ids.COL_VRI_2_0_NORM}
    },
    # The following sections are more v2.5 but included for structural completeness of ITS defaults.
    # Their specific values would be overridden by the main config_v2.json.
    "key_level_identifier_settings": {"multi_timeframe_analysis_enabled": True, "dynamic_mspi_base_threshold_for_intraday": 0.3},
    "signal_generator_v2_5_settings": {"adaptive_directional_params": { "base_min_stars_for_signal": 2.0 }},
    "adaptive_trade_idea_framework_settings": {"min_overall_conviction_to_generate_idea": 3}, # High default if ATIF is accidentally on for v2.3
    "trade_parameter_optimizer_settings": {"stop_loss_params": {"base_atr_multiplier": 1.5}},
    "validation": { "required_top_level_sections": ["system_settings", "metrics_calculator_v2_5_settings", "strategy_settings"]}
}

def deep_merge_dicts(base_dict: Dict[Any, Any], updates_dict: Dict[Any, Any]) -> Dict[Any, Any]:
    """
    Recursively merges updates_dict into base_dict.
    If a key exists in both and both values are dicts, it merges them.
    Otherwise, the value from updates_dict overwrites the value in base_dict.
    This function returns a new dictionary and does not modify inputs.
    """
    merged = copy.deepcopy(base_dict)
    for key, value_from_updates in updates_dict.items():
        if isinstance(value_from_updates, dict) and key in merged and isinstance(merged[key], dict):
            merged[key] = deep_merge_dicts(merged[key], value_from_updates)
        else:
            merged[key] = copy.deepcopy(value_from_updates)
    return merged

def load_and_validate_config(
    config_path: Optional[str], # Made optional; if None, only default_config_data is used
    default_config_data: Dict[str, Any],
    log_instance: Optional[logging.Logger] = None
) -> Dict[str, Any]:
    """
    Loads a JSON configuration file, deeply merges it over the provided default_config_data,
    and performs validation based on the 'validation' section of the *final merged* config.
    """
    config_loader_logger = log_instance.getChild("LoadAndValidateConfig_ITS_v2.3") if log_instance else logger.getChild("LoadAndValidateConfig_ITS_v2.3")
    config_loader_logger.info(f"ITS Config: Attempting to load and validate. Provided path: '{config_path}'")

    final_effective_config = copy.deepcopy(default_config_data)
    final_effective_config["_config_source_default_its"] = True

    absolute_config_file_path_to_try: Optional[str] = None
    if config_path: # Only attempt to load if a path is provided
        if os.path.isabs(config_path):
            absolute_config_file_path_to_try = config_path
        else:
            path_rel_to_cwd = os.path.join(os.getcwd(), config_path)
            if os.path.exists(path_rel_to_cwd):
                absolute_config_file_path_to_try = path_rel_to_cwd
            else:
                try: script_dir = os.path.dirname(os.path.abspath(__file__))
                except NameError: script_dir = os.getcwd()
                path_rel_to_script = os.path.join(script_dir, config_path)
                if os.path.exists(path_rel_to_script): absolute_config_file_path_to_try = path_rel_to_script
                else: absolute_config_file_path_to_try = os.path.abspath(config_path) # Last resort abspath
        config_loader_logger.debug(f"ITS Config: Resolved path to try: '{absolute_config_file_path_to_try}'")

    loaded_external_config: Optional[Dict[str, Any]] = None
    if absolute_config_file_path_to_try and os.path.exists(absolute_config_file_path_to_try):
        try:
            with open(absolute_config_file_path_to_try, 'r', encoding='utf-8') as f_external_cfg:
                loaded_external_config = json.load(f_external_cfg)
            if isinstance(loaded_external_config, dict):
                config_loader_logger.info(f"ITS Config: Successfully loaded external configuration from: {absolute_config_file_path_to_try}")
                final_effective_config = deep_merge_dicts(final_effective_config, loaded_external_config)
                final_effective_config["_config_source_default_its"] = False
                final_effective_config["_config_file_path"] = absolute_config_file_path_to_try
                config_loader_logger.info("ITS Config: External configuration deeply merged with ITS defaults.")
            else:
                config_loader_logger.warning(f"ITS Config: External file at '{absolute_config_file_path_to_try}' not a valid JSON dictionary. Using defaults.")
        except json.JSONDecodeError as e_json_ext:
            config_loader_logger.error(f"ITS Config: Error decoding JSON from '{absolute_config_file_path_to_try}': {e_json_ext}. Using defaults.", exc_info=True)
        except Exception as e_load_ext:
            config_loader_logger.error(f"ITS Config: Unexpected error loading '{absolute_config_file_path_to_try}': {e_load_ext}. Using defaults.", exc_info=True)
    elif config_path: # A path was given, but file not found
        config_loader_logger.warning(f"ITS Config: External config file '{config_path}' (resolved to '{absolute_config_file_path_to_try}') not found. Using defaults.")
    else: # No path provided, just use defaults
        config_loader_logger.info("ITS Config: No external config path provided. Using internal defaults.")


    validation_block = final_effective_config.get("validation", {})
    if not isinstance(validation_block, dict): validation_block = {}

    required_sections = validation_block.get("required_top_level_sections", [])
    if not isinstance(required_sections, list): required_sections = []

    missing_sections: List[str] = [s for s in required_sections if s not in final_effective_config]
    if missing_sections:
        final_effective_config["_its_config_validation_status"] = f"FAILED_MISSING_SECTIONS: {missing_sections}"
        config_loader_logger.error(f"ITS Config Validation CRITICAL: Missing required sections: {missing_sections}")
    else:
        final_effective_config["_its_config_validation_status"] = "PASSED (Required Sections Present)"
        config_loader_logger.info("ITS Config: Validation for required top-level sections passed.")

    final_effective_config["_config_load_timestamp_its_util"] = datetime.now().isoformat()
    config_loader_logger.info(f"ITS Config: Final effective version: {final_effective_config.get('version', final_effective_config.get('module_version_its_default', 'N/A_ITS_VERSION'))}")
    return final_effective_config

