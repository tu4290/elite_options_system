# utils/ids.py
# ids.py
# Centralized repository for Dash component IDs, DataFrame column names,
# API parameters, and Configuration Keys used throughout the EOTS system.
# Version: IDS-Canon-V2.0.1 - Comprehensive Integration & New Parameters (TXVOLM fix confirmed)
# Canon Directive: Focus on v2.3 level functionality for dry run.

# ==============================================================================
# I. DASH COMPONENT IDs
# ==============================================================================
# Extracted and consolidated from layout.py, callbacks.py, etc.

# --- Control Panel Component IDs ---
ID_SYMBOL_INPUT = "symbol-input-main-controls"
ID_DTE_INPUT = "expiration-input-main-controls"
ID_RANGE_SLIDER = "price-range-slider-main-controls"
ID_RANGE_SLIDER_OUTPUT_LABEL = "price-range-slider-label-main-controls"
ID_FETCH_DATA_BUTTON = "fetch-button-main-controls"
ID_REFRESH_INTERVAL_DROPDOWN = "interval-dropdown-main-controls"

# --- Mode Selection (Tabs) ---
ID_MODE_SELECTOR_TABS = "dashboard-mode-selector-tabs"
# ID_MODE_SELECTOR_DROPDOWN = "mode-selector-dropdown-id" # Kept if planned for future use

# --- Store Component IDs (for dcc.Store) ---
# ID_URL_LOCATION = "url-location-id" # Kept if used for URL routing
ID_MAIN_DATA_STORE_MEMORY = "cache-key-data-store-memory" # Main store for processed data cache key
ID_APP_CONFIG_STORE = "application-configuration-store-memory" # Stores app configuration
ID_CURRENT_MODE_STORE = "dashboard-current-active-mode-store" # Stores active tab/mode
ID_REFRESH_INTERVAL_STORE = "dashboard-refresh-interval-settings-store" # Stores refresh interval setting

# --- Layout Area & UI Element IDs ---
ID_STATUS_DISPLAY_AREA = "status-display-main-area" # For status messages
ID_MAIN_CONTENT_AREA = "dashboard-mode-display-content-area" # Where mode layouts are rendered
ID_ALERT_CONTAINER = "main-alert-container-dynamic" # For dynamic alerts
ID_OVERLAY_LOADING = "full-page-overlay-loading-spinner" # Loading spinner overlay

# --- Timer/Trigger IDs ---
ID_AUTO_REFRESH_INTERVAL_COMPONENT = "interval-timer-main-component" # The dcc.Interval component
ID_HIDDEN_INITIAL_LOAD_TRIGGER = "hidden-div-for-initial-load-trigger" # For triggering initial data load (e.g., from app config load)

# --- Chart Placeholder IDs (Main Dashboard View) ---
ID_CHART_KEY_LEVELS = "key-market-levels-chart"
ID_CHART_MSPI_COMPONENTS = "mspi-components-comparison-chart"
ID_CHART_MSPI_HEATMAP = "mspi-heatmap-main-chart"
ID_CHART_NET_GREEK_FLOW_HEATMAP = "net-greek-flow-heatmap-main-chart"
ID_CHART_COMBINED_ROLLING_FLOW = "combined-rolling-flow-main-chart"
ID_CHART_TRADING_SIGNALS = "generated-trading-signals-chart"
ID_CHART_RECOMMENDATIONS_TABLE = "strategy-recommendations-table-display"

# --- Chart Placeholder IDs (SDAG Diagnostics View) ---
ID_CHART_SDAG_MULTIPLICATIVE = "sdag-multiplicative-detail-chart"
ID_CHART_SDAG_DIRECTIONAL = "sdag-directional-detail-chart"
ID_CHART_SDAG_WEIGHTED = "sdag-weighted-detail-chart"
ID_CHART_SDAG_VOLATILITY_FOCUSED = "sdag-volatility-focused-detail-chart"

# --- Chart Placeholder IDs (Enhanced Flow View) ---
ID_CHART_NET_VALUE_HEATMAP = "net-value-pressure-heuristic-heatmap-chart"
ID_CHART_NET_VOLUME_PRESSURE_HEATMAP = "net-volume-pressure-heuristic-heatmap-chart"
# ID_CHART_VAPI_FA_OSCILLATOR = "vapi-fa-oscillator-flow-chart" # Review for v2.3 / v2.5 integration
# ID_CHART_DWFD_OSCILLATOR = "dwfd-oscillator-flow-chart" # Review for v2.3 / v2.5 integration
# ID_CHART_TW_LAF_OSCILLATOR = "tw-laf-oscillator-flow-chart" # Review for v2.3 / v2.5 integration

# --- Chart Placeholder IDs (Volatility Deep Dive View) ---
ID_CHART_VOLATILITY_REGIME = "volatility-regime-indicator-chart" # Likely plots VRI
ID_CHART_TIME_DECAY = "time-decay-pressure-indicator-chart" # Likely plots TDPI

# --- Selector IDs associated with specific charts ---
ID_MSPI_HEATMAP_SELECTOR = "mspi-heatmap-view-selector-dropdown"
ID_NET_GREEK_FLOW_SELECTOR = "net-greek-flow-metric-selector-dropdown"
ID_ROLLING_FLOW_SELECTOR = "combined-rolling-flow-type-selector-dropdown"

# --- Tab IDs for Mode Content ---
ID_TAB_MAIN_DASHBOARD = "tab-main-dashboard-view"
ID_TAB_SDAG_DIAGNOSTICS = "tab-sdag-diagnostics-view"
ID_TAB_ENHANCED_FLOW = "tab-enhanced-flow-view"
ID_TAB_VOLATILITY_DEEP_DIVE = "tab-volatility-deep-dive-view"
ID_TAB_PERFORMANCE = "tab-performance-view" # For future use

# --- Lists of Chart IDs for Callback Factory (consolidated for iteration) ---
ALL_CHART_IDS_FOR_FACTORY = [
    ID_CHART_KEY_LEVELS, ID_CHART_MSPI_COMPONENTS, ID_CHART_MSPI_HEATMAP,
    ID_CHART_NET_GREEK_FLOW_HEATMAP, ID_CHART_COMBINED_ROLLING_FLOW,
    ID_CHART_TRADING_SIGNALS, ID_CHART_RECOMMENDATIONS_TABLE,
    ID_CHART_SDAG_MULTIPLICATIVE, ID_CHART_SDAG_DIRECTIONAL,
    ID_CHART_SDAG_WEIGHTED, ID_CHART_SDAG_VOLATILITY_FOCUSED,
    ID_CHART_NET_VALUE_HEATMAP, ID_CHART_NET_VOLUME_PRESSURE_HEATMAP,
    ID_CHART_VOLATILITY_REGIME, ID_CHART_TIME_DECAY,
    # ID_CHART_VAPI_FA_OSCILLATOR, ID_CHART_DWFD_OSCILLATOR, ID_CHART_TW_LAF_OSCILLATOR, # Keep commented if not implemented
]

