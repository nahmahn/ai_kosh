"use client";

import { useEffect, useRef } from "react";

const layers = [
    {
        id: "L1",
        title: "Document-Grounded Capability Inference",
        desc: "Extracts verified capabilities from Udyam, GST, invoices & multilingual voice — replacing unreliable self-declared forms.",
        icon: "fas fa-fingerprint",
        color: "#28a745",
        bg: "rgba(40, 167, 69, 0.08)",
        models: ["LayoutLMv3", "Donut", "IndicASR", "Whisper"],
        output: "Verified Capability Fingerprint"
    },
    {
        id: "L2",
        title: "Heterogeneous Knowledge Graph",
        desc: "Maps the entire MSME-ONDC ecosystem to enable semantic matching and cold-start resolution for new enterprises.",
        icon: "fas fa-project-diagram",
        color: "#38bdf8",
        bg: "rgba(56, 189, 248, 0.08)",
        models: ["GraphSAGE", "HGT"],
        output: "Inductive Node Embeddings"
    },
    {
        id: "L3",
        title: "Federated SNP Performance",
        desc: "Privacy-preserving prediction of 90-day transaction success — zero raw data ever leaves SNP infrastructure.",
        icon: "fas fa-lock",
        color: "#a78bfa",
        bg: "rgba(167, 139, 250, 0.08)",
        models: ["Flower", "FedAvg", "SecAgg"],
        output: "P(Success | MSE, SNP)"
    },
    {
        id: "L4",
        title: "Friction-Aware Composite Score",
        desc: "Final ranked recommendations penalized by IGM dispute history, with SHAP-based explainability and fairness audits.",
        icon: "fas fa-balance-scale",
        color: "#f59e0b",
        bg: "rgba(245, 158, 11, 0.08)",
        models: ["SHAP", "IGM API", "Fairness Audit"],
        output: "Top-3 SNP Recommendations"
    },
];

export default function Architecture() {
    const ref = useRef<HTMLDivElement>(null);

    useEffect(() => {
        const observer = new IntersectionObserver(
            (entries) =>
                entries.forEach((e) => e.isIntersecting && e.target.classList.add("visible")),
            { threshold: 0.1 }
        );
        ref.current?.querySelectorAll(".animate-in").forEach((el) => observer.observe(el));
        return () => observer.disconnect();
    }, []);

    return (
        <section
            className="section section-alt"
            id="architecture"
            ref={ref}
            style={{ position: "relative", overflow: "hidden" }}
        >
            <div className="container" style={{ position: "relative", zIndex: 2 }}>
                <span className="section-badge animate-in">Technical Architecture</span>
                <h2 className="section-title animate-in" style={{ animationDelay: "0.1s" }}>
                    4-Layer AI Pipeline
                </h2>
                <p className="section-subtitle animate-in" style={{ animationDelay: "0.2s", maxWidth: 640 }}>
                    From document parsing to intelligent matching — each layer adds a new dimension of intelligence.
                </p>

                <div className="grid-2" style={{ marginTop: 40, gap: 20 }}>
                    {layers.map((layer, i) => (
                        <div
                            key={layer.id}
                            className={`arch-card arch-card-${layer.id.toLowerCase()} animate-in`}
                            style={{ animationDelay: `${0.3 + i * 0.12}s` }}
                        >
                            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                                <div
                                    className="arch-icon"
                                    style={{ background: layer.bg, color: layer.color }}
                                >
                                    <i className={layer.icon} />
                                </div>
                                <span style={{
                                    fontFamily: "var(--font-heading)",
                                    fontSize: "2rem",
                                    fontWeight: 800,
                                    color: `${layer.color}15`,
                                    lineHeight: 1
                                }}>
                                    {layer.id}
                                </span>
                            </div>

                            <h3 style={{ fontSize: "1.05rem", marginBottom: 8, color: "var(--dark-blue)" }}>
                                {layer.title}
                            </h3>
                            <p style={{ fontSize: "0.85rem", color: "var(--text-muted)", lineHeight: 1.6, margin: 0 }}>
                                {layer.desc}
                            </p>

                            <div className="arch-models">
                                {layer.models.map((m) => (
                                    <span key={m} className="arch-model-tag">{m}</span>
                                ))}
                            </div>

                            <div style={{
                                marginTop: 14,
                                padding: "8px 12px",
                                borderRadius: 8,
                                background: layer.bg,
                                fontSize: "0.75rem",
                                fontWeight: 600,
                                color: layer.color,
                                display: "inline-flex",
                                alignItems: "center",
                                gap: 6
                            }}>
                                <i className="fas fa-arrow-right" style={{ fontSize: "0.65rem" }} />
                                {layer.output}
                            </div>
                        </div>
                    ))}
                </div>

                {/* DPDP + ONDC Compliance Bar */}
                <div
                    className="animate-in"
                    style={{
                        animationDelay: "0.8s",
                        marginTop: 32,
                        padding: "20px 28px",
                        borderRadius: 14,
                        background: "linear-gradient(135deg, #0f172a, #1e293b)",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        gap: 40,
                        flexWrap: "wrap"
                    }}
                >
                    <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                        <i className="fas fa-shield-alt" style={{ color: "#10B981", fontSize: "1.3rem" }} />
                        <div>
                            <div style={{ color: "#10B981", fontWeight: 700, fontSize: "0.85rem" }}>DPDP Act 2023</div>
                            <div style={{ color: "#94a3b8", fontSize: "0.72rem" }}>Full Compliance</div>
                        </div>
                    </div>
                    <div style={{ width: 1, height: 30, background: "rgba(255,255,255,0.1)" }} />
                    <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                        <i className="fas fa-plug" style={{ color: "#38bdf8", fontSize: "1.3rem" }} />
                        <div>
                            <div style={{ color: "#38bdf8", fontWeight: 700, fontSize: "0.85rem" }}>ONDC Beckn v1.2.0</div>
                            <div style={{ color: "#94a3b8", fontSize: "0.72rem" }}>Protocol Integrated</div>
                        </div>
                    </div>
                    <div style={{ width: 1, height: 30, background: "rgba(255,255,255,0.1)" }} />
                    <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                        <i className="fas fa-lock" style={{ color: "#a78bfa", fontSize: "1.3rem" }} />
                        <div>
                            <div style={{ color: "#a78bfa", fontWeight: 700, fontSize: "0.85rem" }}>Federated Learning</div>
                            <div style={{ color: "#94a3b8", fontSize: "0.72rem" }}>Zero Data Leakage</div>
                        </div>
                    </div>
                </div>
            </div>
        </section>
    );
}
