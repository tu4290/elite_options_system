# data_management/initial_processor_v2_5.py
# (Evolved from enhanced_data_processor_v2.py)
# EOTS v2.5 - Initial Data Processor

# Standard Library Imports
import os
import sys # Keep sys if used by your logger fallback
import json
import traceback
import logging
from datetime import datetime, date, time as dt_time, timedelta
import time as pytime # Alias to avoid conflict
from typing import Dict, Any, Optional, List, Union, Tuple, Callable # Added Callable
import copy # Used in your original enhanced_data_processor_v2.py

# Third-Party Imports
import pandas as pd
import numpy as np

# --- Project-Specific Imports ---
# Assuming project root is in sys.path, allowing absolute imports for other packages

# To import MetricsCalculatorV2_5 from core_analytics_engine
from core_analytics_engine.metrics_calculator_v2_5 import MetricsCalculatorV2_5

# To import utilities. Assuming system_utilities.py is in core_analytics_engine/
# If system_utilities.py is in a top-level utils/ package, this would be:
# from utils.system_utilities import ensure_columns, normalize_series # etc.
from core_analytics_engine.system_utilities import ensure_columns, normalize_series 
# Add any other utilities you directly use in this processor class from system_utilities

# To import ConfigManagerV2_5 if the processor needs to fetch its own config values.
# This assumes ConfigManagerV2_5 is defined in utils/config_manager_v2_5.py
# from utils.config_manager_v2_5 import ConfigManagerV2_5 # Example if needed directly

