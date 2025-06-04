# /home/ubuntu/dashboard_v2/styling.py
# -*- coding: utf-8 -*-
"""
Styling constants, theme definitions, and content blurbs for the Enhanced Options Dashboard V2.
(Version: Styling v2.2 - Corrected Typing Import and Self-Contained Blurbs)
"""
import logging # Added for potential logging if fallbacks are extensive
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from typing import Dict, Any, Union, List, Optional, Tuple, Callable, Deque # <<< ENSURED Union IS HERE

logger_styling = logging.getLogger(__name__) # Logger for this module

# --- Theme ---
APP_THEME: str = dbc.themes.CYBORG # Or DARKLY, VAPOR, etc. You can choose.

# --- Plotly Figure Templates/Layouts ---
PLOTLY_TEMPLATE_DARK: Dict[str, Any] = {
    "layout": go.Layout(
        template="plotly_dark",
        font=dict(family="'Segoe UI', Arial, sans-serif", size=12, color="#f0f0f0"),
        title_font_size=18,
        paper_bgcolor="rgba(0,0,0,0)", # Transparent background for cards
        plot_bgcolor="rgba(0,0,0,0)",  # Transparent plot area
        xaxis=dict(
            gridcolor="#444444",
            linecolor="#555555",
            zerolinecolor="#666666",
            showgrid=True,
            gridwidth=1,
            title_font_color="#aaaaaa",
            tickfont_color="#aaaaaa"
        ),
        yaxis=dict(
            gridcolor="#444444",
            linecolor="#555555",
            zerolinecolor="#666666",
            showgrid=True,
            gridwidth=1,
            title_font_color="#aaaaaa",
            tickfont_color="#aaaaaa"
        ),
        legend=dict(
            bgcolor="rgba(40,40,40,0.85)",
            bordercolor="#555555",
            borderwidth=1,
            font_color="#f0f0f0",
            itemsizing='constant',
            orientation='h',
            yanchor='bottom',
            y=1.02,
            xanchor='right',
            x=1
        ),
        margin=dict(l=50, r=50, t=80, b=50)
    )
}

# --- General Styles ---
STYLE_APP_WRAPPER: Dict[str, str] = {
    "backgroundColor": "#1E2021",
    "color": "#EAEAEA",
    "padding": "15px",
    "fontFamily": "'Roboto', 'Segoe UI', Arial, sans-serif",
    "minHeight": "100vh"
}

STYLE_H1_TITLE: Dict[str, str] = {
    "textAlign": "center",
    "color": "#FFFFFF",
    "marginBottom": "25px",
    "fontSize": "2.2em",
    "fontWeight": "700",
    "letterSpacing": "1px",
    "textShadow": "1px 1px 3px rgba(0,0,0,0.7)"
}

STYLE_FOOTER: Dict[str, str] = {
    "marginTop": "40px",
    "paddingTop": "15px",
    "borderTop": "1px solid #333",
    "textAlign": "center",
    "fontSize": "0.85em",
    "color": "#888888"
}

# --- Control Panel Styles ---
STYLE_CONTROL_PANEL_WRAPPER: Dict[str, str] = {
    "width": "100%",
    "maxWidth": "1400px",
    "margin": "0 auto 25px auto",
}

STYLE_CONTROL_BOX_CARD: Dict[str, str] = {
    "padding": "15px 20px",
    "backgroundColor": "#2B2E30",
    "borderRadius": "6px",
    "border": "1px solid #3A3F42",
    "boxShadow": "0 4px 10px rgba(0,0,0,0.3)"
}

STYLE_CONTROL_ROW: Dict[str, str] = {
    "marginBottom": "15px",
    "alignItems": "flex-end"
}

STYLE_LABEL: Dict[str, str] = {
    "display": "block",
    "marginBottom": "6px",
    "fontWeight": "500",
    "color": "#C5C8C6",
    "fontSize": "0.9rem"
}

STYLE_INPUT: Dict[str, str] = {
    "width": "100%",
    "padding": "8px 12px",
    "borderRadius": "4px",
    "border": "1px solid #4A4E52",
    "backgroundColor": "#33373A",
    "color": "#F0F0F0",
    "fontSize": "0.9rem"
}

STYLE_BUTTON_PRIMARY: Dict[str, str] = {
    "width": "100%",
    "padding": "10px",
    "fontSize": "1rem",
    "fontWeight": "600",
}

STYLE_STATUS_DISPLAY: Dict[str, str] = {
    "marginTop": "10px",
    "textAlign": "center",
    "minHeight": "38px",
    "padding": "8px",
    "borderRadius": "4px",
    "fontSize": "0.9rem",
    "fontWeight": "500",
    "transition": "background-color 0.3s ease, color 0.3s ease"
}

# --- Chart Styles ---
STYLE_CHART_ROW: Dict[str, str] = {
    "marginBottom": "25px",
}

STYLE_CHART_CARD: Dict[str, str] = {
    "backgroundColor": "#2B2E30",
    "padding": "15px",
    "borderRadius": "6px",
    "border": "1px solid #3A3F42",
    "height": "100%",
    "boxShadow": "0 3px 7px rgba(0,0,0,0.25)"
}

STYLE_CHART_TITLE_CONTAINER: Dict[str, str] = {
    "display": "flex",
    "justifyContent": "space-between",
    "alignItems": "center",
    "marginBottom": "8px"
}

STYLE_CHART_TITLE: Dict[str, str] = {
    "color": "#D0D0D0",
    "fontSize": "1.1em",
    "fontWeight": "600",
}

STYLE_INFO_ICON: Dict[str, str] = {
    "cursor": "pointer",
    "color": "#4A90E2",
    "fontSize": "1rem"
}

