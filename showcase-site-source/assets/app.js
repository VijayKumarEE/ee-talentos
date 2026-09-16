/*
  EE TalentOS -> Greenhouse-style showcase
  Single-role (IND - Operability Engineer) demo pipeline.
  Reads /data/candidates.json and renders a Greenhouse-style
  candidate list + candidate detail view. No backend calls from
  here - this file only ever reads the static JSON that the real
  TalentOS backend pushes to this repo.
*/

const DATA_URL = "data/candidates.json";

const STAGE_ORDER = [
  "Application Review",
  "Screening",
  "Take Home Test",
  "Technical Skills Interview",
  "Consulting Skills Interview",
  "Offer",
  "Hired",
];

function fmtDate(iso) {
  const d = new Date(iso + "T00:00:00");
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

function stageIndex(stage) {
  return STAGE_ORDER.indexOf(stage);
}

function recSlug(rec) {
  return (rec || "").toLowerCase().replace(/\s+/g, "");
}

let STATE = null;

async function loadData() {
  if (STATE) return STATE;
  const res = await fetch(DATA_URL, { cache: "no-store" });
  STATE = await res.json();
  return STATE;
}

function renderHeader() {
  return `
    <header class="gh-header">
      <div class="gh-logo"><strong>greenhouse</strong><span>Recruiting</span></div>
      <nav class="gh-nav">
        <a href="#/candidates" class="active">Jobs</a>
        <a href="#/candidates">Candidates</a>
        <a href="#/candidates">Reports</a>
        <a href="#/candidates">Analytics <span class="gh-beta">Beta</span></a>
        <a href="#/candidates">Integrations</a>
      </nav>
      <div class="gh-header-spacer"></div>
      <div class="gh-search">&#128269; Search</div>
      <div class="gh-icon-btn">&#9881;</div>
      <div class="gh-icon-btn">&#63;</div>
      <div class="gh-avatar">EE</div>
    </header>
  `;
}

function renderSidebar(active) {
  const items = ["Job Dashboard", "Sourcing", "Candidates", "Pipeline", "Reports", "Job Setup"];
  return `
    <aside class="gh-sidebar">
      ${items.map(i => `<a class="gh-sidebar-item ${i === active ? "active" : ""}" href="#/candidates">${i}</a>`).join("")}
    </aside>
  `;
}

function pipelineCounts(candidates) {
  const counts = {};
  STAGE_ORDER.forEach(s => counts[s] = 0);
  let rejected = 0;
  candidates.forEach(c => {
    if (c.status === "rejected") { rejected += 1; return; }
    if (counts[c.current_stage] !== undefined) counts[c.current_stage] += 1;
  });
  return { counts, rejected };
}

function renderList(job, candidates) {
  const { counts, rejected } = pipelineCounts(candidates);
  const active = candidates.filter(c => c.status !== "rejected");

  const pipelineHtml = STAGE_ORDER.map(s => `
    <div class="gh-pipeline-stage">
      <div class="n ${counts[s] === 0 ? "zero" : ""}">${counts[s] || "-"}</div>
      <div class="label">${s}</div>
    </div>
  `).join("") + `
    <div class="gh-pipeline-stage">
      <div class="n zero" style="color:var(--gh-red)">${rejected || "-"}</div>
      <div class="label">Rejected</div>
    </div>
  `;

  const rows = candidates.map(c => `
    <tr class="row-link" data-id="${c.id}">
      <td>
        <div class="cand-name">${c.name}</div>
        <div class="cand-sub">${c.current_title} at ${c.current_company}</div>
      </td>
      <td>
        <div class="stage-cell">
          <span class="down">&#8595;</span>
          <span class="stage-name">${c.current_stage}</span> &middot; ${c.note}
        </div>
        <span class="status-tag ${c.status}">${c.status.toUpperCase()}</span>
      </td>
    </tr>
  `).join("");

  return `
    ${renderHeader()}
    <div class="gh-body">
      ${renderSidebar("Candidates")}
      <main class="gh-main">
        <div class="gh-breadcrumb"><a href="#/candidates">All jobs</a></div>
        <div class="gh-title-row">
          <h1 class="gh-title">${job.title}</h1>
          <div class="gh-status-pill"><span class="gh-status-dot"></span>Job Status: ${job.status}</div>
        </div>
        <div class="gh-subtitle">${job.location}</div>

        <div class="gh-pipeline-card">
          <h2>Pipeline</h2>
          <div class="gh-pipeline-row">${pipelineHtml}</div>
        </div>

        <div class="gh-filters">
          <span class="gh-pill">Active <span class="x">&times;</span></span>
          <span class="gh-pill">Open Jobs <span class="x">&times;</span></span>
          <span class="gh-pill">${job.title} <span class="x">&times;</span></span>
        </div>

        <div class="gh-table-toolbar">
          <div class="count">Showing <strong>${candidates.length}</strong> candidate or prospect applications</div>
          <div class="gh-toolbar-actions">
            <button class="gh-btn-outline">Generate Report</button>
            <button class="gh-btn-outline">Add Candidate</button>
          </div>
        </div>

        <table class="gh-table">
          <thead><tr><th>Name</th><th>Job / Status</th></tr></thead>
          <tbody>${rows}</tbody>
        </table>

        <div class="gh-footer-note">Demo data &middot; EE TalentOS showcase, styled to resemble Greenhouse Recruiting. Every candidate here is a fictional persona created for this buildathon demo.</div>
      </main>
    </div>
  `;
}

function stageStatusFor(candidate, stage) {
  const done = candidate.stage_history.find(h => h.stage === stage);
  if (done) {
    if (candidate.status === "rejected" && stage === candidate.current_stage) return "current-rejected";
    if (stage === candidate.current_stage && candidate.status !== "hired") return "current";
    return "done";
  }
  return "upcoming";
}

function renderCompetencyList(competencies) {
  return competencies.map(c => {
    const positives = c.positives.length
      ? `<div class="ev-row ev-positive"><strong>Strengths:</strong> ${c.positives.join("; ")}</div>` : "";
    const gaps = c.gaps.length
      ? `<div class="ev-row ev-gap"><strong>Gaps:</strong> ${c.gaps.join("; ")}</div>` : "";
    const flags = c.risk_flags.length
      ? `<div class="ev-row ev-flag"><strong>Flags:</strong> ${c.risk_flags.join("; ")}</div>` : "";
    const followUps = c.follow_up_questions.length
      ? `<div class="ev-row"><strong>Follow-up:</strong> ${c.follow_up_questions.join(" / ")}</div>` : "";
    return `
      <div class="comp-detail">
        <div class="comp-detail-head">
          <span class="comp-name">${c.name}<span class="comp-tag">${c.type}</span></span>
          <span class="comp-score">${c.score.toFixed(1)} / 5 &middot; ${c.level}</span>
        </div>
        ${c.summary ? `<div class="comp-summary">${c.summary}</div>` : ""}
        ${positives}${gaps}${flags}${followUps}
      </div>
    `;
  }).join("");
}

function renderStageDetail(historyItem) {
  const detail = historyItem && historyItem.detail;
  if (!detail) return "";

  if (detail.type === "ai_report") {
    return `
      <div class="stage-detail">
        <div class="stage-detail-title">AI Assessment Report</div>
        <div class="scorecard-summary">
          <span class="rec-pill ${recSlug(detail.overall_recommendation)}">${detail.overall_recommendation}</span>
          <span class="overall-score">Overall AI score: ${detail.overall_score.toFixed(1)} / 5</span>
        </div>
        ${renderCompetencyList(detail.competencies)}
        ${detail.notes ? `<div class="recruiter-note">${detail.notes}</div>` : ""}
      </div>
    `;
  }

  if (detail.type === "recruiter_review") {
    const decisionLabel = detail.decision === "advance" ? "Advanced" : "Not advanced";
    return `
      <div class="stage-detail">
        <div class="stage-detail-title">Recruiter Screen Outcome</div>
        <div class="scorecard-summary">
          <span class="rec-pill ${detail.decision === "advance" ? "strongyes" : "no"}">${decisionLabel}</span>
          ${detail.recruiter_score != null ? `<span class="overall-score">Recruiter score: ${detail.recruiter_score.toFixed(1)} / 5</span>` : ""}
        </div>
        ${detail.recruiter_notes ? `<div class="recruiter-note"><strong>Recruiter notes:</strong> ${detail.recruiter_notes}</div>` : ""}
      </div>
    `;
  }

  if (detail.type === "status") {
    return `
      <div class="stage-detail stage-detail-status">
        ${detail.message}
      </div>
    `;
  }

  return "";
}

function renderDetail(job, candidate) {
  const stagesToShow = candidate.status === "rejected"
    ? STAGE_ORDER.slice(0, stageIndex(candidate.current_stage) + 1)
    : STAGE_ORDER;

  const stageRows = stagesToShow.map((s, i) => {
    const state = stageStatusFor(candidate, s);
    const hist = candidate.stage_history.find(h => h.stage === s);
    let badge = "";
    if (state === "current") badge = `<span class="current-badge">Current stage</span>`;
    if (state === "current-rejected") badge = `<span class="current-badge" style="background:var(--gh-red)">Rejected here</span>`;
    return `
      <div class="stage-row">
        <div class="stage-row-head">
          <span class="tri">&#9656;</span>
          ${i + 1}. ${s}
          ${hist ? `<span class="date">${fmtDate(hist.date)}</span>` : ""}
          ${badge}
        </div>
        ${renderStageDetail(hist)}
      </div>
    `;
  }).join("");

  return `
    ${renderHeader()}
    <div class="gh-body">
      <main class="gh-main" style="max-width:1180px">
        <div class="gh-breadcrumb">
          <a href="#/candidates">All jobs</a><span class="sep">&gt;</span>
          <a href="#/candidates">${job.title} / ${job.location} / ${job.department}</a><span class="sep">&gt;</span>
          ${candidate.name}
        </div>

        <div class="cand-header">
          <div>
            <h1 class="cand-title">${candidate.name}</h1>
            <div class="cand-contact">${candidate.email}<span class="dot">&middot;</span>${candidate.phone}</div>
            <div class="cand-actions">
              <span class="icon-circle">&#128203;</span>
              <span class="icon-circle">&#9993;</span>
              <span class="icon-circle">+</span>
              <span class="icon-circle">&#8635;</span>
              <button class="btn-reject">Reject</button>
              <button class="btn-move">Move stage</button>
              <span class="icon-circle">&#8943;</span>
            </div>
          </div>
        </div>

        <div class="cand-body">
          <div class="cand-tabs">
            <a class="cand-tab active" href="#">Stages</a>
            <a class="cand-tab" href="#">Scorecards</a>
            <a class="cand-tab" href="#">Offer details</a>
            <a class="cand-tab" href="#">Activity feed</a>
          </div>

          <div class="cand-main">${stageRows}</div>

          <aside class="cand-side">
            <h3>${candidate.name.split(" ")[0]}'s details</h3>
            <div class="side-field"><div class="k">Current job title &amp; company</div><div class="v">${candidate.current_title} @ ${candidate.current_company}</div></div>
            <div class="side-field"><div class="k">Email address</div><div class="v">${candidate.email}</div></div>
            <div class="side-field"><div class="k">Phone number</div><div class="v">${candidate.phone}</div></div>
            <div class="side-field"><div class="k">Total experience</div><div class="v">${candidate.years_experience} years</div></div>
            <div class="side-field"><div class="k">Applied</div><div class="v">${fmtDate(candidate.applied_date)}</div></div>

            <div class="resume-card">
              <div class="resume-icon">PDF</div>
              <div>
                <div class="name">${candidate.name.replace(" ", "_")}_Resume.pdf</div>
                <div class="type">Resume</div>
              </div>
            </div>

            <div class="side-field"><div class="k">Education</div><div class="v muted">No school specified</div></div>
          </aside>
        </div>

        <div class="gh-footer-note">Demo data &middot; EE TalentOS showcase, styled to resemble Greenhouse Recruiting. This is a fictional persona created for this buildathon demo.</div>
      </main>
    </div>
  `;
}

async function render() {
  const root = document.getElementById("view-root");
  const { job, candidates } = await loadData();
  const hash = location.hash || "#/candidates";

  if (hash.startsWith("#/candidate/")) {
    const id = decodeURIComponent(hash.split("/")[2]);
    const candidate = candidates.find(c => c.id === id);
    if (!candidate) { location.hash = "#/candidates"; return; }
    root.innerHTML = renderDetail(job, candidate);
  } else {
    root.innerHTML = renderList(job, candidates);
    root.querySelectorAll("tr.row-link").forEach(row => {
      row.addEventListener("click", () => {
        location.hash = `#/candidate/${encodeURIComponent(row.dataset.id)}`;
      });
    });
  }
}

window.addEventListener("hashchange", render);
window.addEventListener("DOMContentLoaded", render);
