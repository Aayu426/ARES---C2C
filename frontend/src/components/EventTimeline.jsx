import { AlertTriangle, CheckCircle, Activity } from "lucide-react";

function EventTimeline({ events }) {
  if (!events.length) {
    return (
      <div className="empty-timeline">
        <Activity size={20} />
        <span>No events recorded.</span>
      </div>
    );
  }

  return (
    <div className="timeline">
      {events.map((event, index) => {
        const type = event.type?.toLowerCase();

        const Icon =
          type === "incident"
            ? AlertTriangle
            : CheckCircle;

        return (
          <div className="timeline-event" key={event.id || index}>
            <div className="timeline-icon">
              <Icon size={15} />
            </div>

            <div className="timeline-content">
              <div className="timeline-meta">
                <span>{event.ts || event.timestamp || "--:--:--"}</span>
                <span>{event.type || "EVENT"}</span>
              </div>

              <p>
                {event.message ||
                  event.reason ||
                  event.description ||
                  "System event detected"}
              </p>
            </div>
          </div>
        );
      })}
    </div>
  );
}

export default EventTimeline;