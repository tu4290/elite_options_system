
# /home/ubuntu/dashboard_v2/layout.py
# -*- coding: utf-8 -*-
"""
Defines the layout structure for the Enhanced Options Dashboard V2.
Uses Dash Bootstrap Components for layout and includes placeholders for all charts
and configuration-driven UI elements.
(Version: V19.2 - Full IDS Integration - Layout with Robustness Fixes)
"""

import logging
import os
import json
import dash_bootstrap_components as dbc # Alias is 'dbc' here
from dash import dcc, html
from typing import Optional, List, Dict, Any
import plotly.graph_objects as go

# --- Initialize Logger for this Script ---
logger_layout = logging.getLogger(__name__)
logger_layout.info("layout.py (V19.2): Logger initialized.")

# --- EOTS Project Imports ---
try:
    from utils import ids # Correct: 'ids.py' is in the 'utils' folder
    from .utils import get_config_value, create_empty_figure as util_create_empty_figure # Correct: relative import for sibling utils.py
    from dashboard_v2.styling import APP_THEME, ENHANCED_BLURBS, apply_card_styling # Correct: relative to project root
    # Import specific style dicts for direct use where needed.
    from dashboard_v2.styling import (
        STYLE_APP_WRAPPER, STYLE_H1_TITLE, STYLE_CONTROL_PANEL_WRAPPER,
        STYLE_CONTROL_BOX_CARD, STYLE_CONTROL_ROW, STYLE_LABEL, STYLE_INPUT,
        STYLE_BUTTON_PRIMARY, STYLE_STATUS_DISPLAY, STYLE_CHART_ROW,
        STYLE_CHART_CARD, STYLE_CHART_TITLE_CONTAINER, STYLE_CHART_TITLE,
        STYLE_INFO_ICON, STYLE_LOADING_WRAPPER, STYLE_TOOLTIP
    )

    _layout_dependencies_imported_ok = True
    logger_layout.info("LAYOUT.PY (V19.2): Successfully imported from .utils and .styling.")
