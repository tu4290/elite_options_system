# Ranking Criteria for Darkpool Levels

This document outlines the systematic approach for ranking and narrowing down darkpool levels to identify the most significant ones with highest plausibility.

## Primary Ranking Framework

The ranking of darkpool levels follows a multi-factor approach that integrates signals from all seven methodologies while prioritizing those with the strongest theoretical and empirical support.

### Core Ranking Factors

1. **Methodology Diversity Score (40%)**
   - Formula: `(Number of methods identifying the strike) / 7`
   - Rationale: Strikes identified by multiple methodologies have higher plausibility as they represent robust institutional positioning rather than statistical noise.
   - Implementation: Each strike receives a score based on how many of the seven methods identified it as significant.

2. **Gamma Concentration Factor (20%)**
   - Formula: `abs(gxoi) / max(abs(gxoi))`
   - Rationale: Gamma concentration is the primary driver of dealer hedging needs and therefore a critical factor in darkpool level significance.
   - Implementation: Normalize the absolute gamma concentration values to create a relative ranking.

3. **Flow Consistency Factor (15%)**
   - Formula: `abs(volmbs_15m) / max(abs(volmbs_15m))`
   - Rationale: Consistent directional flow indicates deliberate positioning rather than random trading activity.
   - Implementation: Normalize the absolute flow values to create a relative ranking.

4. **Delta-Gamma Alignment Factor (10%)**
   - Formula: `1 - abs(gxoi * dxoi) / (abs(gxoi) * abs(dxoi) + 1)`
   - Rationale: The relationship between delta and gamma exposures reveals the sophistication of the positioning strategy.
   - Implementation: Higher scores indicate more complex positioning typical of institutional darkpool activity.

5. **Volatility Sensitivity Factor (10%)**
   - Formula: `(abs(vannaxoi) + abs(vommaxoi)) / max(abs(vannaxoi) + abs(vommaxoi))`
   - Rationale: Sensitivity to volatility regime changes is a hallmark of sophisticated darkpool strategies.
   - Implementation: Normalize the combined vanna and vomma exposure to create a relative ranking.

6. **Time Decay Sensitivity Factor (5%)**
   - Formula: `abs(charmxoi) / max(abs(charmxoi))`
   - Rationale: Sensitivity to time decay effects reveals expiration-targeting strategies often executed via darkpools.
   - Implementation: Normalize the absolute charm exposure to create a relative ranking.

### Composite Plausibility Score

The final plausibility score is calculated as a weighted sum of the above factors:

```
plausibility_score = (0.4 * methodology_diversity) + 
                     (0.2 * gamma_concentration) + 
                     (0.15 * flow_consistency) + 
                     (0.1 * delta_gamma_alignment) + 
                     (0.1 * volatility_sensitivity) + 
                     (0.05 * time_decay_sensitivity)
```

## Secondary Filtering Criteria

After calculating the composite plausibility score, secondary filters are applied to ensure the selected levels are not only statistically significant but also practically meaningful:

1. **Strike Clustering Filter**
   - Purpose: Avoid selecting multiple strikes that are too close together
   - Implementation: If two high-scoring strikes are within 1% of each other, select the one with the higher score

2. **Technical Level Alignment**
   - Purpose: Prioritize strikes that align with key technical levels
   - Implementation: Boost scores for strikes near round numbers or key technical levels

3. **Historical Reaction Filter**
   - Purpose: Prioritize strikes that have shown historical price reactions
   - Implementation: Boost scores for strikes where price has previously shown support/resistance behavior

## Top 7 Selection Process

The selection of the top 7 darkpool levels follows this process:

1. Calculate the composite plausibility score for all identified darkpool levels
2. Apply secondary filters to adjust scores where appropriate
3. Rank all levels by their final adjusted plausibility score
4. Select the top 7 levels with highest scores
5. Document the selected levels along with their scores and the methods that identified them

## Documentation Format

For each selected level, the following information is documented:

1. Strike price
2. Composite plausibility score
3. Contributing methodologies
4. Key metrics values (gxoi, dxoi, volmbs_15m, charmxoi, vannaxoi, vommaxoi)
5. Brief interpretation of why this level is significant

## Conclusion

This ranking framework ensures a systematic, transparent, and theoretically sound approach to identifying the most significant darkpool levels. By integrating multiple methodologies and applying both quantitative scoring and qualitative filters, we maximize the plausibility and reliability of the selected levels.
