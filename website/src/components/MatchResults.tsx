"use client";

import { useEffect, useState, useRef, useCallback } from "react";

/* ─── Animated Counter ─── */
function AnimCounter({ target, duration = 1200, decimals = 2, prefix = "", suffix = "" }: { target: number, duration?: number, decimals?: number, prefix?: string, suffix?: string }) {
    const [val, setVal] = useState(0);
    const ref = useRef<number>(0);
    useEffect(() => {
        const start = performance.now();
        const step = (now: number) => {
            const t = Math.min((now - start) / duration, 1);
            const eased = 1 - Math.pow(1 - t, 3);
            setVal(eased * target);
            if (t < 1) ref.current = requestAnimationFrame(step);
        };
        ref.current = requestAnimationFrame(step);
        return () => cancelAnimationFrame(ref.current);
    }, [target, duration]);
    return <span>{prefix}{val.toFixed(decimals)}{suffix}</span>;
}

/* ─── Progress Bar ─── */
function ProgressBar({ value, max = 1, color = "var(--primary-blue)", delay = 0 }: { value: number, max?: number, color?: string, delay?: number }) {
    const [width, setWidth] = useState(0);
    useEffect(() => {
        const t = setTimeout(() => setWidth((value / max) * 100), delay);
        return () => clearTimeout(t);
    }, [value, max, delay]);
    return (
        <div style={{ height: 8, borderRadius: 4, background: "rgba(28,117,188,0.08)", overflow: "hidden", width: "100%" }}>
            <div style={{ height: "100%", width: `${width}%`, background: color, borderRadius: 4, transition: "width 0.8s cubic-bezier(0.16,1,0.3,1)" }} />
        </div>
    );
}

/* ─── Mini Bar Chart for FL Convergence ─── */
function ConvergenceChart({ data }: { data: { round: number, loss: number, accuracy: number }[] }) {
    const maxLoss = Math.max(...data.map(d => d.loss));
    return (
        <div style={{ display: "flex", alignItems: "flex-end", gap: 6, height: 100, padding: "0 4px" }}>
            {data.map((d, i) => (
                <div key={i} style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", gap: 4 }}>
                    <span style={{ fontSize: "0.65rem", color: "var(--text-muted)", fontWeight: 600 }}>
                        {d.accuracy.toFixed(2)}
                    </span>
                    <div style={{
                        width: "100%", borderRadius: "4px 4px 0 0", minHeight: 4,
                        height: `${(d.accuracy) * 80}px`,
                        background: `linear-gradient(180deg, #10B981 0%, ${i === data.length - 1 ? '#059669' : '#34D399'} 100%)`,
                        transition: "height 0.6s cubic-bezier(0.16,1,0.3,1)",
                        transitionDelay: `${i * 200}ms`,
                        boxShadow: i === data.length - 1 ? "0 0 12px rgba(16,185,129,0.4)" : "none"
                    }} />
                    <span style={{ fontSize: "0.6rem", color: "var(--text-muted)" }}>R{d.round}</span>
                </div>
            ))}
        </div>
    );
}

