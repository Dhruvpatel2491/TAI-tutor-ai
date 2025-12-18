import React, { useState, useEffect, useCallback, useRef } from "react";
import { DEFAULT_BACKEND_URL } from "../config";
import { apiGet, apiPost } from "../services/http";
import { authService } from "../services/authService";
import { renderPlanMarkdown } from "../utils/planFormatter";
import ConfirmModal from "./ConfirmModal";
import PromptModal from "./PromptModal";
import "../styles/PlannerPage.css";

function PlannerPanel({ backendURL = DEFAULT_BACKEND_URL }) {
  const [token, setToken] = useState("");
  const [plans, setPlans] = useState([]);
  const [savedPlansError, setSavedPlansError] = useState("");
  const [savedPlansLoading, setSavedPlansLoading] = useState(false);
  const [filterText, setFilterText] = useState("");
  const [requirements, setRequirements] = useState("");
  const [msg, setMsg] = useState("");

  // Confirm modal state
  const [confirmModal, setConfirmModal] = useState({
    isOpen: false,
    title: "",
    message: "",
    onConfirm: null,
    variant: "warning",
    confirmText: "Confirm",
    cancelText: "Cancel"
  });

  // Prompt modal state
  const [promptModal, setPromptModal] = useState({
    isOpen: false,
    title: "",
    message: "",
    placeholder: "",
    defaultValue: "",
    onConfirm: null,
    variant: "primary",
    confirmText: "OK",
    cancelText: "Cancel"
  });

  const [selectedPlan, setSelectedPlan] = useState(null);
  const [planText, setPlanText] = useState("");
  // user id / auth-disabled flows removed: app no longer relies on
  // default_dev_user or passing user_id when auth is disabled.
  const [isGenerating, setIsGenerating] = useState(false);
  const [generatedPlan, setGeneratedPlan] = useState("");
  // view can be: 'dashboard' | 'new' | 'saved' | 'edit' | 'preview'
  const [view, setView] = useState("dashboard");
  // when viewing a saved plan, track whether user is editing it
  const [isEditingSaved, setIsEditingSaved] = useState(false);
  // (legacy saved view variant removed; preview/edit flow used instead)
  const [hasUnsavedGeneratedPlan, setHasUnsavedGeneratedPlan] = useState(false);

  // Track unsaved changes for cancel confirmation
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
  const prevPlanTextRef = useRef("");

  // When a generated plan arrives and the user is in the editor (new/saved),
  // copy it into the editable planText field so the textarea shows the
  // generated content and becomes editable immediately.
  useEffect(() => {
    if (generatedPlan && (isEditingSaved || view === "new")) {
      setPlanText(generatedPlan);
      setHasUnsavedChanges(true);
    }
  }, [generatedPlan, isEditingSaved, view]);

  // Track unsaved changes when planText changes
  useEffect(() => {
    if (view === "edit" || view === "new") {
      setHasUnsavedChanges(planText !== prevPlanTextRef.current);
    }
    prevPlanTextRef.current = planText;
  }, [planText, view]);

  // If a plan is selected from the left list, navigate to the Plan Preview
  // view to display the saved plan. Do not override selection when the user
  // is actively working on an unsaved generated plan.
  useEffect(() => {
    if (selectedPlan && !hasUnsavedGeneratedPlan) {
      setView("preview");
      setIsEditingSaved(false);
      setPlanText(selectedPlan.text || "");
      
    }
  }, [selectedPlan, hasUnsavedGeneratedPlan]);

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

  // Helper to show confirmation modal
  const showConfirmModal = (title, message, onConfirm, variant = "warning", confirmText = "Confirm", cancelText = "Cancel") => {
    setConfirmModal({
      isOpen: true,
      title,
      message,
      onConfirm,
      variant,
      confirmText,
      cancelText
    });
  };

  // Helper to close confirmation modal
  const closeConfirmModal = () => {
    setConfirmModal({
      isOpen: false,
      title: "",
      message: "",
      onConfirm: null,
      variant: "warning",
      confirmText: "Confirm",
      cancelText: "Cancel"
    });
  };

  // Helper to show prompt modal
  const showPromptModal = (title, message, onConfirm, placeholder = "", defaultValue = "", variant = "primary", confirmText = "OK", cancelText = "Cancel") => {
    setPromptModal({
      isOpen: true,
      title,
      message,
      placeholder,
      defaultValue,
      onConfirm,
      variant,
      confirmText,
      cancelText
    });
  };

  // Helper to close prompt modal
  const closePromptModal = () => {
    setPromptModal({
      isOpen: false,
      title: "",
      message: "",
      placeholder: "",
      defaultValue: "",
      onConfirm: null,
      variant: "primary",
      confirmText: "OK",
      cancelText: "Cancel"
    });
  };

  const handleInvalidToken = () => {
    try {
      authService.clearToken();
    } catch (e) {}
    setToken("");
    setMsg("Session expired or invalid token. Please login again.");
    // Force a full reload so app-level routing / auth checks redirect to login
    window.location.reload();

  };

  // Regenerate an existing saved plan using a new requirement/instruction.
  const regenerateSavedPlan = async (path) => {
    if (!requirements.trim()) {
      setMsg("Please enter new requirement for regeneration");
      return;
    }
    setMsg("Regenerating plan…");
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
        // regenerated content should be treated as an unsaved generated plan
        setHasUnsavedGeneratedPlan(true);
        setMsg("Plan regenerated successfully. Review and save to overwrite.");
        setView("edit");
        setIsEditingSaved(true);
        setHasUnsavedChanges(true);
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

  // Create Plan: generate a plan from requirements (shows loading spinner)
  const createPlan = async () => {
    if (!requirements.trim()) {
      setMsg("Please enter plan requirements");
      return;
    }
    // token is optional; backend may accept unauthenticated requests depending on configuration
    setIsGenerating(true);
    setMsg('Generating plan…');
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
        setMsg("Plan generated successfully");

        // refresh saved plans list in case server persisted a draft
        fetchPlans();
        // Move into Edit/Update Plan View so user can tweak, regenerate, or save
        setView("edit");
        setIsEditingSaved(true);
        setPlanText(planText || "");
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

  // Delete a saved plan by path
  const deletePlan = async (path) => {
    if (!path) {
      setMsg("No saved plan path provided for deletion");
      return;
    }
    
    // Show custom confirmation modal instead of window.confirm
    showConfirmModal(
      "Delete Plan",
      "Delete this plan? This action cannot be undone.",
      async () => {
        await performDeletePlan(path);
      },
      "danger",
      "Delete",
      "Cancel"
    );
  };

  // Actual delete operation (separated for modal callback)
  const performDeletePlan = async (path) => {
    setMsg("Deleting plan…");
    try {
      const headers = { "Content-Type": "application/json" };
      if (token) headers["Authorization"] = `Bearer ${token}`;
      const body = { path };
      const res = await apiPost(`${backendURL}/saved_plans/delete`, body);
      const data = await res.json().catch(() => ({}));
      if (res.ok) {
        setMsg("Plan deleted");
        // refresh plans and clear selection
        try { await fetchPlans(); } catch (e) {}
        setSelectedPlan(null);
        setView("dashboard");
      } else if (res.status === 401) {
        if (data && data.error && data.error.toLowerCase().includes("token")) {
          handleInvalidToken();
        } else {
          setMsg(data.error || "Unauthorized");
        }
      } else {
        setMsg(data.error || "Failed to delete plan");
      }
    } catch (e) {
      setMsg("Network error");
    }
  };

  

  const savePlan = async () => {
    // allow saving either the explicitly edited planText or the last generatedPlan
    const finalText = planText || generatedPlan;
    if (!finalText) {
      setMsg("No plan text to save");
      return;
    }
    // If editing an existing saved plan, prompt for confirmation to overwrite
    if (selectedPlan && selectedPlan.path) {
      showConfirmModal(
        "Overwrite Plan",
        `Overwrite existing plan '${selectedPlan.name}'? This action cannot be undone.`,
        async () => {
          await performSaveExistingPlan(selectedPlan.path, finalText);
        },
        "warning",
        "Overwrite",
        "Cancel"
      );
      return;
    }

    // Otherwise create a new saved plan (prompt for a name)
    showPromptModal(
      "Save Plan",
      "Enter a name for this plan (ASCII characters only):",
      async (finalName) => {
        if (finalName) {
          await performSaveNewPlan(finalName, finalText);
        }
      },
      "Plan name",
      selectedPlan?.name || "",
      "primary",
      "Save",
      "Cancel"
    );
  };

  // Separated save operations for modal callbacks
  const performSaveExistingPlan = async (path, finalText) => {
    setMsg("Saving changes…");
    try {
      const headers = { "Content-Type": "application/json" };
      if (token) headers["Authorization"] = `Bearer ${token}`;
      const body = { path: path, plan_text: finalText };
      const res = await apiPost(`${backendURL}/saved_plans/update`, body);
      const data = await res.json().catch(() => ({}));
      if (res.ok) {
        setMsg("Changes saved successfully");
        setSelectedPlan((prev) => ({ ...(prev || {}), text: finalText }));
        setGeneratedPlan(finalText);
        setHasUnsavedGeneratedPlan(false);
        setHasUnsavedChanges(false);
        try {
          fetchPlans();
        } catch (e) {}
        setIsEditingSaved(false);
        setView("preview");
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

  const performSaveNewPlan = async (finalName, finalText) => {
    setMsg("Saving plan…");
    try {
      const headers = { "Content-Type": "application/json" };
      if (token) headers["Authorization"] = `Bearer ${token}`;
      const body = { plan_name: finalName, plan_text: finalText };
      const res = await apiPost(`${backendURL}/saved_plans`, body);
      const data = await res.json().catch(() => ({}));
      if (res.ok || res.status === 201) {
        setMsg("Plan saved successfully");
        try {
          fetchPlans();
        } catch (e) {}
        setHasUnsavedGeneratedPlan(false);
        setHasUnsavedChanges(false);
        setView("preview");
        if (data && data.path) {
          setSelectedPlan((prev) => ({ ...(prev || {}), path: data.path }));
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
  };

  // --- Small subcomponents for readability (kept inside same file) ---
  const LoadingSpinner = () => (
    <div className="planner-loading-container">
      <div className="spinner"></div>
      <span className="planner-loading-text">Please wait, Generating Your Personalized Plan...</span>
    </div>
  );
  // --- View Components ---
  const CreateNewPlanView = ({
    isGenerating,
    hasUnsavedGeneratedPlan,
    planText,
    setPlanText,
    generatedPlan,
    renderPlanMarkdown,
    LoadingSpinner
  }) => (
    <div className="muted planner-create-view">
      {isGenerating ? (
        <LoadingSpinner />
      ) : !hasUnsavedGeneratedPlan ? (
        <div>Provide requirements and click Create New Plan to generate.</div>
      ) : (
        <div>
          <div>
            <textarea
              value={planText}
              onChange={(e) => setPlanText(e.target.value)}
              className="planner-textarea"
            />
          </div>
          <div className="planner-preview-section">
            <h4>Generated Plan Preview</h4>
            <div className="planner-preview-content" dangerouslySetInnerHTML={{ __html: renderPlanMarkdown(planText || generatedPlan) }} />
          </div>
        </div>
      )}
    </div>
  );

  const EditUpdatePlanView = ({
    isGenerating,
    planText,
    setPlanText,
    selectedPlan,
    renderPlanMarkdown,
    LoadingSpinner
  }) => (
    <div>
      {isGenerating ? <LoadingSpinner /> : (
        <>
          <div>
            <textarea
              value={planText}
              onChange={(e) => setPlanText(e.target.value)}
              placeholder={"Edit the selected plan here."}
              className="planner-textarea"
            />
          </div>
          <div className="planner-preview-section">
            <h4>Formatted Preview</h4>
            <div
              className="planner-preview-content-large"
              dangerouslySetInnerHTML={{ __html: renderPlanMarkdown(planText || (selectedPlan && selectedPlan.text) || "") }}
            />
          </div>
        </>
      )}
    </div>
  );

  const PlanPreviewView = ({
    selectedPlan,
    renderPlanMarkdown
  }) => (
    <div className="card planner-plan-preview-card">
      <div className="planner-plan-preview-header">
        <div>
          <strong className="planner-plan-preview-title">{selectedPlan?.name || "Untitled plan"}</strong>
          <div className="planner-plan-preview-meta">
            <div className="muted small-text planner-plan-preview-meta-item">Owner: <strong className="planner-plan-preview-meta-value">{selectedPlan?.owner || "unknown"}</strong></div>
            <div className="muted small-text planner-plan-preview-meta-item">Created: <strong className="planner-plan-preview-meta-value">{formatDateFriendly(selectedPlan?.created_at)}</strong></div>
          </div>
        </div>
        <div className="planner-plan-preview-actions" />
      </div>
      <div className="planner-plan-preview-body">
        <div className="planner-preview-content-large" dangerouslySetInnerHTML={{ __html: renderPlanMarkdown(selectedPlan?.text || "No plan loaded") }} />
      </div>
    </div>
  );

  // Helper: friendly date formatting with graceful fallback
  function formatDateFriendly(dt) {
    if (!dt) return "";
    try {
      const d = new Date(dt);
      if (isNaN(d.getTime())) return dt;
      // include short time for clarity
      return d.toLocaleString(undefined, { year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
    } catch (e) {
      return dt;
    }
  }

  // Helper: decide message type for UI (error / success / info)
  function getMessageMeta(text) {
    if (!text) return { type: null };
    const t = text.toLowerCase();
    if (/(failed|fail|error|unauthor|invalid|network|session expired)/i.test(t)) return { type: 'error' };
    if (/(saved|success|generated|created)/i.test(t)) return { type: 'success' };
    return { type: 'info' };
  }

  return (
    <div className="planner-panel card planner-panel-container">
      {/* <div className="planner-header">
        <button
          title="Create new plan"
          className="btn planner-new-btn"
          aria-label="Create new plan"
          onClick={() => {
            setView("new");
            setSelectedPlan(null);
            setRequirements("");
            setPlanText("");
            setGeneratedPlan("");
            setIsEditingSaved(false);
          }}
        >
          + Create New Plan
        </button>
      </div> */}

      {/* dev-mode user id input removed; app no longer depends on auth_disabled/default_dev_user */}

      <div className="planner-main-layout">
        {/* Left sidebar: list of plans (title + date only) */}
        <div className="planner-left-sidebar">
          <div className="planner-header-createplan">
            <button
              title="Create new plan"
              className="planner-new-btn btn"
              aria-label="Create new plan"
              onClick={() => {
                setView("new");
                setSelectedPlan(null);
                setRequirements("");
                setPlanText("");
                setGeneratedPlan("");
                setIsEditingSaved(false);
              }}
            >
              + Create New Plan
            </button>
          </div>
          <div className="planner-plans-header">
            <h4>Saved Plans ({plans.length})</h4>
            {/* <div className="planner-plans-count"> */}
              {/* <span className="muted small-text">{plans.length}</span> */}
              <button className="refresh-btn" onClick={refreshSavedPlans}>
                ⟳
              </button>
            {/* </div> */}
          </div>
          <div className="planner-filter-container">
            <input
              placeholder="Filter plans"
              value={filterText}
              onChange={(e) => setFilterText(e.target.value)}
              className="planner-filter-input"
            />
          </div>
          <div className="planner-plans-list-container">
            {hasUnsavedGeneratedPlan && (
              <div className="muted planner-unsaved-notice">
                You are reviewing a newly-generated plan. Existing saved plans
                are temporarily non-interactive until you Save or Clear the new
                plan.
              </div>
            )}
            {savedPlansError && (
              <p className="muted planner-error-text">
                {savedPlansError}
              </p>
            )}
            {!savedPlansError && savedPlansLoading && (
              <p className="muted">Loading saved plans…</p>
            )}
            {!savedPlansError && !savedPlansLoading && plans.length === 0 && (
              <p className="muted">No plans yet</p>
            )}
            <ul className="planner-plans-list">
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
                  const itemClasses = `planner-plan-item ${isSelected ? 'selected' : ''} ${hasUnsavedGeneratedPlan ? 'disabled' : ''}`;
                  return (
                    <li
                      key={p.path || p.filename || p.id || idx}
                      className={itemClasses}
                      onClick={hasUnsavedGeneratedPlan ? undefined : () => {
                        console.info("Selected plan:", p);
                        setSelectedPlan({
                          name: p.name || p.filename || "",
                          owner: p.owner || p.user_id || p.email || "Unknown",
                          created_at: p.created_at || p.created || "",
                          text: p.plan_text || p.text || "N/A Plan",
                          path: p.path || null,
                        });
                        // Open Plan Preview View directly
                        setIsEditingSaved(false);
                        setView("preview");
                        setPlanText("");
                      }}
                    >
                      <div className="planner-plan-item-content">
                        <strong className="planner-plan-name">
                          {p.name || p.id || p.filename || `plan-${idx + 1}`}
                        </strong>
                        <span className="muted small-text planner-plan-date">
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
        <div className="planner-right-sidebar">
          {/* Row 1: controls */}
          <div className="planner-controls-row">
            {(view !== "preview" || isEditingSaved) && (
              <input
                placeholder="Enter instructions to create a plan"
                value={requirements}
                onChange={(e) => {
                  setRequirements(e.target.value);
                }}
                className="planner-requirements-input"
                aria-label="plan-requirements"
              />
            )}
            

            {(view === "dashboard" || view === "new") && (
              <>
                {!hasUnsavedGeneratedPlan ? (
                  <>
                    <button
                      type="button"
                      className="btn"
                      onClick={async () => {
                        try {
                          await createPlan();
                        } catch (e) {
                          console.error(e);
                        }
                      }}
                      disabled={isGenerating || !requirements.trim()}
                    >
                      Create New Plan
                    </button>
                    <button
                      className="btn secondary clear-btn"
                      onClick={() => {
                        // Clear inputs for new plan creation and refresh page
                        setRequirements("");
                        setGeneratedPlan("");
                        setPlanText("");
                        setHasUnsavedGeneratedPlan(false);
                        setMsg("");
                        setView("dashboard");
                        setSelectedPlan(null);
                        setIsEditingSaved(false);
                        // Refresh the page to reset all state
                        window.location.reload();
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
                        if (hasUnsavedChanges) {
                          showConfirmModal(
                            "Unsaved Changes",
                            "You have unsaved changes. Are you sure you want to cancel?",
                            () => {
                              setView("dashboard");
                              setRequirements("");
                              setGeneratedPlan("");
                              setPlanText("");
                              setHasUnsavedGeneratedPlan(false);
                              setMsg("");
                              setIsEditingSaved(false);
                              setHasUnsavedChanges(false);
                              window.location.reload();
                            },
                            "warning",
                            "Yes, Cancel",
                            "Keep Editing"
                          );
                          return;
                        }
                        setView("dashboard");
                        setRequirements("");
                        setGeneratedPlan("");
                        setPlanText("");
                        setHasUnsavedGeneratedPlan(false);
                        setMsg("");
                        setIsEditingSaved(false);
                        setHasUnsavedChanges(false);
                        window.location.reload();
                      }}
                    >
                      Cancel
                    </button>
                  </>
                )}
              </>
            )}

            {view === "preview" && !isEditingSaved && selectedPlan && (
              <>
                <button
                  className="btn"
                  onClick={() => {
                    // Enter edit mode for this saved plan
                    setView("edit");
                    setIsEditingSaved(true);
                    setPlanText(selectedPlan.text || "");
                  }}
                >
                  Edit Plan
                </button>
                <button
                  className="btn secondary clear-btn"
                  onClick={() => {
                    // Delete the selected plan
                    if (selectedPlan && selectedPlan.path) {
                      deletePlan(selectedPlan.path);
                    } else if (selectedPlan && selectedPlan.name) {
                      // fallback by name
                      deletePlan(null);
                    }
                  }}
                >
                  Delete
                </button>
              </>
            )}

            {view === "edit" && isEditingSaved && (
              <>
                <button
                  type="button"
                  className="btn"
                  onClick={async () => {
                    // Regenerate/Update Plan: for saved plans call update endpoint,
                    // for unsaved generated plans call createPlan again with requirements
                    if (selectedPlan && selectedPlan.path) {

                      if (!requirements.trim()) {
                        setMsg("Please enter a New Instruction to regenerate this plan.");
                        return;
                      }
                      setMsg("Regenerating plan…");
                      setIsGenerating(true);
                      try {
                        await regenerateSavedPlan(selectedPlan.path);
                        // After regeneration completes, stay in Edit/Update view
                        setView("edit");
                        setIsEditingSaved(true);
                      } finally {

                        setHasUnsavedGeneratedPlan(true);
                        setIsGenerating(false);
                      }
                    } else {
                      // unsaved plan: regenerate by creating again
                      await createPlan();
                    }
                  }}
                >
                  Regenerate Plan
                </button>
                <button
                  type="button"
                  className="btn"
                  onClick={async () => {
                    await savePlan();
                    setHasUnsavedGeneratedPlan(false);
                    setHasUnsavedChanges(false);
                    setMsg("Changes saved successfully.");
                    setView("preview");
                  }}
                >
                  Save Changes
                </button>
                <button
                  type="button"
                  className="btn"
                  onClick={() => {
                    if (hasUnsavedChanges) {
                      showConfirmModal(
                        "Unsaved Changes",
                        "You have unsaved changes. Are you sure you want to cancel?",
                        () => {
                          setIsEditingSaved(false);
                          if (selectedPlan) {
                            setView("preview");
                          } else {
                            setView("dashboard");
                          }
                          setHasUnsavedChanges(false);
                          window.location.reload();
                        },
                        "warning",
                        "Yes, Cancel",
                        "Keep Editing"
                      );
                      return;
                    }
                    setIsEditingSaved(false);
                    if (selectedPlan) {
                      setView("preview");
                    } else {
                      setView("dashboard");
                    }
                    setHasUnsavedChanges(false);
                    window.location.reload();
                  }}
                >
                  Cancel
                </button>
              </>
            )}
          </div>

          {/* Row 2: editable area for editing saved plan; New view shows requirement + preview; Saved shows formatted view */}
          <div className="planner-content-area">
            {view === "edit" && isEditingSaved && (
              <EditUpdatePlanView
                isGenerating={isGenerating}
                planText={planText}
                setPlanText={setPlanText}
                selectedPlan={selectedPlan}
                renderPlanMarkdown={renderPlanMarkdown}
                LoadingSpinner={LoadingSpinner}
              />
            )}
            {view === "new" && (
              <CreateNewPlanView
                isGenerating={isGenerating}
                hasUnsavedGeneratedPlan={hasUnsavedGeneratedPlan}
                planText={planText}
                setPlanText={setPlanText}
                generatedPlan={generatedPlan}
                renderPlanMarkdown={renderPlanMarkdown}
                LoadingSpinner={LoadingSpinner}
              />
            )}
            {view === "preview" && selectedPlan && (
              <PlanPreviewView
                selectedPlan={selectedPlan}
                renderPlanMarkdown={renderPlanMarkdown}
              />
            )}
            {/* fallback when no view matches */}
            {(!isEditingSaved && view !== "new" && view !== "preview" && !selectedPlan) && (
              <div className="muted planner-empty-state">
                Select a plan from the left or Provide instructions to create a
                new plan...
              </div>
            )}
          </div>

          <div aria-live="polite" className="planner-message-container">
            {msg && (() => {
              const meta = getMessageMeta(msg);
              let messageClass = 'planner-message info';
              let iconClass = 'planner-message-icon info';
              let icon = null;
              if (meta.type === 'error') {
                messageClass = 'planner-message error';
                iconClass = 'planner-message-icon warning';
                icon = (<span className={iconClass}>⚠️</span>);
              } else if (meta.type === 'success') {
                messageClass = 'planner-message success';
                iconClass = 'planner-message-icon success';
                icon = (<span className={iconClass}>✅</span>);
              } else {
                icon = (<span className={iconClass}>ℹ️</span>);
              }
              return (
                <div className={messageClass} role={meta.type === 'error' ? 'alert' : 'status'}>
                  {icon}
                  <div className="planner-message-text">{msg}</div>
                </div>
              );
            })()}
          </div>

          {/* generated preview removed (rendered inline in New view or edit view) */}
        </div>
      </div>

      {/* Custom Confirmation Modal */}
      <ConfirmModal
        isOpen={confirmModal.isOpen}
        onClose={closeConfirmModal}
        onConfirm={confirmModal.onConfirm}
        title={confirmModal.title}
        message={confirmModal.message}
        confirmText={confirmModal.confirmText}
        cancelText={confirmModal.cancelText}
        variant={confirmModal.variant}
      />

      {/* Custom Prompt Modal */}
      <PromptModal
        isOpen={promptModal.isOpen}
        onClose={closePromptModal}
        onConfirm={promptModal.onConfirm}
        title={promptModal.title}
        message={promptModal.message}
        placeholder={promptModal.placeholder}
        defaultValue={promptModal.defaultValue}
        confirmText={promptModal.confirmText}
        cancelText={promptModal.cancelText}
        variant={promptModal.variant}
      />
    </div>
  );
}

export default PlannerPanel;
