"use client";

import { useState, useEffect } from "react";
import DocumentUpload from "../../components/DocumentUpload";
import VoiceOnboarding from "../../components/VoiceOnboarding";
import OnboardingForm from "../../components/OnboardingForm";
import MatchResults from "../../components/MatchResults";
import Link from "next/link";

export default function OnboardingPage() {
    const [step, setStep] = useState<"form" | "match">("form");
    const [showVoiceModal, setShowVoiceModal] = useState(false);
    const [showOcrModal, setShowOcrModal] = useState(false);
    const [autoFillData, setAutoFillData] = useState<Record<string, string> | null>(null);
    const [formData, setFormData] = useState<any>(null);

    useEffect(() => {
        const handleAutoFill = (e: object) => {
            const ce = e as CustomEvent;
            if (ce.detail) {
                setAutoFillData(prev => ({ ...prev, ...ce.detail }));

                // Only close modal automatically if conversation is actually complete
                if (ce.detail.conversation_complete) {
                    setTimeout(() => {
                        setShowVoiceModal(false);
                        setShowOcrModal(false);
                    }, 1500);
                }
            }
        };
        const handleRegistrationComplete = (e: object) => {
            const ce = e as CustomEvent;
            setFormData(ce.detail);
            setStep("match");
            window.scrollTo({ top: 0, behavior: "smooth" });
        };

        window.addEventListener("ondc-autofill", handleAutoFill as EventListener);
        window.addEventListener("ondc-registration-complete", handleRegistrationComplete as EventListener);

        return () => {
            window.removeEventListener("ondc-autofill", handleAutoFill as EventListener);
            window.removeEventListener("ondc-registration-complete", handleRegistrationComplete as EventListener);
        };
    }, []);

    // Prevent body scroll when modal is open
    useEffect(() => {
        if (showVoiceModal || showOcrModal) {
            document.body.style.overflow = "hidden";
        } else {
            document.body.style.overflow = "auto";
        }
        return () => { document.body.style.overflow = "auto"; }
    }, [showVoiceModal, showOcrModal]);

    return (
        <div style={{ minHeight: "100vh", background: "var(--bg-section-alt)", paddingBottom: "100px", position: "relative" }}>

            {/* Header */}
            <header className="onboarding-header" style={{ padding: "20px 0", background: "rgba(255,255,255,0.8)", backdropFilter: "blur(12px)", borderBottom: "1px solid rgba(28, 117, 188, 0.1)", position: "sticky", top: 0, zIndex: 100 }}>
                <div className="container" style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                    <Link href="/" style={{ color: "var(--dark-blue)", textDecoration: "none", fontWeight: 700, fontSize: "1.2rem", display: "flex", alignItems: "center", gap: 8 }}>
                        <div style={{ width: 32, height: 32, borderRadius: 8, background: "var(--gradient-primary)", color: "white", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "1rem" }}>
                            <i className="fas fa-network-wired" />
                        </div>
                        AIKOSH <span style={{ fontWeight: 400, opacity: 0.7 }}>| Seller Onboarding</span>
                    </Link>

                    {step === "form" && (
                        <div style={{ display: "flex", gap: "12px" }}>
                            <button className="btn btn-outline btn-sm" onClick={() => setShowOcrModal(true)} style={{ background: "white", borderRadius: "20px", padding: "8px 16px", border: "1px solid rgba(28, 117, 188, 0.2)" }}>
                                <i className="fas fa-file-upload" style={{ marginRight: 6, color: "var(--primary-blue)" }} /> Upload Document
                            </button>
                            <button className="btn btn-primary btn-sm" onClick={() => setShowVoiceModal(true)} style={{ borderRadius: "20px", padding: "8px 16px", boxShadow: "0 4px 12px rgba(74, 161, 224, 0.3)" }}>
                                <i className="fas fa-microphone-alt" style={{ marginRight: 6 }} /> Fill with Voice
                            </button>
                        </div>
                    )}
                </div>
            </header>

            <div className="container" style={{ marginTop: 40 }}>
                {step === "form" && (
                    <div className="fade-in">
                        <div style={{ textAlign: "center", marginBottom: 32 }}>
                            <h1 style={{ fontSize: "2rem", marginBottom: 8 }}>Complete Your Profile</h1>
                            <p style={{ color: "var(--text-secondary)" }}>Review and complete your business details to join the ONDC network.</p>
                        </div>
                        <OnboardingForm isEmbedded={false} initialData={autoFillData} />
                    </div>
                )}

                {step === "match" && (
                    <div className="fade-in">
                        <MatchResults formData={formData} />
                    </div>
                )}
            </div>

            {/* Voice Modal Overlay */}
            {showVoiceModal && (
                <div className="glass-modal-overlay" onClick={(e) => { if (e.target === e.currentTarget) setShowVoiceModal(false) }}>
                    <div className="glass-modal">
                        <button className="modal-close" onClick={() => setShowVoiceModal(false)}>
                            <i className="fas fa-times" />
                        </button>
                        <VoiceOnboarding isEmbedded={true} />
                    </div>
                </div>
            )}

            {/* OCR Modal Overlay */}
            {showOcrModal && (
                <div className="glass-modal-overlay" onClick={(e) => { if (e.target === e.currentTarget) setShowOcrModal(false) }}>
                    <div className="glass-modal lg">
                        <button className="modal-close" onClick={() => setShowOcrModal(false)}>
                            <i className="fas fa-times" />
                        </button>
                        <div style={{ padding: "0 16px" }}>
                            <h3 style={{ textAlign: "center", marginBottom: 8, fontSize: "1.4rem" }}>Upload Business Document</h3>
                            <p style={{ textAlign: "center", color: "var(--text-secondary)", marginBottom: 24, fontSize: "0.9rem" }}>
                                We'll extract your details to auto-fill the form behind this window.
                            </p>
                            <DocumentUpload isEmbedded={true} initialDocType={"udyam"} />
                        </div>
                    </div>
                </div>
            )}

            <style jsx>{`
                .fade-in {
                    animation: fadeIn 0.4s ease-out forwards;
                }
                @keyframes fadeIn {
                    from { opacity: 0; transform: translateY(10px); }
                    to { opacity: 1; transform: translateY(0); }
                }
            `}</style>
        </div>
    );
}
