"use client";

import { useState, useRef, useCallback } from "react";

type DocType = "auto" | "udyam" | "gst" | "invoice" | "bank";

export default function DocumentUpload({ initialDocType }: { isEmbedded?: boolean; initialDocType?: DocType }) {
    const [selectedType, setSelectedType] = useState<DocType>(initialDocType || "auto");
    const [file, setFile] = useState<File | null>(null);
    const [dragOver, setDragOver] = useState(false);
    const [processing, setProcessing] = useState(false);
    const [success, setSuccess] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const inputRef = useRef<HTMLInputElement>(null);

    const handleFile = useCallback((f: File) => {
        setFile(f);
        setSuccess(false);
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
        setSuccess(false);

        const formData = new FormData();
        formData.append("file", file);
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
            setSuccess(true);

            // ── Dispatch auto-fill event based on returned keys ──────────
            const autoFillData: Record<string, any> = { _source: "Document OCR" };

            if (data?.udyam) {
                const udyam = data.udyam;
                autoFillData._docSource = "Udyam Certificate";
                if (udyam.udyam_id) autoFillData.udyamNumber = udyam.udyam_id;
                if (udyam.enterprise_name) autoFillData.enterpriseName = udyam.enterprise_name;
                if (udyam.gstin_from_udyam) autoFillData.gstin = udyam.gstin_from_udyam;
                if (udyam.state) autoFillData.state = udyam.state;
                if (udyam.district) autoFillData.district = udyam.district;
                if (udyam.nic_2digit) autoFillData.productCategory = udyam.nic_2digit;
                if (udyam.enterprise_class) autoFillData.enterpriseClass = udyam.enterprise_class;
                if (udyam.major_activity) autoFillData.majorActivity = udyam.major_activity;
                if (udyam.social_category) autoFillData.socialCategory = udyam.social_category;

                if (udyam.major_activity) {
                    const activity = udyam.major_activity.toLowerCase();
                    if (activity === "manufacturing") autoFillData.transactionType = "B2B";
                    else if (activity === "trading") autoFillData.transactionType = "both";
                }
            }

            if (data?.gstr1) {
                const gstr1 = data.gstr1;
                autoFillData._docSource = "GSTR-1 Return";
                if (gstr1.gstin) autoFillData.gstin = gstr1.gstin;
                if (gstr1.annual_turnover_inr) {
                    autoFillData.turnover = new Intl.NumberFormat("en-IN").format(gstr1.annual_turnover_inr);
                }
                if (gstr1.b2b_ratio != null && gstr1.b2c_ratio != null) {
                    if (gstr1.b2b_ratio > 0.7) autoFillData.transactionType = "B2B";
                    else if (gstr1.b2c_ratio > 0.7) autoFillData.transactionType = "B2C";
                    else autoFillData.transactionType = "both";
                }
            }

            if (data?.bank) {
                const bankData = data.bank;
                autoFillData._docSource = "Bank Statement";
                if (bankData?.average_receivables) {
                    autoFillData.turnover = new Intl.NumberFormat("en-IN").format(
                        bankData.average_receivables * 12
                    );
                }
            }

            if (data?.invoice) {
                const invoiceData = data.invoice;
                autoFillData._docSource = "Sales Invoice";
                if (invoiceData?.product_categories?.length) {
                    autoFillData._productHint = invoiceData.product_categories.join(", ");
                }
            }

            if (Object.keys(autoFillData).length > 1) {
                window.dispatchEvent(new CustomEvent("ondc-autofill", { detail: autoFillData }));
            }
        } catch (err) {
            setError(err instanceof Error ? err.message : "Processing failed.");
            setSuccess(false);
        } finally {
            setProcessing(false);
        }
    };

    return (
        <div style={{ width: "100%", margin: "0 auto", padding: "12px 0" }}>
            {/* Drop Zone */}
            <div
                className={`upload-area ${dragOver ? "drag-over" : ""} ${file ? "has-file" : ""}`}
                onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
                onDragLeave={() => setDragOver(false)}
                onDrop={handleDrop}
                onClick={() => inputRef.current?.click()}
                style={{
                    border: dragOver ? "2px dashed var(--primary-blue)" : "2px dashed var(--border-color)",
                    borderRadius: "16px",
                    padding: "40px 20px",
                    textAlign: "center",
                    cursor: "pointer",
                    background: dragOver ? "rgba(74, 161, 224, 0.05)" : "var(--bg-light)",
                    transition: "all 0.2s ease"
                }}
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
                        <div className="upload-icon" style={{ fontSize: "2.5rem", marginBottom: 16 }}>
                            <i className="fas fa-file-pdf" style={{ color: "var(--primary-blue)" }} />
                        </div>
                        <p className="upload-text" style={{ fontWeight: 600, fontSize: "1.1rem", marginBottom: 4 }}>{file.name}</p>
                        <p className="upload-hint" style={{ color: "var(--text-muted)", fontSize: "0.9rem" }}>
                            {(file.size / 1024).toFixed(1)} KB · Click to change file
                        </p>
                    </>
                ) : (
                    <>
                        <div className="upload-icon" style={{ fontSize: "2.5rem", color: "var(--text-muted)", marginBottom: 16 }}>
                            <i className="fas fa-cloud-upload-alt" />
                        </div>
                        <p className="upload-text" style={{ fontWeight: 600, fontSize: "1.1rem", marginBottom: 4 }}>
                            Drag &amp; drop your document here
                        </p>
                        <p className="upload-hint" style={{ color: "var(--text-muted)", fontSize: "0.9rem" }}>
                            Supports PDF, PNG, JPG (Max 10MB)
                        </p>
                    </>
                )}
            </div>

            {error && (
                <div style={{ marginTop: 16, padding: 12, borderRadius: 8, background: "#fee2e2", color: "#b91c1c", fontSize: "0.9rem", display: "flex", alignItems: "center", gap: 8 }}>
                    <i className="fas fa-exclamation-circle" /> {error}
                </div>
            )}

            {success && (
                <div style={{ marginTop: 16, padding: 12, borderRadius: 8, background: "#dcfce7", color: "#15803d", fontSize: "0.9rem", display: "flex", alignItems: "center", gap: 8 }}>
                    <i className="fas fa-check-circle" /> Document processed! Auto-filling form...
                </div>
            )}

            {/* Process Button */}
            <div style={{ marginTop: 24, display: "flex", flexWrap: "wrap", justifyContent: "space-between", gap: 12 }}>
                <div className="onb-row" style={{ width: "100%", marginBottom: 16 }}>
                    <div className="onb-field" style={{ flex: 1 }}>
                        <label className="onb-label" style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>Document Type (Auto-Detect recommended)</label>
                        <select
                            className="onb-input"
                            style={{ padding: "8px 12px", height: "40px" }}
                            value={selectedType}
                            onChange={(e) => setSelectedType(e.target.value as DocType)}
                        >
                            <option value="auto">Auto-Detect Document</option>
                            <option value="udyam">Udyam Registration Certificate</option>
                            <option value="gst">GSTR-1 Return</option>
                            <option value="invoice">E-Invoice / Commercial Invoice</option>
                            <option value="bank">Bank Statement</option>
                        </select>
                    </div>
                </div>

                {file && !processing && !success && (
                    <button
                        className="btn btn-outline"
                        onClick={(e) => { e.stopPropagation(); setFile(null); setError(null); }}
                        style={{ border: "1px solid var(--border-color)", padding: "10px 24px", borderRadius: "12px", background: "white" }}
                    >
                        Clear
                    </button>
                )}
                <button
                    className="btn btn-primary"
                    disabled={!file || processing || success}
                    onClick={(e) => { e.stopPropagation(); processDocument(); }}
                    style={{
                        flex: 1,
                        opacity: !file || success ? 0.6 : 1,
                        padding: "12px 24px",
                        borderRadius: "12px",
                        marginLeft: (!file || processing || success) ? 0 : "auto",
                        background: success ? "#22c55e" : "var(--primary-blue)"
                    }}
                >
                    {processing ? (
                        <>
                            <i className="fas fa-spinner fa-spin" style={{ marginRight: 8 }} />
                            Analyising Document...
                        </>
                    ) : success ? (
                        <>
                            <i className="fas fa-check" style={{ marginRight: 8 }} />
                            Done
                        </>
                    ) : (
                        <>
                            <i className="fas fa-magic" style={{ marginRight: 8 }} />
                            Extract Data
                        </>
                    )}
                </button>
            </div>
        </div>
    );
}
