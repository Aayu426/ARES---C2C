import { memo } from "react";
import { History, Bell, Sparkles } from "lucide-react";
import EventTimeline from "../components/EventTimeline";
import ExplainIncidentModal from "../components/ExplainIncidentModal";
import AuditLogAssistant from "../components/AuditLogAssistant";

function IncidentsView({
  events = [],
  aiExplanation,
  isExplaining,
  onTriggerExplain,
  onCloseExplanation,
}) {
  const latestIncident = events.find(
    (e) => e.type === "INCIDENT" || e.raw?.e === "incident"
  );

  return (
    <div className="view-container incidents-view-container">
      <div className="view-header">
        <div>
          <p className="eyebrow">FORENSIC AUDIT & AI EXPLAINABILITY</p>
          <h2>System Incidents & AI Explanation</h2>
          <p className="subtitle">
            Cryptographic event timeline recording challenges, state transitions, consensus votes, and advisory AI forensic reconstruction.
          </p>
        </div>

        <div className="view-badge-info text-amber">
          <History size={16} />
          <span>IMMUTABLE AUDIT LOG</span>
        </div>
      </div>

      {/* Ask-the-audit-log assistant (Groq + optional ElevenLabs voice) */}
      <AuditLogAssistant />

      {/* AI Incident Explainer */}
      <div className="ai-explainer-section-wrapper">
        <ExplainIncidentModal
          explanation={aiExplanation}
          isExplaining={isExplaining}
          onClose={onCloseExplanation}
          onTriggerExplain={onTriggerExplain}
          latestIncidentId={latestIncident?.raw?.id || latestIncident?.id}
        />
      </div>

      {/* Full Forensic Event Timeline */}
      <div className="timeline-section fullpage-card">
        <div className="section-header">
          <div>
            <p className="eyebrow">AUDIT TRAIL</p>
            <h3>Complete Chronological Event Stream</h3>
          </div>
          <Bell size={18} />
        </div>

        <EventTimeline events={events} />
      </div>
    </div>
  );
}

export default memo(IncidentsView);