# Lists for organizing charts by tab content (used in layout.py to populate tabs)
MAIN_DASHBOARD_CHART_IDS_LIST = [
    ID_CHART_KEY_LEVELS, ID_CHART_MSPI_COMPONENTS, ID_CHART_MSPI_HEATMAP,
    ID_CHART_NET_GREEK_FLOW_HEATMAP, ID_CHART_COMBINED_ROLLING_FLOW,
    ID_CHART_TRADING_SIGNALS, ID_CHART_RECOMMENDATIONS_TABLE
]
SDAG_DIAGNOSTICS_CHART_IDS_LIST = [
    ID_CHART_SDAG_MULTIPLICATIVE, ID_CHART_SDAG_DIRECTIONAL,
    ID_CHART_SDAG_WEIGHTED, ID_CHART_SDAG_VOLATILITY_FOCUSED,
]
ENHANCED_FLOW_CHART_IDS_LIST = [
    ID_CHART_NET_VALUE_HEATMAP, ID_CHART_NET_VOLUME_PRESSURE_HEATMAP,
    # ID_CHART_VAPI_FA_OSCILLATOR, # Add when ready
]
VOLATILITY_DEEP_DIVE_CHART_IDS_LIST = [
    ID_CHART_VOLATILITY_REGIME, ID_CHART_TIME_DECAY,
]


# ==============================================================================
# II. DATAFRAME COLUMN NAMES
# ==============================================================================
# Standardized names for DataFrame columns used across various modules.
# Focus is on v2.3 relevant columns, but also includes v2.5 if EDP might pass them through.

# --- A. RAW DATA FETCH & INITIAL PARSING (Directly from fetchers or first-step standardizations) ---
# 1. Option Contract Identifiers & Characteristics
COL_CONTRACT_SYMBOL_API = "contract_symbol_api"       # Raw symbol from ConvexValue get_chain
COL_OPTION_SYMBOL = "symbol"                          # Standardized option symbol after parsing (e.g., SPY250609C500)
COL_UNDERLYING_SYMBOL = "underlying_symbol"     # Explicitly define this
COL_UNDERLYING_SYMBOL_CHAIN = "underlying_symbol"     # Underlying symbol associated with the option contract (e.g., SPY)
COL_STRIKE_API = "strike_api"                         # Raw strike from ConvexValue get_chain
COL_STRIKE = "strike_price"                           # Standardized, numeric strike price (used across system)
COL_OPT_KIND_API = "opt_kind_api"                     # Raw option type from ConvexValue get_chain
COL_OPT_KIND = "opt_kind"                             # Standardized ('call'/'put')
COL_EXPIRATION_DAYS_EPOCH_API = "expiration_days_epoch_api" # Raw from ConvexValue (days since 1970-01-01 epoch)
COL_EXPIRATION_DATE = "expiration_date"               # Standardized (YYYY-MM-DD string or datetime object)
COL_DATE = "date"                                     # Standardized date column for OHLCV data

# 2. Underlying Info (when merged into options_df or as standalone dict keys from get_und)
COL_UND_PRICE = "price"                        # Underlying price (from get_und or snapshot)
COL_UND_VOLATILITY = "volatility"              # Underlying's aggregate IV (from get_und)
COL_UND_DAY_VOLUME = "day_volume"              # Underlying's trading volume (from get_und)
COL_UND_FETCH_TIMESTAMP = "fetch_timestamp"    # Timestamp of data fetch (ISO format string)

# 3. Raw Greek OI (Open Interest based exposures from ConvexValue get_chain, per contract)
COL_GXOI_CONTRACT = "gxoi"           # Gamma * OI for the contract
COL_DXOI_CONTRACT = "dxoi"           # Delta * OI for the contract
COL_VXOI_CONTRACT = "vxoi"           # Vega * OI for the contract
COL_TXOI_CONTRACT = "txoi"           # Theta * OI for the contract
COL_CHARMXOI_CONTRACT = "charmxoi"   # Charm * OI for the contract
COL_VANNAXOI_CONTRACT = "vannaxoi"   # Vanna * OI for the contract
COL_VOMMAXOI_CONTRACT = "vommaxoi"   # Vomma * OI for the contract

# 4. Raw Per-Contract Greeks & Core Data (from ConvexValue get_chain)
COL_DELTA_CONTRACT = "delta"
COL_GAMMA_CONTRACT = "gamma"
COL_VEGA_CONTRACT = "vega"
COL_THETA_CONTRACT = "theta"
COL_VANNA_CONTRACT = "vanna"
COL_VOMMA_CONTRACT = "vomma"
COL_CHARM_CONTRACT = "charm"
COL_PRICE_OPTION_CONTRACT = "price"                 # Option's own market price
COL_VOLATILITY_OPTION_CONTRACT = "volatility"       # Option's Implied Volatility
COL_MULTIPLIER_OPTION_CONTRACT = "multiplier"       # Option multiplier (e.g., 100 for equities)
COL_OI_OPTION_CONTRACT = "oi"                       # Option's Open Interest
COL_VOLUME_OPTION_CONTRACT = "volm"                 # Option's traded volume
COL_BID_PRICE = "bid_price"
COL_ASK_PRICE = "ask_price"
COL_BID_SIZE = "bid_size"
COL_ASK_SIZE = "ask_size"
COL_HIGH = "high"                                   # High price for OHLCV
COL_LOW = "low"                                     # Low price for OHLCV
COL_OPEN = "open"                                   # Open price for OHLCV
COL_CLOSE = "close"                                 # Close price for OHLCV
COL_OI_CHG_TEMP = "oi_chg_temp"                 # Temporary column for OI change, used in SMI calc

# 5. Raw Per-Contract Customer Flows (from ConvexValue get_chain)
# These represent net customer activity for the specific contract, often derived from bid/ask side trades.
COL_DELTAS_BUY_CONTRACT = "deltas_buy"              # Net delta bought by customers for this contract
COL_DELTAS_SELL_CONTRACT = "deltas_sell"            # Net delta sold by customers for this contract
COL_GAMMAS_BUY_CONTRACT = "gammas_buy"
COL_GAMMAS_SELL_CONTRACT = "gammas_sell"
COL_VEGAS_BUY_CONTRACT = "vegas_buy"
COL_VEGAS_SELL_CONTRACT = "vegas_sell"
COL_THETAS_BUY_CONTRACT = "thetas_buy"
COL_THETAS_SELL_CONTRACT = "thetas_sell"
COL_VOLM_BUY_CONTRACT = "volm_buy"                  # Volume of this contract bought by customers
COL_VOLM_SELL_CONTRACT = "volm_sell"                # Volume of this contract sold by customers
COL_VALUE_BUY_CONTRACT = "value_buy"                # Value of this contract bought by customers
COL_VALUE_SELL_CONTRACT = "value_sell"              # Value of this contract sold by customers
COL_VALUE_BS_CONTRACT = "value_bs"                  # Net value (buy-sell) for this contract
COL_VOLM_BS_CONTRACT = "volm_bs"                    # Net volume (buy-sell) for this contract

