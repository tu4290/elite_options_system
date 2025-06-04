# core_analytics/impact_calculations.py
"""
Functions for calculating various Greek and flow impact factors (v2.3 EOTS context).
This version is refactored to use centralized column name constants from ids.py
and to accept input column names as parameters for flexibility.

Version: 2.3.1-ids-unabridged
"""
import sys
import os
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
import logging
print(f"IMPACT_CALCULATIONS: Current sys.path: {sys.path}")
# Attempt to find where 'utils' might be coming from
try:
    import utils
    print(f"IMPACT_CALCULATIONS: Imported 'utils' module from: {utils.__file__}")
    if hasattr(utils, 'ids'):
        print(f"IMPACT_CALCULATIONS: 'utils.ids' exists. Path: {utils.ids.__file__ if hasattr(utils.ids, '__file__') else 'Built-in or Namespace'}")
        print(f"IMPACT_CALCULATIONS: Attributes in utils.ids: {dir(utils.ids)}")
    else:
        print("IMPACT_CALCULATIONS: 'utils' was imported, but it has no 'ids' attribute.")
except ImportError:
    print("IMPACT_CALCULATIONS: Could NOT import 'utils' module directly here.")
except AttributeError as ae:
    print(f"IMPACT_CALCULATIONS: AttributeError during diagnostic: {ae}")

# Assuming ids.py is in elite_options_system_package.utils.ids
# Adjust import path if necessary based on your project structure.
try:
    from utils import ids # Centralized IDs
    from .system_utilities import ensure_columns
    print(f"DEBUG_IMPACT_CALC: Successfully imported 'ids' from 'utils'. Module path: {ids.__file__}") # Print path
    if hasattr(ids, 'IMPACT_VEGA_RAW'):
        print(f"DEBUG_IMPACT_CALC: ids.IMPACT_VEGA_RAW exists! Value: '{getattr(ids, 'IMPACT_VEGA_RAW')}'")
    else:
        print("DEBUG_IMPACT_CALC: CRITICAL - ids.IMPACT_VEGA_RAW DOES NOT EXIST in the imported 'ids' module.")
        # You could even force an error here to be absolutely sure this part is running before the AttributeError
        # raise AttributeError("DEBUG_IMPACT_CALC: Manually raising error because IMPACT_VEGA_RAW is missing in ids")
    IMPORTS_SUCCESSFUL = True # Assuming the rest of your imports in this block are fine
except ImportError as e:
    print(f"CRITICAL ERROR (impact_calculations.py): Failed to import 'ids' or 'system_utilities'. Error: {e}")
    IMPORTS_SUCCESSFUL = False
    # Define fallback constants if ids.py is missing, for basic script parsing
    class ids: # type: ignore
        COL_STRIKE = "strike_price"; COL_OPT_KIND = "opt_kind"; COL_DELTA_CONTRACT = "delta"
        CV_CHAIN_PARAM_DELTAS_BUY_CONTRACT = "deltas_buy"; CV_CHAIN_PARAM_DELTAS_SELL_CONTRACT = "deltas_sell"
        IMPACT_DELTA_RAW = 'delta_impact'; IMPACT_GAMMA_RAW = 'gamma_impact'; IMPACT_VEGA_RAW = 'vega_impact'
        IMPACT_THETA_RAW = 'theta_impact'; IMPACT_VOLUME_RAW = 'volume_impact'; IMPACT_VALUE_RAW = 'value_impact'
        IMPACT_SMI_RAW = 'smi'; IMPACT_VPI_RAW = 'vpi'; IMPACT_VPI_NORM = 'vpi_norm'; IMPACT_PROXIMITY = 'proximity'
        IMPACT_COMPOSITE_RAW = 'composite_impact'
        CV_CHAIN_PARAM_GAMMA_CONTRACT = "gamma"; CV_CHAIN_PARAM_GAMMAS_BUY_CONTRACT = "gammas_buy"; CV_CHAIN_PARAM_GAMMAS_SELL_CONTRACT = "gammas_sell"
        CV_CHAIN_PARAM_VEGA_CONTRACT = "vega"; CV_CHAIN_PARAM_VEGAS_BUY_CONTRACT = "vegas_buy"; CV_CHAIN_PARAM_VEGAS_SELL_CONTRACT = "vegas_sell"
        CV_CHAIN_PARAM_THETA_CONTRACT = "theta"; CV_CHAIN_PARAM_THETAS_BUY_CONTRACT = "thetas_buy"; CV_CHAIN_PARAM_THETAS_SELL_CONTRACT = "thetas_sell"
        CV_CHAIN_PARAM_VOLM_BUY_C = "volm_buy"; CV_CHAIN_PARAM_VOLM_SELL_C = "volm_sell"
        CV_CHAIN_PARAM_VALUE_BUY_C = "value_buy"; CV_CHAIN_PARAM_VALUE_SELL_C = "value_sell"
        COL_GXOI_CONTRACT = "gxoi"; COL_DXOI_CONTRACT = "dxoi"; COL_OI_OPTION_CONTRACT = "oi"; COL_OI_CHG_TEMP = "oi_ch"
        COL_PRICE_OPTION_CONTRACT = "price" # Option's own price


    class system_utilities_fallback: # type: ignore
        @staticmethod
        # Fallback for utility functions for snippet context
        def ensure_columns(df: pd.DataFrame, req_cols: List[str], name: str, log_instance: Optional[logging.Logger]) -> Tuple[pd.DataFrame, bool]:
            missing = [col for col in req_cols if col not in df.columns]
            if missing:
                if log_instance:
                    log_instance.warning(f"Ensure_columns ({name}): Missing columns: {missing}")
                # For snippet, let's add missing columns with 0.0 to avoid further errors in this isolated context
                for col in missing:
                    df[col] = 0.0
        # return df, False # In real code, you might return False
                return df, not missing
        @staticmethod
        def calculate_proximity_factor(strikes: pd.Series, price: float, delta: Optional[pd.Series], log_instance: Optional[logging.Logger]) -> pd.Series:
        # Simplified for snippet
            if log_instance:
                log_instance.debug(f"Calculating proximity factor for price {price}")
            return pd.Series(np.exp(-0.1 * np.abs(strikes - price) / price), index=strikes.index).fillna(0.5)
        @staticmethod
        def normalize_series(series: pd.Series, name: str, min_denominator: float) -> pd.Series:
            if log_instance: log_instance.debug(f"Dummy normalize_series called for {name}.") # type: ignore
            return series if isinstance(series, pd.Series) else pd.Series(dtype=float)
    ensure_columns = system_utilities_fallback.ensure_columns
    calculate_proximity_factor = system_utilities_fallback.calculate_proximity_factor
    normalize_series = system_utilities_fallback.normalize_series

