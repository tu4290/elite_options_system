# enhanced_data_processor_v2.py
# (Elite Version 2.0.7 - Greek Flow Integration & Refined Pressure Metrics)

# Standard Library Imports
import os
import json
import traceback
import logging
from datetime import datetime, date, time
from typing import Dict, Any, Optional, List, Union, Tuple, Callable

# Third-Party Imports
import pandas as pd
import numpy as np

# --- Global Logger Setup ---
if not logging.getLogger().hasHandlers():
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO").upper(),
        format="[%(levelname)s] (%(name)s:%(lineno)d) %(asctime)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
logger = logging.getLogger(__name__)

# --- Constants ---
# For HEURISTIC pressure calculations (your original method)
HEURISTIC_PRESSURE_REQUIRED_COLS: List[str] = ["opt_kind", "strike", "volm_buy", "volm_sell", "value_buy", "value_sell"]
NET_HEURISTIC_VOLUME_PRESSURE_COL: str = "net_volume_pressure" # Keeping original name for this output
NET_HEURISTIC_VALUE_PRESSURE_COL: str = "net_value_pressure"  # Keeping original name for this output

# For NEW TRUE NET FLOW calculations based on direct buy/sell of Greeks/Vol/Val
NET_DELTA_FLOW_TOTAL_COL: str = "net_delta_flow_total"
NET_DELTA_FLOW_CALLS_COL: str = "net_delta_flow_calls"
NET_DELTA_FLOW_PUTS_COL: str = "net_delta_flow_puts"
NET_HEURISTIC_DELTA_PRESSURE_COL: str = "heuristic_net_delta_pressure" # Your specific heuristic
NET_GAMMA_FLOW_COL: str = "net_gamma_flow"
NET_VEGA_FLOW_COL: str = "net_vega_flow"
NET_THETA_EXPOSURE_COL: str = "net_theta_exposure"
# Columns for true net volume/value from volm_bs, value_bs if also desired alongside heuristic
TRUE_NET_VOLUME_FLOW_COL: str = "true_net_volume_flow" # From volm_bs
TRUE_NET_VALUE_FLOW_COL: str = "true_net_value_flow"   # From value_bs


DEFAULT_DATA_DIR_PROC: str = "data"
DEFAULT_CONFIG_PATH_PROC: str = "config_v2.json"
JSON_CONVERSION_ERROR_PLACEHOLDER_PROC = "JSON_CONVERSION_ERROR_IN_PROCESSOR"

# --- Dummy Trading System (Fallback - unchanged from your v2.0.6) ---
class IntegratedTradingSystemDummy:
    """ Dummy fallback for IntegratedTradingSystem. Provides default method implementations. """
    def __init__(self, config_path: str = DEFAULT_CONFIG_PATH_PROC):
         logger.warning(f"PROCESSOR: Initializing DUMMY IntegratedTradingSystem (Config: {config_path}). Fallback.")
         self.config_path = config_path; self.config: Dict[str, Any] = {}
         try:
            abs_config_path = config_path
            if not os.path.isabs(config_path):
                script_dir = os.path.dirname(os.path.abspath(__file__))
                abs_config_path = os.path.join(script_dir, config_path)
                if not os.path.exists(abs_config_path) and os.path.exists(config_path):
                    abs_config_path = config_path
            if os.path.exists(abs_config_path):
                with open(abs_config_path, "r") as f: self.config = json.load(f)
            else:
                logger.warning(f"Dummy ITS: Config file '{abs_config_path}' not found during dummy init.")
         except Exception as e: logger.error(f"Dummy ITS: Error loading config {config_path}: {e}")
    def _get_atr(self, symbol: str, price: Optional[float], history_df: Optional[pd.DataFrame] = None) -> float:
        logger.warning(f"DUMMY ITS: _get_atr called for {symbol}. Returning fallback 1.0."); return 1.0
    def _aggregate_for_levels(self, df: pd.DataFrame, group_col: str = 'strike') -> pd.DataFrame:
        logger.warning(f"DUMMY ITS: _aggregate_for_levels called for {group_col}.")
        if 'strike' in df.columns: return df.groupby(group_col, as_index=False).first()
        return pd.DataFrame()
    def calculate_mspi(self, options_df: pd.DataFrame, historical_ohlc_df_for_atr: Optional[pd.DataFrame]=None,avg_iv_5day: Optional[float]=None,**kwargs) -> pd.DataFrame:
        logger.warning("DUMMY ITS: calculate_mspi called."); df = options_df.copy() if isinstance(options_df,pd.DataFrame) else pd.DataFrame()
        cols_to_ensure = ["mspi","dag_custom","tdpi","vri","sai","ssi","cfi","underlying_symbol","symbol","strike","price",NET_HEURISTIC_VOLUME_PRESSURE_COL,NET_HEURISTIC_VALUE_PRESSURE_COL]
        for c in cols_to_ensure:
            if c not in df.columns:
                if c == 'ssi': df[c] = 0.5
                elif c in ['symbol','underlying_symbol']: df[c] = "DUMMY_SYM"
                elif c == 'strike': df[c] = [100.0] * len(df) if not df.empty else []
                elif c == 'price': df[c] = 100.0
                else: df[c] = 0.0
        return df
    def identify_key_levels(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]: return pd.DataFrame(columns=['strike']), pd.DataFrame(columns=['strike'])
    def identify_high_conviction_levels(self, df: pd.DataFrame) -> pd.DataFrame: return pd.DataFrame(columns=['strike'])
    def identify_potential_structure_changes(self, df: pd.DataFrame) -> pd.DataFrame: return pd.DataFrame(columns=['strike'])
    def generate_trading_signals(self, df: pd.DataFrame, **kwargs) -> Dict[str, Dict[str, list]]: return {'directional':{'bullish':[],'bearish':[]}, 'volatility':{}, 'time_decay':{}, 'complex':{}}
    def get_strategy_recommendations(self, symbol: str, mspi_df: pd.DataFrame, trading_signals: Dict[str, Dict[str, list]], key_levels: Tuple[pd.DataFrame, pd.DataFrame], conviction_levels: pd.DataFrame, structure_changes: pd.DataFrame, current_price: float, atr: float, **kwargs) -> List[Dict[str,Any]]: return [{"id": "DUMMY_REC_001", "symbol": symbol, "category": "Dummy", "rationale": "ITS Unavailable (Dummy)"}]

# --- Real ITS Import (unchanged) ---
RealIntegratedTradingSystem: Optional[type] = None
try:
    from integrated_strategies_v2 import IntegratedTradingSystem as ImportedITS
    RealIntegratedTradingSystem = ImportedITS
    logger.info("PROCESSOR: Successfully imported RealIntegratedTradingSystem from integrated_strategies_v2.")
except ImportError as import_error_its:
    logger.error(f"PROCESSOR IMPORT ERROR: Could not import IntegratedTradingSystem from integrated_strategies_v2: {import_error_its}")
    logger.warning("PROCESSOR: Processing will use the DUMMY fallback trading system.")
except Exception as general_import_error_its:
    logger.error(f"PROCESSOR UNEXPECTED IMPORT ERROR for IntegratedTradingSystem: {general_import_error_its}", exc_info=True)
    logger.warning("PROCESSOR: Processing will use the DUMMY fallback trading system.")


