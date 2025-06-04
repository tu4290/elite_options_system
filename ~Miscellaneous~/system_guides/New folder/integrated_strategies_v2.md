# integrated_strategies_v2.py
# (Elite Version 2.4.1 - Stateful - Initialization & Config Fully Fleshed)

# --- Standard & Third-Party Imports ---
import json
import traceback
import logging
import os
from datetime import datetime, time, date, timedelta
from typing import Dict, Optional, Tuple, Any, List, Union, Deque
from collections import deque
import pandas as pd
import numpy as np

# --- Module-Specific Logger ---
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] (%(name)s:%(lineno)d) %(asctime)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# --- Helper Constants ---
MIN_NORMALIZATION_DENOMINATOR: float = 1e-9
DEFAULT_ATR_FALLBACK_MIN_VALUE: float = 1.0
DEFAULT_ATR_FALLBACK_PERCENTAGE: float = 0.005
# These NET_ constants are illustrative if used by other methods, not directly in __init__
NET_VOLUME_PRESSURE_COL: str = "net_volume_pressure"
NET_VALUE_PRESSURE_COL: str = "net_value_pressure"

# --- Default Configuration (Fully Written Out) ---
DEFAULT_CONFIG: Dict[str, Any] = {
  "version": "2.4.1-EliteSchema-Stateful-FullConfig-ProductionReady",
  "system_settings": {
    "log_level": "INFO",
    "df_history_maxlen": 5,
    "signal_activation": {
      "directional": True, "volatility_expansion": True, "volatility_contraction": True,
      "time_decay_pin_risk": True, "time_decay_charm_cascade": True,
      "complex_structure_change": True, "complex_flow_divergence": True,
      "complex_sdag_conviction": True
    }
  },
  "data_processor_settings": {
    "weights": {
      "selection_logic": "time_based",
      "time_based": {
        "morning": {"dag_custom": 0.3, "tdpi": 0.2, "vri": 0.2, "sdag_multiplicative_norm": 0.1, "sdag_weighted_norm": 0.1, "sdag_volatility_focused_norm": 0.1},
        "midday": {"dag_custom": 0.3, "tdpi": 0.3, "vri": 0.2, "sdag_multiplicative_norm": 0.2},
        "final": {"dag_custom": 0.2, "tdpi": 0.4, "vri": 0.2, "sdag_multiplicative_norm": 0.2}
      },
      "volatility_based": {
        "iv_percentile_threshold": 50,
        "low_iv": {"dag_custom": 0.45, "tdpi": 0.2, "vri": 0.15, "sdag_multiplicative_norm": 0.2},
        "high_iv": {"dag_custom": 0.3, "tdpi": 0.25, "vri": 0.25, "sdag_multiplicative_norm": 0.2}
      },
      "time_based_definitions": {
            "morning_end": "11:00:00",
            "midday_end": "14:00:00",
            "market_open": "09:30:00",
            "market_close": "16:00:00"
      }
    },
    "coefficients": {
      "dag_alpha": {"aligned": 1.3, "opposed": 0.7, "neutral": 1.0},
      "tdpi_beta": {"aligned": 1.3, "opposed": 0.7, "neutral": 1.0},
      "vri_gamma": {"aligned": 1.3, "opposed": 0.7, "neutral": 1.0}
    },
    "factors": {
        "tdpi_gaussian_width": -0.5,
        "vri_vol_trend_fallback_factor": 0.95
    },
    "approximations": {
        "tdpi_atr_fallback": {"type": "percentage_of_price", "percentage": 0.005, "min_value": 1.0}
    },
    "iv_context_parameters": {"iv_percentile": "iv_percentile_30d"}
  },
  "strategy_settings": {
    "gamma_exposure_source_col": "gxoi",
    "delta_exposure_source_col": "dxoi",
    "skew_adjusted_gamma_source_col": "sgxoi",
    "use_skew_adjusted_for_sdag": False,
    "direct_delta_buy_col": "deltas_buy",
    "direct_delta_sell_col": "deltas_sell",
    "direct_gamma_buy_col": "gammas_buy",
    "direct_gamma_sell_col": "gammas_sell",
    "direct_vega_buy_col": "vegas_buy",
    "direct_vega_sell_col": "vegas_sell",
    "direct_theta_buy_col": "thetas_buy",
    "direct_theta_sell_col": "thetas_sell",
    "proxy_delta_flow_col": "dxvolm",
    "proxy_gamma_flow_col": "gxvolm",
    "proxy_vega_flow_col": "vxvolm",
    "proxy_theta_flow_col": "txvolm",
    "proxy_charm_flow_col": "charmxvolm",
    "proxy_vanna_flow_col": "vannaxvolm",
    "proxy_vomma_flow_col": "vommaxvolm",
    "thresholds": {
        "sai_high_conviction": {"type": "fixed", "value": 0.7, "fallback_value": 0.7},
        "ssi_structure_change": {"type": "relative_percentile", "percentile": 15, "fallback_value": 0.3},
        "ssi_vol_contraction": {"type": "relative_percentile", "percentile": 85, "fallback_value": 0.7},
        "ssi_conviction_split": {"type": "fixed", "value": 0.2, "fallback_value": 0.2},
        "cfi_flow_divergence": {"type": "fixed", "tiers": [0.75, 1.25], "fallback_value": 0.75},
        "vol_expansion_vri_trigger": {"type": "relative_mean_factor", "factor": 1.5, "fallback_value": 0.5},
        "vol_expansion_vfi_trigger": {"type": "fixed", "value": 1.2, "fallback_value": 1.2},
        "vol_contraction_vri_trigger": {"type": "relative_mean_factor", "factor": 0.5, "fallback_value": 0.2},
        "vol_contraction_vfi_trigger": {"type": "fixed", "value": 0.8, "fallback_value": 0.8},
        "pin_risk_tdpi_trigger": {"type": "relative_mean_factor", "factor": 1.5, "fallback_value": 0.4},
        "charm_cascade_ctr_trigger": {"type": "fixed", "value": 1.2, "fallback_value": 1.2},
        "charm_cascade_tdfi_trigger": {"type": "fixed", "value": 1.2, "fallback_value": 1.2},
        "arfi_strong_flow_threshold": {"type": "fixed", "value": 1.5, "fallback_value": 1.5},
        "arfi_low_flow_threshold": {"type": "fixed", "value": 0.5, "fallback_value": 0.5},
        "sdag_vf_strong_negative_threshold": {"type": "fixed", "value": -0.5, "fallback_value": -0.5}
    },
    "dag_methodologies": {
      "enabled": ["multiplicative", "directional", "weighted", "volatility_focused"],
      "multiplicative": {"weight_in_mspi": 0.1, "delta_weight_factor": 0.5},
      "directional": {"weight_in_mspi": 0.0, "delta_weight_factor": 0.5},
      "weighted": {"enabled": True, "weight_in_mspi": 0.1, "w1_gamma": 0.6, "w2_delta": 0.4},
      "volatility_focused": {"enabled": True, "weight_in_mspi": 0.1, "delta_weight_factor": 0.5},
      "min_agreement_for_conviction_signal": 2
    },
    "recommendations": {
        "min_directional_stars_to_issue": 2,
        "min_volatility_stars_to_issue": 2,
        "min_pinrisk_stars_to_issue": 2,
        "min_caution_stars_to_issue": 2,
        "min_reissue_time_seconds": 300,
        "conviction_map_high": 4.0,
        "conviction_map_high_medium": 3.0,
        "conviction_map_medium": 2.0,
        "conviction_map_medium_low": 1.0,
        "conviction_map_base_one_star": 0.5,
        "conv_mod_ssi_low": -1.0,
        "conv_mod_ssi_high": 0.25,
        "conv_mod_vol_expansion": -0.5,
        "conv_mod_sdag_align": 0.75,
        "conv_mod_sdag_oppose": -1.0
    },
    "exits": {
        "contradiction_stars_threshold": 4,
        "ssi_exit_stars_threshold": 3,
        "mspi_flip_threshold": 0.7,
        "arfi_exit_stars_threshold": 4
    },
    "targets": {
        "min_target_atr_distance": 0.75,
        "nvp_support_quantile": 0.90,
        "nvp_resistance_quantile": 0.10,
        "target_atr_stop_loss_multiplier": 1.5,
        "target_atr_target1_multiplier_no_sr": 2.0,
        "target_atr_target2_multiplier_no_sr": 3.5,
        "target_atr_target2_multiplier_from_t1": 2.0
    }
  },
   "visualization_settings": { # Minimal, as this is ITS, not visualizer
        "mspi_visualizer": { "column_names": { "net_value_pressure": "net_value_pressure" } }
  },
  "validation": {
     "required_top_level_sections": ["system_settings", "data_processor_settings", "strategy_settings"],
     "weights_sum_tolerance": 0.01
  }
}