# Module-level logger
logger = logging.getLogger(__name__)
if not IMPORTS_SUCCESSFUL:
    logger.critical("Impact Calculations module running with DUMMY imports due to failure. Functionality will be severely limited.")

# Constants for impact calculations
BASE_IMPACT_WEIGHTS: Dict[str, float] = {
    "buy_call": 1.00, "sell_put": 0.65, "buy_put": 1.00, "sell_call": 0.65
}
GREEK_IMPACT_WEIGHTS: Dict[str, Dict[str, float]] = {
    "delta": {"buy_weight": 1.00, "sell_weight": 0.65},
    "gamma": {"buy_weight": 1.20, "sell_weight": 0.60},
    "vega": {"buy_weight": 1.15, "sell_weight": 0.70},
    "theta": {"buy_weight": 0.90, "sell_weight": 0.80},
    "volume": {"buy_weight": 1.00, "sell_weight": 0.65},
    "value": {"buy_weight": 1.10, "sell_weight": 0.70}
}
MIN_NORMALIZATION_DENOMINATOR_IMPACT = 1e-9


def calculate_delta_impact(
    options_df: pd.DataFrame,
    current_price: float,
    strike_col: str = ids.COL_STRIKE,
    opt_kind_col: str = ids.COL_OPT_KIND,
    option_delta_col: str = ids.COL_DELTA_CONTRACT,
    deltas_buy_col: str = ids.CV_CHAIN_PARAM_DELTAS_BUY_CONTRACT,
    deltas_sell_col: str = ids.CV_CHAIN_PARAM_DELTAS_SELL_CONTRACT,
    log_instance: Optional[logging.Logger] = None
) -> pd.DataFrame:
    """
    Calculate the delta impact on the underlying asset.
    Output column: ids.IMPACT_DELTA_RAW
    """
    impact_logger = log_instance.getChild("CalculateDeltaImpact") if log_instance else logger.getChild("CalculateDeltaImpact")
    impact_logger.debug(f"Calculating Delta Impact for {len(options_df)} options.")
    result_df = options_df.copy()

    required_cols = [strike_col, opt_kind_col, option_delta_col, deltas_buy_col, deltas_sell_col]
    result_df, cols_ok = ensure_columns(result_df, required_cols, "DeltaImpactCalc", log_instance=impact_logger)

    if not cols_ok:
        impact_logger.warning("Delta Impact: Missing required columns. Returning DataFrame with zero impact.")
        result_df[ids.IMPACT_DELTA_RAW] = 0.0
        return result_df

    if ids.IMPACT_PROXIMITY not in result_df.columns:
        result_df[ids.IMPACT_PROXIMITY] = calculate_proximity_factor(
            result_df[strike_col], current_price, delta=result_df[option_delta_col], log_instance=impact_logger
        )
    result_df[ids.IMPACT_PROXIMITY] = pd.to_numeric(result_df[ids.IMPACT_PROXIMITY], errors='coerce').fillna(0.0)

    delta_weights_cfg = GREEK_IMPACT_WEIGHTS.get("delta", {"buy_weight": 1.00, "sell_weight": 0.65})
    buy_w = delta_weights_cfg.get("buy_weight", 1.00)
    sell_w = delta_weights_cfg.get("sell_weight", 0.65)

    deltas_buy_num = pd.to_numeric(result_df[deltas_buy_col], errors='coerce').fillna(0.0)
    deltas_sell_num = pd.to_numeric(result_df[deltas_sell_col], errors='coerce').fillna(0.0)
    proximity_num = result_df[ids.IMPACT_PROXIMITY]

    result_df[ids.IMPACT_DELTA_RAW] = 0.0
    call_mask = result_df[opt_kind_col].astype(str).str.lower() == 'call'
    put_mask = result_df[opt_kind_col].astype(str).str.lower() == 'put'

    result_df.loc[call_mask, ids.IMPACT_DELTA_RAW] += (deltas_buy_num[call_mask] * buy_w * proximity_num[call_mask])
    result_df.loc[put_mask, ids.IMPACT_DELTA_RAW] += (deltas_sell_num[put_mask] * sell_w * proximity_num[put_mask])
    result_df.loc[call_mask, ids.IMPACT_DELTA_RAW] -= (deltas_sell_num[call_mask] * sell_w * proximity_num[call_mask])
    result_df.loc[put_mask, ids.IMPACT_DELTA_RAW] -= (deltas_buy_num[put_mask] * buy_w * proximity_num[put_mask])

    result_df[ids.IMPACT_DELTA_RAW] = result_df[ids.IMPACT_DELTA_RAW].fillna(0.0)
    impact_logger.debug(f"Delta Impact calculated. Example: {result_df[ids.IMPACT_DELTA_RAW].head(1).to_string(index=False) if not result_df.empty else 'N/A'}")
    return result_df