except ImportError as e_layout_dependencies_imp:
    logger_layout.critical(
        f"LAYOUT.PY (V19.2) CRITICAL: Failed to import essential dependencies: {e_layout_dependencies_imp}. "
        "Layout will use hardcoded fallbacks, functionality and appearance will be affected.",
        exc_info=True
    )
    _layout_dependencies_imported_ok = False
    # Hardcoded Fallbacks for critical functions/variables if imports fail
    _FALLBACK_CONFIG_LAYOUT_INTERNAL: Optional[Dict[str, Any]] = None
    def _load_fallback_config_layout() -> Dict[str, Any]:
        global _FALLBACK_CONFIG_LAYOUT_INTERNAL
        if _FALLBACK_CONFIG_LAYOUT_INTERNAL is not None: return _FALLBACK_CONFIG_LAYOUT_INTERNAL
        fallback_path_options = [
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "config_v2.json"), # Parent dir
            os.path.join(os.path.abspath(os.getcwd()), "config_v2.json") # CWD
        ]
        for fp_option in fallback_path_options:
            if os.path.exists(fp_option):
                try:
                    with open(fp_option, 'r') as f_cfg_fb:
                        _FALLBACK_CONFIG_LAYOUT_INTERNAL = json.load(f_cfg_fb)
                        logger_layout.warning(f"LAYOUT.PY FALLBACK: Loaded config from {fp_option} for fallback get_config_value.")
                        return _FALLBACK_CONFIG_LAYOUT_INTERNAL
                except Exception as e_fb_load: logger_layout.error(f"LAYOUT.PY FALLBACK: Error loading config from {fp_option}: {e_fb_load}")
        
        logger_layout.warning("LAYOUT.PY FALLBACK: Using hardcoded minimal config as no fallback file found.")
        _FALLBACK_CONFIG_LAYOUT_INTERNAL = {
            "visualization_settings": {
                "dashboard": {
                    "defaults": {"symbol": "SPY_FB", "dte": "0_FB", "range_pct": 2.5, "refresh_interval_ms": 0},
                    "range_slider_marks": {str(i): f"{i}%" for i in range(1, 21, 2)},
                    "refresh_options": [{'label': 'Manual', 'value': 0}, {'label': '30s', 'value': 30000}],
                    "title": "EOTS Dashboard (Fallback Title)",
                    "footer_text": "© Fallback Footer Text",
                    "default_graph_height": 550
                },
                "mspi_visualizer": {
                    "column_names": {"strike": "strike_price_fb"}, # Fallback strike col name
                    "greek_flow_heatmap_options": [{'label': 'MSPI (Default_FB)', 'value': 'mspi_fb'}],
                    "greek_flow_heatmap_default_metric": "mspi_fb",
                    "rolling_flow_chart_options": [{'label': 'Raw Vol/Val BS (FB)', 'value': 'raw_volval_bs_fb'}],
                    "rolling_flow_chart_default_option": 'raw_volval_bs_fb'
                }
            }
        }
        return _FALLBACK_CONFIG_LAYOUT_INTERNAL

    def get_config_value(keys: List[str], default: Any = None, config_override: Optional[Dict] = None) -> Any:
        config_to_use = config_override if isinstance(config_override, dict) else _load_fallback_config_layout()
        temp = config_to_use
        try:
            for k in keys: temp = temp[k]
            return temp
        except (KeyError, TypeError): return default

    def util_create_empty_figure(title: str = "Chart Error", height: Optional[int] = 550, reason: Optional[str] = "Layout Dependency Missing") -> go.Figure:
        fig = go.Figure(); fig.update_layout(title={"text": f"{title}<br><sub>({reason})</sub>"}, template="plotly_dark", height=height or 550, xaxis={'visible': False}, yaxis={'visible': False}); return fig

    APP_THEME = dbc.themes.DARKLY # Use dbc alias here for fallback
    ENHANCED_BLURBS: Dict[str, str] = {key: f"<p>Info: {key.replace('-', ' ').title()} (Fallback Blurb)</p>" for key in [
        # Directly use string literals here for fallbacks as ids.py might not be imported.
        "mspi-heatmap-main-chart", "net-value-pressure-heuristic-heatmap-chart", "net-volume-pressure-heuristic-heatmap-chart",
        "mspi-components-comparison-chart", "net-greek-flow-heatmap-main-chart", "combined-rolling-flow-main-chart",
        "volatility-regime-indicator-chart", "time-decay-pressure-indicator-chart", "sdag-multiplicative-detail-chart",
        "sdag-directional-detail-chart", "sdag-weighted-detail-chart", "sdag-volatility-focused-detail-chart",
        "key-market-levels-chart", "generated-trading-signals-chart", "strategy-recommendations-table-display"
    ]}
    # Fallback for styles if import fails, ensure they are dicts
    STYLE_APP_WRAPPER, STYLE_H1_TITLE, STYLE_CONTROL_PANEL_WRAPPER, STYLE_CONTROL_BOX_CARD, \
    STYLE_CONTROL_ROW, STYLE_LABEL, STYLE_INPUT, STYLE_BUTTON_PRIMARY, \
    STYLE_STATUS_DISPLAY, STYLE_CHART_ROW, STYLE_CHART_CARD, \
    STYLE_CHART_TITLE_CONTAINER, STYLE_CHART_TITLE, STYLE_INFO_ICON, \
    STYLE_LOADING_WRAPPER, STYLE_TOOLTIP = [{} for _ in range(16)]
    def apply_card_styling(): return {"marginBottom": "20px", "border": "1px solid #555"}


