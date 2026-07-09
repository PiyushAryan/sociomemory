import React, { useEffect, useMemo, useState, useRef } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

const INITIAL_CHILD_ID = "Piyush";
const DASHBOARD_TOKEN_KEY = "sociomemory-dashboard-token";

const TYPE_COLORS = {
  Child: "#1e40af",       // Royal Blue
  Neighborhood: "#0f766e",// Teal
  City: "#0369a1",        // Sky
  School: "#4338ca",      // Indigo
  Economic: "#0284c7",    // Sky Accent
  Income: "#075985",      // Dark Sky
  Cultural: "#6d28d9",    // Purple
  Safety: "#be123c",      // Rose Accent (Warning)
  Transport: "#475569",   // Slate
  RealEstate: "#047857",  // Emerald
  Visit: "#2563eb",       // Blue
  Episode: "#3b82f6",     // Light Blue
  Religious: "#5b21b6",   // Deep Purple
  Lifestyle: "#115e59",   // Deep Teal
  Implication: "#0e7490", // Cyan
  Tradeoff: "#b91c1c",    // Red
};

const SENSITIVITY_STROKE = {
  public: "#10b981",
  contextual: "#6366f1",
  personal: "#f59e0b",
  sensitive: "#ef4444",
};

const DEMO_CHILD_ID = "Piyush";

const DEMO_NODES = [
  {
    id: "demo-child",
    child_id: DEMO_CHILD_ID,
    type: "Child",
    properties: { name: "Piyush", child_id: DEMO_CHILD_ID },
    confidence: 1,
    sensitivity: "personal",
    document_date: "2026-07-10",
    event_date: null,
    source_chunk: "Demo profile seeded for public sociomemory exploration.",
    stale: false,
    label: "Piyush",
  },
  {
    id: "demo-school",
    child_id: DEMO_CHILD_ID,
    type: "School",
    properties: { name: "Greenwood High", board: "IB", locality: "Koramangala" },
    confidence: 0.91,
    sensitivity: "contextual",
    document_date: "2026-07-10",
    event_date: null,
    source_chunk: "Piyush studies at Greenwood High in Koramangala.",
    stale: false,
    label: "Greenwood High",
  },
  {
    id: "demo-neighborhood",
    child_id: DEMO_CHILD_ID,
    type: "Neighborhood",
    properties: { name: "Koramangala", city: "Bengaluru", country: "IN" },
    confidence: 0.88,
    sensitivity: "contextual",
    document_date: "2026-07-10",
    event_date: null,
    source_chunk: "The family recently moved near Koramangala 5th Block.",
    stale: false,
    label: "Koramangala",
  },
  {
    id: "demo-city",
    child_id: DEMO_CHILD_ID,
    type: "City",
    properties: { name: "Bengaluru", state: "Karnataka" },
    confidence: 0.96,
    sensitivity: "public",
    document_date: "2026-07-10",
    event_date: null,
    source_chunk: "Koramangala is resolved to Bengaluru, Karnataka.",
    stale: false,
    label: "Bengaluru",
  },
  {
    id: "demo-economic",
    child_id: DEMO_CHILD_ID,
    type: "Economic",
    properties: { segment: "urban professional", evidence: "school + neighborhood + transport" },
    confidence: 0.68,
    sensitivity: "sensitive",
    document_date: "2026-07-10",
    event_date: null,
    source_chunk: "Context suggests urban professional household signals.",
    stale: false,
    label: "Urban professional",
  },
  {
    id: "demo-visit",
    child_id: DEMO_CHILD_ID,
    type: "Visit",
    properties: { name: "Shiva Temple visit", place: "Shiva Temple", frequency: "occasional" },
    confidence: 0.79,
    sensitivity: "personal",
    document_date: "2026-07-10",
    event_date: "2026-07-08",
    source_chunk: "Yesterday evening, Piyush visited a Shiva Temple with family.",
    stale: false,
    label: "Shiva Temple visit",
  },
  {
    id: "demo-transport",
    child_id: DEMO_CHILD_ID,
    type: "Transport",
    properties: { mode: "school bus", commute_pattern: "weekday mornings" },
    confidence: 0.74,
    sensitivity: "contextual",
    document_date: "2026-07-10",
    event_date: null,
    source_chunk: "Piyush usually takes the school bus on weekday mornings.",
    stale: false,
    label: "School bus",
  },
  {
    id: "demo-safety",
    child_id: DEMO_CHILD_ID,
    type: "Safety",
    properties: { concern: "dark alley near park entrance", severity: "moderate" },
    confidence: 0.62,
    sensitivity: "sensitive",
    document_date: "2026-07-10",
    event_date: null,
    source_chunk: "Piyush mentioned feeling anxious near a dark alley by the park.",
    stale: false,
    label: "Park entrance concern",
  },
  {
    id: "demo-implication",
    child_id: DEMO_CHILD_ID,
    type: "Implication",
    properties: {
      insight: "Coaching tone should reference school routine and avoid over-indexing on temple visits.",
    },
    confidence: 0.7,
    sensitivity: "contextual",
    document_date: "2026-07-10",
    event_date: null,
    source_chunk: "Aggregated from school, neighborhood, visit, and safety signals.",
    stale: false,
    label: "Coaching context",
  },
];

const DEMO_EDGES = [
  { id: "edge-1", source: "demo-child", target: "demo-school", type: "STUDIES_AT", weight: 0.91, properties: {} },
  {
    id: "edge-2",
    source: "demo-child",
    target: "demo-neighborhood",
    type: "LIVES_NEAR",
    weight: 0.88,
    properties: {},
  },
  {
    id: "edge-3",
    source: "demo-neighborhood",
    target: "demo-city",
    type: "LOCATED_IN",
    weight: 0.96,
    properties: {},
  },
  {
    id: "edge-4",
    source: "demo-neighborhood",
    target: "demo-economic",
    type: "SIGNALS",
    weight: 0.68,
    properties: {},
  },
  { id: "edge-5", source: "demo-child", target: "demo-visit", type: "VISITED", weight: 0.79, properties: {} },
  {
    id: "edge-6",
    source: "demo-child",
    target: "demo-transport",
    type: "COMMUTES_BY",
    weight: 0.74,
    properties: {},
  },
  {
    id: "edge-7",
    source: "demo-child",
    target: "demo-safety",
    type: "FEELS_UNSAFE_NEAR",
    weight: 0.62,
    properties: {},
  },
  {
    id: "edge-8",
    source: "demo-economic",
    target: "demo-implication",
    type: "INFORMS",
    weight: 0.7,
    properties: {},
  },
  {
    id: "edge-9",
    source: "demo-safety",
    target: "demo-implication",
    type: "INFORMS",
    weight: 0.66,
    properties: {},
  },
];

// Custom Inline SVGs
const Icon = {
  Refresh: () => (
    <svg viewBox="0 0 24 24" width="13" height="13" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round" className="mr-1.5">
      <path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"/>
    </svg>
  ),
  Save: () => (
    <svg viewBox="0 0 24 24" width="13" height="13" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round" className="mr-1.5">
      <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/>
      <polyline points="17 21 17 13 7 13 7 21"/>
      <polyline points="7 3 7 8 15 8"/>
    </svg>
  ),
  Search: () => (
    <svg viewBox="0 0 24 24" width="14" height="14" stroke="currentColor" strokeWidth="2.5" fill="none" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="11" cy="11" r="8"/>
      <line x1="21" y1="21" x2="16.65" y2="16.65"/>
    </svg>
  ),
  ZoomIn: () => (
    <svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round">
      <line x1="12" y1="5" x2="12" y2="19"/>
      <line x1="5" y1="12" x2="19" y2="12"/>
    </svg>
  ),
  ZoomOut: () => (
    <svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round">
      <line x1="5" y1="12" x2="19" y2="12"/>
    </svg>
  ),
  Fit: () => (
    <svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round">
      <path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3"/>
    </svg>
  ),
  Reset: () => (
    <svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round">
      <path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7"/>
    </svg>
  ),
  Ingest: () => (
    <svg viewBox="0 0 24 24" width="13" height="13" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round" className="mr-1.5">
      <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
    </svg>
  ),
  Brain: () => (
    <svg viewBox="0 0 24 24" width="22" height="22" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round" className="inline-block mr-2 align-middle text-primary">
      <path d="M9.5 2A2.5 2.5 0 0 1 12 4.5v15a2.5 2.5 0 0 1-4.96-.44 2.5 2.5 0 0 1 0-3.12 3 3 0 0 1 0-4.88 2.5 2.5 0 0 1 0-3.12A2.5 2.5 0 0 1 9.5 2z"/>
      <path d="M14.5 2A2.5 2.5 0 0 0 12 4.5v15a2.5 2.5 0 0 0 4.96-.44 2.5 2.5 0 0 0 0-3.12 3 3 0 0 0 0-4.88 2.5 2.5 0 0 0 0-3.12A2.5 2.5 0 0 0 14.5 2z"/>
    </svg>
  ),
  Location: () => (
    <svg viewBox="0 0 24 24" width="12" height="12" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round" className="mr-1.5">
      <path d="M12 2a8 8 0 0 0-8 8c0 5.25 8 12 8 12s8-6.75 8-12a8 8 0 0 0-8-8z"/>
      <circle cx="12" cy="10" r="3"/>
    </svg>
  ),
  Segment: () => (
    <svg viewBox="0 0 24 24" width="12" height="12" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round" className="mr-1.5">
      <path d="M4 21v-7a5 5 0 0 1 5-5h12"/>
      <polyline points="17 5 21 9 17 13"/>
    </svg>
  ),
  Profile: () => (
    <svg viewBox="0 0 24 24" width="12" height="12" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round" className="mr-1.5">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
      <polyline points="14 2 14 8 20 8"/>
      <line x1="16" y1="13" x2="8" y2="13"/>
      <line x1="16" y1="17" x2="8" y2="17"/>
    </svg>
  ),
  Context: () => (
    <svg viewBox="0 0 24 24" width="12" height="12" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round" className="mr-1.5">
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
    </svg>
  ),
  Privacy: () => (
    <svg viewBox="0 0 24 24" width="12" height="12" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round" className="mr-1.5">
      <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
      <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
    </svg>
  ),
  Clear: () => (
    <svg viewBox="0 0 24 24" width="12" height="12" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round" className="mr-1.5">
      <polyline points="3 6 5 6 21 6"/>
      <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
    </svg>
  )
};

function ThemeSwitcher({ theme, setTheme }) {
  const themes = [
    { id: "greenish-white", label: "light" },
    { id: "greenish-black", label: "dark" }
  ];

  return (
    <div className="flex items-center border border-line bg-panel p-0.5 font-mono text-[9px] uppercase tracking-wider rounded-none">
      {themes.map((t) => (
        <button
          key={t.id}
          type="button"
          onClick={() => setTheme(t.id)}
          className={`px-3 py-1 cursor-pointer transition-all duration-200 border-none font-bold rounded-none ${
            theme === t.id
              ? "bg-ink text-bg font-extrabold"
              : "text-muted hover:text-ink hover:bg-line/40"
          }`}
        >
          {t.label}
        </button>
      ))}
    </div>
  );
}

function DashboardTokenControl({ token, setToken }) {
  const hasToken = Boolean(token.trim());

  function updateToken(value) {
    setToken(value);
    if (value.trim()) {
      sessionStorage.setItem(DASHBOARD_TOKEN_KEY, value);
    } else {
      sessionStorage.removeItem(DASHBOARD_TOKEN_KEY);
    }
  }

  return (
    <label className="flex items-center gap-2 min-w-0">
      <span className="label whitespace-nowrap">Private API</span>
      <input
        type="password"
        value={token}
        onChange={(event) => updateToken(event.target.value)}
        autoComplete="off"
        placeholder="optional token"
        className="field w-36 sm:w-44 font-mono"
      />
      <span className={`token-state ${hasToken ? "is-set" : ""}`}>
        {hasToken ? "private" : "demo"}
      </span>
    </label>
  );
}

