import { memo } from "react";
import { Sparkles, Bot, AlertTriangle, X, ShieldAlert } from "lucide-react";

/**
 * Gemini AI Incident Explanation Panel / Modal
 * Displays natural language breakdown of incidents.
 * CRITICAL RULE: Strictly labeled "ADVISORY ONLY · AI NEVER DECIDES".
 */
function ExplainIncidentModal({
  explanation,
  isExplaining,
  onClose,
  onTriggerExplain,
  latestIncidentId,
}) {
  return (
    <div className="ai-explain-card">
      <div className="ai-header">
        <div className="ai-title-block">
          <Sparkles size={18} className="text-amber" />
          <div>
            <h4>ADAPTIVE INCIDENT EXPLAINER</h4>
            <span>Gemini LLM Forensic Reconstruction</span>
          </div>
        </div>

        <div className="advisory-badge">
          <ShieldAlert size={14} />
          <strong>ADVISORY ONLY · AI NEVER DECIDES</strong>
        </div>
      </div>

      <div className="ai-body">
        {isExplaining ? (
          <div className="ai-loading">
            <Sparkles size={20} className="ai-spinner text-amber" />
            <span>Generating cryptographic & consensus explanation...</span>
          </div>
        ) : explanation ? (
          <div className="ai-response-box">
            <div className="ai-source-meta">
              <Bot size={15} />
              <span>
                MODEL: {explanation.source?.toUpperCase() || "GEMINI"} · INCIDENT:{" "}
                {explanation.incidentId}
              </span>
            </div>

            <p className="ai-text-content">{explanation.text}</p>

            <div className="ai-disclaimer-footnote">
              * The ARES Consensus Engine and cryptographic verifiers reached all security
              actions deterministically prior to this advisory summary.
            </div>
          </div>
        ) : (
          <div className="ai-prompt-box">
            <p>
              Request a causal breakdown of recent node conflicts, integrity failures,
              and consensus decisions.
            </p>
            <button
              className="explain-btn"
              onClick={() => onTriggerExplain(latestIncidentId || "i-17")}
            >
              <Sparkles size={16} />
              <span>EXPLAIN LATEST INCIDENT WITH GEMINI</span>
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

export default memo(ExplainIncidentModal);
