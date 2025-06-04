# visualizer_config.py
"""
Configuration for the MSPIVisualizer.
"""

import os
import json
import logging
import copy
from typing import Dict, Any, Optional, List, Union

# --- Default Configuration for MSPIVisualizerV2 ---
DEFAULT_VISUALIZER_CONFIG: Dict[str, Any] = {
    'log_level': 'INFO',  # Default logging level for the visualizer instance
    'output_dir': 'visualizations',  # Default subdirectory for saving charts
    'save_charts_as_html': False,  # Whether to save charts as HTML files
    'save_charts_as_png': False,   # Whether to save charts as PNG files (requires Kaleido)
    'plotly_template': 'plotly_dark',  # Default Plotly template for charts
    'default_chart_height': 700,      # Default height for most charts
    'min_normalization_denominator': 1e-9, # Small value to prevent division by zero

    'colorscales': { # Predefined colorscales for heatmaps
        'mspi_heatmap': 'RdBu',
        'net_value_heatmap': 'RdYlGn', # Example: Green for positive, Red for negative
        'net_volume_pressure_heatmap': 'coolwarm', # Example
        'default_greek_cs': 'viridis', # Default for greek exposure heatmaps
        'gamma_colorscale': 'Viridis',
        'vanna_colorscale': 'Cividis',
        'charm_colorscale': 'Plasma',
        'ultima_colorscale': 'Magma',
        'vomma_colorscale': 'Inferno',
        'speed_colorscale': 'Portland'
    },

    'key_level_markers': { # Styles for key levels visualization
        'major_support': {'name': 'Major Support', 'symbol': 'triangle-up', 'color': '#2ECC71', 'size': 12},
        'minor_support': {'name': 'Minor Support', 'symbol': 'triangle-up-dot', 'color': '#ABEBC6', 'size': 10},
        'major_resistance': {'name': 'Major Resistance', 'symbol': 'triangle-down', 'color': '#E74C3C', 'size': 12},
        'minor_resistance': {'name': 'Minor Resistance', 'symbol': 'triangle-down-dot', 'color': '#F5B7B1', 'size': 10},
        'equilibrium': {'name': 'Equilibrium', 'symbol': 'diamond', 'color': '#3498DB', 'size': 10},
        'critical_threshold': {'name': 'Critical Threshold', 'symbol': 'hexagram', 'color': '#F39C12', 'size': 11},
        'attraction_point': {'name': 'Attraction Point', 'symbol': 'star', 'color': '#9B59B6', 'size': 10},
        'neutral_zone': {'name': 'Neutral Zone', 'symbol': 'square-dot', 'color': '#BDC3C7', 'size': 8},
        'custom_level_1': {'name': 'Custom Level Alpha', 'symbol': 'cross', 'color': '#1ABC9C', 'size': 9},
        'custom_level_2': {'name': 'Custom Level Beta', 'symbol': 'x', 'color': '#E67E22', 'size': 9},
        'default': {'name': 'Undefined Level', 'symbol':'circle-open', 'color':'grey', 'size':7}
    },

    'signal_styles': { # Styles for trading signals visualization
        'bullish_reversal': {'symbol': 'arrow-up', 'color': 'lime', 'size': 12, 'name': 'Bullish Reversal'},
        'bearish_reversal': {'symbol': 'arrow-down', 'color': 'magenta', 'size': 12, 'name': 'Bearish Reversal'},
        'continuation_bull': {'symbol': 'arrow-right', 'color': 'cyan', 'size': 10, 'name': 'Bullish Continuation'},
        'continuation_bear': {'symbol': 'arrow-left', 'color': 'yellow', 'size': 10, 'name': 'Bearish Continuation'},
        'zone_entry_bull': {'symbol': 'star-triangle-up', 'color': 'palegreen', 'size': 10, 'name': 'Bullish Zone Entry'},
        'zone_entry_bear': {'symbol': 'star-triangle-down', 'color': 'lightcoral', 'size': 10, 'name': 'Bearish Zone Entry'},
        'high_conviction_buy': {'symbol': 'star-diamond', 'color': 'springgreen', 'size': 14, 'name': 'High Conviction Buy'},
        'high_conviction_sell': {'symbol': 'star-diamond', 'color': 'tomato', 'size': 14, 'name': 'High Conviction Sell'},
        'neutral_signal': {'symbol': 'circle-dot', 'color': 'silver', 'size': 9, 'name': 'Neutral Signal'},
        'default': {'symbol': 'circle', 'color': 'grey', 'size': 8, 'name': 'Undefined Signal'}
    },

    'column_names': { # Mapping internal keys to expected DataFrame column names
        'strike': 'strike',
        'option_type': 'opt_kind', # Changed from option_kind
        'mspi_score': 'MSPI_Score', # Changed from mspi
        'net_volume_pressure': 'net_volume_pressure',
        'net_value_pressure': 'net_value_pressure',
        'heuristic_net_delta_pressure': 'heuristic_net_delta_pressure',
        'net_gamma_flow_at_strike': 'net_gamma_flow',
        'net_vega_flow_at_strike': 'net_vega_flow',
        'net_theta_exposure_at_strike': 'net_theta_exposure',
        'expiry_date': 'expiry_date', # For heatmaps needing expiry
        # Add other mappings as needed by the visualizer or its data sources
    },

    'hover_settings': { # Configuration for hover tooltips
        'mode': 'closest', # Default hovermode for most charts ('x', 'y', 'closest', 'x unified', 'y unified')
        'overview_metrics_config': [ # Columns to show in a generic "Overview" section
            {'key': 'MSPI_Score', 'label': 'MSPI', 'precision': 3, 'is_currency': False},
            {'key': 'sai', 'label': 'SAI', 'precision': 3, 'is_currency': False},
            {'key': 'ssi', 'label': 'SSI', 'precision': 3, 'is_currency': False},
            {'key': 'cfi', 'label': 'ARFI', 'precision': 3, 'is_currency': False}, # ARFI is new cfi
        ],
        'oi_structure_metrics_config': [ # For OI structure section
            {'base_key': 'oi', 'label': 'Open Interest'},
            {'base_key': 'vol', 'label': 'Volume'},
            {'base_key': 'net_oi_norm', 'label': 'Net OI (N)'},
        ],
        'details_section_keys': [ # Keys to show in a "Details" section of hover
            'level_category', 'level_type_original', 'strategy', 'rationale', 'type', 'conviction', 'status_update'
        ],
        'chart_specific_hover': { # Overrides or specific settings per chart_type key
            'mspi_heatmap': {
                'sections': ['base_info', 'mspi_value', 'core_indices'], # Order of sections
                'core_indices_keys': ['sai', 'ssi', 'cfi'] # Which core indices for this heatmap
            },
            'net_value_heatmap': {
                'sections': ['base_info', 'net_pressures', 'overview_metrics']
            },
            'net_volume_pressure_heatmap':{
                'sections': ['base_info', 'net_pressures', 'overview_metrics']
            },
            'mspi_components': {
                'sections': ['base_info', 'mspi_value', 'overview_metrics', 'oi_structure']
            },
            'key_levels': {
                'sections': ['base_info', 'details_section']
            },
            'trading_signals': {
                'sections': ['base_info', 'details_section', 'core_metrics_context']
            },
            'default': { # Default hover sections if chart_type not specified
                'sections': ['base_info', 'overview_metrics']
            }
        },
        'show_overview_metrics_default': True,
        'show_oi_structure_default': True,
        'show_details_section_default': True,
    },

    'chart_specific_params': { # Parameters specific to certain chart types
        'component_comparison_height': 800,
        'volval_comparison_height': 700,
        'combined_flow_chart_height': 750,
        'key_levels_height': 600,
        'trading_signals_height': 650,
        'recommendations_table_height': 450,
        'raw_greek_charts_price_range_pct': 10.0, # Default +/- % for raw greek chart x-axis range
        'combined_flow_chart_price_range_pct': 15.0, # Default for combined flow chart x-axis
        'combined_rolling_flow_chart_barmode': 'relative', # 'group', 'overlay', 'relative'
        'mspi_components_bar_colors': { # Default colors for component comparison chart
            # Main MSPI (though plotted as area, can have a ref color)
            "MSPI_Score": {"pos": "rgba(0,0,200,0.5)", "neg": "rgba(200,0,0,0.5)"}, # Example for area fill
            # Normalized Components (typically bars)
            "a_dag_norm": {"pos": "#1f77b4", "neg": "#aec7e8"}, # Blueish
            "dag_custom_norm": {"pos": "#1f77b4", "neg": "#aec7e8"},
            "d_tdpi_norm": {"pos": "#ff7f0e", "neg": "#ffbb78"},  # Orangish
            "tdpi_norm": {"pos": "#ff7f0e", "neg": "#ffbb78"},
            "vri_2_0_norm": {"pos": "#2ca02c", "neg": "#98df8a"}, # greenish
            "vri_norm": {"pos": "#2ca02c", "neg": "#98df8a"},
            "e_sdag_composite_norm": {"pos": "#d62728", "neg": "#ff9896"}, # Reddish
            # Individual sDAG methods if plotted directly (can be more specific)
            "sdag_multiplicative_norm": {"pos": "#9467bd", "neg": "#c5b0d5"}, # Purplish
            "sdag_directional_norm": {"pos": "#8c564b", "neg": "#c49c94"}, # brownish
            "sdag_weighted_norm": {"pos": "#e377c2", "neg": "#f7b6d2"}, # Pinkish
            "sdag_volatility_focused_norm": {"pos": "#7f7f7f", "neg": "#c7c7c7"}, # Greyish
            # Default for any other component not listed
            "default_pos": "#cccccc", "default_neg": "#777777"
        },
        'volval_ghost_settings': { # Settings for historical traces in VolVal comparison
            'enabled': True,
            'number_of_ghosts': 3, # Max number of historical traces to show
            'base_opacity': 0.4,
            'opacity_step': 0.1, # Reduction per older trace
            'min_opacity': 0.1
            # Specific color overrides per history slot (T-1, T-A etc.) can be added if needed
        },
        'rolling_flow_customization': { # For create_combined_rolling_flow_chart
            "5m": {"volume_positive_color":"#1f77b4", "volume_negative_color":"#aec7e8", "volume_opacity":0.7,
                   "value_positive_fill_color":"rgba(255,127,14,0.1)", "value_negative_fill_color":"rgba(255,187,120,0.1)",
                   "value_positive_line_color":"rgba(255,127,14,0.5)", "value_negative_line_color":"rgba(255,187,120,0.5)"},
            "15m": {"volume_positive_color":"#2ca02c", "volume_negative_color":"#98df8a", "volume_opacity":0.6}, # And so on for value
            # ... other intervals like 30m, 60m
            "defaults": {"volume_positive_color":"#cccccc", "volume_negative_color":"#777777", "volume_opacity":0.5,
                         "value_positive_fill_color":"rgba(200,200,200,0.1)", "value_negative_fill_color":"rgba(100,100,100,0.1)",
                         "value_positive_line_color":"rgba(200,200,200,0.5)", "value_negative_line_color":"rgba(100,100,100,0.5)"}
        },
        'recommendations_table_column_display_map': { # For strategy recommendations table
            'id': "ID", 'Category': "Category", 'direction_label': "Bias/Type", 'strike': "Strike",
            'strategy': "Strategy / Note", 'conviction_stars': "Conv★", 'status': 'Status',
            'raw_conviction_score_final_adj': "Score",
            'entry_ideal': "Entry", 'target_1': "T1", 'target_2': "T2", 'stop_loss': "SL",
            'underlying_price_at_signal': 'Underlying@Signal',
            'rationale': "Rationale", 'target_rationale': "Tgt. Logic",
            'mspi_at_signal': 'MSPI@Signal', 'sai_at_signal': 'SAI@Signal',
            'timestamp': 'Issued', 'last_updated_ts': 'Adjusted', 'exit_reason':'Exit Info',
            'signal_type_source': 'Signal Src Detail'
        },
        'show_net_sdag_trace': True, # For _create_raw_greek_chart (specifically sDAG variants)
        'net_sdag_marker_style': {'symbol': 'diamond', 'color': 'rgba(255, 255, 255, 0.7)', 'size': 8, 'line': dict(color='white', width=1)},
        'net_sdag_trace_default_visibility': 'legendonly', # True, False, 'legendonly'
    },

    'legend_settings': { # Default legend settings
        'orientation': 'h', # 'h' for horizontal, 'v' for vertical
        'yanchor': 'bottom',
        'y': 1.02,
        'xanchor': 'right',
        'x': 1,
        'traceorder': 'normal', # 'normal', 'reversed', 'grouped', 'reversed grouped'
        'show_legend': True
    },

    'price_line_config': { # For current price lines on charts
        'show_current_price_line': True,
        'current_price_line_color': 'rgba(255, 255, 0, 0.6)', # Yellowish, semi-transparent
        'current_price_line_width': 1.5,
        'current_price_line_dash': 'dash',
        'show_current_price_line_heatmap': True, # Specifically for heatmaps
    },
    
    'timestamp_config': { # For timestamp annotations on charts
        'enabled': True,
        'font_color': 'grey',
        'font_size': 10,
        'position_x': 0.99, # Paper referenced
        'position_y': 0.01, # Paper referenced
        'xanchor': 'right',
        'yanchor': 'bottom'
    },
    
    'rolling_intervals': ["5m", "15m", "30m", "60m"], # For combined rolling flow chart
    
    # Added based on the previous DEFAULT_VISUALIZER_CONFIG from visualizer_config.py
    "MSPI_INPUT_DATA_PATH": "data/mspi_output_data_2024_01_01_to_2024_04_01_SPY.json", # Example path
    # VISUALIZATION_OUTPUT_PATH is now 'output_dir' above.
    "LOG_LEVEL": "INFO", # Already covered by 'log_level'
    "MAX_ROWS_FOR_AGGREGATION": 1000, # Example, might not be used by refactored version directly
    "DEFAULT_AGGREGATION_TYPE": "mean", # Example
    "PLOT_WIDTH": 1200, # General plot width, used by save_figure
    "PLOT_HEIGHT": 600, # Covered by 'default_chart_height'
    "SHOW_GRID": True, # General grid setting, usually controlled per axis in layout
    "FIGURE_TITLE_PREFIX": "MSPI Viz - ", # Prefix for chart titles
    "DATE_FORMAT": "%Y-%m-%d", # General date formatting string
    "HOVER_TOOLTIPS_PRICE_FORMAT": "$0,0.00", # Format for prices in hover (if plot_utils._format_hover_value uses it)
    "AXIS_LABEL_FONT_SIZE": "12pt",
    "TITLE_FONT_SIZE": "14pt",
    "LEGEND_FONT_SIZE": "10pt",
    "ERROR_BAR_ALPHA": 0.2,
    "EXTERNAL_STYLESHEETS": ["https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css"], # For Dash apps
    "DATA_REFRESH_INTERVAL_SECONDS": 300, # For Dash apps
    "USE_DARK_THEME": False, # General theme preference
    "UI_ELEMENT_CONFIG": { # For Dash apps or similar UI
        "DROPDOWN_WIDTH": "200px",
        "BUTTON_COLOR": "primary",
        "SLIDER_STEP": 0.1
    },
    # Configuration for specific Greek flow heatmaps (used if create_net_greek_flow_heatmap is called via a dispatcher)
    "greek_flow_heatmap_options": [
        {"id": "net_gamma_flow", "label": "Net Gamma Flow", "metric_col": "net_gamma_flow", "cs_key": "gamma_colorscale", "cb_title": "Net Gamma"},
        {"id": "net_vanna_flow", "label": "Net Vanna Flow", "metric_col": "net_vanna_flow", "cs_key": "vanna_colorscale", "cb_title": "Net Vanna"},
        # Add other greeks like charm, vomma, speed if they are generated and need heatmaps
    ],
    "greek_flow_heatmap_default_metric": "net_gamma_flow" # Default metric for the generic greek heatmap if no specific one is chosen
}