# Rolling time window flow prefixes (from ConvexValue get_chain, per contract)
# Example: f"{CV_VALUE_BS_ROLLING_PREFIX}_5m" -> "valuebs_5m"
CV_VALUE_BS_ROLLING_PREFIX = "valuebs"
CV_VOLM_BS_ROLLING_PREFIX = "volmbs"

# 6. Raw Proxied Greek Flows (Greek-weighted volume from ConvexValue get_chain, per contract)
COL_DXVOLM_CONTRACT = "dxvolm"              # Delta-weighted volume
COL_GXVOLM_CONTRACT = "gxvolm"              # Gamma-weighted volume
COL_VXVOLM_CONTRACT = "vxvolm"              # Vega-weighted volume
COL_TXVOLM_CONTRACT = "txvolm"              # Theta-weighted volume
COL_CHARMXVOLM_CONTRACT = "charmxvolm"      # Charm-weighted volume
COL_VANNAXVOLM_CONTRACT = "vannaxvolm"      # Vanna-weighted volume
COL_VOMMAXVOLM_CONTRACT = "vommaxvolm"      # Vomma-weighted volume


# --- B. EDP PROCESSED COLUMNS (Added by EnhancedDataProcessor before ITS) ---
COL_CURRENT_PRICE_EDP = "current_price"             # Underlying price added to each option row for context
COL_DISTANCE_FROM_CURRENT_EDP = "distance_from_current" # Strike - current_price
COL_PCT_DISTANCE_FROM_CURRENT_EDP = "pct_distance_from_current" # (Strike - current_price) / current_price * 100
COL_FETCH_TIMESTAMP_EDP = "fetch_timestamp"         # Standardized fetch timestamp on each row (ISO string)
COL_UNDERLYING_PRICE_AT_FETCH_EDP = "underlying_price_at_fetch" # Price at time of fetch (redundant but explicit)
COL_EDP_PREPARATION_TIMESTAMP_EDP = "edp_dataframe_preparation_timestamp" # Timestamp EDP finished initial prep

# --- C. IMPACT CALCULATION OUTPUTS (Direct outputs from core_analytics.impact_calculations) ---
# These are the names your impact_calculations.py module currently produces.
COL_IMPACT_DELTA_RAW = 'delta_impact'
COL_IMPACT_GAMMA_RAW = 'gamma_impact'
COL_IMPACT_VEGA_RAW = 'vega_impact'
COL_IMPACT_THETA_RAW = 'theta_impact'
COL_IMPACT_VOLUME_RAW = 'volume_impact'
COL_IMPACT_VALUE_RAW = 'value_impact'
COL_IMPACT_COMPOSITE_RAW = 'composite_impact' # If used by impact_calculations
COL_IMPACT_SMI_RAW = 'smi' # Strike Magnetism Index (if calculated)
COL_IMPACT_VPI_RAW = 'vpi' # Volatility Pressure Index (if calculated)
COL_IMPACT_VPI_NORM = 'vpi_norm' # Normalized VPI (if calculated)
COL_IMPACT_PROXIMITY = 'proximity' # Calculated within impact_calculations (e.g., distance-based weighting)

# --- D. BASE METRIC MODULE OUTPUTS (Direct outputs from core_analytics.integrated_strategies_v2 - v2.3 style) ---
# These are the calculated metrics before final MSPI normalization and indexing.
# 1. Core Metrics (DAG, TDPI, VRI)
COL_DAG_CUSTOM_RAW = "dag_custom"  # Output of calculate_custom_flow_dag
COL_TDPI_RAW = "tdpi"              # Output of calculate_tdpi
COL_VRI_RAW = "vri"                # Output of calculate_vri

# 2. SDAG Methodologies (Outputs from integrated_strategies_v2, if enabled)
COL_SDAG_MULTIPLICATIVE_RAW = "sdag_multiplicative"
COL_SDAG_DIRECTIONAL_RAW = "sdag_directional"
COL_SDAG_WEIGHTED_RAW = "sdag_weighted"
COL_SDAG_VOLATILITY_FOCUSED_RAW = "sdag_volatility_focused"

# 3. Intermediate / Debugging Metrics (for transparency or specific calculations)
COL_DAG_FLOW_RATIO_DEBUG = "dag_flow_ratio_debug"
COL_NORM_NET_GAMMA_FLOW_DAG = "norm_net_gamma_flow" # Used in DAG
COL_BETA_TDPI = "beta" # Alignment factor in TDPI
COL_CHARM_FLOW_TO_OI_RATIO_TDPI = "charm_flow_to_charm_oi_ratio"
COL_NORM_NET_THETA_FLOW_TDPI = "norm_net_theta_flow" # Used in TDPI
COL_GAMMA_COEFF_VRI = "gamma_coeff_vri" # Alignment factor in VRI
COL_VANNA_FLOW_TO_OI_RATIO_VRI = "vanna_flow_to_vanna_oi_ratio"
COL_NORM_NET_VOMMA_FLOW_VRI = "norm_net_vomma_flow"
COL_SKEW_FACTOR_VRI = "skew_factor"
COL_VOL_TREND_FACTOR_VRI = "vol_trend_factor"
COL_NORM_VXOI_ABS_VRI = "norm_vxoi_abs"
COL_CTR = "ctr"         # Charm Decay Rate (from TDPI calculation)
COL_TDFI = "tdfi"       # Time Decay Flow Imbalance (from TDPI calculation)
COL_VVR = "vvr"         # Vanna-Vomma Ratio (from VRI calculation)
COL_VFI = "vfi"         # Volatility Flow Imbalance (from VRI calculation)

# 4. Normalized Core Metrics (Primary inputs to final MSPI calculation)
COL_DAG_CUSTOM_NORM = "dag_custom_norm"
COL_TDPI_NORM = "tdpi_norm"
COL_VRI_NORM = "vri_norm"
COL_SDAG_MULTIPLICATIVE_NORM = "sdag_multiplicative_norm"
COL_SDAG_DIRECTIONAL_NORM = "sdag_directional_norm"
COL_SDAG_WEIGHTED_NORM = "sdag_weighted_norm"
COL_SDAG_VOLATILITY_FOCUSED_NORM = "sdag_volatility_focused_norm"

# 5. Final Composite & Index Metrics (Outputs from integrated_strategies_v2)
COL_MSPI_SCORE = "mspi"         # Final MSPI score column (normalized -1 to +1)
COL_SAI = "sai"                 # Sentiment Alignment Indicator (normalized -1 to +1)
COL_SSI = "ssi"                 # Structural Stability Index (normalized 0 to +1)
COL_ARFI = "arfi"               # Average Relative Flow Index

