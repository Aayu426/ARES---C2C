import { memo, useEffect, useRef, useState } from "react";
import { Sparkles, Send, Volume2, Loader2 } from "lucide-react";

const API_BASE_URL =
  import.meta.env.VITE_API_URL || "http://localhost:8000";

const SUGGESTIONS = [
  "What is the most recent incident and what did ARES do?",
  "Which node lost trust and why?",
  "Was any claim rejected? Explain the evidence.",
];

/**
 * Audit-Log Assistant
 * Ask a plain-language question about the forensic audit log. The gateway answers with
 * Groq (advisory only, reads logged evidence) and, when an ElevenLabs key is configured,
 * speaks the answer aloud. Fully self-contained: mounts on the Forensic Audit Log.
 */
function AuditLogAssistant() {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState(null);
  const [source, setSource] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [voiceAvailable, setVoiceAvailable] = useState(false);
  const [speaking, setSpeaking] = useState(false);
  const audioRef = useRef(null);

  // Is the ElevenLabs voice reply configured on the gateway?
  useEffect(() => {
    let alive = true;
    fetch(`${API_BASE_URL}/voice/available`)
      .then((r) => r.json())
      .then((d) => alive && setVoiceAvailable(Boolean(d.available)))
      .catch(() => {});
    return () => {
      alive = false;
    };
  }, []);

  const ask = async (q) => {
    const query = (q ?? question).trim();
    if (!query || loading) return;
    setLoading(true);
    setError(null);
    setAnswer(null);
    try {
      const res = await fetch(`${API_BASE_URL}/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: query }),
      });
      if (!res.ok) throw new Error(`gateway ${res.status}`);
      const data = await res.json();
      setAnswer(data.answer);
      setSource(data.source);
    } catch (e) {
      setError("Could not reach the audit-log assistant. Is the gateway running?");
    } finally {
      setLoading(false);
    }
  };

  const speak = async () => {
    if (!answer || speaking) return;
    setSpeaking(true);
    try {
      const res = await fetch(`${API_BASE_URL}/tts`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: answer }),
      });
      if (!res.ok) throw new Error(`tts ${res.status}`);
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      if (audioRef.current) {
        audioRef.current.src = url;
        audioRef.current.onended = () => {
          setSpeaking(false);
          URL.revokeObjectURL(url);
        };
        await audioRef.current.play();
      }
    } catch (e) {
      setSpeaking(false);
    }
  };

  return (
    <div className="audit-assistant-card">
      <div className="assistant-heading-row">
        <Sparkles size={18} className="text-blue" />
        <div>
          <h3>Ask the Audit Log</h3>
          <p className="assistant-sub">
            Plain-language questions answered from logged evidence. Advisory only, the AI never decides.
          </p>
        </div>
      </div>

      <div className="assistant-input-row">
        <input
          type="text"
          className="assistant-input"
          placeholder="Ask what happened, which node, or why a claim was rejected..."
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && ask()}
          disabled={loading}
        />
        <button className="assistant-ask-btn" onClick={() => ask()} disabled={loading}>
          {loading ? <Loader2 size={16} className="spin" /> : <Send size={16} />}
          <span>{loading ? "Thinking" : "Ask"}</span>
        </button>
      </div>

      <div className="assistant-suggestions">
        {SUGGESTIONS.map((s) => (
          <button key={s} className="assistant-chip" onClick={() => { setQuestion(s); ask(s); }} disabled={loading}>
            {s}
          </button>
        ))}
      </div>

      {error && <div className="assistant-error">{error}</div>}

      {answer && (
        <div className="assistant-answer">
          <p>{answer}</p>
          <div className="assistant-answer-footer">
            <span className={`assistant-source ${source === "groq" ? "src-live" : "src-template"}`}>
              {source === "groq" ? "GROQ LLM" : "OFFLINE TEMPLATE"}
            </span>
            {voiceAvailable && (
              <button className="assistant-listen-btn" onClick={speak} disabled={speaking}>
                {speaking ? <Loader2 size={14} className="spin" /> : <Volume2 size={14} />}
                <span>{speaking ? "Speaking" : "Listen"}</span>
              </button>
            )}
          </div>
        </div>
      )}

      <audio ref={audioRef} hidden />
    </div>
  );
}

export default memo(AuditLogAssistant);
