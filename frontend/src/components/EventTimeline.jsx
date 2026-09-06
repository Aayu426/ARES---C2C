import {
  AlertTriangle,
  CheckCircle2,
  Activity,
  ShieldAlert,
  ShieldCheck,
  Bell,
} from "lucide-react";

function getEventMeta(event) {
  const type = (event.type || event.e || "").toUpperCase();

  switch (type) {
    case "INCIDENT":
      return {
        icon: <AlertTriangle size={15} />,
        label: "INCIDENT",
      };
    case "ALARM_ON":
      return {
        icon: <Bell size={15} />,
        label: "ALARM TRIGGERED",
      };
    case "ALARM_OFF":
      return {
        icon: <CheckCircle2 size={15} />,
        label: "ALARM CLEARED",
      };
    case "STATE_CHANGE":
      return {
        icon: <Activity size={15} />,
        label: "STATE CHANGE",
      };
    case "CHALLENGE_ISSUED":
      return {
        icon: <ShieldAlert size={15} />,
        label: "CHALLENGE ISSUED",
      };
    case "CHALLENGE_PASSED":
      return {
        icon: <ShieldCheck size={15} />,
        label: "CHALLENGE PASSED",
      };
    case "CHALLENGE_FAILED":
      return {
        icon: <ShieldAlert size={15} />,
        label: "CHALLENGE FAILED",
      };
    case "CLAIM_CONFIRMED":
      return {
        icon: <CheckCircle2 size={15} />,
        label: "CLAIM CONFIRMED",
      };
    default:
      return {
        icon: <Activity size={15} />,
        label: type || "EVENT",
      };
  }
}

function EventTimeline({ events = [] }) {
  if (!events.length) {
    return (
      <div className="empty-timeline">
        <Activity size={20} />
        <span>No events recorded yet. Waiting for telemetry...</span>
      </div>
    );
  }

  return (
    <div className="timeline">
      {events.map((event, index) => {
        const { icon, label } = getEventMeta(event);
        const time =
          event.timestamp ||
          (event.raw?.ts ? new Date(event.raw.ts).toLocaleTimeString() : "--:--:--");

        return (
          <div className="timeline-event" key={event.id || index}>
            <div className="timeline-icon">{icon}</div>

            <div className="timeline-content">
              <div className="timeline-meta">
                <span>{time}</span>
                <span>{label}</span>
                {event.node_id && <span>NODE {event.node_id}</span>}
              </div>

              <p>
                {event.message ||
                  event.summary ||
                  event.reason ||
                  "System event recorded"}
              </p>
            </div>
          </div>
        );
      })}
    </div>
  );
}

export default EventTimeline;