def calculate_gamma_impact(
    options_df: pd.DataFrame,
    current_price: float,
    strike_col: str = ids.COL_STRIKE,
    opt_kind_col: str = ids.COL_OPT_KIND,
    option_delta_col: str = ids.COL_DELTA_CONTRACT,
    gammas_buy_col: str = ids.CV_CHAIN_PARAM_GAMMAS_BUY_CONTRACT,
    gammas_sell_col: str = ids.CV_CHAIN_PARAM_GAMMAS_SELL_CONTRACT,
    log_instance: Optional[logging.Logger] = None
) -> pd.DataFrame:
    impact_logger = log_instance.getChild("CalculateGammaImpact") if log_instance else logger.getChild("CalculateGammaImpact")
    impact_logger.debug("Calculating Gamma Impact...")
    result_df = options_df.copy()
    required_cols = [strike_col, opt_kind_col, option_delta_col, gammas_buy_col, gammas_sell_col]
    result_df, cols_ok = ensure_columns(result_df, required_cols, "GammaImpactCalc", log_instance=impact_logger)
    if not cols_ok: result_df[ids.IMPACT_GAMMA_RAW] = 0.0; return result_df
    if ids.IMPACT_PROXIMITY not in result_df.columns:
        result_df[ids.IMPACT_PROXIMITY] = calculate_proximity_factor(result_df[strike_col], current_price, delta=result_df[option_delta_col], log_instance=impact_logger)
    result_df[ids.IMPACT_PROXIMITY] = pd.to_numeric(result_df[ids.IMPACT_PROXIMITY], errors='coerce').fillna(0.0)
    cfg = GREEK_IMPACT_WEIGHTS.get("gamma", {"buy_weight": 1.20, "sell_weight": 0.60})
    buy_w, sell_w = cfg["buy_weight"], cfg["sell_weight"]
    gb_num = pd.to_numeric(result_df[gammas_buy_col], errors='coerce').fillna(0.0)
    gs_num = pd.to_numeric(result_df[gammas_sell_col], errors='coerce').fillna(0.0)
    prox_num = result_df[ids.IMPACT_PROXIMITY]
    result_df[ids.IMPACT_GAMMA_RAW] = ((gs_num * sell_w) - (gb_num * buy_w)) * prox_num # Dealer perspective: selling gamma is positive for their book
    result_df[ids.IMPACT_GAMMA_RAW] = result_df[ids.IMPACT_GAMMA_RAW].fillna(0.0)
    impact_logger.debug(f"Gamma Impact calculated. Example: {result_df[ids.IMPACT_GAMMA_RAW].head(1).to_string(index=False) if not result_df.empty else 'N/A'}")
    return result_df

def calculate_vega_impact(
    options_df: pd.DataFrame,
    current_price: float,
    strike_col: str = ids.COL_STRIKE,
    opt_kind_col: str = ids.COL_OPT_KIND,
    option_delta_col: str = ids.COL_DELTA_CONTRACT,
    vegas_buy_col: str = ids.CV_CHAIN_PARAM_VEGAS_BUY_CONTRACT,
    vegas_sell_col: str = ids.CV_CHAIN_PARAM_VEGAS_SELL_CONTRACT,
    log_instance: Optional[logging.Logger] = None
) -> pd.DataFrame:
    impact_logger = log_instance.getChild("CalculateVegaImpact") if log_instance else logger.getChild("CalculateVegaImpact")
    impact_logger.debug("Calculating Vega Impact...")
    result_df = options_df.copy()
    required_cols = [strike_col, opt_kind_col, option_delta_col, vegas_buy_col, vegas_sell_col]
    result_df, cols_ok = ensure_columns(result_df, required_cols, "VegaImpactCalc", log_instance=impact_logger)
    if not cols_ok: result_df[ids.IMPACT_VEGA_RAW] = 0.0; return result_df
    if ids.IMPACT_PROXIMITY not in result_df.columns:
        result_df[ids.IMPACT_PROXIMITY] = calculate_proximity_factor(result_df[strike_col], current_price, delta=result_df[option_delta_col], log_instance=impact_logger)
    result_df[ids.IMPACT_PROXIMITY] = pd.to_numeric(result_df[ids.IMPACT_PROXIMITY], errors='coerce').fillna(0.0)
    cfg = GREEK_IMPACT_WEIGHTS.get("vega", {"buy_weight":1.15, "sell_weight":0.70})
    buy_w, sell_w = cfg["buy_weight"], cfg["sell_weight"]
    vb_num = pd.to_numeric(result_df[vegas_buy_col], errors='coerce').fillna(0.0)
    vs_num = pd.to_numeric(result_df[vegas_sell_col], errors='coerce').fillna(0.0)
    prox_num = result_df[ids.IMPACT_PROXIMITY]
    result_df[ids.IMPACT_VEGA_RAW] = ((vb_num * buy_w) - (vs_num * sell_w)) * prox_num
    result_df[ids.IMPACT_VEGA_RAW] = result_df[ids.IMPACT_VEGA_RAW].fillna(0.0)
    impact_logger.debug(f"Vega Impact calculated. Example: {result_df[ids.IMPACT_VEGA_RAW].head(1).to_string(index=False) if not result_df.empty else 'N/A'}")
    return result_df

def calculate_theta_impact(
    options_df: pd.DataFrame,
    current_price: float,
    strike_col: str = ids.COL_STRIKE,
    opt_kind_col: str = ids.COL_OPT_KIND,
    option_delta_col: str = ids.COL_DELTA_CONTRACT,
    thetas_buy_col: str = ids.CV_CHAIN_PARAM_THETAS_BUY_CONTRACT,
    thetas_sell_col: str = ids.CV_CHAIN_PARAM_THETAS_SELL_CONTRACT,
    log_instance: Optional[logging.Logger] = None
) -> pd.DataFrame:
    impact_logger = log_instance.getChild("CalculateThetaImpact") if log_instance else logger.getChild("CalculateThetaImpact")
    impact_logger.debug("Calculating Theta Impact...")
    result_df = options_df.copy()
    required_cols = [strike_col, opt_kind_col, option_delta_col, thetas_buy_col, thetas_sell_col]
    result_df, cols_ok = ensure_columns(result_df, required_cols, "ThetaImpactCalc", log_instance=impact_logger)
    if not cols_ok: result_df[ids.IMPACT_THETA_RAW] = 0.0; return result_df
    if ids.IMPACT_PROXIMITY not in result_df.columns:
        result_df[ids.IMPACT_PROXIMITY] = calculate_proximity_factor(result_df[strike_col], current_price, delta=result_df[option_delta_col], log_instance=impact_logger)
    result_df[ids.IMPACT_PROXIMITY] = pd.to_numeric(result_df[ids.IMPACT_PROXIMITY], errors='coerce').fillna(0.0)
    cfg = GREEK_IMPACT_WEIGHTS.get("theta", {"buy_weight":0.90, "sell_weight":0.80})
    buy_w, sell_w = cfg["buy_weight"], cfg["sell_weight"]
    tb_num = pd.to_numeric(result_df[thetas_buy_col], errors='coerce').fillna(0.0)
    ts_num = pd.to_numeric(result_df[thetas_sell_col], errors='coerce').fillna(0.0)
    prox_num = result_df[ids.IMPACT_PROXIMITY]
    result_df[ids.IMPACT_THETA_RAW] = ((tb_num * buy_w) - (ts_num * sell_w)) * prox_num
    result_df[ids.IMPACT_THETA_RAW] = result_df[ids.IMPACT_THETA_RAW].fillna(0.0)
    impact_logger.debug(f"Theta Impact calculated. Example: {result_df[ids.IMPACT_THETA_RAW].head(1).to_string(index=False) if not result_df.empty else 'N/A'}")
    return result_df