class EnhancedDataProcessor:
    # __init__, _load_main_config_for_processor, _ensure_processed_output_dir_exists,
    # _initialize_trading_system_instance, _validate_input_data, _prepare_dataframe
    # --- These methods can remain largely THE SAME as your v2.0.6 ---
    # --- Ensure _validate_input_data checks for new required per-contract Greek flow fields if they become essential ---
    def __init__(self, config_path: str = DEFAULT_CONFIG_PATH_PROC, data_dir: str = DEFAULT_DATA_DIR_PROC):
        init_logger = logger.getChild("ProcessorInit")
        init_logger.info(f"Initializing EnhancedDataProcessor V2.0.7 (Config: {config_path}, Data Dir: {data_dir})...")
        self.data_dir: str = data_dir
        self.config_path: str = config_path
        self.processor_config: Dict[str, Any] = self._load_main_config_for_processor()
        system_settings_cfg = self.processor_config.get("system_settings", {})
        output_dir_from_config = system_settings_cfg.get("data_directory", self.data_dir)
        if os.path.isabs(output_dir_from_config):
            self.processed_output_dir = output_dir_from_config
        else:
            base_path_for_relative = os.getcwd(); script_dir = os.path.dirname(os.path.abspath(__file__))
            if os.path.isfile(self.config_path): base_path_for_relative = os.path.dirname(os.path.abspath(self.config_path))
            elif os.path.isdir(self.config_path): base_path_for_relative = os.path.abspath(self.config_path)
            else: base_path_for_relative = script_dir # Fallback to script dir if config path itself is not found
            self.processed_output_dir = os.path.join(base_path_for_relative, output_dir_from_config)
        init_logger.debug(f"Resolved processed_output_dir to: {self.processed_output_dir}")
        self.trading_system_instance: Union[ImportedITS, IntegratedTradingSystemDummy] # type: ignore
        self._initialize_trading_system_instance()
        self._ensure_processed_output_dir_exists()
        init_logger.info("EnhancedDataProcessor V2.0.7 Initialized.")
    def _load_main_config_for_processor(self) -> Dict[str, Any]:
        load_cfg_logger = logger.getChild("ProcessorConfigLoad"); load_cfg_logger.debug(f"Loading FULL application configuration from: {self.config_path}")
        abs_config_path = self.config_path
        if not os.path.isabs(self.config_path):
            script_dir = os.path.dirname(os.path.abspath(__file__)); abs_config_path = os.path.join(script_dir, self.config_path)
            if not os.path.exists(abs_config_path) and os.path.exists(self.config_path): abs_config_path = os.path.abspath(self.config_path)
        try:
            if os.path.exists(abs_config_path):
                with open(abs_config_path, "r", encoding="utf-8") as f_cfg: full_loaded_config = json.load(f_cfg)
                load_cfg_logger.info(f"Successfully loaded FULL config from {abs_config_path} for processor use."); return full_loaded_config
            else: load_cfg_logger.warning(f"FULL Config file {abs_config_path} not found. Using empty dict."); return {}
        except Exception as e_load_cfg: load_cfg_logger.error(f"Error loading FULL config from '{abs_config_path}': {e_load_cfg}. Using empty dict.", exc_info=True); return {}
    def _ensure_processed_output_dir_exists(self) -> None:
        try: os.makedirs(self.processed_output_dir, exist_ok=True); logger.debug(f"Ensured output directory exists: {self.processed_output_dir}")
        except OSError as e_dir_create: logger.warning(f"Could not create output directory '{self.processed_output_dir}': {e_dir_create}")
    def _initialize_trading_system_instance(self) -> None:
        init_its_logger = logger.getChild("ProcessorITSInit")
        if RealIntegratedTradingSystem is not None:
            try: self.trading_system_instance = RealIntegratedTradingSystem(config_path=self.config_path); init_its_logger.info("Real ITS instance created.")
            except Exception as e_init_its_real: init_its_logger.error(f"Failed to instantiate real ITS: {e_init_its_real}", exc_info=True); init_its_logger.warning("Processor falling back to DUMMY ITS."); self.trading_system_instance = IntegratedTradingSystemDummy(config_path=self.config_path)
        else: init_its_logger.warning("Real ITS class not imported. Processor using DUMMY ITS."); self.trading_system_instance = IntegratedTradingSystemDummy(config_path=self.config_path)
    def _validate_input_data(self, options_chain_df: Optional[pd.DataFrame], symbol: str) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
        val_logger = logger.getChild("ValidateInput")
        if options_chain_df is None or not isinstance(options_chain_df, pd.DataFrame) or options_chain_df.empty:
            error_msg = f"Input options chain data for {symbol} missing, empty, or invalid type ({type(options_chain_df)})."; val_logger.error(error_msg); return None, error_msg
        df = options_chain_df.copy()
        required_base_cols = ["strike", "opt_kind", "symbol"] # 'underlying_symbol' will be derived if missing
        missing_base = [col for col in required_base_cols if col not in df.columns]
        if missing_base: error_msg_base = f"'{symbol}': Missing critical base columns: {missing_base}."; val_logger.error(error_msg_base); return df, error_msg_base
        if 'underlying_symbol' not in df.columns:
            first_symbol_val = str(df['symbol'].iloc[0]) if not df.empty else symbol; parsed_underlying = first_symbol_val.split(':')[0] if ':' in first_symbol_val else first_symbol_val
            df['underlying_symbol'] = parsed_underlying; val_logger.warning(f"'{symbol}': 'underlying_symbol' derived as '{parsed_underlying}'.")
        # Validation for Greek flow columns (can be extended) - for now, ensure they exist if strict mode
        flow_related_cols_to_check = ['deltas_buy', 'deltas_sell', 'volm_buy', 'volm_sell', 'value_buy', 'value_sell', 'volm_bs', 'value_bs', 'gammas_buy', 'gammas_sell', 'vegas_buy', 'vegas_sell', 'thetas_buy', 'thetas_sell']
        if self.processor_config.get("data_processor_settings",{}).get("perform_strict_column_validation", True):
            missing_flow_cols = [col for col in flow_related_cols_to_check if col not in df.columns]
            if any(f_col in missing_flow_cols for f_col in ['volm_buy','volm_sell','value_buy','value_sell']) and \
               any(f_col_bs in missing_flow_cols for f_col_bs in ['volm_bs','value_bs']): # If neither set is present
                 error_msg_flow = f"'{symbol}': Missing columns for pressure/flow calculation (neither direct _bs nor granular buy/sell are fully present). Missing: {missing_flow_cols}"; val_logger.error(error_msg_flow); return df, error_msg_flow
        return df, None
    def _prepare_dataframe(self, df_to_prepare: pd.DataFrame, underlying_data_bundle: Optional[Dict], symbol_str: str) -> pd.DataFrame:
        prep_logger = logger.getChild("PrepareDataFrame"); current_underlying_price = underlying_data_bundle.get("price") if isinstance(underlying_data_bundle, dict) else None; df_prepared = df_to_prepare.copy()
        if 'price' in df_prepared.columns:
            if 'option_price' not in df_prepared.columns: df_prepared.rename(columns={'price': 'option_price'}, inplace=True); prep_logger.debug(f"({symbol_str}): Renamed original 'price' to 'option_price'.")
            else: prep_logger.debug(f"({symbol_str}): 'option_price' exists. 'price' will be overwritten.")
        if current_underlying_price is not None and isinstance(current_underlying_price, (int, float)) and current_underlying_price > 0:
            df_prepared["price"] = float(current_underlying_price); prep_logger.info(f"({symbol_str}): Set 'price' column to underlying price: {current_underlying_price:.4f}")
        else: df_prepared["price"] = 0.0; prep_logger.warning(f"({symbol_str}): Setting 'price' to 0.0 (underlying price issue: {current_underlying_price}).")
        df_prepared["price"] = df_prepared["price"].astype(float)
        if 'underlying_symbol' not in df_prepared.columns or df_prepared['underlying_symbol'].isnull().all():
            fetched_und_sym = underlying_data_bundle.get("symbol") if isinstance(underlying_data_bundle, dict) else None
            if fetched_und_sym: df_prepared['underlying_symbol'] = str(fetched_und_sym); prep_logger.info(f"({symbol_str}): Populated 'underlying_symbol' from fetcher bundle ('{fetched_und_sym}').")
            elif 'symbol' in df_prepared.columns and not df_prepared.empty and pd.notna(df_prepared['symbol'].iloc[0]):
                parsed_sym = str(df_prepared['symbol'].iloc[0]).split(':')[0]; df_prepared['underlying_symbol'] = parsed_sym; prep_logger.warning(f"({symbol_str}): Used parsed options 'symbol' ('{parsed_sym}') for 'underlying_symbol'.")
            else: df_prepared['underlying_symbol'] = str(symbol_str); prep_logger.warning(f"({symbol_str}): Used main processing symbol ('{symbol_str}') for 'underlying_symbol'.")
        df_prepared['underlying_symbol'] = df_prepared['underlying_symbol'].astype(str)
        return df_prepared

    # --- START OF MODIFIED/NEW SECTION for _calculate_all_strike_level_flows ---
    def _calculate_all_strike_level_flows(self, df_input: pd.DataFrame, symbol_context: str) -> pd.DataFrame:
        """
        Calculates various strike-level net flow and pressure metrics.
        - Your Heuristic Net Value Pressure
        - Your Heuristic Net Volume Pressure
        - True Net Delta Flow (Calls, Puts, Total)
        - Your Heuristic Net Delta Pressure
        - Net Gamma Flow
        - Net Vega Flow
        - Net Theta Exposure Initiated
        - True Net Volume Flow (from volm_bs)
        - True Net Value Flow (from value_bs)
        """
        flow_calc_logger = logger.getChild("CalculateAllFlows")
        flow_calc_logger.info(f"Calculating all strike-level flow metrics for {symbol_context}...")
        df = df_input.copy()

        # Ensure base columns for any aggregation are present
        base_agg_cols = ['strike', 'opt_kind']
        df, _ = self.trading_system_instance._ensure_columns(df, base_agg_cols, "BaseAggColsForFlows") # Use ITS's _ensure_columns

        # --- 1. Your Heuristic Net Value & Volume Pressure (forced) ---
        flow_calc_logger.debug("Calculating Heuristic Net Value/Volume Pressures...")
        h_pressure_cols = HEURISTIC_PRESSURE_REQUIRED_COLS
        df_for_heuristic, _ = self.trading_system_instance._ensure_columns(df, h_pressure_cols, "HeuristicPressureInputs")
        
        calls_df_h = df_for_heuristic[df_for_heuristic['opt_kind'] == 'call']
        puts_df_h = df_for_heuristic[df_for_heuristic['opt_kind'] == 'put']
        
        named_aggs_heuristic = {
            "total_volm_buy": pd.NamedAgg("volm_buy", "sum"), "total_volm_sell": pd.NamedAgg("volm_sell", "sum"),
            "total_value_buy": pd.NamedAgg("value_buy", "sum"), "total_value_sell": pd.NamedAgg("value_sell", "sum")
        }
        call_comps_h = calls_df_h.groupby("strike").agg(**named_aggs_heuristic).add_suffix("_call").reset_index() if not calls_df_h.empty else pd.DataFrame(columns=['strike']+[f"{k}_call" for k in named_aggs_heuristic])
        put_comps_h = puts_df_h.groupby("strike").agg(**named_aggs_heuristic).add_suffix("_put").reset_index() if not puts_df_h.empty else pd.DataFrame(columns=['strike']+[f"{k}_put" for k in named_aggs_heuristic])
        
        unique_strikes_h = pd.to_numeric(df_for_heuristic["strike"], errors='coerce').dropna().unique()
        if len(unique_strikes_h) > 0:
            all_strikes_h_df = pd.DataFrame({'strike': unique_strikes_h})
            merged_h = pd.merge(all_strikes_h_df, call_comps_h, on="strike", how="left")
            merged_h = pd.merge(merged_h, put_comps_h, on="strike", how="left").fillna(0.0)

            merged_h["agg_bullish_vol"] = merged_h.get("total_volm_buy_call",0.0) + merged_h.get("total_volm_sell_put",0.0)
            merged_h["agg_bearish_vol"] = merged_h.get("total_volm_buy_put",0.0) + merged_h.get("total_volm_sell_call",0.0)
            merged_h[NET_HEURISTIC_VOLUME_PRESSURE_COL] = merged_h["agg_bullish_vol"] - merged_h["agg_bearish_vol"]
            
            merged_h["agg_bullish_val"] = merged_h.get("total_value_buy_call",0.0) + merged_h.get("total_value_sell_put",0.0)
            merged_h["agg_bearish_val"] = merged_h.get("total_value_buy_put",0.0) + merged_h.get("total_value_sell_call",0.0)
            merged_h[NET_HEURISTIC_VALUE_PRESSURE_COL] = merged_h["agg_bullish_val"] - merged_h["agg_bearish_val"]
            
            heuristic_pressures_df = merged_h[["strike", NET_HEURISTIC_VOLUME_PRESSURE_COL, NET_HEURISTIC_VALUE_PRESSURE_COL]]
            df = df.drop(columns=[NET_HEURISTIC_VOLUME_PRESSURE_COL, NET_HEURISTIC_VALUE_PRESSURE_COL], errors="ignore").merge(heuristic_pressures_df, on="strike", how="left")
        else:
            df[NET_HEURISTIC_VOLUME_PRESSURE_COL] = 0.0
            df[NET_HEURISTIC_VALUE_PRESSURE_COL] = 0.0
        df[NET_HEURISTIC_VOLUME_PRESSURE_COL] = df[NET_HEURISTIC_VOLUME_PRESSURE_COL].fillna(0.0)
        df[NET_HEURISTIC_VALUE_PRESSURE_COL] = df[NET_HEURISTIC_VALUE_PRESSURE_COL].fillna(0.0)

        # --- 2. True Net Volume & Value Flow (from direct _bs fields if available) ---
        flow_calc_logger.debug("Calculating True Net Volume/Value Flows (from _bs fields)...")
        true_flow_cols = ['volm_bs', 'value_bs', 'strike']
        df_for_true_flow, _ = self.trading_system_instance._ensure_columns(df, true_flow_cols, "TrueNetFlowInputs")
        if 'volm_bs' in df_for_true_flow.columns:
            true_net_vol = df_for_true_flow.groupby('strike')['volm_bs'].sum().reset_index(name=TRUE_NET_VOLUME_FLOW_COL)
            df = pd.merge(df, true_net_vol, on='strike', how='left')
            df[TRUE_NET_VOLUME_FLOW_COL] = df[TRUE_NET_VOLUME_FLOW_COL].fillna(0.0)
        else: df[TRUE_NET_VOLUME_FLOW_COL] = 0.0
        
        if 'value_bs' in df_for_true_flow.columns:
            true_net_val = df_for_true_flow.groupby('strike')['value_bs'].sum().reset_index(name=TRUE_NET_VALUE_FLOW_COL)
            df = pd.merge(df, true_net_val, on='strike', how='left')
            df[TRUE_NET_VALUE_FLOW_COL] = df[TRUE_NET_VALUE_FLOW_COL].fillna(0.0)
        else: df[TRUE_NET_VALUE_FLOW_COL] = 0.0


        # --- 3. Greek Flows (Delta, Gamma, Vega, Theta) ---
        flow_calc_logger.debug("Calculating Net Greek Flows (Delta, Gamma, Vega, Theta)...")
        greek_flow_map = {
            'delta': {'buy': 'deltas_buy', 'sell': 'deltas_sell', 'out_heuristic': NET_HEURISTIC_DELTA_PRESSURE_COL, 'out_true_net': NET_DELTA_FLOW_TOTAL_COL, 'out_calls': NET_DELTA_FLOW_CALLS_COL, 'out_puts': NET_DELTA_FLOW_PUTS_COL},
            'gamma': {'buy': 'gammas_buy', 'sell': 'gammas_sell', 'out_true_net': NET_GAMMA_FLOW_COL},
            'vega':  {'buy': 'vegas_buy',  'sell': 'vegas_sell',  'out_true_net': NET_VEGA_FLOW_COL},
            'theta': {'buy': 'thetas_buy', 'sell': 'thetas_sell', 'out_true_net': NET_THETA_EXPOSURE_COL} # For Theta, it's "exposure"
        }

        for greek, cfg in greek_flow_map.items():
            buy_col, sell_col = cfg['buy'], cfg['sell']
            df_for_greek_flow, _ = self.trading_system_instance._ensure_columns(df, [buy_col, sell_col, 'opt_kind', 'strike'], f"{greek.capitalize()}NetFlowInputs")

            if buy_col not in df_for_greek_flow.columns or sell_col not in df_for_greek_flow.columns:
                flow_calc_logger.warning(f"Missing '{buy_col}' or '{sell_col}' for {greek} flow. Skipping calculation for {cfg.get('out_true_net','N/A')}.")
                if cfg.get('out_true_net'): df[cfg['out_true_net']] = 0.0
                if cfg.get('out_heuristic'): df[cfg['out_heuristic']] = 0.0
                if cfg.get('out_calls'): df[cfg['out_calls']] = 0.0
                if cfg.get('out_puts'): df[cfg['out_puts']] = 0.0
                continue

            # Calculate per-contract net based on Greek type
            if greek == 'delta': # Your specific heuristic for delta
                # True Net Delta Flow (Buy - Sell)
                df_for_greek_flow['net_delta_contract_temp'] = pd.to_numeric(df_for_greek_flow[buy_col], errors='coerce').fillna(0) - pd.to_numeric(df_for_greek_flow[sell_col], errors='coerce').fillna(0)
                
                # Your Heuristic Net Delta Pressure
                df_for_greek_flow['heuristic_delta_temp'] = 0.0
                # Calls bought: +deltas_buy_call
                df_for_greek_flow.loc[df_for_greek_flow['opt_kind'] == 'call', 'heuristic_delta_temp'] += pd.to_numeric(df_for_greek_flow[buy_col], errors='coerce').fillna(0)
                # Puts sold: -deltas_sell_put (flip sign as selling a negative delta put is bullish)
                df_for_greek_flow.loc[df_for_greek_flow['opt_kind'] == 'put', 'heuristic_delta_temp'] += -1 * pd.to_numeric(df_for_greek_flow[sell_col], errors='coerce').fillna(0)
                # Puts bought: +deltas_buy_put (already negative)
                df_for_greek_flow.loc[df_for_greek_flow['opt_kind'] == 'put', 'heuristic_delta_temp'] += pd.to_numeric(df_for_greek_flow[buy_col], errors='coerce').fillna(0)
                # Calls sold: -deltas_sell_call (flip sign as selling a positive delta call is bearish)
                df_for_greek_flow.loc[df_for_greek_flow['opt_kind'] == 'call', 'heuristic_delta_temp'] += -1 * pd.to_numeric(df_for_greek_flow[sell_col], errors='coerce').fillna(0)

            elif greek == 'theta': # Net Theta Exposure Initiated
                df_for_greek_flow['net_greek_contract_temp'] = pd.to_numeric(df_for_greek_flow[buy_col], errors='coerce').fillna(0) + \
                                                              (-1 * pd.to_numeric(df_for_greek_flow[sell_col], errors='coerce').fillna(0))
            else: # Gamma, Vega (Net Flow = Buy - Sell)
                df_for_greek_flow['net_greek_contract_temp'] = pd.to_numeric(df_for_greek_flow[buy_col], errors='coerce').fillna(0) - \
                                                              pd.to_numeric(df_for_greek_flow[sell_col], errors='coerce').fillna(0)

            # Aggregate per strike
            if greek == 'delta':
                agg_h_delta = df_for_greek_flow.groupby('strike')['heuristic_delta_temp'].sum().reset_index(name=cfg['out_heuristic'])
                df = pd.merge(df, agg_h_delta, on='strike', how='left')
                df[cfg['out_heuristic']] = df[cfg['out_heuristic']].fillna(0.0)
                
                # True Net Delta Flow (Calls, Puts, Total)
                calls_true_net_delta = df_for_greek_flow[df_for_greek_flow['opt_kind'] == 'call'].groupby('strike')['net_delta_contract_temp'].sum().reset_index(name=cfg['out_calls'])
                puts_true_net_delta = df_for_greek_flow[df_for_greek_flow['opt_kind'] == 'put'].groupby('strike')['net_delta_contract_temp'].sum().reset_index(name=cfg['out_puts'])
                df = pd.merge(df, calls_true_net_delta, on='strike', how='left')
                df = pd.merge(df, puts_true_net_delta, on='strike', how='left')
                df[cfg['out_calls']] = df[cfg['out_calls']].fillna(0.0)
                df[cfg['out_puts']] = df[cfg['out_puts']].fillna(0.0)
                df[cfg['out_true_net']] = df[cfg['out_calls']] + df[cfg['out_puts']]
            else:
                agg_greek = df_for_greek_flow.groupby('strike')['net_greek_contract_temp'].sum().reset_index(name=cfg['out_true_net'])
                df = pd.merge(df, agg_greek, on='strike', how='left')
                df[cfg['out_true_net']] = df[cfg['out_true_net']].fillna(0.0)
        
        flow_calc_logger.info(f"Finished calculating all strike-level flow metrics for {symbol_context}.")
        return df

    def _ensure_pressure_metrics(self, df_to_ensure: pd.DataFrame, symbol_to_ensure: str) -> pd.DataFrame:
        # THIS METHOD IS NOW REPLACED/EXPANDED by _calculate_all_strike_level_flows
        # For backward compatibility, it can call the new comprehensive function.
        # Or, it can be deprecated if all call sites are updated.
        # For now, let's make it call the new function.
        ensure_press_logger = logger.getChild("EnsurePressureMetrics")
        ensure_press_logger.info(f"EnsurePressureMetrics now calls _calculate_all_strike_level_flows for {symbol_to_ensure}.")
        return self._calculate_all_strike_level_flows(df_to_ensure, symbol_to_ensure)
    # --- END OF MODIFIED/NEW SECTION ---


    # _apply_integrated_strategies, _convert_scalar_to_json_safe, _convert_to_json_safe,
    # _package_results, process_data_with_integrated_strategies, process_market_data
    # --- These methods remain largely the same as your v2.0.6, but ensure _ensure_pressure_metrics
    # (or its replacement _calculate_all_strike_level_flows) is called correctly.
    def _apply_integrated_strategies(self, df_after_pressure_calc: pd.DataFrame, underlying_data_bundle_from_fetcher: Dict[str, Any], volatility_data_for_its: Dict[str, Any], historical_ohlc_data_for_atr: Optional[pd.DataFrame], symbol_str_context: str) -> Tuple[pd.DataFrame, Dict[str, pd.DataFrame], Dict[str, Dict[str, list]], List[Dict[str,Any]], Optional[float], Optional[str]]:
        apply_strat_logger = logger.getChild("ApplyStrategies"); df_current_for_its = df_after_pressure_calc.copy()
        identified_levels: Dict[str, pd.DataFrame] = {"support": pd.DataFrame(), "resistance": pd.DataFrame(), "high_conviction": pd.DataFrame(), "structure_change": pd.DataFrame()}
        generated_signals_dict: Dict[str, Dict[str, list]] = {'directional':{'bullish':[],'bearish':[]}, 'volatility':{'expansion':[],'contraction':[]}, 'time_decay':{'pin_risk':[],'charm_cascade':[]}, 'complex':{'structure_change':[],'flow_divergence':[],'sdag_conviction':[]}}
        generated_recommendations_list: List[Dict[str,Any]] = []; atr_value_calculated: Optional[float] = None; current_processing_error: Optional[str] = None; final_metric_rich_df: pd.DataFrame = df_current_for_its
        is_its_dummy = isinstance(self.trading_system_instance, IntegratedTradingSystemDummy)
        required_its_methods = ['calculate_mspi', 'generate_trading_signals', 'identify_key_levels', 'identify_high_conviction_levels', 'identify_potential_structure_changes', 'get_strategy_recommendations', '_get_atr', '_aggregate_for_levels']
        methods_ok = all(hasattr(self.trading_system_instance, method) for method in required_its_methods)
        if is_its_dummy or not methods_ok:
            error_detail = "Using DUMMY ITS." if is_its_dummy else f"Real ITS instance missing required methods (OK: {methods_ok}). Using DUMMY."; current_processing_error = f"CRITICAL: {error_detail}"; apply_strat_logger.error(f"Processor ({symbol_str_context}): {current_processing_error}")
            dummy_its = IntegratedTradingSystemDummy(config_path=self.config_path)
            final_metric_rich_df = dummy_its.calculate_mspi(df_current_for_its,historical_ohlc_df_for_atr=historical_ohlc_data_for_atr,avg_iv_5day=volatility_data_for_its.get("avg_5day_iv"))
            atr_value_calculated = dummy_its._get_atr(symbol_str_context, underlying_data_bundle_from_fetcher.get("price"), historical_ohlc_data_for_atr)
            identified_levels["support"], identified_levels["resistance"] = dummy_its.identify_key_levels(final_metric_rich_df); identified_levels["high_conviction"] = dummy_its.identify_high_conviction_levels(final_metric_rich_df); identified_levels["structure_change"] = dummy_its.identify_potential_structure_changes(final_metric_rich_df)
            generated_signals_dict = dummy_its.generate_trading_signals(final_metric_rich_df); aggregated_dummy_df = dummy_its._aggregate_for_levels(final_metric_rich_df)
            generated_recommendations_list = dummy_its.get_strategy_recommendations(symbol=symbol_str_context, mspi_df=aggregated_dummy_df, trading_signals=generated_signals_dict,key_levels=(identified_levels["support"], identified_levels["resistance"]),conviction_levels=identified_levels["high_conviction"], structure_changes=identified_levels["structure_change"],current_price=underlying_data_bundle_from_fetcher.get("price",0.0),atr=atr_value_calculated if atr_value_calculated is not None else 1.0)
            return final_metric_rich_df, identified_levels, generated_signals_dict, generated_recommendations_list, atr_value_calculated, current_processing_error
        try:
            apply_strat_logger.info(f"Processor ({symbol_str_context}): Applying REAL ITS instance for snapshot analysis...")
            current_processing_time=datetime.now().time(); iv_cfg=self.processor_config.get("data_processor_settings",{}).get("iv_context_parameters",{}); iv_ctx_its:Optional[Dict[str,Any]]=None
            if iv_cfg and isinstance(volatility_data_for_its,dict): iv_ctx_its={k:volatility_data_for_its.get(v) for k,v in iv_cfg.items() if volatility_data_for_its.get(v) is not None}; iv_ctx_its=None if not iv_ctx_its else iv_ctx_its
            current_und_px_its=underlying_data_bundle_from_fetcher.get("price")
            if current_und_px_its is None and 'price' in df_current_for_its.columns and not df_current_for_its.empty: current_und_px_its=df_current_for_its['price'].iloc[0]
            if 'underlying_symbol' not in df_current_for_its.columns: df_current_for_its['underlying_symbol']=symbol_str_context; apply_strat_logger.warning(f"Added 'underlying_symbol' as '{symbol_str_context}' to df for ITS.")
            final_metric_rich_df=self.trading_system_instance.calculate_mspi(options_df=df_current_for_its,current_time=current_processing_time,current_iv=volatility_data_for_its.get("current_iv"),avg_iv_5day=volatility_data_for_its.get("avg_5day_iv"),iv_context=iv_ctx_its,underlying_price=current_und_px_its,historical_ohlc_df_for_atr=historical_ohlc_data_for_atr)
            if not isinstance(final_metric_rich_df, pd.DataFrame) or final_metric_rich_df.empty: raise TypeError(f"ITS.calculate_mspi for {symbol_str_context} invalid DataFrame.")
            atr_sym_calc=symbol_str_context
            if 'underlying_symbol' in final_metric_rich_df.columns and not final_metric_rich_df['underlying_symbol'].empty: atr_sym_calc=final_metric_rich_df['underlying_symbol'].iloc[0]
            px_atr_calc=current_und_px_its
            if px_atr_calc is None and 'price' in final_metric_rich_df.columns and not final_metric_rich_df['price'].empty: px_atr_calc=final_metric_rich_df['price'].iloc[0]
            atr_value_calculated=self.trading_system_instance._get_atr(atr_sym_calc,px_atr_calc,history_df=historical_ohlc_data_for_atr); apply_strat_logger.debug(f"Processor ({symbol_str_context}): ATR for recs: {atr_value_calculated:.4f}")
            identified_levels["support"],identified_levels["resistance"]=self.trading_system_instance.identify_key_levels(final_metric_rich_df); identified_levels["high_conviction"]=self.trading_system_instance.identify_high_conviction_levels(final_metric_rich_df); identified_levels["structure_change"]=self.trading_system_instance.identify_potential_structure_changes(final_metric_rich_df)
            generated_signals_dict=self.trading_system_instance.generate_trading_signals(final_metric_rich_df); agg_mspi_df_recs=self.trading_system_instance._aggregate_for_levels(final_metric_rich_df,group_col='strike')
            if agg_mspi_df_recs.empty and not final_metric_rich_df.empty: apply_strat_logger.warning(f"Agg for recs empty ({symbol_str_context}). Using unaggregated."); agg_mspi_df_recs=final_metric_rich_df
            generated_recommendations_list=self.trading_system_instance.get_strategy_recommendations(symbol=symbol_str_context,mspi_df=agg_mspi_df_recs,trading_signals=generated_signals_dict,key_levels=(identified_levels["support"],identified_levels["resistance"]),conviction_levels=identified_levels["high_conviction"],structure_changes=identified_levels["structure_change"],current_price=current_und_px_its if current_und_px_its is not None else 0.0,atr=atr_value_calculated if atr_value_calculated is not None else 1.0,current_time=current_processing_time,iv_context=iv_ctx_its)
            if not isinstance(generated_recommendations_list, list): apply_strat_logger.warning(f"ITS.get_strategy_recommendations unexpected type. Using empty list."); generated_recommendations_list = []
            apply_strat_logger.info(f"Processor ({symbol_str_context}): Snapshot analysis using REAL ITS completed.")
        except Exception as e_apply_real_its:
            current_processing_error = f"Error applying REAL ITS ({symbol_str_context}): {e_apply_real_its}"; apply_strat_logger.error(current_processing_error, exc_info=True)
            final_metric_rich_df=df_after_pressure_calc; identified_levels={"support":pd.DataFrame(),"resistance":pd.DataFrame(),"high_conviction":pd.DataFrame(),"structure_change":pd.DataFrame()}; generated_signals_dict={'directional':{'bullish':[],'bearish':[]}}; generated_recommendations_list=[]; atr_value_calculated=None
        return final_metric_rich_df, identified_levels, generated_signals_dict, generated_recommendations_list, atr_value_calculated, current_processing_error
    def _convert_scalar_to_json_safe(self, scalar_data: Any) -> Any: # Unchanged
        if pd.isna(scalar_data): return None;
        if isinstance(scalar_data, (datetime, date, pd.Timestamp)): return scalar_data.isoformat()
        if isinstance(scalar_data, time): return scalar_data.strftime('%H:%M:%S.%f')
        if isinstance(scalar_data, pd.Timedelta): return scalar_data.total_seconds()
        if isinstance(scalar_data, np.integer): return int(scalar_data)
        if isinstance(scalar_data, np.floating): return None if np.isinf(scalar_data) or np.isnan(scalar_data) else float(scalar_data)
        if isinstance(scalar_data, np.bool_): return bool(scalar_data)
        if hasattr(scalar_data, 'as_posix'): return scalar_data.as_posix()
        return scalar_data
    def _convert_to_json_safe(self, data_to_convert: Any) -> Any: # Unchanged
        if isinstance(data_to_convert, pd.DataFrame):
            df_copy=data_to_convert.copy()
            for col in df_copy.select_dtypes(include=[np.number]).columns: df_copy[col]=df_copy[col].replace([np.inf,-np.inf],np.nan)
            return [self._convert_to_json_safe(rec) for rec in df_copy.to_dict(orient="records")]
        elif isinstance(data_to_convert, pd.Series): return [self._convert_scalar_to_json_safe(item) for item in data_to_convert.replace([np.inf,-np.inf],np.nan).tolist()]
        elif isinstance(data_to_convert, dict): return {str(k):self._convert_to_json_safe(v) for k,v in data_to_convert.items()}
        elif isinstance(data_to_convert, (list,tuple,set,np.ndarray)): return [self._convert_to_json_safe(item) for item in data_to_convert]
        return self._convert_scalar_to_json_safe(data_to_convert)
    def _package_results(self, symbol_str_pkg: str, fetch_ts_pkg: Optional[str], final_metric_rich_df_obj_pkg: pd.DataFrame, levels_dict_pkg: Dict[str, pd.DataFrame], signals_dict_pkg: Dict[str, Dict[str,list]], recommendations_list_pkg: List[Dict[str,Any]], underlying_data_pkg: Optional[Dict[str,Any]], volatility_data_pkg: Optional[Dict[str,Any]], atr_value_used_pkg: Optional[float], final_error_message_pkg: Optional[str], processor_config_snapshot_pkg: Dict[str,Any]) -> Dict[str, Any]: # Unchanged
        pkg_logger = logger.getChild("PackageResults"); pkg_logger.info(f"Processor ({symbol_str_pkg}): Packaging results bundle..."); pkg_start_ts = datetime.now()
        bundle:Dict[str,Any]={"symbol":symbol_str_pkg.upper(),"fetch_timestamp":fetch_ts_pkg,"processing_timestamp":pkg_start_ts.isoformat(),"processor_version":"2.0.7-GreekFlowIntegration","error":final_error_message_pkg,"processed_data":{"options_chain":[]},"final_metric_rich_df_obj":final_metric_rich_df_obj_pkg,"key_levels":{"support":[],"resistance":[],"high_conviction":[],"structure_change":[]},"trading_signals":{},"strategy_recommendations":[],"underlying":{},"volatility":{},"config_snapshot":{},"atr_value_used":atr_value_used_pkg}; json_err=False
        try:
            converted_chain=self._convert_to_json_safe(final_metric_rich_df_obj_pkg)
            if isinstance(converted_chain,list): bundle["processed_data"]["options_chain"]=converted_chain
            else: json_err=True; bundle["processed_data"]["options_chain"]=[{"error":f"{JSON_CONVERSION_ERROR_PLACEHOLDER_PROC}: Main DF not list"}]
            for k_lvl_type in bundle["key_levels"].keys(): bundle["key_levels"][k_lvl_type]=self._convert_to_json_safe(levels_dict_pkg.get(k_lvl_type, pd.DataFrame()))
            bundle["trading_signals"]=self._convert_to_json_safe(signals_dict_pkg); bundle["strategy_recommendations"]=self._convert_to_json_safe(recommendations_list_pkg); bundle["underlying"]=self._convert_to_json_safe(underlying_data_pkg or {}); bundle["volatility"]=self._convert_to_json_safe(volatility_data_pkg or {})
            rel_cfg_parts={"data_processor_settings":processor_config_snapshot_pkg.get("data_processor_settings"),"strategy_settings":processor_config_snapshot_pkg.get("strategy_settings"),"system_settings":{"log_level":processor_config_snapshot_pkg.get("system_settings",{}).get("log_level")}}; bundle["config_snapshot"]=self._convert_to_json_safe(rel_cfg_parts)
            if JSON_CONVERSION_ERROR_PLACEHOLDER_PROC in str(bundle): json_err=True; pkg_logger.error(f"Packaging Err ({symbol_str_pkg}): JSON conversion errors detected.")
            pkg_dur_s=(datetime.now()-pkg_start_ts).total_seconds(); log_fn=pkg_logger.error if json_err else pkg_logger.info; log_fn(f"Processor ({symbol_str_pkg}): Packaging done in {pkg_dur_s:.3f}s.{' JSON errors.' if json_err else ''}")
        except Exception as e_pkg:
            pkg_err_txt=f"Unexpected packaging error: {e_pkg}"; pkg_logger.error(f"Processor ({symbol_str_pkg}): {pkg_err_txt}",exc_info=True); curr_bndl_err=bundle.get("error"); bundle["error"]=f"{curr_bndl_err} | {pkg_err_txt}".strip(" | ") if curr_bndl_err else pkg_err_txt
            if not isinstance(bundle["processed_data"]["options_chain"],list) or not bundle["processed_data"]["options_chain"]: bundle["processed_data"]["options_chain"]=[{"error":f"{JSON_CONVERSION_ERROR_PLACEHOLDER_PROC}: Packaging critical fail"}]
            if "final_metric_rich_df_obj" not in bundle or not isinstance(bundle.get("final_metric_rich_df_obj"),pd.DataFrame): bundle["final_metric_rich_df_obj"]=final_metric_rich_df_obj_pkg if isinstance(final_metric_rich_df_obj_pkg,pd.DataFrame) else pd.DataFrame()
        return bundle
    def process_data_with_integrated_strategies(self, options_chain_df: Optional[pd.DataFrame], underlying_data: Optional[Dict] = None, volatility_data: Optional[Dict] = None, historical_ohlc_df: Optional[pd.DataFrame] = None ) -> Dict[str, Any]: # Signature unchanged
        sym_proc="UnknownSymbol"; fetch_ts_proc=None
        if isinstance(underlying_data,dict):
            sym_proc=underlying_data.get("symbol","UnknownSymbol").upper()
            fetch_ts_proc=underlying_data.get("fetch_timestamp")
        elif isinstance(options_chain_df,pd.DataFrame) and not options_chain_df.empty:
             if "underlying_symbol" in options_chain_df.columns and pd.notna(options_chain_df["underlying_symbol"].iloc[0]):
                 sym_proc=str(options_chain_df["underlying_symbol"].iloc[0]).upper()
             elif "symbol" in options_chain_df.columns and pd.notna(options_chain_df["symbol"].iloc[0]):
                 # --- START OF CORRECTION (Already applied in my previous full file content) ---
                 try:
                     sym_proc=str(options_chain_df["symbol"].iloc[0]).upper().split(':')[0]
                 except: # Broad except to catch any error during split and continue
                     pass # sym_proc remains as previously set or "UnknownSymbol"
                 # --- END OF CORRECTION ---
             if "fetch_timestamp" in options_chain_df.columns and pd.notna(options_chain_df["fetch_timestamp"].iloc[0]):
                 # --- START OF CORRECTION (Already applied in my previous full file content) ---
                 try:
                     fetch_ts_proc=str(options_chain_df["fetch_timestamp"].iloc[0])
                 except: # Broad except
                     pass # fetch_ts_proc remains None or as previously set
                 # --- END OF CORRECTION ---
        if fetch_ts_proc is not None and not isinstance(fetch_ts_proc,str): fetch_ts_proc=str(fetch_ts_proc)
        logger.info(f"\n--- [Processor V2.0.7 Start] Processing for: {sym_proc} (Fetched: {fetch_ts_proc}) ---"); logger.info(f"Processor ({sym_proc}): OHLCV shape: {historical_ohlc_df.shape if isinstance(historical_ohlc_df,pd.DataFrame) else 'None'}"); logger.info(f"Processor ({sym_proc}): Volatility data: {str(volatility_data)[:100] if volatility_data else 'None'}")
        valid_opts_df,val_err_str=self._validate_input_data(options_chain_df,sym_proc); strict_val_mode=self.processor_config.get("data_processor_settings",{}).get("perform_strict_column_validation",True)
        if valid_opts_df is None or (val_err_str and strict_val_mode):
            final_err=val_err_str or "Input validation fail (strict)."; logger.error(f"--- [Processor V2.0.7 End] ({sym_proc}) Validation failed: {final_err} ---")
            return self._package_results(sym_proc,fetch_ts_proc,pd.DataFrame(),{},{},[],underlying_data,volatility_data,None,final_err,self.processor_config)
        current_work_df=valid_opts_df; overall_err:Optional[str]=val_err_str
        try: current_work_df=self._prepare_dataframe(current_work_df,underlying_data,sym_proc)
        except Exception as e_prep: prep_err=f"DF prep fail: {e_prep}"; logger.error(f"Processor ({sym_proc}): {prep_err}",exc_info=True); overall_err=f"{overall_err} | {prep_err}".strip(" | ") if overall_err else prep_err; return self._package_results(sym_proc,fetch_ts_proc,current_work_df,{},{},[],underlying_data,volatility_data,None,overall_err,self.processor_config)
        
        try: df_with_all_flows = self._calculate_all_strike_level_flows(current_work_df, sym_proc)
        except Exception as e_flow_calc:
            flow_err_str = f"All flow/pressure metric calculation failed: {e_flow_calc}"; logger.error(f"Processor ({sym_proc}): {flow_err_str}", exc_info=True)
            overall_err = f"{overall_err} | {flow_err_str}".strip(" | ") if overall_err else flow_err_str
            return self._package_results(sym_proc,fetch_ts_proc,current_work_df,{},{},[],underlying_data,volatility_data,None,overall_err,self.processor_config)
        
        final_metric_rich_df, lvls_its, sigs_its, recs_list, atr_val_used, its_err = self._apply_integrated_strategies(df_after_pressure_calc=df_with_all_flows, underlying_data_bundle_from_fetcher=underlying_data or {}, volatility_data_for_its=volatility_data or {}, historical_ohlc_data_for_atr=historical_ohlc_df, symbol_str_context=sym_proc)
        if its_err: overall_err = f"{overall_err if overall_err else ''} | {its_err}".strip(" | ")
        final_bundle = self._package_results(sym_proc,fetch_ts_proc,final_metric_rich_df,lvls_its,sigs_its,recs_list,underlying_data,volatility_data,atr_val_used,overall_err,self.processor_config)
        final_log_lvl = logging.ERROR if final_bundle.get("error") else logging.INFO; final_stat_msg = final_bundle.get('error','Success'); log_stat_disp = (str(final_stat_msg)[:150]+'...') if isinstance(final_stat_msg,str) and len(final_stat_msg)>150 else final_stat_msg
        logger.log(final_log_lvl, f"--- [Processor V2.0.7 End] Finished for: {sym_proc}. Status: '{log_stat_disp}' ---"); return final_bundle
    def process_market_data(self, market_data_bundle_dict: Dict[str, Any]) -> Dict[str, Any]: # Largely unchanged
        mkt_logger = logger.getChild("MarketProcessor"); mkt_logger.info("--- [Processor V2.0.7] Market Data Aggregation START ---"); errors_list:List[str]=[]; prim_sym_cfg=self.processor_config.get("market_primary_symbol","SPX"); mkt_fetch_ts:Optional[str]=None; num_proc,num_err=0,0
        prim_sym_bndl=market_data_bundle_dict.get(prim_sym_cfg)
        if isinstance(prim_sym_bndl,dict): mkt_fetch_ts=prim_sym_bndl.get("fetch_timestamp")
        elif market_data_bundle_dict: first_key=next(iter(market_data_bundle_dict),None); mkt_fetch_ts=market_data_bundle_dict[first_key].get("fetch_timestamp") if first_key and isinstance(market_data_bundle_dict.get(first_key),dict) else None
        for sym_k,sym_bndl_val in market_data_bundle_dict.items():
            if isinstance(sym_bndl_val,dict): num_proc+=1; err_val=sym_bndl_val.get("error"); errors_list.append(f"{sym_k}: {err_val}" if err_val else "") ; num_err+=1 if err_val else 0
            else: errors_list.append(f"{sym_k}: Invalid bundle type ({type(sym_bndl_val)})."); num_err+=1
        errors_list = [e for e in errors_list if e] # Filter out empty error strings
        mkt_err_sum_txt = f"Processed {num_proc} symbols. {num_err} had errors." if errors_list else None
        if errors_list: mkt_logger.warning(f"Market Proc: Errors (first 5): {errors_list[:5]}...")
        json_safe_cfg=self._convert_to_json_safe(self.processor_config)
        processed_mkt_bndl:Dict[str,Any]={"symbol":"MARKET_OVERVIEW_SNAPSHOT","fetch_timestamp":mkt_fetch_ts,"processing_timestamp":datetime.now().isoformat(),"processor_version":"2.0.7-GreekFlowIntegration","config_snapshot":json_safe_cfg,"error":mkt_err_sum_txt,"individual_symbol_errors":errors_list,"summary_metrics":{"info":"Market summary not yet implemented."},"market_signals":{"info":"Market signals not yet implemented."}}
        final_mkt_log_stat="Errors encountered" if mkt_err_sum_txt else "Success"; mkt_logger.info(f"--- [Processor V2.0.7] Market Data Aggregation Complete. Status: {final_mkt_log_stat} ---"); return processed_mkt_bndl

