{
  "$schema": "./config.schema.json",
  "version": "3.2.5-EliteSchema-FullSystemIntegration-Final",
  "system_settings": {
    "log_level": "INFO",
    "dashboard_debug_mode": false,
    "dashboard_host": "0.0.0.0",
    "dashboard_port": 8050,
    "dashboard_cache_timeout_seconds": 300,
    "data_directory": "processed_market_data",
    "df_history_maxlen": 10,
    "signal_activation": {
      "directional": true,
      "volatility_expansion": true,
      "volatility_contraction": true,
      "time_decay_pin_risk": true,
      "time_decay_charm_cascade": true,
      "complex_structure_change": true,
      "complex_flow_divergence": true,
      "complex_sdag_conviction": true
    }
  },
  "runner_settings": {
    "dashboard_module_path": "dashboard_v2.enhanced_dashboard_v2"
  },
  "api_credentials": {
    "email_env_var": "CONVEX_EMAIL",
    "password_env_var": "CONVEX_PASSWORD",
    "environment": "pro"
  },
  "tradier_api_settings": {
    "base_url": "https://api.tradier.com/v1/",
    "access_token_env_var": "TRADIER_PRODUCTION_TOKEN",
    "access_token_direct": "YOUR_TRADIER_PRODUCTION_TOKEN_PLACEHOLDER",
    "retry_config": {
      "max_retries": 3,
      "base_delay_seconds": 1.0,
      "max_delay_seconds": 10.0,
      "jitter": true
    },
    "ohlcv_num_days_history": 45,
    "iv_approx_target_dte": 5
  },
  "data_fetcher_settings": {
    "api_timeout_seconds": 45,
    "max_retries": 3,
    "base_retry_delay_seconds": 1.5,
    "max_retry_delay_seconds": 15.0,
    "inter_call_delay_seconds": 0.25,
    "volatility_fallback_factor": 0.95,
    "default_dte_range": [0, 1, 2, 3, 7, 14, 21, 30],
    "default_price_range_pct": 0.075,
    "cache_expiry_seconds": {
      "options_data": 45,
      "underlying_data": 120
    }
  },
  "data_processor_settings": {
    "perform_strict_column_validation": true,
    "weights": {
      "selection_logic": "time_based",
      "time_based": {
        "time_based_definitions": {
            "morning_end": "11:00:00",
            "midday_end": "14:00:00",
            "market_open": "09:30:00",
            "market_close": "16:00:00"
        },
        "morning": {
          "dag_custom": 0.30, "tdpi": 0.20, "vri": 0.20,
          "sdag_multiplicative_norm": 0.10, "sdag_weighted_norm": 0.10, "sdag_volatility_focused_norm": 0.10
        },
        "midday": {
          "dag_custom": 0.25, "tdpi": 0.25, "vri": 0.25,
          "sdag_multiplicative_norm": 0.10, "sdag_weighted_norm": 0.10, "sdag_volatility_focused_norm": 0.05
        },
        "final": {
          "dag_custom": 0.20, "tdpi": 0.35, "vri": 0.20,
          "sdag_multiplicative_norm": 0.10, "sdag_weighted_norm": 0.10, "sdag_volatility_focused_norm": 0.05
        }
      },
      "volatility_based": {
        "iv_percentile_threshold": 60,
        "low_iv": {
          "dag_custom": 0.40, "tdpi": 0.25, "vri": 0.15,
          "sdag_multiplicative_norm": 0.10, "sdag_weighted_norm": 0.05, "sdag_volatility_focused_norm": 0.05
        },
        "high_iv": {
          "dag_custom": 0.25, "tdpi": 0.20, "vri": 0.30,
          "sdag_multiplicative_norm": 0.10, "sdag_weighted_norm": 0.10, "sdag_volatility_focused_norm": 0.05
        }
      }
    },
    "coefficients": {
      "dag_alpha": { "aligned": 1.3, "opposed": 0.7, "neutral": 1.0 },
      "tdpi_beta": { "aligned": 1.3, "opposed": 0.7, "neutral": 1.0 },
      "vri_gamma": { "aligned": 1.3, "opposed": 0.7, "neutral": 1.0 }
    },
    "factors": {
      "tdpi_gaussian_width": -0.45,
      "vri_vol_trend_fallback_factor": 0.90
    },
    "approximations": {
      "tdpi_atr_fallback": { "type": "percentage_of_price", "percentage": 0.0075, "min_value": 0.5 }
    },
    "iv_context_parameters": { "iv_percentile": "iv_percentile_30d" }
  },
  "strategy_settings": {
    "gamma_exposure_source_col": "gxoi",
    "delta_exposure_source_col": "dxoi",
    "skew_adjusted_gamma_source_col": "sgxoi",
    "use_skew_adjusted_for_sdag": false,
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
      "sai_high_conviction": { "type": "fixed", "value": 0.65, "fallback_value": 0.65 },
      "ssi_structure_change": { "type": "relative_percentile", "percentile": 20, "fallback_value": 0.25 },
      "ssi_vol_contraction": { "type": "relative_percentile", "percentile": 80, "fallback_value": 0.75 },
      "ssi_conviction_split": { "type": "fixed", "value": 0.25, "fallback_value": 0.25 },
      "cfi_flow_divergence": { "type": "fixed", "tiers": [ 0.80, 1.30 ], "fallback_value": 0.80 },
      "arfi_strong_flow_threshold": {"type": "fixed", "value": 1.6, "fallback_value": 1.6},
      "arfi_low_flow_threshold": {"type": "fixed", "value": 0.4, "fallback_value": 0.4},
      "sdag_vf_strong_negative_threshold": {"type": "fixed", "value": -0.6, "fallback_value": -0.6},
      "vol_expansion_vri_trigger": { "type": "relative_mean_factor", "factor": 1.6, "fallback_value": 0.6 },
      "vol_expansion_vfi_trigger": { "type": "fixed", "value": 1.3, "fallback_value": 1.3 },
      "vol_contraction_vri_trigger": { "type": "relative_mean_factor", "factor": 0.4, "fallback_value": 0.15 },
      "vol_contraction_vfi_trigger": { "type": "fixed", "value": 0.7, "fallback_value": 0.7 },
      "pin_risk_tdpi_trigger": { "type": "relative_mean_factor", "factor": 1.6, "fallback_value": 0.5 },
      "charm_cascade_ctr_trigger": { "type": "fixed", "value": 1.3, "fallback_value": 1.3 },
      "charm_cascade_tdfi_trigger": { "type": "fixed", "value": 1.3, "fallback_value": 1.3 },
      "ssi_exit_stars_threshold": {"type": "fixed", "value": 0.20, "fallback_value": 0.20},
      "arfi_exit_stars_threshold": {"type": "fixed", "value": 1.9, "fallback_value": 1.9}
    },
    "dag_methodologies": {
      "enabled": [ "multiplicative", "directional", "weighted", "volatility_focused" ],
      "multiplicative": { "weight_in_mspi": 0.10, "delta_weight_factor": 0.5 },
      "directional": { "weight_in_mspi": 0.05, "delta_weight_factor": 0.5 },
      "weighted": { "enabled": true, "weight_in_mspi": 0.10, "w1_gamma": 0.6, "w2_delta": 0.4 },
      "volatility_focused": { "enabled": true, "weight_in_mspi": 0.05, "delta_weight_factor": 0.5 },
      "min_agreement_for_conviction_signal": 2
    },
    "sdag_conviction_threshold_pct": 0.70,
    "recommendations": {
        "min_directional_stars_to_issue": 2,
        "min_volatility_stars_to_issue": 2,
        "min_pinrisk_stars_to_issue": 2,
        "min_caution_stars_to_issue": 2,
        "min_reissue_time_seconds": 240,
        "conviction_map_high": 3.8,
        "conviction_map_high_medium": 2.8,
        "conviction_map_medium": 1.8,
        "conviction_map_medium_low": 0.8,
        "conviction_map_base_one_star": 0.4,
        "conv_mod_ssi_low": -1.2,
        "conv_mod_ssi_high": 0.30,
        "conv_mod_vol_expansion": -0.6,
        "conv_mod_sdag_align": 0.80,
        "conv_mod_sdag_oppose": -1.2
    },
    "exits": {
        "contradiction_stars_threshold": 3,
        "ssi_exit_stars_threshold": 2,
        "mspi_flip_threshold": 0.65,
        "arfi_exit_stars_threshold": 3
    },
    "targets": {
        "min_target_atr_distance": 0.70,
        "nvp_support_quantile": 0.88,
        "nvp_resistance_quantile": 0.12,
        "target_atr_stop_loss_multiplier": 1.4,
        "target_atr_target1_multiplier_no_sr": 1.8,
        "target_atr_target2_multiplier_no_sr": 3.2,
        "target_atr_target2_multiplier_from_t1": 1.8
    }
  },
  "visualization_settings": {
    "mspi_visualizer": {
      "log_level": "INFO",
      "output_dir": "mspi_visualizations_output_v2",
      "save_charts_as_html": false,
      "save_charts_as_png": false,
      "default_chart_height": 600,
      "plotly_template": "plotly_dark",
      "plot_order_history": [ "T-5", "T-4", "T-3", "T-2", "T-1", "T-B", "T-A", "Now" ],
      "rolling_intervals": [ "5m", "15m", "30m", "60m" ],
      "min_normalization_denominator": 1e-09,
      "min_value_for_ratio": 1e-06,
      "colorscales": {
        "mspi_heatmap": [ [ 0.0, "rgb(178,24,43)" ], [ 0.5, "rgb(245,245,245)" ], [ 1.0, "rgb(33,102,172)" ] ],
        "net_value_heatmap": [ [ 0.0, "rgb(214,47,39)" ], [ 0.5, "rgb(240,240,240)" ], [ 1.0, "rgb(69,117,180)" ] ],
        "net_delta_heuristic_heatmap": [ [ 0.0, "rgb(200,100,0)" ], [ 0.5, "rgb(240,240,240)" ], [ 1.0, "rgb(0,100,200)" ] ],
        "net_gamma_flow_heatmap": [ [ 0.0, "rgb(180,0,180)" ], [ 0.5, "rgb(240,240,240)" ], [ 1.0, "rgb(0,180,180)" ] ],
        "net_vega_flow_heatmap": [ [ 0.0, "rgb(255,120,0)" ], [ 0.5, "rgb(240,240,240)" ], [ 1.0, "rgb(0,120,255)" ] ],
        "net_theta_exposure_heatmap": [ [ 0.0, "rgb(255,0,0)" ], [ 0.5, "rgb(240,240,240)" ], [ 1.0, "rgb(0,200,0)" ] ],
        "true_net_delta_flow_heatmap": [ [ 0.0, "rgb(220,50,47)" ], [ 0.5, "rgb(235,235,235)" ], [ 1.0, "rgb(33,145,140)" ] ],
        "true_net_volume_flow_heatmap": [ [ 0.0, "rgb(253,174,97)" ], [ 0.5, "rgb(240,240,240)" ], [ 1.0, "rgb(171,221,164)" ] ],
        "true_net_value_flow_heatmap": [ [ 0.0, "rgb(213,62,79)" ], [ 0.5, "rgb(240,240,240)" ], [ 1.0, "rgb(67,147,195)" ] ]
      },
      "key_level_markers": {
        "Support": { "symbol": "triangle-up", "color": "rgb(34,139,34)", "name": "Support" },
        "Resistance": { "symbol": "triangle-down", "color": "rgb(220,20,60)", "name": "Resistance" },
        "High Conviction": { "symbol": "diamond", "color": "rgb(255,215,0)", "name": "High Conviction" },
        "Structure Change": { "symbol": "cross", "color": "rgb(0,191,255)", "name": "Structure Change" }
      },
      "signal_styles": {
        "bullish": { "color": "lime", "symbol": "triangle-up" }, "bearish": { "color": "red", "symbol": "triangle-down" },
        "sdag_bullish": { "color": "gold", "symbol": "diamond-wide" }, "sdag_bearish": { "color": "purple", "symbol": "diamond-wide-dot" },
        "expansion": { "color": "cyan", "symbol": "diamond-open" }, "contraction": { "color": "magenta", "symbol": "square-open" },
        "pin_risk": { "color": "yellow", "symbol": "star" }, "charm_cascade": { "color": "orange", "symbol": "hourglass" },
        "structure_change": { "color": "white", "symbol": "cross-thin" }, "flow_divergence": { "color": "lightblue", "symbol": "x-thin" },
        "default": { "color": "grey", "symbol": "circle" }
      },
      "column_names": {
          "net_volume_pressure": "net_volume_pressure",
          "net_value_pressure": "net_value_pressure",
          "mspi": "mspi", "strike": "strike", "option_kind": "opt_kind",
          "heuristic_net_delta_pressure": "heuristic_net_delta_pressure",
          "net_gamma_flow_at_strike": "net_gamma_flow",
          "net_vega_flow_at_strike": "net_vega_flow",
          "net_theta_exposure_at_strike": "net_theta_exposure",
          "net_delta_flow_total": "net_delta_flow_total",
          "true_net_volume_flow": "true_net_volume_flow",
          "true_net_value_flow": "true_net_value_flow"
      },
      "greek_flow_heatmap_options": [
            {"label": "Net Delta P (Heuristic)", "value": "heuristic_net_delta_pressure"},
            {"label": "Net Gamma Flow", "value": "net_gamma_flow"},
            {"label": "Net Vega Flow", "value": "net_vega_flow"},
            {"label": "Net Theta Exposure", "value": "net_theta_exposure"},
            {"label": "True Net Delta Flow", "value": "net_delta_flow_total"},
            {"label": "True Net Volume Flow", "value": "true_net_volume_flow"},
            {"label": "True Net Value Flow", "value": "true_net_value_flow"}
      ],
      "greek_flow_heatmap_default_metric": "heuristic_net_delta_pressure",
      "hover_settings": {
        "show_overview_metrics_default": true, "show_oi_structure_default": true, "show_details_section_default": true,
        "overview_metrics_config": [
          { "key": "mspi", "label": "MSPI", "precision": 3, "is_currency": false }, { "key": "sai", "label": "SAI", "precision": 3, "is_currency": false },
          { "key": "ssi", "label": "SSI", "precision": 3, "is_currency": false }, { "key": "cfi", "label": "ARFI", "precision": 3, "is_currency": false },
          { "key": "dag_custom", "label": "DAG(C)", "precision": 0, "is_currency": false }, { "key": "tdpi", "label": "TDPI", "precision": 0, "is_currency": false },
          { "key": "vri", "label": "VRI", "precision": 0, "is_currency": false },
          { "key": "sdag_multiplicative", "label": "SDAG(M)", "precision":0, "is_currency": false }, { "key": "sdag_directional", "label": "SDAG(D)", "precision":0, "is_currency": false },
          { "key": "sdag_weighted", "label": "SDAG(W)", "precision":0, "is_currency": false },  { "key": "sdag_volatility_focused", "label": "SDAG(VF)", "precision":0, "is_currency": false },
          { "key": "net_volume_pressure", "label": "Net Vol P (H)", "precision": 0, "is_currency": false }, { "key": "net_value_pressure", "label": "Net Val P (H)", "precision": 0, "is_currency": true },
          { "key": "heuristic_net_delta_pressure", "label": "Net Delta P (H)", "precision": 0, "is_currency": false },
          { "key": "net_gamma_flow_at_strike", "label": "Net Γ Flow", "precision": 0, "is_currency": false },
          { "key": "net_vega_flow_at_strike", "label": "Net ν Flow", "precision": 0, "is_currency": false },
          { "key": "net_theta_exposure_at_strike", "label": "Net θ Exp", "precision": 0, "is_currency": false },
          { "key": "net_delta_flow_total", "label": "True Net Δ Flow", "precision": 0, "is_currency": false },
          { "key": "true_net_volume_flow", "label": "True Net Vol Flow", "precision": 0, "is_currency": false },
          { "key": "true_net_value_flow", "label": "True Net Val Flow", "precision": 0, "is_currency": true }
        ],
        "oi_structure_metrics_config": [
          { "base_key": "dxoi", "label": "DxOI" }, { "base_key": "gxoi", "label": "GxOI" },
          { "base_key": "txoi", "label": "TxOI" }, { "base_key": "vxoi", "label": "VxOI" }
        ],
        "details_section_keys": [ "level_category", "conviction", "strategy", "rationale", "type", "agree_count", "exit_reason", "status_update" ],
        "chart_specific_hover": {
            "default": {"sections": ["base_info", "mspi_value"]},
            "mspi_heatmap": {"sections": ["base_info", "mspi_value", "core_indices"], "core_indices_keys": ["sai", "ssi"]},
            "net_value_heatmap": {"sections": ["base_info", "net_pressures"]},
            "net_greek_flow_heatmap": {"sections": ["base_info", "selected_greek_flow", "overview_metrics"]},
            "mspi_components": {"sections": ["base_info", "overview_metrics", "oi_structure"]},
            "sdag": {"sections": ["base_info", "sdag_specific_value", "core_indices"], "core_indices_keys": ["mspi", "sai"]},
            "sdag_net": {"sections": ["base_info", "sdag_specific_value"]},
            "tdpi": {"sections": ["base_info", "tdpi_specific_values"]},
            "vri": {"sections": ["base_info", "vri_specific_values"]},
            "key_levels": {"sections": ["base_info", "core_metrics_context", "details_section"]},
            "trading_signals": {"sections": ["base_info", "core_metrics_context", "details_section"]}
        }
      },
      "chart_specific_params": {
        "raw_greek_charts_price_range_pct": 7.5,
        "combined_flow_chart_price_range_pct": 12.0,
        "mspi_components_bar_colors": {
            "mspi": { "pos": "darkblue", "neg": "darkred" }, "dag_custom_norm": { "pos": "rgb(255,215,0)", "neg": "rgb(128,0,128)" },
            "tdpi_norm": { "pos": "green", "neg": "red", "is_border": true }, "vri_norm": { "pos": "cyan", "neg": "magenta" },
            "sdag_multiplicative_norm": { "pos": "#FFA07A", "neg": "#6A5ACD" }, "sdag_directional_norm": { "pos": "#FFD700", "neg": "#8A2BE2" },
            "sdag_weighted_norm": { "pos": "#98FB98", "neg": "#FF6347" }, "sdag_volatility_focused_norm": { "pos": "#AFEEEE", "neg": "#DA70D6" }
        },
        "show_net_sdag_trace": true, "net_sdag_trace_default_visibility": "legendonly",
        "net_sdag_marker_style": { "symbol": "diamond", "color": "rgba(255, 255, 255, 0.7)", "size": 8, "line": { "color": "white", "width": 1 } },
        "component_comparison_height": 600, "volval_comparison_height": 600, "key_levels_height": 600, "trading_signals_height": 600, "recommendations_table_height": 650,
        "recommendations_table_column_display_map": {
            "id": "ID", "Category": "Category", "direction_label": "Bias/Type", "strike": "Strike", "strategy": "Strategy / Note",
            "conviction_stars": "Conv★", "raw_conviction_score": "Score", "status": "Status",
            "entry_ideal": "Entry", "target_1": "T1", "target_2": "T2", "stop_loss": "SL",
            "rationale": "Rationale", "target_rationale": "Tgt. Logic",
            "mspi": "MSPI", "sai": "SAI", "ssi": "SSI", "arfi": "ARFI",
            "issued_ts": "Issued", "last_adjusted_ts": "Adjusted", "exit_reason":"Exit Info", "type": "Signal Src", "status_update": "Last Update"
        },
        "combined_rolling_flow_chart_barmode": "overlay",
        "rolling_flow_customization": {
          "5m": {"volume_positive_color": "#2ca02c", "volume_negative_color": "#d62728", "volume_opacity": 0.8, "value_positive_fill_color": "rgba(44,160,44,0.15)", "value_negative_fill_color": "rgba(214,39,40,0.15)", "value_positive_line_color": "rgba(44,160,44,0.6)", "value_negative_line_color": "rgba(214,39,40,0.6)"},
          "15m": {"volume_positive_color": "#98df8a", "volume_negative_color": "#ff9896", "volume_opacity": 0.75, "value_positive_fill_color": "rgba(152,223,138,0.15)", "value_negative_fill_color": "rgba(255,152,150,0.15)", "value_positive_line_color": "rgba(152,223,138,0.55)", "value_negative_line_color": "rgba(255,152,150,0.55)"},
          "30m": {"volume_positive_color": "#1f77b4", "volume_negative_color": "#ff7f0e", "volume_opacity": 0.7, "value_positive_fill_color": "rgba(31,119,180,0.1)", "value_negative_fill_color": "rgba(255,127,14,0.1)", "value_positive_line_color": "rgba(31,119,180,0.5)", "value_negative_line_color": "rgba(255,127,14,0.5)"},
          "60m": {"volume_positive_color": "#aec7e8", "volume_negative_color": "#ffbb78", "volume_opacity": 0.65, "value_positive_fill_color": "rgba(174,199,232,0.1)", "value_negative_fill_color": "rgba(255,187,120,0.1)", "value_positive_line_color": "rgba(174,199,232,0.45)", "value_negative_line_color": "rgba(255,187,120,0.45)"},
           "defaults": {"volume_positive_color": "#cccccc", "volume_negative_color": "#777777", "volume_opacity": 0.7, "value_positive_fill_color": "rgba(204,204,204,0.1)", "value_negative_fill_color": "rgba(119,119,119,0.1)", "value_positive_line_color": "rgba(204,204,204,0.5)", "value_negative_line_color": "rgba(119,119,119,0.5)"}
        }
      }
    },
    "heatmap_visualizer": {
      "default_metric": "gex_oi",
      "color_scales": { "gex": "RdBu", "dex": "Picnic" }
    },
    "dashboard": {
      "title": "V2 Elite Options Dashboard - Cerberus Directive",
      "footer": "© 2024-2025 Elite Trading Systems Inc. All Rights Reserved. Alpha Build.",
      "default_graph_height": 700,
      "table_height": 675,
      "output_directory": "dashboard_charts_output",
      "defaults": { "symbol": "SPY", "dte": "0", "range_pct": 1.0, "refresh_interval_ms": 0 },
      "refresh_options": [
        { "label": "Manual", "value": 0 }, { "label": "5 Sec", "value": 5000 }, { "label": "10 Sec", "value": 10000 },
        { "label": "15 Sec", "value": 15000 }, { "label": "30 Sec", "value": 30000 }, { "label": "1 Min", "value": 60000 },
        { "label": "2 Min", "value": 120000 }, { "label": "5 Min", "value": 300000 }
      ],
      "range_slider_marks": {
        "1": "1%", "2": "2%", "3": "3%", "4":"4%", "5": "5%", "6":"6%", "7": "7%", "8":"8%", "10": "10%", "12": "12%", "15": "15%", "18":"18%", "20": "20%"
      },
      "styles": {
        "status_display": {
          "base": { "marginTop": "15px", "textAlign": "center", "minHeight": "25px", "padding": "8px", "borderRadius": "5px", "fontSize": "0.95em" },
          "success": { "color": "#d4edda", "backgroundColor": "#155724", "borderColor": "#c3e6cb" },
          "error": { "color": "#f8d7da", "backgroundColor": "#721c24", "borderColor": "#f5c6cb" },
          "info": { "color": "#cce5ff", "backgroundColor": "#004085", "borderColor": "#b8daff" }
        }
      }
    }
  },
  "validation": {
     "required_top_level_sections": ["system_settings", "data_processor_settings", "strategy_settings", "tradier_api_settings", "visualization_settings"],
     "weights_sum_tolerance": 0.02
  }
}