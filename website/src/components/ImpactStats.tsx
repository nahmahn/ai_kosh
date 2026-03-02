"use client";

import { useEffect, useRef, useState } from "react";

const stats = [
    {
        target: 3,
        suffix: " min",
        label: "Average Onboarding Time",
        icon: "fas fa-clock",
        color: "#1C75BC",
        bg: "rgba(28, 117, 188, 0.08)",
    },
    {
        target: 11,
        suffix: "",
        label: "Indian Languages",
        icon: "fas fa-language",
        color: "#059669",
        bg: "rgba(5, 150, 105, 0.08)",
    },
    {
        target: 99,
        suffix: "%",
        label: "Accuracy Rate",
        icon: "fas fa-bullseye",
        color: "#EA580C",
        bg: "rgba(234, 88, 12, 0.08)",
    },
    {
        target: 0,
        suffix: "",
        prefix: "",
        label: "Manual Data Entry",
        icon: "fas fa-keyboard",
        color: "#7C3AED",
        bg: "rgba(124, 58, 237, 0.08)",
        displayText: "ZERO",
    },
];

function AnimatedCounter({
    target,
    prefix = "",
    suffix = "",
    displayText,
}: {
    target: number;
    prefix?: string;
    suffix?: string;
    displayText?: string;
}) {
    const [count, setCount] = useState(0);
    const ref = useRef<HTMLDivElement>(null);
    const animated = useRef(false);

    useEffect(() => {
        if (displayText) return; // static text, no animation
        const observer = new IntersectionObserver(
            ([entry]) => {
                if (entry.isIntersecting && !animated.current) {
                    animated.current = true;
                    const duration = 2000;
                    const steps = 60;
                    const increment = target / steps;
                    let current = 0;
                    const timer = setInterval(() => {
                        current += increment;
                        if (current >= target) {
                            setCount(target);
                            clearInterval(timer);
                        } else {
                            setCount(Math.floor(current));
                        }
                    }, duration / steps);
                }
            },
            { threshold: 0.3 }
        );
        if (ref.current) observer.observe(ref.current);
        return () => observer.disconnect();
    }, [target, displayText]);

    return (
        <div ref={ref} style={{ fontFamily: "var(--font-heading)", fontSize: "clamp(2rem, 4vw, 2.8rem)", fontWeight: 800, lineHeight: 1, marginBottom: 8 }}>
            {displayText ? displayText : `${prefix}${count.toLocaleString()}${suffix}`}
        </div>
    );
}

export default function ImpactStats() {
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
            id="impact"
            ref={ref}
            style={{
                background: "var(--bg-section-alt)",
                position: "relative",
            }}
        >
            <div className="container" style={{ position: "relative", zIndex: 2 }}>
                <span className="section-badge animate-in" style={{ animationDelay: "0.05s" }}>
                    By the Numbers
                </span>
                <h2 className="section-title animate-in" style={{ animationDelay: "0.1s" }}>
                    Why Sellers would Love ONDC?
                </h2>
                <p
                    className="section-subtitle animate-in"
                    style={{ animationDelay: "0.15s", maxWidth: 580 }}
                >
                    AI-powered onboarding that eliminates friction and gets you
                    selling faster.
                </p>

                <div className="grid-4" style={{ marginTop: 40 }}>
                    {stats.map((s, i) => (
                        <div
                            key={i}
                            className="animate-in"
                            style={{
                                animationDelay: `${0.2 + i * 0.1}s`,
                                textAlign: "center",
                                padding: "36px 24px",
                                borderRadius: 20,
                                background: "rgba(255, 255, 255, 0.7)",
                                backdropFilter: "blur(12px)",
                                border: "1px solid rgba(255, 255, 255, 0.8)",
                                transition: "all 0.3s ease",
                            }}
                        >
                            <div
                                style={{
                                    width: 56,
                                    height: 56,
                                    borderRadius: "50%",
                                    background: s.bg,
                                    color: s.color,
                                    display: "flex",
                                    alignItems: "center",
                                    justifyContent: "center",
                                    fontSize: "1.3rem",
                                    margin: "0 auto 20px",
                                }}
                            >
                                <i className={s.icon} />
                            </div>
                            <div style={{ color: s.color }}>
                                <AnimatedCounter
                                    target={s.target}
                                    prefix={s.prefix}
                                    suffix={s.suffix}
                                    displayText={s.displayText}
                                />
                            </div>
                            <p
                                style={{
                                    fontSize: "0.9rem",
                                    color: "var(--text-secondary)",
                                    fontWeight: 500,
                                    margin: 0,
                                }}
                            >
                                {s.label}
                            </p>
                        </div>
                    ))}
                </div>
            </div>
        </section>
    );
}
