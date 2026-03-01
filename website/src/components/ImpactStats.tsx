"use client";

import { useEffect, useRef, useState } from "react";

const stats = [
    { target: 3, suffix: " Days", label: "Onboarding Time (vs 14 days)", icon: "fas fa-clock" },
    { target: 10, prefix: "<", suffix: "%", label: "NSIC Claim Rejection Rate", icon: "fas fa-check-circle" },
    { target: 12000, suffix: "+", label: "MSEs Targeted in Production", icon: "fas fa-industry" },
    { target: 11, suffix: "", label: "Indian Languages Supported", icon: "fas fa-language" },
];

function AnimatedCounter({ target, prefix = "", suffix = "" }: { target: number; prefix?: string; suffix?: string }) {
    const [count, setCount] = useState(0);
    const ref = useRef<HTMLDivElement>(null);
    const animated = useRef(false);

    useEffect(() => {
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
    }, [target]);

    return (
        <div ref={ref} className="stat-number">
            {prefix}{count.toLocaleString()}{suffix}
        </div>
    );
}

export default function ImpactStats() {
    return (
        <section className="section section-dark" id="impact">
            <div className="container">
                <span className="section-badge">Performance</span>
                <h2 className="section-title">Our Network&apos;s Impact</h2>
                <p className="section-subtitle">
                    Measurable improvements over the current MSME TEAM portal — faster
                    onboarding, lower rejections, broader reach.
                </p>

                <div className="grid-4">
                    {stats.map((s, i) => (
                        <div key={i} className="stat-card">
                            <div
                                style={{
                                    width: 48,
                                    height: 48,
                                    borderRadius: 14,
                                    background: "rgba(74, 161, 224, 0.12)",
                                    display: "flex",
                                    alignItems: "center",
                                    justifyContent: "center",
                                    margin: "0 auto 16px",
                                    fontSize: "1.1rem",
                                    color: "var(--primary-blue-light)",
                                }}
                            >
                                <i className={s.icon} />
                            </div>
                            <AnimatedCounter target={s.target} prefix={s.prefix} suffix={s.suffix} />
                            <p className="stat-label">{s.label}</p>
                        </div>
                    ))}
                </div>
            </div>
        </section>
    );
}
