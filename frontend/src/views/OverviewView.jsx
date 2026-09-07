import { memo } from "react";
import {
  Activity,
  ShieldCheck,
  ShieldAlert,
  Radio,
  Zap,
  Layers,
  ArrowRight,
  AlertTriangle,
} from "lucide-react";
import AlarmBanner from "../components/AlarmBanner";

function OverviewView({
  nodes = {},
  events = [],
  alarm = {},
  claims = {},
  onNavigate,
  onSelectNode,
}) {
  const nodeArray = Object.values(nodes);
  const trustedCount = nodeArray.filter((n) => n.state === "TRUSTED").length;
  const suspiciousCount = nodeArray.filter((n) => n.state === "SUSPICIOUS").length;
  const shadowCount = nodeArray.filter((n) => n.state === "SHADOW").length;
  const recoveringCount = nodeArray.filter((n) => n.state === "RECOVERING").length;

  const incidents = events.filter(
    (e) => e.type === "INCIDENT" || e.raw?.e === "incident"
  );

  return (
    <div className="view-container overview-view">
      {/* Alarm Alert */}
      <AlarmBanner alarm={alarm} activeClaim={claims.motion || claims.water} />

      {/* Header */}
      <div className="view-header">
        <div>
          <p className="eyebrow">EXECUTIVE SYSTEM STATUS</p>
          <h2>Cyber-Physical Mesh Control Overview</h2>
          <p className="subtitle">
            Autonomous zero-trust evidence validation. Device keys authenticate hardware identity; multi-witness physics corroborates readings.
          </p>
        </div>

        <div className="monitor-status">
          <Activity size={18} />
          <span>REAL-TIME MESH ACTIVE</span>
        </div>
      </div>

      {/* 4-Stat Metric Row */}
      <div className="overview-bar">
        <div>
          <span className="overview-label">TOTAL MESH UNITS</span>
          <strong>{nodeArray.length} NODES</strong>
        </div>

        <div>
          <span className="overview-label">TRUSTED QUORUM</span>
          <strong className={trustedCount === nodeArray.length ? "text-green" : "text-amber"}>
            {trustedCount} / {nodeArray.length} HEALTHY
          </strong>
        </div>

        <div>
          <span className="overview-label">SECURITY INCIDENTS</span>
          <strong className={incidents.length > 0 ? "text-amber" : "text-green"}>
            {incidents.length} LOGGED
          </strong>
        </div>

        <div>
          <span className="overview-label">PHYSICAL ALARM STATE</span>
          <strong className={alarm?.on ? "text-red" : "text-green"}>
            {alarm?.on ? "ALERT ACTIVE" : "NOMINAL"}
          </strong>
        </div>
      </div>

      {/* Health Breakdown Cards Grid */}
      <div className="overview-nodes-summary-grid">
        {nodeArray.map((node) => {
          const isShadow = node.state === "SHADOW";
          const isTrusted = node.state === "TRUSTED";
          return (
            <div
              key={node.node_id}
              className={`node-summary-card ${isShadow ? "card-shadowed" : ""}`}
              onClick={() => {
                onSelectNode(node.node_id);
                onNavigate("inspector");
              }}
            >
              <div className="summary-card-header">
                <div className="summary-node-title">
                  <span className="node-id-tag">NODE {node.node_id}</span>
                  <h4>{node.sensorLabel || node.name}</h4>
                </div>
                <span className={`state-badge ${node.state?.toLowerCase()}`}>
                  {node.state || "TRUSTED"}
                </span>
              </div>

              <div className="summary-card-body">
                <div className="summary-reading-row">
                  <span>MEASUREMENT:</span>
                  <strong>
                    {node.last?.motion !== undefined && node.last?.water !== undefined
                      ? `${node.last.motion ? "MOTION" : "CLEAR"} · ${node.last.water ? "WET" : "DRY"}`
                      : node.last?.motion !== undefined
                      ? node.last.motion ? "MOTION (1)" : "CLEAR (0)"
                      : node.last?.water !== undefined
                      ? node.last.water ? "WET (1)" : "DRY (0)"
                      : node.last?.temp !== undefined
                      ? `${node.last.temp.toFixed(1)}°C`
                      : "NOMINAL"}
                  </strong>
                </div>

                <div className="summary-trust-row">
                  <span>OVERALL TRUST:</span>
                  <strong
                    className={
                      (node.overall ?? 100) >= 70
                        ? "text-green"
                        : (node.overall ?? 100) >= 40
                        ? "text-amber"
                        : "text-red"
                    }
                  >
                    {node.overall ?? 100}%
                  </strong>
                </div>
              </div>

              <div className="summary-card-footer">
                <span>{node.hardware}</span>
                <span className="inspect-link">
                  Inspect <ArrowRight size={12} />
                </span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Quick Access & Critical Incidents */}
      <div className="overview-bottom-split">
        {/* Quick View Jumps */}
        <div className="overview-actions-card">
          <div className="card-heading-row">
            <Zap size={18} className="text-amber" />
            <h3>Quick Control Actions</h3>
          </div>
          <p className="card-desc">
            Directly manipulate or investigate cyber-physical security layers:
          </p>
          <div className="action-button-list">
            <button className="overview-btn" onClick={() => onNavigate("mesh")}>
              <Radio size={16} />
              <span>Inspect Full-Stage Mesh Topology</span>
            </button>
            <button className="overview-btn" onClick={() => onNavigate("attacks")}>
              <Zap size={16} className="text-amber" />
              <span>Launch Judge Adversarial Attack Panel</span>
            </button>
            <button className="overview-btn" onClick={() => onNavigate("challenges")}>
              <ShieldAlert size={16} />
              <span>Audit Live Adaptive Challenge Engine</span>
            </button>
          </div>
        </div>

        {/* Recent Incidents Feed */}
        <div className="overview-incidents-card">
          <div className="card-heading-row">
            <AlertTriangle size={18} className="text-amber" />
            <h3>Recent Critical Incidents</h3>
          </div>
          <div className="incidents-preview-list">
            {incidents.slice(0, 4).map((inc, i) => (
              <div className="incident-preview-item" key={inc.id || i}>
                <span className="incident-time">{inc.timestamp}</span>
                <p className="incident-text">{inc.summary || inc.message}</p>
              </div>
            ))}
            {incidents.length === 0 && (
              <div className="empty-incidents-note">
                <ShieldCheck size={16} className="text-green" />
                <span>Zero security violations detected. Baseline nominal.</span>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default memo(OverviewView);
