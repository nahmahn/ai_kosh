"use client";

import { useEffect, useRef } from "react";

const steps = [
    {
        icon: "fas fa-microphone-alt",
        title: "Speak Your Details",
        desc: "Use our voice assistant in your preferred language to narrate your business information naturally.",
        color: "#1C75BC",
    },
    {
        icon: "fas fa-file-upload",
        title: "Upload Documents",
        desc: "Simply upload your Udyam or GST certificate. Our AI extracts and verifies all relevant data instantly.",
        color: "#059669",
    },
    {
        icon: "fas fa-magic",
        title: "Auto-Filled Form",
        desc: "Watch as your onboarding form populates automatically in real-time — zero manual typing required.",
        color: "#EA580C",
    },
    {
        icon: "fas fa-rocket",
        title: "Start Selling",
        desc: "Review your details and submit. You're now part of the ONDC network, ready to reach millions of buyers.",
        color: "#7C3AED",
    },
];

export default function HowItWorks() {
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
            className="section"
            id="how-it-works"
            ref={ref}
            style={{ background: "var(--bg-white)", position: "relative" }}
        >
            <div className="container" style={{ position: "relative", zIndex: 2 }}>
                <span
                    className="section-badge animate-in"
                    style={{ animationDelay: "0.1s" }}
                >
                    Simple &amp; Fast
                </span>
                <h2
                    className="section-title animate-in"
                    style={{ animationDelay: "0.2s" }}
                >
                    How It Works
                </h2>
                <p
                    className="section-subtitle animate-in"
                    style={{ animationDelay: "0.3s", maxWidth: 600 }}
                >
                    Join the ONDC network in four simple steps — no technical
                    knowledge needed.
                </p>

                <div className="grid-4" style={{ marginTop: 48 }}>
                    {steps.map((step, i) => (
                        <div
                            key={i}
                            className="animate-in"
                            style={{
                                animationDelay: `${0.4 + i * 0.1}s`,
                                padding: "36px 24px 32px",
                                background: "var(--bg-white)",
                                border: "1px solid rgba(25, 72, 109, 0.08)",
                                textAlign: "center",
                                borderRadius: 20,
                                position: "relative",
                                boxShadow: "0 4px 20px rgba(25, 72, 109, 0.06)",
                                transition: "all 0.3s ease",
                            }}
                        >
                            {/* Step number */}
                            <div
                                style={{
                                    position: "absolute",
                                    top: 16,
                                    right: 18,
                                    fontFamily: "var(--font-heading)",
                                    fontSize: "2.5rem",
                                    fontWeight: 800,
                                    color: "rgba(28, 117, 188, 0.06)",
                                    lineHeight: 1,
                                }}
                            >
                                {i + 1}
                            </div>

                            {/* Icon circle */}
                            <div
                                style={{
                                    width: 64,
                                    height: 64,
                                    borderRadius: "50%",
                                    background: step.color,
                                    color: "white",
                                    display: "flex",
                                    alignItems: "center",
                                    justifyContent: "center",
                                    fontSize: "1.4rem",
                                    margin: "0 auto 20px",
                                    boxShadow: `0 8px 20px ${step.color}33`,
                                }}
                            >
                                <i className={step.icon} />
                            </div>

                            <h3 style={{ fontSize: "1.05rem", marginBottom: 10, color: "var(--dark-blue)" }}>
                                {step.title}
                            </h3>
                            <p
                                style={{
                                    fontSize: "0.88rem",
                                    color: "var(--text-muted)",
                                    lineHeight: 1.65,
                                    margin: 0,
                                }}
                            >
                                {step.desc}
                            </p>
                        </div>
                    ))}
                </div>
            </div>

            {/* Subtle diagonal decoration */}
            <div
                style={{
                    position: "absolute",
                    top: "40%",
                    left: 0,
                    width: "100%",
                    height: 200,
                    background:
                        "linear-gradient(90deg, rgba(74, 161, 224, 0.02), rgba(28, 117, 188, 0.04), rgba(74, 161, 224, 0.02))",
                    transform: "skewY(-2deg)",
                    zIndex: 1,
                }}
            />
        </section>
    );
}
