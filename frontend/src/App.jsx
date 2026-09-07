import { useState, useCallback } from "react";
import Sidebar from "./components/Sidebar";
import OverviewView from "./views/OverviewView";
import MeshView from "./views/MeshView";
import InspectorView from "./views/InspectorView";
import ConsensusView from "./views/ConsensusView";
import ChallengesView from "./views/ChallengesView";
import AttacksView from "./views/AttacksView";
import DriftView from "./views/DriftView";
import MetricsView from "./views/MetricsView";
import IncidentsView from "./views/IncidentsView";
import useStreamData from "./hooks/useStreamData";
import "./App.css";

function App() {
  const [activeView, setActiveView] = useState(() => {
    const params = new URLSearchParams(window.location.search);
    return params.get("view") || "overview";
  });

  const {
    nodes,
    selectedNodeId,
    setSelectedNodeId,
    events,
    alarm,
    claims,
    conflicts,
    metrics,
    aiExplanation,
    isExplaining,
    isConnected,
    isReplaying,
    triggerAttack,
    explainIncident,
    setAiExplanation,
  } = useStreamData();

  const handleSelectView = useCallback((viewId) => {
    setActiveView(viewId);
    try {
      const url = new URL(window.location);
      url.searchParams.set("view", viewId);
      window.history.replaceState({}, "", url);
    } catch {
      // Ignore URL state replacement errors in restricted environments
    }
  }, []);

  const renderActiveView = () => {
    switch (activeView) {
      case "overview":
        return (
          <OverviewView
            nodes={nodes}
            events={events}
            alarm={alarm}
            claims={claims}
            onNavigate={handleSelectView}
            onSelectNode={setSelectedNodeId}
          />
        );

      case "mesh":
        return (
          <MeshView
            nodes={nodes}
            selectedNodeId={selectedNodeId}
            onSelectNode={setSelectedNodeId}
            onNavigate={handleSelectView}
          />
        );

      case "inspector":
        return (
          <InspectorView
            nodes={nodes}
            selectedNodeId={selectedNodeId}
            onSelectNode={setSelectedNodeId}
            onNavigate={handleSelectView}
            events={events}
          />
        );

      case "consensus":
        return (
          <ConsensusView
            nodes={nodes}
            claims={claims}
            conflicts={conflicts}
          />
        );

      case "challenges":
        return <ChallengesView events={events} />;

      case "attacks":
        return (
          <AttacksView
            onTriggerAttack={triggerAttack}
            isConnected={isConnected}
            nodes={nodes}
          />
        );

      case "drift":
        return <DriftView />;

      case "metrics":
        return <MetricsView metrics={metrics} />;

      case "incidents":
        return (
          <IncidentsView
            events={events}
            aiExplanation={aiExplanation}
            isExplaining={isExplaining}
            onTriggerExplain={explainIncident}
            onCloseExplanation={() => setAiExplanation(null)}
          />
        );

      default:
        return (
          <OverviewView
            nodes={nodes}
            events={events}
            alarm={alarm}
            claims={claims}
            onNavigate={handleSelectView}
            onSelectNode={setSelectedNodeId}
          />
        );
    }
  };

  return (
    <div className="app app-layout">
      {/* Fixed Vertical Left Sidebar */}
      <Sidebar
        activeView={activeView}
        onSelectView={handleSelectView}
        isConnected={isConnected}
        isReplaying={isReplaying}
        onSwitchPhoneMode={() => handleSelectView("attacks")}
      />

      {/* Main Multi-View Content Stage */}
      <div className="main-content-wrapper">
        <main className="dashboard multi-view-dashboard">
          {renderActiveView()}
        </main>
      </div>
    </div>
  );
}

export default App;