"use client";

import { useEffect, useRef } from "react";

const layers = [
    {
        icon: "fas fa-file-invoice",
        title: "Document-Grounded Capability Inference",
        desc: "LayoutLMv3 and Sarvam Vision API extract verified capabilities from Udyam certificates, GST returns, bank statements, and e-invoices — no manual data entry needed.",
        tech: "LayoutLMv3 · Gemini 2.5 Flash · Sarvam Vision",
    },
    {
        icon: "fas fa-project-diagram",
        title: "Heterogeneous Knowledge Graph",
        desc: "GraphSAGE and HGT model relationships between MSEs, Seller Network Participants, and products — enabling cold-start recommendations for new enterprises.",
        tech: "Neo4j · PyTorch Geometric · GraphSAGE · HGT",
    },
    {
        icon: "fas fa-lock",
        title: "Privacy-Preserving Federated Learning",
        desc: "Flower framework enables SNP performance modelling without sharing sensitive transaction data — fully compliant with DPDP Act 2023.",
        tech: "Flower (flwr.ai) · Differential Privacy · DPDP Act",
    },
    {
        icon: "fas fa-balance-scale",
        title: "Friction-Aware Matching Score",
        desc: "Composite scoring balances capability alignment, success probability, and dispute risk — with demographic parity audits for women-led and SC/ST enterprises.",
        tech: "Custom Scoring · Fairness Constraints · NSIC Gate 3",
    },
];

export default function HowItWorks() {
    const ref = useRef<HTMLDivElement>(null);

    useEffect(() => {
        const observer = new IntersectionObserver(
            (entries) => entries.forEach((e) => e.isIntersecting && e.target.classList.add("visible")),
            { threshold: 0.1 }
        );
        ref.current?.querySelectorAll(".animate-in").forEach((el) => observer.observe(el));
        return () => observer.disconnect();
    }, []);

    return (
        <section className="section section-alt" id="how-it-works" ref={ref}>
            <div className="container">
                <span className="section-badge">Architecture</span>
                <h2 className="section-title">Four-Layer AI Architecture</h2>
                <p className="section-subtitle">
                    Each layer addresses a specific bottleneck in the MSME TEAM portal,
                    from raw document processing to intelligent SNP matching.
                </p>

                <div className="grid-2">
                    {layers.map((layer, i) => (
                        <div
                            key={i}
                            className="card step-card animate-in"
                            style={{ "--i": i } as React.CSSProperties}
                        >
                            <span className="step-number">{String(i + 1).padStart(2, "0")}</span>
                            <div className="card-icon">
                                <i className={layer.icon} />
                            </div>
                            <h3 className="card-title">{layer.title}</h3>
                            <p className="card-text">{layer.desc}</p>
                            <p
                                style={{
                                    marginTop: "16px",
                                    fontSize: "0.75rem",
                                    color: "var(--primary-blue)",
                                    fontWeight: 600,
                                    fontFamily: "var(--font-heading)",
                                    letterSpacing: "0.3px",
                                }}
                            >
                                {layer.tech}
                            </p>
                        </div>
                    ))}
                </div>
            </div>
        </section>
    );
}