# --- Helper function to create a standardized chart card ---
def create_chart_card(chart_id: str, card_title_text: Optional[str] = None, blurb_html_key: Optional[str] = None) -> dbc.Card:
    card_creation_logger = logger_layout.getChild(f"CreateChartCard.{chart_id}")
    card_creation_logger.debug(f"Creating chart card for ID: '{chart_id}'")

    default_height_cfg = get_config_value(ids.CFG_DASHBOARD_DEFAULT_GRAPH_HEIGHT, 600)
    default_height = int(default_height_cfg) if isinstance(default_height_cfg, (int, float)) and default_height_cfg > 100 else 600

    # Ensure blurb_html_key is mapped to an ID constant for lookup in ENHANCED_BLURBS
    actual_blurb_key = blurb_html_key or chart_id
    blurb_html_str = ENHANCED_BLURBS.get(actual_blurb_key, f"<p class='text-muted small'>No description available for: {actual_blurb_key}.</p>")
    
    accordion_display_title = card_title_text or actual_blurb_key.replace('-', ' ').replace('_', ' ').title()
    # Extract title from blurb_html_str if it contains h3 or h6 tags
    if "<h6>" in blurb_html_str:
        try: accordion_display_title = blurb_html_str.split("<h6>")[1].split("</h6>")[0]
        except IndexError: pass
    elif "<h3>" in blurb_html_str:
        try: accordion_display_title = blurb_html_str.split("<h3>")[1].split("</h3>")[0]
        except IndexError: pass

    card_body_elements: List[Any] = []

    # Logic for chart-specific dropdowns using ids.py constants
    if chart_id == ids.ID_CHART_MSPI_HEATMAP:
        mspi_view_options_cfg = get_config_value(ids.CFG_VIZ_MSPI_HEATMAP_VIEW_OPTIONS, [
            {'label': 'MSPI Heatmap (Base)', 'value': 'mspi_heatmap'},
            {'label': 'Net Volume Pressure (H)', 'value': 'net_volume_pressure_heatmap'},
            {'label': 'Net Value Pressure (H)', 'value': 'net_value_heatmap'}
        ])
        default_mspi_view = get_config_value(ids.CFG_VIZ_MSPI_HEATMAP_DEFAULT_VIEW, 'mspi_heatmap')
        card_body_elements.append(
            html.Div([
                dbc.Label("Select Heatmap View:", html_for=ids.ID_MSPI_HEATMAP_SELECTOR, className="fw-bold control-label mb-1 small"),
                dcc.Dropdown(
                    id=ids.ID_MSPI_HEATMAP_SELECTOR, options=mspi_view_options_cfg, value=default_mspi_view,
                    clearable=False, className="mb-3 form-select-sm dashboard-dropdown", searchable=False, style={'fontSize': '0.85rem'}
                )
            ], className="mb-2 chart-selector-container")
        )
    elif chart_id == ids.ID_CHART_NET_GREEK_FLOW_HEATMAP:
        raw_greek_opts = get_config_value(ids.CFG_VIZ_GREEK_FLOW_HEATMAP_OPTIONS, [])
        greek_options_for_dd = [{'label': str(opt.get('label')), 'value': str(opt.get('value'))} for opt in raw_greek_opts if isinstance(opt, dict) and 'label' in opt and 'value' in opt]
        default_greek_val = get_config_value(ids.CFG_VIZ_GREEK_FLOW_HEATMAP_DEFAULT_METRIC, (greek_options_for_dd[0]['value'] if greek_options_for_dd else None))
        card_body_elements.append(
            html.Div([
                dbc.Label("Select Greek/Metric View:", html_for=ids.ID_NET_GREEK_FLOW_SELECTOR, className="fw-bold control-label mb-1 small"),
                dcc.Dropdown(
                    id=ids.ID_NET_GREEK_FLOW_SELECTOR, options=greek_options_for_dd, value=default_greek_val,
                    clearable=False, className="mb-3 form-select-sm dashboard-dropdown", searchable=False, style={'fontSize': '0.85rem'}
                )
            ], className="mb-2 chart-selector-container")
        )
    elif chart_id == ids.ID_CHART_COMBINED_ROLLING_FLOW:
        raw_rolling_opts = get_config_value(ids.CFG_VIZ_ROLLING_FLOW_CHART_OPTIONS, [])
        rolling_options_for_dd = [{'label': str(opt.get('label')), 'value': str(opt.get('value'))} for opt in raw_rolling_opts if isinstance(opt, dict) and 'label' in opt and 'value' in opt]
        default_rolling_val = get_config_value(ids.CFG_VIZ_ROLLING_FLOW_CHART_DEFAULT_OPTION, (rolling_options_for_dd[0]['value'] if rolling_options_for_dd else None))
        card_body_elements.append(
            html.Div([
                dbc.Label("Select Rolling Flow Type:", html_for=ids.ID_ROLLING_FLOW_SELECTOR, className="fw-bold control-label mb-1 small"),
                dcc.Dropdown(
                    id=ids.ID_ROLLING_FLOW_SELECTOR, options=rolling_options_for_dd, value=default_rolling_val,
                    clearable=False, className="mb-3 form-select-sm dashboard-dropdown", searchable=False, style={'fontSize': '0.85rem'}
                )
            ], className="mb-2 chart-selector-container")
        )

    card_body_elements.append(
        dbc.Accordion(
            dbc.AccordionItem(
                dcc.Markdown(blurb_html_str, dangerously_allow_html=True, className="blurb-markdown small text-muted"),
                title=f"Info: {accordion_display_title}", item_id=f"accordion-item-{chart_id}",
            ), start_collapsed=True, flush=True, id=f"accordion-control-{chart_id}", className="mb-2 custom-accordion"
        )
    )
    card_body_elements.append(
        dcc.Loading(
            id=f"loading-wrapper-for-{chart_id}", type="circle", color="#007BFF", fullscreen=False,
            className="chart-loading-spinner",
            children=[
                dcc.Graph(
                    id=chart_id,
                    figure=util_create_empty_figure(title=f"{accordion_display_title} - Awaiting Data...", height=default_height, reason="Initial Load"),
                    config={'displayModeBar': True, 'scrollZoom': True, 'responsive': True, 'displaylogo': False},
                    className="dashboard-chart-graph-component"
                )
            ]
        )
    )
    
    card_style_to_apply = apply_card_styling() if _layout_dependencies_imported_ok else {"marginBottom": "20px", "border": "1px solid #555"}
    return dbc.Card(dbc.CardBody(card_body_elements, className="p-2 chart-card-body-internal"),
                    className="mb-4 shadow-sm chart-card-main-wrapper", style=card_style_to_apply)

