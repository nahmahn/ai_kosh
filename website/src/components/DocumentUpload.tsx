"use client";

import { useState, useRef, useCallback } from "react";

type DocType = "udyam" | "gst" | "invoice" | "bank";

const DOC_TYPES: { key: DocType; label: string; icon: string }[] = [
    { key: "udyam", label: "Udyam Certificate", icon: "fas fa-id-card" },
    { key: "gst", label: "GST Return (GSTR-1)", icon: "fas fa-file-invoice-dollar" },
    { key: "invoice", label: "E-Invoice", icon: "fas fa-receipt" },
    { key: "bank", label: "Bank Statement", icon: "fas fa-university" },
];

function syntaxHighlight(json: string): string {
    return json.replace(
        /("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\\-]?\d+)?)/g,
        (match) => {
            let cls = "number";
            if (/^"/.test(match)) {
                cls = /:$/.test(match) ? "key" : "string";
            } else if (/true|false/.test(match)) {
                cls = "boolean";
            } else if (/null/.test(match)) {
                cls = "null";
            }
            return `<span class="${cls}">${match}</span>`;
        }
    );
}

export default function DocumentUpload({ isEmbedded = false, initialDocType }: { isEmbedded?: boolean; initialDocType?: DocType }) {
    const [selectedType, setSelectedType] = useState<DocType>(initialDocType || "udyam");
    const [file, setFile] = useState<File | null>(null);
    const [dragOver, setDragOver] = useState(false);
    const [processing, setProcessing] = useState(false);
    const [result, setResult] = useState<object | null>(null);
    const [error, setError] = useState<string | null>(null);
    const inputRef = useRef<HTMLInputElement>(null);

    const handleFile = useCallback((f: File) => {
        setFile(f);
        setResult(null);
        setError(null);
    }, []);

    const handleDrop = useCallback(
        (e: React.DragEvent) => {
            e.preventDefault();
            setDragOver(false);
            const f = e.dataTransfer.files[0];
            if (f) handleFile(f);
        },
        [handleFile]
    );

    const processDocument = async () => {
        if (!file) return;
        setProcessing(true);
        setError(null);
        setResult(null);

        const formData = new FormData();
        formData.append("document", file);
        formData.append("doc_type", selectedType);

        try {
            const res = await fetch("/api/ocr/process", {
                method: "POST",
                body: formData,
            });

            if (!res.ok) {
                const errData = await res.json().catch(() => ({}));
                throw new Error(errData.detail || `Server error ${res.status}`);
            }

            const data = await res.json();
            setResult(data);

            // ── Dispatch auto-fill event to OnboardingForm ──────────
            // OCR backend returns VerifiedCapabilityFingerprint:
            //   { udyam: { udyam_id, enterprise_name, nic_2digit, state, district, gstin_from_udyam, ... },
            //     gstr1: { gstin, annual_turnover_inr, b2b_ratio, b2c_ratio, ... },
            //     nsic_preclearance: { ... } }
            const autoFillData: Record<string, string> = { _source: "Document OCR" };

            if (selectedType === "udyam") {
                const udyam = data?.udyam || {};
                if (udyam.udyam_id) autoFillData.udyamNumber = udyam.udyam_id;
                if (udyam.enterprise_name) autoFillData.enterpriseName = udyam.enterprise_name;
                if (udyam.gstin_from_udyam) autoFillData.gstin = udyam.gstin_from_udyam;
                if (udyam.state) autoFillData.state = udyam.state;
                if (udyam.district) autoFillData.district = udyam.district;
                // NIC 2-digit code maps to product category in the form
                if (udyam.nic_2digit) autoFillData.productCategory = udyam.nic_2digit;
            } else if (selectedType === "gst") {
                const gstr1 = data?.gstr1 || {};
                if (gstr1.gstin) autoFillData.gstin = gstr1.gstin;
                if (gstr1.annual_turnover_inr) {
                    autoFillData.turnover = new Intl.NumberFormat("en-IN").format(gstr1.annual_turnover_inr);
                }
                // B2B/B2C ratio → transaction type auto-fill
                if (gstr1.b2b_ratio != null && gstr1.b2c_ratio != null) {
                    if (gstr1.b2b_ratio > 0.7) autoFillData.transactionType = "B2B";
                    else if (gstr1.b2c_ratio > 0.7) autoFillData.transactionType = "B2C";
                    else autoFillData.transactionType = "both";
                }
            } else if (selectedType === "bank") {
                // Bank statement parser returns BankStatementSignals (less structured)
                // Fall through to generic extraction for any matching fields
                const bankData = data?.bank || data;
                if (bankData?.average_receivables) {
                    autoFillData.turnover = new Intl.NumberFormat("en-IN").format(
                        bankData.average_receivables * 12
                    );
                }
            } else if (selectedType === "invoice") {
                // Invoice parser returns InvoiceSignals
                const invoiceData = data?.invoice || data;
                if (invoiceData?.product_categories?.length) {
                    autoFillData._productHint = invoiceData.product_categories.join(", ");
                }
            }

            if (Object.keys(autoFillData).length > 1) {
                window.dispatchEvent(new CustomEvent("ondc-autofill", { detail: autoFillData }));
            }
        } catch (err) {
            setError(err instanceof Error ? err.message : "Processing failed. Make sure the FastAPI backend is running on port 8000.");
        } finally {
            setProcessing(false);
        }
    };

    const content = (
        <div className={isEmbedded ? "" : "two-col"} style={isEmbedded ? { maxWidth: 500, margin: "0 auto" } : {}}>
            {/* Left: Upload */}
            <div>
                {/* Doc Type Selector */}
                {!isEmbedded && (
                    <div className="doc-type-selector" style={{ justifyContent: "flex-start", marginTop: 0, marginBottom: 24 }}>
                        {DOC_TYPES.map((dt) => (
                            <button
                                key={dt.key}
                                className={`doc-type-btn ${selectedType === dt.key ? "active" : ""}`}
                                onClick={() => setSelectedType(dt.key)}
                            >
                                <i className={dt.icon} style={{ marginRight: 6 }} />
                                {dt.label}
                            </button>
                        ))}
                    </div>
                )}

                {/* Drop Zone */}
                <div
                    className={`upload-area ${dragOver ? "drag-over" : ""} ${file ? "has-file" : ""}`}
                    onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
                    onDragLeave={() => setDragOver(false)}
                    onDrop={handleDrop}
                    onClick={() => inputRef.current?.click()}
                >
                    <input
                        ref={inputRef}
                        type="file"
                        accept=".pdf,.png,.jpg,.jpeg"
                        style={{ display: "none" }}
                        onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
                    />

                    {file ? (
                        <>
                            <div className="upload-icon">
                                <i className="fas fa-check-circle" style={{ color: "#28a745" }} />
                            </div>
                            <p className="upload-text" style={{ fontWeight: 600 }}>{file.name}</p>
                            <p className="upload-hint">
                                {(file.size / 1024).toFixed(1)} KB · Click to change
                            </p>
                        </>
                    ) : (
                        <>
                            <div className="upload-icon">
                                <i className="fas fa-cloud-upload-alt" />
                            </div>
                            <p className="upload-text">
                                Drag &amp; drop your document here
                            </p>
                            <p className="upload-hint">Supports PDF, PNG, JPG · Max 10MB</p>
                        </>
                    )}
                </div>

                {/* Process Button */}
                <div style={{ marginTop: 20, display: "flex", gap: 12 }}>
                    <button
                        className="btn btn-primary"
                        disabled={!file || processing}
                        onClick={processDocument}
                        style={{ opacity: !file ? 0.5 : 1 }}
                    >
                        {processing ? (
                            <>
                                <i className="fas fa-spinner fa-spin" />
                                Processing...
                            </>
                        ) : (
                            <>
                                <i className="fas fa-magic" />
                                Extract Capabilities
                            </>
                        )}
                    </button>
                    {file && (
                        <button
                            className="btn btn-outline"
                            onClick={() => { setFile(null); setResult(null); setError(null); }}
                        >
                            Clear
                        </button>
                    )}
                </div>
            </div>

            {/* Right: Results */}
            {!isEmbedded && (
                <div>
                    <div className="results-panel" style={{ minHeight: 300 }}>
                        <div className="results-header">
                            <span>
                                <i className="fas fa-terminal" style={{ marginRight: 8, opacity: 0.5 }} />
                                Verified Capability Fingerprint
                            </span>
                            {result && (
                                <span className="status-badge success">
                                    <span className="status-dot" />
                                    Extracted
                                </span>
                            )}
                            {processing && (
                                <span className="status-badge processing">
                                    <span className="status-dot" />
                                    Processing
                                </span>
                            )}
                        </div>
                        <div className="results-body">
                            {processing && (
                                <div style={{ textAlign: "center", padding: "40px 0" }}>
                                    <div className="spinner" />
                                    <p style={{ color: "var(--text-light)", fontSize: "0.85rem", marginTop: 12 }}>
                                        Running LayoutLMv3 + Gemini extraction...
                                    </p>
                                </div>
                            )}
                            {error && (
                                <div style={{ color: "#e53935", padding: 16 }}>
                                    <i className="fas fa-exclamation-triangle" style={{ marginRight: 8 }} />
                                    {error}
                                </div>
                            )}
                            {result && (
                                <div
                                    dangerouslySetInnerHTML={{
                                        __html: syntaxHighlight(JSON.stringify(result, null, 2)),
                                    }}
                                />
                            )}
                            {!processing && !result && !error && (
                                <div style={{ color: "var(--text-muted)", textAlign: "center", padding: "60px 20px" }}>
                                    <i className="fas fa-arrow-left" style={{ fontSize: "1.5rem", opacity: 0.3, marginBottom: 12, display: "block" }} />
                                    Upload a document and click &quot;Extract Capabilities&quot;
                                    <br />
                                    to see the AI-extracted fingerprint here.
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            )}
        </div>
    );

    if (isEmbedded) {
        return <div style={{ padding: "40px 20px" }}>{content}</div>;
    }

    return (
        <section className="section" id="document-upload">
            <div className="container">
                <span className="section-badge">Layer 1</span>
                <h2 className="section-title">Document Intelligence Engine</h2>
                <p className="section-subtitle">
                    Upload MSME documents to extract verified capabilities using LayoutLMv3
                    and Gemini 2.5 Flash — zero manual entry required.
                </p>
                {content}
            </div>
        </section>
    );
}
