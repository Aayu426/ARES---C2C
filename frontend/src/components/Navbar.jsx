import { useState, useEffect, memo } from "react";
import { ShieldCheck, Wifi, WifiOff, Zap, Radio, Activity } from "lucide-react";

const NAV_LINKS = [
  { id: "overview", label: "Overview" },
  { id: "mesh", label: "Mesh" },
  { id: "inspector", label: "Inspector" },
  { id: "consensus", label: "Consensus" },
  { id: "challenges", label: "Challenges" },
  { id: "attacks", label: "Attacks" },
  { id: "drift", label: "Drift" },
  { id: "metrics", label: "Metrics" },
  { id: "incidents", label: "Incidents" },
];

/**
 * Sticky Control-Room Top Navbar
 * Provides continuous brand identity, section scrolling with active highlights,
 * and live gateway connectivity status.
 */
function Navbar({ isConnected, isReplaying, onSwitchPhoneMode }) {
  const [activeSection, setActiveSection] = useState("overview");

  useEffect(() => {
    const handleScroll = () => {
      const scrollPosition = window.scrollY + 140;

      for (let i = NAV_LINKS.length - 1; i >= 0; i--) {
        const link = NAV_LINKS[i];
        const element = document.getElementById(link.id);
        if (element) {
          const top = element.offsetTop;
          if (scrollPosition >= top) {
            setActiveSection(link.id);
            break;
          }
        }
      }
    };

    window.addEventListener("scroll", handleScroll, { passive: true });
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  const scrollToSection = (e, id) => {
    e.preventDefault();
    const element = document.getElementById(id);
    if (element) {
      const offset = 80;
      const bodyRect = document.body.getBoundingClientRect().top;
      const elementRect = element.getBoundingClientRect().top;
      const elementPosition = elementRect - bodyRect;
      const offsetPosition = elementPosition - offset;

      window.scrollTo({
        top: offsetPosition,
        behavior: "smooth",
      });
      setActiveSection(id);
    }
  };

  return (
    <header className="control-navbar">
      {/* Left: Brand Identity */}
      <div className="navbar-brand-block">
        <div className="navbar-logo">
          <ShieldCheck size={24} />
        </div>
        <div className="navbar-title-text">
          <div className="brand-row">
            <h1>ARES</h1>
            <span className="version-pill">v1.4</span>
          </div>
          <span className="brand-tagline">
            Adaptive Trust & Deception-Resistant Mesh
          </span>
        </div>
      </div>

      {/* Center: Navigation Links */}
      <nav className="navbar-nav-links">
        {NAV_LINKS.map((link) => (
          <a
            key={link.id}
            href={`#${link.id}`}
            className={`nav-link ${activeSection === link.id ? "active" : ""}`}
            onClick={(e) => scrollToSection(e, link.id)}
          >
            {link.label}
          </a>
        ))}
      </nav>

      {/* Right: Status & Actions */}
      <div className="navbar-status-block">
        <button
          className="phone-mode-nav-btn"
          onClick={onSwitchPhoneMode}
          title="Open Judge Phone Mode (§9)"
        >
          <Zap size={14} className="text-amber" />
          <span>Judge Phone Mode</span>
        </button>

        <div className="navbar-live-status">
          {isConnected ? (
            <>
              <span className="status-dot online" />
              <span className="live-status-text text-green">GATEWAY WS LIVE</span>
            </>
          ) : (
            <>
              <span className="status-dot replay" />
              <span className="live-status-text text-amber">
                {isReplaying ? "SAMPLE REPLAY ACTIVE" : "DISCONNECTED"}
              </span>
            </>
          )}
        </div>

        <div className="rec-live-badge">
          <span className="rec-dot" />
          <span>LIVE</span>
        </div>
      </div>
    </header>
  );
}

export default memo(Navbar);