# --- Functions to get layout for each mode/tab ---
def get_main_dashboard_mode_layout() -> html.Div:
    layout_build_logger = logger_layout.getChild("GetMainDashboardLayout_V19_2")
    layout_build_logger.info("Generating MAIN DASHBOARD MODE layout...")
    # Use lists of IDs imported from ids.py
    return html.Div([
        dbc.Row([
            dbc.Col(create_chart_card(ids.ID_CHART_KEY_LEVELS, "Key Market Levels"), lg=6, md=12, className="mb-3 chart-col"),
            dbc.Col(create_chart_card(ids.ID_CHART_MSPI_COMPONENTS, "MSPI Components"), lg=6, md=12, className="mb-3 chart-col"),
        ], className="mb-3 chart-row"),
        dbc.Row([
            dbc.Col(create_chart_card(ids.ID_CHART_MSPI_HEATMAP, "MSPI Landscape"), lg=6, md=12, className="mb-3 chart-col"),
            dbc.Col(create_chart_card(ids.ID_CHART_NET_GREEK_FLOW_HEATMAP, "Net Greek Flow"), lg=6, md=12, className="mb-3 chart-col"),
        ], className="mb-3 chart-row"),
        dbc.Row([
            dbc.Col(create_chart_card(ids.ID_CHART_COMBINED_ROLLING_FLOW, "Combined Rolling Flow"), lg=12, md=12, className="mb-3 chart-col"),
        ], className="mb-3 chart-row"),
        dbc.Row([
             dbc.Col(create_chart_card(ids.ID_CHART_TRADING_SIGNALS, "Trading Signals"), lg=6, md=12, className="mb-3 chart-col"),
             dbc.Col(create_chart_card(ids.ID_CHART_RECOMMENDATIONS_TABLE, "Strategy Recommendations"), lg=6, md=12, className="mb-3 chart-col"),
        ], className="mb-3 chart-row"),
    ], className="mode-layout-container p-3")