function App() {
  const [childId, setChildId] = useState(INITIAL_CHILD_ID);
  const [draftChildId, setDraftChildId] = useState(INITIAL_CHILD_ID);
  const [dashboardToken, setDashboardToken] = useState(
    () => sessionStorage.getItem(DASHBOARD_TOKEN_KEY) || "",
  );
  const [graph, setGraph] = useState({ nodes: [], edges: [] });
  const [summary, setSummary] = useState(null);
  const [selectedNodeId, setSelectedNodeId] = useState(null);
  const [detail, setDetail] = useState(null);
  const [output, setOutput] = useState("");
  const [status, setStatus] = useState("Idle");
  const [ingestText, setIngestText] = useState("");
  const [person, setPerson] = useState({
    id: "",
    name: "",
    area: "",
    school: "",
    places: "",
    notes: "",
  });
  const [filters, setFilters] = useState({
    type: "",
    sensitivity: "",
    minConfidence: 0,
    staleOnly: false,
  });

  const [theme, setTheme] = useState(() => {
    const saved = localStorage.getItem("sociomemory-theme");
    return saved === "greenish-white" || saved === "greenish-black" ? saved : "greenish-white";
  });
  const [view, setView] = useState("overview");

  useEffect(() => {
    const root = document.documentElement;
    const themeClasses = [
      "theme-greenish-white",
      "theme-greenish-black",
      "theme-light",
      "theme-warm",
      "theme-dark",
      "theme-nightly"
    ];
    root.dataset.theme = theme;
    document.body.classList.remove(...themeClasses);
    document.body.classList.add(`theme-${theme}`);
    localStorage.setItem("sociomemory-theme", theme);
  }, [theme]);

  const nodeTypes = useMemo(
    () => Array.from(new Set(graph.nodes.map((node) => node.type))).sort(),
    [graph.nodes],
  );

  const visibleNodes = useMemo(
    () =>
      graph.nodes.filter((node) => {
        if (filters.type && node.type !== filters.type) return false;
        if (filters.sensitivity && node.sensitivity !== filters.sensitivity) return false;
        if (Number(node.confidence || 0) < filters.minConfidence) return false;
        if (filters.staleOnly && !node.stale) return false;
        return true;
      }),
    [filters, graph.nodes],
  );

  const visibleNodeIds = useMemo(() => new Set(visibleNodes.map((node) => node.id)), [visibleNodes]);
  const visibleEdges = useMemo(
    () => graph.edges.filter((edge) => visibleNodeIds.has(edge.source) && visibleNodeIds.has(edge.target)),
    [graph.edges, visibleNodeIds],
  );

  useEffect(() => {
    loadGraph(childId);
  }, [childId]);

  async function loadGraph(nextChildId = childId) {
    setStatus("Loading graph...");
    try {
      const child = encodeURIComponent(nextChildId);
      const [summaryPayload, graphPayload] = await Promise.all([
        fetchJson(`/api/children/${child}/summary`),
        fetchJson(`/api/children/${child}/graph`),
      ]);
      setSummary(summaryPayload.summary);
      setGraph(graphPayload);
      setSelectedNodeId(null);
      setDetail(null);
      setStatus(`${graphPayload.nodes.length} nodes, ${graphPayload.edges.length} edges`);
    } catch (error) {
      setStatus("Load failed");
      setOutput(errorToText(error));
    }
  }

  async function ingest() {
    const text = ingestText.trim();
    if (!text) {
      setOutput("Paste a conversation turn before ingesting.");
      return;
    }
    setStatus("Ingesting...");
    try {
      const result = await fetchJson(`/api/children/${encodeURIComponent(childId)}/ingest`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text, source: "conversation" }),
      });
      setOutput(JSON.stringify(result, null, 2));
      await loadGraph(childId);
      setIngestText("");
    } catch (error) {
      setStatus("Ingest failed");
      setOutput(errorToText(error));
    }
  }

  async function savePerson() {
    const personId = person.id.trim() || childId;
    if (!personId) {
      setOutput("Enter a Person ID before saving.");
      return;
    }
    setStatus("Saving person...");
    try {
      const result = await fetchJson(`/api/children/${encodeURIComponent(personId)}/person`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: person.name,
          area: person.area,
          school: person.school,
          places: person.places,
          notes: person.notes,
        }),
      });
      setOutput(JSON.stringify(result, null, 2));
      setDraftChildId(personId);
      setChildId(personId);
      setPerson({
        id: "",
        name: "",
        area: "",
        school: "",
        places: "",
        notes: "",
      });
      await loadGraph(personId);
    } catch (error) {
      setStatus("Save failed");
      setOutput(errorToText(error));
    }
  }

  async function segmentEpisodes() {
    setStatus("Segmenting episodes...");
    try {
      const result = await fetchJson(`/api/children/${encodeURIComponent(childId)}/episodes/segment`, {
        method: "POST",
      });
      setOutput(JSON.stringify(result, null, 2));
      await loadGraph(childId);
    } catch (error) {
      setStatus("Episode segmentation failed");
      setOutput(errorToText(error));
    }
  }

  async function acquireLocation() {
    if (!("geolocation" in navigator)) {
      setOutput("Browser geolocation is not available.");
      return;
    }
    setStatus("Acquiring location...");
    navigator.geolocation.getCurrentPosition(
      async (position) => {
        try {
          const { latitude, longitude, accuracy } = position.coords;
          setStatus("Enriching location...");
          const result = await fetchJson(`/api/children/${encodeURIComponent(childId)}/location/acquire`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ lat: latitude, lng: longitude, accuracy_m: accuracy }),
          });
          setOutput(JSON.stringify(result, null, 2));
          await loadGraph(childId);
        } catch (error) {
          setStatus("Location enrichment failed");
          setOutput(errorToText(error));
        }
      },
      (error) => {
        setStatus("Location acquisition failed");
        setOutput(error.message || "Location permission was not granted.");
      },
      { enableHighAccuracy: false, maximumAge: 300000, timeout: 15000 },
    );
  }

  async function loadOutput(path) {
    setStatus("Loading output...");
    try {
      const result = await fetchJson(path);
      setOutput(JSON.stringify(result, null, 2));
      setStatus("Output loaded");
    } catch (error) {
      setStatus("Output failed");
      setOutput(errorToText(error));
    }
  }

  async function selectNode(nodeId) {
    setSelectedNodeId(nodeId);
    setStatus("Loading node detail...");
    try {
      const payload = await fetchJson(
        `/api/children/${encodeURIComponent(childId)}/nodes/${encodeURIComponent(nodeId)}`,
      );
      setDetail(payload);
      setStatus("Node selected");
    } catch (error) {
      setStatus("Node detail failed");
      setOutput(errorToText(error));
    }
  }

  function clearFilters() {
    setFilters({ type: "", sensitivity: "", minConfidence: 0, staleOnly: false });
  }

  return (
    <div className="min-h-screen flex flex-col bg-bg text-ink">
      {view === "overview" ? (
        <Overview
          summary={summary}
          nodes={graph.nodes}
          childId={childId}
          theme={theme}
          setTheme={setTheme}
          dashboardToken={dashboardToken}
          setDashboardToken={setDashboardToken}
          onOpenGraph={() => setView("graph")}
          onInspect={(id) => { setView("graph"); selectNode(id); }}
          onRefresh={() => loadGraph(childId)}
        />
      ) : (
      <>
      <header className="topbar z-50">
        <div className="flex items-center gap-4">
          <button type="button" className="arrow-link" onClick={() => setView("overview")} title="Back to overview"><span aria-hidden="true">&larr;</span> Overview</button>
          <div className="hidden sm:block w-px h-8 bg-line" />
          <div>
            <h1 className="text-lg font-bold flex items-center tracking-tight"><Icon.Brain />sociomemory</h1>
            <p className="eyebrow mt-0.5">Graph memory explorer for AI agents</p>
          </div>
        </div>

        <div className="flex items-center gap-5">
          <DashboardTokenControl token={dashboardToken} setToken={setDashboardToken} />

          {/* Theme Switcher Selector */}
          <div className="flex items-center gap-1.5">
            <span className="label">Theme</span>
            <ThemeSwitcher theme={theme} setTheme={setTheme} />
          </div>

          <form
            className="flex items-center gap-2"
            onSubmit={(event) => {
              event.preventDefault();
              setChildId(draftChildId.trim() || INITIAL_CHILD_ID);
            }}
          >
            <label htmlFor="child-id" className="label">Agent / Child ID</label>
            <input
              id="child-id"
              value={draftChildId}
              onChange={(event) => setDraftChildId(event.target.value)}
              autoComplete="off"
              className="field w-44 font-medium"
            />
            <button type="submit" className="btn btn-primary">Load Profile <span aria-hidden="true">&rarr;</span></button>
          </form>
        </div>
      </header>

      <main className="flex-1 grid grid-cols-1 xl:grid-cols-[300px_1fr_350px] gap-4 p-4 bg-bg">
        <aside className="flex flex-col gap-4 min-h-0">
          <section className="card">
            <div className="card-head">
              <h2 className="card-title"><span className="sec-index">01</span>Summary</h2>
              <button type="button" onClick={() => loadGraph(childId)} className="btn btn-ghost btn-sm"><Icon.Refresh />Refresh</button>
            </div>
            <dl className="grid grid-cols-2 gap-2 list-none p-0 m-0">
              <Metric label="Nodes" value={summary?.nodes} />
              <Metric label="Edges" value={summary?.edges} />
              <Metric label="Stale" value={summary?.stale_nodes} />
              <Metric label="Faiss Vectors" value={summary?.faiss_vectors} />
            </dl>
          </section>

          <section className="card">
            <div className="card-head">
              <h2 className="card-title"><span className="sec-index">02</span>Add Person / Child</h2>
              <button type="button" onClick={savePerson} className="btn btn-primary btn-sm"><Icon.Save />Save</button>
            </div>
            <label className="grid gap-1 mb-3">
              <span className="label">Person ID</span>
              <input
                value={person.id}
                placeholder="e.g. piyush_01 (blank = current)"
                autoComplete="off"
                onChange={(event) => setPerson({ ...person, id: event.target.value })}
                className="field"
              />
            </label>
            <label className="grid gap-1 mb-3">
              <span className="label">Name</span>
              <input
                value={person.name}
                placeholder="Full name"
                onChange={(event) => setPerson({ ...person, name: event.target.value })}
                className="field"
              />
            </label>
            <label className="grid gap-1 mb-3">
              <span className="label">Area / Neighborhood</span>
              <input
                value={person.area}
                placeholder="e.g. Koramangala, Bangalore"
                onChange={(event) => setPerson({ ...person, area: event.target.value })}
                className="field"
              />
            </label>
            <label className="grid gap-1 mb-3">
              <span className="label">School</span>
              <input
                value={person.school}
                placeholder="e.g. Greenwood High"
                onChange={(event) => setPerson({ ...person, school: event.target.value })}
                className="field"
              />
            </label>
            <label className="grid gap-1 mb-3">
              <span className="label">Places Visited</span>
              <input
                value={person.places}
                placeholder="comma-separated: temple, park, mall"
                onChange={(event) => setPerson({ ...person, places: event.target.value })}
                className="field"
              />
            </label>
            <label className="grid gap-1 mb-3">
              <span className="label">Notes</span>
              <textarea
                rows="3"
                value={person.notes}
                placeholder="Father's occupation, spoken languages, special traits..."
                onChange={(event) => setPerson({ ...person, notes: event.target.value })}
                className="field"
              />
            </label>
          </section>

          <section className="card">
            <div className="card-head">
              <h2 className="card-title"><span className="sec-index">03</span>Filters</h2>
              <button type="button" onClick={clearFilters} className="btn btn-ghost btn-sm"><Icon.Clear />Clear</button>
            </div>
            <label className="grid gap-1 mb-3">
              <span className="label">Node Type</span>
              <select value={filters.type} onChange={(event) => setFilters({ ...filters, type: event.target.value })} className="field">
                <option value="">All types</option>
                {nodeTypes.map((type) => <option key={type} value={type}>{type}</option>)}
              </select>
            </label>
            <label className="grid gap-1 mb-3">
              <span className="label">Sensitivity</span>
              <select
                value={filters.sensitivity}
                onChange={(event) => setFilters({ ...filters, sensitivity: event.target.value })}
                className="field"
              >
                <option value="">All levels</option>
                <option value="public">Public</option>
                <option value="contextual">Contextual</option>
                <option value="personal">Personal</option>
                <option value="sensitive">Sensitive</option>
              </select>
            </label>
            <label className="grid gap-1 mb-3">
              <span className="label">Minimum Confidence <b>{filters.minConfidence.toFixed(2)}</b></span>
              <input
                type="range"
                min="0"
                max="1"
                step="0.05"
                value={filters.minConfidence}
                onChange={(event) => setFilters({ ...filters, minConfidence: Number(event.target.value) })}
                className="w-full h-1 bg-line rounded-none outline-none my-2 accent-ink cursor-pointer"
              />
            </label>
            <label className="flex gap-2 items-center text-ink text-xs font-medium cursor-pointer select-none mt-0.5">
              <input
                type="checkbox"
                checked={filters.staleOnly}
                onChange={(event) => setFilters({ ...filters, staleOnly: event.target.checked })}
                className="w-3.5 h-3.5 border border-line rounded-none bg-bg checked:bg-ink checked:border-ink cursor-pointer transition-all"
              />
              <span>Only stale nodes</span>
            </label>
          </section>

          <section className="card">
            <div className="card-head">
              <h2 className="card-title"><span className="sec-index">04</span>Ingest memory</h2>
              <button type="button" onClick={ingest} className="btn btn-primary btn-sm"><Icon.Ingest />Run Ingest</button>
            </div>
            <textarea
              rows="4"
              value={ingestText}
              placeholder="Paste a conversation turn, user statement, or agent prompt..."
              onChange={(event) => setIngestText(event.target.value)}
              className="field"
            />
          </section>
        </aside>

        <section className="card flush flex-1 min-h-0 overflow-hidden relative">
          <div className="min-h-[52px] border-b border-line flex items-center justify-between p-2 px-4 gap-3 bg-panel z-10">
            <div>
              <strong className="block text-xs font-bold text-ink uppercase tracking-wider">Graph Explorer</strong>
              <span className="text-muted text-[11px] font-mono mt-0.5 block">{status}</span>
            </div>
            <div className="flex flex-wrap gap-1.5">
              <button type="button" onClick={() => loadOutput(`/api/children/${encodeURIComponent(childId)}/profile`)} className="btn btn-ghost btn-sm">
                <Icon.Profile />Profile JSON
              </button>
              <button type="button" onClick={() => loadOutput(`/api/children/${encodeURIComponent(childId)}/context`)} className="btn btn-ghost btn-sm">
                <Icon.Context />Context JSON
              </button>
              <button type="button" onClick={acquireLocation} className="btn btn-ghost btn-sm">
                <Icon.Location />Acquire location
              </button>
              <button type="button" onClick={segmentEpisodes} className="btn btn-ghost btn-sm">
                <Icon.Segment />Segment episodes
              </button>
              <button type="button" onClick={() => loadOutput(`/api/children/${encodeURIComponent(childId)}/privacy/export`)} className="btn btn-ghost btn-sm">
                <Icon.Privacy />Privacy Export
              </button>
            </div>
          </div>
          
          <GraphCanvas
            nodes={visibleNodes}
            edges={visibleEdges}
            selectedNodeId={selectedNodeId}
            onSelectNode={selectNode}
          />
        </section>

        <aside className="flex flex-col gap-4 min-h-0">
          <section className="card flex-1 min-h-[360px] overflow-y-auto">
            <div className="card-head">
              <h2 className="card-title"><span className="sec-index">05</span>Inspector</h2>
              {selectedNodeId && <button type="button" onClick={() => setSelectedNodeId(null)} className="btn btn-ghost btn-sm"><Icon.Clear />Close</button>}
            </div>
            <NodeInspector detail={detail} />
          </section>
          
          <section className="card max-h-[240px] overflow-y-auto">
            <div className="card-head">
              <h2 className="card-title"><span className="sec-index">06</span>Output terminal</h2>
              {output && <button type="button" onClick={() => setOutput("")} className="btn btn-ghost btn-sm"><Icon.Clear />Clear</button>}
            </div>
            <pre className="m-0 text-accent bg-bg rounded-none p-2.5 border border-line flex-1 overflow-y-auto font-mono text-[11px]">{output || "Awaiting operation logs..."}</pre>
          </section>
        </aside>
      </main>
      </>
      )}
    </div>
  );
}