if __name__ == "__main__":
    main_proc_test_logger = logger.getChild("ProcessorTestMain")
    main_proc_test_logger.info("--- EnhancedDataProcessor V2.0.7 Test Run (Greek Flow Integration) --- ")
    test_cfg_path_main = DEFAULT_CONFIG_PATH_PROC
    if not os.path.exists(test_cfg_path_main):
         main_proc_test_logger.warning(f"Main config '{test_cfg_path_main}' not found. Using internal defaults & creating dummy if possible.")
         try:
             with open(test_cfg_path_main,'w') as f_cfg_dum: json.dump({"system_settings":{"log_level":"DEBUG"}, "data_processor_settings":{"perform_strict_column_validation":False}},f_cfg_dum) # Make strict validation false for dummy
             main_proc_test_logger.info(f"Created dummy '{test_cfg_path_main}' for test.")
         except Exception as e_cfg_dum_crt: main_proc_test_logger.error(f"Could not create dummy config: {e_cfg_dum_crt}")
    try:
         processor_test_instance = EnhancedDataProcessor(config_path=test_cfg_path_main)
         main_proc_test_logger.info("\n--- Test Case: Basic Options Chain with Greek Flows (Processor V2.0.7) ---")
         sample_opts_data_gf = {
            "strike":[100.0,100.0,105.0,105.0],"opt_kind":["call","put","call","put"], "symbol":["GFOPT"]*4, "underlying_symbol":["GFTEST"]*4,
            "fetch_timestamp":[datetime.now().isoformat()]*4, "price":[102.50]*4, # Underlying price
            # Heuristic Pressure Inputs
            "volm_buy": [10,5,8,6], "volm_sell": [3,2,4,3], "value_buy": [1000,50,800,60], "value_sell": [300,20,400,30],
            # True Net Flow Inputs (from API's _bs fields)
            "volm_bs": [7,3,4,3], "value_bs": [700,30,400,30],
            # Delta Flows
            "deltas_buy": [100, -40, 80, -30], "deltas_sell": [20, -10, 15, -5],
            # Gamma Flows
            "gammas_buy": [10,10,8,8], "gammas_sell": [3,3,2,2],
            # Vega Flows
            "vegas_buy": [50,50,40,40], "vegas_sell": [10,10,8,8],
            # Theta Flows (typically negative)
            "thetas_buy": [-20,-20,-15,-15], "thetas_sell": [-5,-5,-4,-4],
            # Other Greek OI/Flows needed by ITS
            'gxoi':[100,100,80,80],'dxoi':[1000,-400,800,-300],'txoi':[-10,-10,-8,-8],'vxoi':[20,20,15,15],'charmxoi':[1,1,0.8,0.8],'vannaxoi':[5,5,4,4],'vommaxoi':[0.1,0.1,0.08,0.08],
            'gxvolm':[10,10,8,8],'dxvolm':[100,-40,80,-30],'txvolm':[-1,-1,-0.8,-0.8],'vxvolm':[5,5,4,4],'charmxvolm':[0.1,0.1,0.08,0.08],'vannaxvolm':[0.5,0.5,0.4,0.4],'vommaxvolm':[0.01,0.01,0.008,0.008],
            'oi':[100,100,80,80],'volm':[10,10,8,8], 'volatility':[0.2,0.2,0.18,0.18]
         }
         sample_df_gf = pd.DataFrame(sample_opts_data_gf)
         sample_und_gf = { "symbol": "GFTEST", "price": 102.50, "fetch_timestamp": datetime.now().isoformat(), "volatility": 0.19 }
         ohlc_dates_gf = [date.today() - timedelta(days=i) for i in range(15,0,-1)]; sample_ohlc_hist_data_gf = {'date':pd.to_datetime(ohlc_dates_gf),'open':np.random.uniform(98,100,15),'high':np.random.uniform(100,103,15),'low':np.random.uniform(97,99,15),'close':np.random.uniform(99,102,15),'volume':np.random.randint(100000,500000,15)}; sample_ohlc_df_gf=pd.DataFrame(sample_ohlc_hist_data_gf)
         sample_vol_data_gf = {"current_iv":0.19, "avg_iv_5day":0.185, "iv_percentile_30d":0.40}
         result_bundle_gf = processor_test_instance.process_data_with_integrated_strategies(options_chain_df=sample_df_gf,underlying_data=sample_und_gf,volatility_data=sample_vol_data_gf,historical_ohlc_df=sample_ohlc_df_gf)
         main_proc_test_logger.info(f"Test Run GF - Error in Bundle: {result_bundle_gf.get('error')}")
         df_obj_proc_gf = result_bundle_gf.get("final_metric_rich_df_obj")
         if isinstance(df_obj_proc_gf, pd.DataFrame) and not df_obj_proc_gf.empty:
             main_proc_test_logger.info(f"Test Run GF - Processed DF shape: {df_obj_proc_gf.shape}")
             cols_to_check_in_output = [NET_HEURISTIC_VALUE_PRESSURE_COL, NET_HEURISTIC_VOLUME_PRESSURE_COL, NET_HEURISTIC_DELTA_PRESSURE_COL, NET_DELTA_FLOW_TOTAL_COL, NET_GAMMA_FLOW_COL, NET_VEGA_FLOW_COL, NET_THETA_EXPOSURE_COL, TRUE_NET_VOLUME_FLOW_COL, TRUE_NET_VALUE_FLOW_COL, "mspi"]
             main_proc_test_logger.info(f"Test Run GF - Checking for new/key columns (first record if available):")
             for col_chk in cols_to_check_in_output:
                 if col_chk in df_obj_proc_gf.columns: main_proc_test_logger.info(f"  Found '{col_chk}'. Example value: {df_obj_proc_gf[col_chk].iloc[0] if not df_obj_proc_gf.empty else 'N/A_DF_EMPTY'}")
                 else: main_proc_test_logger.error(f"  MISSING Column '{col_chk}' in processed output!")
         else: main_proc_test_logger.error("Test Run GF - 'final_metric_rich_df_obj' is MISSING or not a valid DataFrame!")
    except Exception as e_proc_test_main_gf: main_proc_test_logger.critical(f"Error during EnhancedDataProcessor Greek Flow test run: {e_proc_test_main_gf}", exc_info=True)
    main_proc_test_logger.info("--- EnhancedDataProcessor V2.0.7 Test Run Complete ---")