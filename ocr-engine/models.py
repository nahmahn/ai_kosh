"""
Data models for the OCR Document Extraction Module (Layer 1).
Matches the EXACT output schema from OCR Module Brief Section 5.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


# ─── Udyam Certificate Fields (Section 3.1) ──────────────────────────────

class UdyamSignals(BaseModel):
    udyam_id: Optional[str] = Field(None, description="Format: UDYAM-XX-XX-XXXXXXX")
    enterprise_name: Optional[str] = Field(None, description="Legal registered name")
    nic_2digit: Optional[str] = Field(None, description="First 2 digits of NIC code")
    nic_5digit: Optional[str] = Field(None, description="Full 5-digit NIC code — critical for matching")
    enterprise_class: Optional[str] = Field(None, description="One of: Micro, Small, Medium")
    major_activity: Optional[str] = Field(None, description="One of: Manufacturing, Services, Trading")
    district: Optional[str] = Field(None, description="District name as on certificate")
    state: Optional[str] = Field(None, description="State name")
    gstin_from_udyam: Optional[str] = Field(None, description="GSTIN if present on Udyam cert")
    date_of_incorporation: Optional[str] = Field(None, description="DD/MM/YYYY format exactly")
    social_category: Optional[str] = Field(None, description="One of: General, SC, ST, OBC, Women")
    extraction_confidence: float = Field(0.0, ge=0.0, le=1.0)


# ─── GSTR-1 Fields (Section 3.2) ─────────────────────────────────────────

class HSNRow(BaseModel):
    """A single row from Table 12 (HSN Summary) — the most important table."""
    hsn_code: str = Field(..., description="4-8 digit HSN code")
    description: str = Field("", description="Product/service description")
    uqc: str = Field("", description="Unit of quantity (MTR, KGS, NOS, etc)")
    total_qty: float = Field(0.0, description="Total quantity")
    total_value: float = Field(0.0, description="Total invoice value in Rs.")
    taxable_value: float = Field(0.0, description="Taxable value in Rs.")
    tax_rate_pct: float = Field(0.0, description="Tax rate percentage")


class GSTR1Signals(BaseModel):
    """All extracted + computed fields from a GSTR-1 PDF."""
    # Header fields
    gstin: Optional[str] = Field(None, description="15-character GSTIN")
    financial_year: Optional[str] = Field(None, description="e.g. 2024-25")
    tax_period: Optional[str] = Field(None, description="Month + Year, e.g. October 2024")
    filing_date: Optional[str] = Field(None, description="Date ARN was generated")
    turnover_previous_fy: Optional[float] = Field(None, description="Aggregate turnover preceding FY, in Rs.")
    turnover_current_ytd: Optional[float] = Field(None, description="Aggregate turnover current FY YTD, in Rs.")

    # Computed from Table 4A (B2B invoices)
    b2b_total_taxable_value: Optional[float] = Field(None, description="Sum of taxable values in Table 4A")
    b2b_invoice_count: Optional[int] = Field(None, description="Count of invoice rows in Table 4A")
    b2b_buyer_states: List[str] = Field(default_factory=list, description="Unique Place of Supply values")
    b2b_avg_invoice_value: Optional[float] = Field(None, description="b2b_total / b2b_count")

    # Computed: B2B vs B2C ratio
    b2c_total_taxable_value: Optional[float] = Field(None, description="Sum of taxable values in Table 7A")
    b2b_ratio: Optional[float] = Field(None, description="b2b_total / (b2b_total + b2c_total), 0.0-1.0")
    b2c_ratio: Optional[float] = Field(None, description="b2c_total / (b2b_total + b2c_total), 0.0-1.0")

    # Table 12 — HSN Summary (most critical)
    hsn_table_rows: List[HSNRow] = Field(default_factory=list, description="Every row from Table 12")

    # Computed summary from Table 12
    hsn_codes_transacted: List[str] = Field(default_factory=list, description="Just the codes")
    avg_invoice_value_inr: Optional[float] = Field(None, description="Same as b2b_avg_invoice_value")
    annual_turnover_inr: Optional[float] = Field(None, description="turnover_previous_fy or annualized current")
    peak_months: List[int] = Field(default_factory=list, description="Peak months if multiple returns processed")

    extraction_confidence: float = Field(0.0, ge=0.0, le=1.0)


# ─── NSIC Preclearance (Section 4) ───────────────────────────────────────

class NSICPreclearance(BaseModel):
    manufacturing_confidence_score: float = Field(0.0, ge=0.0, le=1.0)
    trading_pattern_detected: bool = Field(False)
    raw_material_hsn_found: bool = Field(False)
    finished_good_hsn_found: bool = Field(False)
    nsic_gate3_status: str = Field("HUMAN_REVIEW", description="AUTO_APPROVE / HUMAN_REVIEW / AUTO_REJECT")
    flag_reason: Optional[str] = Field(None, description="Reason if flagged/rejected")


# ─── Top-Level Output (Section 5 exact schema) ──────────────────────────

class VerifiedCapabilityFingerprint(BaseModel):
    """Top-level output matching OCR Module Brief Section 5 schema exactly."""
    module: str = Field(default="ocr_document_extraction")
    schema_version: str = Field(default="1.0.0")
    merge_ready: bool = Field(default=True)
    generated_at: Optional[str] = Field(None, description="ISO timestamp")
    processing_time_ms: Optional[int] = Field(None)

    # Document-specific blocks (filled based on what's processed)
    udyam: Optional[Dict[str, Any]] = Field(None)
    gstr1: Optional[Dict[str, Any]] = Field(None)

    # Manufacturing confidence
    nsic_preclearance: Optional[Dict[str, Any]] = Field(None)

    # Tracking
    documents_processed: List[str] = Field(default_factory=list)
    documents_missing: List[str] = Field(default_factory=list)
    partial_data_flag: bool = Field(False)


# ─── Legacy models (keep for backward compat with other parsers) ─────────

class InvoiceSignals(BaseModel):
    average_order_size: Optional[float] = Field(None)
    buyer_geographies: List[str] = Field(default_factory=list)
    delivery_patterns: Optional[str] = Field(None)
    product_categories: List[str] = Field(default_factory=list)

class BankStatementSignals(BaseModel):
    payment_cycles: Optional[str] = Field(None)
    average_receivables: Optional[float] = Field(None)
    seasonal_revenue_bands: Optional[str] = Field(None)