# --- E. RENAMED CHART-READY COLUMNS (Target names for visualization after processor renaming) ---
# These align with what the visualizer expects and are often derived from raw impact columns.
COL_CHART_HEURISTIC_NET_DELTA_PRESSURE = 'heuristic_net_delta_pressure' # From IMPACT_DELTA_RAW
COL_CHART_NET_GAMMA_FLOW = 'net_gamma_flow'                             # From IMPACT_GAMMA_RAW
COL_CHART_NET_VEGA_FLOW = 'net_vega_flow'                               # From IMPACT_VEGA_RAW
COL_CHART_NET_THETA_EXPOSURE = 'net_theta_exposure'                     # From IMPACT_THETA_RAW
COL_CHART_NET_VOLUME_PRESSURE = 'net_volume_pressure'                   # From IMPACT_VOLUME_RAW
COL_CHART_NET_VALUE_PRESSURE = 'net_value_pressure'                     # From IMPACT_VALUE_RAW

# --- F. (Optional/Advanced) ADAPTIVE & V2.5 METRIC COLUMNS ---
# These are from your more advanced Integrated Trading System v2.5.
# Kept here for consistency if EDP might pass them through, even if not fully processed in v2.3 flow.
COL_A_DAG_OUTPUT = "a_dag"                      # Adaptive DAG raw output
COL_A_DAG_NORM = "a_dag_norm"                   # Normalized Adaptive DAG
COL_D_TDPI_OUTPUT = "d_tdpi"                    # Dynamic TDPI raw output
COL_D_TDPI_NORM = "d_tdpi_norm"                 # Normalized Dynamic TDPI
COL_ENHANCED_CTR = "enhanced_ctr"             # From D-TDPI module
COL_ENHANCED_TDFI = "enhanced_tdfi"            # From D-TDPI module
COL_VRI_2_0_OUTPUT = "vri_2_0"                  # VRI v2.0 raw output
COL_VRI_2_0_NORM = "vri_2_0_norm"               # Normalized VRI v2.0
COL_ENHANCED_VVR_SENS = "enhanced_vvr_sens"    # From VRI 2.0 module
COL_ENHANCED_VFI_SENS = "enhanced_vfi_sens"    # From VRI 2.0 module
COL_E_SDAG_COMPOSITE_OUTPUT = "e_sdag_composite" # Enhanced SDAG Composite raw output
COL_E_SDAG_COMPOSITE_NORM = "e_sdag_composite_norm" # Normalized Enhanced SDAG Composite
COL_E_SDAG_SKEW_ADJUSTED_GEX = "e_sdag_skew_adjusted_gex" # Intermediate in E-SDAG calculation
COL_SDAG_CONVICTION_SCORE = "sdag_conviction_score" # From E-SDAG or general SDAG module

# --- G. TRADIER FETCHER DERIVED COLUMNS (for consistency) ---
COL_TRADIER_IV_APPROX_PREFIX = "tradier_iv" # Prefix for Tradier's DTE-specific IV approximation (e.g., "tradier_iv5_approx_smv_avg")
# This was the missing one that caused AttributeError previously, added here:
CV_UND_PARAM_IV_PERCENTILE_30D = "iv_percentile_30d" # Example of a specific IV percentile key

# --- H. LEVEL IDENTIFICATION & SIGNAL GENERATION ---
COL_LEVEL_TYPE = "level_type"                         # 'support' or 'resistance'
COL_LEVEL_STRENGTH = "strength_score"                 # Numeric strength of the identified level

# ==============================================================================
# III. API PARAMETERS (Strings for external API calls, especially ConvexValue)
# ==============================================================================
# These match the exact parameter names expected by the external APIs.

# --- A. Parameters for ConvexApi.get_und() API call ---
CV_UND_PARAM_PRICE = "price"
CV_UND_PARAM_VOLATILITY = "volatility"
CV_UND_PARAM_DAY_VOLUME = "day_volume"
CV_UND_PARAM_CALL_GXOI = "call_gxoi"
CV_UND_PARAM_FETCH_TIMESTAMP = "fetch_timestamp"
CV_UND_PARAM_PUT_GXOI = "put_gxoi"
CV_UND_PARAM_GAMMAS_CALL_BUY = "gammas_call_buy"
CV_UND_PARAM_GAMMAS_CALL_SELL = "gammas_call_sell"
CV_UND_PARAM_GAMMAS_PUT_BUY = "gammas_put_buy"
CV_UND_PARAM_GAMMAS_PUT_SELL = "gammas_put_sell"
CV_UND_PARAM_DELTAS_CALL_BUY = "deltas_call_buy"
CV_UND_PARAM_DELTAS_CALL_SELL = "deltas_call_sell"
CV_UND_PARAM_DELTAS_PUT_BUY = "deltas_put_buy"
CV_UND_PARAM_DELTAS_PUT_SELL = "deltas_put_sell"
CV_UND_PARAM_VEGAS_CALL_BUY = "vegas_call_buy"
CV_UND_PARAM_VEGAS_CALL_SELL = "vegas_call_sell"
CV_UND_PARAM_VEGAS_PUT_BUY = "vegas_put_buy"
CV_UND_PARAM_VEGAS_PUT_SELL = "vegas_put_sell"
CV_UND_PARAM_THETAS_CALL_BUY = "thetas_call_buy"
CV_UND_PARAM_THETAS_CALL_SELL = "thetas_call_sell"
CV_UND_PARAM_THETAS_PUT_BUY = "thetas_put_buy"
CV_UND_PARAM_THETAS_PUT_SELL = "thetas_put_sell"
CV_UND_PARAM_CALL_VXOI = "call_vxoi"
CV_UND_PARAM_PUT_VXOI = "put_vxoi"
CV_UND_PARAM_VALUE_BS = "value_bs"
CV_UND_PARAM_VOLM_BS = "volm_bs"
CV_UND_PARAM_DELTAS_BUY = "deltas_buy"
CV_UND_PARAM_DELTAS_SELL = "deltas_sell"
CV_UND_PARAM_VEGAS_BUY = "vegas_buy"
CV_UND_PARAM_VEGAS_SELL = "vegas_sell"
CV_UND_PARAM_THETAS_BUY = "thetas_buy"
CV_UND_PARAM_THETAS_SELL = "thetas_sell"
CV_UND_PARAM_VOLM_CALL_BUY = "volm_call_buy"
CV_UND_PARAM_VOLM_PUT_BUY = "volm_put_buy"
CV_UND_PARAM_VOLM_CALL_SELL = "volm_call_sell"
CV_UND_PARAM_VOLM_PUT_SELL = "volm_put_sell"
CV_UND_PARAM_VALUE_CALL_BUY = "value_call_buy"
CV_UND_PARAM_VALUE_PUT_BUY = "value_put_buy"
CV_UND_PARAM_VALUE_CALL_SELL = "value_call_sell"
CV_UND_PARAM_VALUE_PUT_SELL = "value_put_sell"
CV_UND_PARAM_VFLOWRATIO = "vflowratio"
CV_UND_PARAM_DXOI = "dxoi"
CV_UND_PARAM_GXOI = "gxoi"
CV_UND_PARAM_VXOI = "vxoi"
CV_UND_PARAM_TXOI = "txoi"
CV_UND_PARAM_CALL_DXOI = "call_dxoi"
CV_UND_PARAM_PUT_DXOI = "put_dxoi"
CV_UND_PARAM_CHARMXOI = "charmxoi"
CV_UND_PARAM_VANNAXOI = "vannaxoi"
CV_UND_PARAM_VOMMAXOI = "vommaxoi"