def calculate_volume_impact(
    options_df: pd.DataFrame,
    current_price: float,
    strike_col: str = ids.COL_STRIKE,
    opt_kind_col: str = ids.COL_OPT_KIND,
    option_delta_col: str = ids.COL_DELTA_CONTRACT,
    volm_buy_col: str = ids.CV_CHAIN_PARAM_VOLM_BUY_C,
    volm_sell_col: str = ids.CV_CHAIN_PARAM_VOLM_SELL_C,
    log_instance: Optional[logging.Logger] = None
) -> pd.DataFrame:
    impact_logger = log_instance.getChild("CalculateVolumeImpact") if log_instance else logger.getChild("CalculateVolumeImpact")
    impact_logger.debug("Calculating Volume Impact...")
    result_df = options_df.copy()
    required_cols = [strike_col, opt_kind_col, option_delta_col, volm_buy_col, volm_sell_col]
    result_df, cols_ok = ensure_columns(result_df, required_cols, "VolumeImpactCalc", log_instance=impact_logger)
    if not cols_ok: result_df[ids.IMPACT_VOLUME_RAW] = 0.0; return result_df
    if ids.IMPACT_PROXIMITY not in result_df.columns:
        result_df[ids.IMPACT_PROXIMITY] = calculate_proximity_factor(result_df[strike_col], current_price, delta=result_df[option_delta_col], log_instance=impact_logger)
    result_df[ids.IMPACT_PROXIMITY] = pd.to_numeric(result_df[ids.IMPACT_PROXIMITY], errors='coerce').fillna(0.0)
    cfg = GREEK_IMPACT_WEIGHTS.get("volume", {"buy_weight":1.00, "sell_weight":0.65})
    buy_w, sell_w = cfg["buy_weight"], cfg["sell_weight"]
    vb_num = pd.to_numeric(result_df[volm_buy_col], errors='coerce').fillna(0.0)
    vs_num = pd.to_numeric(result_df[volm_sell_col], errors='coerce').fillna(0.0)
    prox_num = result_df[ids.IMPACT_PROXIMITY]
    call_mask = result_df[opt_kind_col].astype(str).str.lower() == 'call'
    put_mask = result_df[opt_kind_col].astype(str).str.lower() == 'put'
    result_df[ids.IMPACT_VOLUME_RAW] = 0.0
    result_df.loc[call_mask, ids.IMPACT_VOLUME_RAW] += (vb_num[call_mask] * buy_w * prox_num[call_mask])
    result_df.loc[put_mask, ids.IMPACT_VOLUME_RAW] += (vs_num[put_mask] * sell_w * prox_num[put_mask])
    result_df.loc[call_mask, ids.IMPACT_VOLUME_RAW] -= (vs_num[call_mask] * sell_w * prox_num[call_mask])
    result_df.loc[put_mask, ids.IMPACT_VOLUME_RAW] -= (vb_num[put_mask] * buy_w * prox_num[put_mask])
    result_df[ids.IMPACT_VOLUME_RAW] = result_df[ids.IMPACT_VOLUME_RAW].fillna(0.0)
    impact_logger.debug(f"Volume Impact calculated. Example: {result_df[ids.IMPACT_VOLUME_RAW].head(1).to_string(index=False) if not result_df.empty else 'N/A'}")
    return result_df

