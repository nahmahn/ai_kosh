import Image from "next/image";

export default function Footer() {
    return (
        <footer className="footer">
            <div className="container">
                <div className="footer-grid">
                    <div className="footer-brand">
                        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 12 }}>
                            <Image
                                src="/ondc_logo.svg"
                                alt="ONDC"
                                width={100}
                                height={36}
                                style={{ height: "auto", filter: "brightness(0) invert(1) opacity(0.8)" }}
                            />
                            <span style={{ color: "rgba(255,255,255,0.3)", fontSize: "1.2rem" }}>×</span>
                            <span style={{ color: "white", fontWeight: 700, fontSize: "1.1rem", fontFamily: "var(--font-heading)" }}>
                                AIKOSH
                            </span>
                        </div>
                        <p>
                            AI-powered onboarding platform for the ONDC Network.
                            Developed for the IndiaAI Innovation Challenge 2026
                            under the Ministry of MSME&apos;s TEAM Initiative.
                        </p>
                        <div className="footer-social" style={{ marginTop: 20 }}>
                            <a href="https://github.com" target="_blank" rel="noopener noreferrer">
                                <i className="fab fa-github" />
                            </a>
                            <a href="https://linkedin.com" target="_blank" rel="noopener noreferrer">
                                <i className="fab fa-linkedin-in" />
                            </a>
                        </div>
                    </div>

                    <div className="footer-col">
                        <h4>Platform</h4>
                        <ul>
                            <li><a href="#how-it-works">How It Works</a></li>
                            <li><a href="#impact">Impact</a></li>
                            <li><a href="/onboarding">Get Started</a></li>
                        </ul>
                    </div>

                    <div className="footer-col">
                        <h4>Resources</h4>
                        <ul>
                            <li><a href="https://ondc.org" target="_blank" rel="noopener noreferrer">ONDC Official</a></li>
                            <li><a href="https://indiaai.gov.in" target="_blank" rel="noopener noreferrer">IndiaAI Portal</a></li>
                            <li><a href="https://msme.gov.in" target="_blank" rel="noopener noreferrer">Ministry of MSME</a></li>
                        </ul>
                    </div>

                    <div className="footer-col">
                        <h4>Legal</h4>
                        <ul>
                            <li><a href="#">Privacy Policy</a></li>
                            <li><a href="#">Terms of Service</a></li>
                            <li><a href="#">DPDP Compliance</a></li>
                        </ul>
                    </div>
                </div>

                <div className="footer-bottom">
                    <p>© 2026 AIKOSH · IndiaAI Innovation Challenge</p>
                    <p>
                        Built with{" "}
                        <span style={{ color: "var(--primary-blue-light)" }}>♥</span>{" "}
                        for India&apos;s 63 Million MSMEs
                    </p>
                </div>
            </div>
        </footer>
    );
}