# List of all default parameters for get_und() (used in fetcher_convexvalue_v2_5)
CV_UNDERLYING_DEFAULT_PARAMS_LIST = [
    CV_UND_PARAM_PRICE, CV_UND_PARAM_VOLATILITY, CV_UND_PARAM_DAY_VOLUME,
    CV_UND_PARAM_CALL_GXOI, CV_UND_PARAM_PUT_GXOI, CV_UND_PARAM_GAMMAS_CALL_BUY,
    CV_UND_PARAM_GAMMAS_CALL_SELL, CV_UND_PARAM_GAMMAS_PUT_BUY, CV_UND_PARAM_GAMMAS_PUT_SELL,
    CV_UND_PARAM_DELTAS_CALL_BUY, CV_UND_PARAM_DELTAS_CALL_SELL, CV_UND_PARAM_DELTAS_PUT_BUY,
    CV_UND_PARAM_DELTAS_PUT_SELL, CV_UND_PARAM_VEGAS_CALL_BUY, CV_UND_PARAM_VEGAS_CALL_SELL,
    CV_UND_PARAM_VEGAS_PUT_BUY, CV_UND_PARAM_VEGAS_PUT_SELL, CV_UND_PARAM_THETAS_CALL_BUY,
    CV_UND_PARAM_THETAS_CALL_SELL, CV_UND_PARAM_THETAS_PUT_BUY, CV_UND_PARAM_THETAS_PUT_SELL,
    CV_UND_PARAM_CALL_VXOI, CV_UND_PARAM_PUT_VXOI, CV_UND_PARAM_VALUE_BS,
    CV_UND_PARAM_VOLM_BS, CV_UND_PARAM_DELTAS_BUY, CV_UND_PARAM_DELTAS_SELL,
    CV_UND_PARAM_VEGAS_BUY, CV_UND_PARAM_VEGAS_SELL, CV_UND_PARAM_THETAS_BUY,
    CV_UND_PARAM_THETAS_SELL, CV_UND_PARAM_VOLM_CALL_BUY, CV_UND_PARAM_VOLM_PUT_BUY,
    CV_UND_PARAM_VOLM_CALL_SELL, CV_UND_PARAM_VOLM_PUT_SELL, CV_UND_PARAM_VALUE_CALL_BUY,
    CV_UND_PARAM_VALUE_PUT_BUY, CV_UND_PARAM_VALUE_CALL_SELL, CV_UND_PARAM_VALUE_PUT_SELL,
    CV_UND_PARAM_VFLOWRATIO, CV_UND_PARAM_DXOI, CV_UND_PARAM_GXOI,
    CV_UND_PARAM_VXOI, CV_UND_PARAM_TXOI, CV_UND_PARAM_CALL_DXOI,
    CV_UND_PARAM_PUT_DXOI, CV_UND_PARAM_CHARMXOI, CV_UND_PARAM_VANNAXOI,
    CV_UND_PARAM_VOMMAXOI
]

# --- B. Parameters for ConvexApi.get_chain_as_rows() API call ---
CV_CHAIN_PARAM_PRICE = "price"
CV_CHAIN_PARAM_VOLATILITY = "volatility"
CV_CHAIN_PARAM_MULTIPLIER = "multiplier"
CV_CHAIN_PARAM_OI = "oi"
CV_CHAIN_PARAM_DELTA = "delta"
CV_CHAIN_PARAM_GAMMA = "gamma"
CV_CHAIN_PARAM_THETA = "theta"
CV_CHAIN_PARAM_VEGA = "vega"
CV_CHAIN_PARAM_VANNA = "vanna"
CV_CHAIN_PARAM_VOMMA = "vomma"
CV_CHAIN_PARAM_CHARM = "charm"
CV_CHAIN_PARAM_DXOI_CONTRACT = "dxoi"
CV_CHAIN_PARAM_GXOI_CONTRACT = "gxoi"
CV_CHAIN_PARAM_VXOI_CONTRACT = "vxoi"
CV_CHAIN_PARAM_TXOI_CONTRACT = "txoi"
CV_CHAIN_PARAM_VANNAXOI_CONTRACT = "vannaxoi"
CV_CHAIN_PARAM_VOMMAXOI_CONTRACT = "vommaxoi"
CV_CHAIN_PARAM_CHARMXOI_CONTRACT = "charmxoi"
CV_CHAIN_PARAM_DXVOLM = "dxvolm"
CV_CHAIN_PARAM_GXVOLM = "gxvolm"
CV_CHAIN_PARAM_VXVOLM = "vxvolm"
CV_CHAIN_PARAM_TXVOLM = "txvolm" # <--- ADDED THIS MISSING CONSTANT
CV_CHAIN_PARAM_VANNAXVOLM = "vannaxvolm"
CV_CHAIN_PARAM_VOMMAXVOLM = "vommaxvolm"
CV_CHAIN_PARAM_CHARMXVOLM = "charmxvolm"
CV_CHAIN_PARAM_VALUE_BS_CONTRACT = "value_bs"
CV_CHAIN_PARAM_VOLM_BS_CONTRACT = "volm_bs"
CV_CHAIN_PARAM_DELTAS_BUY_CONTRACT = "deltas_buy"
CV_CHAIN_PARAM_DELTAS_SELL_CONTRACT = "deltas_sell"
CV_CHAIN_PARAM_GAMMAS_BUY_CONTRACT = "gammas_buy"
CV_CHAIN_PARAM_GAMMAS_SELL_CONTRACT = "gammas_sell"
CV_CHAIN_PARAM_VEGAS_BUY_CONTRACT = "vegas_buy"
CV_CHAIN_PARAM_VEGAS_SELL_CONTRACT = "vegas_sell"
CV_CHAIN_PARAM_THETAS_BUY_CONTRACT = "thetas_buy"
CV_CHAIN_PARAM_THETAS_SELL_CONTRACT = "thetas_sell"
CV_CHAIN_PARAM_VALUEBS_5M = "valuebs_5m"
CV_CHAIN_PARAM_VOLMBS_5M = "volmbs_5m"
CV_CHAIN_PARAM_VALUEBS_15M = "valuebs_15m"
CV_CHAIN_PARAM_VOLMBS_15M = "volmbs_15m"
CV_CHAIN_PARAM_VALUEBS_30M = "valuebs_30m"
CV_CHAIN_PARAM_VOLMBS_30M = "volmbs_30m"
CV_CHAIN_PARAM_VALUEBS_60M = "valuebs_60m"
CV_CHAIN_PARAM_VOLMBS_60M = "volmbs_60m"
CV_CHAIN_PARAM_VOLM_CONTRACT = "volm"
CV_CHAIN_PARAM_VOLM_BUY_C = "volm_buy"
CV_CHAIN_PARAM_VOLM_SELL_C = "volm_sell"
CV_CHAIN_PARAM_VALUE_BUY_C = "value_buy"
CV_CHAIN_PARAM_VALUE_SELL_C = "value_sell"
CV_CHAIN_PARAM_BID_PRICE = "bid_price"
CV_CHAIN_PARAM_ASK_PRICE = "ask_price"
CV_CHAIN_PARAM_BID_SIZE = "bid_size"
CV_CHAIN_PARAM_ASK_SIZE = "ask_size"

