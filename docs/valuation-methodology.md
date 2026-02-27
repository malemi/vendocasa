# Valuation Methodology

## Pipeline Overview

```
Address Input
     |
     v
[1] Geocoding
     Address -> (latitude, longitude)
     |
     v
[2] Zone Identification
     Point -> OMI zone polygon (via ST_Intersects)
     |
     v
[3] Quotation Lookup
     Zone + semester -> EUR/m2 price ranges (by conservation state)
     |
     v
[4] Basic Estimate
     Price range * surface area -> total value estimate
     |
     v
[5] Enhanced Estimate (Coefficient Wizard)
     User provides property-specific details
     -> correction coefficients applied
     -> adjusted EUR/m2 range
     |
     v
[6] Benchmark Comparison
     Compare adjusted estimate with real transactions
     |
     v
[7] Agent Incentives Education
     Freakonomics insights on real estate agent behavior
```

## What OMI Quotations Represent

OMI quotations are **expert-assessed price ranges**, not transaction prices. They represent:

- The range of EUR/m2 values that the OMI technical committee considers representative for a given zone, property type, and conservation state
- Updated every 6 months based on market analysis
- Published as min/max ranges (e.g. 1,800-2,400 EUR/m2)
- Broken down by conservation state: OTTIMO (excellent), NORMALE (normal), SCADENTE (poor)
- One state per zone is marked as "prevalent" (most common)

They are **not** statistical averages of actual transactions. They are professional assessments of market conditions.

## Basic Estimate Calculation

For a given address, property type, and surface area:

1. Find the **prevalent** quotation (the conservation state marked as most common in the zone)
2. Use the price range from that quotation
3. Calculate:
   - **Minimum:** price_min * surface_m2
   - **Maximum:** price_max * surface_m2
   - **Midpoint:** (price_min + price_max) / 2 * surface_m2

Example:
- Zone B01, Abitazioni civili, NORMALE (prevalent)
- Price range: 2,100-2,800 EUR/m2
- Surface: 85 m2
- Estimate: 178,500 - 238,000 EUR (midpoint: 208,250 EUR)

## Enhanced Valuation: Correction Coefficients

The basic estimate uses zone averages, which can significantly undervalue (or overvalue) a specific property. The enhanced valuation applies **correction coefficients** based on Italian appraisal methodology (coefficienti correttivi di merito).

### How It Works

1. **User selects conservation state**: OTTIMO, NORMALE, or SCADENTE. This chooses the OMI base range (difference can be 30-50%).
2. **User provides property details**: renovation, floor, exposure, noise, elevator, common areas, facade, energy class.
3. **System computes total coefficient**: sum of all percentage adjustments.
4. **Adjusted range**: OMI base * (1 + total coefficient).

### Coefficient Table

| Factor | Option | Coefficient | Rationale |
|--------|--------|-------------|-----------|
| **Renovation** | Premium post-2015 | +10% | Full renovation with certified systems |
| | Standard/recent | +5% | Partial or older renovation |
| | None | 0% | As-is condition |
| | Needs work | -10% | Renovation cost discount |
| **Floor** | Ground/semi-basement | -5% | Humidity, security, noise from street |
| | First floor | -2% | Slightly less desirable |
| | Second floor | 0% | Baseline |
| | Third/fourth floor | +5% | Optimal: light + no heat issues |
| | Fifth floor+ | +4% | High but potential heat/no-elevator issues |
| | Penthouse | +8% | Premium position |
| **Exposure** | South/dual | +5% | Maximum natural light |
| | East/West | +2% | Adequate light |
| | North only | -5% | Limited natural light |
| | Internal/dark | -8% | Courtyard-facing with poor light |
| **Noise** | Very silent | +3% | No traffic noise, premium location |
| | Silent courtyard | +2% | Internal courtyard, moderate silence |
| | Normal | 0% | Baseline |
| | Street moderate | -2% | Some traffic noise |
| | Busy street | -5% | High traffic, significant noise |
| **Elevator** | Present | 0% | Expected for floors 3+ |
| | Absent (low floor) | 0% | Acceptable for ground/first |
| | Absent (high floor) | -5% | Significant penalty |
| **Common areas** | Excellent | +2% | Well-maintained, recently updated |
| | Good | 0% | Baseline |
| | Needs maintenance | -2% | Minor issues |
| | Poor | -5% | Visible neglect |
| | Serious neglect | -7% | Major structural/maintenance issues |
| **Building facade** | Recently restored | +2% | Fresh appearance, buyer confidence |
| | Good condition | 0% | Baseline |
| | Needs work | -2% | Cosmetic issues |
| | Visibly degraded | -5% | Deters buyers, suggests neglect |
| **Energy class** | A-B | +5% | EU Green Directive compliant, low costs |
| | C-D | +2% | Adequate |
| | E | 0% | Baseline |
| | F-G | -5% | Growing penalty with EU regulations |

