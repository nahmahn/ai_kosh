"use client";

import Link from "next/link";
import Image from "next/image";

/* Inline SVG gear for decorative background elements */
function GearSVG({ size, className, style }: { size: number; className?: string; style?: React.CSSProperties }) {
    return (
        <svg
            width={size}
            height={size}
            viewBox="0 0 100 100"
            fill="none"
            className={className}
            style={style}
        >
            <path
                d="M50 18a3 3 0 0 1 3-3h4a3 3 0 0 1 3 3v5.2a22 22 0 0 1 7.8 4.5l4.5-2.6a3 3 0 0 1 4.1 1.1l2 3.5a3 3 0 0 1-1.1 4.1l-4.5 2.6a22 22 0 0 1 2.2 8.6h5.2a3 3 0 0 1 3 3v4a3 3 0 0 1-3 3H74.9a22 22 0 0 1-4.5 7.8l2.6 4.5a3 3 0 0 1-1.1 4.1l-3.5 2a3 3 0 0 1-4.1-1.1l-2.6-4.5a22 22 0 0 1-8.6 2.2V80a3 3 0 0 1-3 3h-4a3 3 0 0 1-3-3v-5.2a22 22 0 0 1-7.8-4.5l-4.5 2.6a3 3 0 0 1-4.1-1.1l-2-3.5a3 3 0 0 1 1.1-4.1l4.5-2.6A22 22 0 0 1 24.1 53H18a3 3 0 0 1-3-3v-4a3 3 0 0 1 3-3h5.2a22 22 0 0 1 4.5-7.8l-2.6-4.5a3 3 0 0 1 1.1-4.1l3.5-2a3 3 0 0 1 4.1 1.1l2.6 4.5a22 22 0 0 1 8.6-2.2V18z"
                stroke="rgba(28, 117, 188, 0.08)"
                strokeWidth="1.5"
                fill="none"
            />
            <circle cx="50" cy="49" r="12" stroke="rgba(28, 117, 188, 0.06)" strokeWidth="1.5" fill="none" />
        </svg>
    );
}

export default function Hero() {
    return (
        <section className="hero" id="hero">
            <div className="container">
                <div className="hero-grid">
                    {/* Left Column — Text */}
                    <div className="hero-content" style={{ display: "flex", flexDirection: "column", justifyContent: "center" }}>
                        <div
                            className="hero-badge hero-badge-ondc"
                            style={{ animation: "slideUpModal 0.6s ease-out forwards", opacity: 0, animationDelay: "0.1s" }}
                        >
                            Open Network for Digital Commerce
                        </div>

                        <h1
                            style={{
                                fontSize: "clamp(2.6rem, 5.5vw, 4.2rem)",
                                letterSpacing: "-0.5px",
                                lineHeight: 1.08,
                                marginBottom: 24,
                                animation: "slideUpModal 0.7s ease-out forwards",
                                opacity: 0,
                                animationDelay: "0.15s",
                            }}
                        >
                            Everyone&apos;s Commerce,
                            <br />
                            <span className="text-gradient-primary">Powered by AI</span>
                        </h1>

                        <p
                            style={{
                                fontSize: "1.15rem",
                                color: "var(--text-secondary)",
                                maxWidth: 520,
                                lineHeight: 1.75,
                                marginBottom: 40,
                                animation: "slideUpModal 0.8s ease-out forwards",
                                opacity: 0,
                                animationDelay: "0.25s",
                            }}
                        >
                            Join the backed by the Govt. of India, empowers you{" "}
                            <strong>to sell to buyers across India</strong> and grow your
                            business multifold.
                        </p>

                        <div
                            className="hero-buttons"
                            style={{
                                display: "flex",
                                gap: 16,
                                animation: "slideUpModal 0.8s ease-out forwards",
                                opacity: 0,
                                animationDelay: "0.35s",
                                flexWrap: "wrap",
                            }}
                        >
                            <Link
                                href="/onboarding"
                                className="btn btn-primary btn-lg"
                                style={{ padding: "16px 36px", fontSize: "1.05rem", borderRadius: 14 }}
                            >
                                <i className="fas fa-microphone-alt" /> Fill with Voice
                            </Link>
                            <Link
                                href="/onboarding"
                                className="btn btn-white btn-lg"
                                style={{ padding: "16px 36px", fontSize: "1.05rem", borderRadius: 14, border: "1.5px solid rgba(28, 117, 188, 0.2)" }}
                            >
                                <i className="fas fa-file-upload" style={{ color: "var(--primary-blue)" }} />{" "}
                                Upload Document
                            </Link>
                        </div>

                        {/* Trust badges */}
                        <div
                            style={{
                                marginTop: 48,
                                display: "flex",
                                alignItems: "center",
                                gap: 28,
                                opacity: 0,
                                animation: "fadeInOverlay 1s ease-out forwards",
                                animationDelay: "0.8s",
                                flexWrap: "wrap",
                            }}
                        >
                            {[
                                { icon: "fas fa-clock", label: "3-Minute Onboarding" },
                                { icon: "fas fa-magic", label: "Zero Manual Entry" },
                                { icon: "fas fa-language", label: "11 Indian Languages" },
                            ].map((b) => (
                                <div
                                    key={b.label}
                                    style={{
                                        display: "flex",
                                        alignItems: "center",
                                        gap: 8,
                                        fontSize: "0.85rem",
                                        fontWeight: 600,
                                        color: "var(--text-secondary)",
                                    }}
                                >
                                    <i className={b.icon} style={{ color: "#28a745" }} /> {b.label}
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* Right Column — Illustration (larger, blended) */}
                    <div
                        className="hero-illustration"
                        style={{
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                            position: "relative",
                            opacity: 0,
                            animation: "slideUpModal 0.9s ease-out forwards",
                            animationDelay: "0.3s",
                        }}
                    >
                        <Image
                            src="/hero_illustration.png"
                            alt="ONDC — Online Business Made Easy and Transparent"
                            width={720}
                            height={640}
                            style={{
                                objectFit: "contain",
                                maxWidth: "110%",
                                height: "auto",
                                mixBlendMode: "multiply",
                            }}
                            priority
                        />
                    </div>
                </div>
            </div>

            {/* Decorative background gears */}
            <GearSVG
                size={320}
                className="hero-deco hero-deco-1"
                style={{ position: "absolute", top: "3%", right: "-2%", opacity: 0.7 }}
            />
            <GearSVG
                size={220}
                className="hero-deco hero-deco-2"
                style={{ position: "absolute", bottom: "5%", right: "5%", opacity: 0.5 }}
            />
            <GearSVG
                size={160}
                className="hero-deco hero-deco-3"
                style={{ position: "absolute", top: "25%", left: "40%", opacity: 0.4 }}
            />
            <GearSVG
                size={100}
                className="hero-deco hero-deco-2"
                style={{ position: "absolute", bottom: "20%", left: "3%", opacity: 0.3 }}
            />
        </section>
    );
}
