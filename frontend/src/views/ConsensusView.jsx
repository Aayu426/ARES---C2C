import { memo } from "react";
import { Users, Info } from "lucide-react";
import ConsensusConflictView from "../components/ConsensusConflictView";

function ConsensusView({ nodes = {}, claims = {}, conflicts = {} }) {
  return (
    <div className="view-container consensus-view-container">
      <div className="view-header">
        <div>
          <p className="eyebrow">CONSENSUS & WITNESS CORROBORATION</p>
          <h2>Multi-Witness Quorum & Conflict Resolution</h2>
          <p className="subtitle">
            A single shadowed liar cannot suppress a claim that independent witnesses can corroborate. Majority voting across the live witnesses for motion and water claims.
          </p>
        </div>

        <div className="view-badge-info">
          <Users size={16} />
          <span>MULTI-WITNESS QUORUM</span>
        </div>
      </div>

      <div className="view-content-card">
        <ConsensusConflictView
          nodes={nodes}
          claims={claims}
          conflicts={conflicts}
        />
      </div>
    </div>
  );
}

export default memo(ConsensusView);