# List of all default parameters for get_chain_as_rows() (used in fetcher_convexvalue_v2_5)
CV_OPTIONS_CHAIN_DEFAULT_PARAMS_LIST = [
    CV_CHAIN_PARAM_PRICE, CV_CHAIN_PARAM_VOLATILITY, CV_CHAIN_PARAM_MULTIPLIER, CV_CHAIN_PARAM_OI,
    CV_CHAIN_PARAM_DELTA, CV_CHAIN_PARAM_GAMMA, CV_CHAIN_PARAM_THETA, CV_CHAIN_PARAM_VEGA,
    CV_CHAIN_PARAM_VANNA, CV_CHAIN_PARAM_VOMMA, CV_CHAIN_PARAM_CHARM,
    CV_CHAIN_PARAM_DXOI_CONTRACT, CV_CHAIN_PARAM_GXOI_CONTRACT, CV_CHAIN_PARAM_VXOI_CONTRACT, CV_CHAIN_PARAM_TXOI_CONTRACT,
    CV_CHAIN_PARAM_VANNAXOI_CONTRACT, CV_CHAIN_PARAM_VOMMAXOI_CONTRACT, CV_CHAIN_PARAM_CHARMXOI_CONTRACT,
    CV_CHAIN_PARAM_DXVOLM, CV_CHAIN_PARAM_GXVOLM, CV_CHAIN_PARAM_VXVOLM, CV_CHAIN_PARAM_TXVOLM,
    CV_CHAIN_PARAM_VANNAXVOLM, CV_CHAIN_PARAM_VOMMAXVOLM, CV_CHAIN_PARAM_CHARMXVOLM,
    CV_CHAIN_PARAM_VALUE_BS_CONTRACT, CV_CHAIN_PARAM_VOLM_BS_CONTRACT,
    CV_CHAIN_PARAM_DELTAS_BUY_CONTRACT, CV_CHAIN_PARAM_DELTAS_SELL_CONTRACT,
    CV_CHAIN_PARAM_GAMMAS_BUY_CONTRACT, CV_CHAIN_PARAM_GAMMAS_SELL_CONTRACT,
    CV_CHAIN_PARAM_VEGAS_BUY_CONTRACT, CV_CHAIN_PARAM_VEGAS_SELL_CONTRACT,
    CV_CHAIN_PARAM_THETAS_BUY_CONTRACT, CV_CHAIN_PARAM_THETAS_SELL_CONTRACT,
    CV_CHAIN_PARAM_VALUEBS_5M, CV_CHAIN_PARAM_VOLMBS_5M,
    CV_CHAIN_PARAM_VALUEBS_15M, CV_CHAIN_PARAM_VOLMBS_15M,
    CV_CHAIN_PARAM_VALUEBS_30M, CV_CHAIN_PARAM_VOLMBS_30M,
    CV_CHAIN_PARAM_VALUEBS_60M, CV_CHAIN_PARAM_VOLMBS_60M,
    CV_CHAIN_PARAM_VOLM_CONTRACT, CV_CHAIN_PARAM_VOLM_BUY_C, CV_CHAIN_PARAM_VOLM_SELL_C,
    CV_CHAIN_PARAM_VALUE_BUY_C, CV_CHAIN_PARAM_VALUE_SELL_C,
    CV_CHAIN_PARAM_BID_PRICE, CV_CHAIN_PARAM_ASK_PRICE,
    CV_CHAIN_PARAM_BID_SIZE, CV_CHAIN_PARAM_ASK_SIZE
]

# --- C. Numeric Column Lists (for type conversion assistance, from fetcher_convexvalue_v2_5.py) ---
CV_NUMERIC_COLUMNS_OPTIONS_LIST = [ # Renamed for clarity
    'strike', 'price', 'volatility', 'multiplier', 'oi', 'delta', 'gamma', 'theta', 'vega',
    'vanna', 'vomma', 'charm', 'dxoi', 'gxoi', 'vxoi', 'txoi', 'vannaxoi', 'vommaxoi',
    'charmxoi', 'dxvolm', 'gxvolm', 'vxvolm', 'txvolm',
    'vannaxvolm', 'vommaxvolm', 'charmxvolm',
    'value_bs', 'volm_bs', 'deltas_buy', 'deltas_sell',
    'gammas_buy', 'gammas_sell', 'vegas_buy', 'vegas_sell', 'thetas_buy', 'thetas_sell',
    'valuebs_5m', 'volmbs_5m', 'valuebs_15m', 'volmbs_15m',
    'valuebs_30m', 'volmbs_30m', 'valuebs_60m', 'volmbs_60m',
    'volm', 'volm_buy', 'volm_sell', 'value_buy', 'value_sell',
    'bid_price', 'ask_price', 'bid_size', 'ask_size'
]

CV_NUMERIC_COLUMNS_UNDERLYING_LIST = [ # Renamed for clarity
    param for param in CV_UNDERLYING_DEFAULT_PARAMS_LIST if param not in ['symbol']
]


# ==============================================================================
# IV. CONFIGURATION KEYS (Strings used to access nested values in config_v2.json)
# ==============================================================================
# This section defines common paths to access configuration settings from the loaded APP_CONFIG.

# --- Internal Config Keys (for reference to how config is managed) ---
DEFAULT_CONFIG_FILE_PATH = "config_v2.json" # The default filename expected for the main config
CFG_CONFIG_FILE_PATH_CACHED_AT = "_config_file_path_cached_at" # Key used internally by ConfigManager to store path
CFG_CONFIG_FILE_PATH = "_config_file_path" # Another internal key ConfigManager might use

# --- System Settings (under "system_settings" in config_v2.json) ---
CFG_SYSTEM_SETTINGS = ["system_settings"]
CFG_SYSTEM_LOG_LEVEL = CFG_SYSTEM_SETTINGS + ["log_level"]
CFG_SYSTEM_LOG_LEVELS_GRANULAR = CFG_SYSTEM_SETTINGS + ["log_levels_granular"]
CFG_SYSTEM_DASHBOARD_DEBUG_MODE = CFG_SYSTEM_SETTINGS + ["dashboard_debug_mode"] # Assumed path for dash debug mode
CFG_SYSTEM_DASHBOARD_HOST = CFG_SYSTEM_SETTINGS + ["dashboard_host"] # Assumed path
CFG_SYSTEM_DASHBOARD_PORT = CFG_SYSTEM_SETTINGS + ["dashboard_port"] # Assumed path
CFG_SYSTEM_DASHBOARD_CACHE_TIMEOUT_SECONDS = CFG_SYSTEM_SETTINGS + ["dashboard_cache_timeout_seconds"]
CFG_SYSTEM_DATA_DIRECTORY_BASE = CFG_SYSTEM_SETTINGS + ["data_directory_base"]
CFG_SYSTEM_PROCESSED_DATA_SUBDIRECTORY = CFG_SYSTEM_SETTINGS + ["processed_data_subdirectory"]
CFG_SYSTEM_THREAD_POOL_SIZE = CFG_SYSTEM_SETTINGS + ["thread_pool_size"]
CFG_SYSTEM_DF_HISTORY_MAXLEN_ITS = CFG_SYSTEM_SETTINGS + ["df_history_maxlen_its"] # Maxlen for historical DataFrame deques