class IntegratedTradingSystem:
    """
    Elite core engine for calculating MSPI metrics, levels, signals,
    and DYNAMICALLY MANAGED strategy recommendations.
    Version 2.4.1: Initialization & Config Refined with full Greek flow integration.
    """

    # --- Initialization & Configuration ---
    def __init__(self, config_path: str = "config_v2.json"):
        self.instance_logger = logger.getChild(self.__class__.__name__)
        self.instance_logger.info(f"Initializing IntegratedTradingSystem (Version 2.4.1 - Init & Config Refined)...")

        self.config: Dict[str, Any] = self._load_and_validate_config(config_path)

        log_level_str = self._get_config_value(["system_settings", "log_level"], "INFO")
        try:
            log_level_val = getattr(logging, log_level_str.upper())
            self.instance_logger.setLevel(log_level_val)
            # logger.setLevel(log_level_val) # Module-level logger, uncomment if desired
            self.instance_logger.info(f"Instance logger level set to: {log_level_str} ({logging.getLevelName(self.instance_logger.getEffectiveLevel())})")
        except AttributeError:
            log_level_val = logging.INFO
            self.instance_logger.setLevel(log_level_val)
            self.instance_logger.warning(f"Invalid log level '{log_level_str}' in config. ITS instance logger defaulting to INFO.")

        self.gamma_exposure_col: str = self._get_config_value(["strategy_settings", "gamma_exposure_source_col"], "gxoi")
        self.delta_exposure_col: str = self._get_config_value(["strategy_settings", "delta_exposure_source_col"], "dxoi")
        self.use_skew_adjusted_for_sdag: bool = self._get_config_value(["strategy_settings", "use_skew_adjusted_for_sdag"], False)
        self.skew_adjusted_gamma_col: str = self._get_config_value(["strategy_settings", "skew_adjusted_gamma_source_col"], "sgxoi")
        self.gamma_col_for_sdag_final: str = self.skew_adjusted_gamma_col if self.use_skew_adjusted_for_sdag else self.gamma_exposure_col

        self.direct_delta_buy_col: str = self._get_config_value(["strategy_settings", "direct_delta_buy_col"], "deltas_buy")
        self.direct_delta_sell_col: str = self._get_config_value(["strategy_settings", "direct_delta_sell_col"], "deltas_sell")
        self.direct_gamma_buy_col: str = self._get_config_value(["strategy_settings", "direct_gamma_buy_col"], "gammas_buy")
        self.direct_gamma_sell_col: str = self._get_config_value(["strategy_settings", "direct_gamma_sell_col"], "gammas_sell")
        self.direct_vega_buy_col: str = self._get_config_value(["strategy_settings", "direct_vega_buy_col"], "vegas_buy")
        self.direct_vega_sell_col: str = self._get_config_value(["strategy_settings", "direct_vega_sell_col"], "vegas_sell")
        self.direct_theta_buy_col: str = self._get_config_value(["strategy_settings", "direct_theta_buy_col"], "thetas_buy")
        self.direct_theta_sell_col: str = self._get_config_value(["strategy_settings", "direct_theta_sell_col"], "thetas_sell")

        self.proxy_delta_flow_col: str = self._get_config_value(["strategy_settings", "proxy_delta_flow_col"], "dxvolm")
        self.proxy_gamma_flow_col: str = self._get_config_value(["strategy_settings", "proxy_gamma_flow_col"], "gxvolm")
        self.proxy_vega_flow_col: str = self._get_config_value(["strategy_settings", "proxy_vega_flow_col"], "vxvolm")
        self.proxy_theta_flow_col: str = self._get_config_value(["strategy_settings", "proxy_theta_flow_col"], "txvolm")
        self.proxy_charm_flow_col: str = self._get_config_value(["strategy_settings", "proxy_charm_flow_col"], "charmxvolm")
        self.proxy_vanna_flow_col: str = self._get_config_value(["strategy_settings", "proxy_vanna_flow_col"], "vannaxvolm")
        self.proxy_vomma_flow_col: str = self._get_config_value(["strategy_settings", "proxy_vomma_flow_col"], "vommaxvolm")

        df_history_maxlen_cfg_val: Any = self._get_config_value(["system_settings", "df_history_maxlen"], 5)
        if not (isinstance(df_history_maxlen_cfg_val, int) and df_history_maxlen_cfg_val > 0):
            self.instance_logger.warning(f"Invalid df_history_maxlen '{df_history_maxlen_cfg_val}' in config. Defaulting to 5.")
            df_history_maxlen_cfg_val = 5
        self.processed_df_history: Deque[pd.DataFrame] = deque(maxlen=df_history_maxlen_cfg_val)
        self.active_recommendations: List[Dict] = []
        self.recommendation_id_counter: int = 0
        self.current_symbol_being_managed: Optional[str] = None

        self.instance_logger.info(
            f"ITS (V2.4.1) Initialized. LogLvl: {logging.getLevelName(self.instance_logger.getEffectiveLevel())}, "
            f"GammaOICol: {self.gamma_exposure_col}, DeltaOICol: {self.delta_exposure_col}, "
            f"SDAG GammaSrc: {self.gamma_col_for_sdag_final}, UseSkew: {self.use_skew_adjusted_for_sdag}, "
            f"HistoryMaxlen: {df_history_maxlen_cfg_val}"
        )
        self.instance_logger.debug(f"  Direct Delta Flow Cols: Buy='{self.direct_delta_buy_col}', Sell='{self.direct_delta_sell_col}' (Proxy: '{self.proxy_delta_flow_col}')")
        self.instance_logger.debug(f"  Direct Gamma Flow Cols: Buy='{self.direct_gamma_buy_col}', Sell='{self.direct_gamma_sell_col}' (Proxy: '{self.proxy_gamma_flow_col}')")
        self.instance_logger.debug(f"  Direct Vega Flow Cols:  Buy='{self.direct_vega_buy_col}', Sell='{self.direct_vega_sell_col}' (Proxy: '{self.proxy_vega_flow_col}')")
        self.instance_logger.debug(f"  Direct Theta Flow Cols: Buy='{self.direct_theta_buy_col}', Sell='{self.direct_theta_sell_col}' (Proxy: '{self.proxy_theta_flow_col}')")

    def _load_and_validate_config(self, config_path: str) -> Dict[str, Any]:
        load_logger = self.instance_logger.getChild("ConfigLoader")
        load_logger.info(f"Attempting to load configuration from: {config_path}")

        absolute_config_path_to_load: str
        if os.path.isabs(config_path):
            absolute_config_path_to_load = config_path
        else:
            path_from_cwd = os.path.join(os.getcwd(), config_path)
            if os.path.exists(path_from_cwd):
                absolute_config_path_to_load = path_from_cwd
                load_logger.debug(f"Config path '{config_path}' resolved relative to CWD: {absolute_config_path_to_load}")
            else:
                script_dir = os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else os.getcwd()
                absolute_config_path_to_load = os.path.join(script_dir, config_path)
                load_logger.debug(f"Config path '{config_path}' resolved relative to script dir '{script_dir}': {absolute_config_path_to_load}")
        
        loaded_config_data: Optional[Dict[str, Any]] = None
        try:
            if os.path.exists(absolute_config_path_to_load):
                with open(absolute_config_path_to_load, 'r', encoding='utf-8') as f:
                    loaded_config_data = json.load(f)
                load_logger.info(f"Successfully loaded user configuration from: {absolute_config_path_to_load}")
            else:
                load_logger.error(f"Configuration file '{absolute_config_path_to_load}' not found. Default configuration will be heavily relied upon.")
        except json.JSONDecodeError as e_json:
            load_logger.error(f"Error decoding JSON from config file '{absolute_config_path_to_load}': {e_json}. Default configuration will be heavily relied upon.", exc_info=True)
        except Exception as e_load:
            load_logger.error(f"Unexpected error loading ITS config '{absolute_config_path_to_load}': {e_load}. Default configuration will be heavily relied upon.", exc_info=True)

        final_config = json.loads(json.dumps(DEFAULT_CONFIG)) # Deep copy of DEFAULT_CONFIG

        if isinstance(loaded_config_data, dict):
            load_logger.info("Merging loaded user configuration with default configuration values.")
            def _deep_merge_dicts(base_dict: Dict, updates_dict: Dict) -> Dict:
                merged = base_dict.copy()
                for key, value in updates_dict.items():
                    if isinstance(value, dict) and key in merged and isinstance(merged[key], dict):
                        merged[key] = _deep_merge_dicts(merged[key], value)
                    else:
                        merged[key] = value
                return merged
            final_config = _deep_merge_dicts(final_config, loaded_config_data)
            load_logger.debug("User configuration merged with defaults successfully.")
        elif loaded_config_data is not None:
            load_logger.warning("Loaded configuration was not a valid dictionary. Full default configuration will be used.")
        else:
            load_logger.info("No user configuration file loaded or error during load. Full default configuration will be used.")

        validation_rules = final_config.get("validation", {})
        required_top_level_sections = validation_rules.get("required_top_level_sections", [])
        if isinstance(required_top_level_sections, list):
            for section_name in required_top_level_sections:
                if section_name not in final_config:
                    load_logger.error(f"Config Validation CRITICAL: Required top-level section '{section_name}' is missing from the final configuration.")
        else:
            load_logger.warning("Config Validation section 'required_top_level_sections' is not a list. Skipping this validation check.")
        
        load_logger.info(f"Final effective configuration version used by ITS: {final_config.get('version', 'N/A')}")
        return final_config

    def _get_config_value_from_loaded_config(self, config_dict_to_search: Dict, path: List[str], default_val_override: Any = None) -> Any:
        current_level = config_dict_to_search
        try:
            for key_item in path:
                if isinstance(current_level, dict):
                    current_level = current_level[key_item]
                else:
                    return default_val_override
            return current_level
        except (KeyError, TypeError):
            return default_val_override

    def _get_config_value(self, path: List[str], default_override: Any = None) -> Any:
        value = self._get_config_value_from_loaded_config(self.config, path, None)
        if value is not None:
            return value
        # self.instance_logger.getChild("GetConfig").debug(f"Path {'.'.join(path)} not in user config, trying DEFAULT_CONFIG value.")
        return self._get_config_value_from_loaded_config(DEFAULT_CONFIG, path, default_override)
    
    # --- C. Data Processing & Utility Methods ---

    def _normalize_series(self, series: pd.Series, series_name: str) -> pd.Series:
        """
        Normalizes a Pandas Series to a -1 to 1 range based on its maximum absolute value.
        Handles NaNs, Infs, and zero max absolute value scenarios gracefully.

        Args:
            series (pd.Series): The Pandas Series to normalize.
            series_name (str): A descriptive name for the series, used for logging.

        Returns:
            pd.Series: The normalized Pandas Series. Returns a series of zeros if normalization
                       is not possible (e.g., all NaNs, max_abs_val is zero or too small).
        """
        norm_logger = self.instance_logger.getChild("NormalizeSeries")
        norm_logger.debug(f"Normalizing series '{series_name}'. Input head: {series.head().to_string() if not series.empty else 'Empty Series'}")

        if not isinstance(series, pd.Series):
            norm_logger.error(f"Input '{series_name}' is not a Pandas Series (type: {type(series)}). Returning an empty Series of dtype float.")
            return pd.Series(dtype=float)

        if series.empty:
            norm_logger.debug(f"Series '{series_name}' is empty. Returning a copy.")
            return series.copy()

        # Ensure the series is numeric, coercing errors to NaN
        series_numeric = pd.to_numeric(series, errors='coerce') if not pd.api.types.is_numeric_dtype(series) else series.copy()

        if series_numeric.isnull().all():
            norm_logger.warning(f"Series '{series_name}' contains only NaN values after numeric coercion. Returning a series of zeros with original index and name.")
            return pd.Series(0.0, index=series.index, name=series.name)

        # Replace Inf with NaN, then fill NaNs with 0.0 for max_abs_val calculation
        series_cleaned = series_numeric.replace([np.inf, -np.inf], np.nan).fillna(0.0)
        max_abs_val = series_cleaned.abs().max()
        norm_logger.debug(f"Series '{series_name}': Max absolute value after cleaning = {max_abs_val}")

        if pd.isna(max_abs_val) or max_abs_val < MIN_NORMALIZATION_DENOMINATOR:
            norm_logger.warning(f"Series '{series_name}': Max absolute value is NaN or too small ({max_abs_val}). Normalization would result in division by zero or unstable values. Returning a series of zeros with original index and name.")
            return pd.Series(0.0, index=series.index, name=series.name)

        try:
            # Perform normalization on the cleaned series (where NaNs were 0 for max_abs_val calculation)
            # but apply it to the series_numeric to preserve original NaNs if they should not be 0 in output.
            # However, for consistent -1 to 1 scaling, it's often better to normalize the cleaned series.
            # Let's stick to normalizing the series_cleaned where NaNs became 0.
            normalized_series = series_cleaned / max_abs_val
        except ZeroDivisionError: # Should be caught by the MIN_NORMALIZATION_DENOMINATOR check
            norm_logger.error(f"Series '{series_name}': ZeroDivisionError during normalization despite checks. This should not happen. Returning series of zeros.", exc_info=True)
            normalized_series = pd.Series(0.0, index=series.index, name=series.name)

        # Ensure any resulting NaNs (e.g., if an original NaN was in series_numeric and wasn't part of series_cleaned for division)
        # or Infs (if somehow MIN_NORMALIZATION_DENOMINATOR was bypassed and max_abs_val was still effectively zero for some values)
        # are handled.
        final_normalized_series = normalized_series.fillna(0.0).replace([np.inf, -np.inf], 0.0)
        norm_logger.debug(f"Series '{series_name}' normalized successfully. Output head: {final_normalized_series.head().to_string() if not final_normalized_series.empty else 'Empty Series'}")
        return final_normalized_series

    def _ensure_columns(self, df: pd.DataFrame, required_cols: List[str], calculation_name: str) -> Tuple[pd.DataFrame, bool]:
        ensure_logger = self.instance_logger.getChild("EnsureColumns")
        ensure_logger.debug(f"Ensuring columns for '{calculation_name}'. Required: {required_cols}")
        df_copy = df.copy()
        all_present_and_valid_initially = True
        actions_taken_log: List[str] = []
        string_like_id_cols = ['opt_kind', 'symbol', 'underlying_symbol', 'expiration_date', 'fetch_timestamp']
        # Define columns that should be treated as datetime objects
        datetime_cols_special_handling = ['date'] # Specifically for historical OHLC 'date' column

        for col_name in required_cols:
            if col_name not in df_copy.columns:
                all_present_and_valid_initially = False
                actions_taken_log.append(f"Added missing column '{col_name}'")
                default_val_to_add: Any
                if col_name == 'opt_kind':
                    default_val_to_add = 'unknown'
                elif col_name in string_like_id_cols:
                    default_val_to_add = 'N/A_DEFAULT'
                elif col_name in datetime_cols_special_handling:
                    default_val_to_add = pd.NaT # Use NaT for missing datetime columns
                else:
                    default_val_to_add = 0.0
                df_copy[col_name] = default_val_to_add
                ensure_logger.warning(f"Context: {calculation_name}. Missing column '{col_name}' added with default: {default_val_to_add}.")
            else: # Column exists, check type and NaNs
                if col_name in string_like_id_cols:
                    if not pd.api.types.is_string_dtype(df_copy[col_name]) and not pd.api.types.is_object_dtype(df_copy[col_name]):
                        all_present_and_valid_initially = False
                        original_dtype_str = str(df_copy[col_name].dtype)
                        df_copy[col_name] = df_copy[col_name].astype(str)
                        actions_taken_log.append(f"Coerced column '{col_name}' from {original_dtype_str} to string")
                        ensure_logger.warning(f"Context: {calculation_name}. Coerced column '{col_name}' from {original_dtype_str} to string.")
                    if df_copy[col_name].isnull().any(): # Fill NaNs in existing string cols
                        if all_present_and_valid_initially: all_present_and_valid_initially = False # If it had NaNs initially
                        df_copy[col_name] = df_copy[col_name].fillna('N/A_FILLED')
                        actions_taken_log.append(f"Filled NaNs in string column '{col_name}' with 'N/A_FILLED'")
                elif col_name in datetime_cols_special_handling:
                    # Attempt to convert to datetime if not already, but don't fill NaT with 0.0
                    if not pd.api.types.is_datetime64_any_dtype(df_copy[col_name]) and not pd.api.types.is_period_dtype(df_copy[col_name]) and not all(isinstance(x, (date, datetime, pd.Timestamp, type(pd.NaT))) for x in df_copy[col_name].dropna()):
                        original_dtype_dt = str(df_copy[col_name].dtype)
                        # Try a more robust conversion for date-like objects
                        try:
                            df_copy[col_name] = pd.to_datetime(df_copy[col_name], errors='coerce')
                            coerced_successfully = pd.api.types.is_datetime64_any_dtype(df_copy[col_name])
                        except Exception: # Broad exception if pd.to_datetime itself fails
                            coerced_successfully = False

                        if not coerced_successfully:
                            actions_taken_log.append(f"Failed to coerce '{col_name}' from {original_dtype_dt} to datetime. Problematic for ATR.")
                            ensure_logger.error(f"Context: {calculation_name}. Column '{col_name}' could not be coerced to datetime from {original_dtype_dt}.")
                            all_present_and_valid_initially = False
                        else: # Coercion to datetime happened
                            actions_taken_log.append(f"Coerced column '{col_name}' from {original_dtype_dt} to datetime. Check for new NaTs.")
                            ensure_logger.info(f"Context: {calculation_name}. Coerced column '{col_name}' from {original_dtype_dt} to datetime.")
                            all_present_and_valid_initially = False
                    
                    # Log if NaNs/NaTs are present, but do not fill them with 0.0
                    if df_copy[col_name].isnull().any():
                        if all_present_and_valid_initially : all_present_and_valid_initially = False
                        actions_taken_log.append(f"Column '{col_name}' (datetime) has NaNs/NaTs which will be handled by specific functions (e.g., ATR).")
                        ensure_logger.debug(f"Context: {calculation_name}. Column '{col_name}' (datetime) contains NaNs/NaTs.")

                else: # Assumed to be numeric if not in string_like_id_cols or datetime_cols_special_handling
                    if not pd.api.types.is_numeric_dtype(df_copy[col_name]):
                        all_present_and_valid_initially = False
                        original_dtype_str = str(df_copy[col_name].dtype)
                        df_copy[col_name] = pd.to_numeric(df_copy[col_name], errors='coerce')
                        actions_taken_log.append(f"Coerced column '{col_name}' from {original_dtype_str} to numeric")
                        ensure_logger.warning(f"Context: {calculation_name}. Coerced column '{col_name}' from {original_dtype_str} to numeric. Review for new NaNs if coercion failed for some values.")
                    
                    if df_copy[col_name].isnull().any():
                        if all_present_and_valid_initially : all_present_and_valid_initially = False
                        df_copy[col_name] = df_copy[col_name].fillna(0.0)
                        actions_taken_log.append(f"Filled NaNs in numeric column '{col_name}' with 0.0")
                        ensure_logger.debug(f"Context: {calculation_name}. Filled NaNs in numeric column '{col_name}' with 0.0.")

        if not all_present_and_valid_initially:
            ensure_logger.info(f"Context: {calculation_name}. Column integrity actions performed: {'; '.join(actions_taken_log) if actions_taken_log else 'Type/NaN modifications occurred.'}")
        else:
            ensure_logger.debug(f"Context: {calculation_name}. All required columns were initially present and valid (or already appropriately typed with no NaNs for their category).")
        return df_copy, all_present_and_valid_initially

    def get_weights(self, current_time: Optional[time] = None, iv_context: Optional[Dict[str, Any]] = None) -> Dict[str, float]:
        """
        Determines the appropriate weights for MSPI components based on either
        time of day or implied volatility context, as specified in the configuration.

        Args:
            current_time (Optional[time]): The current market time. Defaults to now if None.
                                           Used if selection_logic is 'time_based'.
            iv_context (Optional[Dict[str, Any]]): Dictionary containing IV context,
                                                   e.g., {"iv_percentile_30d": 0.65}.
                                                   Used if selection_logic is 'volatility_based'.

        Returns:
            Dict[str, float]: A dictionary where keys are component names (e.g., 'dag_custom',
                              'sdag_multiplicative_norm') and values are their respective weights.
        """
        weights_logger = self.instance_logger.getChild("GetWeights")
        weights_logger.debug(f"Getting MSPI component weights. Current time: {current_time}, IV context provided: {iv_context is not None}")

        weights_root_config = self._get_config_value(["data_processor_settings", "weights"], {})
        selection_logic = str(weights_root_config.get("selection_logic", "time_based"))
        weights_logger.debug(f"Weight selection logic from config: '{selection_logic}'")

        # Define ultimate fallback in case all other logic fails or config is malformed
        ultimate_fallback_path = ["data_processor_settings", "weights", "time_based", "midday"]
        ultimate_fallback_weights_dict = self._get_config_value_from_loaded_config(DEFAULT_CONFIG, ultimate_fallback_path, {})
        if not isinstance(ultimate_fallback_weights_dict, dict) or not ultimate_fallback_weights_dict:
            weights_logger.error("Ultimate fallback weights (DefaultConfig 'time_based.midday') are invalid or empty. Using hardcoded failsafe for fallback.")
            ultimate_fallback_weights_dict = {"dag_custom": 0.3, "tdpi": 0.3, "vri": 0.2, "sdag_multiplicative_norm": 0.2} # Hardcoded failsafe

        selected_weights_dict: Optional[Dict[str, Any]] = None
        selection_source_info: str = "Ultimate Fallback (Midday - from DEFAULT_CONFIG)"

        if selection_logic == "time_based":
            current_time_obj = current_time if current_time is not None else datetime.now().time()
            if isinstance(current_time_obj, datetime): # Convert if full datetime passed
                current_time_obj = current_time_obj.time()

            if isinstance(current_time_obj, time):
                time_based_definitions = self._get_config_value(["data_processor_settings", "weights", "time_based_definitions"], {})
                morning_end_str = str(time_based_definitions.get("morning_end", "11:00:00"))
                midday_end_str = str(time_based_definitions.get("midday_end", "14:00:00"))
                try:
                    morning_end_time = datetime.strptime(morning_end_str, "%H:%M:%S").time()
                    midday_end_time = datetime.strptime(midday_end_str, "%H:%M:%S").time()
                except ValueError:
                    weights_logger.error(f"Invalid time format in 'time_based_definitions' from config (morning_end: '{morning_end_str}', midday_end: '{midday_end_str}'). Using default times 11:00 and 14:00.")
                    morning_end_time, midday_end_time = time(11, 0, 0), time(14, 0, 0)

                time_period_key = "morning" if current_time_obj < morning_end_time else \
                                  ("midday" if current_time_obj < midday_end_time else "final")
                weights_logger.debug(f"Time-based period determined: '{time_period_key}' for time {current_time_obj.strftime('%H:%M:%S')}")
                period_specific_weights_candidate = self._get_config_value(["data_processor_settings", "weights", "time_based", time_period_key])
                if isinstance(period_specific_weights_candidate, dict) and period_specific_weights_candidate:
                    selected_weights_dict = period_specific_weights_candidate
                    selection_source_info = f"Time Based ('{time_period_key}' - {current_time_obj.strftime('%H:%M')})"
                else:
                    weights_logger.warning(f"Invalid or missing weights configuration for time_based period '{time_period_key}'. Will attempt fallback.")
            else:
                weights_logger.warning(f"Invalid current_time type ({type(current_time_obj)}) provided for 'time_based' weight logic. Will attempt fallback.")

        elif selection_logic == "volatility_based":
            iv_context_param_key_for_percentile = str(self._get_config_value(["data_processor_settings", "iv_context_parameters", "iv_percentile"], "iv_percentile_30d"))
            volatility_based_config_section = self._get_config_value(["data_processor_settings", "weights", "volatility_based"], {})

            if isinstance(iv_context, dict) and iv_context_param_key_for_percentile in iv_context and \
               iv_context[iv_context_param_key_for_percentile] is not None and isinstance(volatility_based_config_section, dict):
                try:
                    current_iv_percentile_value = float(iv_context[iv_context_param_key_for_percentile]) * 100.0 # Assuming it's a decimal like 0.65
                    iv_threshold_percentage = float(volatility_based_config_section.get("iv_percentile_threshold", 50.0))
                    weights_logger.debug(f"Volatility-based: IV Percentile ('{iv_context_param_key_for_percentile}') = {current_iv_percentile_value:.1f}%, Threshold = {iv_threshold_percentage:.1f}%")

                    vol_context_key = "low_iv" if current_iv_percentile_value < iv_threshold_percentage else "high_iv"
                    context_specific_weights_candidate = volatility_based_config_section.get(vol_context_key)
                    if isinstance(context_specific_weights_candidate, dict) and context_specific_weights_candidate:
                        selected_weights_dict = context_specific_weights_candidate
                        selection_source_info = f"Volatility Based ('{vol_context_key}', IV %ile: {current_iv_percentile_value:.1f} vs Thr: {iv_threshold_percentage:.1f})"
                    else:
                        weights_logger.warning(f"Invalid or missing weights configuration for IV context '{vol_context_key}'. Will attempt fallback.")
                except (ValueError, TypeError) as e_iv_processing:
                    weights_logger.error(f"Error processing IV context value '{iv_context.get(iv_context_param_key_for_percentile)}' for volatility-based weights: {e_iv_processing}. Will attempt fallback.", exc_info=True)
            else:
                weights_logger.warning(f"'volatility_based' logic selected, but IV context (key: '{iv_context_param_key_for_percentile}') or 'volatility_based' config section is missing/invalid. IV Context: {iv_context}. Will attempt fallback.")
        else:
            weights_logger.error(f"Unknown weight 'selection_logic': '{selection_logic}' in config. Will attempt fallback.")

        # Fallback if selected_weights_dict is still None or empty
        if not isinstance(selected_weights_dict, dict) or not selected_weights_dict:
            selected_weights_dict = ultimate_fallback_weights_dict.copy() # Use a copy
            selection_source_info = f"Ultimate Fallback (Midday - from DEFAULT_CONFIG) due to prior failure or empty dict from '{selection_logic}' logic."
            weights_logger.warning(f"Using ultimate fallback weights. Original intended selection source logic: {selection_source_info}")

        # Construct final weights dictionary ensuring float types and handling missing keys
        mspi_base_components_list = ["dag_custom", "tdpi", "vri"]
        dag_methodologies_config = self._get_config_value(["strategy_settings", "dag_methodologies"], {})
        enabled_sdag_methods_list = dag_methodologies_config.get("enabled", []) if isinstance(dag_methodologies_config, dict) else []
        
        weighted_sdag_norm_keys_list = []
        if isinstance(dag_methodologies_config, dict): # Ensure it's a dict before trying .get
            for sdag_method_name in enabled_sdag_methods_list:
                method_config = dag_methodologies_config.get(sdag_method_name, {})
                if isinstance(method_config, dict) and method_config.get("weight_in_mspi", 0.0) > 0:
                    weighted_sdag_norm_keys_list.append(f"sdag_{sdag_method_name}_norm")

        all_potential_component_keys_for_mspi = mspi_base_components_list + weighted_sdag_norm_keys_list
        
        final_component_weights_map: Dict[str, float] = {}
        for component_key in all_potential_component_keys_for_mspi:
            weight_val = selected_weights_dict.get(component_key, 0.0) # Default to 0.0 if key not in selected dict
            try:
                final_component_weights_map[component_key] = float(weight_val)
            except (ValueError, TypeError):
                final_component_weights_map[component_key] = 0.0
                weights_logger.warning(f"Could not convert weight for component '{component_key}' (value: '{weight_val}') to float. Defaulting to 0.0.")

        weights_logger.info(f"Final MSPI Component Weights Selected (Source: {selection_source_info}): {final_component_weights_map}")
        return final_component_weights_map

    def _get_atr(self, symbol: str, price: Optional[float], history_df: Optional[pd.DataFrame] = None) -> float:
        """
        Calculates Average True Range (ATR) for a given symbol.
        Prioritizes calculation from provided historical OHLC DataFrame.
        If history_df is insufficient or unavailable, falls back to a percentage of the current price
        or a configured minimum value.

        Args:
            symbol (str): The symbol for which ATR is being calculated (for logging).
            price (Optional[float]): The current price of the underlying, used for fallback.
            history_df (Optional[pd.DataFrame]): DataFrame with historical OHLC data.
                                                 Expected columns: 'date', 'high', 'low', 'close'.

        Returns:
            float: The calculated or fallback ATR value.
        """
        atr_logger = self.instance_logger.getChild("GetATR")
        atr_logger.debug(f"ATR calculation started for symbol '{symbol}'. Current price for fallback: {price}. History DF provided: {history_df is not None and not history_df.empty}")

        atr_period: int = 14 # Standard ATR period
        min_value_from_config = float(self._get_config_value(["data_processor_settings", "approximations", "tdpi_atr_fallback", "min_value"], DEFAULT_ATR_FALLBACK_MIN_VALUE))
        calculated_atr_value: float = min_value_from_config # Initialize with a floor

        if history_df is not None and isinstance(history_df, pd.DataFrame) and not history_df.empty:
            atr_logger.debug(f"ATR ({symbol}): Processing history_df with shape {history_df.shape}.")
            hist_df_copy = history_df.copy()
            
            # Define expected column names for OHLC data
            date_col, high_col, low_col, close_col = 'date', 'high', 'low', 'close'
            required_ohlc_cols_for_atr_calc = [high_col, low_col, close_col, date_col]
            
            # Ensure columns exist and are of correct type
            hist_df_copy, cols_ok = self._ensure_columns(hist_df_copy, required_ohlc_cols_for_atr_calc, f"ATR_History_Input_For_{symbol}")

            if not cols_ok:
                atr_logger.warning(f"ATR ({symbol}): history_df missing or has invalid required OHLC columns after _ensure_columns. Using fallback ATR.")
            elif hist_df_copy.empty: # Should be caught by _ensure_columns if critical cols were entirely bad
                atr_logger.warning(f"ATR ({symbol}): history_df became empty after data type coercion or NaN handling. Using fallback ATR.")
            else:
                try:
                    # Ensure date is datetime for sorting, high/low/close are numeric
                    hist_df_copy[date_col] = pd.to_datetime(hist_df_copy[date_col], errors='coerce')
                    # Already handled by _ensure_columns:
                    # for col in [high_col, low_col, close_col]:
                    #     hist_df_copy[col] = pd.to_numeric(hist_df_copy[col], errors='coerce')
                    
                    hist_df_copy.dropna(subset=required_ohlc_cols_for_atr_calc, inplace=True)
                    
                    if len(hist_df_copy) >= atr_period:
                        hist_df_copy.sort_values(by=date_col, inplace=True, ascending=True)
                        hist_df_copy.reset_index(drop=True, inplace=True)

                        high_low_range = hist_df_copy[high_col] - hist_df_copy[low_col]
                        prev_close_shifted = hist_df_copy[close_col].shift(1)
                        high_prev_close_range = abs(hist_df_copy[high_col] - prev_close_shifted)
                        low_prev_close_range = abs(hist_df_copy[low_col] - prev_close_shifted)

                        true_ranges_concat_df = pd.concat([high_low_range, high_prev_close_range, low_prev_close_range], axis=1)
                        true_range_series_calc = true_ranges_concat_df.max(axis=1, skipna=False) # Calculate max across each row for TR

                        # Handle the first TR value (which would have NaN for prev_close based calculations)
                        # The first True Range is simply High - Low of the first period.
                        if not true_range_series_calc.empty and not high_low_range.empty and pd.notna(high_low_range.iloc[0]):
                            true_range_series_calc.iloc[0] = high_low_range.iloc[0]
                        elif not true_range_series_calc.empty: # If first TR could not be set, make it NaN so it's handled by dropna
                            true_range_series_calc.iloc[0] = np.nan
                        
                        true_range_series_calc.dropna(inplace=True) # Remove any NaNs that might remain

                        if not true_range_series_calc.empty and len(true_range_series_calc) >= atr_period:
                            atr_logger.debug(f"ATR ({symbol}): Calculating Exponential Moving Average over {len(true_range_series_calc)} True Range values for ATR{atr_period}.")
                            # Using pandas ewm for ATR calculation
                            atr_calculated_series_ewm = true_range_series_calc.ewm(span=atr_period, adjust=False, min_periods=atr_period).mean()
                            
                            if not atr_calculated_series_ewm.empty and pd.notna(atr_calculated_series_ewm.iloc[-1]):
                                atr_from_historical_data = atr_calculated_series_ewm.iloc[-1]
                                if atr_from_historical_data > MIN_NORMALIZATION_DENOMINATOR: # Ensure ATR is positive and not excessively small
                                    calculated_atr_value = max(atr_from_historical_data, min_value_from_config) # Ensure it's at least the min_value
                                    atr_logger.info(f"ATR for {symbol} calculated successfully from history_df: {calculated_atr_value:.4f} (Raw EMA: {atr_from_historical_data:.4f}, Config Min Floor: {min_value_from_config:.4f})")
                                    return calculated_atr_value # Successful calculation
                                else:
                                    atr_logger.warning(f"ATR ({symbol}): Calculated ATR from history_df is invalid or too small ({atr_from_historical_data:.4f}). Using fallback ATR.")
                            else:
                                atr_logger.warning(f"ATR ({symbol}): ATR EMA calculation resulted in NaN or empty series. Using fallback ATR.")
                        else:
                             atr_logger.warning(f"ATR ({symbol}): Insufficient True Range values ({len(true_range_series_calc)}) after processing for ATR{atr_period}. Using fallback ATR.")
                    else:
                        atr_logger.warning(f"ATR ({symbol}): Insufficient valid data rows ({len(hist_df_copy)}) in history_df for ATR{atr_period} (need at least {atr_period} periods). Using fallback ATR.")
                except Exception as e_atr_hist_calc:
                    atr_logger.error(f"ATR ({symbol}): Error during ATR calculation from history_df: {e_atr_hist_calc}. Using fallback ATR.", exc_info=True)
        else: # Fallback logic if history_df is not provided or was empty
            if history_df is None:
                atr_logger.debug(f"ATR ({symbol}): history_df not provided by caller. Using fallback ATR.")
            else: # history_df was provided but was empty or invalid type
                atr_logger.warning(f"ATR ({symbol}): history_df provided was invalid (e.g., empty, wrong type: {type(history_df)}). Using fallback ATR.")

        # Fallback ATR calculation (if historical calculation failed or data was insufficient)
        atr_fallback_config = self._get_config_value(["data_processor_settings", "approximations", "tdpi_atr_fallback"], {})
        fallback_type = str(atr_fallback_config.get("type", "percentage_of_price"))
        min_value_cfg_fallback = float(atr_fallback_config.get("min_value", DEFAULT_ATR_FALLBACK_MIN_VALUE))
        # Ensure calculated_atr_value starts at the floor if not already determined by successful history calc
        calculated_atr_value = min_value_cfg_fallback 

        if fallback_type == "percentage_of_price":
            percentage_cfg_fallback = float(atr_fallback_config.get("percentage", DEFAULT_ATR_FALLBACK_PERCENTAGE))
            if price is not None and pd.notna(price) and price > 0:
                price_based_atr_fallback = price * percentage_cfg_fallback
                calculated_atr_value = max(price_based_atr_fallback, min_value_cfg_fallback) # Ensure it's at least min_value
                atr_logger.info(f"ATR for {symbol} using fallback (Percentage of Price: {price_based_atr_fallback:.4f} vs Min Config: {min_value_cfg_fallback:.4f}): Result = {calculated_atr_value:.4f}")
            else:
                atr_logger.warning(f"ATR ({symbol}): Fallback type is 'percentage_of_price' but current price is invalid ({price}). Using configured min_value: {min_value_cfg_fallback:.4f}.")
                # calculated_atr_value remains min_value_cfg_fallback in this case
        else: # Other fallback types not implemented, defaults to min_value_cfg_fallback
            atr_logger.warning(f"ATR for {symbol}: Unknown ATR fallback type configured ('{fallback_type}'). Using configured min_value: {min_value_cfg_fallback:.4f}.")
            # calculated_atr_value remains min_value_cfg_fallback

        return calculated_atr_value

    def map_score_to_stars(self, score: Optional[Union[float, int]]) -> int:
        """Converts a numerical conviction score to a 0-5 star rating based on configured thresholds."""
        map_logger = self.instance_logger.getChild("MapScoreToStars")
        score_val: float = 0.0
        if isinstance(score, (int, float)) and pd.notna(score) and np.isfinite(score): # Check for finite
            score_val = float(score)
        else:
            map_logger.debug(f"Invalid or non-finite score input ({score}, type: {type(score)}). Defaulting to 0.0 for star mapping.")

        recommendations_config = self._get_config_value(["strategy_settings", "recommendations"], {})
        conviction_map_high_thresh = float(recommendations_config.get("conviction_map_high", 4.0))
        conviction_map_high_medium_thresh = float(recommendations_config.get("conviction_map_high_medium", 3.0))
        conviction_map_medium_thresh = float(recommendations_config.get("conviction_map_medium", 2.0))
        conviction_map_medium_low_thresh = float(recommendations_config.get("conviction_map_medium_low", 1.0))
        conviction_map_base_one_star_thresh = float(recommendations_config.get("conviction_map_base_one_star", 0.5))

        stars_calculated: int = 0
        if score_val >= conviction_map_high_thresh:
            stars_calculated = 5
        elif score_val >= conviction_map_high_medium_thresh:
            stars_calculated = 4
        elif score_val >= conviction_map_medium_thresh:
            stars_calculated = 3
        elif score_val >= conviction_map_medium_low_thresh:
            stars_calculated = 2
        elif score_val >= conviction_map_base_one_star_thresh:
            stars_calculated = 1
        # else stars_calculated remains 0

        map_logger.debug(f"Mapped score {score_val:.3f} to {stars_calculated} stars.")
        return stars_calculated

    def _calculate_dynamic_threshold_wrapper(self, config_path_suffix: List[str], data_series: Optional[pd.Series], comparison_mode: str = 'above') -> Optional[Union[float, List[float]]]:
        """
        Wrapper for _calculate_dynamic_threshold that handles fetching threshold configuration
        and applying a fallback value if dynamic calculation fails or config is missing.
        """
        dt_wrap_logger = self.instance_logger.getChild("DynamicThresholdWrapper")
        full_config_path = ["strategy_settings", "thresholds"] + config_path_suffix
        threshold_config_dict = self._get_config_value(full_config_path, {}) # Returns {} if path not found
        
        dt_wrap_logger.debug(f"Attempting to calculate dynamic threshold for: {'.'.join(config_path_suffix)}. Config found: {bool(threshold_config_dict)}")

        if not isinstance(threshold_config_dict, dict) or not threshold_config_dict: # Ensure it's a non-empty dict
            dt_wrap_logger.error(f"Invalid or empty threshold configuration at '{'/'.join(full_config_path)}'. Cannot calculate threshold; no fallback specified in this structure.")
            return None # No config, no calculation possible

        calculated_result = self._calculate_dynamic_threshold(threshold_config_dict, data_series, comparison_mode)

        if calculated_result is None: # Dynamic calculation failed or returned None
            fixed_fallback_value_from_cfg = threshold_config_dict.get('fallback_value')
            dt_wrap_logger.warning(f"Dynamic threshold calculation failed for '{'/'.join(config_path_suffix)}'. Attempting to use fallback value from config: '{fixed_fallback_value_from_cfg}'")
            if fixed_fallback_value_from_cfg is not None:
                try:
                    if isinstance(fixed_fallback_value_from_cfg, list):
                        # Ensure all items in the list are convertible to float
                        return [float(tier_val) for tier_val in fixed_fallback_value_from_cfg]
                    else:
                        return float(fixed_fallback_value_from_cfg)
                except (ValueError, TypeError) as e_fallback_conversion:
                    dt_wrap_logger.error(f"Fallback value '{fixed_fallback_value_from_cfg}' for '{'/'.join(config_path_suffix)}' is invalid and cannot be converted to float/list: {e_fallback_conversion}. Returning None.", exc_info=True)
                    return None
            else:
                dt_wrap_logger.error(f"No specific 'fallback_value' configured for '{'/'.join(config_path_suffix)}' and dynamic calculation also failed. Returning None.")
                return None
        
        dt_wrap_logger.debug(f"Successfully determined threshold for '{'.'.join(config_path_suffix)}': {calculated_result}")
        return calculated_result

    def _calculate_dynamic_threshold(self, threshold_config: Dict, data_series: Optional[pd.Series], comparison_mode: str = 'above') -> Optional[Union[float, List[float]]]:
        """
        Calculates a dynamic threshold based on the provided configuration and data series.
        Supports 'fixed', 'relative_percentile', and 'relative_mean_factor' types.
        """
        dyn_thresh_logger = self.instance_logger.getChild("DynamicThresholdCalc")
        threshold_type = str(threshold_config.get('type', 'fixed')) # Default to 'fixed' if type not specified
        calculated_threshold_value: Optional[Union[float, List[float]]] = None
        
        dyn_thresh_logger.debug(f"Calculating dynamic threshold. Type: '{threshold_type}', Config: {threshold_config}, Data series provided: {data_series is not None and not data_series.empty}")

        try:
            if threshold_type == 'fixed':
                value_from_cfg = threshold_config.get('value')
                tiers_from_cfg = threshold_config.get('tiers')
                if value_from_cfg is not None:
                    calculated_threshold_value = float(value_from_cfg)
                elif tiers_from_cfg is not None and isinstance(tiers_from_cfg, list) and tiers_from_cfg: # Ensure not empty list
                    calculated_threshold_value = [float(tier_item) for tier_item in tiers_from_cfg]
                else:
                    dyn_thresh_logger.warning(f"'fixed' threshold type selected but requires a valid 'value' or non-empty 'tiers' list in configuration. Config: {threshold_config}")
            elif threshold_type.startswith('relative_'):
                if data_series is None or data_series.empty:
                    dyn_thresh_logger.debug(f"Cannot calculate relative threshold of type '{threshold_type}' because the provided data_series is None or empty.")
                    return None # Cannot proceed without data for relative types

                # Clean the series: convert to numeric, replace Inf, drop NaNs
                cleaned_numeric_series = pd.to_numeric(data_series, errors='coerce').replace([np.inf, -np.inf], np.nan).dropna()
                if cleaned_numeric_series.empty:
                    dyn_thresh_logger.debug(f"Data series for relative threshold type '{threshold_type}' became empty after cleaning (all values were NaN or Inf). Cannot calculate threshold.")
                    return None
                
                dyn_thresh_logger.debug(f"Relative threshold '{threshold_type}': Using cleaned series (Length: {len(cleaned_numeric_series)}, Mean: {cleaned_numeric_series.mean():.3f}, StdDev: {cleaned_numeric_series.std():.3f})")

                if threshold_type == 'relative_percentile':
                    percentile_config_val = float(threshold_config.get('percentile', 50.0)) # Default to median
                    percentile_config_val = max(0.0, min(100.0, percentile_config_val)) # Clamp between 0 and 100
                    calculated_threshold_value = np.percentile(cleaned_numeric_series, percentile_config_val)
                elif threshold_type == 'relative_mean_factor':
                    factor_config_val = float(threshold_config.get('factor', 1.0))
                    # Determine if absolute values should be used for mean based on comparison_mode
                    series_for_mean_calc = cleaned_numeric_series.abs() if comparison_mode == 'above_abs' else cleaned_numeric_series
                    if series_for_mean_calc.empty: # Should not happen if cleaned_numeric_series is not empty
                        dyn_thresh_logger.warning(f"Series for mean calculation (Mode: {comparison_mode}) became empty unexpectedly. Cannot calculate threshold.")
                        return None
                    mean_val_of_series = series_for_mean_calc.mean()
                    calculated_threshold_value = factor_config_val * mean_val_of_series
                else:
                    dyn_thresh_logger.error(f"Unknown 'relative_' threshold type specified: '{threshold_type}'.")
                    return None
            else:
                dyn_thresh_logger.error(f"Unsupported threshold type configured: '{threshold_type}'.")
                return None

            # Validate the calculated_threshold_value before returning
            if calculated_threshold_value is None:
                dyn_thresh_logger.warning(f"Threshold calculation for type '{threshold_type}' resulted in a None value before final validation.")
                return None
            if isinstance(calculated_threshold_value, list):
                 if not all(isinstance(t_val, (int,float)) and pd.notna(t_val) and np.isfinite(t_val) for t_val in calculated_threshold_value):
                     dyn_thresh_logger.warning(f"Calculated threshold list contains invalid (NaN/Inf) values: {calculated_threshold_value}. Returning None.")
                     return None
            elif not (isinstance(calculated_threshold_value, (int,float)) and pd.notna(calculated_threshold_value) and np.isfinite(calculated_threshold_value)):
                 dyn_thresh_logger.warning(f"Calculated threshold is an invalid (NaN/Inf) scalar value: {calculated_threshold_value}. Returning None.")
                 return None

            dyn_thresh_logger.debug(f"Successfully calculated dynamic threshold for type '{threshold_type}': {calculated_threshold_value}")
            return calculated_threshold_value

        except Exception as e_dyn_thresh_calc:
            dyn_thresh_logger.error(f"Error during dynamic threshold calculation (Type: '{threshold_type}', Config: {threshold_config}): {e_dyn_thresh_calc}", exc_info=True)
            return None

    def _aggregate_for_levels(self, df: pd.DataFrame, group_col: str = 'strike') -> pd.DataFrame:
        """
        Aggregates per-contract DataFrame data to a per-strike (or other group_col) level.
        Uses predefined aggregation logic for known metrics (sum for flows/exposures, first for indices).
        """
        agg_logger = self.instance_logger.getChild("AggregateForLevels")
        agg_logger.debug(f"Aggregating DataFrame by '{group_col}'. Input shape: {df.shape if isinstance(df, pd.DataFrame) else 'N/A'}")

        if not isinstance(df, pd.DataFrame) or df.empty:
            agg_logger.warning("Input DataFrame for aggregation is empty or invalid. Returning an empty DataFrame.")
            return pd.DataFrame()
        if group_col not in df.columns:
            agg_logger.error(f"Grouping column '{group_col}' not found in DataFrame. Cannot aggregate. Available columns: {df.columns.tolist()}")
            return pd.DataFrame()

        df_copy_for_aggregation = df.copy()

        # Ensure the grouping column is clean and usable
        if pd.api.types.is_numeric_dtype(df_copy_for_aggregation[group_col]):
            df_copy_for_aggregation[group_col] = pd.to_numeric(df_copy_for_aggregation[group_col], errors='coerce')
        df_copy_for_aggregation.dropna(subset=[group_col], inplace=True)
        
        if df_copy_for_aggregation.empty:
            agg_logger.warning(f"DataFrame became empty after ensuring valid grouping column '{group_col}'. Returning an empty DataFrame.")
            return pd.DataFrame()

        # Define aggregation logic: sum for additive metrics, first for descriptive/state metrics
        aggregation_logic_base: Dict[str, str] = {
            'mspi':'sum', 'sai':'first', 'ssi':'first', 'cfi':'first', # CFI is ARFI
            'dag_custom':'sum', 'tdpi':'sum', 'vri':'sum',
            'ctr':'first', 'tdfi':'first', 'vfi':'first', 'vvr':'first',
            'price':'first', # Underlying price, should be same for all rows for a given snapshot
            NET_VOLUME_PRESSURE_COL: 'first', # Assuming this is already strike-level from processor
            NET_VALUE_PRESSURE_COL: 'first',  # Assuming this is already strike-level from processor
            # Add new net Greek flow columns calculated by processor (they are already strike-level)
            "net_delta_flow_total": 'first', "heuristic_net_delta_pressure": 'first',
            "net_gamma_flow": 'first', "net_vega_flow": 'first', "net_theta_exposure": 'first',
            "true_net_volume_flow": 'first', "true_net_value_flow": 'first'
        }

        dag_method_configurations_agg = self._get_config_value(["strategy_settings", "dag_methodologies"], {})
        enabled_sdag_methods_agg = dag_method_configurations_agg.get("enabled", []) if isinstance(dag_method_configurations_agg, dict) else []
        for sdag_method_name_agg in enabled_sdag_methods_agg:
            sdag_column_name_agg = f"sdag_{sdag_method_name_agg}"
            sdag_norm_column_name_agg = f"sdag_{sdag_method_name_agg}_norm"
            if sdag_column_name_agg in df_copy_for_aggregation.columns:
                aggregation_logic_base[sdag_column_name_agg] = 'sum'
            if sdag_norm_column_name_agg in df_copy_for_aggregation.columns: # Normalized SDAGs take 'first'
                aggregation_logic_base[sdag_norm_column_name_agg] = 'first'
        
        # Filter aggregation logic to only include columns present in the DataFrame
        valid_aggregation_logic_final = {
            col_key: agg_func for col_key, agg_func in aggregation_logic_base.items()
            if col_key in df_copy_for_aggregation.columns
        }

        if not valid_aggregation_logic_final:
            agg_logger.warning("No valid columns found for aggregation after filtering based on DataFrame's columns. Returning an empty DataFrame.")
            return pd.DataFrame()
        
        agg_logger.debug(f"Performing aggregation by '{group_col}' using effective aggregation logic: {valid_aggregation_logic_final}")

        try:
            # Ensure all columns to be aggregated (other than group_col and specific string cols) are numeric
            for column_to_aggregate, agg_function in valid_aggregation_logic_final.items():
                if column_to_aggregate not in [group_col, 'opt_kind', 'symbol', 'underlying_symbol', 'expiration_date']: # Check against string_like_id_cols
                    if column_to_aggregate in df_copy_for_aggregation.columns and \
                       not pd.api.types.is_numeric_dtype(df_copy_for_aggregation[column_to_aggregate]):
                        agg_logger.debug(f"Coercing column '{column_to_aggregate}' to numeric before aggregation.")
                        df_copy_for_aggregation[column_to_aggregate] = pd.to_numeric(df_copy_for_aggregation[column_to_aggregate], errors='coerce')
            
            aggregated_df_final_result = df_copy_for_aggregation.groupby(group_col, as_index=False).agg(valid_aggregation_logic_final)
            
            # Fill NaNs in aggregated results: 0.0 for most, 0.5 for SSI as a neutral default
            default_fill_values_aggregated = {
                col_agg: 0.0 for col_agg in aggregated_df_final_result.columns
                if col_agg != group_col and col_agg != 'ssi'
            }
            if 'ssi' in aggregated_df_final_result.columns:
                default_fill_values_aggregated['ssi'] = 0.5
            
            aggregated_df_final_result = aggregated_df_final_result.fillna(value=default_fill_values_aggregated)
            
            # Ensure SSI is numeric after fillna, just in case
            if 'ssi' in aggregated_df_final_result.columns:
                aggregated_df_final_result['ssi'] = pd.to_numeric(aggregated_df_final_result['ssi'], errors='coerce').fillna(0.5)
            
            agg_logger.info(f"Aggregation by '{group_col}' complete. Output shape: {aggregated_df_final_result.shape}")
            return aggregated_df_final_result
        except Exception as e_aggregation_final:
            agg_logger.error(f"Level Aggregation by '{group_col}' failed critically: {e_aggregation_final}", exc_info=True)
            return pd.DataFrame() # Return empty DataFrame on critical error

    # --- D. Core Metric Calculation Methods (Per Contract) ---

    def calculate_custom_flow_dag(self, options_df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculates Delta Adjusted Gamma Exposure (Custom DAG) per option contract.
        Prioritizes direct delta and gamma flow metrics if available and configured,
        otherwise falls back to proxy columns (e.g., dxvolm, gxvolm).

        Args:
            options_df (pd.DataFrame): Input DataFrame with per-contract option data.
                                       Must contain configured Greek OI and flow columns.
        Returns:
            pd.DataFrame: The input DataFrame with an added 'dag_custom' column and
                          intermediate calculation columns.
        """
        calc_name = "CustomFlowDAG_V2.4.1_DirectFlow"; dag_logger = self.instance_logger.getChild(calc_name)
        dag_logger.info(f"Calculating {calc_name}...")

        # Base Greek OI columns (from config, e.g., "gxoi", "dxoi")
        # Direct flow columns (from config, e.g., "deltas_buy", "gammas_sell")
        # Proxy flow columns (from config, e.g., "dxvolm", "gxvolm")
        required_cols_dag = [
            'strike', self.gamma_exposure_col, self.delta_exposure_col, 'oi', 'volm', # Base & OI Greeks
            self.direct_delta_buy_col, self.direct_delta_sell_col, self.proxy_delta_flow_col, # Delta flow options
            self.direct_gamma_buy_col, self.direct_gamma_sell_col, self.proxy_gamma_flow_col  # Gamma flow options
        ]
        df, _ = self._ensure_columns(options_df, required_cols_dag, calc_name) # Let _ensure_columns handle defaults for missing

        # Get DAG Alpha coefficients from config
        dag_alpha_coeffs = self._get_config_value(["data_processor_settings", "coefficients", "dag_alpha"], {"aligned": 1.3, "opposed": 0.7, "neutral": 1.0})
        alpha_aligned = float(dag_alpha_coeffs.get("aligned", 1.3))
        alpha_opposed = float(dag_alpha_coeffs.get("opposed", 0.7))
        alpha_neutral = float(dag_alpha_coeffs.get("neutral", 1.0))

        # Delta Open Interest (numeric and cleaned)
        dxoi_numeric = pd.to_numeric(df[self.delta_exposure_col], errors='coerce').fillna(0.0)

        # Determine Net Delta Flow (Prioritize Direct, Fallback to Proxy)
        net_delta_flow_series = pd.Series(0.0, index=df.index, name="net_delta_flow_for_dag")
        delta_flow_source_used = "proxy" # Assume proxy initially

        if self.direct_delta_buy_col in df.columns and self.direct_delta_sell_col in df.columns and \
           pd.api.types.is_numeric_dtype(df[self.direct_delta_buy_col]) and \
           pd.api.types.is_numeric_dtype(df[self.direct_delta_sell_col]) and \
           not (df[self.direct_delta_buy_col].isnull().all() and df[self.direct_delta_sell_col].isnull().all()):
            # Note: For "flow against structure", if deltas_buy is positive delta and deltas_sell is positive delta,
            # then net initiating buy delta flow is (deltas_buy - deltas_sell).
            # Here, the original DAG logic used a proxy that might have different sign conventions.
            # For consistency with original logic if dxvolm was signed, we'll use sell - buy for now,
            # but this might need review based on how 'dxvolm' was signed.
            # If deltas_buy = +100 (buyers gain +100 delta) and deltas_sell = +80 (sellers of these take on -80 delta),
            # net delta initiated = +100 (from buyers) + (+80 from sellers taking short position) IF deltas_sell is delta of instrument.
            # If deltas_sell = -80 (sellers take on -80 delta), then net_delta_flow is deltas_buy + deltas_sell.
            # Assuming deltas_buy/sell are "sum of delta of instruments bought/sold":
            net_delta_flow_series = pd.to_numeric(df[self.direct_delta_buy_col], errors='coerce').fillna(0.0) - \
                                    pd.to_numeric(df[self.direct_delta_sell_col], errors='coerce').fillna(0.0)
            delta_flow_source_used = "direct_deltas_buy_minus_sell"
            dag_logger.debug(f"Using DIRECT delta flow ('{self.direct_delta_buy_col}' - '{self.direct_delta_sell_col}') for DAG. Sum: {net_delta_flow_series.sum():.2f}")
        elif self.proxy_delta_flow_col in df.columns:
            net_delta_flow_series = pd.to_numeric(df[self.proxy_delta_flow_col], errors='coerce').fillna(0.0)
            delta_flow_source_used = f"proxy ('{self.proxy_delta_flow_col}')"
            dag_logger.warning(f"Using PROXY delta flow ('{self.proxy_delta_flow_col}') for DAG as direct flow columns were not fully available/valid. Sum: {net_delta_flow_series.sum():.2f}")
        else:
            dag_logger.error(f"Neither direct delta flow columns nor proxy '{self.proxy_delta_flow_col}' are available for DAG. Delta flow component will be zero.")
            # net_delta_flow_series remains series of 0.0

        # Calculate Alpha (Alignment Factor)
        alignment_factor_sign = np.sign(net_delta_flow_series) * np.sign(dxoi_numeric) # dxoi_numeric is Net Delta OI
        df['alpha'] = np.select(
            [alignment_factor_sign > 0, alignment_factor_sign < 0],
            [alpha_aligned, alpha_opposed],
            default=alpha_neutral
        )

        # Calculate Flow Magnitude Ratio (Net Delta Flow relative to Delta OI)
        net_delta_flow_abs = net_delta_flow_series.abs()
        dxoi_abs = dxoi_numeric.abs()
        df['net_delta_flow_to_dxoi_ratio'] = (net_delta_flow_abs / dxoi_abs.replace(0, np.inf)).fillna(0.0)
        dag_logger.debug(f"Calculated 'alpha' and 'net_delta_flow_to_dxoi_ratio' using delta flow source: {delta_flow_source_used}.")

        # Determine Normalized Net Gamma Flow (Prioritize Direct, Fallback to Proxy)
        norm_net_gamma_flow_series = pd.Series(0.0, index=df.index, name="norm_net_gamma_flow_for_dag")
        gamma_flow_source_used = "proxy" # Assume proxy initially

        if self.direct_gamma_buy_col in df.columns and self.direct_gamma_sell_col in df.columns and \
           pd.api.types.is_numeric_dtype(df[self.direct_gamma_buy_col]) and \
           pd.api.types.is_numeric_dtype(df[self.direct_gamma_sell_col]) and \
           not (df[self.direct_gamma_buy_col].isnull().all() and df[self.direct_gamma_sell_col].isnull().all()):
            # Net Gamma Flow: Buyers are long gamma (+), Sellers of gamma are short gamma (-).
            # If gammas_buy/sell are sum of (positive) gamma of instruments:
            # Net gamma initiated by market = gammas_buy (long gamma from buys) - gammas_sell (long gamma from sells by others, so short gamma for these initiators)
            net_gamma_flow_direct = pd.to_numeric(df[self.direct_gamma_buy_col], errors='coerce').fillna(0.0) - \
                                    pd.to_numeric(df[self.direct_gamma_sell_col], errors='coerce').fillna(0.0)
            norm_net_gamma_flow_series = self._normalize_series(net_gamma_flow_direct, 'net_direct_gamma_flow_for_dag')
            gamma_flow_source_used = "direct_gammas_buy_minus_sell"
            dag_logger.debug(f"Using DIRECT gamma flow ('{self.direct_gamma_buy_col}' - '{self.direct_gamma_sell_col}') for DAG. Normed sum: {norm_net_gamma_flow_series.sum():.2f}")
        elif self.proxy_gamma_flow_col in df.columns:
            gamma_flow_proxy = pd.to_numeric(df[self.proxy_gamma_flow_col], errors='coerce').fillna(0.0)
            norm_net_gamma_flow_series = self._normalize_series(gamma_flow_proxy, f"{self.proxy_gamma_flow_col}_for_dag_proxy")
            gamma_flow_source_used = f"proxy ('{self.proxy_gamma_flow_col}')"
            dag_logger.warning(f"Using PROXY gamma flow ('{self.proxy_gamma_flow_col}') for DAG. Normed sum: {norm_net_gamma_flow_series.sum():.2f}")
        else:
            dag_logger.error(f"Neither direct gamma flow columns nor proxy '{self.proxy_gamma_flow_col}' are available for DAG. Gamma flow component will be zero.")
            # norm_net_gamma_flow_series remains series of 0.0

        df['norm_net_gamma_flow'] = norm_net_gamma_flow_series
        dag_logger.debug(f"Calculated 'norm_net_gamma_flow' using gamma flow source: {gamma_flow_source_used}.")

        # Final DAG Calculation
        gamma_exposure_values = pd.to_numeric(df[self.gamma_exposure_col], errors='coerce').fillna(0.0) # This is GxOI (per contract)
        dxoi_sign = np.sign(dxoi_numeric.replace(0, 1)) # Use sign of Delta OI

        df['dag_custom'] = (
            gamma_exposure_values * dxoi_sign *
            (1 + df['alpha'] * df['net_delta_flow_to_dxoi_ratio']) *
            df['norm_net_gamma_flow']
        ).fillna(0.0)

        dag_logger.debug(f"Final 'dag_custom' calculated. Example head: {df['dag_custom'].head().to_string(index=False) if not df.empty else 'N/A_DF_EMPTY'}")
        dag_logger.info(f"{calc_name} calculation complete. Delta Flow Source: {delta_flow_source_used}, Gamma Flow Source: {gamma_flow_source_used}.")
        return df

    def calculate_tdpi(self, options_df: pd.DataFrame, current_time: Optional[time] = None, historical_ohlc_df_for_atr: Optional[pd.DataFrame] = None ) -> pd.DataFrame:
        """
        Calculates Time Decay Pressure Indicator (TDPI), Charm Decay Rate (CTR),
        and Time Decay Flow Imbalance (TDFI) per option contract.
        Prioritizes direct theta flow if available. Uses historical OHLC for ATR.
        """
        calc_name = "TDPI_V2.4.1_DirectFlow"; tdpi_logger = self.instance_logger.getChild(calc_name)
        tdpi_logger.info(f"Calculating {calc_name}... ATR for proximity uses historical OHLC: {'Yes' if historical_ohlc_df_for_atr is not None and not historical_ohlc_df_for_atr.empty else 'No'}")

        required_cols_tdpi = [
            'symbol', 'strike', 'price', 'opt_kind', 'underlying_symbol', # Base
            'charmxoi', 'txoi', # OI Greeks
            self.direct_theta_buy_col, self.direct_theta_sell_col, # Direct Theta Flow
            self.proxy_theta_flow_col, # Proxy Theta Flow
            self.proxy_charm_flow_col # Charm Flow Proxy (charmxvolm)
        ]
        df, _ = self._ensure_columns(options_df, required_cols_tdpi, calc_name)

        # --- (Snapshot logging code from your v2.4.0 can be kept here if desired) ---
        if not df.empty:
            tdpi_logger.debug(f"--- TDPI Input Data Snapshot (first 3 rows if available) for {df['underlying_symbol'].iloc[0] if 'underlying_symbol' in df.columns and not df.empty else 'N/A_SYM'} ---")
            cols_to_snapshot = ['strike', 'opt_kind', 'charmxoi', 'txoi', self.proxy_charm_flow_col, self.proxy_theta_flow_col, self.direct_theta_buy_col, self.direct_theta_sell_col]
            for i in range(min(3, len(df))):
                # ... (your existing snapshot logging logic) ...
                row_data_snapshot = df.iloc[i]; snapshot_log_parts = [f"Row {i}:"]
                for col_snap in cols_to_snapshot: snapshot_log_parts.append(f"{col_snap}={row_data_snapshot.get(col_snap, 'N/A_COL')}")
                tdpi_logger.debug("    " + ", ".join(snapshot_log_parts))
            tdpi_logger.debug("--- End TDPI Input Data Snapshot ---")


        coeffs_tdpi_beta = self._get_config_value(["data_processor_settings", "coefficients", "tdpi_beta"], {"aligned":1.3, "opposed":0.7, "neutral":1.0})
        beta_aligned = float(coeffs_tdpi_beta.get("aligned",1.3)); beta_opposed = float(coeffs_tdpi_beta.get("opposed",0.7)); beta_neutral = float(coeffs_tdpi_beta.get("neutral",1.0))
        gaussian_width_factor = float(self._get_config_value(["data_processor_settings", "factors", "tdpi_gaussian_width"], -0.5))

        charmxoi_numeric = pd.to_numeric(df['charmxoi'], errors='coerce').fillna(0.0)
        # Charm Flow uses proxy self.proxy_charm_flow_col (e.g. "charmxvolm")
        charm_flow_proxy_series = pd.to_numeric(df[self.proxy_charm_flow_col], errors='coerce').fillna(0.0)
        tdpi_logger.debug(f"Using '{self.proxy_charm_flow_col}' (sum: {charm_flow_proxy_series.sum():.2f}) as Charm Flow Proxy. CharmxOI sum: {charmxoi_numeric.sum():.2f}")

        alignment_beta_sign = np.sign(charm_flow_proxy_series) * np.sign(charmxoi_numeric)
        df['beta'] = np.select([alignment_beta_sign > 0, alignment_beta_sign < 0], [beta_aligned, beta_opposed], default=beta_neutral)
        charm_flow_proxy_abs = charm_flow_proxy_series.abs(); charmxoi_abs = charmxoi_numeric.abs()
        df['charm_flow_to_charm_oi_ratio'] = (charm_flow_proxy_abs / charmxoi_abs.replace(0, np.inf)).fillna(0.0) # Renamed for clarity
        tdpi_logger.debug(f"Calculated 'beta' and 'charm_flow_to_charm_oi_ratio'.")

        # Determine Net Theta Flow (Prioritize Direct, Fallback to Proxy)
        norm_net_theta_flow_series = pd.Series(0.0, index=df.index, name="norm_net_theta_flow_for_tdpi")
        theta_flow_source_used = f"proxy ('{self.proxy_theta_flow_col}')"
        # This raw_theta_flow is used for CTR/TDFI and for proxy normalization if direct fails
        raw_theta_flow_for_sub_metrics = pd.to_numeric(df[self.proxy_theta_flow_col], errors='coerce').fillna(0.0)

        if self.direct_theta_buy_col in df.columns and self.direct_theta_sell_col in df.columns and \
           pd.api.types.is_numeric_dtype(df[self.direct_theta_buy_col]) and \
           pd.api.types.is_numeric_dtype(df[self.direct_theta_sell_col]) and \
           not (df[self.direct_theta_buy_col].isnull().all() and df[self.direct_theta_sell_col].isnull().all()):
            # Net Theta Exposure Initiated: sum(thetas_buy_contract + (-1 * thetas_sell_contract))
            # a positive value means net collection of theta by initiators.
            # a negative value means net payment of theta by initiators.
            # For TDPI formula: "Norm_Net_Theta_Flow"
            # If API thetas_buy/sell are already signed (negative for long options),
            # then (thetas_buy - thetas_sell) would be: (-ve) - (-ve).
            # Positive result means less negative theta from buys than sells (net selling of theta by initiators).
            # Negative result means more negative theta from buys than sells (net buying of theta by initiators).
            net_theta_flow_direct = pd.to_numeric(df[self.direct_theta_buy_col], errors='coerce').fillna(0.0) - \
                                    pd.to_numeric(df[self.direct_theta_sell_col], errors='coerce').fillna(0.0)
            norm_net_theta_flow_series = self._normalize_series(net_theta_flow_direct, 'net_direct_theta_flow_for_tdpi')
            raw_theta_flow_for_sub_metrics = net_theta_flow_direct.copy() # Use direct net flow for CTR/TDFI
            theta_flow_source_used = f"direct ('{self.direct_theta_buy_col}' - '{self.direct_theta_sell_col}')"
            tdpi_logger.debug(f"Using DIRECT theta flow for TDPI. Normed sum: {norm_net_theta_flow_series.sum():.2f}")
        elif self.proxy_theta_flow_col in df.columns:
            # raw_theta_flow_for_sub_metrics is already df[self.proxy_theta_flow_col]
            norm_net_theta_flow_series = self._normalize_series(raw_theta_flow_for_sub_metrics, f"{self.proxy_theta_flow_col}_for_tdpi_proxy")
            tdpi_logger.warning(f"Using PROXY theta flow ('{self.proxy_theta_flow_col}') for TDPI. Normed sum: {norm_net_theta_flow_series.sum():.2f}")
        else:
            tdpi_logger.error(f"Neither direct theta flow columns nor proxy '{self.proxy_theta_flow_col}' are available for TDPI. Theta flow component will be zero.")

        df['norm_net_theta_flow'] = norm_net_theta_flow_series
        tdpi_logger.debug(f"Calculated 'norm_net_theta_flow' using {theta_flow_source_used}.")

        # --- (Time Weight and Strike Proximity calculations remain the same as your v2.4.0) ---
        time_weight_value = 1.0; current_time_obj = current_time if current_time is not None else datetime.now().time()
        if isinstance(current_time_obj, datetime): current_time_obj = current_time_obj.time()
        if isinstance(current_time_obj, time):
            try:
                time_defs = self._get_config_value(["data_processor_settings","weights","time_based_definitions"],{}); m_open_s = time_defs.get("market_open","09:30:00"); m_close_s = time_defs.get("market_close","16:00:00")
                m_open_t = datetime.strptime(m_open_s,"%H:%M:%S").time(); m_close_t = datetime.strptime(m_close_s,"%H:%M:%S").time()
                o_secs = m_open_t.hour*3600+m_open_t.minute*60+m_open_t.second; c_secs = m_close_t.hour*3600+m_close_t.minute*60+m_close_t.second; curr_secs = current_time_obj.hour*3600+current_time_obj.minute*60+current_time_obj.second
                total_dur_s = c_secs - o_secs
                if total_dur_s > 0: t_prog_frac = (max(o_secs,min(c_secs,curr_secs))-o_secs)/total_dur_s; time_weight_value=1.0+max(0.0,min(1.0,t_prog_frac))**2
                else: tdpi_logger.warning(f"Invalid market duration. Time weight default 1.0.")
            except Exception as e_tw: tdpi_logger.error(f"Time weight calc error: {e_tw}. Default 1.0.", exc_info=True)
        else: tdpi_logger.warning(f"Invalid current_time type for time weight. Default 1.0.")
        df['time_weight'] = time_weight_value; tdpi_logger.debug(f"Time weight: {time_weight_value:.3f}")
        df['strike_proximity'] = 1.0; strike_numeric_series = pd.to_numeric(df['strike'], errors='coerce')
        if 'price' in df.columns and pd.api.types.is_numeric_dtype(df['price']) and not df['price'].empty and not df['price'].isnull().all():
            und_px_atr = df['price'].dropna().iloc[0] if not df['price'].dropna().empty else None
            if und_px_atr is not None and und_px_atr > 0:
                und_sym_atr = df['underlying_symbol'].dropna().iloc[0] if 'underlying_symbol' in df.columns and not df['underlying_symbol'].dropna().empty else "UNKNOWN"
                atr_val = self._get_atr(und_sym_atr, und_px_atr, history_df=historical_ohlc_df_for_atr)
                if atr_val > MIN_NORMALIZATION_DENOMINATOR and not strike_numeric_series.isnull().all():
                    strike_diff_sq = ((strike_numeric_series.fillna(und_px_atr) - und_px_atr) / atr_val)**2
                    df['strike_proximity'] = np.exp(gaussian_width_factor * strike_diff_sq).fillna(0.0)
                else: tdpi_logger.warning(f"ATR invalid or all strikes NaN. Proximity default 1.0.")
            else: tdpi_logger.warning(f"Underlying price invalid for proximity. Proximity default 1.0.")
        else: tdpi_logger.warning(f"'price' col missing/invalid for proximity. Proximity default 1.0.")
        # --- (End of Time Weight and Strike Proximity) ---

        txoi_numeric = pd.to_numeric(df['txoi'], errors='coerce').fillna(0.0)
        txoi_sign = np.sign(txoi_numeric.replace(0, 1))

        df['tdpi'] = (
            charmxoi_numeric * txoi_sign *
            (1 + df['beta'] * df['charm_flow_to_charm_oi_ratio']) *
            df['norm_net_theta_flow'] *
            df['time_weight'] *
            df['strike_proximity']
        ).fillna(0.0)

        df['ctr'] = (charm_flow_proxy_abs / raw_theta_flow_for_sub_metrics.abs().replace(0, np.inf)).fillna(0.0)
        df['norm_txoi_abs'] = self._normalize_series(txoi_numeric.abs(), 'txoi_abs_for_tdfi')
        df['norm_raw_theta_flow_abs_for_tdfi'] = self._normalize_series(raw_theta_flow_for_sub_metrics.abs(), 'raw_theta_flow_abs_for_tdfi') # Use consistent raw flow
        df['tdfi'] = (df['norm_raw_theta_flow_abs_for_tdfi'] / df['norm_txoi_abs'].replace(0, np.inf)).fillna(0.0)

        tdpi_logger.debug(f"Final 'tdpi' calculated. Sum: {df['tdpi'].sum():.2f}")
        tdpi_logger.info(f"{calc_name} calculation complete. Theta Flow Source: {theta_flow_source_used}.")
        return df

    def calculate_vri(self, options_df: pd.DataFrame, current_iv: Optional[float] = None, avg_iv_5day: Optional[float] = None) -> pd.DataFrame:
        """
        Calculates Volatility Risk Indicator (VRI), Volatility Volume Ratio (VVR),
        and Volatility Flow Imbalance (VFI) per option contract.
        Prioritizes direct vega flow for VFI if available.
        """
        calc_name = "VRI_V2.4.1_DirectFlow"; vri_logger = self.instance_logger.getChild(calc_name)
        vri_logger.info(f"Calculating {calc_name}... Current IV: {current_iv}, Avg 5-day IV: {avg_iv_5day}")

        required_cols_vri = [
            'symbol', 'strike', 'price', 'opt_kind', 'underlying_symbol', 'volatility', # Base & Context
            'vannaxoi', 'vxoi', 'vommaxoi', # OI Greeks
            self.direct_vega_buy_col, self.direct_vega_sell_col, # Direct Vega Flow
            self.proxy_vanna_flow_col, self.proxy_vega_flow_col, self.proxy_vomma_flow_col # Proxy Flows
        ]
        df, _ = self._ensure_columns(options_df, required_cols_vri, calc_name)

        # --- (Snapshot logging code from your v2.4.0 can be kept here if desired) ---
        if not df.empty:
            vri_logger.debug(f"--- VRI Input Data Snapshot (first 3 rows if available) for {df['underlying_symbol'].iloc[0] if 'underlying_symbol' in df.columns and not df.empty else 'N/A_SYM'} ---")
            # ... (your snapshot logging logic) ...
            cols_to_snapshot = ['strike','opt_kind','vannaxoi','vxoi','vommaxoi',self.proxy_vanna_flow_col,self.proxy_vega_flow_col,self.proxy_vomma_flow_col,'volatility',self.direct_vega_buy_col,self.direct_vega_sell_col]
            for i in range(min(3,len(df))):
                row_data_snap=df.iloc[i]; parts_snap=[f"Row {i}:"];
                for col_s in cols_to_snapshot: parts_snap.append(f"{col_s}={row_data_snap.get(col_s,'N/A')}")
                vri_logger.debug("    " + ", ".join(parts_snap))
            vri_logger.debug("--- End VRI Input Data Snapshot ---")


        coeffs_vri_gamma = self._get_config_value(["data_processor_settings", "coefficients", "vri_gamma"], {"aligned":1.3, "opposed":0.7, "neutral":1.0})
        gamma_aligned = float(coeffs_vri_gamma.get("aligned",1.3)); gamma_opposed = float(coeffs_vri_gamma.get("opposed",0.7)); gamma_neutral = float(coeffs_vri_gamma.get("neutral",1.0))
        vol_trend_fallback_factor = float(self._get_config_value(["data_processor_settings", "factors", "vri_vol_trend_fallback_factor"], 0.95))

        vannaxoi_numeric = pd.to_numeric(df['vannaxoi'], errors='coerce').fillna(0.0)
        # Vanna Flow uses proxy self.proxy_vanna_flow_col (e.g. "vannaxvolm")
        vanna_flow_proxy_series = pd.to_numeric(df[self.proxy_vanna_flow_col], errors='coerce').fillna(0.0)
        vri_logger.debug(f"Using '{self.proxy_vanna_flow_col}' (sum: {vanna_flow_proxy_series.sum():.2f}) as Vanna Flow Proxy. VannaxOI sum: {vannaxoi_numeric.sum():.2f}")

        alignment_gamma_coeff_sign = np.sign(vanna_flow_proxy_series) * np.sign(vannaxoi_numeric)
        df['gamma_coeff'] = np.select([alignment_gamma_coeff_sign > 0, alignment_gamma_coeff_sign < 0], [gamma_aligned, gamma_opposed], default=gamma_neutral)
        vanna_flow_proxy_abs = vanna_flow_proxy_series.abs(); vannaxoi_abs = vannaxoi_numeric.abs()
        df['vanna_flow_to_vanna_oi_ratio'] = (vanna_flow_proxy_abs / vannaxoi_abs.replace(0, np.inf)).fillna(0.0) # Renamed
        vri_logger.debug(f"Calculated 'gamma_coeff' and 'vanna_flow_to_vanna_oi_ratio'.")

        # Vomma Flow uses proxy self.proxy_vomma_flow_col (e.g. "vommaxvolm")
        vomma_flow_proxy_series = pd.to_numeric(df[self.proxy_vomma_flow_col], errors='coerce').fillna(0.0)
        df['norm_net_vomma_flow'] = self._normalize_series(vomma_flow_proxy_series, f"{self.proxy_vomma_flow_col}_for_vri") # Renamed
        vri_logger.debug(f"Using '{self.proxy_vomma_flow_col}' (sum: {vomma_flow_proxy_series.sum():.2f}) as Vomma Flow Proxy, normalized into 'norm_net_vomma_flow'.")

        vxoi_numeric = pd.to_numeric(df['vxoi'], errors='coerce').fillna(0.0)
        skew_factor_value = 1.0
        # --- (Skew Factor calculation from your v2.4.0 - unchanged) ---
        if 'opt_kind' in df.columns and not df['opt_kind'].empty:
            df_calls=df[df['opt_kind']=='call']; df_puts=df[df['opt_kind']=='put']
            sum_call_vxoi=pd.to_numeric(df_calls['vxoi'],errors='coerce').sum(skipna=True); sum_put_vxoi=pd.to_numeric(df_puts['vxoi'],errors='coerce').sum(skipna=True)
            total_market_vxoi=sum_call_vxoi+sum_put_vxoi
            if pd.notna(total_market_vxoi) and abs(total_market_vxoi)>MIN_NORMALIZATION_DENOMINATOR: skew_factor_value=1.0+((sum_put_vxoi-sum_call_vxoi)/total_market_vxoi)
            else: vri_logger.warning("Total market VXO_OI is zero/NaN for skew. Skew factor defaults to 1.0.")
        else: vri_logger.warning("'opt_kind' missing for skew. Skew factor defaults to 1.0.")
        df['skew_factor'] = skew_factor_value; vri_logger.debug(f"Skew factor: {skew_factor_value:.3f}")

        # --- (Vol Trend Factor calculation from your v2.4.0 - unchanged, uses actual_vol_trend_source_used logging) ---
        vol_trend_factor_value = 1.0; underlying_symbol_for_vri_log = df['underlying_symbol'].dropna().iloc[0] if 'underlying_symbol' in df.columns and not df['underlying_symbol'].dropna().empty else "UNKNOWN"
        actual_vol_trend_source_used_log = "default (1.0)"
        if current_iv is not None and avg_iv_5day is not None and pd.notna(current_iv) and pd.notna(avg_iv_5day):
            if avg_iv_5day > MIN_NORMALIZATION_DENOMINATOR: vol_trend_factor_value = 1.0 + (current_iv - avg_iv_5day) / avg_iv_5day; actual_vol_trend_source_used_log = f"direct_ivs (curr:{current_iv:.3f}, avg5d:{avg_iv_5day:.3f})"
            else: vri_logger.warning(f"({underlying_symbol_for_vri_log}): Provided avg_iv_5day invalid. Vol trend fallback.")
        if abs(vol_trend_factor_value - 1.0) < MIN_NORMALIZATION_DENOMINATOR: # If not set by direct or direct failed
            if 'volatility' in df.columns and pd.api.types.is_numeric_dtype(df['volatility']) and not df['volatility'].isnull().all():
                mean_opt_iv = df['volatility'].mean()
                if pd.notna(mean_opt_iv) and mean_opt_iv > MIN_NORMALIZATION_DENOMINATOR:
                    approx_5d_avg_iv_fbk = mean_opt_iv * vol_trend_fallback_factor
                    if approx_5d_avg_iv_fbk > MIN_NORMALIZATION_DENOMINATOR: vol_trend_factor_value = 1.0 + (mean_opt_iv - approx_5d_avg_iv_fbk) / approx_5d_avg_iv_fbk; actual_vol_trend_source_used_log = f"fallback_mean_option_iv ({mean_opt_iv:.3f})"
                    else: vri_logger.warning(f"({underlying_symbol_for_vri_log}): Fallback IV trend calc failed (approx 5d avg too small).")
                else: vri_logger.warning(f"({underlying_symbol_for_vri_log}): Mean option IV invalid for fallback trend.")
            else: vri_logger.warning(f"({underlying_symbol_for_vri_log}): No suitable IV data for trend. Trend factor default 1.0.")
        df['vol_trend_factor'] = vol_trend_factor_value; vri_logger.debug(f"Volatility trend factor: {vol_trend_factor_value:.3f} (Source: {actual_vol_trend_source_used_log})")

        vxoi_sign = np.sign(vxoi_numeric.replace(0, 1))

        df['vri'] = (
            vannaxoi_numeric * vxoi_sign *
            (1 + df['gamma_coeff'] * df['vanna_flow_to_vanna_oi_ratio']) *
            df['norm_net_vomma_flow'] *
            df['skew_factor'] *
            df['vol_trend_factor']
        ).fillna(0.0)

        df['vvr'] = (vanna_flow_proxy_abs / vomma_flow_proxy_series.abs().replace(0, np.inf)).fillna(0.0) # VVR uses proxies

        # VFI Calculation (Net Vega Flow / Net Vega OI)
        norm_net_abs_vega_flow_series = pd.Series(0.0, index=df.index, name="norm_net_abs_vega_flow_for_vfi")
        vfi_vega_flow_source_used = f"proxy ('{self.proxy_vega_flow_col}')"

        if self.direct_vega_buy_col in df.columns and self.direct_vega_sell_col in df.columns and \
           pd.api.types.is_numeric_dtype(df[self.direct_vega_buy_col]) and \
           pd.api.types.is_numeric_dtype(df[self.direct_vega_sell_col]) and \
           not (df[self.direct_vega_buy_col].isnull().all() and df[self.direct_vega_sell_col].isnull().all()):
            # Net Vega Flow: vegas_buy - vegas_sell (since vega is positive for long options)
            net_vega_flow_direct = pd.to_numeric(df[self.direct_vega_buy_col], errors='coerce').fillna(0.0) - \
                                   pd.to_numeric(df[self.direct_vega_sell_col], errors='coerce').fillna(0.0)
            norm_net_abs_vega_flow_series = self._normalize_series(net_vega_flow_direct.abs(), 'net_direct_abs_vega_flow_for_vfi')
            vfi_vega_flow_source_used = f"direct ('{self.direct_vega_buy_col}' - '{self.direct_vega_sell_col}')"
            vri_logger.debug(f"Using DIRECT vega flow for VFI. Normed Abs Sum: {norm_net_abs_vega_flow_series.sum():.2f}")
        elif self.proxy_vega_flow_col in df.columns:
            vega_flow_proxy = pd.to_numeric(df[self.proxy_vega_flow_col], errors='coerce').fillna(0.0)
            norm_net_abs_vega_flow_series = self._normalize_series(vega_flow_proxy.abs(), f"{self.proxy_vega_flow_col}_abs_for_vfi_proxy")
            vri_logger.warning(f"Using PROXY vega flow ('{self.proxy_vega_flow_col}') for VFI. Normed Abs Sum: {norm_net_abs_vega_flow_series.sum():.2f}")
        else:
            vri_logger.error(f"Neither direct vega flow columns nor proxy '{self.proxy_vega_flow_col}' are available for VFI. Vega flow component will be zero.")

        df['norm_vxoi_abs'] = self._normalize_series(vxoi_numeric.abs(), 'vxoi_abs_for_vfi')
        df['vfi'] = (norm_net_abs_vega_flow_series / df['norm_vxoi_abs'].replace(0, np.inf)).fillna(0.0)

        vri_logger.debug(f"Final 'vri' (Sum: {df['vri'].sum():.2f}) and 'vfi' (Sum: {df['vfi'].sum():.2f}) calculated.")
        vri_logger.info(f"{calc_name} calculation complete. VFI Vega Flow Source: {vfi_vega_flow_source_used}. Vol Trend Source: {actual_vol_trend_source_used_log}.")
        return df

    # --- SDAG Methods (largely unchanged internally, but inputs from calculate_mspi will be better) ---
    def calculate_sdag_multiplicative(self, df: pd.DataFrame, gamma_exposure: pd.Series, delta_exposure_norm: pd.Series) -> pd.Series:
        # (Implementation from your v2.4.0 is fine here - it takes prepared series)
        # Ensure logging uses self.instance_logger.getChild(...)
        # Ensure _get_config_value is used.
        calc_name = "SDAG_Multiplicative_V2.4.1"; sdag_logger = self.instance_logger.getChild(calc_name); sdag_logger.debug(f"Calculating {calc_name}...")
        gamma_exp_numeric = pd.to_numeric(gamma_exposure, errors='coerce').fillna(0.0); delta_exp_norm_numeric = pd.to_numeric(delta_exposure_norm, errors='coerce').fillna(0.0)
        config_params = self._get_config_value(["strategy_settings", "dag_methodologies", "multiplicative"], {"delta_weight_factor": 0.5}); delta_weight_factor_val = float(config_params.get("delta_weight_factor", 0.5))
        sdag_logger.debug(f"Using delta_weight_factor: {delta_weight_factor_val}. Gamma head: {gamma_exp_numeric.head(2).to_string(index=False) if not gamma_exp_numeric.empty else 'N/A'}, Delta_norm head: {delta_exp_norm_numeric.head(2).to_string(index=False) if not delta_exp_norm_numeric.empty else 'N/A'}")
        result = (gamma_exp_numeric * (1 + delta_exp_norm_numeric * delta_weight_factor_val)).fillna(0.0)
        sdag_logger.debug(f"{calc_name} calculated. Example head: {result.head().to_string(index=False) if not result.empty else 'N/A'}"); return result

    def calculate_sdag_directional(self, df: pd.DataFrame, gamma_exposure: pd.Series, delta_exposure_norm: pd.Series) -> pd.Series:
        # (Implementation from your v2.4.0 is fine here)
        calc_name = "SDAG_Directional_V2.4.1"; sdag_logger = self.instance_logger.getChild(calc_name); sdag_logger.debug(f"Calculating {calc_name}...")
        gamma_exp_numeric = pd.to_numeric(gamma_exposure, errors='coerce').fillna(0.0); delta_exp_norm_numeric = pd.to_numeric(delta_exposure_norm, errors='coerce').fillna(0.0)
        config_params = self._get_config_value(["strategy_settings", "dag_methodologies", "directional"], {"delta_weight_factor": 0.5}); delta_weight_factor_val = float(config_params.get("delta_weight_factor", 0.5))
        sdag_logger.debug(f"Using delta_weight_factor: {delta_weight_factor_val}. Gamma head: {gamma_exp_numeric.head(2).to_string(index=False) if not gamma_exp_numeric.empty else 'N/A'}, Delta_norm head: {delta_exp_norm_numeric.head(2).to_string(index=False) if not delta_exp_norm_numeric.empty else 'N/A'}")
        interaction_term_sign = np.sign(gamma_exp_numeric * delta_exp_norm_numeric).replace(0, 1); magnitude_enhancement_factor = 1 + abs(delta_exp_norm_numeric * delta_weight_factor_val)
        result = (gamma_exp_numeric * interaction_term_sign * magnitude_enhancement_factor).fillna(0.0)
        sdag_logger.debug(f"{calc_name} calculated. Example head: {result.head().to_string(index=False) if not result.empty else 'N/A'}"); return result

    def calculate_sdag_weighted(self, df: pd.DataFrame, gamma_exposure: pd.Series, delta_exposure_raw: pd.Series) -> pd.Series:
        # (Implementation from your v2.4.0 is fine here)
        calc_name = "SDAG_Weighted_V2.4.1"; sdag_logger = self.instance_logger.getChild(calc_name); sdag_logger.debug(f"Calculating {calc_name}...")
        gamma_exp_numeric = pd.to_numeric(gamma_exposure, errors='coerce').fillna(0.0); delta_exp_raw_numeric = pd.to_numeric(delta_exposure_raw, errors='coerce').fillna(0.0)
        config_params = self._get_config_value(["strategy_settings", "dag_methodologies", "weighted"], {"w1_gamma":0.6, "w2_delta":0.4}); w1_gamma_val = float(config_params.get("w1_gamma", 0.6)); w2_delta_val = float(config_params.get("w2_delta", 0.4))
        sdag_logger.debug(f"Using w1_gamma: {w1_gamma_val}, w2_delta: {w2_delta_val}. Gamma head: {gamma_exp_numeric.head(2).to_string(index=False) if not gamma_exp_numeric.empty else 'N/A'}, Delta_raw head: {delta_exp_raw_numeric.head(2).to_string(index=False) if not delta_exp_raw_numeric.empty else 'N/A'}")
        sum_of_weights = w1_gamma_val + w2_delta_val
        if abs(sum_of_weights) < MIN_NORMALIZATION_DENOMINATOR: sdag_logger.warning(f"{calc_name}: Sum of weights ({sum_of_weights:.3f}) is near zero. Returning raw gamma exposure to avoid division by zero."); return gamma_exp_numeric.fillna(0.0)
        result = ((w1_gamma_val * gamma_exp_numeric + w2_delta_val * delta_exp_raw_numeric) / sum_of_weights).fillna(0.0)
        sdag_logger.debug(f"{calc_name} calculated. Example head: {result.head().to_string(index=False) if not result.empty else 'N/A'}"); return result

    def calculate_sdag_volatility_focused(self, df: pd.DataFrame, gamma_exposure: pd.Series, delta_exposure_norm: pd.Series) -> pd.Series:
        # (Implementation from your v2.4.0 is fine here)
        calc_name = "SDAG_VolatilityFocused_V2.4.1"; sdag_logger = self.instance_logger.getChild(calc_name); sdag_logger.debug(f"Calculating {calc_name}...")
        gamma_exp_numeric = pd.to_numeric(gamma_exposure, errors='coerce').fillna(0.0); delta_exp_norm_numeric = pd.to_numeric(delta_exposure_norm, errors='coerce').fillna(0.0)
        config_params = self._get_config_value(["strategy_settings", "dag_methodologies", "volatility_focused"], {"delta_weight_factor": 0.5}); delta_weight_factor_val = float(config_params.get("delta_weight_factor", 0.5))
        sdag_logger.debug(f"Using delta_weight_factor: {delta_weight_factor_val}. Gamma head: {gamma_exp_numeric.head(2).to_string(index=False) if not gamma_exp_numeric.empty else 'N/A'}, Delta_norm head: {delta_exp_norm_numeric.head(2).to_string(index=False) if not delta_exp_norm_numeric.empty else 'N/A'}")
        gamma_exposure_sign = np.sign(gamma_exp_numeric).replace(0, 1)
        result = (gamma_exp_numeric * (1 + delta_exp_norm_numeric * gamma_exposure_sign * delta_weight_factor_val)).fillna(0.0)
        sdag_logger.debug(f"{calc_name} calculated. Example head: {result.head().to_string(index=False) if not result.empty else 'N/A'}"); return result    
        
    # --- E. Main Orchestration Method for Metrics (`calculate_mspi`) ---
    def calculate_mspi(
        self,
        options_df: pd.DataFrame,
        current_time: Optional[time] = None,
        current_iv: Optional[float] = None,
        avg_iv_5day: Optional[float] = None,
        iv_context: Optional[Dict[str, Any]] = None,
        underlying_price: Optional[float] = None, # Explicitly passed by processor
        historical_ohlc_df_for_atr: Optional[pd.DataFrame] = None # Passed by processor
    ) -> pd.DataFrame:
        """
        Orchestrates the calculation of all core metrics including MSPI, its components
        (DAG, TDPI, VRI, SDAGs), and supplementary indices (SAI, ARFI/CFI, SSI).
        All primary metrics are calculated on a per-contract basis.

        Args:
            options_df (pd.DataFrame): Input DataFrame with per-contract option data,
                                       enriched by the processor (e.g., underlying price).
            current_time (Optional[time]): Current market time.
            current_iv (Optional[float]): Current IV of the underlying.
            avg_iv_5day (Optional[float]): 5-day average IV of the underlying.
            iv_context (Optional[Dict[str, Any]]): IV context for weight selection.
            underlying_price (Optional[float]): Current price of the underlying asset.
            historical_ohlc_df_for_atr (Optional[pd.DataFrame]): Historical OHLC for ATR.

        Returns:
            pd.DataFrame: The input DataFrame with all calculated metric columns added.
        """
        calc_name = "MSPI_System_V2.4.1_Orchestration"
        mspi_logger = self.instance_logger.getChild(calc_name)
        mspi_logger.info(f"Calculating {calc_name} START...")
        mspi_logger.debug(f"  Input options_df shape: {options_df.shape if isinstance(options_df, pd.DataFrame) else 'N/A'}")
        mspi_logger.debug(f"  historical_ohlc_df_for_atr provided: {historical_ohlc_df_for_atr is not None and not historical_ohlc_df_for_atr.empty}")
        mspi_logger.debug(f"  avg_iv_5day provided: {avg_iv_5day}, current_iv provided: {current_iv}")
        mspi_logger.debug(f"  underlying_price provided: {underlying_price}")

        if not isinstance(options_df, pd.DataFrame) or options_df.empty:
            mspi_logger.error("Input DataFrame 'options_df' is empty or invalid. Cannot proceed. Returning empty DataFrame.")
            return pd.DataFrame()

        df = options_df.copy()

        # 1. Ensures necessary input columns (underlying price, underlying symbol).
        #    Processor should have already set 'price' to underlying_price and ensured 'underlying_symbol'.
        #    We can add a redundant check here if desired, or rely on processor's prep.
        base_context_cols = ['price', 'underlying_symbol', 'strike', 'opt_kind']
        df, _ = self._ensure_columns(df, base_context_cols, f"{calc_name}_BaseContextCheck")
        if df['price'].eq(0).all() or df['price'].isnull().all(): # Check if underlying price is missing or zero
            if underlying_price is not None and pd.notna(underlying_price) and underlying_price > 0:
                mspi_logger.warning(f"'price' column in DataFrame was zero/NaN, using explicitly passed underlying_price: {underlying_price}")
                df['price'] = float(underlying_price)
            else:
                mspi_logger.error("Underlying price is missing or invalid in DataFrame and not provided as argument. Many calculations will be impacted.")
                # df['price'] will remain 0.0 from _ensure_columns if it was missing.

        # 2. Calls per-contract metric calculations for DAG, TDPI, VRI.
        mspi_logger.info("Calculating core per-contract components: DAG, TDPI, VRI...")
        try:
            df = self.calculate_custom_flow_dag(df)
            df = self.calculate_tdpi(df, current_time, historical_ohlc_df_for_atr=historical_ohlc_df_for_atr)
            df = self.calculate_vri(df, current_iv, avg_iv_5day=avg_iv_5day)
            mspi_logger.info("Core components (DAG, TDPI, VRI) per-contract calculation complete.")
        except Exception as e_core_calc:
            mspi_logger.error(f"Error during core component calculation (DAG, TDPI, or VRI): {e_core_calc}", exc_info=True)
            # Add empty columns for these metrics if they failed, to prevent downstream errors
            for core_col in ['dag_custom', 'tdpi', 'ctr', 'tdfi', 'vri', 'vvr', 'vfi']:
                if core_col not in df.columns: df[core_col] = 0.0
            # Continue, but MSPI will be affected.

        # 3. Prepares inputs and calls individual SDAG calculation methods (per contract).
        mspi_logger.info(f"Calculating SDAGs per contract. Gamma Source for SDAGs: '{self.gamma_col_for_sdag_final}', Delta Source: '{self.delta_exposure_col}'")
        # Ensure base Greek OI columns for SDAGs are present (e.g., gxoi, dxoi, or sgxoi)
        # These are per-contract values.
        sdag_base_input_cols_check = [self.gamma_col_for_sdag_final, self.delta_exposure_col]
        df, _ = self._ensure_columns(df, sdag_base_input_cols_check, f"{calc_name}_SDAG_BaseInputsCheck")

        base_gamma_exposure_series = pd.to_numeric(df.get(self.gamma_col_for_sdag_final), errors='coerce').fillna(0.0)
        base_delta_exposure_raw_series = pd.to_numeric(df.get(self.delta_exposure_col), errors='coerce').fillna(0.0)

        dag_method_configs = self._get_config_value(["strategy_settings", "dag_methodologies"], {})
        enabled_sdag_methods = dag_method_configs.get("enabled", []) if isinstance(dag_method_configs, dict) else []

        # Normalized Delta OI for SDAGs that need it (still per contract)
        norm_delta_col_name_for_sdag = f"{self.delta_exposure_col}_norm_for_sdag"
        needs_normalized_delta_for_sdag = any(method in ["multiplicative", "directional", "volatility_focused"] for method in enabled_sdag_methods)
        base_delta_exposure_norm_series = pd.Series(dtype=float) # Initialize

        if needs_normalized_delta_for_sdag:
            if not base_delta_exposure_raw_series.empty:
                df[norm_delta_col_name_for_sdag] = self._normalize_series(base_delta_exposure_raw_series, norm_delta_col_name_for_sdag)
                base_delta_exposure_norm_series = df[norm_delta_col_name_for_sdag]
                mspi_logger.debug(f"Normalized delta exposure '{self.delta_exposure_col}' into '{norm_delta_col_name_for_sdag}' for SDAGs.")
            else: # Should not happen if _ensure_columns worked, but defensive
                base_delta_exposure_norm_series = pd.Series(0.0, index=df.index, name=norm_delta_col_name_for_sdag)
                df[norm_delta_col_name_for_sdag] = base_delta_exposure_norm_series
                mspi_logger.warning(f"Base delta exposure series '{self.delta_exposure_col}' was empty. '{norm_delta_col_name_for_sdag}' set to zeros.")
        elif norm_delta_col_name_for_sdag not in df.columns: # Ensure column exists even if not "needed" to prevent KeyErrors
             df[norm_delta_col_name_for_sdag] = 0.0
             mspi_logger.debug(f"Normalized delta not strictly needed by enabled SDAGs. Column '{norm_delta_col_name_for_sdag}' added as zeros for completeness.")


        for method_name in enabled_sdag_methods:
            sdag_col_name = f"sdag_{method_name}"
            sdag_norm_col_name = f"{sdag_col_name}_norm"
            calculated_sdag_series: Optional[pd.Series] = None
            try:
                # Prepare series for SDAG functions, ensuring they are not empty Series if base_delta_exposure_norm_series was not populated
                current_gamma_s = base_gamma_exposure_series
                current_delta_norm_s = base_delta_exposure_norm_series if not base_delta_exposure_norm_series.empty else pd.Series(0.0, index=df.index)
                current_delta_raw_s = base_delta_exposure_raw_series if not base_delta_exposure_raw_series.empty else pd.Series(0.0, index=df.index)

                if method_name == "multiplicative":
                    calculated_sdag_series = self.calculate_sdag_multiplicative(df, current_gamma_s, current_delta_norm_s)
                elif method_name == "directional":
                    calculated_sdag_series = self.calculate_sdag_directional(df, current_gamma_s, current_delta_norm_s)
                elif method_name == "weighted":
                    calculated_sdag_series = self.calculate_sdag_weighted(df, current_gamma_s, current_delta_raw_s)
                elif method_name == "volatility_focused":
                    calculated_sdag_series = self.calculate_sdag_volatility_focused(df, current_gamma_s, current_delta_norm_s)
                else:
                    mspi_logger.warning(f"Unknown SDAG method '{method_name}' encountered in config. Skipping.")

                if calculated_sdag_series is not None and isinstance(calculated_sdag_series, pd.Series):
                     df[sdag_col_name] = calculated_sdag_series
                     method_config_current = dag_method_configs.get(method_name, {}) if isinstance(dag_method_configs, dict) else {}
                     if isinstance(method_config_current, dict) and method_config_current.get("weight_in_mspi", 0.0) > 0:
                         df[sdag_norm_col_name] = self._normalize_series(df[sdag_col_name], sdag_col_name)
                     else: # Not weighted in MSPI, so normalized version is 0 or not needed for MSPI sum
                         df[sdag_norm_col_name] = 0.0
                else: # SDAG calculation failed or returned None/wrong type
                    df[sdag_col_name] = 0.0
                    df[sdag_norm_col_name] = 0.0
                    mspi_logger.warning(f"SDAG method '{method_name}' calculation failed or returned invalid type. Columns '{sdag_col_name}' and '{sdag_norm_col_name}' set to 0.")
            except Exception as e_sdag_individual_calc:
                self.instance_logger.error(f"Error during individual SDAG calculation for '{method_name}': {e_sdag_individual_calc}", exc_info=True)
                df[sdag_col_name] = 0.0
                df[sdag_norm_col_name] = 0.0
        mspi_logger.info("Per-contract SDAG methodologies calculation complete.")

        # 4. Normalizes all core components (per contract) for MSPI weighting.
        mspi_logger.debug("Normalizing core MSPI components (DAG, TDPI, VRI) per contract...")
        base_mspi_components_to_normalize = {
            'dag_custom': 'dag_custom_norm',
            'tdpi': 'tdpi_norm',
            'vri': 'vri_norm'
        }
        for base_col, norm_col in base_mspi_components_to_normalize.items():
            if base_col in df.columns:
                df[norm_col] = self._normalize_series(df[base_col], base_col)
            else: # Ensure column exists if base calculation failed
                df[norm_col] = 0.0
                mspi_logger.warning(f"Base MSPI component '{base_col}' not found for normalization. Its norm column '{norm_col}' set to 0.")

        # 5. Applies dynamic weights to normalized components to calculate raw MSPI (per contract).
        current_mspi_weights = self.get_weights(current_time, iv_context)
        df['mspi'] = 0.0 # Initialize MSPI column
        weighted_components_applied_log_list: List[str] = []

        for component_norm_col, weight_val in current_mspi_weights.items():
            if weight_val != 0 and component_norm_col in df.columns:
                component_series_for_sum = pd.to_numeric(df[component_norm_col], errors='coerce').fillna(0.0)
                df['mspi'] += weight_val * component_series_for_sum
                weighted_components_applied_log_list.append(f"{component_norm_col}(w:{weight_val:.2f})")
            elif weight_val != 0: # Weight is non-zero but column is missing
                mspi_logger.warning(f"Weighted component '{component_norm_col}' (weight: {weight_val:.2f}) expected for MSPI but not found in DataFrame columns. Skipping this component.")
        df['mspi'] = df['mspi'].fillna(0.0)
        mspi_logger.info(f"Raw per-contract MSPI calculated from weighted components: {', '.join(weighted_components_applied_log_list) if weighted_components_applied_log_list else 'None_Or_Zero_Weights'}")

        # 6. Normalizes final MSPI score (per contract).
        df['mspi'] = self._normalize_series(df['mspi'], 'final_mspi_score_per_contract')
        mspi_logger.info(f"Final per-contract MSPI score normalized. Example head: {df['mspi'].head().to_string(index=False) if not df.empty else 'N/A_DF_EMPTY'}")

        # 7. Calculates supplementary indices (SAI, ARFI/CFI, SSI) (per contract).
        mspi_logger.info("Calculating supplementary per-contract indices (SAI, ARFI/CFI, SSI)...")
        # SAI
        sign_dag_norm = np.sign(df.get('dag_custom_norm', pd.Series(0.0, index=df.index)).fillna(0.0))
        sign_tdpi_norm = np.sign(df.get('tdpi_norm', pd.Series(0.0, index=df.index)).fillna(0.0))
        sign_vri_norm = np.sign(df.get('vri_norm', pd.Series(0.0, index=df.index)).fillna(0.0))
        df['sai'] = ((sign_dag_norm * sign_tdpi_norm) + \
                     (sign_dag_norm * sign_vri_norm) + \
                     (sign_tdpi_norm * sign_vri_norm)) / 3.0
        df['sai'] = df['sai'].fillna(0.0)
        mspi_logger.debug(f"SAI calculated per contract. Example head: {df['sai'].head().to_string(index=False) if not df.empty else 'N/A_DF_EMPTY'}")

        # ARFI/CFI
        arfi_input_cols_check = [
            self.delta_exposure_col, self.proxy_charm_flow_col, 'charmxoi', # Using charmxoi for td_ratio denominator
            self.proxy_vanna_flow_col, 'vannaxoi', # Using vannaxoi for vx_ratio denominator
            self.direct_delta_buy_col, self.direct_delta_sell_col, self.proxy_delta_flow_col
        ]
        df, _ = self._ensure_columns(df, arfi_input_cols_check, f"{calc_name}_ARFI_InputsCheck")

        # Delta component for ARFI (prioritize direct flow)
        net_delta_flow_for_arfi_abs_series = pd.Series(0.0, index=df.index)
        arfi_delta_flow_source_log = f"proxy ('{self.proxy_delta_flow_col}')"
        if self.direct_delta_buy_col in df.columns and self.direct_delta_sell_col in df.columns and \
           pd.api.types.is_numeric_dtype(df[self.direct_delta_buy_col]) and pd.api.types.is_numeric_dtype(df[self.direct_delta_sell_col]) and \
           not (df[self.direct_delta_buy_col].isnull().all() and df[self.direct_delta_sell_col].isnull().all()):
            net_delta_flow_arfi_calc = pd.to_numeric(df[self.direct_delta_buy_col],errors='coerce').fillna(0.0) - \
                                       pd.to_numeric(df[self.direct_delta_sell_col],errors='coerce').fillna(0.0)
            net_delta_flow_for_arfi_abs_series = net_delta_flow_arfi_calc.abs()
            arfi_delta_flow_source_log = f"direct ('{self.direct_delta_buy_col}' - '{self.direct_delta_sell_col}')"
        elif self.proxy_delta_flow_col in df.columns:
            net_delta_flow_for_arfi_abs_series = pd.to_numeric(df[self.proxy_delta_flow_col],errors='coerce').abs().fillna(0.0)
        else: # Should not happen due to _ensure_columns
            mspi_logger.error("ARFI: Delta flow source columns missing.")

        abs_dxoi_series = pd.to_numeric(df[self.delta_exposure_col], errors='coerce').abs().fillna(0.0)
        df['abs_dx_ratio'] = (net_delta_flow_for_arfi_abs_series / abs_dxoi_series.replace(0, np.inf)).fillna(0.0)

        # Charm (TD) component for ARFI (uses proxy charm flow and charmxoi)
        abs_charm_flow_proxy_series = pd.to_numeric(df[self.proxy_charm_flow_col], errors='coerce').abs().fillna(0.0)
        abs_charmxoi_series = pd.to_numeric(df['charmxoi'], errors='coerce').abs().fillna(0.0)
        df['abs_td_ratio'] = (abs_charm_flow_proxy_series / abs_charmxoi_series.replace(0, np.inf)).fillna(0.0)

        # Vanna (VX) component for ARFI (uses proxy vanna flow and vannaxoi)
        abs_vanna_flow_proxy_series = pd.to_numeric(df[self.proxy_vanna_flow_col], errors='coerce').abs().fillna(0.0)
        abs_vannaxoi_series = pd.to_numeric(df['vannaxoi'], errors='coerce').abs().fillna(0.0)
        df['abs_vx_ratio'] = (abs_vanna_flow_proxy_series / abs_vannaxoi_series.replace(0, np.inf)).fillna(0.0)
        
        df['cfi'] = (df['abs_dx_ratio'] + df['abs_td_ratio'] + df['abs_vx_ratio']) / 3.0
        df['cfi'] = df['cfi'].fillna(0.0)
        mspi_logger.debug(f"CFI/ARFI calculated per contract (Delta Flow Source for ARFI: {arfi_delta_flow_source_log}). Example head: {df['cfi'].head().to_string(index=False) if not df.empty else 'N/A_DF_EMPTY'}")

        # SSI
        # Uses the same current_mspi_weights and normalized component columns as the MSPI calculation
        norm_cols_for_ssi = [
            comp_col for comp_col, weight in current_mspi_weights.items()
            if weight > 0 and comp_col in df.columns
        ]
        df['ssi'] = 0.5 # Default stable value
        if 'strike' in df.columns and len(norm_cols_for_ssi) >= 2: # Need at least 2 components for std dev
            try:
                # Ensure all component columns for SSI are numeric
                for col_ssi_check in norm_cols_for_ssi:
                    if not pd.api.types.is_numeric_dtype(df[col_ssi_check]):
                        df[col_ssi_check] = pd.to_numeric(df[col_ssi_check], errors='coerce').fillna(0.0)
                
                component_values_df_for_ssi = df[norm_cols_for_ssi]
                # Calculate std dev across the component columns for each row (contract)
                std_dev_across_components_per_contract = component_values_df_for_ssi.std(axis=1, ddof=0).fillna(0.0)
                df['ssi'] = (1.0 - std_dev_across_components_per_contract).clip(0, 1).fillna(0.5)
                mspi_logger.debug(f"SSI calculated per contract using components: {norm_cols_for_ssi}. Example head: {df['ssi'].head().to_string(index=False) if not df.empty else 'N/A_DF_EMPTY'}")
            except Exception as e_ssi_calc_detailed:
                mspi_logger.error(f"Detailed SSI calculation failed: {e_ssi_calc_detailed}", exc_info=True)
                df['ssi'] = 0.5 # Fallback on error
        elif 'strike' not in df.columns:
            mspi_logger.warning("SSI calculation skipped: 'strike' column missing (should not happen if _ensure_columns ran).")
        else: # Fewer than 2 weighted components
            mspi_logger.warning(f"SSI calculation skipped: Fewer than 2 weighted MSPI components available for std dev. Components considered: {norm_cols_for_ssi}")
        
        mspi_logger.info("Supplementary per-contract indices (SAI, CFI/ARFI, SSI) calculation complete.")

        # Store the fully processed DataFrame in history (optional, for potential future stateful analysis within ITS)
        # self.processed_df_history.appendleft(df.copy())
        # mspi_logger.debug(f"Added current processed_df to history. History length: {len(self.processed_df_history)}")

        mspi_logger.info(f"{calc_name} Orchestration END. All metrics processed per contract.")
        return df
    
    # --- F. Signal Generation & Level Identification Methods (Operate on Strike-Aggregated Data) ---

    def generate_trading_signals(self, mspi_df: pd.DataFrame) -> Dict[str, Dict[str, list]]:
        """
        Generates discrete trading signals based on strike-aggregated metrics and dynamic thresholds.
        The input mspi_df (per-contract) is first aggregated by strike.

        Args:
            mspi_df (pd.DataFrame): DataFrame containing per-contract MSPI and other metrics,
                                    typically the output of `calculate_mspi`.

        Returns:
            Dict[str, Dict[str, list]]: A dictionary categorizing signals (e.g., 'directional',
                                        'volatility') and their types (e.g., 'bullish', 'expansion'),
                                        containing lists of signal data dictionaries.
        """
        calc_name = "TradingSignals_V2.4.1_Refined" # Updated version in name
        signals_logger = self.instance_logger.getChild(calc_name)
        signals_logger.info(f"Generating {calc_name}...")

        signals_output_dict: Dict[str, Dict[str, list]] = {
            'directional': {'bullish': [], 'bearish': []},
            'volatility': {'expansion': [], 'contraction': []},
            'time_decay': {'pin_risk': [], 'charm_cascade': []},
            'complex': {'structure_change': [], 'flow_divergence': [], 'sdag_conviction': []}
        }
        signal_activation_flags = self._get_config_value(["system_settings", "signal_activation"], {})
        signals_logger.debug(f"Signal activation flags from config: {signal_activation_flags}")

        if not isinstance(mspi_df, pd.DataFrame) or mspi_df.empty:
            signals_logger.warning("Input DataFrame 'mspi_df' is empty or invalid. Cannot generate signals.")
            return signals_output_dict

        # Aggregate per-contract data to strike level for signal evaluation
        # _aggregate_for_levels sums 'mspi', 'tdpi', 'vri', 'sdag_X' and takes 'first' for 'sai', 'ssi', 'cfi', 'ctr', 'tdfi', 'vfi', 'price'
        aggregated_data_for_signals = self._aggregate_for_levels(mspi_df, group_col='strike')
        if aggregated_data_for_signals.empty:
            signals_logger.warning("No data remaining after aggregation by 'strike'. Cannot generate signals.")
            return signals_output_dict

        # Calculate all dynamic thresholds based on the aggregated data
        dynamic_threshold_values: Dict[str, Optional[Union[float, List[float]]]] = {}
        threshold_configurations = self._get_config_value(['strategy_settings', 'thresholds'], {})
        if not isinstance(threshold_configurations, dict):
            signals_logger.error("Threshold configurations in config are invalid (not a dict). Cannot calculate dynamic thresholds for signals.")
            return signals_output_dict # Critical error, cannot proceed

        # Define which metric series from aggregated_data_for_signals to use for each threshold type
        series_name_map_for_thresholds = {
            'sai_high_conviction': 'sai', 'ssi_structure_change': 'ssi', 'ssi_vol_contraction': 'ssi',
            'ssi_conviction_split': 'ssi', 'cfi_flow_divergence': 'cfi', # cfi is ARFI
            'vol_expansion_vri_trigger': 'vri', 'vol_expansion_vfi_trigger': 'vfi',
            'vol_contraction_vri_trigger': 'vri', 'vol_contraction_vfi_trigger': 'vfi',
            'pin_risk_tdpi_trigger': 'tdpi', 'charm_cascade_ctr_trigger': 'ctr',
            'charm_cascade_tdfi_trigger': 'tdfi',
            'arfi_strong_flow_threshold': 'cfi', # ARFI uses 'cfi' column name
            'arfi_low_flow_threshold': 'cfi',   # ARFI uses 'cfi' column name
            'sdag_vf_strong_negative_threshold': 'sdag_volatility_focused' # Assuming this column exists after aggregation
        }

        for threshold_key_name, threshold_config_content in threshold_configurations.items():
            data_series_name_for_calc = series_name_map_for_thresholds.get(threshold_key_name)
            series_to_use_for_calc = aggregated_data_for_signals.get(data_series_name_for_calc) if data_series_name_for_calc else None

            comparison_mode_for_this_calc = 'below' # Default comparison mode
            if 'expansion' in threshold_key_name or 'high_conviction' in threshold_key_name or \
               ('trigger' in threshold_key_name and not ('contraction' in threshold_key_name or 'low' in threshold_key_name)) or \
               'strong_flow' in threshold_key_name:
                comparison_mode_for_this_calc = 'above'
            if 'sai' in threshold_key_name: # SAI high conviction is about absolute magnitude
                comparison_mode_for_this_calc = 'above_abs'
            if 'sdag_vf_strong_negative' in threshold_key_name: # This is specifically for strongly negative values
                comparison_mode_for_this_calc = 'below' # Value should be below a negative threshold

            calculated_threshold_val = self._calculate_dynamic_threshold_wrapper(
                config_path_suffix=[threshold_key_name], # Pass as list
                data_series=series_to_use_for_calc,
                comparison_mode=comparison_mode_for_this_calc
            )
            dynamic_threshold_values[threshold_key_name] = calculated_threshold_val
            if calculated_threshold_val is None:
                signals_logger.warning(f"Threshold for '{threshold_key_name}' could not be determined. Corresponding signals might not trigger accurately.")
        signals_logger.debug(f"Calculated dynamic thresholds for signal generation: {dynamic_threshold_values}")

        # SDAG Conviction Signal specific configurations
        sdag_methodology_configs = self._get_config_value(["strategy_settings", "dag_methodologies"], {})
        enabled_sdag_cols_for_conviction = [
            f"sdag_{m_name}" for m_name in sdag_methodology_configs.get("enabled", [])
            if f"sdag_{m_name}" in aggregated_data_for_signals.columns
        ]
        min_sdag_agreement_count_for_signal = int(sdag_methodology_configs.get("min_agreement_for_conviction_signal", 2))
        if min_sdag_agreement_count_for_signal <= 0: min_sdag_agreement_count_for_signal = 1 # Ensure at least 1

        signals_logger.info(f"Evaluating {len(aggregated_data_for_signals)} aggregated strikes for signals...")
        for _, strike_row_data in aggregated_data_for_signals.iterrows():
            current_strike_context_as_dict = strike_row_data.to_dict()
            strike_value_for_log = current_strike_context_as_dict.get('strike', 'N/A_STRIKE_IN_ROW')

            # Helper to check activation and threshold validity
            def check_signal_active_and_thresholds_valid(signal_config_key: str, *required_threshold_keys_in_map: str) -> bool:
                is_signal_type_active_flag = signal_activation_flags.get(signal_config_key, False)
                if not is_signal_type_active_flag:
                    signals_logger.debug(f"Signal type '{signal_config_key}' is not active in config. Skipping for strike {strike_value_for_log}.")
                    return False
                are_all_thresholds_valid = all(dynamic_threshold_values.get(thr_key) is not None for thr_key in required_threshold_keys_in_map)
                if not are_all_thresholds_valid:
                     signals_logger.warning(f"Signal '{signal_config_key}' for strike {strike_value_for_log} is active, but one or more required thresholds ({required_threshold_keys_in_map}) were invalid/missing. Skipping this specific signal check.")
                return are_all_thresholds_valid

            # --- Directional Signal ---
            if check_signal_active_and_thresholds_valid('directional', 'sai_high_conviction'):
                sai_thresh_val = dynamic_threshold_values['sai_high_conviction']
                sai_metric = current_strike_context_as_dict.get('sai', 0.0)
                mspi_metric = current_strike_context_as_dict.get('mspi', 0.0)
                if isinstance(sai_thresh_val, (int, float)) and abs(sai_metric) >= sai_thresh_val and mspi_metric != 0: # Ensure MSPI is non-zero
                    conv_score = 3.0 + (abs(sai_metric) - sai_thresh_val) * 2.0 # Base score + bonus
                    signal_payload = {**current_strike_context_as_dict, 'conviction_stars': self.map_score_to_stars(conv_score), 'type': 'directional'}
                    bias_label = 'bullish' if mspi_metric > 0 else 'bearish'
                    signals_output_dict['directional'][bias_label].append(signal_payload)
                    signals_logger.debug(f"Directional signal ({bias_label}) at strike {strike_value_for_log} with {signal_payload['conviction_stars']} stars (SAI: {sai_metric:.2f}, MSPI: {mspi_metric:.2f}).")

            # --- Volatility Expansion Signal ---
            if check_signal_active_and_thresholds_valid('volatility_expansion', 'vol_expansion_vri_trigger', 'vol_expansion_vfi_trigger'):
                 vri_exp_thr = dynamic_threshold_values['vol_expansion_vri_trigger']
                 vfi_exp_thr = dynamic_threshold_values['vol_expansion_vfi_trigger']
                 vri_metric = current_strike_context_as_dict.get('vri', 0.0); vfi_metric = current_strike_context_as_dict.get('vfi', 0.0)
                 if isinstance(vri_exp_thr,(int,float)) and isinstance(vfi_exp_thr,(int,float)):
                     if abs(vri_metric) > vri_exp_thr and vfi_metric > vfi_exp_thr:
                          conv_score = 2.0 + (vfi_metric - vfi_exp_thr) * 1.5 # Base score + bonus
                          signals_output_dict['volatility']['expansion'].append({**current_strike_context_as_dict, 'conviction_stars': self.map_score_to_stars(conv_score), 'type': 'vol_expansion'})
                          signals_logger.debug(f"Volatility expansion signal at strike {strike_value_for_log} with {self.map_score_to_stars(conv_score)} stars.")

            # --- Volatility Contraction Signal ---
            if check_signal_active_and_thresholds_valid('volatility_contraction', 'vol_contraction_vri_trigger', 'vol_contraction_vfi_trigger', 'ssi_vol_contraction'):
                 vri_con_thr = dynamic_threshold_values['vol_contraction_vri_trigger']; vfi_con_thr = dynamic_threshold_values['vol_contraction_vfi_trigger']; ssi_con_thr = dynamic_threshold_values['ssi_vol_contraction']
                 vri_metric = current_strike_context_as_dict.get('vri', 0.0); vfi_metric = current_strike_context_as_dict.get('vfi', 0.0); ssi_metric = current_strike_context_as_dict.get('ssi', 0.5)
                 if isinstance(vri_con_thr,(int,float)) and isinstance(vfi_con_thr,(int,float)) and isinstance(ssi_con_thr,(int,float)):
                     if abs(vri_metric) < vri_con_thr and vfi_metric < vfi_con_thr and ssi_metric >= ssi_con_thr:
                          conv_score = 2.0 + (ssi_metric - ssi_con_thr) * 2.0 # Base score + bonus
                          signals_output_dict['volatility']['contraction'].append({**current_strike_context_as_dict, 'conviction_stars': self.map_score_to_stars(conv_score), 'type': 'vol_contraction'})
                          signals_logger.debug(f"Volatility contraction signal at strike {strike_value_for_log} with {self.map_score_to_stars(conv_score)} stars.")

            # --- Time Decay Pin Risk Signal ---
            if check_signal_active_and_thresholds_valid('time_decay_pin_risk', 'pin_risk_tdpi_trigger'):
                 tdpi_pin_thr = dynamic_threshold_values['pin_risk_tdpi_trigger']
                 tdpi_metric = current_strike_context_as_dict.get('tdpi', 0.0)
                 if isinstance(tdpi_pin_thr, (int, float)) and abs(tdpi_metric) > tdpi_pin_thr:
                      conv_score = 1.5 + (abs(tdpi_metric) - tdpi_pin_thr) * 0.5 # Base score + bonus
                      signals_output_dict['time_decay']['pin_risk'].append({**current_strike_context_as_dict, 'conviction_stars': self.map_score_to_stars(conv_score), 'type': 'pin_risk'})
                      signals_logger.debug(f"Pin risk signal at strike {strike_value_for_log} with {self.map_score_to_stars(conv_score)} stars.")

            # --- Time Decay Charm Cascade Signal ---
            if check_signal_active_and_thresholds_valid('time_decay_charm_cascade', 'charm_cascade_ctr_trigger', 'charm_cascade_tdfi_trigger'):
                 ctr_cas_thr = dynamic_threshold_values['charm_cascade_ctr_trigger']; tdfi_cas_thr = dynamic_threshold_values['charm_cascade_tdfi_trigger']
                 ctr_metric = current_strike_context_as_dict.get('ctr', 0.0); tdfi_metric = current_strike_context_as_dict.get('tdfi', 0.0)
                 if isinstance(ctr_cas_thr,(int,float)) and isinstance(tdfi_cas_thr,(int,float)):
                     if ctr_metric > ctr_cas_thr and tdfi_metric > tdfi_cas_thr:
                          conv_score = 1.5 + ctr_metric * 0.3 + tdfi_metric * 0.3 # Base score + bonus
                          signals_output_dict['time_decay']['charm_cascade'].append({**current_strike_context_as_dict, 'conviction_stars': self.map_score_to_stars(conv_score), 'type': 'charm_cascade'})
                          signals_logger.debug(f"Charm cascade signal at strike {strike_value_for_log} with {self.map_score_to_stars(conv_score)} stars.")

            # --- Complex Structure Change Signal ---
            if check_signal_active_and_thresholds_valid('complex_structure_change', 'ssi_structure_change', 'ssi_conviction_split'):
                 ssi_sc_thr = dynamic_threshold_values['ssi_structure_change']; ssi_cs_thr = dynamic_threshold_values['ssi_conviction_split']
                 ssi_metric = current_strike_context_as_dict.get('ssi', 0.5)
                 if isinstance(ssi_sc_thr,(int,float)) and isinstance(ssi_cs_thr,(int,float)):
                     if ssi_metric <= ssi_sc_thr:
                          conv_score = 2.0 + (ssi_sc_thr - ssi_metric) / (ssi_sc_thr - max(0, ssi_sc_thr - ssi_cs_thr*2) + MIN_NORMALIZATION_DENOMINATOR) * 3.0
                          conv_score = min(5.0, max(0.0, conv_score)) # Clamp score
                          signals_output_dict['complex']['structure_change'].append({**current_strike_context_as_dict, 'conviction_stars': self.map_score_to_stars(conv_score), 'type': 'structure_change'})
                          signals_logger.debug(f"Structure change signal at strike {strike_value_for_log} with {self.map_score_to_stars(conv_score)} stars.")

            # --- Complex Flow Divergence Signal (ARFI/CFI based) ---
            if check_signal_active_and_thresholds_valid('complex_flow_divergence', 'cfi_flow_divergence'): # cfi_flow_divergence is key for ARFI tiers
                 arfi_div_tiers = dynamic_threshold_values['cfi_flow_divergence']
                 arfi_metric = current_strike_context_as_dict.get('cfi', 0.0) # 'cfi' column stores ARFI
                 if isinstance(arfi_div_tiers, list) and len(arfi_div_tiers) == 2 and all(isinstance(t, (int,float)) for t in arfi_div_tiers):
                      medium_arfi_thr, high_arfi_thr = sorted(arfi_div_tiers)
                      if arfi_metric > medium_arfi_thr:
                          conv_score = 1.5 # Base for medium
                          if high_arfi_thr > medium_arfi_thr: # Avoid division by zero if tiers are same
                              conv_score += (arfi_metric - medium_arfi_thr) / (high_arfi_thr - medium_arfi_thr + MIN_NORMALIZATION_DENOMINATOR) * 2.0
                          elif arfi_metric > high_arfi_thr: # If tiers are same and metric exceeds it
                              conv_score = 3.5 # Max bonus if tiers are identical and exceeded
                          conv_score = min(5.0, max(0.0, conv_score)) # Clamp score
                          signals_output_dict['complex']['flow_divergence'].append({**current_strike_context_as_dict, 'conviction_stars': self.map_score_to_stars(conv_score), 'type': 'flow_divergence_ARFI'})
                          signals_logger.debug(f"ARFI Flow divergence signal at strike {strike_value_for_log} with {self.map_score_to_stars(conv_score)} stars.")
                 elif arfi_div_tiers is not None:
                     signals_logger.warning(f"ARFI Flow Divergence threshold tiers invalid ({arfi_div_tiers}) for strike {strike_value_for_log}. Signal check skipped.")

            # --- Complex SDAG Conviction Signal ---
            if signal_activation_flags.get("complex_sdag_conviction", True) and enabled_sdag_cols_for_conviction:
                pos_agree_count = sum(1 for sdag_c_name in enabled_sdag_cols_for_conviction if current_strike_context_as_dict.get(sdag_c_name, 0) > 0)
                neg_agree_count = sum(1 for sdag_c_name in enabled_sdag_cols_for_conviction if current_strike_context_as_dict.get(sdag_c_name, 0) < 0)
                if pos_agree_count >= min_sdag_agreement_count_for_signal or neg_agree_count >= min_sdag_agreement_count_for_signal:
                    total_agreements = max(pos_agree_count, neg_agree_count)
                    conv_score = 1.0 + total_agreements * 0.75
                    conv_type = 'sdag_conviction_bullish' if pos_agree_count > neg_agree_count else \
                                ('sdag_conviction_bearish' if neg_agree_count > pos_agree_count else 'sdag_conviction_mixed')
                    if conv_type != 'sdag_conviction_mixed':
                        payload_sdag = {**current_strike_context_as_dict, 'conviction_stars':self.map_score_to_stars(conv_score), 'type':conv_type, 'agree_count':total_agreements, 'methods': enabled_sdag_cols_for_conviction, 'sdag_values':[current_strike_context_as_dict.get(m,0) for m in enabled_sdag_cols_for_conviction]}
                        signals_output_dict['complex']['sdag_conviction'].append(payload_sdag)
                        signals_logger.debug(f"SDAG conviction signal ({conv_type}) at strike {strike_value_for_log} with {self.map_score_to_stars(conv_score)} stars ({total_agreements} methods).")

        signals_logger.info(f"{calc_name} generation complete. Counts logged per type.")
        return signals_output_dict

    def identify_key_levels(self, mspi_df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Identifies Support & Resistance levels based on aggregated MSPI values."""
        # (Implementation from your v2.4.0 is fine here, uses _aggregate_for_levels)
        # Ensure logging uses self.instance_logger.getChild(...)
        calc_name = "KeyLevels_V2.4.1_Refined"; levels_logger = self.instance_logger.getChild(calc_name); levels_logger.info(f"Identifying {calc_name}...")
        empty_df_res = pd.DataFrame(columns=['strike', 'mspi']); req_cols_lvl = ['strike', 'mspi']
        if not isinstance(mspi_df, pd.DataFrame) or mspi_df.empty: levels_logger.warning(f"Input 'mspi_df' empty/invalid."); return empty_df_res.copy(), empty_df_res.copy()
        df_lvl, cols_ok_lvl = self._ensure_columns(mspi_df, req_cols_lvl, calc_name + "_PreAggCheck")
        if not cols_ok_lvl: levels_logger.warning(f"Skipping due to missing/invalid required columns."); return empty_df_res.copy(), empty_df_res.copy()
        try:
            agg_data_lvl = self._aggregate_for_levels(df_lvl, group_col='strike')
            if agg_data_lvl.empty or 'mspi' not in agg_data_lvl.columns: levels_logger.warning(f"No data or 'mspi' after aggregation."); return empty_df_res.copy(), empty_df_res.copy()
            sup_df_lvl = agg_data_lvl[agg_data_lvl['mspi'] > 0].sort_values('mspi', ascending=False).copy()
            res_df_lvl = agg_data_lvl[agg_data_lvl['mspi'] < 0].sort_values('mspi', ascending=True).copy()
            levels_logger.info(f"Identified {len(sup_df_lvl)} S-levels, {len(res_df_lvl)} R-levels."); return sup_df_lvl, res_df_lvl
        except Exception as e_kl_final: levels_logger.error(f"Key level ID error: {e_kl_final}", exc_info=True); return empty_df_res.copy(), empty_df_res.copy()

    def identify_high_conviction_levels(self, mspi_df: pd.DataFrame) -> pd.DataFrame:
        """Identifies High Conviction levels based on SAI and MSPI magnitude."""
        # (Implementation from your v2.4.0 is fine here, uses _aggregate_for_levels and _calculate_dynamic_threshold_wrapper)
        calc_name = "HighConvLevels_V2.4.1_Refined"; hc_logger = self.instance_logger.getChild(calc_name); hc_logger.info(f"Identifying {calc_name}...")
        empty_df_hc = pd.DataFrame(columns=['strike','mspi','sai']); req_cols_hc_lvl = ['strike','mspi','sai']
        if not isinstance(mspi_df, pd.DataFrame) or mspi_df.empty: hc_logger.warning(f"Input 'mspi_df' empty/invalid."); return empty_df_hc.copy()
        df_hc, cols_ok_hc = self._ensure_columns(mspi_df, req_cols_hc_lvl, calc_name + "_PreAggCheck")
        if not cols_ok_hc: hc_logger.warning(f"Skipping due to missing/invalid required columns."); return empty_df_hc.copy()
        try:
            agg_data_hc = self._aggregate_for_levels(df_hc, group_col='strike')
            if agg_data_hc.empty or 'sai' not in agg_data_hc.columns or 'mspi' not in agg_data_hc.columns: hc_logger.warning(f"No data or missing 'sai'/'mspi' after aggregation."); return empty_df_hc.copy()
            sai_thresh_hc = self._calculate_dynamic_threshold_wrapper(['sai_high_conviction'], agg_data_hc['sai'], 'above_abs')
            if sai_thresh_hc is None or not isinstance(sai_thresh_hc, (int,float)): hc_logger.error(f"Invalid SAI threshold ({sai_thresh_hc})."); return empty_df_hc.copy()
            hc_logger.debug(f"Using SAI threshold for high conviction: {sai_thresh_hc:.3f}")
            hc_df_res = agg_data_hc[agg_data_hc['sai'].abs() >= sai_thresh_hc].copy()
            if not hc_df_res.empty: hc_df_res['mspi_abs'] = hc_df_res['mspi'].abs(); hc_df_res = hc_df_res.sort_values('mspi_abs', ascending=False).drop(columns=['mspi_abs'])
            hc_logger.info(f"Identified {len(hc_df_res)} HC levels using SAI threshold >= {sai_thresh_hc:.3f}."); return hc_df_res
        except Exception as e_hc_final: hc_logger.error(f"HC level ID error: {e_hc_final}", exc_info=True); return empty_df_hc.copy()

    def identify_potential_structure_changes(self, mspi_df: pd.DataFrame) -> pd.DataFrame:
        """Identifies potential market structure change points based on low SSI."""
        # (Implementation from your v2.4.0 is fine here, uses _aggregate_for_levels and _calculate_dynamic_threshold_wrapper)
        calc_name = "StructChangePoints_V2.4.1_Refined"; sc_logger = self.instance_logger.getChild(calc_name); sc_logger.info(f"Identifying {calc_name}...")
        empty_df_sc = pd.DataFrame(columns=['strike','mspi','ssi']); req_cols_sc_lvl = ['strike','mspi','ssi']
        if not isinstance(mspi_df, pd.DataFrame) or mspi_df.empty: sc_logger.warning(f"Input 'mspi_df' empty/invalid."); return empty_df_sc.copy()
        df_sc, cols_ok_sc = self._ensure_columns(mspi_df, req_cols_sc_lvl, calc_name + "_PreAggCheck")
        if not cols_ok_sc: sc_logger.warning(f"Skipping due to missing/invalid required columns."); return empty_df_sc.copy()
        try:
            agg_data_sc = self._aggregate_for_levels(df_sc, group_col='strike')
            if agg_data_sc.empty or 'ssi' not in agg_data_sc.columns: sc_logger.warning(f"No data or missing 'ssi' after aggregation."); return empty_df_sc.copy()
            ssi_thresh_sc = self._calculate_dynamic_threshold_wrapper(['ssi_structure_change'], agg_data_sc['ssi'], 'below')
            if ssi_thresh_sc is None or not isinstance(ssi_thresh_sc, (int,float)): sc_logger.error(f"Invalid SSI threshold ({ssi_thresh_sc})."); return empty_df_sc.copy()
            sc_logger.debug(f"Using SSI threshold for structure change: {ssi_thresh_sc:.3f}")
            sc_df_res = agg_data_sc[agg_data_sc['ssi'] <= ssi_thresh_sc].copy()
            if not sc_df_res.empty: sc_df_res = sc_df_res.sort_values('ssi', ascending=True)
            sc_logger.info(f"Identified {len(sc_df_res)} potential structure change points using SSI threshold <= {ssi_thresh_sc:.3f}."); return sc_df_res
        except Exception as e_sc_final: sc_logger.error(f"Structure change ID error: {e_sc_final}", exc_info=True); return empty_df_sc.copy()
        
    # --- G. Stateful Recommendation Engine Methods ---

    def get_enhanced_targets(
        self,
        recommendation_type: str, # 'bullish' or 'bearish'
        entry_price: float,
        atr_val: float,
        support_levels_df: Optional[pd.DataFrame] = None, # DataFrame with 'strike' column
        resistance_levels_df: Optional[pd.DataFrame] = None # DataFrame with 'strike' column
    ) -> Dict[str, Optional[float]]:
        """
        Calculates enhanced stop-loss and target profit levels for a recommendation.

        Uses ATR and provided support/resistance DataFrames (expected from identify_key_levels)
        to set targets. Configuration parameters define multipliers for ATR-based targets
        and minimum ATR distance for considering S/R levels.

        Args:
            recommendation_type (str): 'bullish' or 'bearish'.
            entry_price (float): The ideal entry price for the recommendation.
            atr_val (float): The Average True Range value for the underlying.
            support_levels_df (Optional[pd.DataFrame]): DataFrame of identified support levels.
                                                       Expected columns: 'strike'.
            resistance_levels_df (Optional[pd.DataFrame]): DataFrame of identified resistance levels.
                                                          Expected columns: 'strike'.
        Returns:
            Dict[str, Optional[float]]: Dict with 'stop_loss', 'target_1', 'target_2'.
        """
        target_logger = self.instance_logger.getChild("EnhancedTargets")
        target_logger.debug(f"Calculating targets for {recommendation_type} recommendation. Entry: {entry_price:.2f}, ATR: {atr_val:.4f}")

        targets_config = self._get_config_value(["strategy_settings", "targets"], {})
        min_target_atr_distance_mult = float(targets_config.get("min_target_atr_distance", 0.75))
        stop_loss_atr_multiplier = float(targets_config.get("target_atr_stop_loss_multiplier", 1.5))
        target1_atr_mult_no_sr = float(targets_config.get("target_atr_target1_multiplier_no_sr", 2.0))
        target2_atr_mult_no_sr_from_entry = float(targets_config.get("target_atr_target2_multiplier_no_sr", 3.5)) # T2 from entry if T1 is ATR based
        target2_atr_mult_from_t1_sr = float(targets_config.get("target_atr_target2_multiplier_from_t1", 2.0)) # T2 from T1 if T1 was S/R based

        stop_loss: Optional[float] = None
        target_1: Optional[float] = None
        target_2: Optional[float] = None

        if atr_val <= MIN_NORMALIZATION_DENOMINATOR: # Use the class constant
            target_logger.warning(f"ATR value ({atr_val:.4f}) is too small or invalid. Cannot reliably calculate ATR-based targets/stops. Targets will be None.")
            return {'stop_loss': None, 'target_1': None, 'target_2': None}

        min_target_distance_value = atr_val * min_target_atr_distance_mult

        if recommendation_type == 'bullish':
            stop_loss = entry_price - (stop_loss_atr_multiplier * atr_val)
            target_logger.debug(f"  Bullish SL calculated: {stop_loss:.2f}")

            # Target 1
            nearest_resistance_strike: Optional[float] = None
            if resistance_levels_df is not None and not resistance_levels_df.empty and 'strike' in resistance_levels_df.columns:
                valid_resistances = resistance_levels_df[resistance_levels_df['strike'] > entry_price + min_target_distance_value]
                if not valid_resistances.empty:
                    nearest_resistance_strike = valid_resistances['strike'].min()
                    target_logger.debug(f"  Bullish T1: Nearest valid resistance found at {nearest_resistance_strike:.2f}")

            atr_based_target_1 = entry_price + (target1_atr_mult_no_sr * atr_val)
            if nearest_resistance_strike is not None:
                target_1 = min(nearest_resistance_strike, atr_based_target_1) # Take the closer of S/R or ATR target
                target_logger.debug(f"  Bullish T1: Chosen {target_1:.2f} (min of R: {nearest_resistance_strike:.2f}, ATR T1: {atr_based_target_1:.2f})")
            else:
                target_1 = atr_based_target_1
                target_logger.debug(f"  Bullish T1: No valid resistance found, using ATR-based: {target_1:.2f}")

            # Target 2
            if target_1 is not None: # Only calculate T2 if T1 was successfully determined
                base_for_target2 = target_1 if nearest_resistance_strike is not None and abs(target_1 - nearest_resistance_strike) < MIN_NORMALIZATION_DENOMINATOR else entry_price
                atr_multiplier_for_target2 = target2_atr_mult_from_t1_sr if base_for_target2 == target_1 and nearest_resistance_strike is not None else target2_atr_mult_no_sr_from_entry
                if base_for_target2 == entry_price and nearest_resistance_strike is None : atr_multiplier_for_target2 = target2_atr_mult_no_sr_from_entry # ensure correct multiplier if T1 was ATR based from entry
                
                atr_based_target_2 = base_for_target2 + (atr_multiplier_for_target2 * atr_val)

                next_further_resistance_strike: Optional[float] = None
                if resistance_levels_df is not None and not resistance_levels_df.empty and 'strike' in resistance_levels_df.columns:
                    valid_further_resistances = resistance_levels_df[resistance_levels_df['strike'] > target_1 + min_target_distance_value]
                    if not valid_further_resistances.empty:
                        next_further_resistance_strike = valid_further_resistances['strike'].min()
                        target_logger.debug(f"  Bullish T2: Next valid resistance beyond T1 found at {next_further_resistance_strike:.2f}")
                
                if next_further_resistance_strike is not None:
                    target_2 = min(next_further_resistance_strike, atr_based_target_2)
                    target_logger.debug(f"  Bullish T2: Chosen {target_2:.2f} (min of further R: {next_further_resistance_strike:.2f}, ATR T2: {atr_based_target_2:.2f})")
                else:
                    target_2 = atr_based_target_2
                    target_logger.debug(f"  Bullish T2: No further valid resistance, using ATR-based: {target_2:.2f}")

        elif recommendation_type == 'bearish':
            stop_loss = entry_price + (stop_loss_atr_multiplier * atr_val)
            target_logger.debug(f"  Bearish SL calculated: {stop_loss:.2f}")

            # Target 1
            nearest_support_strike: Optional[float] = None
            if support_levels_df is not None and not support_levels_df.empty and 'strike' in support_levels_df.columns:
                valid_supports = support_levels_df[support_levels_df['strike'] < entry_price - min_target_distance_value]
                if not valid_supports.empty:
                    nearest_support_strike = valid_supports['strike'].max()
                    target_logger.debug(f"  Bearish T1: Nearest valid support found at {nearest_support_strike:.2f}")

            atr_based_target_1 = entry_price - (target1_atr_mult_no_sr * atr_val)
            if nearest_support_strike is not None:
                target_1 = max(nearest_support_strike, atr_based_target_1) # Take the closer of S/R or ATR target
                target_logger.debug(f"  Bearish T1: Chosen {target_1:.2f} (max of S: {nearest_support_strike:.2f}, ATR T1: {atr_based_target_1:.2f})")
            else:
                target_1 = atr_based_target_1
                target_logger.debug(f"  Bearish T1: No valid support found, using ATR-based: {target_1:.2f}")

            # Target 2
            if target_1 is not None:
                base_for_target2 = target_1 if nearest_support_strike is not None and abs(target_1 - nearest_support_strike) < MIN_NORMALIZATION_DENOMINATOR else entry_price
                atr_multiplier_for_target2 = target2_atr_mult_from_t1_sr if base_for_target2 == target_1 and nearest_support_strike is not None else target2_atr_mult_no_sr_from_entry
                if base_for_target2 == entry_price and nearest_support_strike is None : atr_multiplier_for_target2 = target2_atr_mult_no_sr_from_entry
                
                atr_based_target_2 = base_for_target2 - (atr_multiplier_for_target2 * atr_val)

                next_further_support_strike: Optional[float] = None
                if support_levels_df is not None and not support_levels_df.empty and 'strike' in support_levels_df.columns:
                    valid_further_supports = support_levels_df[support_levels_df['strike'] < target_1 - min_target_distance_value]
                    if not valid_further_supports.empty:
                        next_further_support_strike = valid_further_supports['strike'].max()
                        target_logger.debug(f"  Bearish T2: Next valid support beyond T1 found at {next_further_support_strike:.2f}")

                if next_further_support_strike is not None:
                    target_2 = max(next_further_support_strike, atr_based_target_2)
                    target_logger.debug(f"  Bearish T2: Chosen {target_2:.2f} (max of further S: {next_further_support_strike:.2f}, ATR T2: {atr_based_target_2:.2f})")
                else:
                    target_2 = atr_based_target_2
                    target_logger.debug(f"  Bearish T2: No further valid support, using ATR-based: {target_2:.2f}")
        else:
            target_logger.warning(f"Unknown recommendation type: '{recommendation_type}'. Cannot calculate targets.")

        # Ensure targets are logical (T2 further than T1, T1 profitable relative to entry)
        if target_1 is not None and entry_price is not None:
            if (recommendation_type == 'bullish' and target_1 <= entry_price + min_target_distance_value / 2) or \
               (recommendation_type == 'bearish' and target_1 >= entry_price - min_target_distance_value / 2):
                target_logger.debug(f"T1 ({target_1:.2f}) too close to entry ({entry_price:.2f}) or in wrong direction. Invalidating T1 and T2.")
                target_1, target_2 = None, None
        
        if target_1 is not None and target_2 is not None:
            if (recommendation_type == 'bullish' and target_2 <= target_1 + min_target_distance_value / 2) or \
               (recommendation_type == 'bearish' and target_2 >= target_1 - min_target_distance_value / 2):
                target_logger.debug(f"T2 ({target_2:.2f}) too close to T1 ({target_1:.2f}) or in wrong direction. Invalidating T2.")
                target_2 = None
        
        return {'stop_loss': stop_loss, 'target_1': target_1, 'target_2': target_2}

    def get_strategy_recommendations(
        self,
        symbol: str, # Added symbol for clarity and ID generation
        mspi_df: pd.DataFrame, # Expected to be strike-aggregated
        trading_signals: Dict[str, Dict[str, list]],
        key_levels: Tuple[pd.DataFrame, pd.DataFrame], # (support_df, resistance_df)
        conviction_levels: pd.DataFrame, # Strike-aggregated with mspi, sai
        structure_changes: pd.DataFrame, # Strike-aggregated with mspi, ssi
        current_price: float,
        atr: float,
        current_time: Optional[time] = None, # For potential future time-sensitive rec logic
        iv_context: Optional[Dict] = None    # For potential future IV-sensitive rec logic
    ) -> List[Dict[str, Any]]:
        """
        Core logic to generate NEW strategy recommendation dictionaries based on current
        signals, levels, and market context. This method itself is stateless regarding
        previously issued recommendations; it only generates what's currently indicated.
        The stateful management (tracking active recs, exits) happens in
        `update_active_recommendations_and_manage_state`.
        """
        rec_logger = self.instance_logger.getChild("GetStrategyRecs")
        rec_logger.info(f"Generating new strategy recommendations for {symbol} at price {current_price:.2f}, ATR: {atr:.4f}")

        recommendations_generated: List[Dict[str, Any]] = []
        recommendations_config = self._get_config_value(["strategy_settings", "recommendations"], {})
        
        # Ensure inputs are valid DataFrames
        support_df, resistance_df = key_levels if isinstance(key_levels, tuple) and len(key_levels) == 2 and all(isinstance(df, pd.DataFrame) for df in key_levels) else (pd.DataFrame(), pd.DataFrame())
        
        # Helper to safely get values from signal data (which is a dict from aggregated_df row)
        def _safe_get_from_signal(data_dict: Dict, key: str, default: Any = 0.0) -> Any:
            val = data_dict.get(key)
            return default if val is None or pd.isna(val) else val

        # 1. Directional Trade Recommendations (Based on 'directional' and 'sdag_conviction' signals)
        min_dir_stars = int(recommendations_config.get("min_directional_stars_to_issue", 2))
        directional_signals_to_process: List[Dict] = []
        if isinstance(trading_signals.get('directional'), dict):
            directional_signals_to_process.extend(trading_signals['directional'].get('bullish', []))
            directional_signals_to_process.extend(trading_signals['directional'].get('bearish', []))
        if isinstance(trading_signals.get('complex'), dict): # SDAG conviction can also imply direction
             directional_signals_to_process.extend(trading_signals['complex'].get('sdag_conviction', []))

        processed_directional_strikes: set[float] = set()

        for signal_data in sorted(directional_signals_to_process, key=lambda x: x.get('conviction_stars', 0), reverse=True):
            if not isinstance(signal_data, dict): continue
            
            strike_val = _safe_get_from_signal(signal_data, 'strike', None)
            if strike_val is None or strike_val in processed_directional_strikes:
                continue # Skip if no strike or already processed this strike for directional
            
            original_signal_type = str(signal_data.get('type', 'unknown_directional_source')).lower()
            base_stars = int(_safe_get_from_signal(signal_data, 'conviction_stars', 0))

            if base_stars < min_dir_stars: continue # Skip if initial signal not strong enough

            # Determine bias
            bias = "neutral"
            if 'bullish' in original_signal_type: bias = 'bullish'
            elif 'bearish' in original_signal_type: bias = 'bearish'
            elif original_signal_type == 'directional': # From MSPI+SAI
                 bias = 'bullish' if _safe_get_from_signal(signal_data, 'mspi', 0.0) > 0 else 'bearish'
            
            if bias == "neutral": continue # Should not happen if stars >= min_dir_stars for these types

            processed_directional_strikes.add(strike_val) # Mark strike as processed for directional

            # Apply conviction modifiers (can create a helper for this if used elsewhere)
            current_conv_score = float(base_stars) # Start with signal's stars as a base score
            rationale_parts = [f"Base Signal: {original_signal_type.replace('_',' ').title()} ({base_stars}★)"]

            ssi_val = _safe_get_from_signal(signal_data, 'ssi', 0.5)
            ssi_low_thr_val = self._calculate_dynamic_threshold_wrapper(['ssi_structure_change'], mspi_df.get('ssi'), 'below') # Use full mspi_df for context
            if ssi_low_thr_val is not None and isinstance(ssi_low_thr_val, (float,int)) and ssi_val < ssi_low_thr_val:
                current_conv_score += float(recommendations_config.get("conv_mod_ssi_low", -1.0))
                rationale_parts.append(f"LowSSI({ssi_val:.2f})")
            
            # Check for active Volatility Expansion at this strike (or globally if no strike in vol signal)
            vol_exp_active = any(s.get('strike') == strike_val or s.get('strike') is None for s in trading_signals.get('volatility',{}).get('expansion',[]))
            if vol_exp_active:
                current_conv_score += float(recommendations_config.get("conv_mod_vol_expansion", -0.5))
                rationale_parts.append("VolExpActive")

            final_stars_for_rec = self.map_score_to_stars(current_conv_score)
            if final_stars_for_rec < min_dir_stars : continue # Re-check after modifiers

            targets = self.get_enhanced_targets(bias, float(strike_val), atr, support_df, resistance_df)
            
            self.recommendation_id_counter +=1 # Use instance counter
            rec_id = f"DREC_{symbol[:3].upper()}{self.recommendation_id_counter:03d}"

            recommendations_generated.append({
                'id': rec_id, 'symbol': symbol, 'timestamp': datetime.now().isoformat(),
                'category': "Directional Trades", 'signal_type': original_signal_type,
                'strike': float(strike_val), 'direction_label': bias.capitalize(),
                'conviction_stars': final_stars_for_rec, 'raw_conviction_score': round(current_conv_score,2),
                'entry_ideal': float(strike_val), # Entry is at the signal strike
                'stop_loss': targets['stop_loss'], 'target_1': targets['target_1'], 'target_2': targets['target_2'],
                'underlying_price_at_signal': current_price, 'atr_at_signal': atr,
                'mspi_at_signal': _safe_get_from_signal(signal_data, 'mspi'),
                'sai_at_signal': _safe_get_from_signal(signal_data, 'sai'),
                'ssi_at_signal': ssi_val,
                'arfi_at_signal': _safe_get_from_signal(signal_data, 'cfi'), # Using 'cfi' for ARFI
                'rationale': "; ".join(rationale_parts),
                'status': 'NEW_CANDIDATE', # Initial status for stateful management
                'source_signal_data': {k:v for k,v in signal_data.items() if isinstance(v, (int, float, str, bool, list, dict))}
            })

        # 2. Volatility Play Recommendations
        min_vol_stars = int(recommendations_config.get("min_volatility_stars_to_issue", 2))
        if isinstance(trading_signals.get('volatility'), dict):
            for vol_type, vol_signal_list in trading_signals['volatility'].items():
                if not isinstance(vol_signal_list, list): continue
                for signal_data in vol_signal_list:
                    if not isinstance(signal_data, dict): continue
                    base_stars_vol = int(_safe_get_from_signal(signal_data, 'conviction_stars', 0))
                    if base_stars_vol < min_vol_stars: continue
                    
                    strike_val_vol = _safe_get_from_signal(signal_data, 'strike', current_price) # Default to current price if no specific strike
                    current_conv_score_vol = float(base_stars_vol) # Modifiers can be added if needed
                    final_stars_vol = self.map_score_to_stars(current_conv_score_vol)
                    if final_stars_vol < min_vol_stars: continue

                    self.recommendation_id_counter += 1
                    rec_id_vol = f"VREC_{symbol[:3].upper()}{self.recommendation_id_counter:03d}"
                    strat_desc = "Consider Long Vol (e.g., Straddle/Strangle)" if vol_type == 'expansion' else "Consider Short Vol (e.g., Iron Condor/Spreads)"
                    
                    recommendations_generated.append({
                        'id': rec_id_vol, 'symbol': symbol, 'timestamp': datetime.now().isoformat(),
                        'category': "Volatility Plays", 'signal_type': vol_type,
                        'strike': float(strike_val_vol), 'direction_label': vol_type.replace("_", " ").title(),
                        'conviction_stars': final_stars_vol, 'raw_conviction_score': round(current_conv_score_vol,2),
                        'strategy': f"{strat_desc} around {strike_val_vol:.2f}.",
                        'rationale': f"{vol_type.replace('_',' ').title()} signal ({base_stars_vol}★). VRI: {_safe_get_from_signal(signal_data, 'vri'):.2f}, VFI: {_safe_get_from_signal(signal_data, 'vfi'):.2f}, SSI: {_safe_get_from_signal(signal_data, 'ssi'):.2f}",
                        'status': 'NEW_CANDIDATE',
                        'source_signal_data': {k:v for k,v in signal_data.items() if isinstance(v, (int, float, str, bool, list, dict))}
                    })

        # 3. Time Decay / Pin Risk Recommendations
        min_pin_stars = int(recommendations_config.get("min_pinrisk_stars_to_issue", 2))
        if isinstance(trading_signals.get('time_decay'), dict):
            pin_risk_signals = trading_signals['time_decay'].get('pin_risk', [])
            if not isinstance(pin_risk_signals, list): pin_risk_signals = []
            for signal_data in pin_risk_signals:
                if not isinstance(signal_data, dict): continue
                base_stars_pin = int(_safe_get_from_signal(signal_data, 'conviction_stars', 0))
                if base_stars_pin < min_pin_stars: continue

                strike_val_pin = _safe_get_from_signal(signal_data, 'strike', None)
                if strike_val_pin is None: continue
                current_conv_score_pin = float(base_stars_pin) # Modifiers can be added
                final_stars_pin = self.map_score_to_stars(current_conv_score_pin)
                if final_stars_pin < min_pin_stars: continue

                self.recommendation_id_counter += 1
                rec_id_pin = f"TREC_{symbol[:3].upper()}{self.recommendation_id_counter:03d}"

                recommendations_generated.append({
                    'id': rec_id_pin, 'symbol': symbol, 'timestamp': datetime.now().isoformat(),
                    'category': "Range Bound Ideas", 'signal_type': 'pin_risk',
                    'strike': float(strike_val_pin), 'direction_label': "Pin Risk",
                    'conviction_stars': final_stars_pin, 'raw_conviction_score': round(current_conv_score_pin,2),
                    'strategy': f"Potential Pin at {strike_val_pin:.2f}. Consider expiry credit plays (e.g., Iron Butterfly/Condor centered here).",
                    'rationale': f"Pin Risk signal ({base_stars_pin}★). TDPI: {_safe_get_from_signal(signal_data, 'tdpi'):.0f}",
                    'status': 'NEW_CANDIDATE',
                    'source_signal_data': {k:v for k,v in signal_data.items() if isinstance(v, (int, float, str, bool, list, dict))}
                })
        
        # 4. Cautionary Notes (from Structure Change or Strong Divergence)
        min_caution_stars = int(recommendations_config.get("min_caution_stars_to_issue", 2))
        if isinstance(trading_signals.get('complex'), dict):
            structure_change_signals = trading_signals['complex'].get('structure_change', [])
            if not isinstance(structure_change_signals, list): structure_change_signals = []
            for signal_data in structure_change_signals:
                 if not isinstance(signal_data, dict): continue
                 base_stars_sc = int(_safe_get_from_signal(signal_data, 'conviction_stars', 0))
                 if base_stars_sc < min_caution_stars: continue
                 strike_val_sc = _safe_get_from_signal(signal_data, 'strike', None)
                 if strike_val_sc is None: continue
                 
                 self.recommendation_id_counter += 1
                 rec_id_sc = f"CREC_{symbol[:3].upper()}{self.recommendation_id_counter:03d}"
                 recommendations_generated.append({
                     'id': rec_id_sc, 'symbol': symbol, 'timestamp': datetime.now().isoformat(),
                     'category': "Cautionary Notes", 'signal_type': 'structure_change',
                     'strike': float(strike_val_sc), 'direction_label': "Instability Warning",
                     'conviction_stars': base_stars_sc, # Use base stars for cautions
                     'strategy': f"Market structure at {strike_val_sc:.2f} appears unstable. Caution advised.",
                     'rationale': f"Structure Change signal ({base_stars_sc}★). SSI: {_safe_get_from_signal(signal_data, 'ssi'):.2f}",
                     'status': 'NOTE', # Cautions are notes
                     'source_signal_data': {k:v for k,v in signal_data.items() if isinstance(v, (int, float, str, bool, list, dict))}
                 })

        rec_logger.info(f"Generated {len(recommendations_generated)} new candidate recommendations for {symbol}.")
        return recommendations_generated

    def _is_immediate_exit_warranted(self, recommendation: Dict[str, Any], current_aggregated_mspi_df: pd.DataFrame, current_price: float) -> Optional[str]:
        """Checks if an active recommendation warrants an immediate exit based on new market data."""
        exit_logger = self.instance_logger.getChild("ExitCheck")
        exit_config = self._get_config_value(["strategy_settings", "exits"], {})
        rec_strike = recommendation.get('strike')
        rec_direction = recommendation.get('direction_label','').lower() # Use 'direction_label'
        rec_id_log = recommendation.get('id', 'N/A_REC_ID')
        rec_category = recommendation.get('category', '').lower()

        if rec_category != "directional trades" or rec_strike is None or rec_direction not in ['bullish', 'bearish']:
            # Only apply these exits to active directional trades with a strike
            return None 

        # 1. Stop Loss Check
        stop_loss_level = recommendation.get('stop_loss')
        if stop_loss_level is not None and pd.notna(stop_loss_level):
            if (rec_direction == 'bullish' and current_price <= stop_loss_level):
                exit_logger.info(f"EXIT (Stop Loss): Rec ID {rec_id_log}, Price {current_price:.2f} <= SL {stop_loss_level:.2f}")
                return "stop_loss_hit"
            if (rec_direction == 'bearish' and current_price >= stop_loss_level):
                exit_logger.info(f"EXIT (Stop Loss): Rec ID {rec_id_log}, Price {current_price:.2f} >= SL {stop_loss_level:.2f}")
                return "stop_loss_hit"
        
        # 2. Target Hit Check (T2 is usually the final target for exit)
        target_2_level = recommendation.get('target_2')
        if target_2_level is not None and pd.notna(target_2_level):
            if (rec_direction == 'bullish' and current_price >= target_2_level):
                exit_logger.info(f"EXIT (Target 2): Rec ID {rec_id_log}, Price {current_price:.2f} >= T2 {target_2_level:.2f}")
                return "target_2_hit"
            if (rec_direction == 'bearish' and current_price <= target_2_level):
                exit_logger.info(f"EXIT (Target 2): Rec ID {rec_id_log}, Price {current_price:.2f} <= T2 {target_2_level:.2f}")
                return "target_2_hit"
        elif recommendation.get('target_1') is not None and pd.notna(recommendation.get('target_1')): # If no T2, T1 is final
            target_1_level = recommendation.get('target_1')
            if (rec_direction == 'bullish' and current_price >= target_1_level):
                exit_logger.info(f"EXIT (Target 1 as final): Rec ID {rec_id_log}, Price {current_price:.2f} >= T1 {target_1_level:.2f}")
                return "target_1_hit"
            if (rec_direction == 'bearish' and current_price <= target_1_level):
                exit_logger.info(f"EXIT (Target 1 as final): Rec ID {rec_id_log}, Price {current_price:.2f} <= T1 {target_1_level:.2f}")
                return "target_1_hit"

        # --- Metric-based exit conditions (using current_aggregated_mspi_df) ---
        strike_data_dict_for_exit: Optional[Dict[str, Any]] = None
        if not current_aggregated_mspi_df.empty and 'strike' in current_aggregated_mspi_df.columns:
            strike_data_rows_for_exit = current_aggregated_mspi_df[current_aggregated_mspi_df['strike'] == rec_strike]
            if not strike_data_rows_for_exit.empty:
                strike_data_dict_for_exit = strike_data_rows_for_exit.iloc[0].to_dict()
        
        if not strike_data_dict_for_exit:
            exit_logger.debug(f"Rec ID {rec_id_log}: Strike {rec_strike} data not found in current aggregated MSPI for metric-based exit checks.")
            return None # Cannot perform metric-based exits without current data for the strike

        # 3. MSPI Flip
        mspi_at_entry = recommendation.get('mspi_at_signal') # MSPI at time of signal generation
        current_mspi_at_strike = strike_data_dict_for_exit.get('mspi', 0.0)
        mspi_flip_threshold_val = float(exit_config.get("mspi_flip_threshold", 0.7))
        if mspi_at_entry is not None and pd.notna(mspi_at_entry): # Ensure MSPI at entry was valid
            if (rec_direction == 'bullish' and current_mspi_at_strike < -mspi_flip_threshold_val) or \
               (rec_direction == 'bearish' and current_mspi_at_strike > mspi_flip_threshold_val):
                exit_logger.info(f"EXIT (MSPI Flip): Rec ID {rec_id_log} ({rec_direction} at {rec_strike}). MSPI Entry: {mspi_at_entry:.2f}, Now: {current_mspi_at_strike:.2f}. Threshold: +/-{mspi_flip_threshold_val:.2f}")
                return "mspi_strong_flip"
        
        # 4. SSI Low (Structure Instability)
        current_ssi_at_strike = strike_data_dict_for_exit.get('ssi', 0.5)
        ssi_exit_thresh_config = self._get_config_value(["strategy_settings", "thresholds", "ssi_exit_stars_threshold"], {"type":"fixed", "value":0.15}) # Using a different threshold key from config for exit
        ssi_exit_threshold_val = self._calculate_dynamic_threshold(ssi_exit_thresh_config, current_aggregated_mspi_df.get('ssi'), 'below')
        
        if ssi_exit_threshold_val is not None and isinstance(ssi_exit_threshold_val, (float, int)) and current_ssi_at_strike < ssi_exit_threshold_val:
             exit_logger.info(f"EXIT (SSI Low): Rec ID {rec_id_log} ({rec_direction} at {rec_strike}). SSI {current_ssi_at_strike:.2f} < Threshold {ssi_exit_threshold_val:.2f}")
             return "ssi_structure_instability_exit"
        
        # Placeholder for ARFI exit (needs ARFI divergence signal logic from generate_trading_signals)
        # For now, this would require passing new_signals into _is_immediate_exit_warranted
        # or re-calculating a specific ARFI exit condition here.
        # We'll keep it simple and rely on the main loop checking new strong contradictory signals.

        return None # No immediate exit condition met

    def _adjust_active_recommendation_parameters(self, recommendation: Dict[str, Any], support_df: pd.DataFrame, resistance_df: pd.DataFrame, current_price: float, current_atr: float) -> bool:
        """Adjusts SL/TP for an active directional recommendation if new levels or ATR warrant it (e.g., trailing SL)."""
        adj_logger = self.instance_logger.getChild("AdjustRecParams")
        updated_params_flag = False
        rec_id_log = recommendation.get('id', 'N/A_REC_ID')
        rec_strike_adj = recommendation.get('strike')
        rec_direction_adj = recommendation.get('direction_label','').lower()
        
        if recommendation.get('category','').lower() != "directional trades" or rec_strike_adj is None or rec_direction_adj not in ['bullish', 'bearish']:
            return False # Only adjust directional trades with valid strike and direction

        # Recalculate targets based on current S/R, price, and ATR
        new_target_params = self.get_enhanced_targets(
            recommendation_type=rec_direction_adj,
            entry_price=float(recommendation.get('entry_ideal', rec_strike_adj)), # Use original ideal entry for target recalcs for consistency
            atr_val=current_atr,
            support_levels_df=support_df,
            resistance_levels_df=resistance_df
        )
        
        current_stop_loss = recommendation.get('stop_loss')
        new_calculated_stop_loss = new_target_params.get('stop_loss')

        # Trail Stop Loss: Only move SL in the direction of the trade if the new calculation is more favorable
        if new_calculated_stop_loss is not None and pd.notna(new_calculated_stop_loss):
            can_trail_sl = False
            if rec_direction_adj == 'bullish':
                # If current SL is None, or new SL is higher (better) AND still below current price
                if (current_stop_loss is None or not pd.notna(current_stop_loss) or new_calculated_stop_loss > current_stop_loss) and new_calculated_stop_loss < current_price:
                    can_trail_sl = True
            elif rec_direction_adj == 'bearish':
                # If current SL is None, or new SL is lower (better) AND still above current price
                if (current_stop_loss is None or not pd.notna(current_stop_loss) or new_calculated_stop_loss < current_stop_loss) and new_calculated_stop_loss > current_price:
                    can_trail_sl = True
            
            if can_trail_sl:
                old_sl_str = f"{current_stop_loss:.2f}" if current_stop_loss is not None and pd.notna(current_stop_loss) else "None"
                recommendation['stop_loss'] = new_calculated_stop_loss
                updated_params_flag = True
                adj_logger.info(f"Rec ID {rec_id_log}: Trailed Stop Loss from {old_sl_str} to {new_calculated_stop_loss:.2f}")

        # For targets, we might just update them if they differ, rather than "trailing"
        # This part assumes we simply refresh targets based on new S/R landscape
        for target_key in ['target_1', 'target_2']:
            old_target_val = recommendation.get(target_key)
            new_target_val = new_target_params.get(target_key)
            
            old_target_str = f"{old_target_val:.2f}" if old_target_val is not None and pd.notna(old_target_val) else "None"
            new_target_str = f"{new_target_val:.2f}" if new_target_val is not None and pd.notna(new_target_val) else "None"

            if (new_target_val is None and old_target_val is not None and pd.notna(old_target_val)) or \
               (new_target_val is not None and pd.notna(new_target_val) and (old_target_val is None or not pd.notna(old_target_val) or abs(new_target_val - old_target_val) > MIN_NORMALIZATION_DENOMINATOR * 10)): # Check for meaningful change
                recommendation[target_key] = new_target_val
                updated_params_flag = True
                adj_logger.info(f"Rec ID {rec_id_log}: Updated {target_key} from {old_target_str} to {new_target_str}")
        
        if updated_params_flag:
            recommendation['last_updated_ts'] = datetime.now().isoformat() # Use 'last_updated_ts' for adjustments
            recommendation['status'] = 'ACTIVE_ADJUSTED' # Update status
        return updated_params_flag

    def update_active_recommendations_and_manage_state(
        self,
        symbol: str,
        latest_processed_df: pd.DataFrame, # This is the full per-contract df from calculate_mspi
        current_underlying_price: float,
        current_atr: float, # Pass current ATR
        current_time: Optional[time] = None,
        iv_context: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        state_mgr_logger = self.instance_logger.getChild("StatefulRecManager")
        price_disp_str = f"{current_underlying_price:.2f}" if current_underlying_price is not None else "N/A"
        state_mgr_logger.info(f"--- Recommendation State Update Cycle START for {symbol} (Price: {price_disp_str}, ATR: {current_atr:.4f}) ---")

        if self.current_symbol_being_managed != symbol:
            state_mgr_logger.info(f"Symbol changed from '{self.current_symbol_being_managed}' to '{symbol}'. Resetting active recommendations and ID counter.")
            self.active_recommendations.clear()
            self.current_symbol_being_managed = symbol
            self.recommendation_id_counter = 0

        if not isinstance(latest_processed_df, pd.DataFrame) or latest_processed_df.empty:
            state_mgr_logger.error(f"Received empty or invalid latest_processed_df for {symbol}. Cannot update recommendations.")
            return self.active_recommendations.copy() # Return current list if no new data
        
        # Add current processed_df to history (optional for this method's direct logic but good for ITS state)
        # self.processed_df_history.appendleft(latest_processed_df.copy()) 

        # --- Generate current signals and levels based on latest_processed_df ---
        # Important: Signals and levels are derived from strike-aggregated data.
        aggregated_strike_df = self._aggregate_for_levels(latest_processed_df.copy(), group_col='strike')
        if aggregated_strike_df.empty:
            state_mgr_logger.warning(f"Aggregated MSPI DataFrame is empty for {symbol}. No signal-based updates or new recommendations possible this cycle.")
            # We might still check price-based exits for existing recommendations
        
        current_trading_signals = self.generate_trading_signals(latest_processed_df.copy()) # Use original for full context if needed by signals
        current_key_levels = self.identify_key_levels(latest_processed_df.copy())
        current_conviction_levels = self.identify_high_conviction_levels(latest_processed_df.copy())
        current_structure_changes = self.identify_potential_structure_changes(latest_processed_df.copy())
        
        recommendations_to_remove_indices: List[int] = []
        for idx, active_rec in enumerate(self.active_recommendations):
            if active_rec.get('symbol') != symbol: continue # Should be filtered by current_symbol_being_managed

            exit_reason = self._is_immediate_exit_warranted(active_rec, aggregated_strike_df, current_underlying_price)
            if exit_reason:
                active_rec['status'] = 'EXITED_AUTO'
                active_rec['exit_reason'] = exit_reason
                active_rec['exit_timestamp'] = datetime.now().isoformat()
                active_rec['exit_price'] = current_underlying_price
                recommendations_to_remove_indices.append(idx)
                state_mgr_logger.info(f"Recommendation ID {active_rec.get('id')} for {symbol} EXITED due to: {exit_reason} at price {current_underlying_price:.2f}")
                continue

            # If not exited, try to adjust parameters for directional trades
            if active_rec.get('category') == "Directional Trades":
                if self._adjust_active_recommendation_parameters(active_rec, current_key_levels[0], current_key_levels[1], current_underlying_price, current_atr):
                    state_mgr_logger.info(f"Adjusted parameters for active Rec ID {active_rec['id']} for {symbol}. New status: {active_rec.get('status')}")
        
        # Remove exited recommendations (iterating in reverse to avoid index issues)
        for idx_to_remove in sorted(recommendations_to_remove_indices, reverse=True):
            del self.active_recommendations[idx_to_remove]
        state_mgr_logger.info(f"{len(recommendations_to_remove_indices)} recs exited. {len(self.active_recommendations)} remaining before adding new.")

        # Generate new candidate recommendations based on current market state
        new_candidate_recs = self.get_strategy_recommendations(
            symbol=symbol, mspi_df=aggregated_strike_df, trading_signals=current_trading_signals,
            key_levels=current_key_levels, conviction_levels=current_conviction_levels,
            structure_changes=current_structure_changes, current_price=current_underlying_price,
            atr=current_atr, current_time=current_time, iv_context=iv_context
        )
        
        min_reissue_s = float(self._get_config_value(["strategy_settings", "recommendations", "min_reissue_time_seconds"], 300))
        new_recs_added_this_cycle_count = 0

        for new_rec_candidate in new_candidate_recs:
            is_effectively_duplicate = False
            for existing_active_rec in self.active_recommendations:
                # Check for near-identical, recently issued active recommendations
                if existing_active_rec.get('category') == new_rec_candidate.get('category') and \
                   existing_active_rec.get('signal_type') == new_rec_candidate.get('signal_type') and \
                   existing_active_rec.get('strike') == new_rec_candidate.get('strike') and \
                   existing_active_rec.get('direction_label') == new_rec_candidate.get('direction_label'):
                    
                    issued_dt_existing = parse_timestamp(existing_active_rec.get('timestamp')) # Use 'timestamp' from get_strategy_recommendations
                    issued_dt_new = parse_timestamp(new_rec_candidate.get('timestamp'))
                    if issued_dt_existing and issued_dt_new:
                        time_difference_seconds = abs((issued_dt_new - issued_dt_existing).total_seconds())
                        if time_difference_seconds < min_reissue_s and existing_active_rec.get('status','').startswith('ACTIVE'):
                            is_effectively_duplicate = True
                            state_mgr_logger.debug(f"Skipping new candidate (Strike {new_rec_candidate.get('strike')}, Type {new_rec_candidate.get('signal_type')}) as similar to active Rec ID {existing_active_rec.get('id')} issued recently.")
                            break
            if not is_effectively_duplicate:
                # If not a recent duplicate, assign its final ID from the instance counter (already incremented in get_strategy_recs)
                # and set its initial status for tracking.
                # The ID should already be in new_rec_candidate from get_strategy_recommendations
                new_rec_candidate['status'] = 'ACTIVE_NEW' # Mark as newly added and active
                new_rec_candidate['timestamp'] = datetime.now().isoformat() # Overwrite with current timestamp for state management
                new_rec_candidate['mspi_at_entry'] = new_rec_candidate.get('mspi_at_signal') # Store context at entry
                # Add other relevant "at entry" context if needed
                self.active_recommendations.append(new_rec_candidate)
                new_recs_added_this_cycle_count += 1
                state_mgr_logger.info(f"Added NEW recommendation ID {new_rec_candidate.get('id')} for {symbol}: {new_rec_candidate.get('category')}/{new_rec_candidate.get('signal_type')} ({new_rec_candidate.get('direction_label')})")
        
        state_mgr_logger.info(f"{new_recs_added_this_cycle_count} new recommendations added. Total active now for {symbol}: {len(self.active_recommendations)}")
        state_mgr_logger.info(f"--- Recommendation State Update Cycle END for {symbol} ---")
        return self.active_recommendations.copy() # Return a copy of the list

    def get_strategy_recommendations_stateless_snapshot(
        self,
        symbol: str,
        options_df: pd.DataFrame, # Raw per-contract options data
        current_price: float,
        # atr: float, # ATR will be calculated inside using historical_ohlc
        current_time: Optional[time] = None,
        current_iv: Optional[float] = None,
        avg_iv_5day: Optional[float] = None,
        iv_context: Optional[Dict] = None,
        historical_ohlc_df_for_atr: Optional[pd.DataFrame] = None
    ) -> List[Dict[str, Any]]:
        snapshot_logger = self.instance_logger.getChild("StatelessRecSnapshot")
        snapshot_logger.info(f"Generating stateless recommendation snapshot for {symbol} at price {current_price:.2f}...")
        
        original_instance_rec_id_counter = self.recommendation_id_counter # Store instance counter
        self.recommendation_id_counter = 0 # Reset for this stateless call to ensure fresh IDs

        try:
            # 1. Calculate all metrics using the full options_df
            processed_mspi_df_snapshot = self.calculate_mspi(
                options_df=options_df, current_time=current_time, current_iv=current_iv,
                avg_iv_5day=avg_iv_5day, iv_context=iv_context, underlying_price=current_price,
                historical_ohlc_df_for_atr=historical_ohlc_df_for_atr
            )
            if processed_mspi_df_snapshot.empty:
                snapshot_logger.error("MSPI calculation failed or returned empty DataFrame for stateless snapshot. Cannot generate recommendations.")
                return []
            
            # 2. Aggregate metrics to strike level for signals and levels
            aggregated_strike_df_snapshot = self._aggregate_for_levels(processed_mspi_df_snapshot.copy(), group_col='strike')
            if aggregated_strike_df_snapshot.empty:
                snapshot_logger.warning("Aggregated MSPI DataFrame for stateless snapshot is empty. No recommendations will be generated.")
                return []

            # 3. Generate signals and identify levels based on this snapshot's processed data
            trading_signals_snapshot = self.generate_trading_signals(processed_mspi_df_snapshot.copy()) # Use original for context if needed
            key_levels_snapshot = self.identify_key_levels(processed_mspi_df_snapshot.copy())
            conviction_levels_snapshot = self.identify_high_conviction_levels(processed_mspi_df_snapshot.copy())
            structure_changes_snapshot = self.identify_potential_structure_changes(processed_mspi_df_snapshot.copy())
            
            # 4. Calculate ATR for this snapshot context
            # Ensure 'price' and 'underlying_symbol' are in processed_mspi_df_snapshot for _get_atr
            # The 'price' column in processed_mspi_df_snapshot should be the underlying_price
            price_for_atr_ss = current_price # Use the directly passed current_price
            if 'underlying_symbol' in processed_mspi_df_snapshot.columns and not processed_mspi_df_snapshot['underlying_symbol'].empty:
                symbol_for_atr_ss = processed_mspi_df_snapshot['underlying_symbol'].iloc[0]
            else:
                symbol_for_atr_ss = symbol # Fallback to the main symbol if not in df
            
            atr_for_snapshot = self._get_atr(symbol_for_atr_ss, price_for_atr_ss, history_df=historical_ohlc_df_for_atr)
            snapshot_logger.debug(f"ATR calculated for stateless snapshot of {symbol}: {atr_for_snapshot:.4f}")

            # 5. Generate recommendations using the main recommendation logic
            # This call will use the temporarily reset self.recommendation_id_counter for fresh IDs
            recommendations_list_snapshot = self.get_strategy_recommendations(
                symbol=symbol, mspi_df=aggregated_strike_df_snapshot, trading_signals=trading_signals_snapshot,
                key_levels=key_levels_snapshot, conviction_levels=conviction_levels_snapshot,
                structure_changes=structure_changes_snapshot, current_price=current_price,
                atr=atr_for_snapshot, current_time=current_time, iv_context=iv_context
            )
            snapshot_logger.info(f"Stateless snapshot generated {len(recommendations_list_snapshot)} recommendations for {symbol}.")
            return recommendations_list_snapshot
        except Exception as e_stateless:
            snapshot_logger.error(f"Error during stateless recommendation snapshot generation for {symbol}: {e_stateless}", exc_info=True)
            return []
        finally:
            self.recommendation_id_counter = original_instance_rec_id_counter # IMPORTANT: Restore original instance counter
            
    # --- H. Standalone Test Block (`if __name__ == '__main__':`) ---
    if __name__ == '__main__':
        # Setup basic logging if this script is run directly
        if not logging.getLogger().hasHandlers() or not any(isinstance(h, logging.StreamHandler) for h in logging.getLogger().handlers):
            # Configure root logger if no handlers are present
            logging.basicConfig(
                level=logging.DEBUG, # Use DEBUG for detailed test output
                format='[%(levelname)s] (%(module)s-%(funcName)s:%(lineno)d) %(asctime)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
        # Ensure the instance logger also gets a high level of detail for testing
        main_its_test_logger = logging.getLogger(__name__ + ".__main__") # Specific logger for this test block
        main_its_test_logger.setLevel(logging.DEBUG)
        # Also set the class's default module logger to DEBUG for more verbosity from ITS methods
        logger.setLevel(logging.DEBUG)


        main_its_test_logger.info("--- IntegratedTradingSystem V2.4.1 (Stateful - Full) Direct Test Run ---")

        # Attempt to determine script directory for config loading
        try:
            script_dir_for_test = os.path.dirname(os.path.abspath(__file__))
        except NameError: # __file__ is not defined if running in some interactive environments
            script_dir_for_test = os.getcwd()
        test_config_file_path = os.path.join(script_dir_for_test, "config_v2.json")
        main_its_test_logger.debug(f"Attempting to load test config from: {test_config_file_path}")

        if not os.path.exists(test_config_file_path):
            main_its_test_logger.warning(f"Test config '{test_config_file_path}' not found. Creating dummy config file using internal DEFAULT_CONFIG for testing purposes.")
            try:
                with open(test_config_file_path, 'w') as f_dummy_cfg_out:
                    # DEFAULT_CONFIG should be defined within the class or globally in this file
                    json.dump(DEFAULT_CONFIG, f_dummy_cfg_out, indent=2)
                main_its_test_logger.info(f"Created dummy config file at '{test_config_file_path}'.")
            except Exception as e_create_dummy_cfg_err:
                main_its_test_logger.error(f"Could not create dummy config file: {e_create_dummy_cfg_err}. Some tests might rely on default values hardcoded in DEFAULT_CONFIG.")

        # Instantiate the system
        its_test_instance = IntegratedTradingSystem(config_path=test_config_file_path)
        # Override instance logger level to DEBUG for detailed test output from ITS methods
        its_test_instance.instance_logger.setLevel(logging.DEBUG)
        for handler in its_test_instance.instance_logger.handlers: # Ensure handlers also reflect this
            handler.setLevel(logging.DEBUG)

        main_its_test_logger.info("ITS instance created for testing.")

        # --- 1. Sets up test configuration and sample data. ---
        main_its_test_logger.info("--- Setting up Enhanced Sample Data for Testing ---")
        sample_strikes = np.arange(480, 521, 5).astype(float) # More strikes around ATM
        test_symbol_name = 'TESTXYZ'
        current_underlying_test_price = 500.00

        sample_options_data_list = []
        for strike_price_val in sample_strikes:
            # Base data for both call and put at this strike
            base_option_data = {
                'strike': strike_price_val,
                'symbol': f"{test_symbol_name}251231{'C' if strike_price_val >= current_underlying_test_price else 'P'}{int(strike_price_val*1000):07d}", # Example contract symbol
                'price': current_underlying_test_price, # This will be the underlying price column
                'option_price': round(max(0.01, current_underlying_test_price - strike_price_val if strike_price_val < current_underlying_test_price else strike_price_val - current_underlying_test_price + 0.5 + np.random.uniform(-0.2,0.2)),2), # Simulated option price
                'underlying_symbol': test_symbol_name,
                'oi': np.random.randint(50, 3000),
                'volm': np.random.randint(10, 1500),
                'volatility': np.random.uniform(0.15, 0.35), # Per-contract IV
                'multiplier': 100.0,
                'fetch_timestamp': datetime.now().isoformat(),
                'expiration_date': (date.today() + timedelta(days=np.random.randint(5,60))).isoformat()
            }
            # OI Greeks
            base_option_data.update({
                'gxoi': np.random.uniform(1e3, 5e4) * (1 - abs(strike_price_val - current_underlying_test_price)/50),
                'dxoi': np.random.uniform(-5e4, 5e4) * (1 - abs(strike_price_val - current_underlying_test_price)/70),
                'sgxoi': base_option_data['gxoi'] * np.random.uniform(0.9, 1.1), # Skewed GEX OI
                'txoi': np.random.uniform(-1e4, -1e2),
                'vxoi': np.random.uniform(1e3, 2e4),
                'charmxoi': np.random.uniform(-500,500),
                'vannaxoi': np.random.uniform(-1e4,1e4),
                'vommaxoi': np.random.uniform(100,1000)
            })
            # Greek Flow Proxies
            base_option_data.update({
                'gxvolm': base_option_data['gxoi'] * 0.1 * np.random.uniform(0.5, 1.5),
                'dxvolm': base_option_data['dxoi'] * 0.1 * np.random.uniform(0.5, 1.5),
                'txvolm': base_option_data['txoi'] * 0.1 * np.random.uniform(0.5, 1.5),
                'vxvolm': base_option_data['vxoi'] * 0.1 * np.random.uniform(0.5, 1.5),
                'charmxvolm': base_option_data['charmxoi'] * 0.1 * np.random.uniform(0.5, 1.5),
                'vannaxvolm': base_option_data['vannaxoi'] * 0.1 * np.random.uniform(0.5, 1.5),
                'vommaxvolm': base_option_data['vommaxoi'] * 0.1 * np.random.uniform(0.5, 1.5)
            })
            # Direct Buy/Sell Flows (Volume, Value, Greeks)
            base_option_data.update({
                'volm_buy': np.random.randint(0, 1000), 'volm_sell': np.random.randint(0, 1000),
                'value_buy': np.random.randint(0, 100000), 'value_sell': np.random.randint(0, 100000),
                'deltas_buy': np.random.uniform(-5000,5000), 'deltas_sell': np.random.uniform(-5000,5000),
                'gammas_buy': np.random.uniform(0,1000), 'gammas_sell': np.random.uniform(0,1000),
                'vegas_buy': np.random.uniform(0,5000), 'vegas_sell': np.random.uniform(0,5000),
                'thetas_buy': np.random.uniform(-5000,0), 'thetas_sell': np.random.uniform(-5000,0),
                # Direct Net _bs fields (as if from API)
                'volm_bs': base_option_data['volm_buy'] - base_option_data['volm_sell'],
                'value_bs': base_option_data['value_buy'] - base_option_data['value_sell']
            })

            # Create a call and a put for each strike
            call_data = base_option_data.copy()
            call_data['opt_kind'] = 'call'
            call_data['delta'] = max(0, min(1, 0.5 + (current_underlying_test_price - strike_price_val) / 20 + np.random.uniform(-0.05,0.05))) # Simplified delta
            call_data['gamma'] = max(0, 0.05 - abs(current_underlying_test_price - strike_price_val)/500 + np.random.uniform(-0.01,0.01))
            call_data['vega'] = max(0, 10 - abs(current_underlying_test_price - strike_price_val)/5 + np.random.uniform(-1,1))
            call_data['theta'] = -1 * max(0, 500 - abs(current_underlying_test_price - strike_price_val)*5 + np.random.uniform(-50,50))
            sample_options_data_list.append(call_data)

            put_data = base_option_data.copy()
            put_data['opt_kind'] = 'put'
            put_data['delta'] = max(-1, min(0, -0.5 + (current_underlying_test_price - strike_price_val) / 20 + np.random.uniform(-0.05,0.05)))
            put_data['gamma'] = call_data['gamma'] # Similar gamma for ATM/NTM
            put_data['vega'] = call_data['vega']   # Similar vega
            put_data['theta'] = call_data['theta']  # Similar theta
            sample_options_data_list.append(put_data)

        sample_options_df_for_its_test = pd.DataFrame(sample_options_data_list)
        main_its_test_logger.info(f"Test Sample Options DataFrame created. Shape: {sample_options_df_for_its_test.shape}")

        # Sample Historical OHLC for ATR
        atr_hist_dates = pd.to_datetime([date.today() - timedelta(days=i) for i in range(45, 0, -1)]) # 45 days of history
        sim_prices_for_atr = current_underlying_test_price + np.cumsum(np.random.normal(0, current_underlying_test_price * 0.01, 45)) # Random walk
        sample_ohlc_hist_data = {
            'date': atr_hist_dates,
            'open': sim_prices_for_atr - np.random.uniform(0, current_underlying_test_price * 0.005, 45),
            'high': sim_prices_for_atr + np.random.uniform(0, current_underlying_test_price * 0.01, 45),
            'low':  sim_prices_for_atr - np.random.uniform(0, current_underlying_test_price * 0.01, 45),
            'close': sim_prices_for_atr,
            'volume': np.random.randint(1000000, 15000000, 45)
        }
        # Ensure high is highest and low is lowest
        temp_ohlc_df = pd.DataFrame(sample_ohlc_hist_data)
        sample_ohlc_hist_data['high'] = temp_ohlc_df[['high', 'open', 'close']].max(axis=1)
        sample_ohlc_hist_data['low'] = temp_ohlc_df[['low', 'open', 'close']].min(axis=1)
        sample_historical_ohlc_df = pd.DataFrame(sample_ohlc_hist_data)
        main_its_test_logger.info(f"Test Sample Historical OHLC DataFrame created. Shape: {sample_historical_ohlc_df.shape}")

        # Contextual data for testing
        test_current_market_time = time(10, 45, 0) # Example: Morning session
        test_current_underlying_iv = 0.22
        test_avg_5day_iv = 0.21
        test_iv_context_data = {"iv_percentile_30d": 0.60} # Example IV percentile

        # --- 2. Tests `calculate_mspi`. ---
        main_its_test_logger.info(f"\n--- Testing calculate_mspi method ---")
        processed_df_output = its_test_instance.calculate_mspi(
            options_df=sample_options_df_for_its_test.copy(), # Pass a copy
            current_time=test_current_market_time,
            current_iv=test_current_underlying_iv,
            avg_iv_5day=test_avg_5day_iv,
            iv_context=test_iv_context_data,
            underlying_price=current_underlying_test_price,
            historical_ohlc_df_for_atr=sample_historical_ohlc_df.copy()
        )
        if not processed_df_output.empty:
            main_its_test_logger.info(f"calculate_mspi executed. Output DataFrame shape: {processed_df_output.shape}")
            main_its_test_logger.info(f"Columns in processed_df_output: {processed_df_output.columns.tolist()}")
            # Check for key output columns
            key_metric_cols = ['mspi', 'dag_custom', 'tdpi', 'vri', 'sai', 'ssi', 'cfi']
            for col_key_metric in key_metric_cols:
                if col_key_metric in processed_df_output.columns:
                    main_its_test_logger.debug(f"  Metric '{col_key_metric}' found. Example (first non-NaN if any): {processed_df_output[col_key_metric].dropna().head(1).to_string(index=False)}")
                else:
                    main_its_test_logger.error(f"  Metric '{col_key_metric}' NOT FOUND in MSPI output df.")
            main_its_test_logger.info(f"\nSample of MSPI output (head 3, selected cols):\n{processed_df_output[['strike','opt_kind'] + key_metric_cols].head(3).to_string()}")
        else:
            main_its_test_logger.error("calculate_mspi returned an empty DataFrame.")
            # sys.exit("Exiting test due to empty MSPI DataFrame.") # Optional: halt test if MSPI fails

        # --- 3. Tests signal/level identification. ---
        # Ensure processed_df_output is not empty before proceeding
        if not processed_df_output.empty:
            main_its_test_logger.info(f"\n--- Testing Signal Generation & Level Identification methods ---")
            test_trading_signals = its_test_instance.generate_trading_signals(processed_df_output.copy())
            signal_count = sum(len(sig_list) for type_dict in test_trading_signals.values() for sig_list in type_dict.values())
            main_its_test_logger.info(f"generate_trading_signals executed. Total signals generated: {signal_count}")
            if signal_count > 0: main_its_test_logger.debug(f"Sample Signal (first directional bullish if any): {test_trading_signals.get('directional',{}).get('bullish',[{}])[0]}")

            test_support_levels, test_resistance_levels = its_test_instance.identify_key_levels(processed_mspi_df=processed_df_output.copy())
            main_its_test_logger.info(f"identify_key_levels executed. Support levels found: {len(test_support_levels)}, Resistance levels found: {len(test_resistance_levels)}")
            if not test_support_levels.empty : main_its_test_logger.debug(f"  Top Support Level:\n{test_support_levels.head(1).to_string()}")

            test_high_conv_levels = its_test_instance.identify_high_conviction_levels(processed_mspi_df=processed_df_output.copy())
            main_its_test_logger.info(f"identify_high_conviction_levels executed. High conviction levels found: {len(test_high_conv_levels)}")

            test_structure_changes = its_test_instance.identify_potential_structure_changes(processed_mspi_df=processed_df_output.copy())
            main_its_test_logger.info(f"identify_potential_structure_changes executed. Structure change points found: {len(test_structure_changes)}")
        else:
            main_its_test_logger.warning("Skipping signal/level tests as MSPI DataFrame was empty.")

        # --- 4. Tests stateless recommendation generation. ---
        if not processed_df_output.empty: # Only if MSPI calculation was successful
            main_its_test_logger.info(f"\n--- Testing Stateless Recommendation Snapshot ---")
            # ATR for recommendations should be calculated based on the same historical data
            atr_for_stateless_recs = its_test_instance._get_atr(test_symbol_name, current_underlying_test_price, sample_historical_ohlc_df.copy())
            main_its_test_logger.debug(f"ATR calculated for stateless recommendations: {atr_for_stateless_recs:.4f}")

            stateless_recommendations_output = its_test_instance.get_strategy_recommendations_stateless_snapshot(
                symbol=test_symbol_name,
                options_df=sample_options_df_for_its_test.copy(), # Pass original per-contract data
                current_price=current_underlying_test_price,
                # atr=atr_for_stateless_recs, # No longer directly passed, calculated inside
                current_time=test_current_market_time,
                current_iv=test_current_underlying_iv,
                avg_iv_5day=test_avg_5day_iv,
                iv_context=test_iv_context_data,
                historical_ohlc_df_for_atr=sample_historical_ohlc_df.copy()
            )
            main_its_test_logger.info(f"Stateless snapshot generated {len(stateless_recommendations_output)} recommendations.")
            for i, rec_output in enumerate(stateless_recommendations_output[:2]): # Log first 2
                main_its_test_logger.debug(f"  Stateless Rec {i+1}: ID={rec_output.get('id')}, Cat={rec_output.get('category')}, Strike={rec_output.get('strike'):.2f}, Bias={rec_output.get('direction_label')}, Stars={rec_output.get('conviction_stars')}")
        else:
            main_its_test_logger.warning("Skipping stateless recommendation test as MSPI DataFrame was empty.")

        # --- 5. Simulates updates for the stateful recommendation engine. ---
        main_its_test_logger.info(f"\n--- Testing Stateful Recommendation Engine (Simulated Updates) ---")
        # Initial state update (will use data from the first MSPI calculation)
        if not processed_df_output.empty:
            atr_for_stateful_recs_run1 = its_test_instance._get_atr(test_symbol_name, current_underlying_test_price, sample_historical_ohlc_df.copy())
            active_recs_run1 = its_test_instance.update_active_recommendations_and_manage_state(
                symbol=test_symbol_name,
                processed_mspi_df=processed_df_output.copy(), # From first MSPI calc
                current_price=current_underlying_test_price,
                atr=atr_for_stateful_recs_run1,
                current_time=test_current_market_time,
                iv_context=test_iv_context_data
            )
            main_its_test_logger.info(f"Stateful Update 1: {len(active_recs_run1)} active recommendations for {test_symbol_name}.")
            for i, rec_output_run1 in enumerate(active_recs_run1[:2]): # Log first 2
                 main_its_test_logger.debug(f"  Active Rec {i+1} (Run 1): ID={rec_output_run1.get('id')}, Strike={rec_output_run1.get('strike'):.2f}, Status={rec_output_run1.get('status')}")

            # Simulate a price change and a time change for a second update
            simulated_price_run2 = current_underlying_test_price * 0.99 # Price drops 1%
            simulated_time_run2 = (datetime.combine(date.today(), test_current_market_time) + timedelta(minutes=30)).time() # 30 mins later
            main_its_test_logger.info(f"\nSimulating price move to {simulated_price_run2:.2f} at {simulated_time_run2.strftime('%H:%M:%S')} and re-evaluating state...")

            sample_options_df_run2 = sample_options_df_for_its_test.copy()
            sample_options_df_run2['price'] = simulated_price_run2 # Update underlying price
            # Optionally, slightly modify some flow data for Run 2 to simulate market changes
            if its_test_instance.direct_delta_buy_col in sample_options_df_run2.columns:
                sample_options_df_run2[its_test_instance.direct_delta_buy_col] *= np.random.uniform(0.7, 1.3, size=len(sample_options_df_run2))

            processed_df_run2 = its_test_instance.calculate_mspi(
                options_df=sample_options_df_run2, current_time=simulated_time_run2,
                current_iv=test_current_underlying_iv * 0.98, avg_iv_5day=test_avg_5day_iv * 0.99, # IVs slightly change
                iv_context={"iv_percentile_30d": 0.55}, underlying_price=simulated_price_run2,
                historical_ohlc_df_for_atr=sample_historical_ohlc_df.copy()
            )
            if not processed_df_run2.empty:
                atr_for_stateful_recs_run2 = its_test_instance._get_atr(test_symbol_name, simulated_price_run2, sample_historical_ohlc_df.copy())
                active_recs_run2 = its_test_instance.update_active_recommendations_and_manage_state(
                    symbol=test_symbol_name,
                    processed_mspi_df=processed_df_run2,
                    current_price=simulated_price_run2,
                    atr=atr_for_stateful_recs_run2,
                    current_time=simulated_time_run2,
                    iv_context={"iv_percentile_30d": 0.55}
                )
                main_its_test_logger.info(f"Stateful Update 2: {len(active_recs_run2)} active recommendations for {test_symbol_name}.")
                for i, rec_output_run2 in enumerate(active_recs_run2): # Log all to see exits/adjustments
                     main_its_test_logger.info(f"  Active Rec {i+1} (Run 2): ID={rec_output_run2.get('id')}, Strike={rec_output_run2.get('strike'):.2f}, Status={rec_output_run2.get('status')}, Bias={rec_output_run2.get('direction_label')}, SL={rec_output_run2.get('stop_loss'):.2f if rec_output_run2.get('stop_loss') is not None else 'N/A'}, T1={rec_output_run2.get('target_1'):.2f if rec_output_run2.get('target_1') is not None else 'N/A'}, Exit: {rec_output_run2.get('exit_reason')}")
            else:
                main_its_test_logger.warning("MSPI DataFrame for Run 2 was empty. Skipping second stateful update test.")
        else:
            main_its_test_logger.error("Initial MSPI calculation failed. Full stateful recommendation engine tests cannot proceed.")

        main_its_test_logger.info("--- IntegratedTradingSystem V2.4.1 (Stateful - Full) Direct Test Run Complete ---")