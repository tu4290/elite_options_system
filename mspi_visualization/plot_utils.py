# plot_utils.py
"""
Utility functions for creating and manipulating plots for the MSPIVisualizer.
Version: PlotUtils-Canon-V1.0.1 - Signature alignment with mspi_visualizer
"""

import os
import logging
from datetime import datetime, date # Added date
from typing import Dict, Any, Optional, List, Tuple, Union

import pandas as pd
import numpy as np # Ensure numpy is imported
import plotly.graph_objects as go
from dateutil import parser as date_parser
import plotly.colors

# Module-level logger (can be configured by the main application)
logger = logging.getLogger(__name__)
logger.info("plot_utils.py (PlotUtils-Canon-V1.0.1): Module initialized.")


def _create_empty_figure(
    instance_logger: logging.Logger,
    default_chart_height: int,
    plotly_template: str,
    reason_for_empty: Optional[str] = None # Added optional reason for title
) -> go.Figure:
    """Creates an empty Plotly figure with a placeholder message."""
    log = instance_logger.getChild("_create_empty_figure")
    log.info(f"Creating an empty figure. Reason: {reason_for_empty or 'Not specified'}")
    fig = go.Figure()

    title_text = "No Data Available or Error in Plotting"
    if reason_for_empty:
        title_text = f"{reason_for_empty}" # Use the specific reason if provided

    fig.update_layout(
        height=int(default_chart_height) if default_chart_height and default_chart_height > 0 else 600,
        title_text=title_text,
        xaxis_title="Strike / Category", # More generic
        yaxis_title="Value / Metric",    # More generic
        template=plotly_template if plotly_template else "plotly_dark", # Fallback template
        annotations=[
            dict(
                text="No data to display or an error occurred during plot generation.",
                xref="paper",
                yref="paper",
                showarrow=False,
                font=dict(size=16)
            )
        ]
    )
    return fig

def _format_hover_value(value: Any, value_type: str = "generic", precision: int = 2) -> str:
    """
    Formats a value for hover tooltips based on its type.
    Added precision for numeric types.
    """
    if pd.isna(value) or value is None:
        return "N/A"

    try:
        if value_type == "price":
            return f"${float(value):,.{precision}f}"
        if value_type == "percentage":
            return f"{float(value):.{precision}%}"
        if value_type == "volume":
            return f"{int(value):,d}"
        if value_type == "date":
            if isinstance(value, str):
                try: value = date_parser.parse(value)
                except Exception: return str(value)
            if isinstance(value, (datetime, pd.Timestamp)): # pd.Timestamp for pandas datetimes
                return value.strftime('%Y-%m-%d %H:%M:%S')
            elif isinstance(value, date): # Handle date objects
                return value.strftime('%Y-%m-%d')
            return str(value)
        if isinstance(value, (float, np.floating)):
            return f"{float(value):,.{precision}f}"
        if isinstance(value, (int, np.integer)):
            return f"{int(value):,d}"
        return str(value)
    except (ValueError, TypeError) as e_format:
        logger.warning(f"Error formatting hover value '{value}' as type '{value_type}': {e_format}")
        return str(value) # Fallback to string representation