function Metric({ label, value }) {
  return (
    <div className="metric">
      <dt className="metric-label">{label}</dt>
      <dd className="metric-value">{value ?? "-"}</dd>
    </div>
  );
}

/* ---------------------------------------------------------------------------
   Overview — a landing page in the x-arc.ai theme: sticky text nav, centered
   hero with a floating isometric layer stack, live stat strip, a capabilities
   grid, and a mono-dated "field notes" feed sourced from real memory nodes.
--------------------------------------------------------------------------- */

const ARROW = <span className="arw" aria-hidden="true">&rarr;</span>;

const CAPABILITIES = [
  { n: "01", title: "Extraction", body: "Pull entities and relations from every conversation turn into typed memory nodes." },
  { n: "02", title: "Enrichment", body: "Resolve places, schools, and neighborhoods with geocoding and web signals." },
  { n: "03", title: "Implication", body: "Infer lifestyle, economics, and culture from sparse, indirect cues." },
  { n: "04", title: "Episodes", body: "Segment a stream of turns into coherent, time-bound memory episodes." },
  { n: "05", title: "Privacy", body: "Sensitivity tiers, consent gating, and anonymized profile exports." },
  { n: "06", title: "Temporal", body: "Version beliefs over time and let stale knowledge decay with confidence." },
];

// "2026-05-27" / ISO timestamp -> "2026 · 05 · 27" (x-arc field-note format)
function formatNoteDate(value) {
  if (!value) return "—— · —— · ——";
  const match = String(value).match(/(\d{4})-(\d{2})-(\d{2})/);
  if (!match) return String(value);
  return `${match[1]} · ${match[2]} · ${match[3]}`;
}

function InteractiveStack({ activeLayer, setActiveLayer }) {
  const W = 138, H = 64, T = 6;
  const slabs = [
    { id: 0, cy: 96, label: "sociomemory", sub: "memory · inference · privacy", accent: true },
    { id: 1, cy: 192, label: "agent harness", sub: "conversations · coaching", accent: false },
    { id: 2, cy: 288, label: "signals", sub: "location · places · time", accent: false },
  ];
  const cx = 175;
  const topFace = (cy) => `${cx},${cy - H / 2} ${cx + W},${cy} ${cx},${cy + H / 2} ${cx - W},${cy}`;
  const leftFace = (cy) => `${cx - W},${cy} ${cx},${cy + H / 2} ${cx},${cy + H / 2 + T} ${cx - W},${cy + T}`;
  const rightFace = (cy) => `${cx},${cy + H / 2} ${cx + W},${cy} ${cx + W},${cy + T} ${cx},${cy + H / 2 + T}`;

  return (
    <svg viewBox="0 0 350 400" className="w-full h-full max-w-[420px] select-none" role="img" aria-label="Interactive isometric stack layer explorer">
      <line x1={cx} y1={310} x2={cx} y2={80} stroke="var(--line-active)" strokeWidth="1.2" className="playground-line opacity-50" />
      {slabs.map((s) => {
        const isHovered = activeLayer === s.id;
        
        const faceFill = isHovered 
          ? "color-mix(in srgb, var(--panel) 75%, var(--line-active))"
          : "var(--panel)";
          
        const sideFill = isHovered
          ? "color-mix(in srgb, var(--panel-solid) 80%, var(--line-active))"
          : "color-mix(in srgb, var(--panel-solid) 92%, black)";
          
        const sideFill2 = isHovered
          ? "color-mix(in srgb, var(--panel-solid) 85%, var(--line-active))"
          : "color-mix(in srgb, var(--panel-solid) 94%, black)";
          
        const stroke = isHovered 
          ? "var(--line-active)" 
          : (s.accent ? "color-mix(in srgb, var(--line-active) 35%, var(--line))" : "var(--line)");
          
        const textFill = isHovered ? "var(--line-active)" : "var(--ink)";
        const subFill = "var(--muted)";
        
        return (
          <g key={s.id} className={`animate-stack-entrance-${s.id}`}>
            <g className={`animate-stack-${s.id}`}>
              <g 
                className="stack-layer cursor-pointer"
                onMouseEnter={() => setActiveLayer(s.id)}
                style={{ transition: "all 0.3s ease" }}
              >
                <polygon points={leftFace(s.cy)} fill={sideFill} stroke={stroke} strokeWidth={isHovered ? 1.2 : 0.8} strokeLinejoin="round" />
                <polygon points={rightFace(s.cy)} fill={sideFill2} stroke={stroke} strokeWidth={isHovered ? 1.2 : 0.8} strokeLinejoin="round" />
                <polygon points={topFace(s.cy)} fill={faceFill} stroke={stroke} strokeWidth={isHovered ? 1.2 : 0.8} strokeLinejoin="round" />
                <text 
                  x={cx} 
                  y={s.cy - 3} 
                  textAnchor="middle" 
                  fontSize="11" 
                  fontWeight="600" 
                  fill={textFill} 
                  style={{ fontFamily: "var(--font-mono)", letterSpacing: "0.06em", textTransform: "lowercase", transition: "fill 0.2s ease" }}
                >
                  {s.label}
                </text>
                <text 
                  x={cx} 
                  y={s.cy + 10} 
                  textAnchor="middle" 
                  fontSize="8" 
                  fill={subFill} 
                  style={{ fontFamily: "var(--font-mono)", letterSpacing: "0.02em", opacity: isHovered ? 0.9 : 0.65, transition: "opacity 0.2s ease" }}
                >
                  {s.sub}
                </text>
              </g>
            </g>
          </g>
        );
      })}
    </svg>
  );
}