def get_sdag_diagnostics_mode_layout() -> html.Div:
    layout_build_logger = logger_layout.getChild("GetSdagDiagnosticsLayout_V19_2")
    layout_build_logger.info("Generating SDAG DIAGNOSTICS MODE layout...")
    # Use lists of IDs imported from ids.py
    rows_content = [
        dbc.Row([
            dbc.Col(create_chart_card(ids.ID_CHART_SDAG_MULTIPLICATIVE, "SDAG Multiplicative"), lg=6, md=12, className="mb-3 chart-col"),
            dbc.Col(create_chart_card(ids.ID_CHART_SDAG_DIRECTIONAL, "SDAG Directional"), lg=6, md=12, className="mb-3 chart-col"),
        ], className="mb-3 chart-row"),
        dbc.Row([
            dbc.Col(create_chart_card(ids.ID_CHART_SDAG_WEIGHTED, "SDAG Weighted"), lg=6, md=12, className="mb-3 chart-col"),
            dbc.Col(create_chart_card(ids.ID_CHART_SDAG_VOLATILITY_FOCUSED, "SDAG Volatility Focused"), lg=6, md=12, className="mb-3 chart-col"),
        ], className="mb-3 chart-row")
    ]
    return html.Div(rows_content, className="mode-layout-container p-3")

def get_enhanced_flow_mode_layout() -> html.Div:
    layout_build_logger = logger_layout.getChild("GetEnhancedFlowLayout_V19_2")
    layout_build_logger.info("Generating ENHANCED FLOW MODE layout...")
    # Use lists of IDs imported from ids.py
    return html.Div([
        dbc.Row([
            dbc.Col(create_chart_card(ids.ID_CHART_NET_VALUE_HEATMAP, "Net Value Pressure (H)"), lg=6, md=12, className="mb-3 chart-col"),
            dbc.Col(create_chart_card(ids.ID_CHART_NET_VOLUME_PRESSURE_HEATMAP, "Net Volume Pressure (H)"), lg=6, md=12, className="mb-3 chart-col"),
        ], className="mb-3 chart-row"),
        # dbc.Row([ # Uncomment when VAPI, DWFD, TW-LAF charts are ready
        #     dbc.Col(create_chart_card(ids.ID_CHART_VAPI_FA_OSCILLATOR, "VAPI-FA Oscillator"), lg=12, className="mb-3 chart-col"),
        # ], className="mb-3 chart-row"),
    ], className="mode-layout-container p-3")

def get_volatility_deep_dive_mode_layout() -> html.Div:
    layout_build_logger = logger_layout.getChild("GetVolatilityDeepDiveLayout_V19_2")
    layout_build_logger.info("Generating VOLATILITY DEEP DIVE MODE layout...")
    # Use lists of IDs imported from ids.py
    return html.Div([
        dbc.Row([
            dbc.Col(create_chart_card(ids.ID_CHART_VOLATILITY_REGIME, "Volatility Regime (VRI)"), lg=6, md=12, className="mb-3 chart-col"),
            dbc.Col(create_chart_card(ids.ID_CHART_TIME_DECAY, "Time Decay (TDPI)"), lg=6, md=12, className="mb-3 chart-col"),
        ], className="mb-3 chart-row"),
    ], className="mode-layout-container p-3")

