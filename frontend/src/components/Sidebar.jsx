import { useState, memo } from "react";
import {
  ShieldCheck,
  Layers,
  Radio,
  Cpu,
  Users,
  ShieldAlert,
  Zap,
  FastForward,
  BarChart3,
  History,
  Menu,
  X,
} from "lucide-react";

const NAV_ITEMS = [
  { id: "overview", label: "Overview", icon: <Layers size={18} /> },
  { id: "mesh", label: "Mesh Topology", icon: <Radio size={18} /> },
  { id: "inspector", label: "Node Inspector", icon: <Cpu size={18} /> },
  { id: "consensus", label: "Consensus Quorum", icon: <Users size={18} /> },
  { id: "challenges", label: "Adaptive Challenges", icon: <ShieldAlert size={18} /> },
  { id: "attacks", label: "Judge Attack Panel", icon: <Zap size={18} /> },
  { id: "drift", label: "Drift Simulator", icon: <FastForward size={18} /> },
  { id: "metrics", label: "Verification Metrics", icon: <BarChart3 size={18} /> },
  { id: "incidents", label: "Forensic Audit Log", icon: <History size={18} /> },
];

/**
 * Sidebar for Multi-View Navigation
 */
function Sidebar({
  activeView = "overview",
  onSelectView,
  isConnected,
  isReplaying,
}) {
  const [isMobileOpen, setIsMobileOpen] = useState(false);

  const handleNavClick = (viewId) => {
    onSelectView(viewId);
    setIsMobileOpen(false);
  };

  return (
    <>
      {/* Mobile Header Bar */}
      <div className="mobile-header-bar">
        <button
          className="mobile-menu-btn"
          onClick={() => setIsMobileOpen((prev) => !prev)}
          aria-label="Toggle Navigation Menu"
        >
          {isMobileOpen ? <X size={22} /> : <Menu size={22} />}
        </button>

        <div className="mobile-brand-title">
          <ShieldCheck size={20} className="text-blue" />
          <span>ARES CONTROL ROOM</span>
        </div>

        <div className="rec-live-badge-sm">
          <span className="rec-dot" />
          <span>{isConnected ? "LIVE" : "REEL"}</span>
        </div>
      </div>

      {/* Backdrop for Mobile */}
      {isMobileOpen && (
        <div
          className="sidebar-backdrop"
          onClick={() => setIsMobileOpen(false)}
        />
      )}

      {/* Fixed Vertical Left Sidebar */}
      <aside className={`fixed-sidebar ${isMobileOpen ? "mobile-open" : ""}`}>
        {/* Top Brand Block */}
        <div className="sidebar-brand">
          <div className="sidebar-brand-icon">
            <ShieldCheck size={26} />
          </div>
          <div className="sidebar-brand-text">
            <div className="sidebar-title-row">
              <h2>ARES</h2>
              <span className="sidebar-version-tag">v1.4</span>
            </div>
            <span className="sidebar-subtitle">
              Adaptive Trust & Deception-Resistant Mesh
            </span>
          </div>
        </div>

        <div className="sidebar-divider" />

        {/* View Navigation Menu */}
        <nav className="sidebar-nav">
          <div className="nav-group-label">CONTROL ROOM VIEWS</div>
          {NAV_ITEMS.map((item) => {
            const isActive = activeView === item.id;
            return (
              <button
                key={item.id}
                className={`sidebar-nav-item ${isActive ? "active" : ""}`}
                onClick={() => handleNavClick(item.id)}
              >
                <div className="nav-item-icon">{item.icon}</div>
                <span className="nav-item-label">{item.label}</span>
                {isActive && <div className="active-indicator-bar" />}
              </button>
            );
          })}
        </nav>

        {/* Bottom Status Box */}
        <div className="sidebar-footer">
          <div className="sidebar-status-box">
            <div className="status-box-header">
              <span className="status-box-title">GATEWAY LINK</span>
              <div className="rec-live-badge-sm">
                <span className="rec-dot" />
                <span>{isConnected ? "LIVE" : "REEL"}</span>
              </div>
            </div>

            <div className="status-box-body">
              <span className={`status-dot ${isConnected ? "online" : "replay"}`} />
              <span className="status-box-label">
                {isConnected ? "WS LIVE (PORT 8000)" : "SAMPLE REPLAY ACTIVE"}
              </span>
            </div>
          </div>
        </div>
      </aside>
    </>
  );
}

export default memo(Sidebar);
