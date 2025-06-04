# Darkpool Analysis Report for SPY

Analysis Date: 2025-05-29

Timeframe: Past 5 days

## Methodology Overview

This analysis uses seven distinct methodologies to identify potential darkpool levels:

### High Gamma Imbalance

Identifies strikes with unusually high gamma concentration, indicating potential dealer hedging needs that could be exploited by darkpool participants.

### Delta-Gamma Divergence

Identifies strikes where delta and gamma imbalances diverge significantly, suggesting complex positioning that may involve darkpool activity.

### Flow Anomaly

Identifies strikes with unusual flow patterns across timeframes, potentially indicating staggered darkpool execution.

### Volatility Sensitivity

Identifies strikes with high vanna and vomma exposure, suggesting volatility-based darkpool strategies.

### Charm-Adjusted Gamma

Identifies strikes with high gamma that are also sensitive to time decay, indicating potential expiration-related darkpool positioning.

### Active Hedging Detection

Identifies strikes with high gamma and high gamma-weighted volume, suggesting active hedging that may be related to darkpool execution.

### Value-Volume Divergence

Identifies strikes where value and volume flows diverge significantly, potentially indicating large darkpool participants entering positions.

## Identified Darkpool Levels

The following levels were identified as potential darkpool activity zones:

| Strike | Methods | Gamma Concentration | Delta Exposure | Flow (15m) | Charm Effect | Vanna Effect | Vomma Effect | Active Hedging | Value Flow |
|--------|---------|---------------------|---------------|------------|-------------|-------------|-------------|---------------|------------|
| 500 | Value-Volume Divergence, Flow Anomaly, Delta-Gamma Divergence, High Gamma Imbalance, Charm-Adjusted Gamma | 3090236.65 | -260850.43 | 288.57 | -2157.11 | -41136.10 | -1461.59 | 1357.55 | -65544.25 |
| 475 | Value-Volume Divergence, Delta-Gamma Divergence, High Gamma Imbalance, Active Hedging Detection, Charm-Adjusted Gamma | 2880229.43 | 277340.31 | -174.69 | -12452.76 | -14203.79 | 6894.76 | 4739.58 | -3948.63 |
| 450 | Value-Volume Divergence, Flow Anomaly, Delta-Gamma Divergence, High Gamma Imbalance, Active Hedging Detection, Charm-Adjusted Gamma | 1554377.40 | -547579.00 | 36.24 | 24694.49 | -12218.44 | -11019.62 | 7729.89 | 124217.18 |
| 465 | Value-Volume Divergence, Flow Anomaly, Delta-Gamma Divergence, High Gamma Imbalance, Volatility Sensitivity, Charm-Adjusted Gamma | 876519.06 | -153941.59 | -174.84 | -8934.56 | -6750.46 | -17377.64 | 1630.54 | 11758.01 |
| 460 | Flow Anomaly, Delta-Gamma Divergence, Value-Volume Divergence | 476179.27 | 185673.34 | -322.05 | 13534.29 | -4848.51 | -13612.84 | 3281.68 | 105969.90 |
| 490 | Delta-Gamma Divergence, Volatility Sensitivity, Value-Volume Divergence, Active Hedging Detection | 141619.22 | 129501.43 | 168.97 | 13493.02 | -5413.92 | -8822.90 | 1802.98 | -49084.37 |
| 505 | Delta-Gamma Divergence, High Gamma Imbalance, Volatility Sensitivity, Charm-Adjusted Gamma | 888218.73 | 26449.26 | -24.71 | 33492.98 | -8427.59 | 13172.10 | 822.52 | -6891.38 |

## Ultra Darkpool Levels

The following three levels have the highest plausibility of significant darkpool activity:

| Strike | Plausibility | Methods | Gamma Concentration | Delta Exposure | Flow (15m) | Charm Effect |
|--------|--------------|---------|---------------------|---------------|------------|-------------|
| 500 | 2.6747 | Value-Volume Divergence, Flow Anomaly, Delta-Gamma Divergence, High Gamma Imbalance, Charm-Adjusted Gamma | 3090236.65 | -260850.43 | 288.57 | -2157.11 |
| 475 | 2.5606 | Value-Volume Divergence, Delta-Gamma Divergence, High Gamma Imbalance, Active Hedging Detection, Charm-Adjusted Gamma | 2880229.43 | 277340.31 | -174.69 | -12452.76 |
| 450 | 2.2100 | Value-Volume Divergence, Flow Anomaly, Delta-Gamma Divergence, High Gamma Imbalance, Active Hedging Detection, Charm-Adjusted Gamma | 1554377.40 | -547579.00 | 36.24 | 24694.49 |

## Methodology Relationships

The three ultra darkpool levels were identified through a composite analysis that considers the relationships between different methodologies:

1. **Gamma-Delta Relationship**: High gamma concentration coupled with significant delta exposure indicates potential dealer hedging needs that darkpool participants can exploit.

2. **Flow-Gamma Relationship**: Unusual flow patterns at strikes with high gamma concentration suggest darkpool participants may be positioning around key hedging levels.

3. **Volatility-Time Decay Relationship**: The interaction between vanna, vomma, and charm effects can reveal complex darkpool strategies that exploit volatility regime changes and time decay.

## Conclusion

The identified ultra darkpool levels represent the most plausible zones of significant darkpool activity based on a comprehensive analysis of ConvexValue metrics. These levels can serve as key support/resistance zones and may be particularly important for understanding market structure and potential price action.