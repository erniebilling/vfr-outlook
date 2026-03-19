"""
VFR probability scoring algorithm.

Converts raw weather values into a 0-100 VFR score using weighted sub-scores:
  wind        30%
  visibility  25%
  ceiling     25%
  precip      20%

Thresholds are intentionally conservative for VFR GA flying.
"""

from dataclasses import dataclass


@dataclass
class VFRCriteria:
    max_wind_kt: float = 15.0
    min_vis_sm: float = 5.0
    min_ceiling_ft: int = 3000
    max_precip_pct: float = 30.0


DEFAULT_CRITERIA = VFRCriteria()


def _linear(value: float, good: float, bad: float) -> float:
    """
    Map a value to 0-100 where `good` → 100 and `bad` → 0.
    Works for both ascending (vis, ceiling) and descending (wind, precip) scales.
    """
    if good == bad:
        return 100.0
    ratio = (value - bad) / (good - bad)
    return max(0.0, min(100.0, ratio * 100.0))


def score_wind(wind_kt: float, gust_kt: float, criteria: VFRCriteria = DEFAULT_CRITERIA) -> float:
    effective = max(wind_kt, gust_kt)
    # 100 at ≤10 kt, 0 at ≥25 kt
    return _linear(effective, good=10.0, bad=25.0)


def score_visibility(vis_sm: float | None, criteria: VFRCriteria = DEFAULT_CRITERIA) -> float:
    if vis_sm is None:
        return 70.0  # neutral when unknown
    # 100 at ≥10 sm, 0 at ≤1 sm
    return _linear(vis_sm, good=10.0, bad=1.0)


def score_ceiling(ceiling_ft: int | None, cloud_cover_pct: float = 0.0, criteria: VFRCriteria = DEFAULT_CRITERIA) -> float:
    if ceiling_ft is None:
        # Infer from cloud cover when no explicit ceiling (Open-Meteo source)
        if cloud_cover_pct < 20:
            ceiling_ft = 99999   # clear
        elif cloud_cover_pct < 40:
            ceiling_ft = 8000
        elif cloud_cover_pct < 70:
            ceiling_ft = 4000
        else:
            ceiling_ft = 1500   # conservative OVC estimate
    # 100 at ≥5000 ft, 0 at ≤500 ft
    return _linear(ceiling_ft, good=5000.0, bad=500.0)


def score_precip(precip_pct: float, criteria: VFRCriteria = DEFAULT_CRITERIA) -> float:
    # 100 at 0%, 0 at ≥40%
    return _linear(precip_pct, good=0.0, bad=40.0)


def compute_vfr_score(
    wind_kt: float,
    gust_kt: float,
    vis_sm: float | None,
    ceiling_ft: int | None,
    cloud_cover_pct: float,
    precip_pct: float,
    criteria: VFRCriteria = DEFAULT_CRITERIA,
) -> tuple[float, list[str]]:
    """
    Returns (vfr_score 0-100, list of issue strings).
    """
    w = score_wind(wind_kt, gust_kt, criteria)
    v = score_visibility(vis_sm, criteria)
    c = score_ceiling(ceiling_ft, cloud_cover_pct, criteria)
    p = score_precip(precip_pct, criteria)

    score = round(w * 0.30 + v * 0.25 + c * 0.25 + p * 0.20, 1)

    issues = []
    effective_wind = max(wind_kt, gust_kt)
    if effective_wind > criteria.max_wind_kt:
        issues.append(f"Winds {effective_wind:.0f} kt (max {criteria.max_wind_kt:.0f} kt)")
    if vis_sm is not None and vis_sm < criteria.min_vis_sm:
        issues.append(f"Visibility {vis_sm} sm (min {criteria.min_vis_sm} sm)")
    if ceiling_ft is not None and ceiling_ft < criteria.min_ceiling_ft:
        issues.append(f"Ceiling {ceiling_ft} ft (min {criteria.min_ceiling_ft} ft)")
    if precip_pct > criteria.max_precip_pct:
        issues.append(f"Precip probability {precip_pct:.0f}% (max {criteria.max_precip_pct:.0f}%)")

    return score, issues


def score_label(score: float) -> str:
    """Return a human-readable label for a VFR score."""
    if score >= 85:
        return "VFR"
    elif score >= 65:
        return "MVFR"
    elif score >= 45:
        return "Marginal"
    elif score >= 25:
        return "Poor"
    else:
        return "IFR"