/* ─── SVG Graph Visualization ─── */
function GraphVisualization({ edges, meta }: { edges: any[], meta: any }) {
    // Map node names to positions for a simple force-directed-ish layout
    const nodeSet = new Set<string>();
    edges.forEach(e => { nodeSet.add(e.source); nodeSet.add(e.target); });
    const nodes = Array.from(nodeSet);

    const getNodeColor = (id: string) => {
        if (id.includes("mse-new")) return "#38bdf8";
        if (id.includes("mse-sim")) return "#7dd3fc";
        if (id.includes("snp")) return "#a78bfa";
        if (id.includes("cat") || id.includes("4S")) return "#fbbf24";
        if (id.includes("loc")) return "#34d399";
        return "#94a3b8";
    };

    const getNodeLabel = (id: string) => {
        if (id === "mse-new") return "Your MSE";
        if (id.includes("mse-sim")) return id.replace("mse-", "Similar ");
        if (id.includes("snp")) return id.replace("snp-", "").replace(/-/g, " ").slice(0, 12);
        return id.replace("loc-", "").replace("cat-", "");
    };

    // Simple radial layout
    const cx = 220, cy = 140, r = 100;
    const positions: Record<string, { x: number, y: number }> = {};
    nodes.forEach((n, i) => {
        if (n === "mse-new") {
            positions[n] = { x: cx, y: cy };
        } else {
            const angle = (2 * Math.PI * i) / (nodes.length - 1) - Math.PI / 2;
            positions[n] = { x: cx + r * Math.cos(angle), y: cy + r * Math.sin(angle) };
        }
    });

    return (
        <svg viewBox="0 0 440 280" style={{ width: "100%", borderRadius: 12, background: "#0f172a" }}>
            <defs>
                <marker id="arrow" viewBox="0 0 10 7" refX="10" refY="3.5" markerWidth="8" markerHeight="6" orient="auto">
                    <polygon points="0 0, 10 3.5, 0 7" fill="#475569" />
                </marker>
                <filter id="glow">
                    <feGaussianBlur stdDeviation="3" result="blur" />
                    <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
                </filter>
            </defs>

            {/* Edges */}
            {edges.map((e: any, i: number) => {
                const s = positions[e.source], t = positions[e.target];
                if (!s || !t) return null;
                const isInferred = e.type === "inferred";
                return (
                    <g key={i}>
                        <line
                            x1={s.x} y1={s.y} x2={t.x} y2={t.y}
                            stroke={isInferred ? "#38bdf8" : "#334155"}
                            strokeWidth={isInferred ? 2 : 1}
                            strokeDasharray={isInferred ? "6 3" : "none"}
                            markerEnd="url(#arrow)"
                            filter={isInferred ? "url(#glow)" : "none"}
                            style={{ opacity: 0, animation: `gEdgeFadeIn 0.5s ${i * 0.15}s forwards` }}
                        />
                        <text
                            x={(s.x + t.x) / 2} y={(s.y + t.y) / 2 - 6}
                            fill="#64748b" fontSize="6" textAnchor="middle"
                            style={{ opacity: 0, animation: `gEdgeFadeIn 0.5s ${i * 0.15 + 0.3}s forwards` }}
                        >{e.label}</text>
                    </g>
                );
            })}

            {/* Nodes */}
            {nodes.map((n, i) => {
                const p = positions[n];
                if (!p) return null;
                const isCenter = n === "mse-new";
                return (
                    <g key={n} style={{ opacity: 0, animation: `gNodePop 0.4s ${i * 0.1}s forwards` }}>
                        <circle
                            cx={p.x} cy={p.y} r={isCenter ? 18 : 12}
                            fill={getNodeColor(n)}
                            stroke={isCenter ? "#fff" : "transparent"}
                            strokeWidth={isCenter ? 2 : 0}
                            filter={isCenter ? "url(#glow)" : "none"}
                        />
                        {isCenter && (
                            <circle cx={p.x} cy={p.y} r={22} fill="none" stroke="#38bdf8" strokeWidth={1} opacity={0.3}>
                                <animate attributeName="r" from="18" to="30" dur="2s" repeatCount="indefinite" />
                                <animate attributeName="opacity" from="0.5" to="0" dur="2s" repeatCount="indefinite" />
                            </circle>
                        )}
                        <text
                            x={p.x} y={p.y + (isCenter ? 30 : 22)}
                            fill="#cbd5e1" fontSize={isCenter ? "8" : "7"} textAnchor="middle" fontWeight={isCenter ? "700" : "400"}
                        >{getNodeLabel(n)}</text>
                    </g>
                );
            })}
        </svg>
    );
}