def _deep_merge_dicts(source: Dict[Any, Any], destination: Dict[Any, Any]) -> Dict[Any, Any]:
    """
    Deeply merges two dictionaries. Modifies destination in place.
    """
    for key, value in source.items():
        if isinstance(value, dict):
            node = destination.setdefault(key, {})
            if isinstance(node, dict): # Ensure node is a dict before merging
                 _deep_merge_dicts(value, node)
            else: # If node in destination is not a dict, overwrite with source value
                destination[key] = copy.deepcopy(value) # USE DEEPCOPY
        else:
            destination[key] = copy.deepcopy(value) # USE DEEPCOPY
    return destination

def _load_visualizer_specific_config(
    instance_logger: logging.Logger,
    full_app_config_from_init: Optional[Dict[str, Any]] = None,
    config_path_override: Optional[str] = None, # For directly passing a path to a full app config JSON
    default_viz_config_override: Optional[Dict[str, Any]] = None # For tests or specific overrides
) -> Dict[str, Any]:
    """
    Loads visualizer-specific configuration.
    Priority:
    1. Settings from a 'visualization_settings.mspi_visualizer' section in a full app config
       (loaded from `config_path_override` or `full_app_config_from_init`).
    2. Default visualizer configuration (`DEFAULT_VISUALIZER_CONFIG` from this module or `default_viz_config_override`).
    """
    load_config_logger = instance_logger.getChild("LoadVisualizerSpecificConfig")
    
    # Determine the base default visualizer config to use
    base_defaults = default_viz_config_override if isinstance(default_viz_config_override, dict) else DEFAULT_VISUALIZER_CONFIG.copy()
    
    # Determine the source of the full application configuration
    loaded_full_app_config: Dict[str, Any] = {}
    source_description = "using internal defaults"

    if isinstance(full_app_config_from_init, dict) and full_app_config_from_init:
        loaded_full_app_config = json.loads(json.dumps(full_app_config_from_init)) # Deep copy
        source_description = "from 'config_data' passed to init"
        load_config_logger.info(f"Full application config provided via 'config_data'.")
    elif config_path_override:
        abs_path = config_path_override
        if not os.path.isabs(abs_path):
            try: script_dir = os.path.dirname(os.path.abspath(__file__)) # mspi_visualizer dir
            except NameError: script_dir = os.getcwd()
            # Try path relative to current working directory first, then relative to this script
            path_from_cwd = os.path.join(os.getcwd(), config_path_override)
            path_from_script_dir = os.path.join(script_dir, config_path_override)
            if os.path.exists(path_from_cwd): abs_path = path_from_cwd
            elif os.path.exists(path_from_script_dir): abs_path = path_from_script_dir
            # else: abs_path remains as originally passed, might be relative and valid or invalid
        
        if os.path.exists(abs_path):
            try:
                with open(abs_path, 'r', encoding='utf-8') as f:
                    loaded_full_app_config = json.load(f)
                source_description = f"from JSON file at '{abs_path}'"
                load_config_logger.info(f"Full application config loaded from {abs_path}.")
            except json.JSONDecodeError as e:
                load_config_logger.error(f"Error decoding JSON from '{abs_path}': {e}. Proceeding with defaults for visualizer.")
            except Exception as e:
                load_config_logger.error(f"Error loading full app config from '{abs_path}': {e}. Proceeding with defaults for visualizer.")
        else:
            load_config_logger.warning(f"Full app config file '{abs_path}' (from override '{config_path_override}') not found. Visualizer will use defaults.")
    else:
        load_config_logger.info("No 'config_data' or 'config_path_override' provided. Visualizer using its defaults.")

    # Extract the visualizer-specific section from the loaded full app config
    visualizer_settings_from_full_app = {}
    if loaded_full_app_config:
        visualizer_settings_from_full_app = loaded_full_app_config.get("visualization_settings", {}).get("mspi_visualizer", {})
        if visualizer_settings_from_full_app:
             load_config_logger.info(f"Found 'visualization_settings.mspi_visualizer' section in full app config ({source_description}).")
        else:
             load_config_logger.info(f"No 'visualization_settings.mspi_visualizer' section found in full app config ({source_description}). Using visualizer defaults.")
    
    # Merge: Start with base_defaults, then update with visualizer_settings_from_full_app
    final_config = base_defaults.copy() # Start with a copy of defaults
    if isinstance(visualizer_settings_from_full_app, dict) and visualizer_settings_from_full_app:
        _deep_merge_dicts(visualizer_settings_from_full_app, final_config) # Merge user settings into defaults
        load_config_logger.info("Visualizer-specific settings merged with defaults.")
    else:
        load_config_logger.info("Using only default visualizer settings.")
        
    return final_config


