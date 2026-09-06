import { memo } from "react";
import { BarChart3, CheckCircle2 } from "lucide-react";
import MetricsPanel from "../components/MetricsPanel";

function MetricsView({ metrics }) {
  return (
    <div className="view-container metrics-view-container">
      <div className="view-header">
        <div>
          <p className="eyebrow">EMPIRICAL BENCHMARK EVALUATION</p>
          <h2>System Performance & Detection Benchmarks</h2>
          <p className="subtitle">
            Measured against 20 test runs: detection latency, catch rate across spoof/tamper attacks, and zero-error false positive rate.
          </p>
        </div>

        <div className="view-badge-info text-green">
          <CheckCircle2 size={16} />
          <span>VERIFIED 20-RUN DATASET</span>
        </div>
      </div>

      <div className="metrics-fullpage-wrapper">
        <MetricsPanel metrics={metrics} />
      </div>
    </div>
  );
}

export default memo(MetricsView);
