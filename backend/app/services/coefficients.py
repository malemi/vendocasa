"""Correction coefficient engine for enhanced property valuation.

Applies property-specific correction coefficients on top of OMI zone-average
price ranges. Based on standard Italian real estate appraisal methodology
(coefficienti correttivi di merito).

The OMI gives zone-wide EUR/m2 ranges by conservation state (OTTIMO/NORMALE/SCADENTE).
This engine adjusts those ranges based on property-specific factors like floor level,
renovation quality, exposure, noise, and building condition.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Coefficient Tables
# ---------------------------------------------------------------------------
# Each factor maps option keys to percentage adjustments.
# Positive = premium, negative = discount.
# Keys are used in the API request; labels are for display.

COEFFICIENTS: dict[str, dict[str, dict]] = {
    "renovation": {
        "premium_post_2015": {"pct": 0.10, "label": "Ristrutturazione integrale post-2015", "label_en": "Premium renovation post-2015"},
        "standard_recent": {"pct": 0.05, "label": "Ristrutturazione parziale/recente", "label_en": "Standard/recent renovation"},
        "none": {"pct": 0.0, "label": "Nessuna ristrutturazione", "label_en": "No renovation"},
        "needs_work": {"pct": -0.10, "label": "Da ristrutturare", "label_en": "Needs renovation"},
    },
    "floor": {
        "ground_semi": {"pct": -0.05, "label": "Piano terra / seminterrato", "label_en": "Ground / semi-basement"},
        "first": {"pct": -0.02, "label": "Primo piano", "label_en": "First floor"},
        "second": {"pct": 0.0, "label": "Secondo piano", "label_en": "Second floor"},
        "third_fourth": {"pct": 0.05, "label": "Terzo / quarto piano", "label_en": "Third / fourth floor"},
        "fifth_plus": {"pct": 0.04, "label": "Quinto piano e oltre", "label_en": "Fifth floor and above"},
        "penthouse": {"pct": 0.08, "label": "Attico / ultimo piano", "label_en": "Penthouse / top floor"},
    },
    "exposure": {
        "south_dual": {"pct": 0.05, "label": "Sud / doppia esposizione", "label_en": "South / dual exposure"},
        "east_west": {"pct": 0.02, "label": "Est / Ovest", "label_en": "East / West"},
        "north_only": {"pct": -0.05, "label": "Solo Nord", "label_en": "North only"},
        "internal_dark": {"pct": -0.08, "label": "Interno / poco luminoso", "label_en": "Internal / low light"},
    },
    "noise": {
        "very_silent": {"pct": 0.03, "label": "Molto silenzioso", "label_en": "Very silent"},
        "silent_courtyard": {"pct": 0.02, "label": "Cortile interno / silenzioso", "label_en": "Internal courtyard / silent"},
        "normal": {"pct": 0.0, "label": "Normale", "label_en": "Normal"},
        "street_moderate": {"pct": -0.02, "label": "Strada moderata", "label_en": "Moderate street noise"},
        "busy_street": {"pct": -0.05, "label": "Strada trafficata", "label_en": "Busy street"},
    },
    "common_areas": {
        "excellent": {"pct": 0.02, "label": "Ottime condizioni", "label_en": "Excellent condition"},
        "good": {"pct": 0.0, "label": "Buone condizioni", "label_en": "Good condition"},
        "needs_maintenance": {"pct": -0.02, "label": "Necessita manutenzione", "label_en": "Needs maintenance"},
        "poor": {"pct": -0.05, "label": "Cattive condizioni", "label_en": "Poor condition"},
        "serious_neglect": {"pct": -0.07, "label": "Gravi carenze", "label_en": "Serious neglect"},
    },
    "building_facade": {
        "recently_restored": {"pct": 0.02, "label": "Recentemente restaurata", "label_en": "Recently restored"},
        "good_condition": {"pct": 0.0, "label": "Buone condizioni", "label_en": "Good condition"},
        "needs_work": {"pct": -0.02, "label": "Necessita intervento", "label_en": "Needs work"},
        "visibly_degraded": {"pct": -0.05, "label": "Visibilmente degradata", "label_en": "Visibly degraded"},
    },
    "energy_class": {
        "A_B": {"pct": 0.05, "label": "Classe A o B", "label_en": "Class A or B"},
        "C_D": {"pct": 0.02, "label": "Classe C o D", "label_en": "Class C or D"},
        "E": {"pct": 0.0, "label": "Classe E", "label_en": "Class E"},
        "F_G": {"pct": -0.05, "label": "Classe F o G", "label_en": "Class F or G"},
    },
    "elevator": {
        "yes": {"pct": 0.0, "label": "Presente", "label_en": "Yes"},
        "no_low_floor": {"pct": 0.0, "label": "Assente (piano basso)", "label_en": "No (low floor)"},
        "no_high_floor": {"pct": -0.05, "label": "Assente (piano alto)", "label_en": "No (high floor)"},
    },
}

# Factor display names (Italian primary, English secondary)
FACTOR_LABELS: dict[str, dict[str, str]] = {
    "renovation": {"it": "Ristrutturazione", "en": "Renovation"},
    "floor": {"it": "Piano", "en": "Floor"},
    "exposure": {"it": "Esposizione / Luminosita", "en": "Exposure / Light"},
    "noise": {"it": "Rumorosita", "en": "Noise level"},
    "common_areas": {"it": "Parti comuni", "en": "Common areas"},
    "building_facade": {"it": "Facciata edificio", "en": "Building facade"},
    "energy_class": {"it": "Classe energetica", "en": "Energy class"},
    "elevator": {"it": "Ascensore", "en": "Elevator"},
}


# ---------------------------------------------------------------------------
# Data Classes for Results
# ---------------------------------------------------------------------------

@dataclass
class CoefficientBreakdownItem:
    factor: str
    factor_label: str
    selected_key: str
    selected_label: str
    coefficient: float
    impact_eur_m2: float


@dataclass
class BenchmarkComparison:
    has_comparables: bool
    closest_eur_m2: float | None = None
    difference_pct: float | None = None
    confidence: str = "low"  # "high" | "medium" | "low"
    note: str = ""


@dataclass
class AdjustedEstimate:
    base_price_min: float
    base_price_max: float
    base_conservation_state: str
    total_coefficient: float
    adjusted_price_min: float
    adjusted_price_max: float
    adjusted_mid: float
    total_min: float
    total_max: float
    total_mid: float
    surface_m2: float
    breakdown: list[CoefficientBreakdownItem] = field(default_factory=list)
    benchmark_comparison: BenchmarkComparison | None = None


# ---------------------------------------------------------------------------
# Core Computation
# ---------------------------------------------------------------------------

def compute_adjusted_estimate(
    omi_price_min: float,
    omi_price_max: float,
    surface_m2: float,
    property_details: dict[str, str],
) -> AdjustedEstimate:
    """Apply correction coefficients to OMI base prices.

    Args:
        omi_price_min: OMI EUR/m2 minimum for the selected conservation state.
        omi_price_max: OMI EUR/m2 maximum for the selected conservation state.
        surface_m2: Property surface area in square meters.
        property_details: Dict mapping factor names to selected option keys.
            e.g. {"renovation": "premium_post_2015", "floor": "third_fourth", ...}

    Returns:
        AdjustedEstimate with adjusted prices, totals, and coefficient breakdown.
    """
    breakdown: list[CoefficientBreakdownItem] = []
    total_pct = 0.0
    base_mid = (omi_price_min + omi_price_max) / 2

    for factor_name, options in COEFFICIENTS.items():
        selected_key = property_details.get(factor_name)
        if not selected_key or selected_key not in options:
            continue

        option = options[selected_key]
        pct = option["pct"]
        total_pct += pct

        factor_label = FACTOR_LABELS.get(factor_name, {}).get("it", factor_name)
        selected_label = option.get("label", selected_key)

        breakdown.append(CoefficientBreakdownItem(
            factor=factor_name,
            factor_label=factor_label,
            selected_key=selected_key,
            selected_label=selected_label,
            coefficient=pct,
            impact_eur_m2=round(base_mid * pct, 2),
        ))

    multiplier = 1.0 + total_pct
    adj_min = round(omi_price_min * multiplier, 2)
    adj_max = round(omi_price_max * multiplier, 2)
    adj_mid = round(base_mid * multiplier, 2)

    conservation_state = property_details.get("conservation_state", "NORMALE")

    return AdjustedEstimate(
        base_price_min=omi_price_min,
        base_price_max=omi_price_max,
        base_conservation_state=conservation_state,
        total_coefficient=round(total_pct, 4),
        adjusted_price_min=adj_min,
        adjusted_price_max=adj_max,
        adjusted_mid=adj_mid,
        total_min=round(adj_min * surface_m2, 2),
        total_max=round(adj_max * surface_m2, 2),
        total_mid=round(adj_mid * surface_m2, 2),
        surface_m2=surface_m2,
        breakdown=breakdown,
    )


def compare_with_benchmarks(
    adjusted_eur_m2: float,
    comparables: list[dict],
) -> BenchmarkComparison:
    """Compare adjusted estimate with real transaction benchmarks.

    Args:
        adjusted_eur_m2: The adjusted EUR/m2 midpoint from coefficient engine.
        comparables: List of transaction dicts with at least 'declared_price'
            and optionally 'cadastral_mq' or 'cadastral_vani'.

    Returns:
        BenchmarkComparison with closest comparable and confidence assessment.
    """
    if not comparables:
        return BenchmarkComparison(
            has_comparables=False,
            note="Nessuna transazione comparabile disponibile nella zona. "
                 "L'aggiunta di dati reali di vendita migliorerebbe significativamente l'accuratezza.",
        )

    # Try to compute EUR/m2 for each comparable
    comparable_eur_m2: list[float] = []
    for comp in comparables:
        price = comp.get("declared_price")
        mq = comp.get("cadastral_mq")
        vani = comp.get("cadastral_vani")

        if price and price > 0:
            if mq and mq > 0:
                comparable_eur_m2.append(price / mq)
            elif vani and vani > 0:
                # Rough conversion: 1 vano catastale ~ 17 m2 (cat. A average)
                estimated_mq = vani * 17.0
                comparable_eur_m2.append(price / estimated_mq)

    if not comparable_eur_m2:
        return BenchmarkComparison(
            has_comparables=True,
            note="Transazioni disponibili ma senza dati di superficie sufficienti per calcolare EUR/m2.",
        )

    # Find closest comparable
    closest = min(comparable_eur_m2, key=lambda x: abs(x - adjusted_eur_m2))
    diff_pct = round((adjusted_eur_m2 - closest) / closest * 100, 1)
    abs_diff = abs(diff_pct)

    if abs_diff <= 5:
        confidence = "high"
        note = (f"La stima corretta ({adjusted_eur_m2:,.0f} EUR/m2) e entro il 5% "
                f"dalla transazione reale piu vicina ({closest:,.0f} EUR/m2). Ottima coerenza.")
    elif abs_diff <= 15:
        confidence = "medium"
        note = (f"La stima corretta ({adjusted_eur_m2:,.0f} EUR/m2) differisce del {diff_pct:+.1f}% "
                f"dalla transazione reale piu vicina ({closest:,.0f} EUR/m2). "
                f"Differenza ragionevole, verificare i coefficienti applicati.")
    else:
        confidence = "low"
        note = (f"La stima corretta ({adjusted_eur_m2:,.0f} EUR/m2) differisce del {diff_pct:+.1f}% "
                f"dalla transazione reale piu vicina ({closest:,.0f} EUR/m2). "
                f"Differenza significativa: rivedere i coefficienti o considerare fattori non inclusi.")

    return BenchmarkComparison(
        has_comparables=True,
        closest_eur_m2=round(closest, 2),
        difference_pct=diff_pct,
        confidence=confidence,
        note=note,
    )


def get_coefficient_options() -> dict:
    """Return all coefficient factors with their options, for the frontend wizard.

    Returns a dict suitable for JSON serialization with factor names, labels,
    and option lists.
    """
    result = {}
    for factor_name, options in COEFFICIENTS.items():
        labels = FACTOR_LABELS.get(factor_name, {})
        factor_options = []
        for key, opt in options.items():
            factor_options.append({
                "key": key,
                "label": opt["label"],
                "label_en": opt.get("label_en", ""),
                "pct": opt["pct"],
            })
        result[factor_name] = {
            "label": labels.get("it", factor_name),
            "label_en": labels.get("en", factor_name),
            "options": factor_options,
        }
    return result
