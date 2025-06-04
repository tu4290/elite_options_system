# Darkpool Level Analysis Methodologies

This document provides an in-depth explanation of the seven methodologies developed to identify and analyze darkpool activity using ConvexValue metrics. Each methodology targets different aspects of market microstructure that can reveal darkpool positioning.

## 1. High Gamma Imbalance Method

### Concept
The High Gamma Imbalance Method focuses on identifying strikes with unusually high gamma concentration (gxoi). Gamma represents the rate of change in an option's delta with respect to changes in the underlying price. When multiplied by open interest, it reveals price levels where market makers have significant hedging needs.

### Formula
```
gamma_zscore = (gxoi - mean(gxoi)) / std(gxoi)
gamma_threshold = quantile(gamma_zscore, 0.9)
high_gamma_levels = strikes where gamma_zscore > gamma_threshold
```

### Rationale
Darkpool participants often target strikes with high gamma concentration for several reasons:

1. **Hedging Pressure**: Market makers with large gamma exposure at specific strikes must dynamically hedge as the underlying price approaches these levels, creating predictable buying or selling pressure.

2. **Liquidity Pools**: High gamma strikes typically have deeper liquidity, allowing darkpool participants to execute large orders with minimal slippage.

3. **Price Magnets**: These strikes often act as "price magnets" due to dealer hedging flows, making them natural support/resistance levels.

4. **Volatility Compression**: As expiration approaches, gamma concentration increases, potentially leading to volatility compression around these strikes, which sophisticated darkpool participants can exploit.

### Plausibility Indicators
- Persistent gamma concentration across multiple days
- Alignment with key technical levels or round numbers
- Increasing open interest at or near these strikes
- Historical price reactions when approaching these levels

## 2. Delta-Gamma Divergence Method

### Concept
The Delta-Gamma Divergence Method identifies strikes where delta imbalance (dxoi) and gamma concentration (gxoi) diverge significantly. This divergence often indicates complex positioning that may involve darkpool activity.

### Formula
```
delta_zscore = (dxoi - mean(dxoi)) / std(dxoi)
gamma_zscore = (gxoi - mean(gxoi)) / std(gxoi)
delta_gamma_divergence = abs(gamma_zscore - delta_zscore)
divergence_threshold = quantile(delta_gamma_divergence, 0.9)
divergence_levels = strikes where delta_gamma_divergence > divergence_threshold
```

### Rationale
Delta-gamma divergence reveals sophisticated positioning strategies:

1. **Volatility Positioning**: When gamma is high but delta is neutral, it suggests positioning for volatility rather than direction, often a hallmark of institutional darkpool strategies.

2. **Complex Spreads**: Large divergences can indicate complex spread positions being established through darkpools to avoid telegraphing strategy.

3. **Hedged Directional Bets**: High delta with lower gamma may indicate hedged directional positions that have been established via darkpools.

4. **Volatility Skew Exploitation**: Divergences often appear when institutions use darkpools to exploit volatility skew inefficiencies.

### Plausibility Indicators
- Persistent divergence across multiple days
- Correlation with volatility regime changes
- Unusual options activity at these strikes
- Subsequent price behavior confirming the positioning thesis

## 3. Flow Anomaly Method

### Concept
The Flow Anomaly Method identifies strikes with unusual flow patterns across different timeframes, particularly focusing on the volume of buys minus sells (volmbs) metrics.

### Formula
```
volmbs_15m_zscore = (volmbs_15m - mean(volmbs_15m)) / std(volmbs_15m)
volmbs_60m_zscore = (volmbs_60m - mean(volmbs_60m)) / std(volmbs_60m)
flow_anomaly = abs(volmbs_15m_zscore) + abs(volmbs_15m_zscore - volmbs_60m_zscore)
flow_threshold = quantile(flow_anomaly, 0.9)
flow_levels = strikes where flow_anomaly > flow_threshold
```

### Rationale
Flow anomalies across timeframes can reveal darkpool execution strategies:

1. **Staggered Execution**: Darkpool participants often execute large orders in stages to minimize market impact, creating flow anomalies across different timeframes.

2. **Iceberg Orders**: Large darkpool positions may be established using iceberg orders, where only a small portion of the total order is visible at any time.

3. **Time-of-Day Patterns**: Institutional darkpool activity often follows specific time-of-day patterns, creating flow anomalies when compared across different timeframes.

4. **Liquidity Probing**: Before large darkpool executions, participants may probe for liquidity, creating unusual flow patterns in shorter timeframes.

### Plausibility Indicators
- Consistent flow direction despite price fluctuations
- Increasing anomaly magnitude as expiration approaches
- Correlation with known institutional reporting periods
- Flow patterns that diverge from overall market sentiment

## 4. Volatility Sensitivity Method

### Concept
The Volatility Sensitivity Method identifies strikes with high vanna (vannaxoi) and vomma (vommaxoi) exposure, indicating volatility-based darkpool strategies.

### Formula
```
vanna_zscore = (vannaxoi - mean(vannaxoi)) / std(vannaxoi)
vomma_zscore = (vommaxoi - mean(vommaxoi)) / std(vommaxoi)
vol_sensitivity = abs(vanna_zscore) + abs(vomma_zscore)
vol_threshold = quantile(vol_sensitivity, 0.9)
vol_levels = strikes where vol_sensitivity > vol_threshold
```

### Rationale
Volatility sensitivity metrics reveal sophisticated volatility-based darkpool strategies:

1. **Volatility Regime Positioning**: High vanna exposure indicates positioning for volatility regime changes, often established through darkpools to avoid telegraphing the strategy.

2. **Volatility Surface Arbitrage**: Institutions use darkpools to exploit inefficiencies in the volatility surface, creating unusual vanna and vomma concentrations.

