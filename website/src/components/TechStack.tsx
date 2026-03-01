"use client";

const techStack = [
    { name: "LayoutLMv3", desc: "Document understanding", icon: "📄" },
    { name: "Gemini 2.5 Flash", desc: "Structured extraction", icon: "✨" },
    { name: "Indic Conformer 600M", desc: "Speech-to-text (11 langs)", icon: "🎙️" },
    { name: "Gemma 4B (Custom)", desc: "NER entity extraction", icon: "🧠" },
    { name: "Sarvam AI", desc: "TTS + Vision API", icon: "🗣️" },
    { name: "GraphSAGE / HGT", desc: "Knowledge graph learning", icon: "🔗" },
    { name: "Neo4j", desc: "Graph database", icon: "💠" },
    { name: "Flower (flwr.ai)", desc: "Federated learning", icon: "🌸" },
    { name: "FastAPI", desc: "Backend API server", icon: "⚡" },
    { name: "Next.js + React", desc: "Frontend framework", icon: "⚛️" },
    { name: "PyTorch Geometric", desc: "GNN operations", icon: "🔥" },
    { name: "DPDP Act 2023", desc: "Privacy compliance", icon: "🔒" },
];

export default function TechStack() {
    return (
        <section className="section section-dark" id="tech-stack">
            <div className="container">
                <span className="section-badge">Technology</span>
                <h2 className="section-title">Built With World-Class AI</h2>
                <p className="section-subtitle">
                    State-of-the-art models and frameworks, deployed on MeitY-empanelled
                    cloud infrastructure for government-grade reliability.
                </p>

                <div className="grid-4">
                    {techStack.map((tech, i) => (
                        <div key={i} className="tech-badge">
                            <div className="tech-badge-icon">{tech.icon}</div>
                            <div className="tech-badge-info">
                                <h4>{tech.name}</h4>
                                <p>{tech.desc}</p>
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        </section>
    );
}