def calculate_value_impact(
    options_df: pd.DataFrame,
    current_price: float,
    strike_col: str = ids.COL_STRIKE,
    opt_kind_col: str = ids.COL_OPT_KIND,
    option_delta_col: str = ids.COL_DELTA_CONTRACT,
    value_buy_col: str = ids.CV_CHAIN_PARAM_VALUE_BUY_C,
    value_sell_col: str = ids.CV_CHAIN_PARAM_VALUE_SELL_C,
    log_instance: Optional[logging.Logger] = None
) -> pd.DataFrame:
    impact_logger = log_instance.getChild("CalculateValueImpact") if log_instance else logger.getChild("CalculateValueImpact")
    impact_logger.debug("Calculating Value Impact...")
    result_df = options_df.copy()
    required_cols = [strike_col, opt_kind_col, option_delta_col, value_buy_col, value_sell_col]
    result_df, cols_ok = ensure_columns(result_df, required_cols, "ValueImpactCalc", log_instance=impact_logger)
    if not cols_ok: result_df[ids.IMPACT_VALUE_RAW] = 0.0; return result_df
    if ids.IMPACT_PROXIMITY not in result_df.columns:
        result_df[ids.IMPACT_PROXIMITY] = calculate_proximity_factor(result_df[strike_col], current_price, delta=result_df[option_delta_col], log_instance=impact_logger)
    result_df[ids.IMPACT_PROXIMITY] = pd.to_numeric(result_df[ids.IMPACT_PROXIMITY], errors='coerce').fillna(0.0)
    cfg = GREEK_IMPACT_WEIGHTS.get("value", {"buy_weight":1.10, "sell_weight":0.70})
    buy_w, sell_w = cfg["buy_weight"], cfg["sell_weight"]
    vb_num = pd.to_numeric(result_df[value_buy_col], errors='coerce').fillna(0.0)
    vs_num = pd.to_numeric(result_df[value_sell_col], errors='coerce').fillna(0.0)
    prox_num = result_df[ids.IMPACT_PROXIMITY]
    call_mask = result_df[opt_kind_col].astype(str).str.lower() == 'call'
    put_mask = result_df[opt_kind_col].astype(str).str.lower() == 'put'
    result_df[ids.IMPACT_VALUE_RAW] = 0.0
    result_df.loc[call_mask, ids.IMPACT_VALUE_RAW] += (vb_num[call_mask] * buy_w * prox_num[call_mask])
    result_df.loc[put_mask, ids.IMPACT_VALUE_RAW] += (vs_num[put_mask] * sell_w * prox_num[put_mask])
    result_df.loc[call_mask, ids.IMPACT_VALUE_RAW] -= (vs_num[call_mask] * sell_w * prox_num[call_mask])
    result_df.loc[put_mask, ids.IMPACT_VALUE_RAW] -= (vb_num[put_mask] * buy_w * prox_num[put_mask])
    result_df[ids.IMPACT_VALUE_RAW] = result_df[ids.IMPACT_VALUE_RAW].fillna(0.0)
    impact_logger.debug(f"Value Impact calculated. Example: {result_df[ids.IMPACT_VALUE_RAW].head(1).to_string(index=False) if not result_df.empty else 'N/A'}")
    return result_df

def calculate_composite_impact(
    options_df: pd.DataFrame,
    composite_impact_weights_config: Dict[str, float],
    normalize_components: bool = True,
    log_instance: Optional[logging.Logger] = None
) -> pd.DataFrame:
    impact_logger = log_instance.getChild("CalculateCompositeImpact") if log_instance else logger.getChild("CalculateCompositeImpact")
    impact_logger.debug(f"Calculating Composite Impact Score (Normalize Components: {normalize_components})...")
    result_df = options_df.copy()

    # Map from config keys (which might include "_norm") to the RAW impact column names from ids.py
    # The config keys are what the user would set weights for.
    # The values are the actual DataFrame columns that hold the raw, unnormalized impact values.
    config_key_to_raw_col_map = {
        "delta_impact_norm": ids.IMPACT_DELTA_RAW, # Config key for weight vs. raw column name
        "gamma_impact_norm": ids.IMPACT_GAMMA_RAW,
        "vega_impact_norm": ids.IMPACT_VEGA_RAW,
        "theta_impact_norm": ids.IMPACT_THETA_RAW,
        "volume_impact_norm": ids.IMPACT_VOLUME_RAW,
        "value_impact_norm": ids.IMPACT_VALUE_RAW
    }
    
    # Check if all *weighted* raw columns are present
    required_raw_cols_for_composite: List[str] = []
    for norm_key, raw_col_name in config_key_to_raw_col_map.items():
        if composite_impact_weights_config.get(norm_key, 0.0) != 0.0: # Only require if weight is non-zero
            required_raw_cols_for_composite.append(raw_col_name)
    
    result_df, cols_ok = ensure_columns(result_df, list(set(required_raw_cols_for_composite)), "CompositeImpactInput", log_instance=impact_logger)
    if not cols_ok:
        impact_logger.warning("Composite Impact: Missing one or more raw impact columns needed for weighted sum. Composite will be zero.")
        result_df[ids.IMPACT_COMPOSITE_RAW] = 0.0
        return result_df

    result_df[ids.IMPACT_COMPOSITE_RAW] = 0.0
    total_weight_applied = 0.0

    for norm_key_in_config, raw_col_name_in_df in config_key_to_raw_col_map.items():
        weight = composite_impact_weights_config.get(norm_key_in_config, 0.0)
        if weight == 0.0 or raw_col_name_in_df not in result_df.columns:
            continue

        component_series = pd.to_numeric(result_df[raw_col_name_in_df], errors='coerce').fillna(0.0)
        
        if normalize_components:
            # Use the raw column name for normalization logging, as it's the source
            component_series_normalized = normalize_series(component_series, f"{raw_col_name_in_df}_for_composite", min_denominator=MIN_NORMALIZATION_DENOMINATOR_IMPACT)
            result_df[ids.IMPACT_COMPOSITE_RAW] += weight * component_series_normalized
        else:
            impact_logger.debug(f"Composite Impact: Adding raw component '{raw_col_name_in_df}' without normalization. Weight: {weight:.2f}")
            result_df[ids.IMPACT_COMPOSITE_RAW] += weight * component_series
        total_weight_applied += weight
    
    # If components were normalized, and weights don't sum to 1, re-normalize the composite.
    # If components were NOT normalized, the composite score is likely on an arbitrary scale and should be normalized.
    if normalize_components:
        if total_weight_applied > MIN_NORMALIZATION_DENOMINATOR_IMPACT and abs(total_weight_applied - 1.0) > 0.01:
            impact_logger.debug(f"Normalizing final composite impact as sum of weights was {total_weight_applied:.3f}")
            result_df[ids.IMPACT_COMPOSITE_RAW] /= total_weight_applied
        elif total_weight_applied <= MIN_NORMALIZATION_DENOMINATOR_IMPACT:
            impact_logger.warning(f"Sum of weights for Composite Impact is zero or too small ({total_weight_applied:.3f}). Composite will be zero.")
            result_df[ids.IMPACT_COMPOSITE_RAW] = 0.0
    else: # Always normalize the final composite if raw components were used.
        result_df[ids.IMPACT_COMPOSITE_RAW] = normalize_series(result_df[ids.IMPACT_COMPOSITE_RAW], "FinalCompositeImpactRawSource", min_denominator=MIN_NORMALIZATION_DENOMINATOR_IMPACT)

    result_df[ids.IMPACT_COMPOSITE_RAW] = result_df[ids.IMPACT_COMPOSITE_RAW].fillna(0.0)
    impact_logger.debug(f"Composite Impact (Normalized Components: {normalize_components}) calculated. Example: {result_df[ids.IMPACT_COMPOSITE_RAW].head(1).to_string(index=False) if not result_df.empty else 'N/A'}")
    return result_df

