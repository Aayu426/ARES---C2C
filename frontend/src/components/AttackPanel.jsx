import { useState, memo } from "react";
import { Zap, ShieldCheck, Flame, RotateCcw, Copy, Play, Smartphone } from "lucide-react";

/**
 * Judge Attack Panel
 * Provides 6 direct attack injection actions with target node selection
 * and mobile-responsive layout for phones.
 */
const TARGET_LABELS = [
  ["A", "Node A (PIR + Temp)"],
  ["B", "Node B (Water)"],
  ["C", "Node C (ESP32-CAM)"],
  ["WEBCAM", "WEBCAM (Laptop)"],
];

function AttackPanel({ onTriggerAttack, isConnected, nodes }) {
  const [selectedTarget, setSelectedTarget] = useState("A");
  const [statusMessage, setStatusMessage] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);

  const attacks = [
    {
      id: "suppress_motion",
      label: "SUPPRESS MOTION",
      target: "A",
      icon: <Zap size={16} />,
      colorClass: "btn-attack-suppress",
      desc: "Force PIR to report 0 despite movement",
    },
    {
      id: "suppress_water",
      label: "SUPPRESS WATER",
      target: "B",
      icon: <Zap size={16} />,
      colorClass: "btn-attack-suppress",
      desc: "Force Water sensor to report 0 despite liquid",
    },
    {
      id: "spoof",
      label: "SPOOF SIGNATURE",
      target: "A",
      icon: <Copy size={16} />,
      colorClass: "btn-attack-spoof",
      desc: "Inject frame with invalid HMAC key",
    },
    {
      id: "replay",
      label: "REPLAY ATTACK",
      target: "A",
      icon: <Play size={16} />,
      colorClass: "btn-attack-replay",
      desc: "Replay stale seq counter frames",
    },
    {
      id: "inject",
      label: "INJECT TEMP (80°C)",
      target: "A",
      icon: <Flame size={16} />,
      colorClass: "btn-attack-inject",
      desc: "Violate physics rules with 80°C jump",
    },
    {
      id: "restore",
      label: "RESTORE (HONEST)",
      target: "ALL",
      icon: <RotateCcw size={16} />,
      colorClass: "btn-attack-restore",
      desc: "Return firmware to baseline and begin recovery",
    },
  ];

  const handleAttackClick = async (attack) => {
    setIsProcessing(true);
    setStatusMessage(`Dispatching ${attack.label}...`);
    const target = attack.target === "ALL" ? selectedTarget : attack.target;

    try {
      const res = await onTriggerAttack(attack.id, target);
      setStatusMessage(res.message || `Executed: ${attack.label}`);
    } catch {
      setStatusMessage(`Error executing ${attack.label}`);
    } finally {
      setIsProcessing(false);
      setTimeout(() => setStatusMessage(null), 4000);
    }
  };

  return (
    <div className="attack-panel-card">
      <div className="attack-panel-header">
        <div className="attack-header-title">
          <Zap size={18} className="text-amber" />
          <div>
            <h4>JUDGE ATTACK PANEL</h4>
            <span>Interactive Adversarial Injection Matrix</span>
          </div>
        </div>

        <div className="target-selector-wrapper">
          <label>TARGET:</label>
          <select
            value={selectedTarget}
            onChange={(e) => setSelectedTarget(e.target.value)}
            className="target-select"
          >
            {TARGET_LABELS.filter(([id]) => !nodes || nodes[id]).map(([id, label]) => (
              <option key={id} value={id}>{label}</option>
            ))}
          </select>
        </div>
      </div>

      <div className="attack-buttons-grid">
        {attacks.map((atk) => (
          <button
            key={atk.id}
            className={`attack-btn ${atk.colorClass}`}
            onClick={() => handleAttackClick(atk)}
            disabled={isProcessing}
          >
            <div className="attack-btn-top">
              {atk.icon}
              <strong>{atk.label}</strong>
            </div>
            <small>{atk.desc}</small>
          </button>
        ))}
      </div>

      {statusMessage && (
        <div className="attack-status-ack">
          <ShieldCheck size={14} />
          <span>{statusMessage}</span>
        </div>
      )}
    </div>
  );
}

export default memo(AttackPanel);