def _get_config_value(
    instance_logger: logging.Logger, # Logger passed from the visualizer instance
    full_app_config: Dict[str, Any], # The complete application configuration
    visualizer_specific_config: Dict[str, Any], # The already resolved visualizer config
    key: str, # The specific key to retrieve (can be dot-separated for nesting)
    default: Optional[Any] = None # Default value if key is not found
) -> Any:
    """
    Retrieves a configuration value with a specific priority.
    1. From `visualizer_specific_config` if the key exists directly there.
    2. From `full_app_config` if the key exists there (potentially nested).
    3. `default` if not found in either.

    The `key` can be a simple string or a dot-separated path for nested access
    within `full_app_config`. For `visualizer_specific_config`, direct key access is assumed.
    """
    # Check visualizer_specific_config first (direct key access)
    if key in visualizer_specific_config:
        # instance_logger.debug(f"Config key '{key}' found in visualizer_specific_config.")
        return visualizer_specific_config[key]

    # If not in specific, try full_app_config (potentially nested)
    keys = key.split('.')
    current_level = full_app_config
    path_found = True
    try:
        for k_part in keys:
            if isinstance(current_level, dict) and k_part in current_level:
                current_level = current_level[k_part]
            else:
                path_found = False
                break
        if path_found:
            # instance_logger.debug(f"Config key '{key}' found in full_app_config.")
            return current_level
    except Exception as e: # Broad exception for safety during dict traversal
        instance_logger.debug(f"Error accessing key '{key}' in full_app_config: {e}. Will try default.")
        path_found = False
        
    # instance_logger.debug(f"Config key '{key}' not found in specific or full config. Returning default: {default}")
    return default
