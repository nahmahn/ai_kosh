"use client";

import Link from "next/link";

export default function CTABanner() {
    return (
        <section
            style={{
                background: "var(--gradient-hero)",
                padding: "80px 0",
                position: "relative",
                overflow: "hidden",
            }}
        >
            <div
                className="container"
                style={{
                    textAlign: "center",
                    position: "relative",
                    zIndex: 2,
                }}
            >
                <h2
                    style={{
                        color: "white",
                        fontSize: "clamp(1.8rem, 4vw, 2.8rem)",
                        fontWeight: 800,
                        marginBottom: 16,
                        lineHeight: 1.2,
                    }}
                >
                    Ready to Join India&apos;s Largest
                    <br />
                    Digital Commerce Network?
                </h2>
                <p
                    style={{
                        color: "rgba(255,255,255,0.8)",
                        fontSize: "1.1rem",
                        maxWidth: 560,
                        margin: "0 auto 36px",
                        lineHeight: 1.7,
                    }}
                >
                    Start selling to millions of buyers across India. Our AI
                    handles the paperwork — you focus on your business.
                </p>
                <div style={{ display: "flex", gap: 16, justifyContent: "center", flexWrap: "wrap" }}>
                    <Link
                        href="/onboarding"
                        className="btn btn-white btn-lg"
                        style={{
                            padding: "16px 40px",
                            fontSize: "1.1rem",
                            borderRadius: 14,
                            fontWeight: 700,
                        }}
                    >
                        <i className="fas fa-rocket" style={{ marginRight: 8 }} />
                        Get Started Free
                    </Link>
                </div>
            </div>

            {/* Subtle background shapes */}
            <div
                style={{
                    position: "absolute",
                    top: "-30%",
                    right: "-10%",
                    width: 400,
                    height: 400,
                    borderRadius: "50%",
                    background: "rgba(255,255,255,0.03)",
                }}
            />
            <div
                style={{
                    position: "absolute",
                    bottom: "-20%",
                    left: "-5%",
                    width: 300,
                    height: 300,
                    borderRadius: "50%",
                    background: "rgba(255,255,255,0.03)",
                }}
            />
        </section>
    );
}