function IngestPlayground({ childId, onInjected }) {
  const [inputText, setInputText] = useState("Piyush studies at Greenwood High. Yesterday they visited Shiva Temple in Koramangala.");
  const [status, setStatus] = useState("idle"); // idle, simulating, success, injecting, inject_success, inject_failed
  const [logs, setLogs] = useState([]);
  const [simulatedNodes, setSimulatedNodes] = useState([]);
  const [simulatedEdges, setSimulatedEdges] = useState([]);
  const [realOutput, setRealOutput] = useState("");

  const presets = [
    {
      label: "School & Parents",
      text: "Piyush studies at Greenwood High school in Koramangala. His father works as a software engineer at a startup."
    },
    {
      label: "Temple Visit",
      text: "We visited the Shiva Temple yesterday evening, then had dinner at a nearby South Indian café."
    },
    {
      label: "Safety Anxiety",
      text: "Piyush mentioned he feels anxious walking through the dark alley near the park entrance."
    }
  ];

  const simulatePipeline = () => {
    setStatus("simulating");
    setLogs([]);
    setSimulatedNodes([]);
    setSimulatedEdges([]);

    const steps = [
      { text: "⚡ Ingesting raw natural language stream...", delay: 200 },
      { text: "⚙️ Extracting entity tags and semantic triples...", delay: 800 },
      { text: "🔍 Resolving spatial geocoding for Shiva Temple/Greenwood High...", delay: 1400 },
      { text: "🔒 Checking privacy constraints & sensitivity classifications...", delay: 2000 },
      { text: "✨ Successfully mapped into graph schema!", delay: 2600 }
    ];

    steps.forEach((step) => {
      setTimeout(() => {
        setLogs((prev) => [...prev, step.text]);
        if (step.text.includes("Successfully")) {
          let nodes = [
            { id: "1", label: "Piyush", type: "Child", sensitivity: "personal", x: 60, y: 80 },
            { id: "2", label: "Greenwood High", type: "School", sensitivity: "public", x: 190, y: 40 },
            { id: "3", label: "Koramangala", type: "Neighborhood", sensitivity: "public", x: 190, y: 120 }
          ];
          let edges = [
            { source: "1", target: "2", label: "studies_at" },
            { source: "1", target: "3", label: "lives_in" }
          ];

          if (inputText.toLowerCase().includes("temple") || inputText.toLowerCase().includes("café")) {
            nodes = [
              { id: "1", label: "Piyush", type: "Child", sensitivity: "personal", x: 60, y: 80 },
              { id: "4", label: "Shiva Temple", type: "Place", sensitivity: "public", x: 190, y: 45 },
              { id: "5", label: "South Indian Café", type: "Place", sensitivity: "public", x: 190, y: 115 }
            ];
            edges = [
              { source: "1", target: "4", label: "visited" },
              { source: "1", target: "5", label: "dined_at" }
            ];
          } else if (inputText.toLowerCase().includes("alley") || inputText.toLowerCase().includes("anxious")) {
            nodes = [
              { id: "1", label: "Piyush", type: "Child", sensitivity: "personal", x: 60, y: 80 },
              { id: "6", label: "Dark Alley", type: "Tradeoff", sensitivity: "sensitive", x: 190, y: 40 },
              { id: "7", label: "Park Entrance", type: "Place", sensitivity: "public", x: 190, y: 120 }
            ];
            edges = [
              { source: "1", target: "6", label: "feels_anxious" },
              { source: "6", target: "7", label: "located_near" }
            ];
          }

          setSimulatedNodes(nodes);
          setSimulatedEdges(edges);
          setStatus("success");
        }
      }, step.delay);
    });
  };

  const handleRealIngest = async () => {
    setStatus("injecting");
    setRealOutput("");
    try {
      const result = await fetchJson(`/api/children/${encodeURIComponent(childId)}/ingest`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: inputText, source: "conversation" }),
      });
      setRealOutput(JSON.stringify(result, null, 2));
      setStatus("inject_success");
      if (onInjected) onInjected();
    } catch (error) {
      setRealOutput(error.message || "Ingest failed");
      setStatus("inject_failed");
    }
  };

  return (
    <section className="glass-panel p-6 border border-line my-12 relative overflow-hidden">
      <div className="absolute top-0 right-0 w-80 h-80 bg-[radial-gradient(circle_at_center,rgba(16,185,129,0.04),transparent_60%)] pointer-events-none" />
      <div className="grid lg:grid-cols-[1fr_1.1fr] gap-8">
        {/* Input Panel */}
        <div className="flex flex-col gap-5">
          <div>
            <div className="flex items-center gap-2">
              <span className="sec-num font-mono">02</span>
              <h3 className="text-lg font-bold text-ink m-0 tracking-tight">Interactive Pipeline Playground</h3>
            </div>
            <p className="text-xs text-muted leading-relaxed mt-1 mb-0">
              Type custom agent statements or click a preset below to simulate how natural conversation is resolved into structured social context nodes.
            </p>
          </div>

          <div className="flex flex-wrap gap-2">
            {presets.map((p, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => {
                  setInputText(p.text);
                  setStatus("idle");
                  setLogs([]);
                  setSimulatedNodes([]);
                }}
                className="btn btn-ghost btn-sm font-mono text-[10px] tracking-tight hover:border-line-active"
              >
                Preset: {p.label}
              </button>
            ))}
          </div>

          <div className="relative">
            <textarea
              rows="4"
              value={inputText}
              onChange={(e) => {
                setInputText(e.target.value);
                if (status !== "idle") setStatus("idle");
              }}
              className="field h-32 py-2.5 font-mono text-xs leading-relaxed border border-line"
              placeholder="Enter text to analyze..."
            />
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <button
              type="button"
              onClick={simulatePipeline}
              disabled={status === "simulating" || status === "injecting"}
              className="btn btn-primary"
            >
              {status === "simulating" ? "Simulating..." : "Simulate Pipeline Extraction"}
            </button>
            
            {status === "success" && (
              <button
                type="button"
                onClick={handleRealIngest}
                className="btn btn-ghost border-line-active text-line-active hover:bg-line"
              >
                Inject into Active Graph
              </button>
            )}
          </div>
        </div>

        {/* Visualizer Terminal */}
        <div className="bg-bg border border-line rounded-none overflow-hidden flex flex-col min-h-[300px] font-mono">
          <div className="bg-panel border-b border-line px-4 py-2 flex items-center justify-between text-[11px] font-bold text-muted">
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-danger/70 animate-pulse" />
              <span>pipeline_visualizer.sh</span>
            </div>
            <span className="text-[10px] text-accent uppercase tracking-wider font-semibold">Active State: {status}</span>
          </div>

          <div className="p-4 flex-1 flex flex-col md:grid md:grid-cols-[1.2fr_1fr] gap-4 min-h-0">
            {/* Logs console */}
            <div className="flex flex-col gap-1.5 overflow-y-auto max-h-[220px] text-[10px] leading-relaxed text-ink/80 border-r border-line/40 pr-2">
              {logs.length === 0 ? (
                <span className="text-muted italic">Awaiting pipeline simulation trigger...</span>
              ) : (
                logs.map((log, idx) => {
                  const isSuccess = log.includes("Successfully");
                  return (
                    <div key={idx} className={`console-line ${isSuccess ? "text-ok font-bold" : ""}`}>
                      <span className="text-muted">{">"}</span> {log}
                    </div>
                  );
                })
              )}
              {status === "injecting" && <div className="text-accent animate-pulse">⚡ Injecting into DB...</div>}
              {status === "inject_success" && (
                <div className="text-ok font-bold">
                  🎉 Graph successfully committed. Stats and recent timeline updated.
                  <pre className="text-[9px] mt-2 p-1.5 bg-panel-solid rounded-none border border-line text-ink leading-normal overflow-x-auto max-w-full">{realOutput}</pre>
                </div>
              )}
              {status === "inject_failed" && (
                <div className="text-danger font-bold">
                  ❌ Ingestion failed:
                  <pre className="text-[9px] mt-2 p-1.5 bg-panel-solid rounded-none border border-line text-ink leading-normal overflow-x-auto max-w-full">{realOutput}</pre>
                </div>
              )}
            </div>

            {/* Tree nodes graph output */}
            <div className="flex items-center justify-center relative min-h-[160px] bg-panel-solid/35 border border-dashed border-line/50 rounded-none p-2">
              {simulatedNodes.length === 0 ? (
                <div className="text-center text-[10px] text-muted p-4">
                  Nodes visualization will compile here.
                </div>
              ) : (
                <svg className="w-full h-full min-h-[160px]" viewBox="0 0 250 160">
                  {/* Edges */}
                  {simulatedEdges.map((e, idx) => {
                    const fromNode = simulatedNodes.find((n) => n.id === e.source);
                    const toNode = simulatedNodes.find((n) => n.id === e.target);
                    if (!fromNode || !toNode) return null;
                    return (
                      <g key={idx}>
                        <line
                          x1={fromNode.x}
                          y1={fromNode.y}
                          x2={toNode.x}
                          y2={toNode.y}
                          stroke="var(--line-active)"
                          strokeWidth="1.2"
                          className="playground-line"
                        />
                        <text
                          x={(fromNode.x + toNode.x) / 2}
                          y={(fromNode.y + toNode.y) / 2 - 4}
                          textAnchor="middle"
                          fill="var(--muted)"
                          fontSize="7"
                          className="font-mono stroke-bg stroke-[2px]"
                          style={{ paintOrder: "stroke" }}
                        >
                          {e.label}
                        </text>
                      </g>
                    );
                  })}
                  
                  {/* Nodes */}
                  {simulatedNodes.map((n) => {
                    const color = TYPE_COLORS[n.type] || "var(--accent)";
                    const strokeColor = SENSITIVITY_STROKE[n.sensitivity] || "var(--muted)";
                    return (
                      <g 
                        key={n.id} 
                        className="node-g animate-float" 
                        style={{ "--origin-x": `${n.x}px`, "--origin-y": `${n.y}px` }}
                      >
                        <polygon
                          points={getHexagonPoints(12)}
                          transform={`translate(${n.x}, ${n.y})`}
                          fill="var(--panel-solid)"
                          stroke={strokeColor}
                          strokeWidth="1.5"
                        />
                        <circle
                          cx={n.x}
                          cy={n.y}
                          r="3"
                          fill={color}
                        />
                        <text
                          x={n.x}
                          y={n.y + 22}
                          textAnchor="middle"
                          fill="var(--ink)"
                          fontSize="8"
                          fontWeight="600"
                          className="font-mono stroke-bg stroke-[2px]"
                          style={{ paintOrder: "stroke" }}
                        >
                          {trimLabel(n.label)}
                        </text>
                      </g>
                    );
                  })}
                </svg>
              )}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function Overview({
  summary,
  nodes,
  childId,
  theme,
  setTheme,
  dashboardToken,
  setDashboardToken,
  onOpenGraph,
  onInspect,
  onRefresh,
}) {
  const [activeLayer, setActiveLayer] = useState(0);

  const layerDetails = [
    {
      title: "sociomemory layer",
      badge: "Core Engine",
      desc: "Resolves implications, versions beliefs, tracks tradeoffs, and extracts semantic triples from turn streams.",
      details: [
        "Graph Inference Engine",
        "Consent-based Privacy Gating",
        "Automated Episodic Segmentation"
      ]
    },
    {
      title: "agent harness layer",
      badge: "Interaction Hub",
      desc: "Orchestrates incoming turns, tracks agent state, triggers coaching notifications, and structures LLM queries.",
      details: [
        "Multi-agent Synchronization",
        "Real-time Coaching Alerts",
        "Raw Input Sanitization"
      ]
    },
    {
      title: "signals layer",
      badge: "Context Ingestion",
      desc: "Ingests raw environmental data including coordinates, time intervals, visited venues, and device logs.",
      details: [
        "Reverse Geocoding",
        "Faiss Spatial Vectors",
        "Temporal Decay Signals"
      ]
    }
  ];

  const recent = useMemo(() => {
    const withDates = (nodes || []).filter((node) => node.type !== "Child");
    const sorted = [...withDates].sort((a, b) =>
      String(b.document_date || b.event_date || "").localeCompare(String(a.document_date || a.event_date || ""))
    );
    return sorted.slice(0, 5);
  }, [nodes]);

  const stats = [
    { label: "Memory nodes", value: summary?.nodes },
    { label: "Relations", value: summary?.edges },
    { label: "Stale nodes", value: summary?.stale_nodes },
    { label: "Faiss vectors", value: summary?.faiss_vectors },
  ];

  const scrollTo = (id) => document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });

  return (
    <div className="min-h-screen flex flex-col font-sans">
      {/* Sticky text nav */}
      <nav className="nav border-b border-line glass-panel rounded-none">
        <div className="flex items-center gap-3">
          <span className="text-base font-bold tracking-tight flex items-center gap-1.5"><Icon.Brain />sociomemory</span>
          <span className="hidden sm:inline eyebrow font-mono text-[9px]">memory engine</span>
        </div>
        <div className="hidden md:flex items-center gap-8 font-mono">
          <button type="button" className="nav-link is-active">overview</button>
          <button type="button" className="nav-link" onClick={() => scrollTo("capabilities")}>capabilities</button>
          <button type="button" className="nav-link" onClick={() => scrollTo("playground")}>playground</button>
          <button type="button" className="nav-link" onClick={() => scrollTo("notes")}>field_notes</button>
        </div>
        <div className="flex items-center gap-4">
          <DashboardTokenControl token={dashboardToken} setToken={setDashboardToken} />
          <ThemeSwitcher theme={theme} setTheme={setTheme} />
          <button type="button" className="arrow-link font-mono" onClick={onOpenGraph}>Graph explorer {ARROW}</button>
        </div>
      </nav>

      <main className="flex-1 max-w-6xl mx-auto px-6 py-8">
        {/* Hero Section */}
        <section id="overview" className="dot-bg border border-line rounded-none p-8 md:p-12 mb-12 relative overflow-hidden">
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_30%_30%,rgba(16,185,129,0.06),transparent_50%)] pointer-events-none" />
          <div className="grid md:grid-cols-[1.1fr_0.9fr] gap-12 items-center relative z-10">
            <div className="flex flex-col gap-6">
              <div className="inline-flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-line-active animate-pulse" />
                <span className="eyebrow font-mono text-[10px]">A social-context memory engine v0.1.0</span>
              </div>
              <h1 className="hero-title gradient-text font-sans">
                The context layer above the conversations your agents already have.
              </h1>
              <p className="lede text-sm leading-relaxed text-muted">
                Raw turns carry social signal by design. sociomemory builds it into a living graph —
                neighborhood, school, lifestyle, economics — so every agent reasons with context, not just text.
              </p>
              <div className="flex flex-wrap items-center gap-4 mt-2">
                <button type="button" className="btn btn-primary px-5 py-2.5 h-auto text-sm" onClick={onOpenGraph}>
                  Open graph explorer <span aria-hidden="true">&rarr;</span>
                </button>
                <button type="button" className="arrow-link text-sm font-mono" onClick={() => scrollTo("playground")}>
                  Try simulator {ARROW}
                </button>
              </div>
              <div className="flex items-center gap-2.5 mt-4">
                <span className="label font-mono text-[9px]">Active agent profile</span>
                <span className="chip lowercase tracking-normal font-mono px-2 py-0.5 text-[10px] bg-panel/30 border-line">{childId}</span>
              </div>
            </div>
            
            {/* Interactive Stack Visualizer Column */}
            <div className="flex flex-col items-center justify-center bg-panel/20 border border-line/40 rounded-none p-6 backdrop-blur-sm relative">
              <InteractiveStack activeLayer={activeLayer} setActiveLayer={setActiveLayer} />
              
              {/* Dynamic Detail Card */}
              <div className="w-full mt-4 p-4 border border-line/60 bg-panel-solid rounded-none font-mono text-left transition-all duration-300">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-ink font-bold text-xs uppercase tracking-wider">
                    {layerDetails[activeLayer].title}
                  </span>
                  <span className="chip bg-line-active/10 border-line-active/40 text-line-active text-[8px] font-bold">
                    {layerDetails[activeLayer].badge}
                  </span>
                </div>
                <p className="text-[11px] text-muted leading-relaxed m-0 mb-3">
                  {layerDetails[activeLayer].desc}
                </p>
                <div className="grid grid-cols-1 gap-1 text-[9px] text-ink opacity-90 border-t border-line/40 pt-2">
                  {layerDetails[activeLayer].details.map((detail, idx) => (
                    <div key={idx} className="flex items-center gap-1.5">
                      <span className="text-line-active">•</span>
                      <span>{detail}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Live stats strip */}
        <section className="mb-12">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {stats.map((s) => (
              <div key={s.label} className="glass-panel px-5 py-6 flex flex-col gap-2 relative overflow-hidden group">
                <div className="absolute top-0 left-0 w-full h-[2px] bg-gradient-to-r from-line-active/50 to-transparent scale-x-0 group-hover:scale-x-100 transition-transform duration-300 origin-left" />
                <span className="metric-label font-mono text-[9px]">{s.label}</span>
                <span className="stat-value text-3xl font-mono tracking-tight font-extrabold">{s.value ?? "—"}</span>
              </div>
            ))}
          </div>
        </section>

        {/* Ingest Playground */}
        <div id="playground">
          <IngestPlayground childId={childId} onInjected={onRefresh} />
        </div>

        {/* Capabilities Grid */}
        <section id="capabilities" className="mb-12 border-t border-line/60 pt-12">
          <div className="flex items-end justify-between gap-4 mb-8">
            <div className="flex flex-col gap-2">
              <span className="eyebrow eyebrow-line">Capabilities</span>
              <h2 className="sec-head">Six stages from a single turn to social context.</h2>
            </div>
            <button type="button" className="arrow-link font-mono hidden sm:inline-flex" onClick={onOpenGraph}>
              Explore the graph {ARROW}
            </button>
          </div>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {CAPABILITIES.map((cap) => (
              <article key={cap.n} className="glass-panel p-5 flex flex-col gap-4 relative group cursor-default">
                <div className="flex items-center justify-between">
                  <span className="sec-num font-mono">{cap.n}</span>
                  <span className="w-2 h-2 rounded-full bg-line-active scale-75 group-hover:scale-100 transition-transform duration-300" />
                </div>
                <h3 className="text-base font-bold text-ink m-0 tracking-tight">{cap.title}</h3>
                <p className="text-xs text-muted leading-relaxed m-0 flex-1">{cap.body}</p>
                <button type="button" className="arrow-link font-mono mt-1 text-[11px] self-start" onClick={onOpenGraph}>
                  Learn more {ARROW}
                </button>
              </article>
            ))}
          </div>
        </section>

        {/* Field Notes Terminal */}
        <section id="notes" className="border-t border-line/60 pt-12">
          <div className="flex flex-col gap-2 mb-6">
            <span className="eyebrow eyebrow-line">Field notes</span>
            <h2 className="sec-head">Recent memory timeline for {childId}.</h2>
          </div>
          <div className="bg-panel-solid border border-line rounded-none p-5 font-mono">
            <div className="border-b border-line pb-3 mb-4 flex items-center justify-between text-[11px] text-muted">
              <span>SYSTEM EVENT LEDGER</span>
              <span>FILTER: REAL_TIME_NODES</span>
            </div>
            {recent.length === 0 ? (
              <div className="text-muted text-xs p-6 border border-dashed border-line/60 rounded-none text-center font-mono">
                No memories committed to database yet. Try running simulator pipeline or open graph explorer.
              </div>
            ) : (
              <div className="flex flex-col gap-1">
                {recent.map((node) => (
                  <button
                    key={node.id}
                    type="button"
                    onClick={() => onInspect(node.id)}
                    className="group text-left grid grid-cols-[130px_1fr_auto] items-center gap-4 py-2.5 px-3 rounded-none hover:bg-panel transition-colors border border-transparent hover:border-line/40 cursor-pointer"
                  >
                    <span className="label font-mono text-muted text-[10px]">{formatNoteDate(node.document_date || node.event_date)}</span>
                    <span className="flex items-center gap-2 min-w-0">
                      <span className="w-1.5 h-1.5 rounded-full shrink-0" style={{ background: TYPE_COLORS[node.type] || "var(--muted)" }} />
                      <span className="text-xs text-ink truncate font-semibold">{node.label || node.type}</span>
                      <span className="chip shrink-0 text-[8px] bg-panel px-1 py-0.5 border-line font-mono">{node.type}</span>
                    </span>
                    <span className="arrow-link font-mono text-[10px] opacity-40 group-hover:opacity-100 group-hover:translate-x-1 transition-all">
                      inspect {ARROW}
                    </span>
                  </button>
                ))}
              </div>
            )}
          </div>
        </section>
      </main>

      <footer className="border-t border-line mt-12 bg-panel/30">
        <div className="max-w-6xl mx-auto px-6 py-8 flex flex-wrap items-center justify-between gap-3 font-mono">
          <span className="text-xs font-bold flex items-center gap-2"><Icon.Brain />sociomemory</span>
          <span className="label text-[9px]">graph memory engine · local system</span>
        </div>
      </footer>
    </div>
  );
}