# --- Main Application Layout Function ---
def get_main_layout() -> dbc.Container:
    layout_main_logger = logger_layout.getChild("GetMainLayout_V19_2_Robust")
    layout_main_logger.info("Generating OVERALL APPLICATION layout (V19.2 Robust)...")

    try:
        # Use ids.CFG_DASHBOARD_... constants for config values
        default_symbol = get_config_value(ids.CFG_DASHBOARD_DEFAULT_SYMBOL, "SPY")
        default_dte = get_config_value(ids.CFG_DASHBOARD_DEFAULT_DTE, "0")
        default_range_pct_raw = get_config_value(ids.CFG_DASHBOARD_DEFAULT_RANGE_PCT, 5.0)
        range_slider_marks_raw = get_config_value(ids.CFG_DASHBOARD_RANGE_SLIDER_MARKS, {str(i): f"{i}%" for i in range(0, 21, 5)})
        refresh_options_cfg_raw = get_config_value(ids.CFG_DASHBOARD_REFRESH_OPTIONS, [{'label': 'Manual', 'value': 0}])
        default_refresh_ms_raw = get_config_value(ids.CFG_DASHBOARD_DEFAULT_REFRESH_MS, 0)
        dashboard_title_raw = get_config_value(ids.CFG_DASHBOARD_TITLE, "EOTS Dashboard v2.5 (Default Title)")
        footer_text_raw = get_config_value(ids.CFG_DASHBOARD_FOOTER_TEXT, "© EOTS System (Default Footer)")
    except Exception as e_config_fetch_main_layout:
        layout_main_logger.critical(f"CRITICAL Error fetching initial config values for main layout: {e_config_fetch_main_layout}. Using hardcoded defaults for UI elements.", exc_info=True)
        default_symbol, default_dte, default_range_pct_raw = "SPY_CFG_ERR", "0_CFG_ERR", 2.5
        range_slider_marks_raw = {str(i): f"{i}%" for i in range(1, 11, 2)}
        refresh_options_cfg_raw = [{'label': 'Manual Error', 'value': 0}]
        default_refresh_ms_raw, dashboard_title_raw, footer_text_raw = 0, "EOTS Dashboard (Config Load Error)", "© EOTS (Config Error)"

    default_range_pct = 5.0
    try: default_range_pct = float(default_range_pct_raw)
    except (ValueError, TypeError): layout_main_logger.warning(f"Invalid default_range_pct '{default_range_pct_raw}'. Using {default_range_pct}.")

    default_refresh_ms = 0
    try: default_refresh_ms = int(default_refresh_ms_raw)
    except (ValueError, TypeError): layout_main_logger.warning(f"Invalid default_refresh_ms '{default_refresh_ms_raw}'. Using {default_refresh_ms}.")

    dashboard_title = str(dashboard_title_raw)
    footer_text_cfg = str(footer_text_raw)

    range_slider_marks_cfg = {}
    if isinstance(range_slider_marks_raw, dict):
        for k, v in range_slider_marks_raw.items():
            try: range_slider_marks_cfg[float(k)] = str(v)
            except (ValueError, TypeError): layout_main_logger.warning(f"Cannot convert slider mark key '{k}' to float.")
    if not range_slider_marks_cfg: range_slider_marks_cfg = {float(i): f"{i}%" for i in [1, 2.5, 5, 7.5, 10, 15, 20]} # Ensure a valid fallback

    refresh_options_cfg = refresh_options_cfg_raw if isinstance(refresh_options_cfg_raw, list) and refresh_options_cfg_raw else [{'label': 'Manual', 'value': 0}]

    # Control Panel
    control_panel = dbc.Card(
        dbc.Row([
            dbc.Col([dbc.Label("Symbol:", html_for=ids.ID_SYMBOL_INPUT, className="fw-bold control-label-main"),
                     dbc.Input(id=ids.ID_SYMBOL_INPUT, type="text", value=str(default_symbol), placeholder="e.g., SPY", className="mb-2 form-control-sm input-main-controls", size="sm", debounce=True)],
                    lg=2, md=4, sm=6, xs=12, className="control-element-spacing"),
            dbc.Col([dbc.Label("DTE:", html_for=ids.ID_DTE_INPUT, className="fw-bold control-label-main"),
                     dbc.Input(id=ids.ID_DTE_INPUT, type="text", value=str(default_dte), placeholder="e.g., 0 or 0-7", className="mb-2 form-control-sm input-main-controls", size="sm", debounce=True)],
                    lg=2, md=4, sm=6, xs=12, className="control-element-spacing"),
            dbc.Col([dbc.Label(f"Strike Range % (+/-): {default_range_pct:.1f}%", id=ids.ID_RANGE_SLIDER_OUTPUT_LABEL, className="fw-bold control-label-main"),
                     dcc.Slider(id=ids.ID_RANGE_SLIDER, min=0.5, max=25, step=0.5, value=default_range_pct, marks=range_slider_marks_cfg,
                                tooltip={"placement": "bottom", "always_visible": False}, className="mb-2 pt-3 slider-main-controls")],
                    lg=3, md=4, sm=12, className="control-element-spacing"),
            dbc.Col([dbc.Label("Auto-Refresh:", html_for=ids.ID_REFRESH_INTERVAL_DROPDOWN, className="fw-bold control-label-main"),
                     dbc.Select(id=ids.ID_REFRESH_INTERVAL_DROPDOWN, options=refresh_options_cfg, value=default_refresh_ms,
                                className="mb-2 form-select-sm select-main-controls", size="sm")],
                    lg=2, md=6, sm=6, xs=12, className="control-element-spacing"),
            dbc.Col([dbc.Button("Fetch Market Data", id=ids.ID_FETCH_DATA_BUTTON, color="primary", n_clicks=0, className="w-100 mt-md-4 mt-sm-2 btn-main-controls", size="md")],
                    lg=3, md=6, sm=6, xs=12, className="d-flex align-items-md-end control-element-spacing"), # Align button better on md+
        ], className="g-2 align-items-stretch p-3 control-row-main"),
        body=False, className="mb-3 shadow-lg control-panel-card-main", style=STYLE_CONTROL_BOX_CARD if _layout_dependencies_imported_ok else {}
    )

    status_display_area = dbc.Row(
        dbc.Col(html.Div(id=ids.ID_STATUS_DISPLAY_AREA, className="p-2 text-center rounded status-bar-default-empty", style=STYLE_STATUS_DISPLAY if _layout_dependencies_imported_ok else {}), width=12),
        className="mb-3 status-display-row",
    )

    mode_tabs_definition = [
        dbc.Tab(label="Main Dashboard", tab_id=ids.ID_TAB_MAIN_DASHBOARD, className="fw-bold custom-tab", active_label_class_name="active-tab-label", tab_style={"padding": "10px 15px"}, active_tab_style={"backgroundColor": "#007bff", "color": "white", "borderBottom": "3px solid #0056b3"}),
        dbc.Tab(label="sDAG Diagnostics", tab_id=ids.ID_TAB_SDAG_DIAGNOSTICS, className="fw-bold custom-tab", active_label_class_name="active-tab-label", tab_style={"padding": "10px 15px"}, active_tab_style={"backgroundColor": "#007bff", "color": "white", "borderBottom": "3px solid #0056b3"}),
        dbc.Tab(label="Enhanced Flow", tab_id=ids.ID_TAB_ENHANCED_FLOW, className="fw-bold custom-tab", active_label_class_name="active-tab-label", tab_style={"padding": "10px 15px"}, active_tab_style={"backgroundColor": "#007bff", "color": "white", "borderBottom": "3px solid #0056b3"}),
        dbc.Tab(label="Volatility Deep Dive", tab_id=ids.ID_TAB_VOLATILITY_DEEP_DIVE, className="fw-bold custom-tab", active_label_class_name="active-tab-label", tab_style={"padding": "10px 15px"}, active_tab_style={"backgroundColor": "#007bff", "color": "white", "borderBottom": "3px solid #0056b3"}),
        dbc.Tab(label="Performance", tab_id=ids.ID_TAB_PERFORMANCE, className="fw-bold custom-tab", active_label_class_name="active-tab-label", tab_style={"padding": "10px 15px"}, active_tab_style={"backgroundColor": "#007bff", "color": "white", "borderBottom": "3px solid #0056b3"}),
    ]
    mode_selector_component = dbc.Tabs(mode_tabs_definition, id=ids.ID_MODE_SELECTOR_TABS, active_tab=ids.ID_TAB_MAIN_DASHBOARD, className="mb-3 custom-nav-tabs nav-justified")

    # Main Application Container
    application_layout = dbc.Container(
        [
            dcc.Store(id=ids.ID_MAIN_DATA_STORE_MEMORY, storage_type='memory'),
            # Data for ID_APP_CONFIG_STORE is now populated by APP_CONFIG from enhanced_dashboard_v2.py
            dcc.Store(id=ids.ID_APP_CONFIG_STORE, storage_type='memory', data={}),
            dcc.Store(id=ids.ID_CURRENT_MODE_STORE, storage_type='memory', data={'active_mode': ids.ID_TAB_MAIN_DASHBOARD}),
            dcc.Store(id=ids.ID_REFRESH_INTERVAL_STORE, storage_type='memory', data={'interval_ms': default_refresh_ms}),

            dcc.Interval(
                id=ids.ID_AUTO_REFRESH_INTERVAL_COMPONENT,
                interval=max(1000, int(default_refresh_ms)) if default_refresh_ms > 0 else (24 * 60 * 60 * 1000), # Ensure interval is at least 1s if enabled
                n_intervals=0,
                disabled=(default_refresh_ms <= 0),
            ),
            html.Div(id=ids.ID_HIDDEN_INITIAL_LOAD_TRIGGER, style={'display': 'none'}, children="trigger_initial_load_on_startup_v19_2"),

            html.H1(dashboard_title, className="my-4 text-center display-4 dashboard-main-title", style=STYLE_H1_TITLE if _layout_dependencies_imported_ok else {}),
            control_panel,
            status_display_area,
            html.Div(id=ids.ID_ALERT_CONTAINER, className="alert-container-main fixed-top-alerts"), # Added class for potential fixed positioning of alerts
            
            mode_selector_component,
            html.Div(id=ids.ID_MAIN_CONTENT_AREA, className="mt-3 mode-content-wrapper", children=[get_main_dashboard_mode_layout()]),
            
            dcc.Loading(
                id=ids.ID_OVERLAY_LOADING,
                type="circle",
                fullscreen=True,
                children=[html.Div(id="dummy-loading-child-for-spinner")], # Essential: dcc.Loading needs children
                style=STYLE_LOADING_WRAPPER if _layout_dependencies_imported_ok else {},
                color="#007BFF",
                overlay_style={"backgroundColor": "rgba(40, 40, 40, 0.8)"}
            ),
            
            html.Footer(
                dbc.Container(html.Small(footer_text_cfg), className="text-center text-muted py-4 footer-content"),
                className="mt-auto app-main-footer pt-4 pb-2 border-top"
            )
        ],
        fluid=True,
        className="dbc dashboard-container-fluid app-wrapper-main-class",
        style=STYLE_APP_WRAPPER if _layout_dependencies_imported_ok else {}
    )
    layout_main_logger.info("Overall application layout generated successfully (V19.2 Robust).")
    return application_layout

