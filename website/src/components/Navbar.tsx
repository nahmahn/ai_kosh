"use client";

import { useState, useEffect } from "react";
import Image from "next/image";

export default function Navbar() {
    const [scrolled, setScrolled] = useState(false);
    const [mobileOpen, setMobileOpen] = useState(false);

    useEffect(() => {
        const handle = () => setScrolled(window.scrollY > 50);
        window.addEventListener("scroll", handle);
        return () => window.removeEventListener("scroll", handle);
    }, []);

    const links = [
        { href: "#how-it-works", label: "How It Works" },
        { href: "#impact", label: "Impact" },
        { href: "#tech-stack", label: "Technology" },
    ];

    return (
        <nav className={`navbar ${scrolled ? "scrolled" : ""}`}>
            <div className="container">
                <a href="/" className="navbar-brand">
                    <Image
                        src="/ondc_logo.svg"
                        alt="ONDC — Open Network for Digital Commerce"
                        width={130}
                        height={48}
                        priority
                        style={{ height: "auto" }}
                    />
                </a>

                <ul className={`navbar-nav ${mobileOpen ? "active" : ""}`}>
                    {links.map((l) => (
                        <li key={l.href}>
                            <a href={l.href} onClick={() => setMobileOpen(false)}>
                                {l.label}
                            </a>
                        </li>
                    ))}
                    <li>
                        <a href="/onboarding" className="btn btn-primary btn-sm" onClick={() => setMobileOpen(false)}>
                            <i className="fas fa-sign-in-alt" style={{ marginRight: 6 }} />
                            Get Started
                        </a>
                    </li>
                </ul>

                <button
                    className="navbar-toggle"
                    onClick={() => setMobileOpen(!mobileOpen)}
                    aria-label="Toggle navigation"
                >
                    <span />
                    <span />
                    <span />
                </button>
            </div>
        </nav>
    );
}
