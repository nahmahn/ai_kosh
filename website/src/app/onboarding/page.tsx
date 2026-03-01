"use client";

import { useState, useEffect } from "react";
import DocumentUpload from "../../components/DocumentUpload";
import VoiceOnboarding from "../../components/VoiceOnboarding";
import OnboardingForm from "../../components/OnboardingForm";
import Link from "next/link";

export default function OnboardingPage() {
    const [step, setStep] = useState<"setup" | "capture" | "form">("setup");
    const [mode, setMode] = useState<"ocr" | "voice" | null>(null);
    const [docType, setDocType] = useState<"udyam" | "gst" | "invoice" | "bank" | null>(null);
    const [autoFillData, setAutoFillData] = useState<Record<string, string> | null>(null);

    useEffect(() => {
        const handleAutoFill = (e: object) => {
            const ce = e as CustomEvent;
            if (ce.detail) setAutoFillData(ce.detail);
            setStep("form");
            window.scrollTo({ top: 0, behavior: "smooth" });
        };
        window.addEventListener("ondc-autofill", handleAutoFill as EventListener);
        return () => window.removeEventListener("ondc-autofill", handleAutoFill as EventListener);
    }, []);

    const DOC_TYPES = [
        { id: "udyam", title: "Udyam Certificate", icon: "fas fa-certificate", desc: "Best for MSME identity verification" },
        { id: "gst", title: "GST Return", icon: "fas fa-file-invoice-dollar", desc: "For detailed tax & B2B metrics" },
        { id: "invoice", title: "E-Invoice", icon: "fas fa-receipt", desc: "For product categories & pricing" },
        { id: "bank", title: "Bank Statement", icon: "fas fa-university", desc: "For financial health & turnover" }
    ] as const;

    return (
        <div style={{ minHeight: "100vh", background: "var(--bg-light)", paddingBottom: "100px" }}>
            {/* Header */}
            <header className="onboarding-header" style={{ padding: "24px 0", background: "white", borderBottom: "1px solid var(--border-color)", marginBottom: 40 }}>
                <div className="container" style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                    <Link href="/" style={{ color: "var(--text-color)", textDecoration: "none", fontWeight: 700, fontSize: "1.2rem", display: "flex", alignItems: "center", gap: 8 }}>
                        <div style={{ width: 32, height: 32, borderRadius: 8, background: "var(--primary-blue)", color: "white", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "1rem" }}>
                            <i className="fas fa-network-wired" />
                        </div>
                        ONDC AI Onboarding
                    </Link>
                    {step === "capture" && (
                        <button className="btn btn-white btn-sm" onClick={() => setStep("setup")}>
                            <i className="fas fa-times" style={{ marginRight: 6 }} /> Cancel
                        </button>
                    )}
                </div>
            </header>

            <div className="container">
                {step === "setup" && (
                    <div className="card slide-up" style={{ maxWidth: 800, margin: "0 auto", padding: "40px" }}>
                        <h1 style={{ fontSize: "2rem", marginBottom: 8, textAlign: "center" }}>Let&apos;s get your business on ONDC</h1>
                        <p style={{ color: "var(--text-secondary)", textAlign: "center", marginBottom: 40 }}>
                            Choose how you would like to provide your details.
                        </p>

                        {/* Mode Selection */}
                        <div style={{ marginBottom: 40 }}>
                            <h3 style={{ fontSize: "1.1rem", marginBottom: 16 }}>1. Select Input Mode</h3>
                            <div className="grid-2">
                                <div
                                    className={`mode-card ${mode === "ocr" ? "active" : ""}`}
                                    onClick={() => setMode("ocr")}
                                >
                                    <div className="mode-icon" style={{ background: mode === "ocr" ? "var(--primary-blue)" : "#E0F2FE", color: mode === "ocr" ? "white" : "#0284C7" }}>
                                        <i className="fas fa-file-upload" />
                                    </div>
                                    <div>
                                        <h4 style={{ margin: 0, marginBottom: 4 }}>Document Upload</h4>
                                        <p style={{ margin: 0, fontSize: "0.85rem", color: "var(--text-muted)" }}>Upload an PDF or image for instant extraction</p>
                                    </div>
                                </div>
                                <div
                                    className={`mode-card ${mode === "voice" ? "active" : ""}`}
                                    onClick={() => setMode("voice")}
                                >
                                    <div className="mode-icon" style={{ background: mode === "voice" ? "var(--accent-orange)" : "#FEF3C7", color: mode === "voice" ? "white" : "#D97706" }}>
                                        <i className="fas fa-microphone-alt" />
                                    </div>
                                    <div>
                                        <h4 style={{ margin: 0, marginBottom: 4 }}>Voice Assistant</h4>
                                        <p style={{ margin: 0, fontSize: "0.85rem", color: "var(--text-muted)" }}>Speak your details naturally in any language</p>
                                    </div>
                                </div>
                            </div>
                        </div>

                        {/* Form/Doc Selection */}
                        <div style={{ marginBottom: 40 }}>
                            <h3 style={{ fontSize: "1.1rem", marginBottom: 16 }}>2. Select Document / Form Type</h3>
                            <div className="grid-2" style={{ gap: 16 }}>
                                {DOC_TYPES.map(doc => (
                                    <div
                                        key={doc.id}
                                        className={`doc-card ${docType === doc.id ? "active" : ""}`}
                                        onClick={() => setDocType(doc.id as any)}
                                    >
                                        <i className={doc.icon} style={{ fontSize: "1.2rem", color: docType === doc.id ? "var(--primary-blue)" : "var(--text-muted)" }} />
                                        <div>
                                            <h4 style={{ margin: 0, fontSize: "0.95rem" }}>{doc.title}</h4>
                                            <p style={{ margin: 0, fontSize: "0.8rem", color: "var(--text-muted)" }}>{doc.desc}</p>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>

                        {/* Proceed action */}
                        <div style={{ textAlign: "center", borderTop: "1px solid var(--border-color)", paddingTop: 32 }}>
                            <button
                                className="btn btn-primary btn-lg"
                                style={{ width: "100%", maxWidth: 300, justifyContent: "center" }}
                                disabled={!mode || !docType}
                                onClick={() => setStep("capture")}
                            >
                                Proceed to Data Capture <i className="fas fa-arrow-right" style={{ marginLeft: 8 }} />
                            </button>
                        </div>
                    </div>
                )}

                {step === "capture" && (
                    <div className="slide-up">
                        {mode === "ocr" ? (
                            <div className="card" style={{ maxWidth: 640, margin: "0 auto", padding: "40px 20px" }}>
                                <h2 style={{ textAlign: "center", marginBottom: 8 }}>Upload your {DOC_TYPES.find(d => d.id === docType)?.title}</h2>
                                <p style={{ textAlign: "center", color: "var(--text-secondary)", marginBottom: 32 }}>
                                    We will extract the required fields automatically using Document AI.
                                </p>
                                <DocumentUpload isEmbedded={true} initialDocType={docType || "udyam"} />
                            </div>
                        ) : (
                            <div className="card" style={{ maxWidth: 800, margin: "0 auto", padding: "40px" }}>
                                <h2 style={{ textAlign: "center", marginBottom: 8 }}>Voice Data Capture</h2>
                                <p style={{ textAlign: "center", color: "var(--text-secondary)", marginBottom: 32 }}>
                                    Tell us about your {DOC_TYPES.find(d => d.id === docType)?.title?.split(" ")[0]} details.
                                </p>
                                <VoiceOnboarding isEmbedded={true} />
                            </div>
                        )}
                    </div>
                )}

                {step === "form" && (
                    <div className="slide-up">
                        <OnboardingForm isEmbedded={false} initialData={autoFillData} />
                    </div>
                )}
            </div>

            <style jsx>{`
                .mode-card {
                    display: flex;
                    align-items: center;
                    gap: 16px;
                    padding: 20px;
                    border: 2px solid var(--border-color);
                    border-radius: 12px;
                    cursor: pointer;
                    transition: all 0.2s;
                    background: white;
                }
                .mode-card:hover {
                    border-color: #9CA3AF;
                    transform: translateY(-2px);
                }
                .mode-card.active {
                    border-color: var(--primary-blue);
                    background: #F0F9FF;
                }
                .mode-icon {
                    width: 48px;
                    height: 48px;
                    border-radius: 50%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 1.2rem;
                    flex-shrink: 0;
                    transition: all 0.2s;
                }
                
                .doc-card {
                    display: flex;
                    align-items: flex-start;
                    gap: 16px;
                    padding: 16px;
                    border: 1px solid var(--border-color);
                    border-radius: 12px;
                    cursor: pointer;
                    transition: all 0.2s;
                    background: white;
                }
                .doc-card:hover {
                    border-color: #9CA3AF;
                }
                .doc-card.active {
                    border-color: var(--primary-blue);
                    border-width: 2px;
                    padding: 15px; /* offset border width */
                    background: #F0F9FF;
                }
                .slide-up {
                    animation: slideUp 0.4s ease-out forwards;
                }
                @keyframes slideUp {
                    from { opacity: 0; transform: translateY(20px); }
                    to { opacity: 1; transform: translateY(0); }
                }
            `}</style>
        </div>
    );
}
