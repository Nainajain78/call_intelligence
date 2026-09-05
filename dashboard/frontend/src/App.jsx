import { useEffect, useState } from "react";
import {
  Upload,
  Phone,
  AlertTriangle,
  CheckCircle,
  Clock,
  ShieldAlert,
  User,
  Calendar,
  MessageSquare,
  X,
  Search,
  RefreshCw,
  FileText,
} from "lucide-react";
import "./App.css";

const API_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
function App() {
  const [calls, setCalls] = useState([]);
  const [selectedCall, setSelectedCall] = useState(null);
  const [transcript, setTranscript] = useState(null);
  const [showTranscript, setShowTranscript] = useState(false);

  const [loading, setLoading] = useState(true);
  const [loadingCall, setLoadingCall] = useState(false);

  const [showUpload, setShowUpload] = useState(false);

  const [search, setSearch] = useState("");

  const [error, setError] = useState("");

  useEffect(() => {
    fetchCalls();
  }, []);

  async function fetchCalls() {
    try {
      setLoading(true);
      setError("");

      const response = await fetch(`${API_URL}/api/calls`);

      if (!response.ok) {
        throw new Error(`Backend returned ${response.status}`);
      }

      const data = await response.json();
      setCalls(data);

      if (data.length > 0) {
        await fetchCallDetails(data[0].call_id);
      } else {
        setSelectedCall(null);
      }
    } catch (err) {
      console.error(err);
      setError("Could not connect to the Call Intelligence backend.");
    } finally {
      setLoading(false);
    }
  }

  async function fetchCallDetails(callId) {
    try {
      setLoadingCall(true);
      setError("");
      setTranscript(null);
      setShowTranscript(false);

      const response = await fetch(
        `${API_URL}/api/calls/${encodeURIComponent(callId)}`
      );

      if (!response.ok) {
        throw new Error("Failed to load call");
      }

      const data = await response.json();
      setSelectedCall(data);

      try {
        const transcriptRes = await fetch(
          `${API_URL}/api/calls/${encodeURIComponent(callId)}/transcript`
        );
        if (transcriptRes.ok) {
          const transcriptData = await transcriptRes.json();
          setTranscript(transcriptData);
        } else {
          setTranscript({ lines: [], unavailable: true });
        }
      } catch {
        setTranscript({ lines: [], unavailable: true });
      }
    } catch (err) {
      console.error(err);
      setError("Could not load this call.");
    } finally {
      setLoadingCall(false);
    }
  }

  const filteredCalls = calls.filter((call) => {
    const query = search.toLowerCase();
    return (
      call.call_id?.toLowerCase().includes(query) ||
      call.tag?.toLowerCase().includes(query) ||
      call.call_type?.toLowerCase().includes(query)
    );
  });

  if (loading) {
    return (
      <div className="loading-screen">
        <div className="spinner"></div>
        <p>Loading Call Intelligence...</p>
      </div>
    );
  }

  return (
    <div className="app">
      {/* SIDEBAR */}
      <aside className="sidebar">
        <div className="logo">
          <div className="logo-icon">
            <Phone size={19} />
          </div>
          <div>
            <h2>Call Intelligence</h2>
            <span>AI Review Platform</span>
          </div>
        </div>

        <div className="search-box">
          <Search size={15} />
          <input
            placeholder="Search calls..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        <div className="sidebar-label">CALLS</div>

        <div className="call-list">
          {filteredCalls.map((call) => (
            <button
              key={call.call_id}
              className={`call-list-item ${
                selectedCall?.call_id === call.call_id ? "active" : ""
              }`}
              onClick={() => fetchCallDetails(call.call_id)}
            >
              <div className="call-icon">
                <Phone size={14} />
              </div>
              <div className="call-info">
                <strong>{call.tag || call.call_id}</strong>
                <span>
                  {call.call_type || "general"}
                  {call.call_date ? ` • ${call.call_date}` : ""}
                </span>
              </div>
              <div className="sidebar-count">
                {call.human_review_count || 0}
              </div>
            </button>
          ))}
        </div>
      </aside>

      {/* MAIN */}
      <main className="main">
        <header className="header">
          <div>
            <div className="eyebrow">AI CALL REVIEW</div>
            <h1>Call Intelligence</h1>
            <p>Evidence-grounded summaries, actions and compliance review.</p>
          </div>

          <div className="header-actions">
            <button className="refresh-button" onClick={fetchCalls}>
              <RefreshCw size={16} />
              Refresh
            </button>
            <button
              className="upload-button"
              onClick={() => setShowUpload(true)}
            >
              <Upload size={17} />
              Analyze Call
            </button>
          </div>
        </header>

        {error && (
          <div className="error-banner">
            <AlertTriangle size={17} />
            {error}
          </div>
        )}

        <Metrics calls={calls} />

        {loadingCall ? (
          <div className="detail-loading">
            <div className="spinner"></div>
            Loading call analysis...
          </div>
        ) : selectedCall ? (
          <CallDetails
            call={selectedCall}
            onViewTranscript={() => setShowTranscript(true)}
            transcriptAvailable={
              transcript && !transcript.unavailable && transcript.lines?.length > 0
            }
          />
        ) : (
          <EmptyState onUpload={() => setShowUpload(true)} />
        )}
      </main>

      {showUpload && (
        <UploadModal
          onClose={() => setShowUpload(false)}
          onComplete={async () => {
            setShowUpload(false);
            await fetchCalls();
          }}
        />
      )}

      {showTranscript && (
        <TranscriptModal
          transcript={transcript}
          call={selectedCall}
          onClose={() => setShowTranscript(false)}
        />
      )}
    </div>
  );
}