def _add_timestamp_annotation(fig: go.Figure, instance_logger: logging.Logger, timestamp_config: Optional[Dict[str, Any]] = None) -> None:
    """Adds a timestamp annotation to the figure based on configuration."""
    log = instance_logger.getChild("_add_timestamp_annotation")
    cfg = timestamp_config or {} # Use empty dict if None
    
    if not cfg.get("enabled", True): # Default to enabled if not specified
        log.debug("Timestamp annotation disabled in config.")
        return

    try:
        # Use current UTC time for consistency, or allow configuration for local time
        now_dt = datetime.utcnow() if cfg.get("use_utc_time", False) else datetime.now()
        timestamp_str = now_dt.strftime(cfg.get("format", "%Y-%m-%d %H:%M:%S %Z")) 
        
        # Adjust y position intelligently
        # If x-axis title is present, default y is lower; otherwise, it's higher (closer to plot).
        # A more robust check might be to see if fig.layout.xaxis.title.text is not None and not empty.
        default_y_pos = -0.12 # Default if x-axis title is likely present
        if fig.layout and fig.layout.xaxis and (not fig.layout.xaxis.title or not fig.layout.xaxis.title.text):
            default_y_pos = 0.01 # Closer to plot if no x-axis title or it's empty
        
        y_pos_final = float(cfg.get("position_y", default_y_pos))

        fig.add_annotation(
            text=f"Generated: {timestamp_str}",
            align=str(cfg.get("align", "left")),
            showarrow=False,
            xref='paper',
            yref='paper',
            x=float(cfg.get("position_x", 0.99 if str(cfg.get("xanchor", "right")).lower() == "right" else 0.01)), 
            y=y_pos_final,
            xanchor=str(cfg.get("xanchor", "right")),
            yanchor=str(cfg.get("yanchor", "top" if y_pos_final < 0 else "bottom")),
            font=dict(
                size=int(cfg.get("font_size", 10)),
                color=str(cfg.get("font_color", "grey"))
            ),
            name="timestamp_annotation_plot_utils" # Consistent name
        )
        log.debug(f"Added timestamp annotation to figure at x={fig.layout.annotations[-1].x}, y={fig.layout.annotations[-1].y}")
    except Exception as e:
        log.error(f"Error adding timestamp annotation: {e}", exc_info=True)


def _add_price_line(
    fig: go.Figure,
    price_value: Union[float, int], # Changed from y_value for clarity
    line_color: str,
    line_width: int,
    line_dash: str,
    label_text: Optional[str] = None, # Changed from label
    annotation_position: str = "bottom right", # Added for flexibility
    instance_logger: Optional[logging.Logger] = None 
) -> None:
    """Adds a horizontal line to the figure, typically for price levels."""
    log = (instance_logger or logger).getChild("_add_price_line") 

    if not pd.notna(price_value):
        log.debug(f"Skipping price line for label '{label_text}': price_value is NaN or None.")
        return

    log.debug(f"Adding price line for '{label_text if label_text else 'unlabeled line'}' at y={price_value}")
    try:
        fig.add_hline(
            y=float(price_value),
            line_color=str(line_color),
            line_width=int(line_width),
            line_dash=str(line_dash),
            annotation_text=str(label_text) if label_text else None,
            annotation_position=str(annotation_position), 
            annotation_font_size=10, # Consider making configurable
            annotation_font_color=str(line_color) # Match line color by default
        )
    except Exception as e:
        log.error(f"Error adding price line for '{label_text}': {e}", exc_info=True)

def _save_figure(
    fig: go.Figure,
    filename_prefix: str,
    output_dir_config: str, 
    save_html_config: bool,
    save_png_config: bool,
    instance_logger: logging.Logger,
    width: Optional[int] = None,
    height: Optional[int] = None,
    png_scale: int = 2 
) -> None:
    """Saves the figure to HTML and/or PNG if configured."""
    log = instance_logger.getChild("_save_figure")

    if not (save_html_config or save_png_config):
        log.debug("Chart saving (HTML/PNG) is disabled.")
        return

    if not output_dir_config or not isinstance(output_dir_config, str):
        log.error(f"Invalid output directory '{output_dir_config}' provided for saving charts. Skipping save.")
        return

    try:
        abs_output_dir = os.path.abspath(output_dir_config)
        if not os.path.exists(abs_output_dir):
            os.makedirs(abs_output_dir)
            log.info(f"Created output directory for charts: {abs_output_dir}")
    except OSError as e_dir:
        log.error(f"Error creating output directory '{abs_output_dir}': {e_dir}. Chart saving might fail.")
        return 

    base_filepath = os.path.join(abs_output_dir, str(filename_prefix).replace(" ", "_").replace(":", "-"))

    if save_html_config:
        html_filepath = f"{base_filepath}.html"
        try:
            fig.write_html(html_filepath, full_html=True, include_plotlyjs='cdn')
            log.info(f"Figure saved as HTML: {html_filepath}")
        except Exception as e_html:
            log.error(f"Error saving figure as HTML to '{html_filepath}': {e_html}", exc_info=True)

    if save_png_config:
        png_filepath = f"{base_filepath}.png"
        try:
            fig_layout = fig.layout
            effective_width = width if isinstance(width, int) and width > 0 else (fig_layout.width if fig_layout and fig_layout.width else 1200)
            effective_height = height if isinstance(height, int) and height > 0 else (fig_layout.height if fig_layout and fig_layout.height else 700)
            
            fig.write_image(png_filepath, width=effective_width, height=effective_height, scale=int(png_scale) if png_scale > 0 else 1)
            log.info(f"Figure saved as PNG: {png_filepath} (w:{effective_width}, h:{effective_height}, scale:{png_scale})")
        except Exception as e_png:
            log.error(f"Error saving figure as PNG to '{png_filepath}': {e_png}. Ensure Kaleido is installed ('pip install -U kaleido').", exc_info=True)