### Worked Example: Via Sottocorno 17, Milano

- **Zone C20** (Semicentrale), 62 m2, 3rd floor
- **OMI base (OTTIMO)**: 6,500-8,900 EUR/m2
- **Coefficients applied**:
  - Renovation: premium post-2015 = +10%
  - Floor: third/fourth = +5%
  - Exposure: south/dual = +5%
  - Noise: very silent = +3%
  - Common areas: needs maintenance = -2%
  - **Total coefficient: +21%**
- **Adjusted midpoint**: 7,700 * 1.21 = ~9,317 EUR/m2 (high end)
- **Alternative approach**: Use 4th floor benchmark (8,536 EUR/m2), adjust -1% floor + 2% silence = 8,620 EUR/m2
- **Total estimate**: ~535,000 EUR

## Benchmark Comparison

When real transactions exist in the same zone (from the manually entered `omi.transactions` table), the system compares the adjusted EUR/m2 estimate with actual sale prices:

- **High confidence** (within 5%): adjusted estimate closely matches real data
- **Medium confidence** (5-15%): reasonable deviation, review coefficients
- **Low confidence** (>15%): significant deviation, property may have unusual characteristics

## Surface Types: Lorda vs Netta

The quotation specifies whether prices refer to:
- **L (Lorda)** -- gross surface area (includes walls, common areas pro-quota)
- **N (Netta)** -- net usable surface area

Most residential quotations use L (gross). When the user enters surface_m2, they should be aware of which measurement the quotation uses.

## Comparable Transactions

Manually entered transaction data from the Agenzia's "Valori Dichiarati" viewer provides actual sale prices. These are used to:

- Cross-check whether the OMI range is realistic for the specific zone
- Calculate actual EUR/m2 from declared prices (price / cadastral m2 or estimated from vani)
- Show recent market activity in the zone
- **Anchor the enhanced estimate** against real-world data

The EUR/m2 from comparables may fall inside or outside the OMI range. Significant deviations may indicate:
- The property was sold above/below market (renovation, distressed sale, etc.)
- The OMI range needs updating (there is always a lag)
- The cadastral data doesn't reflect actual usable surface

## Real Estate Agent Incentives

Based on research by Levitt & Syvester (popularized in *Freakonomics*), real estate agents face a misalignment of incentives:

1. **The marginal incentive problem**: On a 500,000 EUR sale at 3% commission, an extra 10,000 EUR in sale price earns the agent only 300 EUR more. But it might require weeks of additional marketing and showing.

2. **Own vs. client property**: When agents sell their OWN homes, they keep them on market 10 days longer and get 10% more than when selling clients' homes.

3. **Volume over value**: An agent who closes 10 deals at conservative prices earns more total commission than one who closes 5 deals at optimal prices.

The tool educates users about these dynamics so they can:
- Recognize when a valuation is suspiciously low
- Ask agents to justify their valuation with specific comparable transactions
- Understand where a good agent truly adds value (market knowledge, negotiation, buyer qualification)
- Negotiate commission terms effectively

## Important Caveats

1. **OMI values are indicative ranges, not precise valuations.** They should not be used as the sole basis for pricing a property.

2. **Surface type matters.** A quotation of 2,000 EUR/m2 on gross surface (L) is different from 2,000 EUR/m2 on net surface (N). Gross surface is typically 15-25% larger than net.

3. **Conservation state significantly affects price.** The difference between NORMALE and OTTIMO can be 30-50%. Always check which state is being quoted.

4. **Correction coefficients are guidelines.** The percentages are based on standard Italian appraisal practice, but actual market conditions may differ. Local market expertise is always valuable.

5. **The tool does NOT replace a professional appraisal.** For mortgages, legal proceedings, or tax disputes, a certified appraiser (perito) is required.

6. **Zone boundaries are approximate.** A property at the edge of a zone may have characteristics of the neighboring zone. The 200m fallback search helps with boundary cases.

7. **Cadastral consistency (vani) is not the same as commercial surface (m2).** Converting between them requires assumptions about room sizes (typically 15-20 m2 per vano for category A properties).

8. **OMI data has a 6-month lag.** The latest available data reflects market conditions from the previous semester, not current conditions.
