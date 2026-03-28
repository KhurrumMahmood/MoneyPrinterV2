const state = {
  bundle: null,
};

const formatDate = (value) => {
  if (!value) return "Not reviewed yet";
  try {
    return new Date(value).toLocaleString();
  } catch {
    return value;
  }
};

const el = (id) => document.getElementById(id);

const renderMetrics = (bundle) => {
  const dossier = bundle.dossier || {};
  const audits = bundle.audits || {};
  const metrics = [
    { label: "Claims", value: dossier.claim_cards?.length || 0 },
    { label: "Strongest", value: dossier.strongest_evidence?.length || 0 },
    { label: "Contradictions", value: dossier.contradictory_evidence?.length || 0 },
    {
      label: "Audit Flags",
      value: Object.values(audits).reduce(
        (sum, audit) => sum + ((audit.issues || audit.findings || []).length || 0),
        0,
      ),
    },
  ];

  el("metrics-grid").innerHTML = metrics
    .map(
      (metric) => `
        <div class="metric-card">
          <div class="metric-value">${metric.value}</div>
          <div class="metric-label">${metric.label}</div>
        </div>
      `,
    )
    .join("");
};

const renderClaims = (bundle) => {
  const claims = bundle.dossier?.claim_cards || [];
  el("claims-grid").innerHTML = claims
    .map(
      (claim) => `
        <article class="claim-card">
          <div class="claim-topline">
            <span class="claim-status">${claim.evidence_label || "unknown"}</span>
            <span class="claim-status muted">${claim.status || "unrated"}</span>
          </div>
          <h3>${claim.claim_text || "Untitled claim"}</h3>
          <p>${claim.recommended_framing || "No approved framing yet."}</p>
          <div class="claim-citations">
            ${(claim.citations || [])
              .slice(0, 3)
              .map(
                (citation) => `
                  <span class="citation-chip">${citation.label || "Citation"}${
                    citation.detail ? `, ${citation.detail}` : ""
                  }</span>
                `,
              )
              .join("")}
          </div>
        </article>
      `,
    )
    .join("");
};

const renderCaveats = (bundle) => {
  const caveats = bundle.dossier?.harms_and_caveats || [];
  el("caveats-list").innerHTML = caveats.length
    ? caveats.map((item) => `<li>${item}</li>`).join("")
    : "<li>No harms or caveats captured yet.</li>";
};

const renderHub = (bundle) => {
  const hub = bundle.topic_hub || {};
  el("hub-summary").innerHTML = `
    <p>${hub.summary || "Topic hub summary unavailable."}</p>
    <div class="stack-row">
      <div>
        <div class="mini-label">Consensus</div>
        <div>${(hub.consensus || []).slice(0, 3).join("<br />") || "No consensus notes yet."}</div>
      </div>
      <div>
        <div class="mini-label">Uncertainties</div>
        <div>${(hub.uncertainties || []).slice(0, 3).join("<br />") || "No uncertainty notes yet."}</div>
      </div>
    </div>
  `;
  el("hub-runs").innerHTML = (hub.runs || [])
    .map((run) => `<span class="meta-pill">${run}</span>`)
    .join("");
};

const formatAuditIssue = (issue) => {
  if (!issue) return "Unknown issue";
  if (typeof issue === "string") return issue;
  return [
    issue.severity ? `[${issue.severity}]` : "",
    issue.claim_id || issue.scene_id || issue.kind || "",
    issue.issue || issue.message || issue.summary || "",
  ]
    .filter(Boolean)
    .join(" ");
};

const renderAudits = (bundle) => {
  const audits = Object.entries(bundle.audits || {});
  el("audit-grid").innerHTML = audits
    .map(([name, audit]) => {
      const issues = audit.issues || audit.findings || [];
      return `
        <article class="audit-card">
          <div class="audit-name">${name}</div>
          <div class="audit-count">${issues.length} issue${issues.length === 1 ? "" : "s"}</div>
          <ul>
            ${
              issues.length
                ? issues
                    .slice(0, 4)
                    .map((issue) => `<li>${formatAuditIssue(issue)}</li>`)
                    .join("")
                : "<li>No issues flagged.</li>"
            }
          </ul>
        </article>
      `;
    })
    .join("");
};

const renderSources = (bundle) => {
  const sources = bundle.dossier?.source_log || [];
  el("sources-list").innerHTML = sources.length
    ? sources
        .slice(0, 20)
        .map(
          (source) => `
            <div class="source-row">
              <div>
                <div class="source-title">${source.title || source.source_id}</div>
                <div class="source-meta">${source.source_type || "source"} • ${
                  source.trust_tier || "unrated"
                }</div>
              </div>
              <div class="source-provenance">${source.provenance || ""}</div>
            </div>
          `,
        )
        .join("")
    : "<div class=\"empty-copy\">No sources loaded.</div>";
};

const renderSuggestions = () => {
  const prompts = [
    "What are the biggest caveats in this package?",
    "Which claim is strongest and why?",
    "What did the researchers disagree on?",
    "What should a viewer definitely not conclude from this?",
  ];
  el("suggestions").innerHTML = prompts
    .map((prompt) => `<button type="button" class="suggestion">${prompt}</button>`)
    .join("");
  document.querySelectorAll(".suggestion").forEach((button) => {
    button.addEventListener("click", () => {
      el("chat-question").value = button.textContent.trim();
      el("chat-form").requestSubmit();
    });
  });
};

const renderChatResponse = (payload) => {
  const response = el("chat-response");
  const citations = payload.citations || [];
  response.classList.remove("empty");
  response.innerHTML = `
    <div class="chat-header">
      <span class="meta-pill">${payload.confidence || "unknown"} confidence</span>
      ${payload.refused ? '<span class="meta-pill warn">Refused</span>' : ""}
    </div>
    <div class="chat-answer">${(payload.answer || "No answer returned.").replaceAll("\n", "<br /><br />")}</div>
    <div class="chat-citations">
      ${citations
        .map(
          (citation) => `
            <div class="citation-line">
              <strong>${citation.claim_ids?.join(", ") || citation.record_id}</strong>
              <span>${citation.source_ids?.join(", ") || "No source ids"}</span>
            </div>
          `,
        )
        .join("")}
    </div>
  `;
};

const loadBundle = async () => {
  const res = await fetch("/api/bundle");
  const bundle = await res.json();
  state.bundle = bundle;

  el("topic-title").textContent = bundle.dossier?.title || bundle.run_id;
  el("topic-summary").textContent =
    bundle.dossier?.summary || "No evidence summary available yet.";
  el("meta-version").textContent = `Version ${bundle.dossier?.version || bundle.run_id}`;
  el("meta-reviewed").textContent = `Reviewed ${formatDate(bundle.dossier?.last_reviewed_at)}`;
  el("meta-run").textContent = bundle.run_id;

  renderMetrics(bundle);
  renderClaims(bundle);
  renderCaveats(bundle);
  renderHub(bundle);
  renderAudits(bundle);
  renderSources(bundle);
  renderSuggestions();
};

document.getElementById("chat-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const question = el("chat-question").value.trim();
  if (!question) return;

  el("chat-response").classList.remove("empty");
  el("chat-response").textContent = "Thinking over the approved package...";

  const res = await fetch(`/api/answer?question=${encodeURIComponent(question)}`);
  const payload = await res.json();
  renderChatResponse(payload);
});

loadBundle().catch((error) => {
  console.error(error);
  el("topic-title").textContent = "Reader failed to load";
  el("topic-summary").textContent = String(error);
});