/* ─── Proceed Confirmation Modal ─── */
function ProceedModal({ snp, step, setStep, onClose }: { snp: any, step: number, setStep: (s: number) => void, onClose: () => void }) {
    const [confirmed, setConfirmed] = useState(false);

    useEffect(() => {
        if (!confirmed) return;
        const steps = [800, 1200, 1000, 800];
        let timeouts: NodeJS.Timeout[] = [];
        let cum = 0;
        steps.forEach((d, i) => {
            cum += d;
            timeouts.push(setTimeout(() => setStep(i + 1), cum));
        });
        return () => timeouts.forEach(clearTimeout);
    }, [confirmed, setStep]);

    const stages = [
        { icon: "fa-id-card", text: "Verifying MSE Capability Fingerprint..." },
        { icon: "fa-network-wired", text: "Registering with ONDC Gateway (Beckn v1.2.0)..." },
        { icon: "fa-handshake", text: `Subscribing to ${snp.name}...` },
        { icon: "fa-check-double", text: "Onboarding Complete!" }
    ];

    return (
        <div className="glass-modal-overlay" onClick={(e) => { if (e.target === e.currentTarget && !confirmed) onClose(); }}>
            <div className="glass-modal" style={{ maxWidth: 520, padding: 40, textAlign: "center" }}>
                {!confirmed ? (
                    <>
                        <div style={{ width: 64, height: 64, borderRadius: 16, background: "rgba(28,117,188,0.08)", display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto 20px", fontSize: "1.6rem", color: "var(--primary-blue)" }}>
                            <i className="fas fa-rocket" />
                        </div>
                        <h3 style={{ fontSize: "1.4rem", marginBottom: 8 }}>Proceed with {snp.name}?</h3>
                        <p style={{ color: "var(--text-muted)", fontSize: "0.9rem", marginBottom: 8 }}>
                            Domain: <strong>{snp.domain}</strong> · Composite Score: <strong>{snp.composite_score}</strong>
                        </p>
                        <p style={{ color: "var(--text-muted)", fontSize: "0.82rem", marginBottom: 28 }}>
                            This will initiate your ONDC onboarding with this Seller Network Participant via the Beckn Protocol.
                        </p>
                        <div style={{ display: "flex", gap: 12, justifyContent: "center" }}>
                            <button className="btn btn-outline" onClick={onClose} style={{ borderRadius: 10 }}>
                                Cancel
                            </button>
                            <button className="btn btn-primary" onClick={() => setConfirmed(true)} style={{ borderRadius: 10 }}>
                                <i className="fas fa-check" /> Confirm & Proceed
                            </button>
                        </div>
                    </>
                ) : step < 4 ? (
                    <>
                        <div className="match-loading-icon" style={{ width: 64, height: 64, margin: "0 auto 20px", fontSize: "1.5rem" }}>
                            <i className="fas fa-cog fa-spin" />
                            <div className="match-loading-pulse" />
                        </div>
                        <h3 style={{ fontSize: "1.2rem", marginBottom: 24 }}>Initiating ONDC Onboarding</h3>
                        <div style={{ textAlign: "left", maxWidth: 340, margin: "0 auto", display: "flex", flexDirection: "column", gap: 14 }}>
                            {stages.map((s, i) => {
                                const done = step > i;
                                const active = step === i;
                                return (
                                    <div key={i} style={{ display: "flex", alignItems: "center", gap: 12, opacity: step >= i ? 1 : 0.3, transition: "all 0.4s ease" }}>
                                        <div style={{ width: 24, textAlign: "center", color: done ? "#10B981" : (active ? "var(--primary-blue)" : "var(--text-muted)") }}>
                                            {done ? <i className="fas fa-check-circle" /> : active ? <i className={`fas ${s.icon} fa-spin`} /> : <i className={`fas ${s.icon}`} />}
                                        </div>
                                        <span style={{ fontSize: "0.88rem", fontWeight: active ? 600 : 400 }}>{s.text}</span>
                                    </div>
                                );
                            })}
                        </div>
                    </>
                ) : (
                    <div className="fade-in-panel">
                        <div style={{ width: 80, height: 80, borderRadius: "50%", background: "#D1FAE5", display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto 20px", fontSize: "2rem", color: "#059669" }}>
                            <i className="fas fa-check" />
                        </div>
                        <h3 style={{ fontSize: "1.5rem", marginBottom: 8, color: "#059669" }}>Onboarding Successful!</h3>
                        <p style={{ color: "var(--text-muted)", fontSize: "0.9rem", marginBottom: 6 }}>
                            You are now registered with <strong>{snp.name}</strong> on the ONDC network.
                        </p>
                        <p style={{ color: "var(--text-muted)", fontSize: "0.82rem", marginBottom: 28 }}>
                            Your Beckn subscriber ID has been generated. NSIC verification is in progress.
                        </p>
                        <div style={{ padding: 16, borderRadius: 10, background: "#f0fdf4", border: "1px solid #bbf7d0", marginBottom: 24, textAlign: "left" }}>
                            <div style={{ fontSize: "0.75rem", color: "#065F46", fontWeight: 700, textTransform: "uppercase", letterSpacing: 0.5, marginBottom: 8 }}>Registration Summary</div>
                            <div style={{ display: "flex", flexDirection: "column", gap: 6, fontSize: "0.82rem", color: "var(--text-secondary)" }}>
                                <div><strong>SNP:</strong> {snp.name}</div>
                                <div><strong>Domain:</strong> {snp.domain}</div>
                                <div><strong>Score:</strong> {snp.composite_score}</div>
                                <div><strong>Protocol:</strong> Beckn v1.2.0</div>
                                <div><strong>Status:</strong> <span style={{ color: "#059669", fontWeight: 600 }}>Active</span></div>
                            </div>
                        </div>
                        <button className="btn btn-primary" onClick={onClose} style={{ borderRadius: 10 }}>
                            <i className="fas fa-home" /> Back to Results
                        </button>
                    </div>
                )}
            </div>
        </div>
    );
}

/* ═══ Main MatchResults Component ═══ */
export default function MatchResults({ formData }: { formData: any }) {
    const [loading, setLoading] = useState(true);
    const [loadingStep, setLoadingStep] = useState(0);
    const [data, setData] = useState<any>(null);
    const [expandedSnp, setExpandedSnp] = useState<string | null>(null);
    const [activeLayer, setActiveLayer] = useState<number>(2);
    const [selectedSnp, setSelectedSnp] = useState<any>(null);
    const [proceedStep, setProceedStep] = useState(0);

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
            }
        };
        fetchMatches();
    }, [formData]);

    // Cinematic loading step sequence
    useEffect(() => {
        if (!data) return;
        const steps = [
            { delay: 600 },   // step 0 → 1
            { delay: 1000 },  // step 1 → 2
            { delay: 1200 },  // step 2 → 3
            { delay: 1000 },  // step 3 → 4
            { delay: 800 }    // step 4 → done
        ];
        let timeouts: NodeJS.Timeout[] = [];
        let cumDelay = 0;
        steps.forEach((s, i) => {
            cumDelay += s.delay;
            timeouts.push(setTimeout(() => setLoadingStep(i + 1), cumDelay));
        });
        timeouts.push(setTimeout(() => setLoading(false), cumDelay + 400));
        return () => timeouts.forEach(clearTimeout);
    }, [data]);

    /* ─── Loading Screen ─── */
    if (loading) {
        const statuses = [
            { icon: "fa-fingerprint", text: "Parsing Verified Capability Fingerprint", color: "#28a745", label: "L1" },
            { icon: "fa-project-diagram", text: "Constructing HGT Neighbourhood (Layer 2)", color: "#38bdf8", label: "L2" },
            { icon: "fa-lock", text: "Querying Federated SNP Models (Layer 3)", color: "#a78bfa", label: "L3" },
            { icon: "fa-balance-scale", text: "Applying IGM Friction Penalty (Layer 4)", color: "#fbbf24", label: "L4" },
            { icon: "fa-shield-alt", text: "DPDP Compliance Verified — Results Ready", color: "#10B981", label: "✓" }
        ];

        return (
            <div className="match-loading-container">
                <div className="match-loading-card" style={{ maxWidth: 640 }}>
                    <div className="match-loading-icon">
                        <i className="fas fa-network-wired" />
                        <div className="match-loading-pulse" />
                    </div>
                    <h2 style={{ fontSize: "1.6rem", marginBottom: 6 }}>Computing MSME-Graph Match</h2>
                    <p style={{ color: "var(--text-muted)", fontSize: "0.9rem", marginBottom: 28 }}>
                        Running 4-layer AI inference pipeline...
                    </p>

                    {/* ── Horizontal Pipeline Visualization ── */}
                    <div className="pipeline-viz">
                        {statuses.slice(0, 4).map((s, i) => {
                            const isDone = loadingStep > i;
                            const isActive = loadingStep === i;
                            return (
                                <div key={i} className="pipeline-node-group">
                                    <div className={`pipeline-node ${isDone ? 'done' : ''} ${isActive ? 'active' : ''}`}
                                        style={{ borderColor: isDone || isActive ? s.color : "rgba(28,117,188,0.15)" }}>
                                        {isDone ? (
                                            <i className="fas fa-check" style={{ color: s.color, fontSize: "1rem" }} />
                                        ) : isActive ? (
                                            <i className={`fas ${s.icon} fa-spin`} style={{ color: s.color, fontSize: "1rem" }} />
                                        ) : (
                                            <i className={`fas ${s.icon}`} style={{ color: "var(--text-muted)", fontSize: "0.9rem" }} />
                                        )}
                                        {isActive && <div className="pipeline-node-ring" style={{ borderColor: s.color }} />}
                                    </div>
                                    <span className="pipeline-label" style={{ color: isDone || isActive ? "var(--text-primary)" : "var(--text-muted)", fontWeight: isDone || isActive ? 600 : 400 }}>
                                        {s.label}
                                    </span>
                                    {i < 3 && (
                                        <div className="pipeline-arrow">
                                            <div className="pipeline-arrow-line" style={{ background: loadingStep > i ? s.color : "rgba(28,117,188,0.12)" }} />
                                            <div className="pipeline-arrow-head" style={{ borderLeftColor: loadingStep > i ? statuses[i + 1].color : "rgba(28,117,188,0.12)" }} />
                                        </div>
                                    )}
                                </div>
                            );
                        })}
                    </div>

                    {/* ── Step Details ── */}
                    <div style={{ display: "flex", flexDirection: "column", gap: 12, maxWidth: 420, margin: "28px auto 0", textAlign: "left" }}>
                        {statuses.map((s, i) => {
                            const isDone = loadingStep > i;
                            const isActive = loadingStep === i;

                            return (
                                <div key={i} className={`match-status-row ${isDone ? 'done' : ''} ${isActive ? 'active' : ''}`}
                                    style={{ opacity: loadingStep >= i ? 1 : 0.3, transition: "all 0.5s ease" }}>
                                    <div className="match-status-icon" style={{ color: isDone ? s.color : (isActive ? s.color : "var(--text-muted)") }}>
                                        {isDone ? <i className="fas fa-check-circle" /> : (isActive ? <i className={`fas ${s.icon} fa-spin`} /> : <i className={`fas ${s.icon}`} />)}
                                    </div>
                                    <span style={{ fontWeight: isActive ? 600 : 400, color: isDone ? "var(--text-primary)" : "var(--text-muted)", fontSize: "0.88rem" }}>
                                        {s.text}
                                    </span>
                                </div>
                            );
                        })}
                    </div>

                    {/* Mini progress bar */}
                    <div style={{ marginTop: 28, maxWidth: 300, margin: "28px auto 0" }}>
                        <ProgressBar value={loadingStep} max={5} color="var(--primary-blue)" />
                        <div style={{ textAlign: "center", marginTop: 8, fontSize: "0.75rem", color: "var(--text-muted)" }}>
                            Step {loadingStep}/5
                        </div>
                    </div>
                </div>
            </div>
        );
    }

    if (!data) return <div className="card" style={{ padding: 40, textAlign: "center", color: "#e53935" }}>Failed to load matches.</div>;

    /* ─── Main Results View ─── */
    return (
        <div className="match-results-page">
            {/* ── Header ── */}
            <div className="match-results-header">
                <span className="section-badge" style={{ margin: "0 auto 12px" }}>Layer 2, 3 & 4</span>
                <h2 style={{ fontSize: "2rem", marginBottom: 8 }}>Your ONDC SNP Matches</h2>
                <p style={{ color: "var(--text-secondary)" }}>{data.inferenceInfo}</p>
                <div className="match-meta-badges">
                    <span className="match-meta-badge"><i className="fas fa-clock" /> {data.processingTime}</span>
                    <span className="match-meta-badge"><i className="fas fa-plug" /> {data.ondcProtocol}</span>
                    <span className="match-meta-badge success"><i className="fas fa-shield-alt" /> DPDP Compliant</span>
                </div>
            </div>

            {/* ── Layer Tab Switcher ── */}
            <div className="layer-tab-bar">
                {[
                    { id: 2, icon: "fa-project-diagram", label: "Knowledge Graph" },
                    { id: 3, icon: "fa-server", label: "Federated Learning" },
                    { id: 4, icon: "fa-balance-scale", label: "Friction Scoring" }
                ].map(tab => (
                    <button key={tab.id}
                        className={`layer-tab ${activeLayer === tab.id ? 'active' : ''}`}
                        onClick={() => setActiveLayer(tab.id)}>
                        <i className={`fas ${tab.icon}`} />
                        <span>Layer {tab.id}</span>
                        <small>{tab.label}</small>
                    </button>
                ))}
            </div>

            {/* ── Layer Content ── */}
            <div className="match-grid">
                {/* Left: Layer Panels */}
                <div className="layer-panels">
                    {/* Layer 2 */}
                    {activeLayer === 2 && (
                        <div className="layer-panel fade-in-panel">
                            <div className="layer-panel-header">
                                <div className="layer-number">L2</div>
                                <div>
                                    <h3 style={{ margin: 0, fontSize: "1.15rem" }}>Heterogeneous Knowledge Graph</h3>
                                    <p style={{ margin: 0, fontSize: "0.82rem", color: "var(--text-muted)" }}>Cold-start resolution via inductive node embeddings</p>
                                </div>
                            </div>

                            <GraphVisualization edges={data.graph.edges} meta={data.graph.meta} />

                            <div className="layer-stats-grid">
                                <div className="layer-stat">
                                    <div className="layer-stat-value"><AnimCounter target={data.graph.meta.totalNodes} decimals={0} /></div>
                                    <div className="layer-stat-label">Nodes</div>
                                </div>
                                <div className="layer-stat">
                                    <div className="layer-stat-value"><AnimCounter target={data.graph.meta.totalEdges} decimals={0} /></div>
                                    <div className="layer-stat-label">Edges</div>
                                </div>
                                <div className="layer-stat">
                                    <div className="layer-stat-value">{data.graph.meta.embeddingDim}d</div>
                                    <div className="layer-stat-label">Embedding</div>
                                </div>
                                <div className="layer-stat">
                                    <div className="layer-stat-value">{data.graph.meta.neighbourhoodHops}-hop</div>
                                    <div className="layer-stat-label">Depth</div>
                                </div>
                            </div>

                            <div className="layer-detail-box">
                                <h5><i className="fas fa-wave-square" style={{ marginRight: 6 }} /> Cosine Similarity Scores</h5>
                                {data.graph.meta.cosineScores.map((cs: any, i: number) => (
                                    <div key={i} className="cosine-row">
                                        <span className="cosine-name">{cs.snp}</span>
                                        <ProgressBar value={cs.score} color={i === 0 ? "#38bdf8" : i === 1 ? "#a78bfa" : "#fbbf24"} delay={i * 200} />
                                        <span className="cosine-score">{cs.score.toFixed(2)}</span>
                                    </div>
                                ))}
                            </div>

                            <div className="layer-info-tag">
                                <i className="fas fa-lightbulb" /> {data.graph.meta.coldStartResolution}
                            </div>
                        </div>
                    )}

                    {/* Layer 3 */}
                    {activeLayer === 3 && (
                        <div className="layer-panel fade-in-panel">
                            <div className="layer-panel-header">
                                <div className="layer-number" style={{ background: "rgba(167,139,250,0.12)", color: "#a78bfa" }}>L3</div>
                                <div>
                                    <h3 style={{ margin: 0, fontSize: "1.15rem" }}>Federated Learning Dashboard</h3>
                                    <p style={{ margin: 0, fontSize: "0.82rem", color: "var(--text-muted)" }}>Privacy-preserving SNP performance modelling</p>
                                </div>
                            </div>

                            <div className="fl-headline-stats">
                                <div className="fl-headline-stat">
                                    <div className="fl-headline-value" style={{ color: "#10B981" }}>
                                        <AnimCounter target={data.federatedLearning.globalModelAccuracy * 100} decimals={1} suffix="%" />
                                    </div>
                                    <div className="fl-headline-label">Global Accuracy</div>
                                </div>
                                <div className="fl-headline-stat">
                                    <div className="fl-headline-value" style={{ color: "#a78bfa" }}>{data.federatedLearning.totalRounds}</div>
                                    <div className="fl-headline-label">FL Rounds</div>
                                </div>
                                <div className="fl-headline-stat">
                                    <div className="fl-headline-value" style={{ color: "#38bdf8" }}>{data.federatedLearning.participatingClients}</div>
                                    <div className="fl-headline-label">Clients</div>
                                </div>
                                <div className="fl-headline-stat">
                                    <div className="fl-headline-value" style={{ color: "#fbbf24" }}>{data.federatedLearning.predictionLatency}</div>
                                    <div className="fl-headline-label">Latency</div>
                                </div>
                            </div>

                            <h5 style={{ fontSize: "0.85rem", color: "var(--text-muted)", marginBottom: 12, textTransform: "uppercase", letterSpacing: 0.5 }}>
                                <i className="fas fa-chart-bar" style={{ marginRight: 6 }} /> Model Convergence (Accuracy per Round)
                            </h5>
                            <ConvergenceChart data={data.federatedLearning.convergenceData} />

                            <h5 style={{ fontSize: "0.85rem", color: "var(--text-muted)", marginTop: 24, marginBottom: 12, textTransform: "uppercase", letterSpacing: 0.5 }}>
                                <i className="fas fa-server" style={{ marginRight: 6 }} /> Participating SNP Nodes
                            </h5>
                            <div className="fl-clients-grid">
                                {data.federatedLearning.clients.map((c: any, i: number) => (
                                    <div key={i} className="fl-client-card">
                                        <div className="fl-client-dot" />
                                        <div>
                                            <div className="fl-client-name">{c.name}</div>
                                            <div className="fl-client-meta">{c.samplesUsed.toLocaleString()} samples · <span style={{ color: "#10B981" }}>{c.status}</span></div>
                                        </div>
                                    </div>
                                ))}
                            </div>

                            <div className="fl-security-box">
                                <div className="fl-security-header">
                                    <i className="fas fa-lock" style={{ color: "#a78bfa" }} />
                                    <span>{data.federatedLearning.securityProtocol}</span>
                                </div>
                                <div className="fl-security-checks">
                                    {Object.entries(data.federatedLearning.dpdpCompliance).map(([key, val]) => (
                                        <div key={key} className="fl-security-check">
                                            <i className={`fas ${val ? 'fa-check-circle' : 'fa-times-circle'}`} style={{ color: val ? '#10B981' : '#e53935' }} />
                                            <span>{key.replace(/([A-Z])/g, ' $1').replace(/^./, s => s.toUpperCase())}</span>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Layer 4 */}
                    {activeLayer === 4 && (
                        <div className="layer-panel fade-in-panel">
                            <div className="layer-panel-header">
                                <div className="layer-number" style={{ background: "rgba(251,191,36,0.12)", color: "#f59e0b" }}>L4</div>
                                <div>
                                    <h3 style={{ margin: 0, fontSize: "1.15rem" }}>Friction-Aware Composite Scoring</h3>
                                    <p style={{ margin: 0, fontSize: "0.82rem", color: "var(--text-muted)" }}>IGM-penalized ranking with SHAP explainability</p>
                                </div>
                            </div>

                            {/* Formula */}
                            <div className="formula-box">
                                <div className="formula-title">Scoring Formula</div>
                                <div className="formula-text">
                                    Final = (<span className="fw-a">α</span> × Capability) + (<span className="fw-b">β</span> × FL_Success) − (<span className="fw-c">γ</span> × Friction)
                                </div>
                                <div className="formula-weights">
                                    <span className="fw-tag fw-a-bg">α = {data.frictionScoring.weights.alpha}</span>
                                    <span className="fw-tag fw-b-bg">β = {data.frictionScoring.weights.beta}</span>
                                    <span className="fw-tag fw-c-bg">γ = {data.frictionScoring.weights.gamma}</span>
                                </div>
                            </div>

                            {/* Per-SNP Breakdown */}
                            <h5 style={{ fontSize: "0.85rem", color: "var(--text-muted)", marginBottom: 12, textTransform: "uppercase", letterSpacing: 0.5 }}>
                                <i className="fas fa-calculator" style={{ marginRight: 6 }} /> Per-SNP Score Trace
                            </h5>
                            {data.frictionScoring.perSnpBreakdown.map((snp: any, i: number) => (
                                <div key={i} className="friction-snp-card">
                                    <div className="friction-snp-header">
                                        <span className="friction-snp-name">{snp.snpName}</span>
                                        <span className="friction-snp-score">
                                            <AnimCounter target={snp.compositeScore} duration={800 + i * 200} />
                                        </span>
                                    </div>
                                    <div className="friction-bars">
                                        <div className="friction-bar-row">
                                            <span className="friction-bar-label">Capability (α)</span>
                                            <ProgressBar value={snp.capabilityAligned} color="#38bdf8" delay={i * 100} />
                                            <span className="friction-bar-val">{snp.capabilityAligned.toFixed(2)}</span>
                                        </div>
                                        <div className="friction-bar-row">
                                            <span className="friction-bar-label">FL Success (β)</span>
                                            <ProgressBar value={snp.flSuccess} color="#a78bfa" delay={i * 100 + 100} />
                                            <span className="friction-bar-val">{snp.flSuccess.toFixed(2)}</span>
                                        </div>
                                        <div className="friction-bar-row">
                                            <span className="friction-bar-label">Friction (γ)</span>
                                            <ProgressBar value={snp.frictionRisk} max={0.3} color="#ef4444" delay={i * 100 + 200} />
                                            <span className="friction-bar-val" style={{ color: "#ef4444" }}>−{snp.frictionRisk.toFixed(2)}</span>
                                        </div>
                                    </div>
                                    <div className="friction-trace">
                                        <code>{snp.formulaTrace}</code>
                                    </div>
                                    <div className="friction-igm">
                                        <span><i className="fas fa-exclamation-triangle" style={{ color: "#f59e0b", marginRight: 4 }} /> IGM: {snp.igmDisputes.total} disputes</span>
                                        <span>{snp.igmDisputes.resolved} resolved</span>
                                        <span>Avg {snp.igmDisputes.avgDays} days</span>
                                    </div>
                                </div>
                            ))}

                            {/* Fairness Audit */}
                            <div className="fairness-audit-box">
                                <h5><i className="fas fa-gavel" style={{ marginRight: 6, color: "#10B981" }} /> Fairness Audit</h5>
                                <div className="fairness-checks">
                                    {Object.entries(data.frictionScoring.fairnessAudit)
                                        .filter(([k]) => k !== 'auditTimestamp')
                                        .map(([key, val]) => (
                                            <div key={key} className="fairness-check">
                                                <i className="fas fa-check-circle" style={{ color: "#10B981" }} />
                                                <span>{key.replace(/([A-Z])/g, ' $1').replace(/^./, s => s.toUpperCase())}: <strong>{val as string}</strong></span>
                                            </div>
                                        ))}
                                </div>
                            </div>
                        </div>
                    )}
                </div>

                {/* Right: SNP Recommendations */}
                <div className="snp-results-column">
                    <h3 style={{ fontSize: "1.1rem", marginBottom: 16 }}>
                        <i className="fas fa-trophy" style={{ color: "#F59E0B", marginRight: 8 }} /> Top Recommended SNPs
                    </h3>
                    {data.matches.map((snp: any, idx: number) => (
                        <div key={snp.id} className={`snp-card ${idx === 0 ? 'best-match' : ''}`}
                            style={{ animationDelay: `${idx * 0.15}s` }}>
                            {idx === 0 && <div className="snp-best-badge">BEST MATCH</div>}

                            <div className="snp-card-top">
                                <div>
                                    <h4 className="snp-name">{snp.name}</h4>
                                    <span className="snp-domain">{snp.domain}</span>
                                </div>
                                <div className="snp-composite">
                                    <div className="snp-composite-value">
                                        <AnimCounter target={parseFloat(snp.composite_score)} duration={1000 + idx * 200} />
                                    </div>
                                    <div className="snp-composite-label">Composite Score</div>
                                </div>
                            </div>

                            <div className="snp-scores-row">
                                <div className="snp-score-item">
                                    <div className="snp-score-label">Capability (HGT)</div>
                                    <div className="snp-score-value">{snp.capability_alignment}</div>
                                </div>
                                <div className="snp-score-item" style={{ borderLeft: "1px solid var(--border-color, #e2e8f0)", borderRight: "1px solid var(--border-color, #e2e8f0)" }}>
                                    <div className="snp-score-label">Success (FL)</div>
                                    <div className="snp-score-value">{snp.fl_success_prob}</div>
                                </div>
                                <div className="snp-score-item">
                                    <div className="snp-score-label">IGM Friction</div>
                                    <div className="snp-score-value" style={{ color: "#f59e0b" }}>{snp.friction_risk}</div>
                                </div>
                            </div>

                            {/* SHAP Expand */}
                            <button className="snp-shap-toggle" onClick={() => setExpandedSnp(expandedSnp === snp.id ? null : snp.id)}>
                                <i className="fas fa-info-circle" /> SHAP Explanations
                                <i className={`fas fa-chevron-${expandedSnp === snp.id ? 'up' : 'down'}`} style={{ marginLeft: "auto" }} />
                            </button>

                            {expandedSnp === snp.id && (
                                <div className="snp-shap-content">
                                    {snp.shap_explanations.map((exp: any, i: number) => (
                                        <div key={i} className="shap-row">
                                            <span className={`shap-contrib ${exp.contribution.startsWith("+") ? 'positive' : 'negative'}`}>
                                                {exp.contribution}
                                            </span>
                                            <div>
                                                <div className="shap-feature">{exp.feature}</div>
                                                <div className="shap-reason">{exp.reason}</div>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}

                            <button className="btn btn-primary snp-proceed-btn" onClick={() => {
                                setSelectedSnp(snp);
                                setProceedStep(0);
                            }}>
                                Proceed with {snp.name} <i className="fas fa-chevron-right" style={{ marginLeft: 8 }} />
                            </button>
                        </div>
                    ))}

                    {/* DPDP Compliance Footer */}
                    <div className="dpdp-footer-box">
                        <i className="fas fa-shield-alt" style={{ color: "#10B981", fontSize: "1.3rem" }} />
                        <div>
                            <strong style={{ color: "#065F46", display: "block", marginBottom: 4 }}>DPDP Act 2023 Compliant</strong>
                            <span style={{ color: "#047857", lineHeight: 1.4, display: "block", fontSize: "0.82rem" }}>
                                Federated model querying performed securely. Zero raw transaction data left SNP infrastructure.
                            </span>
                        </div>
                    </div>
                </div>
            </div>

            {/* Proceed Confirmation Modal */}
            {selectedSnp && <ProceedModal snp={selectedSnp} step={proceedStep} setStep={setProceedStep} onClose={() => setSelectedSnp(null)} />}

            {/* Graph animation keyframes (scoped) */}
            <style jsx>{`
                @keyframes gNodePop {
                    from { opacity: 0; transform: scale(0); }
                    to { opacity: 1; transform: scale(1); }
                }
                @keyframes gEdgeFadeIn {
                    from { opacity: 0; }
                    to { opacity: 1; }
                }
            `}</style>
        </div>
    );
}
