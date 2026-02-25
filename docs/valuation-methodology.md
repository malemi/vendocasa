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
     Zone + semester -> EUR/m2 price ranges
     |
     v
[4] Estimate Calculation
     Price range * surface area -> total value estimate
     |
     v
[5] Comparable Transactions (optional)
     Manually entered sales in the same zone
```

## What OMI Quotations Represent

OMI quotations are **expert-assessed price ranges**, not transaction prices. They represent:

- The range of EUR/m2 values that the OMI technical committee considers representative for a given zone, property type, and conservation state
- Updated every 6 months based on market analysis
- Published as min/max ranges (e.g. 1,800-2,400 EUR/m2)
- Broken down by conservation state: OTTIMO (excellent), NORMALE (normal), SCADENTE (poor)
- One state per zone is marked as "prevalent" (most common)

They are **not** statistical averages of actual transactions. They are professional assessments of market conditions.

## Estimate Calculation

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

The EUR/m2 from comparables may fall inside or outside the OMI range. Significant deviations may indicate:
- The property was sold above/below market (renovation, distressed sale, etc.)
- The OMI range needs updating (there is always a lag)
- The cadastral data doesn't reflect actual usable surface

## Important Caveats

1. **OMI values are indicative ranges, not precise valuations.** They should not be used as the sole basis for pricing a property.

2. **Surface type matters.** A quotation of 2,000 EUR/m2 on gross surface (L) is different from 2,000 EUR/m2 on net surface (N). Gross surface is typically 15-25% larger than net.

3. **Conservation state significantly affects price.** The difference between NORMALE and OTTIMO can be 30-50%. Always check which state is being quoted.

4. **The tool does NOT replace a professional appraisal.** For mortgages, legal proceedings, or tax disputes, a certified appraiser (perito) is required.

5. **Zone boundaries are approximate.** A property at the edge of a zone may have characteristics of the neighboring zone. The 200m fallback search helps with boundary cases.

6. **Cadastral consistency (vani) is not the same as commercial surface (m2).** Converting between them requires assumptions about room sizes (typically 15-20 m2 per vano for category A properties).

7. **OMI data has a 6-month lag.** The latest available data reflects market conditions from the previous semester, not current conditions.