# --- Global Logger Setup ---
# It's generally best if the main runner script configures the root logger.
# This module can then just get its own logger.
logger = logging.getLogger(__name__)
# Fallback basic config if no handlers are configured by the main application
if not logger.hasHandlers() and not logging.getLogger().hasHandlers():
    _init_proc_log_formatter = logging.Formatter(
        '[%(levelname)s] (%(name)s:%(lineno)d) %(asctime)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    _init_proc_log_handler = logging.StreamHandler(sys.stdout) # Use sys.stdout
    _init_proc_log_handler.setFormatter(_init_proc_log_formatter)
    logger.addHandler(_init_proc_log_handler)
    # Set a default level for this logger if not configured higher up
    # This might be overridden by main app's logging config
    logger.setLevel(os.environ.get("LOG_LEVEL_INIT_PROC", "INFO").upper())


# --- Constants ---
# Constants specific to this processor can remain here or be fetched from config.
JSON_CONVERSION_ERROR_PLACEHOLDER_PROC = "JSON_CONVERSION_ERROR_IN_INITIAL_PROCESSOR"
MIN_NORMALIZATION_DENOMINATOR_PROC = 1e-9 # If used directly for normalization here


class InitialDataProcessorV2_5:
    """
    Handles initial processing of raw data from fetchers and orchestrates
    the full metric calculation via MetricsCalculatorV2_5 for the EOTS v2.5 system.
    """
    def __init__(self, 
                 config_value_getter: Callable[[List[str], Any, Optional[str]], Any], 
                 its_orchestrator_ref: Optional[Any] = None): # Pass a config getter function
        """
        Initializes the InitialDataProcessorV2_5.

        Args:
            config_value_getter (Callable): A function (e.g., from ConfigManager or ITSOrchestrator)
                                           that can retrieve configuration values.
                                           It should accept (path: List[str], default: Any, symbol_context: Optional[str])
            its_orchestrator_ref (Optional[Any]): A reference to the main ITSOrchestratorV2_5 instance
                                                 if needed for accessing shared components like
                                                 historical_data_manager or adaptive_historical_context.
        """
        self.logger = logger.getChild(self.__class__.__name__)
        self._get_config_value = config_value_getter # Store the passed getter
        self.its_orchestrator_ref = its_orchestrator_ref

        # Instantiate MetricsCalculatorV2_5, passing the config_value_getter
        # MetricsCalculatorV2_5 will use this to fetch its own specific configurations.
        self.metrics_calculator = MetricsCalculatorV2_5(
            config_value_getter=self._get_config_value,
            # historical_data_manager_ref can be passed if Orchestrator provides it via its_orchestrator_ref
            # For example:
            # historical_data_manager_ref = self.its_orchestrator_ref.historical_manager 
            #                             if self.its_orchestrator_ref and hasattr(self.its_orchestrator_ref, 'historical_manager') 
            #                             else None,
            log_instance = self.logger # Pass logger instance
        )
        
        # Key column names - fetch from config to ensure flexibility
        viz_col_names_cfg_proc = self._get_config_value(["visualization_settings", "mspi_visualizer", "column_names"], {}, symbol_context=None) # Global viz settings
        self.col_strike_proc: str = str(viz_col_names_cfg_proc.get("strike", "strike"))
        self.col_expiration_date_proc: str = str(viz_col_names_cfg_proc.get("expiration_date", "expiration_date"))
        # Add other column names this processor directly uses if they come from config

        self.logger.info(f"InitialDataProcessorV2_5 initialized. Strike col: '{self.col_strike_proc}'.")

    def _add_essential_context_columns(self, 
                                       options_df: pd.DataFrame, 
                                       underlying_price: Optional[float], 
                                       current_datetime: datetime,
                                       symbol: str) -> pd.DataFrame:
        """
        Adds essential context columns like DTE, current underlying price reference, 
        and processing timestamp to the options DataFrame.
        """
        df = options_df.copy()
        if self.col_expiration_date_proc in df.columns:
            try:
                # Ensure 'expiration_date' is datetime.date for DTE calculation
                exp_dates = pd.to_datetime(df[self.col_expiration_date_proc], errors='coerce').dt.date
                df['dte_calculated'] = (exp_dates - current_datetime.date()).apply(lambda x: x.days if pd.notna(x) else -1)
            except Exception as e_dte_calc:
                self.logger.error(f"Error calculating DTE for symbol {symbol}: {e_dte_calc}", exc_info=True)
                df['dte_calculated'] = np.nan # Or -1 or some other error indicator
        else:
            self.logger.warning(f"'{self.col_expiration_date_proc}' column not found for DTE calculation for symbol {symbol}.")
            df['dte_calculated'] = np.nan

        if underlying_price is not None and pd.notna(underlying_price):
            df['underlying_price_at_processing'] = underlying_price
        else:
            self.logger.warning(f"Missing valid underlying_price for symbol {symbol} during context column addition.")
            df['underlying_price_at_processing'] = np.nan
            
        df['processing_timestamp_utc'] = current_datetime.timestamp() # Store as UTC epoch seconds
        df['symbol_processed'] = symbol
        return df

    def process_raw_data_bundle(self, 
                                raw_data_bundle: Dict[str, Any], 
                                current_processing_datetime: datetime, 
                                symbol: str,
                                # Contexts needed by MetricsCalculatorV2_5 (passed down)
                                current_time_ctx: Optional[dt_time],
                                current_iv_ctx: Optional[float],
                                avg_iv_5day_ctx: Optional[float],
                                iv_context_dict_ctx: Optional[Dict[str, Any]],
                                underlying_price_ctx: Optional[float],
                                historical_ohlc_df_ctx: Optional[pd.DataFrame],
                                avg_iv_long_term_ctx: Optional[float],
                                historical_atr_normalized_vs_avg_ctx: Optional[float],
                                ticker_context_dict_ctx: Optional[Dict[str, Any]], 
                                symbol_specific_adaptive_context_its: Optional[Dict[str, Any]]
                               ) -> Dict[str, Any]:
        """
        Processes the raw data bundle for a symbol:
        1. Validates and performs basic cleaning/preparation.
        2. Adds essential context columns to the options DataFrame.
        3. Invokes MetricsCalculatorV2_5 to perform all detailed metric calculations.
        4. Packages and returns the comprehensive "processed data bundle".
        """
        self.logger.info(f"InitialProcessor: Processing raw data bundle for {symbol} at {current_processing_datetime.isoformat()}")

        raw_options_df = raw_data_bundle.get('options_chain') 
        raw_underlying_dict_combined = raw_data_bundle.get('underlying_data_combined') 

        if not isinstance(raw_options_df, pd.DataFrame) or raw_options_df.empty:
            self.logger.error(f"InitialProcessor: Raw options_df for {symbol} is empty or invalid. Cannot proceed.")
            return {"error": f"Raw options data for {symbol} was empty or invalid."}
        if not isinstance(raw_underlying_dict_combined, dict) or not raw_underlying_dict_combined:
             self.logger.error(f"InitialProcessor: Raw underlying_dict_combined for {symbol} is empty or invalid. Cannot proceed.")
             return {"error": f"Raw underlying data for {symbol} was empty or invalid."}

        # Ensure basic required columns are present early, e.g., strike, opt_kind for options_df
        # These would be the actual column names coming from the fetcher.
        # `self.col_strike_proc` and others are how this processor will refer to them.
        options_df_prepared, cols_ok = ensure_columns(
            raw_options_df, 
            [self.col_strike_proc, self.col_expiration_date_proc], # Add other absolutely essential raw cols
            "InitialProcessor_RawOptionsCheck", 
            log_instance=self.logger
        )
        if not cols_ok:
            self.logger.error(f"InitialProcessor: Essential columns missing from raw_options_df for {symbol}. Cannot proceed.")
            return {"error": f"Essential columns missing in raw options data for {symbol}."}
        
        # Add essential context columns
        options_df_prepared = self._add_essential_context_columns(
            options_df_prepared, 
            underlying_price_ctx, # Use the more reliable underlying_price_ctx passed down
            current_processing_datetime, 
            symbol
        )
        
        # Invoke MetricsCalculatorV2_5
        # The orchestrator (ITS) prepares and passes all necessary contextual data
        metrics_output_bundle = self.metrics_calculator.orchestrate_all_metric_calculations_v2_5(
            options_df_prepared=options_df_prepared.copy(), 
            underlying_data_dict_prepared=copy.deepcopy(raw_underlying_dict_combined),
            current_processing_datetime_mc=current_processing_datetime,
            symbol_mc=symbol,
            # Pass all context values obtained from ITS/Orchestrator
            current_time_mc=current_time_ctx,
            current_iv_mc=current_iv_ctx,
            avg_iv_5day_mc=avg_iv_5day_ctx,
            iv_context_dict_mc=iv_context_dict_ctx,
            underlying_price_mc=underlying_price_ctx,
            historical_ohlc_df_for_atr_mc=historical_ohlc_df_ctx,
            avg_iv_long_term_mc=avg_iv_long_term_ctx,
            historical_atr_normalized_vs_avg_mc=historical_atr_normalized_vs_avg_ctx,
            ticker_context_dict_mc=ticker_context_dict_ctx, 
            symbol_specific_adaptive_context_mc=symbol_specific_adaptive_context_its 
        )
        
        if "error" in metrics_output_bundle:
             self.logger.error(f"InitialProcessor: Error from MetricsCalculatorV2_5 for {symbol}: {metrics_output_bundle['error']}")
             return metrics_output_bundle 

        self.logger.info(f"InitialProcessor: Successfully processed data and calculated metrics for {symbol}.")
        # metrics_output_bundle should contain keys like:
        # 'options_df_with_metrics_obj', 'df_strike_level_metrics_obj', 'underlying_data_enriched_obj'
        return metrics_output_bundle

# --- Main block for standalone testing (if needed) ---
if __name__ == '__main__':
    # This block would be for testing InitialDataProcessorV2_5 in isolation.
    # It would require creating a mock ConfigManager or config_value_getter,
    # and mock raw_data_bundle.
    
    # Basic logging for the test
    logging.basicConfig(level=logging.DEBUG, format='[%(levelname)s] (%(name)s:%(lineno)d) %(asctime)s - %(message)s')
    test_proc_logger = logging.getLogger("InitialProcessor_Standalone_Test")
    test_proc_logger.info("--- Running InitialDataProcessorV2_5 Standalone Test ---")

    # 1. Mock Config Value Getter
    # In a real test, you might load a test config_v2.json
    mock_config_data_proc = {
        "visualization_settings": {"mspi_visualizer": {"column_names": {"strike": "strike", "expiration_date": "expiration"}}},
        # Add any other config paths MetricsCalculatorV2_5 or InitialDataProcessorV2_5 needs
        "metrics_calculator_v2_5_settings": { # Placeholder for what MetricsCalculator needs
            "base_metric_toggles": {"dag_custom_enabled": True, "tdpi_enabled": True, "vri_enabled": True, "original_sdags_enabled": True},
            "adaptive_metric_params": {
                "a_dag_settings": {"base_dag_alpha_coeffs": {"aligned":1.3,"opposed":0.7,"neutral":1.0}},
                "d_tdpi_settings": {"base_tdpi_beta_coeffs": {"aligned":1.3,"opposed":0.7,"neutral":1.0}, "base_tdpi_gaussian_width": -0.45},
                "vri_2_0_settings": {"base_vri_gamma_coeffs": {"aligned":1.3,"opposed":0.7,"neutral":1.0}},
                "e_sdag_settings": {"use_enhanced_skew_calculation_for_sgexoi": False}
             },
             "atr_calculation_params": {"fallback_settings": {"type":"percentage_of_price", "percentage":0.005, "min_value":1.0}}
        },
         "system_settings": {"signal_activation_v2_5": {"master_enable_all_raw_signals": False}} # Example: Turn off enhanced for this test
    }
    def mock_config_getter_proc(path: List[str], default_override: Any = None, symbol_context: Optional[str] = None) -> Any:
        current = mock_config_data_proc
        try:
            for key in path: current = current[key]
            return current
        except KeyError: return default_override

    # 2. Instantiate Processor
    try:
        processor = InitialDataProcessorV2_5(config_value_getter=mock_config_getter_proc)
        test_proc_logger.info("InitialDataProcessorV2_5 instantiated for test.")

        # 3. Create Mock Raw Data Bundle
        test_symbol_proc = "MOCKSPY"
        current_price_test_proc = 450.0
        mock_options_data_proc = []
        for i in range(5): # Small sample
            mock_options_data_proc.append({
                "strike": current_price_test_proc + (i - 2) * 5, "expiration": (date.today() + timedelta(days=10)).isoformat(),
                "opt_kind": "call" if i % 2 == 0 else "put", "price": current_price_test_proc,
                "underlying_symbol": test_symbol_proc, "volatility": 0.20 + i*0.01,
                "delta": 0.5 + (i-2)*0.1, "gamma": 0.02, "theta": -0.05, "vega": 0.1,
                "oi": 100 + i*10, "volm": 50 + i*5,
                "gxoi": (0.02) * (100+i*10) * 100, "dxoi": (0.5+(i-2)*0.1) * (100+i*10) * 100,
                # Add other required raw fields based on what your metrics_calculator expects
                # For simplicity, many are omitted here. Refer to metrics_calculator's needs.
                "charmxoi": np.random.rand() * 1e5, "txoi": np.random.rand() * -1e5, 
                "vannaxoi": np.random.rand() * 1e5, "vxoi": np.random.rand() * 1e6, "vommaxoi": np.random.rand() * 1e4,
                "deltas_buy": np.random.rand()*1e4, "deltas_sell": np.random.rand()*1e4, "proxy_delta_flow_col": np.random.rand()*1e4, # Example proxy col name
                "gammas_buy": np.random.rand()*1e3, "gammas_sell": np.random.rand()*1e3, "proxy_gamma_flow_col": np.random.rand()*1e3,
                "thetas_buy": np.random.rand()*-1e3, "thetas_sell": np.random.rand()*-1e3, "proxy_theta_flow_col": np.random.rand()*-1e3,
                "charmxvolm": np.random.rand()*1e3, "proxy_charm_flow_col": np.random.rand()*1e3,
                "vegas_buy": np.random.rand()*1e3, "vegas_sell": np.random.rand()*1e3, "proxy_vega_flow_col": np.random.rand()*1e3,
                "vannaxvolm": np.random.rand()*1e3, "proxy_vanna_flow_col": np.random.rand()*1e3,
                "vommaxvolm": np.random.rand()*1e3, "proxy_vomma_flow_col": np.random.rand()*1e3,
            })
        mock_options_df_proc = pd.DataFrame(mock_options_data_proc)
        # Ensure all columns needed by metrics_calculator are present and correctly named
        # Map names from ITS attributes to what calculator expects if different
        # (e.g. from its_orchestrator_v2_5)
        # For this basic test, we directly use some names from the config
        # These mappings will be crucial in the real ITS orchestrator
        
        mock_underlying_data_proc = {
            "price": current_price_test_proc, "volatility": 0.21, "symbol": test_symbol_proc, "multiplier": 100,
            "underlying_symbol": test_symbol_proc, # Ensure this matches options_df's reference
            # Add other required underlying fields
        }
        mock_raw_bundle_proc = {
            "options_chain": mock_options_df_proc,
            "underlying_data_combined": mock_underlying_data_proc
        }

        # 4. Mock Contextual Data
        mock_current_time_proc = datetime.now().time()
        mock_iv_context_proc = {"current_iv_rank": 0.55, "current_iv":0.21} # Example
        
        # 5. Process
        processed_bundle = processor.process_raw_data_bundle(
            raw_data_bundle=mock_raw_bundle_proc,
            current_processing_datetime=datetime.now(),
            symbol=test_symbol_proc,
            current_time_ctx=mock_current_time_proc,
            current_iv_ctx=mock_iv_context_proc.get("current_iv"),
            avg_iv_5day_ctx=0.20, # Mock
            iv_context_dict_ctx=mock_iv_context_proc,
            underlying_price_ctx=current_price_test_proc,
            historical_ohlc_df_ctx=None, # Mock - ATR will use fallback
            avg_iv_long_term_ctx=0.22, # Mock
            historical_atr_normalized_vs_avg_ctx=1.0, # Mock
            ticker_context_dict_ctx={"is_0DTE_SPX_Friday_PM": False}, # Mock
            symbol_specific_adaptive_context_its={} # Mock
        )

        if "error" in processed_bundle:
            test_proc_logger.error(f"Error processing bundle: {processed_bundle['error']}")
        else:
            test_proc_logger.info("Processed bundle successfully (standalone test).")
            test_proc_logger.info(f"  Enriched Underlying Data Keys: {list(processed_bundle.get('underlying_data_enriched_obj', {}).keys())}")
            test_proc_logger.info(f"  Options DF with Metrics Shape: {processed_bundle.get('options_df_with_metrics_obj', pd.DataFrame()).shape}")
            test_proc_logger.info(f"  Strike Level Metrics DF Shape: {processed_bundle.get('df_strike_level_metrics_obj', pd.DataFrame()).shape}")
            if isinstance(processed_bundle.get('df_strike_level_metrics_obj'), pd.DataFrame) and not processed_bundle['df_strike_level_metrics_obj'].empty:
                 mspi_col_name_test = mock_config_getter_proc(["visualization_settings", "mspi_visualizer", "column_names", "mspi"], "a_mspi_overall_score")
                 if mspi_col_name_test in processed_bundle['df_strike_level_metrics_obj'].columns:
                    test_proc_logger.info(f"    MSPI '{mspi_col_name_test}' values example: {processed_bundle['df_strike_level_metrics_obj'][mspi_col_name_test].head(2).tolist()}")
                 else:
                    test_proc_logger.warning(f"    MSPI column '{mspi_col_name_test}' not found in strike level metrics.")


    except Exception as e_test_proc:
        test_proc_logger.critical(f"Error in InitialDataProcessorV2_5 standalone test: {e_test_proc}", exc_info=True)

    test_proc_logger.info("--- InitialDataProcessorV2_5 Standalone Test END ---")