function GraphLegend({ nodes }) {
  const [collapsed, setCollapsed] = useState(false);
  const typeCounts = useMemo(() => {
    const counts = new Map();
    for (const node of nodes) counts.set(node.type, (counts.get(node.type) || 0) + 1);
    return Array.from(counts.entries()).sort((a, b) => b[1] - a[1]);
  }, [nodes]);

  if (typeCounts.length === 0) return null;

  return (
    <div className="absolute top-3 right-3 z-20 bg-panel/95 border border-line rounded-none text-[10px] max-w-[200px] backdrop-blur-sm shadow-sm">
      <button
        type="button"
        onClick={() => setCollapsed((c) => !c)}
        className="w-full flex items-center justify-between gap-2 px-2 py-1.5 cursor-pointer bg-transparent border-0 border-b border-line text-muted font-bold uppercase tracking-wider hover:text-ink transition-colors"
      >
        <span>Legend · {typeCounts.length} types</span>
        <span className="font-mono">{collapsed ? "+" : "–"}</span>
      </button>
      {!collapsed && (
        <div className="p-2 flex flex-col gap-1.5">
          <div className="flex flex-col gap-1 max-h-44 overflow-y-auto pr-1">
            {typeCounts.map(([type, count]) => (
              <div key={type} className="flex items-center gap-1.5">
                <svg width="12" height="12" viewBox="-6 -6 12 12" className="shrink-0">
                  <polygon
                    points="0,-5 4.33,-2.5 4.33,2.5 0,5 -4.33,2.5 -4.33,-2.5"
                    fill={TYPE_COLORS[type] || "#64748b"}
                    stroke="rgba(0,0,0,0.15)"
                    strokeWidth="0.5"
                    strokeLinejoin="round"
                  />
                </svg>
                <span className="text-ink flex-1 truncate">{type}</span>
                <span className="text-muted font-mono">{count}</span>
              </div>
            ))}
          </div>
          <div className="border-t border-line pt-1.5 flex flex-col gap-1">
            <div className="text-muted font-bold uppercase tracking-wider">Border = sensitivity</div>
            {Object.entries(SENSITIVITY_STROKE).map(([level, color]) => (
              <div key={level} className="flex items-center gap-1.5">
                <svg width="12" height="12" viewBox="-6 -6 12 12" className="shrink-0">
                  <polygon
                    points="0,-5 4.33,-2.5 4.33,2.5 0,5 -4.33,2.5 -4.33,-2.5"
                    fill="none"
                    stroke={color}
                    strokeWidth="1.5"
                    strokeLinejoin="round"
                  />
                </svg>
                <span className="text-ink capitalize">{level}</span>
              </div>
            ))}
            <div className="flex items-center gap-1.5">
              <svg width="12" height="12" viewBox="-6 -6 12 12" className="shrink-0">
                <polygon
                  points="0,-5 4.33,-2.5 4.33,2.5 0,5 -4.33,2.5 -4.33,-2.5"
                  fill="none"
                  stroke="#f59e0b"
                  strokeWidth="1.5"
                  strokeDasharray="1.5, 1.5"
                  strokeLinejoin="round"
                />
              </svg>
              <span className="text-ink">stale (amber dashed)</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function GraphCanvas({ nodes, edges, selectedNodeId, onSelectNode }) {
  const width = 960;
  const height = 640;
  
  const svgRef = useRef(null);
  const nodesRef = useRef(new Map());
  const dragNodeIdRef = useRef(null);

  // Viewport navigation states (zoom and pan)
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isPanning, setIsPanning] = useState(false);
  const panStartRef = useRef({ x: 0, y: 0 });

  // Floating search and tooltips
  const [searchQuery, setSearchQuery] = useState("");
  const [hoveredNode, setHoveredNode] = useState(null);
  const [tooltipPos, setTooltipPos] = useState({ x: 0, y: 0 });

  // Physics animation values
  const [positions, setPositions] = useState({});

  // Sleek loading/aligning state
  const [isAligning, setIsAligning] = useState(false);

  // Sync incoming filtered nodes with physics engine, preserving current positions
  useEffect(() => {
    const current = nodesRef.current;
    const next = new Map();
    const centerX = width / 2;
    const centerY = height / 2;

    nodes.forEach((node, index) => {
      if (current.has(node.id)) {
        next.set(node.id, current.get(node.id));
      } else {
        // Group radial setup as starting layout
        const angle = (index * 2 * Math.PI) / Math.max(nodes.length, 1);
        const radius = 80 + Math.random() * 60;
        next.set(node.id, {
          id: node.id,
          x: centerX + Math.cos(angle) * radius,
          y: centerY + Math.sin(angle) * radius,
          vx: 0,
          vy: 0,
          pinned: false,
        });
      }
    });

    nodesRef.current = next;
    
    // Trigger alignment state on new node load or changes
    if (nodes.length > 0) {
      setIsAligning(true);
    }
  }, [nodes]);

  // Verlet integration loop for Force-Directed Simulation
  useEffect(() => {
    let animationId;
    let framesCount = 0;
    
    const tick = () => {
      const nodesArray = Array.from(nodesRef.current.values());
      const length = nodesArray.length;
      
      // 1. Repulsion force between all node pairs
      for (let i = 0; i < length; i++) {
        const nodeA = nodesArray[i];
        for (let j = i + 1; j < length; j++) {
          const nodeB = nodesArray[j];
          const dx = nodeB.x - nodeA.x;
          const dy = nodeB.y - nodeA.y;
          const dist = Math.sqrt(dx * dx + dy * dy) + 0.1;
          
          if (dist < 160) {
            const force = (160 - dist) * 0.09;
            const fx = force * (dx / dist);
            const fy = force * (dy / dist);
            
            if (!nodeA.pinned) {
              nodeA.vx -= fx;
              nodeA.vy -= fy;
            }
            if (!nodeB.pinned) {
              nodeB.vx += fx;
              nodeB.vy += fy;
            }
          }
        }
      }
      
      // 2. Attraction force (edges act as springs pulling nodes together)
      edges.forEach((edge) => {
        const nodeA = nodesRef.current.get(edge.source);
        const nodeB = nodesRef.current.get(edge.target);
        if (!nodeA || !nodeB) return;
        
        const dx = nodeB.x - nodeA.x;
        const dy = nodeB.y - nodeA.y;
        const dist = Math.sqrt(dx * dx + dy * dy) + 0.1;
        
        const restLength = 95;
        const strength = 0.055;
        const force = (dist - restLength) * strength;
        const fx = force * (dx / dist);
        const fy = force * (dy / dist);
        
        if (!nodeA.pinned) {
          nodeA.vx += fx;
          nodeA.vy += fy;
        }
        if (!nodeB.pinned) {
          nodeB.vx -= fx;
          nodeB.vy -= fy;
        }
      });
      
      // 3. Gravity center pull & Friction
      const centerX = width / 2;
      const centerY = height / 2;
      
      nodesArray.forEach((node) => {
        if (!node.pinned) {
          const dx = centerX - node.x;
          const dy = centerY - node.y;
          node.vx += dx * 0.007;
          node.vy += dy * 0.007;
          
          node.vx *= 0.82;
          node.vy *= 0.82;
          
          node.x += node.vx;
          node.y += node.vy;
          
          // Boundaries inside canvas
          node.x = Math.max(30, Math.min(width - 30, node.x));
          node.y = Math.max(30, Math.min(height - 30, node.y));
        }
      });
      
      // Export calculated coordinates to React state for SVG render
      const nextPos = {};
      nodesRef.current.forEach((pos, id) => {
        nextPos[id] = { x: pos.x, y: pos.y };
      });
      setPositions(nextPos);
      
      // Track kinetic energy of simulation to hide alignment loading screen when stable
      framesCount += 1;
      let totalEnergy = 0;
      nodesArray.forEach((node) => {
        if (!node.pinned) {
          totalEnergy += Math.sqrt(node.vx * node.vx + node.vy * node.vy);
        }
      });

      // Warmup at least 15 frames, dismiss loading overlay when average node speed settles below 0.15, or max 120 frames timeout
      if (framesCount > 15 && (totalEnergy < 0.15 || framesCount > 120)) {
        setIsAligning(false);
      }
      
      animationId = requestAnimationFrame(tick);
    };
    
    animationId = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(animationId);
  }, [nodes, edges]);

  // Coordinate projection from screen to transform-aware SVG Canvas
  const getSVGCoords = (e) => {
    if (!svgRef.current) return { x: 0, y: 0 };
    const rect = svgRef.current.getBoundingClientRect();
    const clientX = e.clientX - rect.left;
    const clientY = e.clientY - rect.top;
    
    // Reverse zoom and pan calculations
    const x = (clientX - pan.x) / zoom;
    const y = (clientY - pan.y) / zoom;
    return { x, y };
  };

  // Zoom handlers
  const handleZoomIn = () => setZoom((z) => Math.min(z * 1.25, 5));
  const handleZoomOut = () => setZoom((z) => Math.max(z / 1.25, 0.1));
  const handleResetZoom = () => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
  };
  
  const handleFitToScreen = () => {
    if (nodes.length === 0) return;
    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
    let found = false;
    
    nodes.forEach((n) => {
      const pos = nodesRef.current.get(n.id);
      if (pos) {
        found = true;
        if (pos.x < minX) minX = pos.x;
        if (pos.x > maxX) maxX = pos.x;
        if (pos.y < minY) minY = pos.y;
        if (pos.y > maxY) maxY = pos.y;
      }
    });

    if (!found) return;
    
    const graphW = maxX - minX || 1;
    const graphH = maxY - minY || 1;
    const padding = 80;
    
    const scaleX = (width - padding * 2) / graphW;
    const scaleY = (height - padding * 2) / graphH;
    const nextZoom = Math.max(0.15, Math.min(scaleX, scaleY, 1.8));
    
    const graphCenterX = (minX + maxX) / 2;
    const graphCenterY = (minY + maxY) / 2;
    
    const nextPanX = width / 2 - graphCenterX * nextZoom;
    const nextPanY = height / 2 - graphCenterY * nextZoom;
    
    setZoom(nextZoom);
    setPan({ x: nextPanX, y: nextPanY });
  };

  const handleWheel = (e) => {
    e.preventDefault();
    const zoomFactor = 1.08;
    const nextZoom = e.deltaY < 0 ? zoom * zoomFactor : zoom / zoomFactor;
    setZoom(Math.max(0.1, Math.min(nextZoom, 5)));
  };

  // Drag and pan mouse handlers
  const handleMouseDown = (e) => {
    if (e.button === 0) { // Left-click
      setIsPanning(true);
      panStartRef.current = { x: e.clientX - pan.x, y: e.clientY - pan.y };
    }
  };

  const handleMouseMove = (e) => {
    if (dragNodeIdRef.current) {
      // Dragging a node
      const coords = getSVGCoords(e);
      const node = nodesRef.current.get(dragNodeIdRef.current);
      if (node) {
        node.x = coords.x;
        node.y = coords.y;
        node.vx = 0;
        node.vy = 0;
      }
    } else if (isPanning) {
      // Panning the canvas
      setPan({
        x: e.clientX - panStartRef.current.x,
        y: e.clientY - panStartRef.current.y,
      });
    }
    
    // If hovering, update tooltip position
    if (hoveredNode) {
      const rect = svgRef.current.getBoundingClientRect();
      setTooltipPos({
        x: e.clientX - rect.left + 15,
        y: e.clientY - rect.top - 15,
      });
    }
  };

  const handleMouseUp = () => {
    if (dragNodeIdRef.current) {
      const node = nodesRef.current.get(dragNodeIdRef.current);
      if (node) {
        node.pinned = false;
      }
      dragNodeIdRef.current = null;
    }
    setIsPanning(false);
  };

  const handleNodeMouseDown = (e, id) => {
    if (e.button !== 0) return;
    e.stopPropagation();
    dragNodeIdRef.current = id;
    const node = nodesRef.current.get(id);
    if (node) {
      node.pinned = true;
    }
    onSelectNode(id);
  };

  const handleNodeMouseEnter = (e, node) => {
    setHoveredNode(node);
    if (svgRef.current) {
      const rect = svgRef.current.getBoundingClientRect();
      setTooltipPos({
        x: e.clientX - rect.left + 15,
        y: e.clientY - rect.top - 15,
      });
    }
  };

  const handleNodeMouseLeave = () => {
    setHoveredNode(null);
  };

  // Node Neighborhood Dimming Calculations
  const activeNodeId = hoveredNode?.id || selectedNodeId;
  const neighborhoodNodeIds = useMemo(() => {
    if (!activeNodeId) return null;
    const neighbors = new Set([activeNodeId]);
    edges.forEach((edge) => {
      if (edge.source === activeNodeId) neighbors.add(edge.target);
      if (edge.target === activeNodeId) neighbors.add(edge.source);
    });
    return neighbors;
  }, [activeNodeId, edges]);

  // Search Results
  const matchingNodeIds = useMemo(() => {
    const query = searchQuery.trim().toLowerCase();
    if (!query) return new Set();
    return new Set(
      nodes
        .filter(
          (n) =>
            n.id.toLowerCase().includes(query) ||
            (n.label || "").toLowerCase().includes(query) ||
            n.type.toLowerCase().includes(query)
        )
        .map((n) => n.id)
    );
  }, [searchQuery, nodes]);

  // Center view on a searched node
  const focusOnNode = (nodeId) => {
    const pos = nodesRef.current.get(nodeId);
    if (pos) {
      const targetZoom = 1.3;
      setZoom(targetZoom);
      setPan({
        x: width / 2 - pos.x * targetZoom,
        y: height / 2 - pos.y * targetZoom,
      });
      onSelectNode(nodeId);
      setSearchQuery("");
    }
  };

  if (nodes.length === 0) {
    return (
      <div className="w-full h-full flex items-center justify-center bg-bg">
        <div className="text-muted text-xs p-5 border border-dashed border-line rounded-none bg-bg">No nodes match the current filters.</div>
      </div>
    );
  }

  return (
    <div className="flex-1 w-full relative bg-bg overflow-hidden cursor-grab active:cursor-grabbing" onWheel={handleWheel}>
      {/* Sleek Force-Directed Align Overlay */}
      {isAligning && (
        <div className="absolute inset-0 bg-black/70 flex items-center justify-center z-40 transition-all">
          <div className="text-center bg-panel p-6 rounded-none border border-line max-w-[280px]">
            <div className="relative w-9 h-9 mx-auto">
              <div className="absolute inset-0 rounded-full border-2 border-transparent border-t-primary border-b-primary animate-spin"></div>
              <div className="absolute inset-1 rounded-full border-2 border-transparent border-l-accent border-r-accent animate-spin-reverse"></div>
            </div>
            <h3 className="m-0 mt-3 text-xs font-bold text-ink uppercase tracking-wider">Aligning Neural Nodes</h3>
            <p className="m-0 text-[11px] text-muted leading-normal">Optimizing cognitive map geometry...</p>
          </div>
        </div>
      )}

      {/* Floating Search Panel */}
      <div className="absolute top-16 left-3 w-56 z-20 flex gap-1.5">
        <input
          type="text"
          placeholder="Search memory graph..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="field flex-1 bg-panel text-[11px]"
        />
        {searchQuery.trim() !== "" && (
          <div className="absolute top-9 left-0 right-0 bg-panel border border-line rounded-none max-h-44 overflow-y-auto z-50 shadow-none">
            {nodes
              .filter((n) => matchingNodeIds.has(n.id))
              .map((node) => (
                <div
                  key={node.id}
                  onClick={() => focusOnNode(node.id)}
                  className="p-2 cursor-pointer text-[11px] border-b border-line text-ink flex justify-between items-center hover:bg-line transition-colors"
                >
                  <span style={{ fontWeight: '600' }}>{node.label || node.id}</span>
                  <span style={{ fontSize: '10px', color: TYPE_COLORS[node.type] || '#fff', opacity: 0.8 }}>{node.type}</span>
                </div>
              ))}
            {matchingNodeIds.size === 0 && (
              <div className="p-2.5 text-muted text-[11px] text-center">
                No matches found.
              </div>
            )}
          </div>
        )}
      </div>

      {/* Floating Canvas Controls */}
      <div className="absolute bottom-3 right-3 flex flex-col gap-1 z-20 bg-panel p-1 rounded-none border border-line">
        <button type="button" title="Zoom In" onClick={handleZoomIn} className="w-7 h-7 p-0 rounded-none bg-transparent border border-transparent hover:bg-line hover:border-line flex items-center justify-center transition-all cursor-pointer"><Icon.ZoomIn /></button>
        <button type="button" title="Zoom Out" onClick={handleZoomOut} className="w-7 h-7 p-0 rounded-none bg-transparent border border-transparent hover:bg-line hover:border-line flex items-center justify-center transition-all cursor-pointer"><Icon.ZoomOut /></button>
        <div className="h-[1px] bg-line my-0.5"></div>
        <button type="button" title="Fit to View" onClick={handleFitToScreen} className="w-7 h-7 p-0 rounded-none bg-transparent border border-transparent hover:bg-line hover:border-line flex items-center justify-center transition-all cursor-pointer"><Icon.Fit /></button>
        <button type="button" title="Reset Camera" onClick={handleResetZoom} className="w-7 h-7 p-0 rounded-none bg-transparent border border-transparent hover:bg-line hover:border-line flex items-center justify-center transition-all cursor-pointer"><Icon.Reset /></button>
      </div>

      {/* Legend */}
      <GraphLegend nodes={nodes} />

      {/* Hover Tooltip Overlay */}
      {hoveredNode && (
        <div className="absolute z-30 bg-panel border border-line-active p-2.5 rounded-none pointer-events-none text-[11px] max-w-[240px]" style={{ left: tooltipPos.x, top: tooltipPos.y }}>
          <h4 className="m-0 mb-1 text-xs font-bold text-ink truncate">{hoveredNode.label || hoveredNode.id}</h4>
          <div className="flex gap-1 mb-1">
            <span className="chip" style={{ borderColor: TYPE_COLORS[hoveredNode.type], color: TYPE_COLORS[hoveredNode.type] }}>{hoveredNode.type}</span>
            <span className={`chip ${hoveredNode.sensitivity === 'sensitive' ? 'border-danger/40 text-danger' : ''}`}>{hoveredNode.sensitivity}</span>
          </div>
          <div className="text-[10px] text-muted mt-1">
            Confidence: <b className="text-ink">{Number(hoveredNode.confidence || 0).toFixed(2)}</b>
          </div>
          {hoveredNode.properties && Object.keys(hoveredNode.properties).length > 0 && (
            <div className="text-ink opacity-80 leading-normal mt-1">
              {Object.entries(hoveredNode.properties).slice(0, 2).map(([k, v]) => (
                <div key={k} className="truncate">
                  • <b>{k}</b>: {String(v)}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Main SVG Graph */}
      <svg
        ref={svgRef}
        className="w-full h-full bg-transparent select-none"
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        role="img"
        aria-label="Sociomemory graph visualization"
      >
        <defs>
          <marker id="arrow" markerWidth="9" markerHeight="9" refX="7" refY="3" orient="auto" markerUnits="strokeWidth">
            <path d="M0,0 L0,6 L8,3 z" fill="var(--edge-color)" />
          </marker>
          <marker id="arrow-highlighted" markerWidth="9" markerHeight="9" refX="7" refY="3" orient="auto" markerUnits="strokeWidth">
            <path d="M0,0 L0,6 L8,3 z" fill="var(--primary)" />
          </marker>
          {/* Minimalist dot grid pattern background */}
          <pattern
            id="dot-grid"
            width="24"
            height="24"
            patternUnits="userSpaceOnUse"
            patternTransform={`translate(${pan.x}, ${pan.y})`}
          >
            <circle cx="2" cy="2" r="1.2" fill="var(--grid-dot)" />
          </pattern>
          {/* Dynamic linear gradients for node shapes */}
          {Object.entries(TYPE_COLORS).map(([type, color]) => (
            <linearGradient key={type} id={`grad-${type}`} x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stopColor={color} stopOpacity={0.25} />
              <stop offset="100%" stopColor={color} stopOpacity={0.05} />
            </linearGradient>
          ))}
        </defs>

        {/* Stable dot matrix grid overlay */}
        <rect width="100%" height="100%" fill="url(#dot-grid)" />

        {/* Outer transform group */}
        <g transform={`translate(${pan.x}, ${pan.y}) scale(${zoom})`}>
          
          {/* Edges & Link Relationships */}
          {edges.map((edge, index) => {
            const a = positions[edge.source];
            const b = positions[edge.target];
            if (!a || !b) return null;

            // Math to offset links to point exactly to circle borders
            const dx = b.x - a.x;
            const dy = b.y - a.y;
            const dist = Math.sqrt(dx * dx + dy * dy) || 1;
            
            const targetNode = nodes.find(n => n.id === edge.target);
            const sourceNode = nodes.find(n => n.id === edge.source);
            
            const targetRad = 14;
            const sourceRad = 14;

            const x1 = a.x + (dx * sourceRad) / dist;
            const y1 = a.y + (dy * sourceRad) / dist;
            const x2 = b.x - (dx * (targetRad + 6)) / dist;
            const y2 = b.y - (dy * (targetRad + 6)) / dist;

            const isEdgeHighlighted = activeNodeId && (edge.source === activeNodeId || edge.target === activeNodeId);
            const isEdgeDimmed = neighborhoodNodeIds && !isEdgeHighlighted;

            return (
              <g key={`${edge.id || index}-${edge.source}-${edge.target}`} className={`transition-opacity duration-200 ${isEdgeDimmed ? "opacity-10" : "opacity-100"}`}>
                {/* Thick background line for easier hover clicks */}
                <line className="stroke-transparent stroke-[6px] fill-none cursor-pointer" x1={x1} y1={y1} x2={x2} y2={y2} />
                <line
                  x1={x1}
                  y1={y1}
                  x2={x2}
                  y2={y2}
                  stroke={isEdgeHighlighted ? "var(--primary)" : "var(--edge-color)"}
                  strokeWidth={isEdgeHighlighted ? 2.5 : 1.2}
                  className="transition-all duration-200"
                  markerEnd={isEdgeHighlighted ? "url(#arrow-highlighted)" : "url(#arrow)"}
                />
                <text
                  x={(x1 + x2) / 2}
                  y={(y1 + y2) / 2 - 4}
                  textAnchor="middle"
                  className="text-[8px] font-medium select-none stroke-bg stroke-[2px]"
                  style={{ paintOrder: 'stroke', strokeLinejoin: 'round' }}
                  fill={isEdgeHighlighted ? "var(--primary)" : "var(--edge-label-fill)"}
                >
                  {edge.type || ""}
                </text>
              </g>
            );
          })}

          {/* Nodes */}
          {nodes.map((node) => {
            const point = positions[node.id];
            if (!point) return null;

            const isNeighborhoodDimmed = neighborhoodNodeIds && !neighborhoodNodeIds.has(node.id);
            const isMatched = searchQuery.trim() !== "" && matchingNodeIds.has(node.id);

            const color = TYPE_COLORS[node.type] || "#9ca3af";
            const border = SENSITIVITY_STROKE[node.sensitivity] || "#9ca3af";

            return (
              <g
                key={node.id}
                className={`transition-opacity duration-150 ${isNeighborhoodDimmed ? "opacity-10" : "opacity-100"}`}
                transform={`translate(${point.x}, ${point.y})`}
                onMouseDown={(e) => handleNodeMouseDown(e, node.id)}
                onMouseEnter={(e) => handleNodeMouseEnter(e, node)}
                onMouseMove={handleMouseMove}
                onMouseLeave={handleNodeMouseLeave}
                style={{ color: color }}
              >
                {/* Custom Hexagonal Node Shape with dynamic gradient fill and sensitivity outline */}
                <polygon
                  points={getHexagonPoints(14)}
                  fill={`url(#grad-${node.type})`}
                  stroke={border}
                  strokeWidth={selectedNodeId === node.id ? 2.5 : 1.5}
                  strokeDasharray={node.stale ? "2, 2" : undefined}
                  strokeLinejoin="round"
                  className={`transition-all duration-150 cursor-pointer ${
                    selectedNodeId === node.id ? "scale-110" : "hover:scale-110"
                  } ${isMatched ? "animate-pulse" : ""}`}
                />

                {/* Core Point of Focus */}
                <polygon
                  points={getHexagonPoints(4.5)}
                  fill={color}
                  stroke="none"
                  strokeLinejoin="round"
                  className="pointer-events-none"
                />
                
                {/* Stale Node Warning indicator as a tiny secondary hexagonal dot */}
                {node.stale && (
                  <g transform="translate(13, -13)" className="animate-pulse">
                    <polygon
                      points="0,-4 3.46,-2 3.46,2 0,4 -3.46,2 -3.46,-2"
                      fill="#f59e0b"
                      stroke="var(--bg)"
                      strokeWidth={1}
                      strokeLinejoin="round"
                    />
                  </g>
                )}

                {/* Node Label Text */}
                <text
                  x="0"
                  y={25}
                  textAnchor="middle"
                  className="pointer-events-none fill-ink text-[10px] font-semibold tracking-wide transition-colors stroke-bg stroke-[3px] select-none"
                  style={{ paintOrder: 'stroke', strokeLinejoin: 'round' }}
                >
                  {trimLabel(node.label || node.type)}
                </text>
              </g>
            );
          })}
        </g>
      </svg>
    </div>
  );
}

function NodeInspector({ detail }) {
  if (!detail?.node) {
    return (
      <div className="w-full h-full flex items-center justify-center bg-bg">
        <div className="text-muted text-xs p-5 border border-dashed border-line rounded-none bg-bg text-center">
          Select any memory node from the Graph Explorer to inspect properties, confidence, and provenance details.
        </div>
      </div>
    );
  }
  const node = detail.node;
  return (
    <div className="flex flex-col gap-2.5">
      <h3 className="m-0 text-base font-bold text-ink leading-tight">{node.label || node.type}</h3>
      <div className="flex flex-wrap gap-1 mb-1.5">
        <span className="chip" style={{ color: TYPE_COLORS[node.type] || 'var(--ink)', borderColor: TYPE_COLORS[node.type] || 'var(--line)' }}>{node.type}</span>
        <span className={`chip ${node.sensitivity === "sensitive" ? "border-danger/40 text-danger" : node.sensitivity === "personal" ? "border-warn/40 text-warn" : "border-accent/40 text-accent"}`}>{node.sensitivity}</span>
        <span className={`chip ${Number(node.confidence) < 0.5 ? "border-warn/40 text-warn" : "border-accent/40 text-accent"}`}>
          {Number(node.confidence).toFixed(2)} confidence
        </span>
        {node.stale && <span className="chip border-warn/40 text-warn">stale node</span>}
      </div>
      <dl className="grid grid-cols-[100px_1fr] gap-x-2 gap-y-1.5 mb-2 text-xs bg-bg p-2.5 rounded-none border border-line">
        <dt className="text-muted font-bold">Node ID</dt><dd className="m-0 overflow-wrap-anywhere text-ink font-mono text-[11px]">{node.id}</dd>
        <dt className="text-muted font-bold">Doc Date</dt><dd className="m-0 overflow-wrap-anywhere text-ink">{node.document_date || "Not set"}</dd>
        <dt className="text-muted font-bold">Event Date</dt><dd className="m-0 overflow-wrap-anywhere text-ink">{node.event_date || "Not set"}</dd>
        <dt className="text-muted font-bold">Convergence</dt><dd className="m-0 overflow-wrap-anywhere text-ink">{String(detail.convergence ?? "False")}</dd>
        <dt className="text-muted font-bold">Source Chunk</dt><dd className="m-0 overflow-wrap-anywhere text-ink">{node.source_chunk || "None"}</dd>
      </dl>
      
      {node.type === "Place" && node.properties?.web_enriched ? (
        <>
          <h4 className="m-0 mt-3 mb-1 text-[11px] font-bold text-muted uppercase tracking-wider">Place details (web-enriched)</h4>
          <PlaceDetails properties={node.properties} />
        </>
      ) : null}

      <h4 className="m-0 mt-3 mb-1 text-[11px] font-bold text-muted uppercase tracking-wider">Properties</h4>
      <PropertyList properties={node.properties} hideKeys={PLACE_DETAIL_KEYS} />

      <h4 className="m-0 mt-3 mb-1 text-[11px] font-bold text-muted uppercase tracking-wider">Provenance Timeline</h4>
      <ProvenanceList provenance={detail.provenance} />
    </div>
  );
}

const PLACE_DETAIL_KEYS = new Set([
  "web_enriched",
  "enrichment_sources",
  "full_name",
  "category",
  "summary",
  "tags",
  "cuisine",
  "deity_or_tradition",
  "locality",
  "city",
]);

function PlaceDetails({ properties }) {
  const p = properties || {};
  const title = p.full_name || p.name;
  const locality = [p.locality, p.city].filter(Boolean).join(", ");
  const tags = Array.isArray(p.tags) ? p.tags : [];
  return (
    <div className="bg-bg border border-line rounded-none p-2.5 text-xs flex flex-col gap-2">
      <div className="flex items-center justify-between gap-2">
        <div className="text-ink font-bold text-sm leading-tight">{title}</div>
        {p.category ? (
          <span className="chip border-accent/40 text-accent whitespace-nowrap">
            {String(p.category).replace(/_/g, " ")}
          </span>
        ) : null}
      </div>
      {p.summary ? <div className="text-ink opacity-90 leading-relaxed">{p.summary}</div> : null}
      <dl className="grid grid-cols-[88px_1fr] gap-x-2 gap-y-1">
        {locality ? (<><dt className="text-muted font-bold">Location</dt><dd className="m-0 text-ink overflow-wrap-anywhere">{locality}</dd></>) : null}
        {p.cuisine ? (<><dt className="text-muted font-bold">Cuisine</dt><dd className="m-0 text-ink">{String(p.cuisine).replace(/_/g, " ")}</dd></>) : null}
        {p.deity_or_tradition ? (<><dt className="text-muted font-bold">Tradition</dt><dd className="m-0 text-ink">{String(p.deity_or_tradition).replace(/_/g, " ")}</dd></>) : null}
      </dl>
      {tags.length ? (
        <div className="flex flex-wrap gap-1">
          {tags.map((t, i) => (
            <span key={i} className="chip lowercase tracking-normal font-medium">{String(t)}</span>
          ))}
        </div>
      ) : null}
      {p.enrichment_sources ? (
        <div className="text-muted text-[10px] uppercase tracking-wider">Sources: {String(p.enrichment_sources).replace(/_/g, " ")}</div>
      ) : null}
    </div>
  );
}

function PropertyList({ properties, hideKeys }) {
  const entries = Object.entries(properties || {}).filter(
    ([key]) => !(hideKeys && hideKeys.has(key)),
  );
  if (entries.length === 0) {
    return (
      <div className="w-full flex items-center justify-center bg-bg">
        <div className="text-muted text-xs p-4 border border-dashed border-line rounded-none bg-bg text-center">
          No properties set on this node.
        </div>
      </div>
    );
  }
  return (
    <dl className="grid grid-cols-[100px_1fr] gap-x-2 gap-y-1.5 mb-2 text-xs bg-bg p-2.5 rounded-none border border-line">
      {entries.map(([key, val]) => (
        <React.Fragment key={key}>
          <dt className="text-muted font-bold capitalize">{key}</dt>
          <dd className="m-0 overflow-wrap-anywhere text-ink">{typeof val === 'object' ? JSON.stringify(val) : String(val)}</dd>
        </React.Fragment>
      ))}
    </dl>
  );
}

function ProvenanceList({ provenance }) {
  if (!provenance || provenance.length === 0) {
    return (
      <div className="w-full flex items-center justify-center bg-bg">
        <div className="text-muted text-xs p-4 border border-dashed border-line rounded-none bg-bg text-center">
          No provenance logs available.
        </div>
      </div>
    );
  }
  return (
    <div className="flex flex-col gap-2">
      {provenance.map((item, idx) => {
        const text = typeof item === 'object' ? item.text || item.content || JSON.stringify(item) : String(item);
        return (
          <div key={idx} className="bg-bg border border-line rounded-none p-2 text-xs leading-relaxed">
            <div className="text-primary font-bold mb-1 text-[10px] uppercase tracking-wider">
              Reference Source #{idx + 1} {item.timestamp ? `• ${item.timestamp}` : ''}
            </div>
            <div className="text-ink opacity-85 italic">"{text}"</div>
          </div>
        );
      })}
    </div>
  );
}

async function fetchJson(path, options = {}) {
  if (isDemoMode() && String(path).startsWith("/api/")) {
    return demoFetchJson(path, options);
  }

  const response = await fetch(path, withDashboardAuth(path, options));
  const contentType = response.headers.get("content-type") || "";
  const body = contentType.includes("application/json")
    ? await response.json()
    : { detail: await response.text() };
  if (!response.ok) {
    if (response.status === 401) {
      throw new Error("Invalid or missing dashboard token.");
    }
    throw new Error(body.detail || body.error || response.statusText);
  }
  return body;
}

async function demoFetchJson(path, options = {}) {
  const method = String(options.method || "GET").toUpperCase();
  const url = new URL(path, window.location.origin);
  const segments = url.pathname.split("/").filter(Boolean).map(decodeURIComponent);

  if (method === "GET" && url.pathname === "/api/health") {
    return { status: "ok", mode: "demo" };
  }
  if (method === "GET" && url.pathname === "/api/children") {
    return { children: [DEMO_CHILD_ID] };
  }
  if (segments[0] !== "api" || segments[1] !== "children" || !segments[2]) {
    throw new Error("Demo route is not available.");
  }

  const childId = segments[2] || DEMO_CHILD_ID;
  const action = segments.slice(3);

  if (method === "GET" && action.length === 0) {
    return { children: [DEMO_CHILD_ID] };
  }
  if (method === "GET" && action.join("/") === "summary") {
    return {
      summary: {
        child_id: childId,
        nodes: DEMO_NODES.length,
        edges: DEMO_EDGES.length,
        stale_nodes: DEMO_NODES.filter((node) => node.stale).length,
        faiss_vectors: 0,
        bm25_docs: DEMO_NODES.length,
      },
    };
  }
  if (method === "GET" && action.join("/") === "graph") {
    const startId = url.searchParams.get("start_id");
    if (!startId) {
      return { child_id: childId, nodes: DEMO_NODES, edges: DEMO_EDGES, mode: "all" };
    }
    const connected = new Set([startId]);
    for (const edge of DEMO_EDGES) {
      if (edge.source === startId) connected.add(edge.target);
      if (edge.target === startId) connected.add(edge.source);
    }
    return {
      child_id: childId,
      nodes: DEMO_NODES.filter((node) => connected.has(node.id)),
      edges: DEMO_EDGES.filter((edge) => connected.has(edge.source) && connected.has(edge.target)),
      mode: "traverse",
    };
  }
  if (method === "GET" && action[0] === "nodes" && action[1]) {
    const node = DEMO_NODES.find((item) => item.id === action[1]);
    if (!node) throw new Error(`Node not found: ${action[1]}`);
    const neighbors = await demoFetchJson(`/api/children/${childId}/graph?start_id=${encodeURIComponent(node.id)}`);
    return {
      node,
      provenance: [
        {
          id: `${node.id}-source`,
          timestamp: node.document_date,
          text: node.source_chunk,
        },
      ],
      neighbors,
      convergence: Number((node.confidence * 2).toFixed(2)),
    };
  }
  if (method === "GET" && action.join("/") === "stale") {
    return { nodes: DEMO_NODES.filter((node) => node.stale) };
  }
  if (method === "GET" && action.join("/") === "profile") {
    return {
      profile: {
        child_id: childId,
        name: "Piyush",
        location: "Koramangala, Bengaluru",
        school: "Greenwood High",
        inferred_context: {
          economic_segment: "urban professional",
          commute: "school bus",
          safety_note: "moderate park entrance concern",
        },
        demo: true,
      },
    };
  }
  if (method === "GET" && action.join("/") === "context") {
    return {
      context: {
        child_id: childId,
        summary:
          "Demo context: Piyush is represented as a profile connected to school, neighborhood, commute, visit, safety, and coaching implication nodes.",
        relevant_nodes: DEMO_NODES.map((node) => ({ id: node.id, type: node.type, label: node.label })),
        demo: true,
      },
    };
  }
  if (method === "GET" && action.join("/") === "coaching") {
    return {
      implications: [
        {
          title: "Use school routine as grounding context",
          confidence: 0.7,
          rationale: "School and commute nodes provide stable, non-sensitive context for agent responses.",
        },
      ],
    };
  }
  if (method === "GET" && action.join("/") === "privacy/export") {
    return {
      export: {
        child_id: childId,
        demo: true,
        note: "Public demo mode uses synthetic data only. No real child or user data is exported.",
        nodes: DEMO_NODES.length,
        edges: DEMO_EDGES.length,
      },
    };
  }
  if (method === "DELETE" && action.join("/") === "privacy") {
    return {
      status: "demo_noop",
      child_id: childId,
      note: "Privacy erase is disabled in public demo mode because no real data is stored.",
    };
  }
  if (method === "POST" && action.join("/") === "ingest") {
    const body = readDemoBody(options);
    const text = String(body.text || "").trim();
    if (!text) throw new Error("text is required");
    return {
      result: {
        status: "demo_simulated",
        child_id: childId,
        signals: 3,
        note: "Demo mode simulated ingestion without writing to the backend database.",
        preview: text.slice(0, 160),
      },
    };
  }
  if (method === "POST" && action.join("/") === "person") {
    const body = readDemoBody(options);
    return {
      result: {
        status: "demo_simulated",
        child_id: childId,
        name: body.name || "Demo person",
        note: "Demo mode simulated profile creation without writing to Neo4j.",
      },
    };
  }
  if (method === "POST" && action.join("/") === "episodes/segment") {
    return {
      result: {
        status: "demo_simulated",
        child_id: childId,
        episodes: 2,
        episode_ids: ["demo-episode-school", "demo-episode-visit"],
      },
    };
  }
  if (method === "POST" && action.join("/") === "location/acquire") {
    const body = readDemoBody(options);
    return {
      result: {
        status: "demo_simulated",
        child_id: childId,
        location: "Koramangala, Bengaluru",
        location_resolved: true,
        lat: body.lat,
        lng: body.lng,
        accuracy_m: body.accuracy_m,
        note: "Browser coordinates were not sent to the production API in demo mode.",
      },
    };
  }

  throw new Error("Demo route is not available.");
}

function readDemoBody(options) {
  if (!options?.body) return {};
  try {
    return JSON.parse(options.body);
  } catch (_error) {
    return {};
  }
}

function isDemoMode() {
  return !sessionStorage.getItem(DASHBOARD_TOKEN_KEY)?.trim();
}

function withDashboardAuth(path, options = {}) {
  const headers = new Headers(options.headers || {});
  const token = sessionStorage.getItem(DASHBOARD_TOKEN_KEY);
  if (path !== "/api/health" && token?.trim()) {
    headers.set("Authorization", `Bearer ${token.trim()}`);
  }
  return { ...options, headers };
}

function getHexagonPoints(r) {
  const points = [];
  for (let i = 0; i < 6; i++) {
    const angle = (Math.PI / 180) * (60 * i - 30);
    const x = r * Math.cos(angle);
    const y = r * Math.sin(angle);
    points.push(`${x.toFixed(2)},${y.toFixed(2)}`);
  }
  return points.join(" ");
}

function trimLabel(label) {
  const value = String(label);
  return value.length > 20 ? `${value.slice(0, 17)}...` : value;
}

function errorToText(error) {
  return error instanceof Error ? error.message : String(error);
}

createRoot(document.getElementById("root")).render(<App />);
