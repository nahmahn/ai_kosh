"use client";

export default function Hero() {
    return (
        <section className="hero" id="hero">
            <div className="container">
                <div className="hero-content" style={{ textAlign: "center", maxWidth: 800, margin: "0 auto" }}>
                    <div className="hero-badge hero-badge-ondc">
                        Open Network for Digital Commerce
                    </div>
                    <h1>
                        Everyone&apos;s Commerce,<br />
                        <span>Powered by AI</span>
                    </h1>
                    <p style={{ fontSize: "1.15rem", maxWidth: 620, margin: "0 auto 32px" }}>
                        Where any MSME can sell and everyone can buy — AI-powered document
                        intelligence and voice onboarding that cuts registration from 14 days
                        to under 3.
                    </p>
                    <div className="hero-buttons" style={{ justifyContent: "center" }}>
                        <a href="/onboarding" className="btn btn-primary btn-lg">
                            How To Join
                            <i className="fas fa-arrow-right" style={{ marginLeft: 8 }} />
                        </a>
                        <a href="#how-it-works" className="btn btn-outline btn-lg">
                            Learn About ONDC
                        </a>
                    </div>
                </div>

                {/* Network visualization — matching ONDC's connected nodes style */}
                <div className="hero-network" style={{ marginTop: 64 }}>
                    <div className="ondc-network-grid">
                        {/* Row 1 */}
                        <div className="network-card nc-buyer">
                            <div className="nc-icon nc-icon-green"><i className="fas fa-shopping-cart" /></div>
                            <span>Buyer App</span>
                        </div>
                        <div className="network-card nc-seller">
                            <div className="nc-icon nc-icon-coral"><i className="fas fa-store" /></div>
                            <span>Seller App</span>
                        </div>
                        <div className="network-card nc-gateway">
                            <div className="nc-icon nc-icon-blue"><i className="fas fa-project-diagram" /></div>
                            <span>ONDC Gateway</span>
                        </div>
                        <div className="network-card nc-seller">
                            <div className="nc-icon nc-icon-coral"><i className="fas fa-store" /></div>
                            <span>Seller App</span>
                        </div>
                        <div className="network-card nc-buyer">
                            <div className="nc-icon nc-icon-green"><i className="fas fa-shopping-cart" /></div>
                            <span>Buyer App</span>
                        </div>

                        {/* Example MSME nodes */}
                        <div className="network-msme">
                            <img src="https://ui-avatars.com/api/?name=Kiran+Bakery&background=FFECD2&color=D97706&bold=true&size=40" alt="Kiran Bakery" />
                            <span>Kiran Bakery</span>
                        </div>
                        <div className="network-msme">
                            <img src="https://ui-avatars.com/api/?name=Lakshmi+Pickles&background=DBEAFE&color=1D4ED8&bold=true&size=40" alt="Lakshmi Pickles" />
                            <span>Lakshmi Pickles</span>
                        </div>
                        <div className="network-msme">
                            <img src="https://ui-avatars.com/api/?name=Jyoti+Silks&background=FCE7F3&color=BE185D&bold=true&size=40" alt="Jyoti Silks" />
                            <span>Jyoti Silks</span>
                        </div>

                        {/* Connecting SVG lines */}
                        <svg className="network-lines" viewBox="0 0 800 200" preserveAspectRatio="none">
                            <line x1="80" y1="40" x2="240" y2="40" stroke="#D1D5DB" strokeWidth="1" strokeDasharray="6 4" />
                            <line x1="240" y1="40" x2="400" y2="40" stroke="#D1D5DB" strokeWidth="1" strokeDasharray="6 4" />
                            <line x1="400" y1="40" x2="560" y2="40" stroke="#D1D5DB" strokeWidth="1" strokeDasharray="6 4" />
                            <line x1="560" y1="40" x2="720" y2="40" stroke="#D1D5DB" strokeWidth="1" strokeDasharray="6 4" />
                            <line x1="240" y1="40" x2="160" y2="140" stroke="#D1D5DB" strokeWidth="1" strokeDasharray="6 4" />
                            <line x1="400" y1="40" x2="400" y2="140" stroke="#D1D5DB" strokeWidth="1" strokeDasharray="6 4" />
                            <line x1="560" y1="40" x2="640" y2="140" stroke="#D1D5DB" strokeWidth="1" strokeDasharray="6 4" />
                        </svg>
                    </div>
                </div>
            </div>
        </section>
    );
}