# --- API Credentials (under "api_credentials" in config_v2.json) ---
CFG_API_CREDS_ROOT = ["api_credentials"]
CFG_API_CREDS_CONVEXVALUE = CFG_API_CREDS_ROOT + ["convexvalue"]
CFG_API_CREDS_TRADIER = CFG_API_CREDS_ROOT + ["tradier"]

# --- Data Fetcher Settings (under "data_fetcher_settings" in config_v2.json) ---
CFG_DATA_FETCHER_SETTINGS_ROOT = ["data_fetcher_settings"]
CFG_CV_FETCHER = CFG_DATA_FETCHER_SETTINGS_ROOT + ["convexvalue_fetcher_v2_5"]
CFG_CV_UND_PARAMS_TO_FETCH = CFG_CV_FETCHER + ["underlying_params_to_fetch"]
CFG_CV_OPT_PARAMS_TO_FETCH = CFG_CV_FETCHER + ["options_chain_params_to_fetch"]
CFG_TRADIER_FETCHER = CFG_DATA_FETCHER_SETTINGS_ROOT + ["tradier_fetcher_v2_5"]
CFG_TRADIER_OHLCV_NUM_DAYS_HISTORY_DEFAULT = CFG_TRADIER_FETCHER + ["ohlcv_num_days_history_default"]
CFG_TRADIER_IV_APPROX_TARGET_DTE_DEFAULT = CFG_TRADIER_FETCHER + ["iv_approx_target_dte_default"]

# --- Initial Processor Settings (under "initial_processor_v2_5_settings" in config_v2.json) ---
CFG_INIT_PROC_SETTINGS = ["initial_processor_v2_5_settings"]
CFG_CALC_BASE_NET_GREEK_FLOWS = CFG_INIT_PROC_SETTINGS + ["calculate_base_net_greek_flows_from_chain"]
CFG_CALC_HEURISTIC_PRESSURES = CFG_INIT_PROC_SETTINGS + ["calculate_heuristic_pressures_from_chain"]

# --- Metrics Calculator Settings (under "metrics_calculator_v2_5_settings" in config_v2.json) ---
# These are the config keys ITS expects for its internal metric calculations.
CFG_METRICS_CALC = ["metrics_calculator_v2_5_settings"] # Root for metric calculator settings
CFG_METRICS_CALC_STRIKE_COL_INTERNAL = CFG_METRICS_CALC + ["strike_column_name_internal"]
CFG_METRICS_CALC_GAMMA_COL_KEY = CFG_METRICS_CALC + ["gamma_exposure_source_col_config_key"]
CFG_METRICS_CALC_DELTA_COL_KEY = CFG_METRICS_CALC + ["delta_exposure_source_col_config_key"]
CFG_METRICS_CALC_OPT_IV_COL_KEY = CFG_METRICS_CALC + ["option_iv_source_col_config_key"]
CFG_METRICS_CALC_OPT_PRICE_COL_KEY = CFG_METRICS_CALC + ["option_price_source_col_config_key"]
CFG_METRICS_CALC_UND_PRICE_KEY = CFG_METRICS_CALC + ["underlying_price_source_key_in_und_data"]
CFG_METRICS_CALC_CHARM_COL_KEY = CFG_METRICS_CALC + ["charm_exposure_source_col_config_key"]
CFG_METRICS_CALC_THETA_COL_KEY = CFG_METRICS_CALC + ["theta_exposure_source_col_config_key"]
CFG_METRICS_CALC_VANNA_COL_KEY = CFG_METRICS_CALC + ["vanna_exposure_source_col_config_key"]
CFG_METRICS_CALC_VEGA_COL_KEY = CFG_METRICS_CALC + ["vega_exposure_source_col_config_key"]
CFG_METRICS_CALC_VOMMA_COL_KEY = CFG_METRICS_CALC + ["vomma_exposure_source_col_config_key"]
CFG_METRICS_CALC_VOLM_COL_KEY = CFG_METRICS_CALC + ["volume_source_col_config_key"]
CFG_METRICS_CALC_ADAPTIVE_ADAG_SETTINGS = CFG_METRICS_CALC + ["adaptive_metric_params", "a_dag_settings"]
CFG_METRICS_CALC_ADAPTIVE_ADAG_BASE_ALPHA = CFG_METRICS_CALC_ADAPTIVE_ADAG_SETTINGS + ["base_dag_alpha_coeffs"]
CFG_METRICS_CALC_ADAPTIVE_ADAG_DTE_SCALING = CFG_METRICS_CALC_ADAPTIVE_ADAG_SETTINGS + ["dte_gamma_flow_impact_scaling"]
CFG_METRICS_CALC_ADAPTIVE_DTDPI_SETTINGS = CFG_METRICS_CALC + ["adaptive_metric_params", "d_tdpi_settings"]
CFG_METRICS_CALC_ADAPTIVE_DTDPI_BASE_BETA = CFG_METRICS_CALC_ADAPTIVE_DTDPI_SETTINGS + ["base_tdpi_beta_coeffs"]
CFG_METRICS_CALC_ADAPTIVE_DTDPI_BASE_GAUSS = CFG_METRICS_CALC_ADAPTIVE_DTDPI_SETTINGS + ["base_tdpi_gaussian_width"]
CFG_METRICS_CALC_ADAPTIVE_VRI2_SETTINGS = CFG_METRICS_CALC + ["adaptive_metric_params", "vri_2_0_settings"]
CFG_METRICS_CALC_ADAPTIVE_VRI2_BASE_GAMMA = CFG_METRICS_CALC_ADAPTIVE_VRI2_SETTINGS + ["base_vri_gamma_coeffs"]
CFG_METRICS_CALC_VRI_VOL_TREND_FALLBACK = CFG_METRICS_CALC_ADAPTIVE_VRI2_SETTINGS + ["vol_trend_fallback_factor"]
CFG_METRICS_CALC_ADAPTIVE_ESDAG_SETTINGS = CFG_METRICS_CALC + ["adaptive_metric_params", "e_sdag_settings"]
CFG_METRICS_CALC_ATR_FALLBACK = CFG_METRICS_CALC + ["atr_calculation_params", "fallback_settings"]


