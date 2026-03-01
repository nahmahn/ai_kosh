"""
HSN Code Classifier & Manufacturing Confidence Score
Exact algorithm from OCR Module Brief Section 4.

Classifies HSN codes by their first 2 digits (chapter) into:
  - RAW_MATERIAL (raw inputs like cotton, metals, chemicals)
  - FINISHED_GOOD (processed outputs like fabrics, footwear, machinery)
  - UNKNOWN (don't count for or against)

Then computes a manufacturing_confidence_score (0.0 to 1.0) that determines
whether an MSE is a manufacturer or a trader.
"""

from typing import List, Dict, Tuple, Optional


# ─── HSN Chapter Classification Table (Section 4, Step 1) ────────────────
# Maps first 2 digits of HSN code → RAW_MATERIAL or FINISHED_GOOD
RAW_MATERIAL_CHAPTERS = {
    "50", "51", "52", "53",          # Silk raw, wool raw, cotton raw, plant fibres raw
    "72", "74", "76",                # Iron/steel, copper, aluminium — metals raw
    "28", "29", "39", "40",          # Chemicals inorganic/organic, plastics, rubber
    "44", "47",                      # Wood raw, pulp raw
    "10", "11", "12",                # Cereals raw, milling products, oil seeds raw
}

FINISHED_GOOD_CHAPTERS = {
    "54", "55", "57", "58", "59",    # Synthetic fabrics, carpets, apparel, made-up textiles
    "60", "61", "62", "63",          # Knitted fabrics, apparel, other textiles
    "64", "65", "66",                # Footwear, headgear, umbrellas
    "73", "82", "83",                # Iron articles, tools, metal miscellaneous articles
    "84", "85",                      # Machinery, electrical equipment
    "94", "95",                      # Furniture, toys
    "19", "20", "21",                # Food preparations, vegetables prepared, misc food
}


def classify_chapter(chapter: str) -> str:
    """
    Classify an HSN chapter (first 2 digits) as RAW_MATERIAL, FINISHED_GOOD, or UNKNOWN.
    
    Args:
        chapter: First 2 characters of an HSN code (e.g., "52" from "5208")
    
    Returns:
        One of: "RAW_MATERIAL", "FINISHED_GOOD", "UNKNOWN"
    """
    if chapter in RAW_MATERIAL_CHAPTERS:
        return "RAW_MATERIAL"
    elif chapter in FINISHED_GOOD_CHAPTERS:
        return "FINISHED_GOOD"
    return "UNKNOWN"


def detect_trading_pattern(hsn_rows: List[Dict]) -> Tuple[bool, set]:
    """
    Detect if the MSE is trading (buying and selling the same HSN chapter).
    
    A trading pattern = same HSN chapter in both RAW_MATERIAL and FINISHED_GOOD.
    This is a key fraud signal — the MSE buys and resells without transformation.
    
    Args:
        hsn_rows: List of dicts with 'hsn_code' key
    
    Returns:
        (trading_detected: bool, overlapping_chapters: set)
    """
    raw_chapters = set()
    finished_chapters = set()

    for row in hsn_rows:
        chapter = row["hsn_code"][:2]
        classification = classify_chapter(chapter)
        if classification == "RAW_MATERIAL":
            raw_chapters.add(chapter)
        elif classification == "FINISHED_GOOD":
            finished_chapters.add(chapter)

    # Overlap = same chapter bought and sold = trading signal
    overlap = raw_chapters.intersection(finished_chapters)
    return len(overlap) > 0, overlap


def compute_manufacturing_confidence(hsn_rows: List[Dict], b2b_ratio: Optional[float]) -> float:
    """
    Compute the manufacturing confidence score (0.0 to 1.0).
    
    Exact algorithm from Section 4, Step 3:
      Positive signals:
        +0.50 if BOTH raw materials AND finished goods found (transformation pattern)
        +0.25 if ONLY finished goods (could be manufacturer buying inputs elsewhere)
        +0.10 if ONLY raw materials (unclear, not a trading signal)
        +0.20 if B2B heavy (b2b_ratio > 0.6) — manufacturers supply other businesses
        +0.15 if 3+ unique HSN codes — diverse product range
      Negative signals:
        -0.40 if trading pattern detected (same chapter bought and sold)
      
    Clamped to [0.0, 1.0].
    """
    score = 0.0

    # Check what types of HSN codes are present
    raw_found = any(classify_chapter(r["hsn_code"][:2]) == "RAW_MATERIAL" for r in hsn_rows)
    finished_found = any(classify_chapter(r["hsn_code"][:2]) == "FINISHED_GOOD" for r in hsn_rows)

    # Detect trading
    trading_detected, overlap = detect_trading_pattern(hsn_rows)

    # Positive signals
    if raw_found and finished_found:
        score += 0.50    # transformation pattern: raw in, finished out = manufacturing
    elif finished_found and not raw_found:
        score += 0.25    # only finished goods — could be manufacturer buying inputs elsewhere
    elif raw_found and not finished_found:
        score += 0.10    # only raw materials — unclear, but not a trading signal

    if b2b_ratio is not None and b2b_ratio > 0.6:
        score += 0.20    # B2B heavy = more likely manufacturer supplying other businesses

    unique_hsn_count = len(set(r["hsn_code"] for r in hsn_rows))
    if unique_hsn_count >= 3:
        score += 0.15    # diverse product range = more likely manufacturer

    # Negative signals
    if trading_detected:
        score -= 0.40    # same chapter bought and sold = strong trading signal

    # Clamp to 0.0 - 1.0
    return round(max(0.0, min(1.0, score)), 4)


def get_nsic_gate3_status(score: float) -> str:
    """
    Map manufacturing confidence score to NSIC clearance status.
    
    From Section 4, Step 4:
      >= 0.75   → AUTO_APPROVE
      0.45-0.74 → HUMAN_REVIEW
      < 0.45    → AUTO_REJECT
    """
    if score >= 0.75:
        return "AUTO_APPROVE"
    elif score >= 0.45:
        return "HUMAN_REVIEW"
    else:
        return "AUTO_REJECT"