def _parse_color_string(
    color_string: str,
    alpha: float = 1.0,
    instance_logger: Optional[logging.Logger] = None
) -> str:
    """
    Parses a color string (hex, rgb, or named) and applies alpha transparency.
    Returns an rgba string. More robust parsing.
    """
    log = (instance_logger or logger).getChild("_parse_color_string")
    
    if not isinstance(color_string, str):
        log.warning(f"Invalid color_string type ({type(color_string)}), expected str. Defaulting to black.")
        return f"rgba(0,0,0,{np.clip(alpha, 0.0, 1.0)})"
    
    alpha = np.clip(alpha, 0.0, 1.0) 

    try:
        if color_string.startswith('rgba('):
            parts = color_string[5:-1].split(',')
            if len(parts) == 4:
                r, g, b = map(int, parts[:3])
                return f"rgba({r},{g},{b},{alpha})" 
        elif color_string.startswith('rgb('):
            parts = color_string[4:-1].split(',')
            if len(parts) == 3:
                r, g, b = map(int, parts)
                return f"rgba({r},{g},{b},{alpha})"

        if color_string.startswith('#'):
            rgb_tuple = plotly.colors.hex_to_rgb(color_string)
            return f"rgba({rgb_tuple[0]},{rgb_tuple[1]},{rgb_tuple[2]},{alpha})"

        try:
            validated_color_hex = plotly.colors.validate_colors([color_string.lower()], colortype='hex')
            if validated_color_hex and isinstance(validated_color_hex, (list, tuple)) and validated_color_hex[0].startswith('#'):
                rgb_tuple_named = plotly.colors.hex_to_rgb(validated_color_hex[0])
                return f"rgba({rgb_tuple_named[0]},{rgb_tuple_named[1]},{rgb_tuple_named[2]},{alpha})"
        except Exception: 
            pass 

        log.warning(f"Could not parse color string '{color_string}' through standard methods. Defaulting to black with alpha.")
        return f"rgba(0,0,0,{alpha})"
        
    except Exception as e_parse:
        log.error(f"Error parsing color string '{color_string}': {e_parse}. Defaulting to black with alpha.", exc_info=True)
        return f"rgba(0,0,0,{alpha})"


def _ensure_columns(
    df: pd.DataFrame,
    required_columns: List[str],
    instance_logger: logging.Logger # Changed from bool return to match the 3-arg error
) -> Tuple[pd.DataFrame, bool]: # Returns DataFrame and success boolean
    """
    Checks if all required columns are present in the DataFrame.
    This version logs warnings but does NOT add columns or coerce types.
    It returns the original DataFrame and a boolean indicating if all required columns were found.
    """
    log = instance_logger.getChild("_ensure_columns_plot_utils") 
    
    if not isinstance(df, pd.DataFrame):
        log.error("Invalid input: df is not a pandas DataFrame. Ensure_columns check failed.")
        return df, False 

    missing_cols = [col for col in required_columns if col not in df.columns]
    if missing_cols:
        log.warning(f"DataFrame is missing required columns for plotting: {missing_cols}. Current columns: {df.columns.tolist()}")
        return df, False 
    
    return df, True 