# --- ITS Settings (for mspi_orchestration_module and integrated_strategies_v2) ---
CFG_DATA_PROCESSOR_SETTINGS_BASE_KEY = ["data_processor_settings"]
CFG_WEIGHTS_KEY = "weights"
CFG_WEIGHTS_SELECTION_LOGIC_KEY = "selection_logic"
CFG_WEIGHTS_TIME_BASED_DEFS_KEY = "time_based_definitions"
CFG_WEIGHTS_MORNING_END_KEY = "morning_end"
CFG_WEIGHTS_MIDDAY_END_KEY = "midday_end"
CFG_WEIGHTS_SESSION_FINAL_KEY = "final"
CFG_WEIGHTS_SESSION_MIDDAY_KEY = "midday"
CFG_WEIGHTS_SESSION_MORNING_KEY = "morning"
CFG_WEIGHTS_TIME_BASED_KEY = "time_based"

# --- Strategy Settings (under "strategy_settings" in config_v2.json) ---
CFG_STRATEGY_SETTINGS = ["strategy_settings"]
CFG_DAG_METHODOLOGIES_ITS = CFG_STRATEGY_SETTINGS + ["dag_methodologies"]
CFG_DAG_METHODOLOGIES_ENABLED_ITS = CFG_DAG_METHODOLOGIES_ITS + ["enabled"]
# Add thresholds, signals, etc. from strategy_settings here if accessed via config.
CFG_ENHANCED_METRICS = ["enhanced_metrics"]
CFG_ENHANCED_METRICS_ESDAG_CONVICTION_COL = CFG_ENHANCED_METRICS + ["e_sdag", "conviction_score_output_col_name"]


# --- Visualization Settings (under "visualization_settings" in config_v2.json) ---
CFG_VISUALIZATION_SETTINGS_ROOT = ["visualization_settings"]

# Dashboard specific settings
CFG_DASHBOARD = CFG_VISUALIZATION_SETTINGS_ROOT + ["dashboard"]
CFG_DASHBOARD_DEFAULTS = CFG_DASHBOARD + ["defaults"]
CFG_DASHBOARD_DEFAULT_SYMBOL = CFG_DASHBOARD_DEFAULTS + ["symbol"]
CFG_DASHBOARD_DEFAULT_DTE = CFG_DASHBOARD_DEFAULTS + ["dte"]
CFG_DASHBOARD_DEFAULT_RANGE_PCT = CFG_DASHBOARD_DEFAULTS + ["range_pct"]
CFG_DASHBOARD_DEFAULT_REFRESH_MS = CFG_DASHBOARD_DEFAULTS + ["refresh_interval_ms"]
CFG_DASHBOARD_RANGE_SLIDER_MARKS = CFG_DASHBOARD + ["range_slider_marks"]
CFG_DASHBOARD_REFRESH_OPTIONS = CFG_DASHBOARD + ["refresh_options"]
CFG_DASHBOARD_TITLE = CFG_DASHBOARD + ["title"]
CFG_DASHBOARD_FOOTER_TEXT = CFG_DASHBOARD + ["footer_text"]
CFG_DASHBOARD_DEFAULT_GRAPH_HEIGHT = CFG_DASHBOARD + ["default_graph_height"]
DASHBOARD_ASSETS_FOLDER_NAME = "assets" # Folder name for Dash assets within dashboard_v2/

# MSPI Visualizer specific settings
CFG_VIZ_MSPI_VISUALIZER = CFG_VISUALIZATION_SETTINGS_ROOT + ["mspi_visualizer"]
CFG_VIZ_COL_NAMES = CFG_VIZ_MSPI_VISUALIZER + ["column_names"] # Root for column name mappings in visualizer
CFG_VIZ_COL_STRIKE = CFG_VIZ_COL_NAMES + ["strike"]
CFG_VIZ_COL_OPT_KIND = CFG_VIZ_COL_NAMES + ["option_kind"] # was option_type
CFG_VIZ_COL_MSPI = CFG_VIZ_COL_NAMES + ["mspi"] # Changed from mspi_score to mspi to match provided config
CFG_VIZ_COL_NET_VOL_PRESSURE = CFG_VIZ_COL_NAMES + ["net_volume_pressure"]
CFG_VIZ_COL_NET_VAL_PRESSURE = CFG_VIZ_COL_NAMES + ["net_value_pressure"]
CFG_VIZ_COL_HEURISTIC_NET_DELTA_PRESSURE = CFG_VIZ_COL_NAMES + ["heuristic_net_delta_pressure"]
CFG_VIZ_COL_NET_GAMMA_FLOW = CFG_VIZ_COL_NAMES + ["net_gamma_flow_at_strike"]
CFG_VIZ_COL_NET_VEGA_FLOW = CFG_VIZ_COL_NAMES + ["net_vega_flow_at_strike"]
CFG_VIZ_COL_NET_THETA_EXPOSURE = CFG_VIZ_COL_NAMES + ["net_theta_exposure_at_strike"]
CFG_VIZ_COL_EXPIRY_DATE = CFG_VIZ_COL_NAMES + ["expiration_date"] # Corrected to expiration_date as used in mspi_visualizer_v2
CFG_VIZ_COL_UNDERLYING_SYMBOL = CFG_VIZ_COL_NAMES + ["underlying_symbol"] # Added

CFG_VIZ_MSPI_HEATMAP_VIEW_OPTIONS = CFG_VIZ_MSPI_VISUALIZER + ["mspi_heatmap_view_options"] # Path for heatmap view selector options
CFG_VIZ_MSPI_HEATMAP_DEFAULT_VIEW = CFG_VIZ_MSPI_VISUALIZER + ["mspi_heatmap_default_view"] # Path for heatmap default view
CFG_VIZ_GREEK_FLOW_HEATMAP_OPTIONS = CFG_VIZ_MSPI_VISUALIZER + ["greek_flow_heatmap_options"]
CFG_VIZ_GREEK_FLOW_HEATMAP_DEFAULT_METRIC = CFG_VIZ_MSPI_VISUALIZER + ["greek_flow_heatmap_default_metric"]
CFG_VIZ_ROLLING_FLOW_CHART_OPTIONS = CFG_VIZ_MSPI_VISUALIZER + ["rolling_flow_chart_options"]
CFG_VIZ_ROLLING_FLOW_CHART_DEFAULT_OPTION = CFG_VIZ_MSPI_VISUALIZER + ["rolling_flow_chart_default_option"]

CFG_DASHBOARD_STYLES = CFG_DASHBOARD + ["styles"]
CFG_DASHBOARD_STYLES_STATUS_DISPLAY_BASE = CFG_DASHBOARD_STYLES + ["status_display", "base"]
CFG_DASHBOARD_STYLES_STATUS_DISPLAY_ERROR = CFG_DASHBOARD_STYLES + ["status_display", "error"]
CFG_DASHBOARD_STYLES_STATUS_DISPLAY_SUCCESS = CFG_DASHBOARD_STYLES + ["status_display", "success"]
CFG_DASHBOARD_STYLES_STATUS_DISPLAY_INFO = CFG_DASHBOARD_STYLES + ["status_display", "info"]

# Market Regime Engine Settings
CFG_MARKET_REGIME_ENGINE_SETTINGS = ["market_regime_engine_settings"]
CFG_MARKET_REGIME_TIME_DEFS = CFG_MARKET_REGIME_ENGINE_SETTINGS + ["time_of_day_definitions"]