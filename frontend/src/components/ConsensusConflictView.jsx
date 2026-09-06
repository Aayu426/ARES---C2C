import { memo } from "react";
import { Users, AlertTriangle, CheckCircle2, UserCheck, HelpCircle } from "lucide-react";

/**
 * Consensus & Conflict View
 * Visualizes 2-against-1 multi-witness consensus vs physics evidence.
 * Highlights UNKNOWN / Awaiting Human intervention states.
 */
function ConsensusConflictView({ nodes = {}, claims = {}, conflicts = {} }) {
  const nodeA = nodes.A || {};
  const nodeB = nodes.B || {};
  const nodeC = nodes.C || {};
  const webcam = nodes.WEBCAM || {};

  // Motion Claim Consensus
  const motionWitnesses = [
    { id: "A", name: "ESP32 PIR", value: nodeA.last?.motion ?? 0, state: nodeA.state },
    { id: "C", name: "ESP32-CAM", value: nodeC.last?.motion ?? 0, state: nodeC.state },
    { id: "WEBCAM", name: "Webcam Vision", value: webcam.last?.motion ?? 0, state: webcam.state },
  ];

  // Water Claim Consensus
  const waterWitnesses = [
    { id: "B", name: "Water Sensor", value: nodeB.last?.water ?? 0, state: nodeB.state },
    { id: "C", name: "ESP32-CAM", value: nodeC.last?.water ?? 0, state: nodeC.state },
    { id: "WEBCAM", name: "Webcam Vision", value: webcam.last?.water ?? 0, state: webcam.state },
  ];

  const hasConflict = Object.keys(conflicts).length > 0;

  return (
    <div className="consensus-view-panel">
      <div className="consensus-header">
        <div>
          <span className="eyebrow">CONSENSUS & WITNESS VOTING</span>
          <h4>Multi-Witness Corroboration Matrix</h4>
        </div>
        {hasConflict ? (
          <div className="conflict-tag-pill awaiting-human">
            <UserCheck size={14} />
            <span>AWAITING HUMAN ESCALATION · UNRESOLVED CONFLICT</span>
          </div>
        ) : (
          <div className="conflict-tag-pill normal">
            <CheckCircle2 size={14} />
            <span>CONSENSUS RESOLVED (2-OF-3 QUORUM)</span>
          </div>
        )}
      </div>

      <div className="claims-grid">
        {/* Motion Consensus Card */}
        <div className="claim-consensus-card">
          <div className="claim-card-header">
            <strong>CLAIM: MOTION (Walkway)</strong>
            <span
              className={`claim-status-pill ${
                claims.motion?.status === "CONFIRMED" ? "status-confirmed" : "status-clear"
              }`}
            >
              {claims.motion?.status || "BASELINE CLEAR"}
            </span>
          </div>

          <div className="witness-voting-row">
            {motionWitnesses.map((w) => {
              const isShadow = w.state === "SHADOW";
              const reportsPositive = w.value === 1 || w.value === true;

              return (
                <div
                  key={w.id}
                  className={`witness-vote-box ${isShadow ? "vote-shadowed" : reportsPositive ? "vote-pos" : "vote-neg"}`}
                >
                  <div className="witness-id">
                    <span>{w.id}</span>
                    <small>{w.name}</small>
                  </div>
                  <div className="witness-verdict">
                    <strong>{reportsPositive ? "MOTION" : "CLEAR"}</strong>
                    <span className="vote-weight">
                      {isShadow ? "VOTE DISCARDED (SHADOW)" : "VOTE ACTIVE (1.0x)"}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Water Consensus Card */}
        <div className="claim-consensus-card">
          <div className="claim-card-header">
            <strong>CLAIM: WATER (Tray Overflow)</strong>
            <span
              className={`claim-status-pill ${
                claims.water?.status === "CONFIRMED" ? "status-confirmed" : "status-clear"
              }`}
            >
              {claims.water?.status || "BASELINE DRY"}
            </span>
          </div>

          <div className="witness-voting-row">
            {waterWitnesses.map((w) => {
              const isShadow = w.state === "SHADOW";
              const reportsPositive = w.value === 1 || w.value === true;

              return (
                <div
                  key={w.id}
                  className={`witness-vote-box ${isShadow ? "vote-shadowed" : reportsPositive ? "vote-pos" : "vote-neg"}`}
                >
                  <div className="witness-id">
                    <span>{w.id}</span>
                    <small>{w.name}</small>
                  </div>
                  <div className="witness-verdict">
                    <strong>{reportsPositive ? "WET" : "DRY"}</strong>
                    <span className="vote-weight">
                      {isShadow ? "VOTE DISCARDED (SHADOW)" : "VOTE ACTIVE (1.0x)"}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}

export default memo(ConsensusConflictView);
