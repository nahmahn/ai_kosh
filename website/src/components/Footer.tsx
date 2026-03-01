export default function Footer() {
    return (
        <footer className="footer">
            <div className="container">
                <div className="footer-grid">
                    <div className="footer-brand">
                        <h3>
                            <i className="fas fa-project-diagram" style={{ marginRight: 8, color: "var(--primary-blue)" }} />
                            MSME-Graph
                        </h3>
                        <p>
                            An AI-powered federated intelligence system for automating MSME
                            onboarding to ONDC, developed for the IndiaAI Innovation
                            Challenge 2026 under the Ministry of MSME&apos;s TEAM Initiative.
                        </p>
                        <div className="footer-social" style={{ marginTop: 20 }}>
                            <a href="https://github.com" target="_blank" rel="noopener noreferrer">
                                <i className="fab fa-github" />
                            </a>
                            <a href="https://linkedin.com" target="_blank" rel="noopener noreferrer">
                                <i className="fab fa-linkedin-in" />
                            </a>
                            <a href="https://twitter.com" target="_blank" rel="noopener noreferrer">
                                <i className="fab fa-twitter" />
                            </a>
                        </div>
                    </div>

                    <div className="footer-col">
                        <h4>Platform</h4>
                        <ul>
                            <li><a href="#document-upload">Document AI</a></li>
                            <li><a href="#voice-onboarding">Voice Pipeline</a></li>
                            <li><a href="#how-it-works">Architecture</a></li>
                            <li><a href="#tech-stack">Technology</a></li>
                        </ul>
                    </div>

                    <div className="footer-col">
                        <h4>Resources</h4>
                        <ul>
                            <li><a href="https://resources.ondc.org/" target="_blank" rel="noopener noreferrer">ONDC Resources</a></li>
                            <li><a href="https://indiaai.gov.in/" target="_blank" rel="noopener noreferrer">IndiaAI Portal</a></li>
                            <li><a href="https://msme.gov.in/" target="_blank" rel="noopener noreferrer">Ministry of MSME</a></li>
                            <li><a href="https://beckn.org/" target="_blank" rel="noopener noreferrer">Beckn Protocol</a></li>
                        </ul>
                    </div>

                    <div className="footer-col">
                        <h4>Legal</h4>
                        <ul>
                            <li><a href="#">Privacy Policy</a></li>
                            <li><a href="#">Terms of Service</a></li>
                            <li><a href="#">DPDP Compliance</a></li>
                            <li><a href="#">Contact Us</a></li>
                        </ul>
                    </div>
                </div>

                <div className="footer-bottom">
                    <p>© 2026 MSME-Graph · IndiaAI Innovation Challenge</p>
                    <p>
                        Built with{" "}
                        <span style={{ color: "var(--primary-blue)" }}>♥</span> for
                        India&apos;s MSMEs
                    </p>
                </div>
            </div>
        </footer>
    );
}
