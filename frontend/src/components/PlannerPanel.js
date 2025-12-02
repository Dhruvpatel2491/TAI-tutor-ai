import React, { useState, useEffect, useCallback } from "react";
import { DEFAULT_BACKEND_URL } from "../config";
import { apiGet, apiPost } from "../services/http";
import { authService } from "../services/authService";

function PlannerPanel({ backendURL = DEFAULT_BACKEND_URL }) {
  const [token, setToken] = useState("");
  const [plans, setPlans] = useState([]);
  const [savedPlansError, setSavedPlansError] = useState("");
  const [savedPlansLoading, setSavedPlansLoading] = useState(false);
  const [filterText, setFilterText] = useState("");
  const [requirements, setRequirements] = useState("");
  const [msg, setMsg] = useState("");

  const [selectedPlan, setSelectedPlan] = useState(null);
  const [planText, setPlanText] = useState("");
  // user id / auth-disabled flows removed: app no longer relies on
  // default_dev_user or passing user_id when auth is disabled.
  const [isGenerating, setIsGenerating] = useState(false);
  const [generatedPlan, setGeneratedPlan] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [hasUnsavedGeneratedPlan, setHasUnsavedGeneratedPlan] = useState(false);

  // When a generated plan arrives and the user is in the editor (isTyping),
  // copy it into the editable planText field so the textarea shows the
  // generated content and becomes editable immediately.
  useEffect(() => {
    if (generatedPlan && isTyping && !planText) {
      setPlanText(generatedPlan);
    }
  }, [generatedPlan, isTyping, planText]);

  useEffect(() => {
    //console.log('BACKEND_URL=', process.env.REACT_APP_BACKEND_URL);
    // Load initial token from central authService before performing any
    // API calls so the first requests include the Authorization header.
    // Do NOT clear local/session storage here so a remembered session
    // persists across page reloads (fixes missing user info in storage).
    (async () => {
      try {
        // set initial token/state early
        try {
          const initial = authService.getToken();
          setToken(initial || "");
        } catch (e) {}
      } catch (e) {
        // ignore -- proceed with existing behavior
      }
      // then load plans (always trigger GET on page load)
      try {
        await fetchPlans();
        await refreshSavedPlans();
      } catch (e) {
        // ignore fetch errors here; fetchPlans sets error state
      }
    })();
    // listen for token changes via central auth service
    const unsub = authService.onAuthChange((t) => setToken(t || ""));
    return () => {
      try {
        unsub();
      } catch (e) {}
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleInvalidToken = () => {
    try {
      authService.clearToken();
    } catch (e) {}
    setToken("");
    setMsg("Session expired or invalid token. Please login again.");
  };

  const fetchPlans = useCallback(async () => {
    setMsg("");
    try {
      const headers = {};
      //console.log('Fetching plans with token:', token);
      if (token) headers["Authorization"] = `Bearer ${token}`;
      // Always call saved_plans without attaching ad-hoc user_id parameters.
      const url = `${backendURL}/saved_plans`;
      const res = await apiGet(url);
      if (res.ok) {
        const data = await res.json();
        // console.log('Fetched plans:', data);
        setPlans(data || []);

      } else if (res.status === 401) {
        const body = await res.json().catch(() => ({}));
        // console.log('fetchPlans:: body:', body);
        if (body && body.error && body.error.toLowerCase().includes("token")) {
          // console.log('Invalid token detected when fetching plans :: fetchPlans');
          handleInvalidToken();
        } else {
          setMsg("Unauthorized");
        }
      } else {
        const body = await res.json().catch(() => ({}));
        setMsg(body.error || "Failed to load plans");
      }
    } catch (e) {
      setMsg("Network error");
    }
  }, [backendURL, token]);

  // wrapper to expose a refresh helper that mirrors HomePage behavior
  const refreshSavedPlans = useCallback(async () => {
    setSavedPlansError("");
    setSavedPlansLoading(true);
    try {
      await fetchPlans();
    } catch (e) {
      console.error("Failed to refresh saved plans", e);
      setSavedPlansError("Failed to load saved plans");
    } finally {
      setSavedPlansLoading(false);
    }
  }, [fetchPlans]);

  // Create Plan: generate a plan from requirements (shows "Generating plan…")
  const createPlan = async () => {
    if (!requirements.trim()) {
      setMsg("Please enter plan requirements");
      return;
    }
    // token is optional; backend may accept unauthenticated requests depending on configuration
    setIsGenerating(true);
    // setMsg('Generating plan…');
    try {
      const headers = { "Content-Type": "application/json" };
      if (token) headers["Authorization"] = `Bearer ${token}`;
      const body = { requirement: requirements };
      const res = await apiPost(`${backendURL}/plans`, body);
      const data = await res.json().catch(() => ({}));
      if (res.ok) {
        const planText = data.plan_text || data.answer || data.text || "";
        // load into generated plan and switch to create/edit view for review
        //console.log('Generated plan text:', planText);
        setGeneratedPlan(planText || "");
        // mark that we have a newly generated plan that hasn't been saved yet
        setHasUnsavedGeneratedPlan(true);
        console.log("createPlan:: response data:", data);

        setSelectedPlan({
          name: data.name || "",
          owner: data.email || data.owner_id || data.user_id || "unknown",
          created_at: data.created_at || new Date().toISOString(),
          text: planText,
        });
        setMsg("Plan generated");

        // refresh saved plans list in case server persisted a draft
        fetchPlans();
      } else if (res.status === 401) {
        if (data && data.error && data.error.toLowerCase().includes("token")) {
          //console.log('Invalid token detected when generating plan :: createPlan');
          handleInvalidToken();
        } else {
          setMsg(data.error || "Unauthorized");
        }
      } else {
        setMsg(data.error || "Failed to generate plan");
      }
    } catch (e) {
      setMsg("Network error");
    } finally {
      setIsGenerating(false);
    }
  };

  const regenerateSavedPlan = async (path) => {
    if (!requirements.trim()) {
      setMsg("Please enter new requirement for regeneration");
      return;
    }
    setIsGenerating(true);
    try {
      const headers = { "Content-Type": "application/json" };
      if (token) headers["Authorization"] = `Bearer ${token}`;
      const body = {
        path: path,
        new_requirement: requirements,
        // include the original plan text so the backend can perform iterative regeneration
        original_plan_text: selectedPlan?.text || planText || "",
      };
      const res = await apiPost(`${backendURL}/saved_plans/update`, body);
      const data = await res.json().catch(() => ({}));
      if (res.ok) {
        const planText = data.plan_text || "";
        // update UI
        setSelectedPlan((prev) => ({ ...(prev || {}), text: planText }));
        setPlanText(planText);
        setGeneratedPlan(planText);
        setHasUnsavedGeneratedPlan(false);
        setMsg("Plan regenerated and updated");
        // refresh list
        fetchPlans();
      } else if (res.status === 401) {
        if (data && data.error && data.error.toLowerCase().includes("token")) {
          handleInvalidToken();
        } else {
          setMsg(data.error || "Unauthorized");
        }
      } else {
        setMsg(data.error || "Failed to regenerate plan");
      }
    } catch (e) {
      setMsg("Network error");
    } finally {
      setIsGenerating(false);
    }
  };

  const savePlan = async () => {
    // allow saving either the explicitly edited planText or the last generatedPlan
    const finalText = planText || generatedPlan;
    if (!finalText) {
      setMsg("No plan text to save");
      return;
    }
    const finalName =
      window.prompt("Enter a name for this plan (ascii only):") || "";
    if (!finalName) return;
    setMsg("Saving plan…");
    try {
      const headers = { "Content-Type": "application/json" };
      if (token) headers["Authorization"] = `Bearer ${token}`;
      const body = { plan_name: finalName, plan_text: finalText };
      const res = await apiPost(`${backendURL}/saved_plans`, body);
      const data = await res.json().catch(() => ({}));
      if (res.ok || res.status === 201) {
        setMsg("Plan saved");
        // refresh the user's plans list so the new plan appears
        try {
          fetchPlans();
        } catch (e) {
          /* ignore */
        }
        // reload to ensure caller sees fresh data (per UX requirement)
        // clear unsaved flag and reload
        setHasUnsavedGeneratedPlan(false);
        window.location.reload();
      } else if (res.status === 401) {
        if (data && data.error && data.error.toLowerCase().includes("token")) {
          //console.log('Invalid token detected when saving plan :: savePlan');
          handleInvalidToken();
        } else {
          setMsg(data.error || "Unauthorized");
        }
      } else {
        setMsg(data.error || "Failed to save plan");
      }
    } catch (e) {
      setMsg("Network error");
    }
  };

  const containerStyle = { width: "100%", margin: "0 auto" };

  // Simple markdown -> HTML renderer (supports **bold**, unordered/ordered lists, paragraphs, and basic code blocks)
  const escapeHtml = (unsafe) => {
    return (unsafe || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  };

  const renderMarkdown = (md) => {
    if (!md) return "";
    // normalize line endings
    const raw = String(md || "");
    const inputLines = raw.split(/\r?\n/);
    const out = [];
    let inUl = false;
    let inOl = false;
    let inCode = false;
    let codeBuffer = [];

    for (let i = 0; i < inputLines.length; i++) {
      const rawLine = inputLines[i];

      // Code fence handling (```)
      if (rawLine.trim().startsWith("```") ) {
        if (!inCode) {
          // enter code block
          inCode = true;
          codeBuffer = [];
        } else {
          // close code block
          inCode = false;
          const codeHtml = escapeHtml(codeBuffer.join("\n"));
          out.push(`<pre><code>${codeHtml}</code></pre>`);
          codeBuffer = [];
        }
        continue;
      }

      if (inCode) {
        // collect raw code lines (do not run markdown transforms)
        codeBuffer.push(rawLine);
        continue;
      }

      const line = rawLine.trim();
      // table detection: header row contains '|' and next line is a separator with '---'
      const nextLine = inputLines[i + 1] || "";
      const looksLikeTable = rawLine.includes("|") && nextLine.includes("---");
      if (looksLikeTable) {
        // close any open lists
        if (inUl) { out.push("</ul>"); inUl = false; }
        if (inOl) { out.push("</ol>"); inOl = false; }

        // parse header
        const headerCells = rawLine.split("|").map((c) => escapeHtml(c.trim())).filter((c) => c !== "");
        const rows = [];
        let j = i + 2;
        while (j < inputLines.length && inputLines[j].includes("|")) {
          const cells = inputLines[j].split("|").map((c) => escapeHtml(c.trim())).filter((c) => c !== "");
          rows.push(cells);
          j += 1;
        }
        // build table HTML
        out.push('<table class="md-table">');
        out.push('<thead><tr>' + headerCells.map((h) => `<th>${h}</th>`).join("") + '</tr></thead>');
        if (rows.length > 0) {
          out.push('<tbody>');
          rows.forEach((r) => {
            out.push('<tr>' + r.map((c) => `<td>${c}</td>`).join("") + '</tr>');
          });
          out.push('</tbody>');
        }
        out.push('</table>');
        // advance index to last consumed row
        i = j - 1;
        continue;
      }

      if (!line) {
        if (inUl) { out.push("</ul>"); inUl = false; }
        if (inOl) { out.push("</ol>"); inOl = false; }
        continue;
      }

      // inline transforms for non-code lines
      let safeLine = escapeHtml(line);
      // convert bold **text**
      safeLine = safeLine.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");

      const ulMatch = line.match(/^[-+*]\s+(.*)$/);
      const olMatch = line.match(/^\d+\.\s+(.*)$/);
      const h3 = line.match(/^###\s+(.*)$/);
      const h2 = line.match(/^##\s+(.*)$/);
      const h1 = line.match(/^#\s+(.*)$/);
      const strongOnly = safeLine.match(/^<strong>(.+)<\/strong>$/);

      if (ulMatch) {
        if (!inUl) { out.push("<ul>"); inUl = true; }
        out.push(`<li>${escapeHtml(ulMatch[1])}</li>`);
        continue;
      } else if (olMatch) {
        if (!inOl) { out.push("<ol>"); inOl = true; }
        out.push(`<li>${escapeHtml(olMatch[1])}</li>`);
        continue;
      } else if (h3) {
        out.push(`<h3>${escapeHtml(h3[1])}</h3>`);
        continue;
      } else if (h2) {
        out.push(`<h2>${escapeHtml(h2[1])}</h2>`);
        continue;
      } else if (h1) {
        out.push(`<h1>${escapeHtml(h1[1])}</h1>`);
        continue;
      } else if (strongOnly) {
        out.push(`<h2>${escapeHtml(strongOnly[1])}</h2>`);
        continue;
      }

      // plain paragraph line
      out.push(`<p>${safeLine}</p>`);
    }

    if (inUl) out.push("</ul>");
    if (inOl) out.push("</ol>");

    return out.join("\n");
  };

  // layout: left sidebar (list) + right sidebar (controls + detail/edit)
  const leftStyle = {
    width: "10%",
    minWidth: 220,
    borderRight: "1px solid #eee",
    paddingRight: 12,
  };
  const rightStyle = { flex: 1, paddingLeft: 12 };

  return (
    <div className="planner-panel card" style={containerStyle}>
      <h3>Planner</h3>

      {/* dev-mode user id input removed; app no longer depends on auth_disabled/default_dev_user */}

      <div style={{ display: "flex", gap: 12, marginTop: 12 }}>
        {/* Left sidebar: list of plans (title + date only) */}
        <div style={leftStyle}>
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
            }}
          >
            <h4 style={{ margin: 0 }}>Plans</h4>
            <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
              <span className="muted small-text">{plans.length}</span>
              <button className="btn secondary" onClick={refreshSavedPlans}>
                Refresh
              </button>
            </div>
          </div>
          <div style={{ marginTop: 8 }}>
            <input
              placeholder="Filter plans"
              value={filterText}
              onChange={(e) => setFilterText(e.target.value)}
              style={{
                width: "100%",
                padding: "6px 8px",
                boxSizing: "border-box",
              }}
            />
          </div>
          <div style={{ marginTop: 12 }}>
            {hasUnsavedGeneratedPlan && (
              <div className="muted" style={{ fontSize: 13, marginBottom: 8 }}>
                You are reviewing a newly-generated plan. Existing saved plans
                are temporarily non-interactive until you Save or Clear the new
                plan.
              </div>
            )}
            {savedPlansError && (
              <p className="muted" style={{ color: "crimson" }}>
                {savedPlansError}
              </p>
            )}
            {!savedPlansError && savedPlansLoading && (
              <p className="muted">Loading saved plans…</p>
            )}
            {!savedPlansError && !savedPlansLoading && plans.length === 0 && (
              <p className="muted">No plans yet</p>
            )}
            <ul style={{ listStyle: "none", padding: 0 }}>
              {plans
                .filter((p) =>
                  filterText
                    ? (p.name || p.filename || p.id || "")
                        .toLowerCase()
                        .includes(filterText.toLowerCase())
                    : true
                )
                .map((p, idx) => {
                  const isSelected =
                    selectedPlan &&
                    (selectedPlan.name === (p.name || p.filename) ||
                      selectedPlan.text === (p.plan_text || p.text || ""));
                  const disabledStyle = hasUnsavedGeneratedPlan
                    ? { opacity: 0.6, cursor: "not-allowed", pointerEvents: "none" }
                    : { cursor: "pointer" };
                  return (
                    <li
                      key={p.path || p.filename || p.id || idx}
                      style={{
                        marginBottom: 8,
                        padding: 8,
                        borderRadius: 6,
                        background: isSelected ? "#f6f9ff" : "transparent",
                        ...disabledStyle,
                      }}
                      onClick={hasUnsavedGeneratedPlan ? undefined : () => {
                        console.log("Selected plan:", p);
                        setSelectedPlan({
                          name: p.name || p.filename || "",
                          owner: p.owner || p.user_id || p.email || "Unknown",
                          created_at: p.created_at || p.created || "",
                          text: p.plan_text || p.text || "N/A Plan",
                          path: p.path || null,
                        });
                        setIsTyping(false);
                        setPlanText("");
                      }}
                    >
                      <div
                        style={{
                          display: "flex",
                          justifyContent: "space-between",
                          alignItems: "center",
                        }}
                      >
                        <strong style={{ fontSize: 14 }}>
                          {p.name || p.id || p.filename || `plan-${idx + 1}`}
                        </strong>
                        <span className="muted small-text" style={{ fontSize: 11 }}>
                          {(p.created_at || p.created || "").split("T")[0]}
                        </span>
                      </div>
                    </li>
                  );
                })}
            </ul>
          </div>
        </div>

        {/* Right sidebar: row1 controls, row2 detail/edit */}
        <div style={rightStyle}>
          {/* Row 1: controls */}
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <input
              placeholder="Enter instructions to create a plan"
              value={requirements}
              onChange={(e) => {
                setRequirements(e.target.value);
                setIsTyping(e.target.value.trim() !== "");
              }}
              onFocus={() => setIsTyping(true)}
              onBlur={() => {
                if (!requirements.trim()) setIsTyping(false);
              }}
              style={{ flex: 1, padding: "8px 10px" }}
              aria-label="plan-requirements"
            />
            <button
              type="button"
              className="btn"
              onClick={async () => {
                // If editing an existing saved plan (selectedPlan with path) and in edit mode,
                // call regeneration endpoint; otherwise create a new plan.
                if (isTyping && selectedPlan && selectedPlan.path) {
                  await regenerateSavedPlan(selectedPlan.path);
                } else {
                  setRequirements("");
                  setGeneratedPlan("");
                  setIsTyping(true);
                  setSelectedPlan(null);
                  setPlanText("");
                  await createPlan();
                }
              }}
              disabled={isGenerating || !requirements.trim()}
            >
              {isTyping && selectedPlan && selectedPlan.path ? "Edit Plan" : "Create Plan"}
            </button>
            <button
              className="btn secondary"
              onClick={() => {
                // Reset the whole planner UI to its base state
                setRequirements("");
                setIsTyping(false);
                setGeneratedPlan("");
                setPlanText("");
                setSelectedPlan(null);
                setHasUnsavedGeneratedPlan(false);
                setMsg("");
              }}
            >
              Clear
            </button>
          </div>

          {/* Row 2: if typing -> show blank editable area; else if selectedPlan -> show detail */}
          <div style={{ marginTop: 12 }}>
            {isTyping ? (
              <div>
                <textarea
                  value={planText}
                  onChange={(e) => setPlanText(e.target.value)}
                  placeholder={
                    isGenerating
                      ? "Generating plan..."
                      : "Provide instructions to create a new plan."
                  }
                  style={{
                    width: "100%",
                    minHeight: 240,
                    padding: 12,
                    boxSizing: "border-box",
                  }}
                />
                <div style={{ marginTop: 8, display: "flex", gap: 8 }}>
                  <button
                    className="btn"
                    onClick={() => {
                        setPlanText("");
                        setGeneratedPlan("");
                        // user reset -> no unsaved generated plan anymore
                        setHasUnsavedGeneratedPlan(false);
                    }}
                  >
                    Reset
                  </button>
                  <button
                    className="btn"
                    onClick={savePlan}
                    disabled={!(planText || generatedPlan)}
                  >
                    Save
                  </button>
                </div>
              </div>
            ) : selectedPlan ? (
              <div className="card" style={{ padding: 12 }}>
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                  }}
                >
                  <div>
                    <strong>{selectedPlan.name || "Untitled plan"}</strong>
                    <div className="muted small-text">
                      Owner: {selectedPlan.owner || "unknown"}
                    </div>
                    <div className="muted small-text">
                      Created: {selectedPlan.created_at || ""}
                    </div>
                  </div>
                  <div style={{ display: "flex", gap: 8 }}>
                    <button
                      className="btn"
                      onClick={() => {
                        setIsTyping(true);
                        setPlanText(selectedPlan.text || "");
                      }}
                    >
                      Edit
                    </button>
                    <button
                      className="btn secondary"
                      onClick={() => {
                        navigator.clipboard &&
                          navigator.clipboard.writeText(
                            selectedPlan.text || ""
                          );
                      }}
                    >
                      Copy
                    </button>
                  </div>
                </div>
                <div style={{ marginTop: 12 }}>
                  <div
                    style={{ background: "#fafafa", padding: 12 }}
                    dangerouslySetInnerHTML={{
                      __html: renderMarkdown(
                        selectedPlan.text || "No plan loaded"
                      ),
                    }}
                  />
                </div>
              </div>
            ) : (
              <div
                className="muted"
                style={{
                  padding: 12,
                  minHeight: 240,
                  border: "1px dashed #eee",
                  borderRadius: 6,
                }}
              >
                Select a plan from the left or Provide instructions to create a
                new plan..
              </div>
            )}
          </div>

          <div
            className="message text-success"
            aria-live="polite"
            style={{ marginTop: 12 }}
          >
            {msg}
          </div>

          {/* Generated preview (kept below) */}
          {generatedPlan && (
            <div className="card" style={{ padding: 12, marginTop: 12 }}>
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                }}
              >
                <h4 style={{ margin: 0 }}>Generated Plan Preview</h4>

              </div>
              <div style={{ marginTop: 12 }}>
                <div
                  style={{ background: "#fafafa", padding: 12 }}
                  dangerouslySetInnerHTML={{
                    __html: renderMarkdown(generatedPlan),
                  }}
                />
              </div>
              {/* <div style={{ marginTop: 12, display: 'flex', gap: 8 }}>
                <button className="btn" onClick={() => { setPlanText(generatedPlan); setIsTyping(true); }}>Edit / Save</button>
                <button className="btn" onClick={savePlan}>Save</button>
              </div> */}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default PlannerPanel;