3. **Correlation Trading**: Vanna-sensitive positions often relate to correlation trading strategies executed via darkpools.

4. **Volatility of Volatility Exposure**: High vomma indicates positioning for changes in volatility of volatility, a sophisticated strategy often executed through darkpools.

### Plausibility Indicators
- Alignment with key volatility inflection points
- Correlation with VIX term structure changes
- Positioning ahead of known volatility events
- Historical price and volatility reactions at these levels

## 5. Charm-Adjusted Gamma Method

### Concept
The Charm-Adjusted Gamma Method identifies strikes with high gamma that are also sensitive to time decay (charm), indicating expiration-related darkpool positioning.

### Formula
```
gamma_zscore = (gxoi - mean(gxoi)) / std(gxoi)
charm_zscore = (charmxoi - mean(charmxoi)) / std(charmxoi)
charm_adjusted_gamma = gamma_zscore * (1 + abs(charm_zscore))
charm_threshold = quantile(charm_adjusted_gamma, 0.9)
charm_levels = strikes where charm_adjusted_gamma > charm_threshold
```

### Rationale
Charm-adjusted gamma reveals time-sensitive darkpool positioning:

1. **Expiration Targeting**: Darkpool participants often establish positions targeting specific expiration effects, creating high charm-adjusted gamma.

2. **Pin Risk Exploitation**: Institutions use darkpools to position for "pin risk" at strikes with high charm-adjusted gamma.

3. **Gamma Scalping**: Time-decay effects create opportunities for gamma scalping, often established through darkpools.

4. **Calendar Spread Strategies**: High charm-adjusted gamma can indicate calendar spread strategies being executed through darkpools.

### Plausibility Indicators
- Increasing magnitude as expiration approaches
- Clustering around key technical or psychological levels
- Historical tendency for price to gravitate toward these levels near expiration
- Correlation with options expiration cycles

## 6. Active Hedging Detection Method

### Concept
The Active Hedging Detection Method identifies strikes with both high gamma concentration (gxoi) and high gamma-weighted volume (gxvolm), suggesting active hedging that may be related to darkpool execution.

### Formula
```
gamma_zscore = (gxoi - mean(gxoi)) / std(gxoi)
gxvolm_zscore = (gxvolm - mean(gxvolm)) / std(gxvolm)
active_hedging = gamma_zscore * gxvolm_zscore
hedging_threshold = quantile(active_hedging, 0.9)
hedging_levels = strikes where active_hedging > hedging_threshold
```

### Rationale
Active hedging detection reveals real-time darkpool execution:

1. **Real-time Hedging**: High gamma-weighted volume indicates active dealer hedging, often in response to darkpool executions.

2. **Position Unwinding**: Spikes in gamma-weighted volume at high gamma strikes can indicate darkpool positions being unwound.

3. **Liquidity Provision**: Market makers often provide liquidity at these levels to facilitate darkpool executions.

4. **Feedback Loops**: Active hedging can create feedback loops that darkpool participants exploit.

### Plausibility Indicators
- Sudden spikes in gamma-weighted volume
- Price acceleration or deceleration around these levels
- Correlation with known reporting or rebalancing periods
- Unusual options activity at or near these strikes

## 7. Value-Volume Divergence Method

### Concept
The Value-Volume Divergence Method identifies strikes where value flow (value_bs) and volume flow (volmbs) diverge significantly, potentially indicating large darkpool participants entering positions.

### Formula
```
value_bs_zscore = (value_bs - mean(value_bs)) / std(value_bs)
volmbs_zscore = (volmbs_15m - mean(volmbs_15m)) / std(volmbs_15m)
value_volume_divergence = abs(value_bs_zscore - volmbs_zscore)
value_threshold = quantile(value_volume_divergence, 0.9)
value_levels = strikes where value_volume_divergence > value_threshold
```

### Rationale
Value-volume divergence reveals sophisticated darkpool positioning:

1. **Size Disparity**: Large divergences indicate that the average trade size is unusually large or small, often a sign of institutional darkpool activity.

2. **Premium Strategies**: When value flow exceeds volume flow, it suggests high-premium strategies being executed through darkpools.

3. **Retail vs. Institutional Flow**: Divergences help distinguish between retail flow and institutional darkpool flow.

4. **Complex Strategy Execution**: Large divergences often indicate complex multi-leg strategies being executed through darkpools.

### Plausibility Indicators
- Persistent divergence across multiple days
- Correlation with institutional reporting cycles
- Unusual premium patterns at these strikes
- Subsequent convergence of value and volume flows

## Methodology Relationships and Integration

The seven methodologies are not isolated but form an integrated analytical framework:

1. **Gamma-Delta Relationship**: High Gamma Imbalance and Delta-Gamma Divergence methods are complementary, with the former identifying key hedging levels and the latter revealing complex positioning around these levels.

2. **Flow-Gamma Relationship**: Flow Anomaly and Active Hedging Detection methods work together to identify both the preparation for and execution of darkpool strategies.

3. **Volatility-Time Decay Relationship**: Volatility Sensitivity and Charm-Adjusted Gamma methods combine to reveal how darkpool participants position for both volatility regime changes and time decay effects.

4. **Size-Activity Relationship**: Value-Volume Divergence and Flow Anomaly methods together distinguish between different types of darkpool participants and their execution strategies.

5. **Composite Analysis**: The most reliable darkpool levels are those identified by multiple methodologies, suggesting robust institutional positioning rather than statistical noise.

## Conclusion

These seven methodologies provide a comprehensive framework for identifying and analyzing darkpool activity using ConvexValue metrics. By integrating these approaches and focusing on their interrelationships, we can develop a robust paradigm for unraveling darkpool activity across any timeframe and market condition.
