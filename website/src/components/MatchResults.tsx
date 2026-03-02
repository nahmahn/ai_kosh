"use client";

import { useEffect, useState } from "react";

export default function MatchResults({ formData }: { formData: any }) {
    const [loading, setLoading] = useState(true);
    const [data, setData] = useState<any>(null);

    useEffect(() => {
        const fetchMatches = async () => {
            try {
                const res = await fetch("/api/match", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(formData)
                });
                const result = await res.json();
                setData(result);
            } catch (err) {
                console.error(err);
            } finally {
                // Simulate the delays a bit longer for visual effect
                setTimeout(() => setLoading(false), 800);
            }
        };

        fetchMatches();
    }, [formData]);

    if (loading) {
        return (
            <div className="card slide-up" style={{ padding: 60, textAlign: "center", maxWidth: 800, margin: "0 auto" }}>
                <i className="fas fa-network-wired fa-spin fade-inout" style={{ fontSize: "3rem", color: "var(--primary-blue)", marginBottom: 24 }} />
                <h2>Computing MSME-Graph Match...</h2>
                <div style={{ display: "flex", flexDirection: "column", gap: 12, marginTop: 32, maxWidth: 300, margin: "32px auto 0" }}>
                    <div className="status-item"><i className="fas fa-check-circle" style={{ color: "#28a745" }} /> <span>Parsing Verified Capabilities</span></div>
                    <div className="status-item slide-up" style={{ animationDelay: "0.2s" }}><i className="fas fa-sync fa-spin" style={{ color: "var(--accent-orange)" }} /> <span>Constructing HGT Neighbourhood</span></div>
                    <div className="status-item slide-up" style={{ opacity: 0.5, animationDelay: "0.6s" }}><i className="fas fa-lock" /> <span>Querying Federated SNP Models</span></div>
                    <div className="status-item slide-up" style={{ opacity: 0.5, animationDelay: "1s" }}><i className="fas fa-shield-alt" /> <span>Applying IGM Friction Penalty</span></div>
                </div>
                <style jsx>{`
                    .status-item { display: flex; align-items: center; gap: 12px; font-size: 0.95rem; text-align: left; }
                    .fade-inout { animation: fadeInOut 2s infinite ease-in-out; }
                    .slide-up { animation: slideUp 0.6s ease-out forwards; opacity: 0; }
                    @keyframes fadeInOut { 0%, 100% { opacity: 0.5; transform: scale(0.95); } 50% { opacity: 1; transform: scale(1.05); } }
                    @keyframes slideUp { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
                `}</style>
            </div>
        );
    }

    if (!data) return <div className="card" style={{ padding: 40, textAlign: "center", color: "#e53935" }}>Failed to load matches.</div>;

    return (
        <div className="slide-up" style={{ maxWidth: 1000, margin: "0 auto" }}>
            <div style={{ textAlign: "center", marginBottom: 32 }}>
                <span className="section-badge" style={{ margin: "0 auto 12px" }}>Layer 2, 3 & 4</span>
                <h2 style={{ fontSize: "2rem", marginBottom: 8 }}>Your ONDC SNP Matches</h2>
                <p style={{ color: "var(--text-secondary)" }}>{data.inferenceInfo}</p>
            </div>

            <div className="grid-2" style={{ gap: 24, alignItems: "start" }}>
                {/* Left Column: SNP List */}
                <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
                    <h3 style={{ fontSize: "1.2rem", marginBottom: 8 }}><i className="fas fa-trophy" style={{ color: "#F59E0B", marginRight: 8 }} /> Top Recommended SNPs</h3>
                    {data.matches.map((snp: any, idx: number) => (
                        <div key={snp.id} className="card" style={{ padding: 20, position: "relative", border: idx === 0 ? "2px solid var(--primary-blue)" : "1px solid var(--border-color)", overflow: "hidden" }}>
                            {idx === 0 && (
                                <div style={{ position: "absolute", top: -2, right: 20, background: "var(--primary-blue)", color: "white", padding: "4px 12px", borderBottomLeftRadius: 8, borderBottomRightRadius: 8, fontSize: "0.75rem", fontWeight: 700, boxShadow: "0 2px 4px rgba(0,0,0,0.1)" }}>
                                    BEST MATCH
                                </div>
                            )}
                            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 16, marginTop: idx === 0 ? 12 : 0 }}>
                                <div>
                                    <h4 style={{ margin: 0, fontSize: "1.2rem" }}>{snp.name}</h4>
                                    <span style={{ fontSize: "0.85rem", color: "var(--text-secondary)", background: "var(--bg-light)", padding: "4px 8px", borderRadius: 4, display: "inline-block", marginTop: 8, fontWeight: 500 }}>{snp.domain}</span>
                                </div>
                                <div style={{ textAlign: "right" }}>
                                    <div style={{ fontSize: "1.8rem", fontWeight: 800, color: "var(--primary-blue)", lineHeight: 1 }}>{snp.composite_score}</div>
                                    <div style={{ fontSize: "0.65rem", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: 0.5, marginTop: 4 }}>Composite Score</div>
                                </div>
                            </div>

                            <div className="grid-3" style={{ gap: 12, marginBottom: 16, borderTop: "1px solid var(--border-color)", borderBottom: "1px solid var(--border-color)", padding: "16px 0", background: "#f8fafc", margin: "16px -20px", paddingInline: 20 }}>
                                <div style={{ textAlign: "center" }}>
                                    <div style={{ fontSize: "0.7rem", color: "var(--text-muted)", textTransform: "uppercase", marginBottom: 4 }}>Capability (HGT)</div>
                                    <div style={{ fontWeight: 700, fontSize: "1.1rem" }}>{snp.capability_alignment}</div>
                                </div>
                                <div style={{ textAlign: "center", borderLeft: "1px solid var(--border-color)", borderRight: "1px solid var(--border-color)" }}>
                                    <div style={{ fontSize: "0.7rem", color: "var(--text-muted)", textTransform: "uppercase", marginBottom: 4 }}>Success (FL)</div>
                                    <div style={{ fontWeight: 700, fontSize: "1.1rem" }}>{snp.fl_success_prob}</div>
                                </div>
                                <div style={{ textAlign: "center" }}>
                                    <div style={{ fontSize: "0.7rem", color: "var(--text-muted)", textTransform: "uppercase", marginBottom: 4 }}>IGM Friction</div>
                                    <div style={{ fontWeight: 700, fontSize: "1.1rem", color: "var(--accent-orange)" }}>{snp.friction_risk}</div>
                                </div>
                            </div>

                            <div>
                                <h5 style={{ fontSize: "0.85rem", color: "var(--text-muted)", marginBottom: 12, textTransform: "uppercase", letterSpacing: 0.5 }}><i className="fas fa-info-circle" /> SHAP Explanations</h5>
                                <ul style={{ margin: 0, paddingLeft: 0, listStyle: "none", display: "flex", flexDirection: "column", gap: 8 }}>
                                    {snp.shap_explanations.map((exp: any, i: number) => (
                                        <li key={i} style={{ fontSize: "0.85rem", display: "flex", alignItems: "flex-start", gap: 12 }}>
                                            <span style={{
                                                display: "inline-block", minWidth: 46, textAlign: "center", fontWeight: 700,
                                                color: exp.contribution.startsWith("+") ? "#059669" : "#e53935",
                                                background: exp.contribution.startsWith("+") ? "#D1FAE5" : "#fce8e6",
                                                padding: "4px 6px", borderRadius: 6, fontSize: "0.75rem"
                                            }}>
                                                {exp.contribution}
                                            </span>
                                            <div>
                                                <div style={{ fontWeight: 600, color: "var(--text-color)", marginBottom: 2 }}>{exp.feature}</div>
                                                <div style={{ color: "var(--text-muted)", lineHeight: 1.3 }}>{exp.reason}</div>
                                            </div>
                                        </li>
                                    ))}
                                </ul>
                            </div>

                            <button className="btn btn-primary" style={{ width: "100%", marginTop: 20 }}>
                                Proceed with {snp.name} <i className="fas fa-chevron-right" style={{ marginLeft: 8 }} />
                            </button>
                        </div>
                    ))}
                </div>

                {/* Right Column: Knowledge Graph Mock */}
                <div style={{ position: "sticky", top: 40 }}>
                    <div className="card" style={{ padding: 24 }}>
                        <h3 style={{ fontSize: "1.1rem", marginBottom: 16 }}><i className="fas fa-project-diagram" style={{ color: "var(--primary-blue)", marginRight: 8 }} /> Layer 2: Heterogeneous Graph</h3>
                        <p style={{ fontSize: "0.85rem", color: "var(--text-secondary)", marginBottom: 20, lineHeight: 1.5 }}>
                            How MSME-Graph resolved your cold-start matches using inductive node embeddings.
                        </p>

                        <div style={{ background: "#1e293b", borderRadius: 12, padding: 20, fontFamily: "'JetBrains Mono', monospace", fontSize: "0.8rem", color: "#f8fafc", boxShadow: "inset 0 2px 4px rgba(0,0,0,0.1)" }}>
                            {data.graph.edges.map((e: any, i: number) => (
                                <div key={i} style={{ display: "flex", margin: "6px 0", alignItems: "center", opacity: e.source === "mse-new" ? 1 : 0.7 }}>
                                    <span style={{ color: e.source.includes("new") ? "#38bdf8" : "#94a3b8", fontWeight: 600, width: 85, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis", display: "inline-block" }}>{e.source}</span>
                                    <span style={{ color: "#475569", margin: "0 8px" }}>—[</span>
                                    <span style={{ color: "#fbbf24" }}>{e.label}</span>
                                    <span style={{ color: "#475569", margin: "0 8px" }}>]→</span>
                                    <span style={{ color: e.target.includes("snp") ? "#a78bfa" : "#34d399", fontWeight: 600, flex: 1, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{e.target}</span>
                                </div>
                            ))}
                        </div>

                        <div style={{ marginTop: 24, fontSize: "0.85rem", color: "var(--text-secondary)", padding: 16, border: "1px solid #10B981", background: "#ECFDF5", borderRadius: 8, display: "flex", gap: 12 }}>
                            <i className="fas fa-shield-check" style={{ color: "#10B981", fontSize: "1.2rem" }} />
                            <div>
                                <strong style={{ color: "#065F46", display: "block", marginBottom: 4 }}>DPDP Act Compliant</strong>
                                <span style={{ color: "#047857", lineHeight: 1.4, display: "block" }}>Federated model querying was performed securely. Zero raw transaction data left SNP infrastructure.</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            <style jsx>{`
                .slide-up { animation: MathSlideUp 0.5s ease-out forwards; opacity: 0; }
                @keyframes MathSlideUp { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }
            `}</style>
        </div>
    );
}
