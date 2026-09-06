import { ShieldCheck, Activity, Wifi, Bell } from "lucide-react";
import NodeCard from "./components/NodeCard";
import EventTimeline from "./components/EventTimeline";
import sampleStream from "./data/sample_stream.json";
import "./App.css";

function App() {
  const nodes = sampleStream.nodes || [];

  return (
    <div className="app">
      {/* Top navigation */}
      <header className="topbar">
        <div className="brand">
          <div className="brand-icon">
            <ShieldCheck size={22} />
          </div>

          <div>
            <h1>ARES</h1>
            <span>Adaptive Resilience & Evidence System</span>
          </div>
        </div>

        <div className="system-status">
          <div className="status-item">
            <span className="status-dot online" />
            SYSTEM ONLINE
          </div>

          <div className="status-item">
            <Wifi size={15} />
            MESH CONNECTED
          </div>
        </div>
      </header>

      {/* Main dashboard */}
      <main className="dashboard">
        <section className="page-heading">
          <div>
            <p className="eyebrow">SECURITY CONTROL CENTER</p>
            <h2>Cyber-Physical Mesh</h2>
            <p className="subtitle">
              Continuous verification of device claims and physical evidence.
            </p>
          </div>

          <div className="monitor-status">
            <Activity size={17} />
            <span>MONITORING</span>
          </div>
        </section>

        {/* Incident banner */}
        <section className="overview-bar">
          <div>
            <span className="overview-label">ACTIVE NODES</span>
            <strong>{nodes.length}</strong>
          </div>

          <div>
            <span className="overview-label">TRUSTED</span>
            <strong className="text-green">
              {nodes.filter((node) => node.state === "TRUSTED").length}
            </strong>
          </div>

          <div>
            <span className="overview-label">INCIDENTS</span>
            <strong>0</strong>
          </div>

          <div>
            <span className="overview-label">ALERT LEVEL</span>
            <strong className="text-green">NORMAL</strong>
          </div>
        </section>

        {/* Nodes */}
        <section>
          <div className="section-header">
            <div>
              <p className="eyebrow">MESH OBSERVATION</p>
              <h3>Network Nodes</h3>
            </div>

            <span className="live-indicator">
              <span className="status-dot online" />
              LIVE
            </span>
          </div>

          <div className="nodes-grid">
            {nodes.map((node) => (
              <NodeCard key={node.node_id} node={node} />
            ))}
          </div>
        </section>

        {/* Timeline */}
        <section className="timeline-section">
          <div className="section-header">
            <div>
              <p className="eyebrow">SYSTEM ACTIVITY</p>
              <h3>Event Timeline</h3>
            </div>

            <Bell size={18} />
          </div>

          <EventTimeline events={sampleStream.events || []} />
        </section>
      </main>
    </div>
  );
}

export default App;