STYLE_LOADING_WRAPPER: Dict[str, str] = {
    "minHeight": "350px",
    "display": "flex",
    "alignItems": "center",
    "justifyContent": "center",
    "backgroundColor": "rgba(43,46,48,0.7)",
    "borderRadius": "6px"
}

STYLE_TOOLTIP: Dict[str, str] = {
    "position": "absolute",
    "padding": "6px 10px",
    "backgroundColor": "#181A1B",
    "border": "1px solid #007bff",
    "borderRadius": "3px",
    "color": "#E0E0E0",
    "fontSize": "0.85em",
    "boxShadow": "0px 2px 8px rgba(0,123,255,0.4)",
    "pointerEvents": "none",
    "zIndex": "10000"
}

# --- Chart Configuration: Blurbs ---
# Keys are string literals corresponding to chart IDs used in layout.py and callbacks.py
ENHANCED_BLURBS: Dict[str, str] = {
    "mspi-heatmap-chart": """<div class="metric-blurb"><h6>MSPI View</h6><p class="small text-muted mb-0">Displays the MSPI values across strikes and option types (Call/Put), or other selected views like Net Volume Pressure.</p></div>""",
    "net-value-heatmap-chart": """<div class="metric-blurb"><h6>Net Value Pressure (H)</h6><p class="small text-muted mb-0">Shows heuristic net value pressure at each strike.</p></div>""",
    "net-volume-pressure-heatmap-chart": """<div class="metric-blurb"><h6>Net Volume Pressure (H)</h6><p class="small text-muted mb-0">Shows heuristic net volume pressure at each strike.</p></div>""",
    "mspi-components-chart": """<div class="metric-blurb"><h6>MSPI Components Breakdown</h6><p class="small text-muted mb-0">Deconstructs the total MSPI score into its underlying normalized strategy components (e.g., DAG, TDPI, VRI, SDAG variants), aiding in understanding the drivers of overall pressure.</p></div>""",
    "net-greek-flow-heatmap-chart": """<div class="metric-blurb"><h6>Net Greek Flow & Pressure</h6><p class="small text-muted mb-0">Visualizes selected Net Greek flow (e.g., Delta, Gamma) or heuristic pressure across strikes. Use the dropdown to change the viewed metric.</p></div>""", # Note: The ID used by callbacks for the graph component itself is ID_NET_GREEK_FLOW_HEATMAP_CHART_CB
    "combined-rolling-flow-chart": """<div class="metric-blurb"><h6>Combined Rolling Net Flow</h6><p class="small text-muted mb-0">Presents rolling net flow metrics over different time intervals (e.g., 5m, 15m, 30m, 60m). Bars and areas typically represent different aspects of flow, like volume vs. value, normalized for comparison.</p></div>""",
    "volatility-regime-chart": """<div class="metric-blurb"><h6>Volatility Regime Indicator (VRI / VRI 2.0)</h6><p class="small text-muted mb-0">Assesses the current volatility environment by strike. Positive values may suggest volatility expansion, negative values contraction.</p></div>""",
    "time-decay-chart": """<div class="metric-blurb"><h6>Time Decay Pressure (TDPI / D-TDPI)</h6><p class="small text-muted mb-0">Highlights strikes most sensitive to time decay (theta), particularly relevant for 0DTE or near-expiration options.</p></div>""",
    "sdag-multiplicative-chart": """<div class="metric-blurb"><h6>SDAG - Multiplicative</h6><p class="small text-muted mb-0">Skew-adjusted Gamma exposure, multiplicatively adjusted by Delta exposure.</p></div>""",
    "sdag-directional-chart": """<div class="metric-blurb"><h6>SDAG - Directional</h6><p class="small text-muted mb-0">Skew-adjusted Gamma exposure, directionally influenced by Delta exposure.</p></div>""",
    "sdag-weighted-chart": """<div class="metric-blurb"><h6>SDAG - Weighted</h6><p class="small text-muted mb-0">Weighted average of Skew-adjusted Gamma and Delta exposures.</p></div>""",
    "sdag-volatility-focused-chart": """<div class="metric-blurb"><h6>SDAG - Volatility Focused</h6><p class="small text-muted mb-0">Skew-adjusted Gamma, adjusted by Delta relative to Gamma's own sign.</p></div>""",
    "key-levels-chart": """<div class="metric-blurb"><h6>Key Market Levels</h6><p class="small text-muted mb-0">Identifies and scores potential support, resistance, and other significant price levels derived from MSPI metrics and historical price action.</p></div>""",
    "trading-signals-chart": """<div class="metric-blurb"><h6>Generated Trading Signals</h6><p class="small text-muted mb-0">Visualizes specific trading signals triggered by the system's analysis across various categories (Directional, Volatility, Complex, etc.).</p></div>""",
    "recommendations-table-chart": """<div class="metric-blurb"><h6>Strategy Insights & Recommendations</h6><p class="small text-muted mb-0">Presents potential trade ideas and strategy recommendations based on the confluence of signals, levels, and overall market context.</p></div>"""
}
# Important Note on ENHANCED_BLURBS keys:
# The keys here are string literals (e.g., "mspi-heatmap-chart").
# When you use this in layout.py or callbacks.py, you will access them like:
# ENHANCED_BLURBS.get(ID_MSPI_HEATMAP_CHART, "Default blurb")
# where ID_MSPI_HEATMAP_CHART is the constant string "mspi-heatmap-chart".
# This avoids styling.py needing to import from layout.py.


# --- Function to apply card styling (can be imported by layout.py or callbacks.py) ---
def apply_card_styling() -> Dict[str, Union[str, int]]: # Type hint is now valid
    """Returns the standard dictionary for chart card styling."""
    return STYLE_CHART_CARD