/* ============================================================
   METRICS
============================================================ */

function Metrics({ calls }) {
  const totalReviews = calls.reduce(
    (sum, call) => sum + (call.human_review_count || 0),
    0
  );
  const totalCompliance = calls.reduce(
    (sum, call) => sum + (call.compliance_count || 0),
    0
  );
  const totalTriggers = calls.reduce(
    (sum, call) => sum + (call.trigger_count || 0),
    0
  );

  return (
    <section className="metrics">
      <Metric icon={<Phone size={18} />} label="Calls Analyzed" value={calls.length} />
      <Metric icon={<AlertTriangle size={18} />} label="Human Review" value={totalReviews} danger />
      <Metric icon={<ShieldAlert size={18} />} label="Compliance Flags" value={totalCompliance} />
      <Metric icon={<MessageSquare size={18} />} label="Special Triggers" value={totalTriggers} />
    </section>
  );
}

function Metric({ icon, label, value, danger }) {
  return (
    <div className="metric-card">
      <div className={`metric-icon ${danger ? "danger-bg" : ""}`}>{icon}</div>
      <div>
        <span>{label}</span>
        <strong>{value}</strong>
      </div>
    </div>
  );
}

/* ============================================================
   CALL DETAILS
============================================================ */

function CallDetails({ call, onViewTranscript, transcriptAvailable }) {
  const stats = call._dashboard_stats || {};

  return (
    <div className="details">
      {/* CALL HEADER */}
      <div className="call-header">
        <div>
          <div className="tag">{call.call_type || "GENERAL"}</div>
          <h2>{call.tag || "Call Analysis"}</h2>
          <div className="metadata">
            <span>
              <Calendar size={14} />
              {call.call_date || "Unknown date"}
            </span>
            <span>
              <FileText size={14} />
              {call.call_id}
            </span>
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
          <button
            className="transcript-button"
            onClick={onViewTranscript}
            disabled={!transcriptAvailable}
            title={transcriptAvailable ? "View original transcript" : "Transcript unavailable"}
          >
            <FileText size={15} />
            View Transcript
          </button>

          <div className="header-stat">
            <span>Human Review</span>
            <strong>
              {stats.human_review ?? call.human_review?.length ?? 0}
            </strong>
          </div>
        </div>
      </div>

      {/* SUMMARY */}
      <Section title="Summary" icon={<MessageSquare size={17} />}>
        <div className="summary">{call.summary || "No summary available."}</div>
      </Section>

      {/* DECISIONS */}
      <Section title="Decisions" icon={<CheckCircle size={17} />} count={call.decisions?.length}>
        {call.decisions?.length ? (
          call.decisions.map((decision, index) => (
            <GroundedItem
              key={index}
              icon={<CheckCircle size={18} className="green-icon" />}
              text={decision.text}
              confidence={decision.confidence}
              sourceLines={decision.source_lines}
              excerpts={decision.source_excerpts}
            />
          ))
        ) : (
          <EmptySection text="No decisions detected." />
        )}
      </Section>

      {/* ACTION ITEMS */}
      <Section title="Action Items" icon={<Clock size={17} />} count={call.action_items?.length}>
        {call.action_items?.length ? (
          call.action_items.map((item, index) => (
            <div className="item-card" key={index}>
              <div className="item-main">
                <Clock size={18} className="orange-icon" />
                <div className="item-content">
                  <p>{item.text}</p>
                  <div className="details-row">
                    {item.owner && (
                      <span>
                        <User size={13} />
                        <b>Owner:</b> {item.owner}
                      </span>
                    )}
                    {item.due_date && (
                      <span>
                        <Calendar size={13} />
                        <b>Due:</b> {item.due_date}
                      </span>
                    )}
                    {item.date_basis && (
                      <span>
                        <b>Basis:</b> {item.date_basis}
                      </span>
                    )}
                    {item.status && <span className="status">{item.status}</span>}
                  </div>
                  <Source lines={item.source_lines} excerpts={item.source_excerpts} />
                </div>
              </div>
              <Confidence value={item.confidence} />
            </div>
          ))
        ) : (
          <EmptySection text="No action items detected." />
        )}
      </Section>

      {/* BLOCKERS */}
      <Section title="Blockers" icon={<AlertTriangle size={17} />} count={call.blockers?.length}>
        {call.blockers?.length ? (
          call.blockers.map((blocker, index) => (
            <GroundedItem
              key={index}
              icon={<AlertTriangle size={18} className="red-icon" />}
              text={blocker.text}
              confidence={blocker.confidence}
              sourceLines={blocker.source_lines}
              excerpts={blocker.source_excerpts}
            />
          ))
        ) : (
          <EmptySection text="No blockers detected." />
        )}
      </Section>

      {/* COMPLIANCE */}
      <Section title="Compliance & Coaching" icon={<ShieldAlert size={17} />} count={call.compliance_flags?.length}>
        {call.compliance_flags?.length ? (
          call.compliance_flags.map((flag, index) => (
            <div className="compliance-card" key={index}>
              <div className="compliance-top">
                <span className={`severity ${String(flag.severity || "").toLowerCase()}`}>
                  {flag.severity}
                </span>
                <span className="category">{flag.category || "Compliance"}</span>
              </div>
              <p>{flag.text}</p>
              <Source lines={flag.source_lines} excerpts={flag.source_excerpts} />
              <Confidence value={flag.confidence} />
            </div>
          ))
        ) : (
          <EmptySection text="No compliance observations." />
        )}
      </Section>

      {/* SENTIMENT */}
      <Section title="Conversation Signals" icon={<MessageSquare size={17} />}>
        <div className="signals">
          <Signal label="Overall" value={call.sentiment?.overall} />
          <Signal label="Customer" value={call.sentiment?.customer_sentiment} />
          <Signal label="Agent" value={call.sentiment?.agent_sentiment} />
          <Signal label="Anger" value={call.sentiment?.anger_detected ? "Detected" : "Not detected"} />
          <Signal label="Profanity" value={call.sentiment?.profanity_detected ? "Detected" : "Not detected"} />
        </div>
        {call.sentiment?.notes && <p className="signal-notes">{call.sentiment.notes}</p>}
      </Section>

      {/* SPECIAL TRIGGERS */}
      <Section title="Special Triggers" icon={<AlertTriangle size={17} />} count={call.special_triggers?.length}>
        {call.special_triggers?.length ? (
          call.special_triggers.map((trigger, index) => (
            <GroundedItem
              key={index}
              icon={<AlertTriangle size={18} className="red-icon" />}
              text={trigger.text}
              confidence={trigger.confidence}
              sourceLines={trigger.source_lines}
              excerpts={trigger.source_excerpts}
            />
          ))
        ) : (
          <EmptySection text="No special triggers detected." />
        )}
      </Section>

      {/* HUMAN REVIEW */}
      <Section title="Human Review Required" icon={<AlertTriangle size={17} />} count={call.human_review?.length}>
        {call.human_review?.length ? (
          call.human_review.map((review, index) => (
            <div className="review-card" key={index}>
              <div className="review-header">
                <span className={`review-severity ${review.severity || "medium"}`}>
                  {review.severity || "review"}
                </span>
                {review.auto_flagged && <span className="auto">Automatically flagged</span>}
              </div>
              <h4>{review.reason}</h4>
              {review.related_item && <p>{review.related_item}</p>}
              <Source lines={review.source_lines} excerpts={review.source_excerpts} />
            </div>
          ))
        ) : (
          <div className="safe-message">
            <CheckCircle size={18} />
            No items currently require human review.
          </div>
        )}
      </Section>
    </div>
  );
}