def calculate_strike_magnetism(
    options_df: pd.DataFrame,
    current_price: float,
    strike_col: str = ids.COL_STRIKE,
    opt_kind_col: str = ids.COL_OPT_KIND,
    option_delta_col: str = ids.COL_DELTA_CONTRACT,
    gxoi_col: str = ids.COL_GXOI_CONTRACT,
    dxoi_col: str = ids.COL_DXOI_CONTRACT,
    oi_col: str = ids.COL_OI_OPTION_CONTRACT,
    oi_chg_col: str = ids.COL_OI_CHG_TEMP, # This column name might need to be confirmed/sourced
    log_instance: Optional[logging.Logger] = None
) -> pd.DataFrame:
    impact_logger = log_instance.getChild("CalculateSMI") if log_instance else logger.getChild("CalculateSMI")
    impact_logger.debug("Calculating Strike Magnetism Index (SMI)...")
    result_df = options_df.copy()
    required_cols = [strike_col, opt_kind_col, option_delta_col, gxoi_col, dxoi_col, oi_col]
    if oi_chg_col in result_df.columns: # Only require if present, otherwise factor is neutral
        required_cols.append(oi_chg_col)

    result_df, cols_ok = ensure_columns(result_df, required_cols, "SMICalc", log_instance=impact_logger)
    if not cols_ok:
        impact_logger.warning("SMI: Missing base required columns. Returning DataFrame with zero SMI.")
        result_df[ids.IMPACT_SMI_RAW] = 0.0
        return result_df

    if ids.IMPACT_PROXIMITY not in result_df.columns:
        result_df[ids.IMPACT_PROXIMITY] = calculate_proximity_factor(result_df[strike_col], current_price, delta=result_df[option_delta_col], log_instance=impact_logger)
    result_df[ids.IMPACT_PROXIMITY] = pd.to_numeric(result_df[ids.IMPACT_PROXIMITY], errors='coerce').fillna(0.0)

    gxoi_numeric = pd.to_numeric(result_df[gxoi_col], errors='coerce').fillna(0.0)
    dxoi_numeric = pd.to_numeric(result_df[dxoi_col], errors='coerce').fillna(0.0)
    oi_numeric = pd.to_numeric(result_df[oi_col], errors='coerce').fillna(0.0)
    
    oi_change_factor = pd.Series(1.0, index=result_df.index)
    if oi_chg_col in result_df.columns:
        oi_chg_numeric = pd.to_numeric(result_df[oi_chg_col], errors='coerce').fillna(0.0)
        oi_previous = oi_numeric - oi_chg_numeric # Previous OI = Current OI - Change in OI
        # Ensure denominator is stable and positive
        denominator_oi_chg = (oi_previous.abs().replace(0, 1) + oi_chg_numeric.abs() + MIN_NORMALIZATION_DENOMINATOR_IMPACT)
        oi_change_factor = (1 + oi_chg_numeric / denominator_oi_chg).fillna(1.0).clip(0.5, 2.0)
    else:
        impact_logger.debug(f"SMI: Column '{oi_chg_col}' for OI change not found. Using neutral OI change factor (1.0).")

    result_df[ids.IMPACT_SMI_RAW] = (
        gxoi_numeric * np.sign(dxoi_numeric.replace(0,1e-9)) * oi_change_factor * result_df[ids.IMPACT_PROXIMITY]
    ).fillna(0.0)
    impact_logger.debug(f"SMI calculated. Example: {result_df[ids.IMPACT_SMI_RAW].head(1).to_string(index=False) if not result_df.empty else 'N/A'}")
    return result_df

def calculate_volatility_pressure(
    options_df: pd.DataFrame,
    current_price: float,
    strike_col: str = ids.COL_STRIKE,
    opt_kind_col: str = ids.COL_OPT_KIND,
    option_delta_col: str = ids.COL_DELTA_CONTRACT,
    # VPI uses the *output* of vega_impact and gamma_impact calculations
    vega_impact_col: str = ids.COL_IMPACT_VEGA_RAW,
    gamma_impact_col: str = ids.COL_IMPACT_GAMMA_RAW,
    log_instance: Optional[logging.Logger] = None
) -> pd.DataFrame:
    impact_logger = log_instance.getChild("CalculateVPI") if log_instance else logger.getChild("CalculateVPI")
    impact_logger.debug("Calculating Volatility Pressure Index (VPI)...")
    result_df = options_df.copy()

    required_cols = [strike_col, opt_kind_col, option_delta_col, vega_impact_col, gamma_impact_col]
    result_df, cols_ok = ensure_columns(result_df, required_cols, "VPICalc", log_instance=impact_logger)

    if not cols_ok:
        impact_logger.warning("VPI: Missing required pre-calculated impact columns. Returning DataFrame with zero VPI.")
        result_df[ids.IMPACT_VPI_RAW] = 0.0
        result_df[ids.IMPACT_VPI_NORM] = 0.0
        return result_df

    if ids.IMPACT_PROXIMITY not in result_df.columns:
        result_df[ids.IMPACT_PROXIMITY] = calculate_proximity_factor(
            result_df[strike_col], current_price, delta=result_df[option_delta_col], log_instance=impact_logger
        )
    result_df[ids.IMPACT_PROXIMITY] = pd.to_numeric(result_df[ids.IMPACT_PROXIMITY], errors='coerce').fillna(0.0)

    gamma_impact_numeric = pd.to_numeric(result_df[gamma_impact_col], errors='coerce').fillna(0.0)
    vega_impact_numeric = pd.to_numeric(result_df[vega_impact_col], errors='coerce').fillna(0.0)
    proximity_numeric = result_df[ids.IMPACT_PROXIMITY]

    result_df[ids.IMPACT_VPI_RAW] = (vega_impact_numeric * np.sign(gamma_impact_numeric.replace(0,1e-9)) * proximity_numeric).fillna(0.0)
    result_df[ids.IMPACT_VPI_NORM] = normalize_series(result_df[ids.IMPACT_VPI_RAW], "VPINorm", min_denominator=MIN_NORMALIZATION_DENOMINATOR_IMPACT)
    impact_logger.debug(f"VPI calculated. Example Raw: {result_df[ids.IMPACT_VPI_RAW].head(1).to_string(index=False) if not result_df.empty else 'N/A'}, Norm: {result_df[ids.IMPACT_VPI_NORM].head(1).to_string(index=False) if not result_df.empty else 'N/A'}")
    return result_df

