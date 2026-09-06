import { memo } from "react";
import { AlertOctagon, BellRing, ShieldAlert } from "lucide-react";

/**
 * Prominent Alarm Banner
 * Displayed when an alarm condition is confirmed by corroborated consensus
 * despite any sensor lying or in shadow.
 */
function AlarmBanner({ alarm, activeClaim }) {
  if (!alarm?.on) return null;

  const reason = alarm.reason || "Consensus confirmed physical anomaly";

  return (
    <div className="alarm-banner-container">
      <div className="alarm-banner-content">
        <div className="alarm-icon-box">
          <BellRing size={24} className="alarm-bell-anim" />
        </div>

        <div className="alarm-text-block">
          <div className="alarm-tag">CRITICAL ALERT · CONSENSUS CONFIRMED</div>
          <h3 className="alarm-title">
            PHYSICAL INCIDENT CONFIRMED · ALARM RINGS ANYWAY
          </h3>
          <p className="alarm-reason">
            <ShieldAlert size={14} />
            <span>Reason: {reason}</span>
          </p>
        </div>
      </div>

      <div className="alarm-status-pill">
        <AlertOctagon size={16} />
        <span>BUZZER + RELAY ACTIVE</span>
      </div>
    </div>
  );
}

export default memo(AlarmBanner);
