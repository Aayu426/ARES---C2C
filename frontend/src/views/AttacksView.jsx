import { memo } from "react";
import { Zap, ShieldAlert, Smartphone } from "lucide-react";
import AttackPanel from "../components/AttackPanel";

function AttacksView({ onTriggerAttack, isConnected, nodes }) {
  return (
    <div className="view-container attacks-view-container">
      <div className="view-header">
        <div>
          <p className="eyebrow">JUDGE ADVERSARIAL ATTACK PANEL (§9)</p>
          <h2>Interactive Attack & Fault Injection</h2>
          <p className="subtitle">
            Simulate or dispatch physical attacks directly to target nodes. Large touch-friendly controls suitable for judges on phones or projectors.
          </p>
        </div>

        <div className="view-badge-info text-amber">
          <Zap size={16} />
          <span>DIRECT ADVERSARIAL CONTROLLER</span>
        </div>
      </div>

      <div className="attacks-fullpage-wrapper">
        <AttackPanel
          onTriggerAttack={onTriggerAttack}
          isConnected={isConnected}
          nodes={nodes}
        />
      </div>
    </div>
  );
}

export default memo(AttacksView);