def calculate_gamma_exposure_profile(
    options_df: pd.DataFrame,
    current_price: float,
    price_range_pct: float = 0.05,
    strike_col: str = ids.COL_STRIKE,
    opt_kind_col: str = ids.COL_OPT_KIND,
    option_delta_col: str = ids.COL_DELTA_CONTRACT, # For proximity calculation
    # --- MODIFIED PARAMETERS ---
    # Use general contract-level gamma flow columns
    contract_gammas_buy_col: str = ids.CV_CHAIN_PARAM_GAMMAS_BUY_CONTRACT,
    contract_gammas_sell_col: str = ids.CV_CHAIN_PARAM_GAMMAS_SELL_CONTRACT,
    log_instance: Optional[logging.Logger] = None
) -> pd.DataFrame:
    impact_logger = log_instance.getChild("CalculateGammaProfile") if log_instance else logger.getChild("CalculateGammaProfile")
    impact_logger.debug(f"Calculating Gamma Exposure Profile for price range +/- {price_range_pct*100:.1f}%...")
    data = options_df.copy()

    # --- MODIFIED REQUIRED COLUMNS ---
    required_raw_gamma_cols = [strike_col, opt_kind_col, option_delta_col,
                               contract_gammas_buy_col, contract_gammas_sell_col]
    
    data, cols_ok = ensure_columns(data, required_raw_gamma_cols, "GammaProfileInput", log_instance=impact_logger)
    if not cols_ok:
        impact_logger.error("Gamma Exposure Profile: Missing required raw gamma columns. Returning empty DataFrame.")
        return pd.DataFrame()

    min_price = current_price * (1 - price_range_pct)
    max_price = current_price * (1 + price_range_pct)
    price_steps = 100 # Can be made configurable
    price_levels = np.linspace(min_price, max_price, price_steps)
    results = []

    # --- MODIFIED GAMMA VALUE READING ---
    # These now refer to the general 'gammas_buy' and 'gammas_sell' columns for each contract
    gammas_buy_for_contract_num = pd.to_numeric(data[contract_gammas_buy_col], errors='coerce').fillna(0.0)
    gammas_sell_for_contract_num = pd.to_numeric(data[contract_gammas_sell_col], errors='coerce').fillna(0.0)

    gamma_weights_cfg = GREEK_IMPACT_WEIGHTS.get("gamma", {"buy_weight": 1.20, "sell_weight": 0.60})
    buy_w = gamma_weights_cfg.get("buy_weight", 1.20)
    sell_w = gamma_weights_cfg.get("sell_weight", 0.60)

    call_mask = data[opt_kind_col].astype(str).str.lower() == 'call'
    put_mask = data[opt_kind_col].astype(str).str.lower() == 'put'

    for price_level_eval in price_levels:
        temp_proximity = calculate_proximity_factor(data[strike_col], price_level_eval, delta=data[option_delta_col], log_instance=impact_logger)
        temp_proximity_num = pd.to_numeric(temp_proximity, errors='coerce').fillna(0.0)

        # Dealer perspective:
        # Customer buys calls/puts (gamma > 0) -> dealer sells calls/puts -> dealer short gamma -> negative contribution to dealer's gamma
        # Customer sells calls/puts (gamma > 0) -> dealer buys calls/puts -> dealer long gamma -> positive contribution to dealer's gamma
        # contract_gammas_buy_col ('gammas_buy') = gamma bought by customers for this contract (dealer sold this gamma)
        # contract_gammas_sell_col ('gammas_sell') = gamma sold by customers for this contract (dealer bought this gamma)

        # --- MODIFIED CALCULATION LOGIC ---
        # For calls:
        # Dealer buys gamma from customers selling calls: gammas_sell_for_contract_num[call_mask] * sell_w (positive for dealer)
        # Dealer sells gamma to customers buying calls: gammas_buy_for_contract_num[call_mask] * buy_w (negative for dealer)
        dealer_gamma_from_calls = (gammas_sell_for_contract_num[call_mask] * sell_w * temp_proximity_num[call_mask]).sum() - \
                                  (gammas_buy_for_contract_num[call_mask] * buy_w * temp_proximity_num[call_mask]).sum()
        
        # For puts:
        # Dealer buys gamma from customers selling puts: gammas_sell_for_contract_num[put_mask] * sell_w (positive for dealer)
        # Dealer sells gamma to customers buying puts: gammas_buy_for_contract_num[put_mask] * buy_w (negative for dealer)
        dealer_gamma_from_puts  = (gammas_sell_for_contract_num[put_mask] * sell_w * temp_proximity_num[put_mask]).sum() - \
                                  (gammas_buy_for_contract_num[put_mask] * buy_w * temp_proximity_num[put_mask]).sum()
        
        total_dealer_gamma_exposure_at_price = dealer_gamma_from_calls + dealer_gamma_from_puts
        
        results.append({'price': price_level_eval, 'gamma_exposure': total_dealer_gamma_exposure_at_price, 'price_pct_change': (price_level_eval / current_price - 1) * 100})

    impact_logger.info(f"Gamma Exposure Profile calculated for {len(price_levels)} price steps.")
    return pd.DataFrame(results)