/* ============================================================
   TRANSCRIPT MODAL
============================================================ */

function TranscriptModal({ transcript, call, onClose }) {
  return (
    <div className="modal-overlay" onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="modal transcript-modal">
        <div className="modal-header">
          <div>
            <h2>Original Transcript</h2>
            <p>{call?.tag || call?.call_id}</p>
          </div>
          <button className="close-button" onClick={onClose}>
            <X size={19} />
          </button>
        </div>

        <div className="transcript-modal-body">
          {!transcript ? (
            <div className="empty-section">Loading transcript...</div>
          ) : transcript.unavailable || !transcript.lines?.length ? (
            <div className="empty-section">Original transcript unavailable for this call.</div>
          ) : (
            transcript.lines.map((l) => {
              const match = l.text.match(/^([^:]+):\s*(.*)$/);
              const speaker = match ? match[1] : "";
              const text = match ? match[2] : l.text;
              return (
                <div className="transcript-line" key={l.line}>
                  <span className="transcript-ln">{l.line}</span>
                  <span className="transcript-speaker">{speaker}</span>
                  <span className="transcript-text">{text}</span>
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}

/* ============================================================
   GROUNDED ITEM
============================================================ */

function GroundedItem({ icon, text, confidence, sourceLines, excerpts }) {
  return (
    <div className="item-card">
      <div className="item-main">
        {icon}
        <div className="item-content">
          <p>{text}</p>
          <Source lines={sourceLines} excerpts={excerpts} />
        </div>
      </div>
      <Confidence value={confidence} />
    </div>
  );
}

/* ============================================================
   SOURCE
============================================================ */

function Source({ lines, excerpts }) {
  if (!lines?.length && !excerpts?.length) {
    return null;
  }

  return (
    <div className="source">
      <div className="source-label">SOURCE EVIDENCE</div>
      <div className="source-lines">
        {(excerpts?.length ? excerpts : lines?.map((line) => ({ line, text: null })))?.map(
          (item, index) => (
            <div className="source-excerpt" key={index}>
              <span>Line {item.line}</span>
              {item.text ? <p>{item.text}</p> : <p className="no-excerpt">Transcript excerpt unavailable</p>}
            </div>
          )
        )}
      </div>
    </div>
  );
}

/* ============================================================
   CONFIDENCE
============================================================ */

function Confidence({ value }) {
  if (value === undefined || value === null) {
    return null;
  }
  const percentage = Math.round(value * 100);
  return (
    <div className="confidence">
      <span>CONFIDENCE</span>
      <strong>{percentage}%</strong>
    </div>
  );
}

/* ============================================================
   SIGNAL
============================================================ */

function Signal({ label, value }) {
  return (
    <div className="signal">
      <span>{label}</span>
      <strong>{value || "N/A"}</strong>
    </div>
  );
}

/* ============================================================
   SECTION
============================================================ */

function Section({ title, icon, count, children }) {
  return (
    <section className="section">
      <div className="section-header">
        <div className="section-title-wrapper">
          {icon}
          <h3>{title}</h3>
          {count !== undefined && <span className="count">{count}</span>}
        </div>
      </div>
      {children}
    </section>
  );
}

/* ============================================================
   EMPTY
============================================================ */

function EmptySection({ text }) {
  return <div className="empty-section">{text}</div>;
}

function EmptyState({ onUpload }) {
  return (
    <div className="empty-state">
      <FileText size={40} />
      <h2>No calls analyzed yet</h2>
      <p>Upload a transcript to run the Call Intelligence pipeline.</p>
      <button className="upload-button" onClick={onUpload}>
        <Upload size={17} />
        Analyze Call
      </button>
    </div>
  );
}

/* ============================================================
   UPLOAD MODAL
============================================================ */

function UploadModal({ onClose, onComplete }) {
  const [file, setFile] = useState(null);
  const [callType, setCallType] = useState("general");
  const [callDate, setCallDate] = useState(new Date().toISOString().split("T")[0]);
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState("");
  const [success, setSuccess] = useState(false);

  function handleFile(selectedFile) {
    if (!selectedFile) {
      return;
    }
    const allowed = [".txt", ".text", ".transcript", ".json"];
    const extension = selectedFile.name.substring(selectedFile.name.lastIndexOf(".")).toLowerCase();
    if (!allowed.includes(extension)) {
      setUploadError("Please upload a .txt, .text, .transcript or .json file.");
      return;
    }
    setUploadError("");
    setFile(selectedFile);
  }

  async function submit() {
    if (!file) {
      setUploadError("Please select a transcript first.");
      return;
    }
    try {
      setUploading(true);
      setUploadError("");

      const formData = new FormData();
      formData.append("file", file);
      formData.append("call_type", callType);
      formData.append("call_date", callDate);

      const response = await fetch(`${API_URL}/api/analyze`, {
        method: "POST",
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Analysis failed");
      }

      setSuccess(true);
      setTimeout(() => {
        onComplete();
      }, 700);
    } catch (err) {
      console.error(err);
      setUploadError(err.message || "Could not analyze the call.");
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="modal-overlay">
      <div className="modal">
        <div className="modal-header">
          <div>
            <h2>Analyze New Call</h2>
            <p>Upload a transcript and run the complete AI pipeline.</p>
          </div>
          <button className="close-button" onClick={onClose}>
            <X size={19} />
          </button>
        </div>

        {success ? (
          <div className="upload-success">
            <CheckCircle size={42} />
            <h3>Analysis complete</h3>
            <p>The call has been added to your dashboard.</p>
          </div>
        ) : (
          <>
            <div
              className={`drop-zone ${dragging ? "dragging" : ""} ${file ? "has-file" : ""}`}
              onDragOver={(e) => {
                e.preventDefault();
                setDragging(true);
              }}
              onDragLeave={() => setDragging(false)}
              onDrop={(e) => {
                e.preventDefault();
                setDragging(false);
                handleFile(e.dataTransfer.files[0]);
              }}
              onClick={() => document.getElementById("call-file").click()}
            >
              <input
                id="call-file"
                type="file"
                accept=".txt,.text,.transcript,.json"
                hidden
                onChange={(e) => handleFile(e.target.files[0])}
              />
              <Upload size={30} />
              {file ? (
                <>
                  <strong>{file.name}</strong>
                  <span>File selected</span>
                </>
              ) : (
                <>
                  <strong>Drop transcript here</strong>
                  <span>or click to browse</span>
                </>
              )}
            </div>

            <div className="form-grid">
              <label>
                <span>Call Type</span>
                <select value={callType} onChange={(e) => setCallType(e.target.value)}>
                  <option value="general">General</option>
                  <option value="collections">Collections</option>
                  <option value="support">Support</option>
                  <option value="sales">Sales</option>
                  <option value="standup">Standup</option>
                </select>
              </label>

              <label>
                <span>Call Date</span>
                <input type="date" value={callDate} onChange={(e) => setCallDate(e.target.value)} />
              </label>
            </div>

            {uploadError && (
              <div className="upload-error">
                <AlertTriangle size={16} />
                {uploadError}
              </div>
            )}

            <div className="modal-footer">
              <button className="cancel-button" onClick={onClose} disabled={uploading}>
                Cancel
              </button>
              <button className="upload-button" onClick={submit} disabled={uploading || !file}>
                {uploading ? (
                  <>
                    <div className="small-spinner"></div>
                    Analyzing...
                  </>
                ) : (
                  <>
                    <Upload size={16} />
                    Run AI Analysis
                  </>
                )}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

export default App;
