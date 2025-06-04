import os
import json
import logging
from datetime import datetime, date, time # Keep for type hints
import time as pytime # Alias to avoid conflict with datetime.time
from typing import Optional, Dict, Any, List, Tuple, Union, Deque, Callable # Keep for type hints

import numpy as np
import pandas as pd

# Import the class to be tested
from mspi_visualizer_v2 import MSPIVisualizerV2
# Import visualizer_config for the _get_config_value call in the test script
import visualizer_config


# --- Logging Setup for the test script ---
if not logging.getLogger().hasHandlers() or not any(isinstance(h, logging.StreamHandler) for h in logging.getLogger().handlers):
    logging.basicConfig(
        level=logging.DEBUG, # Use DEBUG for detailed test output
        format='[%(levelname)s] (%(module)s-%(funcName)s:%(lineno)d) %(asctime)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
# Explicitly named logger for the test script
test_logger = logging.getLogger("test_mspi_visualizer")
test_logger.setLevel(logging.DEBUG)


# --- E. Standalone Test Block (copied from mspi_visualizer_v2.py) ---
if __name__ == '__main__':
    test_logger.info("--- MSPIVisualizerV2 Test Run (VAPI-FA Multi-Interval Focus) --- ")

    test_config_path = "config_v2.json" 
    main_app_config_for_test = {}
    abs_test_config_path = test_config_path
    if not os.path.isabs(test_config_path):
        try: script_dir_test_viz = os.path.dirname(os.path.abspath(__file__))
        except NameError: script_dir_test_viz = os.getcwd() # Fallback if __file__ not defined (e.g. interactive)
        abs_test_config_path = os.path.join(script_dir_test_viz, test_config_path)

    try:
        if os.path.exists(abs_test_config_path):
            with open(abs_test_config_path, 'r') as f_cfg_viz_test:
                main_app_config_for_test = json.load(f_cfg_viz_test)
            test_logger.info(f"Loaded main application config for visualizer test run from {abs_test_config_path}")
        else:
            test_logger.warning(f"Main config file '{abs_test_config_path}' not found. Visualizer will use its internal defaults and then config settings from this test block.")
    except Exception as e_cfg_load_test:
        test_logger.error(f"Could not load '{abs_test_config_path}': {e_cfg_load_test}. Visualizer will use its defaults.")

    visualizer_test_instance = MSPIVisualizerV2(config_data=main_app_config_for_test)
    if visualizer_test_instance.instance_logger:
        visualizer_test_instance.instance_logger.setLevel(logging.DEBUG)
        for handler in visualizer_test_instance.instance_logger.handlers: 
             handler.setLevel(logging.DEBUG)
    test_logger.info("MSPIVisualizerV2 instance created for testing.")

    test_logger.info("--- Creating Sample Processed Data for Visualizer Tests (with VAPI-FA data) ---")
    test_symbol_viz = 'SPY_VAPITEST' 
    current_underlying_price_viz = 500.0 
    fetch_timestamp_viz = datetime.now().isoformat()
    
    sample_strikes_viz_flow = np.arange(current_underlying_price_viz - 15, current_underlying_price_viz + 16, 2.5).astype(float)
    per_contract_data_list_viz = []
    
    col_strike_test = visualizer_test_instance.col_strike
    col_opt_kind_test = visualizer_test_instance.col_opt_kind
    col_mspi_test = visualizer_test_instance.col_mspi
    col_expiry_date_test = visualizer_test_instance.config.get("column_names",{}).get("expiry_date", "expiry_date")
    
    for strike_val_viz in sample_strikes_viz_flow:
        for opt_type_viz in ['call', 'put']:
            flow_intensity_factor = np.exp(-0.05 * abs(strike_val_viz - current_underlying_price_viz))
            contract_data = {
                col_strike_test: strike_val_viz, 
                col_opt_kind_test: opt_type_viz, 
                'symbol': f".{test_symbol_viz}...", 
                'underlying_symbol': test_symbol_viz, 
                'price': current_underlying_price_viz, 
                col_mspi_test: np.random.uniform(-0.5, 0.5) * flow_intensity_factor,
                'fetch_timestamp': fetch_timestamp_viz,
                'volmbs_5m': np.random.randint(-150, 150) * flow_intensity_factor,
                'valuebs_5m': np.random.randint(-15000, 15000) * flow_intensity_factor,
                'volmbs_15m': np.random.randint(-100, 100) * flow_intensity_factor,
                'valuebs_15m': np.random.randint(-10000, 10000) * flow_intensity_factor,
                'volmbs_30m': np.random.randint(-80, 80) * flow_intensity_factor,
                'valuebs_30m': np.random.randint(-8000, 8000) * flow_intensity_factor,
                'volmbs_60m': np.random.randint(-60, 60) * flow_intensity_factor,
                'valuebs_60m': np.random.randint(-6000, 6000) * flow_intensity_factor,
                'sai': np.random.uniform(0,1), 'ssi': np.random.uniform(-1,1), 'cfi': np.random.uniform(-0.5,0.5),
                'tdpi_score_norm':  np.random.uniform(-1,1) * flow_intensity_factor,
                'vri_score_norm': np.random.uniform(-1,1) * flow_intensity_factor,
                'sdag_multiplicative_norm': np.random.uniform(-1,1) * flow_intensity_factor,
                'sdag_directional_norm': np.random.uniform(-1,1) * flow_intensity_factor,
                'sdag_weighted_norm': np.random.uniform(-1,1) * flow_intensity_factor,
                'sdag_volatility_focused_norm': np.random.uniform(-1,1) * flow_intensity_factor,
                visualizer_test_instance.col_net_gamma_flow: np.random.uniform(-100,100) * flow_intensity_factor,
                col_expiry_date_test: (datetime.now() + pd.Timedelta(days=np.random.choice([7,14,30]))).strftime('%Y-%m-%d')
            }
            per_contract_data_list_viz.append(contract_data)
    
    sample_processed_data_df_viz = pd.DataFrame(per_contract_data_list_viz)
    
    if col_expiry_date_test not in sample_processed_data_df_viz.columns:
        sample_processed_data_df_viz[col_expiry_date_test] = (datetime.now() + pd.Timedelta(days=30)).strftime('%Y-%m-%d')

    test_logger.info("--- Simulating VAPI-FA calculation on sample data ---")
    mock_current_iv_for_test = 0.18 
    small_constant_pvr_test = 1e-6

    intervals_to_sim = {
        "5m": {"pvr_inputs": ["valuebs_5m", "volmbs_5m"], "fa_inputs": ["volmbs_5m", "volmbs_15m"]},
        "15m": {"pvr_inputs": ["valuebs_15m", "volmbs_15m"], "fa_inputs": ["volmbs_15m", "volmbs_30m"]},
        "30m": {"pvr_inputs": ["valuebs_30m", "volmbs_30m"], "fa_inputs": ["volmbs_30m", "volmbs_60m"]},
        "60m": {"pvr_inputs": ["valuebs_60m", "volmbs_60m"], "fa_inputs": []} 
    }

    for interval, specs in intervals_to_sim.items():
        pvr_col = f"pvr_{interval}_debug" 
        fa_col = f"fa_{interval}_debug"   
        vapi_fa_col = f"vapi_fa_{interval}" 

        pvr_val_col_name, pvr_vol_col_name = specs["pvr_inputs"]
        if pvr_val_col_name in sample_processed_data_df_viz.columns and pvr_vol_col_name in sample_processed_data_df_viz.columns:
            valbs_s = pd.to_numeric(sample_processed_data_df_viz[pvr_val_col_name], errors='coerce').fillna(0.0)
            volmbs_s = pd.to_numeric(sample_processed_data_df_viz[pvr_vol_col_name], errors='coerce').fillna(0.0)
            pvr_s_num = valbs_s
            pvr_s_den = volmbs_s.abs() + small_constant_pvr_test
            pvr_s_uns = pvr_s_num / pvr_s_den
            sample_processed_data_df_viz[pvr_col] = (pvr_s_uns * np.sign(volmbs_s.replace(0, 1e-9))).fillna(0.0)
        else:
            sample_processed_data_df_viz[pvr_col] = 0.0
            test_logger.warning(f"  Missing inputs for PVR {interval} in sample data. Setting {pvr_col} to 0.")

        if specs["fa_inputs"]:
            fa_curr_col_name, fa_next_col_name = specs["fa_inputs"]
            if fa_curr_col_name in sample_processed_data_df_viz.columns and fa_next_col_name in sample_processed_data_df_viz.columns:
                volmbs_c_s = pd.to_numeric(sample_processed_data_df_viz[fa_curr_col_name], errors='coerce').fillna(0.0)
                volmbs_n_s = pd.to_numeric(sample_processed_data_df_viz[fa_next_col_name], errors='coerce').fillna(0.0)
                sample_processed_data_df_viz[fa_col] = (1.5 * volmbs_c_s - 0.5 * volmbs_n_s).fillna(0.0)
            else:
                sample_processed_data_df_viz[fa_col] = 0.0
                test_logger.warning(f"  Missing inputs for FA {interval} in sample data. Setting {fa_col} to 0.")
        else: 
            if not specs["fa_inputs"] and f"volmbs_{interval}" in sample_processed_data_df_viz.columns:
                 sample_processed_data_df_viz[fa_col] = sample_processed_data_df_viz[f"volmbs_{interval}"].fillna(0.0)
            else:
                 sample_processed_data_df_viz[fa_col] = 0.0 

        if pvr_col in sample_processed_data_df_viz.columns and fa_col in sample_processed_data_df_viz.columns:
            sample_processed_data_df_viz[vapi_fa_col] = (sample_processed_data_df_viz[pvr_col] * mock_current_iv_for_test) * sample_processed_data_df_viz[fa_col]
            sample_processed_data_df_viz[vapi_fa_col] = sample_processed_data_df_viz[vapi_fa_col].fillna(0.0)
            test_logger.info(f"  Simulated '{vapi_fa_col}' column added. Mean: {sample_processed_data_df_viz[vapi_fa_col].mean():.2f}")
        else:
            sample_processed_data_df_viz[vapi_fa_col] = 0.0
            test_logger.warning(f"  Missing PVR/FA debug columns for VAPI-FA {interval} in sample data. Setting {vapi_fa_col} to 0.")
        
    test_logger.info(f"Sample Processed DataFrame with VAPI-FA simulation. Shape: {sample_processed_data_df_viz.shape}")
    test_logger.debug(f"Columns in sample_processed_data_df_viz: {sample_processed_data_df_viz.columns.tolist()}")

    test_logger.info(f"\n--- Testing Combined Rolling Flow Chart ---")
    
    test_logger.info("  Testing with VAPI-FA (bar) vs ValueBS (area) - default intervals from config")
    fig_vapi_vs_value = visualizer_test_instance.create_combined_rolling_flow_chart(
        processed_data=sample_processed_data_df_viz, 
        symbol=test_symbol_viz, 
        current_price=current_underlying_price_viz, 
        fetch_timestamp=fetch_timestamp_viz,
        bar_metric_prefix="vapi_fa", 
        area_metric_prefix="valuebs",
        selected_price_range_pct_override=10.0 
    )
    if fig_vapi_vs_value and fig_vapi_vs_value.data: 
        test_logger.info("    Combined Rolling Flow chart (VAPI-FA vs ValueBS) generated successfully.")
    else: 
        test_logger.error("    Combined Rolling Flow chart (VAPI-FA vs ValueBS) generation FAILED or returned no data.")

    test_logger.info("  Testing with VAPI-FA (bar) vs ValueBS (area) - focused on 5m, 15m intervals")
    # Use visualizer_config._get_config_value for accessing config from the test script context
    # This requires passing the visualizer's full_app_config and specific_config
    original_intervals = visualizer_config._get_config_value(
        visualizer_test_instance.instance_logger, # pass a logger
        visualizer_test_instance.full_app_config, # full config
        visualizer_test_instance.config,          # specific viz config
        "rolling_intervals",                      # key
        ["5m", "15m", "30m", "60m"]               # default
    )
    visualizer_test_instance.config["rolling_intervals"] = ["5m", "15m"] 
    
    fig_vapi_vs_value_focused = visualizer_test_instance.create_combined_rolling_flow_chart(
        processed_data=sample_processed_data_df_viz, 
        symbol=test_symbol_viz, 
        current_price=current_underlying_price_viz, 
        fetch_timestamp=fetch_timestamp_viz,
        bar_metric_prefix="vapi_fa",
        area_metric_prefix="valuebs",
        selected_price_range_pct_override=7.5
    )
    if fig_vapi_vs_value_focused and fig_vapi_vs_value_focused.data: 
        test_logger.info("    Combined Rolling Flow chart (VAPI-FA vs ValueBS - 5m/15m focus) generated successfully.")
    else: 
        test_logger.error("    Combined Rolling Flow chart (VAPI-FA vs ValueBS - 5m/15m focus) generation FAILED.")
    
    visualizer_test_instance.config["rolling_intervals"] = original_intervals 

    test_logger.info("  Testing with Raw VolBS (bar) vs Raw ValueBS (area) - default intervals from config")
    fig_raw_volval = visualizer_test_instance.create_combined_rolling_flow_chart(
        processed_data=sample_processed_data_df_viz, 
        symbol=test_symbol_viz, 
        current_price=current_underlying_price_viz, 
        fetch_timestamp=fetch_timestamp_viz
    )
    if fig_raw_volval and fig_raw_volval.data: 
        test_logger.info("    Combined Rolling Flow chart (Raw VolBS vs Raw ValueBS) generated successfully.")
    else: 
        test_logger.error("    Combined Rolling Flow chart (Raw VolBS vs Raw ValueBS) generation FAILED.")

    test_logger.info(f"\n--- Briefly re-testing a few other chart functions ---")
    fig_mspi_hm = visualizer_test_instance.create_mspi_heatmap(sample_processed_data_df_viz, symbol=test_symbol_viz, fetch_timestamp=fetch_timestamp_viz)
    if fig_mspi_hm and fig_mspi_hm.data: test_logger.info("  MSPI Heatmap generated.")
    else: test_logger.error("  MSPI Heatmap FAILED.")

    greek_heatmap_options = visualizer_config._get_config_value(visualizer_test_instance.instance_logger, visualizer_test_instance.full_app_config, visualizer_test_instance.config, "greek_flow_heatmap_options", [])
    default_greek_metric = visualizer_config._get_config_value(visualizer_test_instance.instance_logger, visualizer_test_instance.full_app_config, visualizer_test_instance.config, "greek_flow_heatmap_default_metric", visualizer_test_instance.col_net_gamma_flow)
    
    default_cs_key = "default_greek_cs" 
    default_cb_title = "Default Greek Flow Value"
    
    if greek_heatmap_options and isinstance(greek_heatmap_options, list) and len(greek_heatmap_options) > 0:
        default_option_cfg = greek_heatmap_options[0]
        metric_to_plot_greek = default_option_cfg.get("metric_col", default_greek_metric)
        cs_key_greek = default_option_cfg.get("cs_key", default_cs_key)
        cb_title_greek = default_option_cfg.get("cb_title", default_cb_title)
    else: 
        metric_to_plot_greek = default_greek_metric
        cs_key_greek = default_cs_key
        cb_title_greek = default_cb_title
        test_logger.warning("  Greek heatmap options not found in config, using test defaults for metric, cs_key, cb_title.")

    fig_greek_default = visualizer_test_instance.create_net_greek_flow_heatmap(
        processed_data=sample_processed_data_df_viz,
        metric_column_to_plot=metric_to_plot_greek,
        chart_main_title_prefix="Net Gamma Flow", 
        colorscale_config_key=cs_key_greek, 
        colorbar_title_text=cb_title_greek,
        symbol=test_symbol_viz, fetch_timestamp=fetch_timestamp_viz, current_price=current_underlying_price_viz
    )
    if fig_greek_default and fig_greek_default.data: test_logger.info(f"  Net Greek Flow Heatmap ({metric_to_plot_greek}) generated.")
    else: test_logger.error(f"  Net Greek Flow Heatmap ({metric_to_plot_greek}) FAILED.")

    test_logger.info("--- MSPIVisualizerV2 Test Run Complete (VAPI-FA Multi-Interval Focus) ---")