def detect_volatility_regime(
    options_df: pd.DataFrame,
    current_price: float,
    strike_col: str = ids.COL_STRIKE,
    opt_kind_col: str = ids.COL_OPT_KIND,
    option_delta_col: str = ids.COL_DELTA_CONTRACT,
    # --- MODIFIED PARAMETERS TO USE CORRECT ids CONSTANTS ---
    vega_impact_col: str = ids.COL_IMPACT_VEGA_RAW, # Expects pre-calculated vega_impact
    vpi_col: str = ids.COL_IMPACT_VPI_RAW,           # Expects pre-calculated vpi
    log_instance: Optional[logging.Logger] = None,
    min_norm_denominator: float = MIN_NORMALIZATION_DENOMINATOR_IMPACT # Use local constant
) -> Dict[str, Any]:
    regime_logger = log_instance.getChild("DetectVolatilityRegime") if log_instance else logger.getChild("DetectVolatilityRegime")
    regime_logger.debug("Detecting Volatility Regime...")
    data = options_df.copy()

    required_cols = [strike_col, opt_kind_col, option_delta_col, vega_impact_col, vpi_col]
    data, cols_ok = ensure_columns(data, required_cols, "VolatilityRegimeInput", log_instance=regime_logger)
    if not cols_ok:
        regime_logger.warning("Volatility Regime Detection: Missing required columns. Returning neutral regime.")
        return {'regime': "Neutral Volatility (Data Missing)", 'score': 0.0, 'net_vega': 0.0, 'vega_skew': 0.0, 'vpi_ratio': 0.0}

    # Ensure strike column is numeric for comparison and proximity calculation
    data[strike_col] = pd.to_numeric(data[strike_col], errors='coerce')
    
    # Calculate proximity if not already present (though typically it would be)
    # This check is more for robustness if this function is called with a DataFrame
    # that hasn't had proximity calculated yet.
    if ids.IMPACT_PROXIMITY not in data.columns:
        regime_logger.debug(f"Proximity column '{ids.IMPACT_PROXIMITY}' not found. Calculating it now.")
        data[ids.IMPACT_PROXIMITY] = calculate_proximity_factor(
            data[strike_col], current_price, delta=data[option_delta_col], log_instance=regime_logger
        )
    data[ids.IMPACT_PROXIMITY] = pd.to_numeric(data[ids.IMPACT_PROXIMITY], errors='coerce').fillna(0.0)


    vega_impact_num = pd.to_numeric(data[vega_impact_col], errors='coerce').fillna(0.0)
    vpi_num = pd.to_numeric(data[vpi_col], errors='coerce').fillna(0.0)

    net_vega = vega_impact_num.sum()
    
    upside_vega_impact = vega_impact_num[data[strike_col] > current_price].sum()
    downside_vega_impact = vega_impact_num[data[strike_col] < current_price].sum()
    
    vega_skew_denominator = abs(upside_vega_impact) + abs(downside_vega_impact) + min_norm_denominator
    vega_skew = (upside_vega_impact - downside_vega_impact) / vega_skew_denominator if vega_skew_denominator > min_norm_denominator else 0.0


    vpi_positive_sum = vpi_num[vpi_num > 0].sum()
    vpi_negative_sum_abs = abs(vpi_num[vpi_num < 0].sum()) # Absolute value of negative sum
    
    vpi_ratio_denominator = vpi_negative_sum_abs + min_norm_denominator # Add min_norm_denominator here too
    vpi_ratio = vpi_positive_sum / vpi_ratio_denominator if vpi_ratio_denominator > min_norm_denominator else (float('inf') if vpi_positive_sum > 0 else 0.0)


    regime = "Neutral Volatility"; regime_score = 0.5
    # These thresholds should ideally come from config
    vpi_expansion_strong_thresh = 2.0
    vpi_expansion_mod_thresh = 1.5
    vpi_contraction_strong_thresh = 0.5
    vpi_contraction_mod_thresh = 0.67
    vega_skew_significance_thresh = 0.3 # If skew ratio is > 30%

    if vpi_ratio > vpi_expansion_strong_thresh and net_vega > 0:
        regime = "Strong Volatility Expansion"; regime_score = min(1.0, vpi_ratio / 5.0) # Capped at 1.0
    elif vpi_ratio > vpi_expansion_mod_thresh and net_vega > 0:
        regime = "Moderate Volatility Expansion"; regime_score = min(0.8, vpi_ratio / 5.0) # Capped at 0.8
    elif vpi_ratio < vpi_contraction_strong_thresh and net_vega < 0:
        # Ensure vpi_ratio + min_norm_denominator is not zero if vpi_ratio is very small negative
        regime = "Strong Volatility Contraction"; regime_score = min(1.0, 1.0 / (vpi_ratio + min_norm_denominator if vpi_ratio > -min_norm_denominator else 0.1)) 
    elif vpi_ratio < vpi_contraction_mod_thresh and net_vega < 0:
        regime = "Moderate Volatility Contraction"; regime_score = min(0.8, 1.0 / (vpi_ratio + min_norm_denominator if vpi_ratio > -min_norm_denominator else 0.1))
    elif abs(vega_skew) > vega_skew_significance_thresh : # Check absolute skew ratio
        if vega_skew > 0: regime = "Upside Volatility Skew"
        else: regime = "Downside Volatility Skew"
        regime_score = min(0.9, abs(vega_skew)) # Score based on skew magnitude, capped at 0.9
    else:
        regime = "Neutral Volatility"; regime_score = 0.5 # Default neutral score

    # Ensure regime_score is within [0,1]
    regime_score = max(0.0, min(1.0, regime_score))

    regime_logger.info(f"Volatility Regime detected: '{regime}' (Score: {regime_score:.2f}, Net Vega: {net_vega:.2f}, Vega Skew Ratio: {vega_skew:.2f}, VPI Ratio: {vpi_ratio:.2f})")
    return {'regime': regime, 'score': round(regime_score,3), 'net_vega': round(net_vega,2), 'vega_skew': round(vega_skew,3), 'vpi_ratio': round(vpi_ratio,3)}