def _check_hover_enabled(hover_settings_config: Dict[str, Any], hover_section_key: str) -> bool:
    """
    Checks if a specific hover section or feature is enabled based on configuration.
    """
    if not isinstance(hover_settings_config, dict):
        return False 

    chart_specific = hover_settings_config.get("chart_specific_hover", {})
    if isinstance(chart_specific, dict):
        section_config = chart_specific.get(hover_section_key)
        if isinstance(section_config, dict) and "enabled" in section_config:
            return bool(section_config["enabled"])
        elif isinstance(section_config, bool): 
            return section_config

    # Defaulting to True if not explicitly disabled, or if key implies a generally desired hover.
    # This is a heuristic; more explicit 'enabled' flags in config are better.
    if hover_section_key in ["base_info", "mspi_value", "core_indices", "net_pressures", "overview_metrics",
                             "key_levels_mspi_line", "key_level_marker", "signals_chart_base_line", "trading_signal_marker",
                             "mspi_heatmap_cell", "net_value_cell", "net_volume_cell", "raw_greek_call", "raw_greek_put",
                             "default_bar", "default_line", "default_area"]: # Added common internal keys
        return True 
    
    # Check for a global default toggle if present in hover_settings_config (e.g., for a category)
    # Example: hover_settings_config.get(f"show_{hover_section_key}_default", False)
    # This part would require knowing the structure of such default toggles.

    return False 


