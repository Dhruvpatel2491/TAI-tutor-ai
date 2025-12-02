import React, { useState, useEffect, useCallback } from "react";
import { DEFAULT_BACKEND_URL } from "../config";
import { apiGet, apiPost } from "../services/http";
import { authService } from "../services/authService";
import { renderPlanMarkdown } from "../utils/planFormatter";

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
  // view can be: 'dashboard' | 'new' | 'saved'
  const [view, setView] = useState("dashboard");
  // when viewing a saved plan, track whether user is editing it
  const [isEditingSaved, setIsEditingSaved] = useState(false);
  // when in saved view, variant controls whether cancel shows Clear afterwards
  const [savedViewVariant, setSavedViewVariant] = useState("initial");
  const [hasUnsavedGeneratedPlan, setHasUnsavedGeneratedPlan] = useState(false);

  // When a generated plan arrives and the user is in the editor (new/saved),
  // copy it into the editable planText field so the textarea shows the
  // generated content and becomes editable immediately.
  useEffect(() => {
    if (generatedPlan && (isEditingSaved || view === "new") && !planText) {
      setPlanText(generatedPlan);
    }
  }, [generatedPlan, isEditingSaved, view, planText]);

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

  // Regenerate an existing saved plan using a new requirement/instruction.
  const regenerateSavedPlan = async (path) => {
    if (!requirements.trim()) {
      setMsg("Please enter new requirement for regeneration");
      return;
    }
    setMsg("Creating updated plan…");
    setIsGenerating(true);
    try {
      const headers = { "Content-Type": "application/json" };
      if (token) headers["Authorization"] = `Bearer ${token}`;
      const body = {
        path: path,
        new_requirement: requirements,
        original_plan_text: selectedPlan?.text || planText || "",
      };
      const res = await apiPost(`${backendURL}/saved_plans/update`, body);
      const data = await res.json().catch(() => ({}));
      if (res.ok) {
        const newText = data.plan_text || "";
        setSelectedPlan((prev) => ({ ...(prev || {}), text: newText }));
        setPlanText(newText);
        setGeneratedPlan(newText);
        setHasUnsavedGeneratedPlan(false);
        setMsg("Plan regenerated and updated");
        try { fetchPlans(); } catch (e) {}
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

  

  const savePlan = async () => {
    // allow saving either the explicitly edited planText or the last generatedPlan
    const finalText = planText || generatedPlan;
    if (!finalText) {
      setMsg("No plan text to save");
      return;
    }
    // If editing an existing saved plan, update it in-place instead of
    // prompting for a new name. We treat plans with a `path` as saved plans.
    if (selectedPlan && selectedPlan.path) {
      setMsg("Saving changes to existing plan…");
      try {
        const headers = { "Content-Type": "application/json" };
        if (token) headers["Authorization"] = `Bearer ${token}`;
        const body = { path: selectedPlan.path, plan_text: finalText };
        const res = await apiPost(`${backendURL}/saved_plans/update`, body);
        const data = await res.json().catch(() => ({}));
        if (res.ok) {
          setMsg("Changes saved to existing plan");
          // update UI to reflect saved changes
          setSelectedPlan((prev) => ({ ...(prev || {}), text: finalText }));
          setGeneratedPlan(finalText);
          setHasUnsavedGeneratedPlan(false);
          // refresh the user's plans list so the updated text is visible
          try {
            fetchPlans();
          } catch (e) {
            /* ignore */
          }
        } else if (res.status === 401) {
          if (data && data.error && data.error.toLowerCase().includes("token")) {
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
      return;
    }

    // Otherwise create a new saved plan (prompt for a name)
    const finalName = window.prompt("Enter a name for this plan (ascii only):") || "";
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
        // clear unsaved flag and reload to ensure caller sees fresh data
        setHasUnsavedGeneratedPlan(false);
        window.location.reload();
      } else if (res.status === 401) {
        if (data && data.error && data.error.toLowerCase().includes("token")) {
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

  // Use centralized plan formatter for previews

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
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <h3 style={{ margin: 0 }}>Planner</h3>
        <button
          title="Create new plan"
          className="btn"
          aria-label="Create new plan"
          style={{ display: "inline-flex", alignItems: "center", justifyContent: "center", width: 34, height: 34, padding: 6, borderRadius: 6 }}
          onClick={() => {
            setView("new");
            setSelectedPlan(null);
            setRequirements("");
            setPlanText("");
            setGeneratedPlan("");
            setIsEditingSaved(false);
          }}
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <rect x="0" y="0" width="24" height="24" rx="4" fill="transparent" />
            <path d="M12 5v14" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            <path d="M5 12h14" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </button>
      </div>

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
                        // enter saved-plan view
                        setIsEditingSaved(false);
                        setSavedViewVariant("initial");
                        setView("saved");
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
            {(view !== "saved" || isEditingSaved) && (
              <input
                placeholder="Enter instructions to create a plan"
                value={requirements}
                onChange={(e) => {
                  setRequirements(e.target.value);
                }}
                style={{ flex: 1, padding: "8px 10px" }}
                aria-label="plan-requirements"
              />
            )}
            {/* Render buttons based on explicit view state */}
            {view === "dashboard" && (
              <>
                <button
                  type="button"
                  className="btn"
                  onClick={() => {
                    // Navigate to New Plan view keeping current requirement
                    setView("new");
                    setSelectedPlan(null);
                    setPlanText("");
                    setGeneratedPlan("");
                    setHasUnsavedGeneratedPlan(false);
                    setIsEditingSaved(false);
                  }}
                  disabled={!requirements.trim()}
                >
                  Create New Plan
                </button>
                <button
                  className="btn secondary"
                  onClick={() => {
                    // Reset the whole planner UI to its base state
                    setRequirements("");
                    setView("dashboard");
                    setGeneratedPlan("");
                    setPlanText("");
                    setSelectedPlan(null);
                    setHasUnsavedGeneratedPlan(false);
                    setMsg("");
                    setIsEditingSaved(false);
                    setSavedViewVariant("initial");
                  }}
                >
                  Clear
                </button>
              </>
            )}

            {view === "new" && (
              <>
                {!hasUnsavedGeneratedPlan ? (
                  <>
                    <button
                      type="button"
                      className="btn"
                      onClick={async () => {
                        try {
                          await createPlan();
                          setView("new");
                        } catch (e) {
                          console.error(e);
                        }
                      }}
                      disabled={isGenerating || !requirements.trim()}
                    >
                      Create New Plan
                    </button>
                    <button
                      className="btn secondary"
                      onClick={() => {
                        // Clear inputs for new plan creation
                        setRequirements("");
                        setGeneratedPlan("");
                        setPlanText("");
                        setHasUnsavedGeneratedPlan(false);
                        setMsg("");
                      }}
                    >
                      Clear
                    </button>
                  </>
                ) : (
                  // After generation: show Save, Cancel, Clear
                  <>
                    <button
                      className="btn"
                      onClick={async () => {
                        await savePlan();
                      }}
                    >
                      Save Plan
                    </button>
                    <button
                      className="btn"
                      onClick={() => {
                        // Cancel returns to dashboard but keep generated preview cleared
                        setView("dashboard");
                        setRequirements("");
                        setGeneratedPlan("");
                        setPlanText("");
                        setHasUnsavedGeneratedPlan(false);
                        setMsg("");
                      }}
                    >
                      Cancel
                    </button>
                    <button
                      className="btn secondary"
                      onClick={() => {
                        setRequirements("");
                        setGeneratedPlan("");
                        setPlanText("");
                        setHasUnsavedGeneratedPlan(false);
                        setMsg("");
                      }}
                    >
                      Clear
                    </button>
                  </>
                )}
              </>
            )}

            {view === "saved" && !isEditingSaved && selectedPlan && (
              <>
                <button
                  className="btn"
                  onClick={() => {
                    // Enter edit mode for this saved plan
                    setIsEditingSaved(true);
                    setPlanText(selectedPlan.text || "");
                  }}
                >
                  Edit Plan
                </button>
                <button
                  className="btn"
                  onClick={() => {
                    // Cancel in saved view (initial variant) -> if initial, show Cancel behavior
                    if (savedViewVariant === "initial") {
                      // switch to postCancel variant where Clear is shown instead
                      setSavedViewVariant("postCancel");
                    } else {
                      // otherwise clear selection and return to dashboard
                      setSelectedPlan(null);
                      setView("dashboard");
                      setSavedViewVariant("initial");
                    }
                  }}
                >
                  {savedViewVariant === "initial" ? "Cancel" : "Clear"}
                </button>
              </>
            )}

            {view === "saved" && isEditingSaved && selectedPlan && (
              <>
                <button
                  type="button"
                  className="btn"
                  onClick={async () => {
                    // Update Plan: require New Instruction to regenerate
                    if (selectedPlan && selectedPlan.path && requirements.trim()) {
                      // show explicit status while regeneration starts
                      setMsg("Updated plan is being Generated");
                      // show message in textarea while regenerating
                      setPlanText("Updating Plan with New Instructions");
                      setIsGenerating(true);
                      try {
                        await regenerateSavedPlan(selectedPlan.path);
                        setIsEditingSaved(false);
                        setSavedViewVariant("postCancel");
                      } finally {
                        setIsGenerating(false);
                      }
                    } else {
                      setMsg("Please enter a New Instruction to update this plan.");
                    }
                  }}
                >
                  Update Plan
                </button>
                <button
                  type="button"
                  className="btn"
                  onClick={() => {
                    // Cancel editing -> return to formatted saved view
                    setIsEditingSaved(false);
                    setSavedViewVariant("postCancel");
                  }}
                >
                  Cancel
                </button>
                <button
                  className="btn secondary"
                  onClick={() => {
                    // Clear selection (completely reset)
                    setSelectedPlan(null);
                    setView("dashboard");
                    setIsEditingSaved(false);
                    setSavedViewVariant("initial");
                    setRequirements("");
                    setPlanText("");
                    setGeneratedPlan("");
                  }}
                >
                  Clear
                </button>
              </>
            )}
          </div>

          {/* Row 2: editable area for editing saved plan; New view shows requirement + preview; Saved shows formatted view */}
          <div style={{ marginTop: 12 }}>
            {isEditingSaved ? (
              <div>
                    <div>
                      <textarea
                        value={planText}
                        onChange={(e) => setPlanText(e.target.value)}
                        placeholder={isGenerating ? "Generating plan..." : "Edit the selected plan here."}
                        style={{ width: "100%", minHeight: 160, padding: 12, boxSizing: "border-box" }}
                      />
                    </div>
                <div style={{ marginTop: 12 }}>
                  <h4>Formatted Preview</h4>
                  <div
                    style={{ background: "#fafafa", padding: 12 }}
                    dangerouslySetInnerHTML={{ __html: renderPlanMarkdown(planText || selectedPlan.text || "") }}
                  />
                </div>
              </div>
            ) : view === "new" ? (
              <div
                className="muted"
                style={{
                  padding: 12,
                  minHeight: 240,
                  border: "1px dashed #eee",
                  borderRadius: 6,
                }}
              >
                {isGenerating ? (
                  <div>Generating plan…</div>
                ) : !hasUnsavedGeneratedPlan ? (
                  <div>Provide requirements and click Create New Plan to generate.</div>
                ) : (
                  <div>
                    <div>
                      <textarea
                        value={planText}
                        onChange={(e) => setPlanText(e.target.value)}
                        style={{ width: "100%", minHeight: 160, padding: 12, boxSizing: "border-box" }}
                      />
                    </div>
                    <div style={{ marginTop: 12 }}>
                      <h4>Generated Plan Preview</h4>
                      <div style={{ background: "#fafafa", padding: 12 }} dangerouslySetInnerHTML={{ __html: renderPlanMarkdown(planText || generatedPlan) }} />
                    </div>
                  </div>
                )}
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
                    {/* Controls are shown at the top controls bar; keep this area minimal */}
                  </div>
                </div>
                <div style={{ marginTop: 12 }}>
                  <div className="muted small-text" style={{ marginBottom: 8 }}>
                    Tip: Saved plans also support Markdown tables. Use the same
                    table format as shown in the New Plan preview.
                  </div>
                  <div
                    style={{ background: "#fafafa", padding: 12 }}
                    dangerouslySetInnerHTML={{
                      __html: renderPlanMarkdown(
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

          {/* generated preview removed (rendered inline in New view or edit view) */}
        </div>
      </div>
    </div>
  );
}

export default PlannerPanel;
