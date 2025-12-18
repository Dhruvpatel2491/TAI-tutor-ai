import React from "react";
import PlannerPanel from "../components/PlannerPanel";
import "../styles/PlannerPage.css";

function PlannerPage() {
  return (
    <div className="planner-page">
      <div className="planner-page-container">
        <PlannerPanel />
      </div>
    </div>
  );
}

export default PlannerPage;