def _create_hover_text(
    row_data: pd.Series, 
    chart_type_hover_key: str, 
    hover_settings_config: Dict[str, Any],
    column_names_config: Dict[str, str], 
    instance_logger: logging.Logger,
    extra_context: Optional[Dict[str, Any]] = None 
) -> str:
    """
    Generates customized HTML hover text for a data point.
    Relies on hover_settings_config for structure and fields.
    """
    log = instance_logger.getChild("_create_hover_text")
    if not isinstance(row_data, pd.Series):
        log.error(f"Invalid row_data (type: {type(row_data)}) for hover text. Expected pd.Series.")
        return "Error: Invalid data for hover.<extra></extra>"
    if not isinstance(hover_settings_config, dict):
        log.warning("hover_settings_config is not a dict. Using minimal hover.")
        hover_settings_config = {} 

    hover_parts: List[str] = []

    chart_specific_hover_cfg_main = hover_settings_config.get("chart_specific_hover", {})
    specific_hover_rules = chart_specific_hover_cfg_main.get(chart_type_hover_key, chart_specific_hover_cfg_main.get("default", {}))
    
    sections_to_display: List[str] = specific_hover_rules.get("sections", []) 
    if not sections_to_display and hover_settings_config.get("show_overview_metrics_default", True): # Fallback to generic if no sections defined
        sections_to_display = ['base_info', 'overview_metrics']

    def add_part(label: str, value: Any, value_type_hint: str = "generic", precision: int = 2):
        formatted_val = _format_hover_value(value, value_type_hint, precision)
        if formatted_val != "N/A":
            hover_parts.append(f"<b>{label}:</b> {formatted_val}") # No std_html.escape for value here as _format_hover_value might produce HTML (e.g. price)

    if "base_info" in sections_to_display:
        strike_col = column_names_config.get("strike", "strike") # Use the mapping
        opt_kind_col = column_names_config.get("option_kind", column_names_config.get("option_type", "opt_kind")) # Handle both common keys
        expiration_col = column_names_config.get("expiration_date", column_names_config.get("expiry_date", "expiration_date"))
        
        # Common base fields: Strike, Option Type, Expiration
        if strike_col in row_data: add_part("Strike", row_data.get(strike_col), "price")
        if opt_kind_col in row_data: add_part("Type", str(row_data.get(opt_kind_col)).title())
        if expiration_col in row_data: add_part("Expiry", row_data.get(expiration_col), "date")
        
        # Add symbol if it's a specific chart type (like a heatmap cell where symbol context is useful)
        if chart_type_hover_key in ["mspi_heatmap_cell", "net_value_cell", "net_volume_cell", "net_greek_flow_heatmap_cell"]:
            if "underlying_symbol" in row_data: add_part("Symbol", str(row_data.get("underlying_symbol")))
            elif "Symbol" in (extra_context or {}): add_part("Symbol", str((extra_context or {}).get("Symbol")))


    if "overview_metrics" in sections_to_display or "core_indices" in sections_to_display or "net_pressures" in sections_to_display or "selected_greek_flow" in sections_to_display:
        overview_metrics_list = hover_settings_config.get("overview_metrics_config", [])
        # Determine which keys to actually plot based on specific_hover_rules if provided
        keys_to_plot_in_section = set()
        if "core_indices" in sections_to_display: keys_to_plot_in_section.update(specific_hover_rules.get("core_indices_keys", []))
        if "net_pressures" in sections_to_display: keys_to_plot_in_section.update(specific_hover_rules.get("net_pressure_keys", ['net_value_pressure', 'net_volume_pressure'])) # Example defaults
        if "selected_greek_flow" in sections_to_display: keys_to_plot_in_section.update(specific_hover_rules.get("selected_greek_keys", [])) # E.g., from greek_flow_heatmap_options value


        for metric_cfg in overview_metrics_list:
            if isinstance(metric_cfg, dict):
                key = metric_cfg.get("key")
                label = metric_cfg.get("label", key.replace("_"," ").title() if key else "N/A")
                precision = metric_cfg.get("precision", 2)
                is_currency = metric_cfg.get("is_currency", False)
                value_type = "price" if is_currency else "generic"
                
                # If a specific set of keys is defined for the section, only plot those. Otherwise, plot all from overview_metrics_config.
                should_plot_this_metric = True
                if keys_to_plot_in_section: # If specific keys are defined for this hover section type
                    should_plot_this_metric = (key in keys_to_plot_in_section)
                
                if key and key in row_data and should_plot_this_metric:
                    add_part(label, row_data.get(key), value_type, precision)
    
    # Specific section for the primary value of a heatmap cell if not covered by overview
    if "mspi_value" in sections_to_display:
        mspi_col_mapped = column_names_config.get("mspi", column_names_config.get("mspi_score", "mspi"))
        if mspi_col_mapped in row_data: add_part("MSPI", row_data.get(mspi_col_mapped), "generic", 3)

    if "sdag_specific_value" in sections_to_display: # For individual SDAG charts
        # The 'metric_col' or 'output_column_name' used to plot this SDAG chart.
        # This needs to be passed via extra_context perhaps, e.g., extra_context={"metric_name": "sdag_multiplicative_norm", "metric_label": "SDAG(M)"}
        metric_name = (extra_context or {}).get("metric_name")
        metric_label = (extra_context or {}).get("metric_label", metric_name.replace("_", " ").title() if metric_name else "SDAG Score")
        if metric_name and metric_name in row_data:
            add_part(metric_label, row_data.get(metric_name), "generic", 3)
            
    # Similar specific sections for tdpi_specific_values, vri_specific_values etc. would follow the same pattern.

    if "details_section" in sections_to_display:
        details_keys_list = hover_settings_config.get("details_section_keys", [])
        for detail_key_str in details_keys_list:
            if detail_key_str in row_data and pd.notna(row_data.get(detail_key_str)):
                label_for_detail = str(detail_key_str).replace("_"," ").title()
                value_for_detail = str(row_data.get(detail_key_str))
                if len(value_for_detail) > 70: value_for_detail = value_for_detail[:67] + "..." # Truncate long details
                add_part(label_for_detail, value_for_detail)

    if extra_context and isinstance(extra_context, dict):
        # Avoid re-adding Symbol if already handled by base_info for specific chart types
        keys_to_skip_from_extra = set()
        if "base_info" in sections_to_display and chart_type_hover_key in ["mspi_heatmap_cell", "net_value_cell", "net_volume_cell", "net_greek_flow_heatmap_cell"]:
             keys_to_skip_from_extra.add("Symbol")

        for label_extra, value_extra in extra_context.items():
            if label_extra not in keys_to_skip_from_extra:
                add_part(str(label_extra), value_extra) # Assume generic formatting

    if not hover_parts: # Minimal hover if no specific parts were added
        strike_col_disp = column_names_config.get("strike", "strike")
        if strike_col_disp in row_data:
            return f"<b>Strike:</b> {_format_hover_value(row_data.get(strike_col_disp), 'price')}<extra></extra>"
        return "No hover data<extra></extra>"

    return "<br>".join(hover_parts) + "<extra></extra>"