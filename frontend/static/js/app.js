/**
 * Business Entity Resolution - Commercial Operations Controller
 * Pure vanilla JavaScript with zero dummy data and direct SQLite/ML integration.
 */

document.addEventListener("DOMContentLoaded", () => {
  // Navigation elements
  const navItems = document.querySelectorAll(".nav-item");
  const tabPanels = document.querySelectorAll(".tab-panel");
  const topbarBreadcrumb = document.getElementById("topbar-breadcrumb");
  const topbarAnalyst = document.getElementById("topbar-analyst");

  // Home Quick Action Buttons
  const heroBtnSearch = document.getElementById("hero-btn-search");
  const heroBtnBatch = document.getElementById("hero-btn-batch");
  const heroBtnUpload = document.getElementById("hero-btn-upload");

  // Search elements
  const searchInput = document.getElementById("search-input-box");
  const searchCountrySelect = document.getElementById("search-country-select");
  const btnDoSearch = document.getElementById("btn-do-search");
  const searchResultsStatus = document.getElementById("search-results-status");
  const searchResultsList = document.getElementById("search-results-list");

  // Matching Workspace Profile elements
  const profileBname = document.getElementById("profile-bname");
  const profileIdPill = document.getElementById("profile-id-pill");
  const profileStatus = document.getElementById("profile-status");
  const s1FieldId = document.getElementById("s1-field-id");
  const s1FieldName = document.getElementById("s1-field-name");
  const s1FieldAddr = document.getElementById("s1-field-addr");
  const s1FieldCtry = document.getElementById("s1-field-ctry");
  const btnReRunMatching = document.getElementById("btn-re-run-matching");
  const btnNextBusinessTop = document.getElementById("btn-next-business-top");
  const btnNextInline = document.getElementById("btn-next-inline");

  // Candidates & Comparison elements
  const candidatesCountSummary = document.getElementById("candidates-count-summary");
  const candidatesRankedList = document.getElementById("candidates-ranked-list");
  const comparisonSection = document.getElementById("comparison-section");
  const comparisonOverallBadge = document.getElementById("comparison-overall-badge");
  const thCandidateHeader = document.getElementById("th-candidate-header");
  const compS1Name = document.getElementById("comp-s1-name");
  const compCandName = document.getElementById("comp-cand-name");
  const compS1Addr = document.getElementById("comp-s1-addr");
  const compCandAddr = document.getElementById("comp-cand-addr");
  const compS1Ctry = document.getElementById("comp-s1-ctry");
  const compCandCtry = document.getElementById("comp-cand-ctry");
  const evidenceBulletsList = document.getElementById("evidence-bullets-list");

  // Decision buttons
  const btnConfirmMatch = document.getElementById("btn-confirm-match");
  const btnRejectMatch = document.getElementById("btn-reject-match");
  const btnReviewLater = document.getElementById("btn-review-later");

  // Review Queue elements
  const queueTabs = document.querySelectorAll("[data-queue-filter]");
  const queueItemsContainer = document.getElementById("queue-items-container");
  const btnSeedQueue = document.getElementById("btn-seed-queue");

  // Batch Matching elements
  const btnStartBatch = document.getElementById("btn-start-batch");
  const batchProgressContainer = document.getElementById("batch-progress-container");
  const batchProgressFill = document.getElementById("batch-progress-fill");
  const batchProgressPct = document.getElementById("batch-progress-pct");
  const batchProgressLabel = document.getElementById("batch-progress-label");
  const batchResultsBox = document.getElementById("batch-results-box");
  const batchResTotal = document.getElementById("batch-res-total");
  const batchResMatches = document.getElementById("batch-res-matches");
  const batchResNoMatches = document.getElementById("batch-res-nomatches");
  const btnBatchReviewResults = document.getElementById("btn-batch-review-results");

  // Resolved Entities elements
  const resolvedTabs = document.querySelectorAll("[data-resolved-filter]");
  const resolvedTableBody = document.getElementById("resolved-table-body");

  // History elements
  const historyFeedContainer = document.getElementById("history-feed-container");

  // Settings elements
  const settingThresholdRange = document.getElementById("setting-threshold-range");
  const settingThresholdVal = document.getElementById("setting-threshold-val");
  const settingCandLimit = document.getElementById("setting-cand-limit");
  const settingSearchLimit = document.getElementById("setting-search-limit");
  const settingAnalystName = document.getElementById("setting-analyst-name");
  const btnSaveSettings = document.getElementById("btn-save-settings");

  // Active state
  let currentS1Record = null;
  let currentCandidates = [];
  let currentSelectedCandidate = null;
  let currentNextId = null;
  let activeAnalyst = "Operations Lead";

  // ── Toast Notification Helper ─────────────────────────────────────────────
  function showToast(message, type = "success") {
    const container = document.getElementById("toast-container");
    const toast = document.createElement("div");
    toast.className = "toast";
    const icon = type === "success" ? "✓" : (type === "warning" ? "⚠️" : "ℹ️");
    toast.innerHTML = `<span>${icon}</span> <span>${message}</span>`;
    container.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = "0";
      setTimeout(() => toast.remove(), 200);
    }, 3200);
  }

  // ── Tab Navigation ────────────────────────────────────────────────────────
  function switchTab(tabId, title) {
    navItems.forEach(item => {
      item.classList.toggle("active", item.getAttribute("data-tab") === tabId);
    });
    tabPanels.forEach(panel => {
      panel.classList.toggle("active", panel.id === tabId);
    });
    if (title && topbarBreadcrumb) {
      topbarBreadcrumb.textContent = title;
    }

    // Refresh tab content
    if (tabId === "tab-home") {
      loadKpis();
    } else if (tabId === "tab-search") {
      if (searchResultsList.children.length === 0) performSearch();
    } else if (tabId === "tab-queue") {
      loadReviewQueue("all");
    } else if (tabId === "tab-resolved") {
      loadResolvedEntities("all");
    } else if (tabId === "tab-history") {
      loadHistory();
    } else if (tabId === "tab-settings") {
      loadSettings();
      loadEvaluationMetrics();
    }
  }

  navItems.forEach(item => {
    item.addEventListener("click", () => {
      const tabId = item.getAttribute("data-tab");
      const title = item.querySelector("span:last-child").textContent;
      switchTab(tabId, title);
    });
  });

  // Hero action buttons
  heroBtnSearch.addEventListener("click", () => switchTab("tab-search", "Entity Search"));
  heroBtnBatch.addEventListener("click", () => switchTab("tab-batch", "Batch Matching"));
  heroBtnUpload.addEventListener("click", () => switchTab("tab-batch", "Batch Matching"));

  // ── Operational KPIs Loader ───────────────────────────────────────────────
  async function loadKpis() {
    try {
      const res = await fetch("/api/kpis");
      const data = await res.json();
      if (data.success && data.kpis) {
        document.getElementById("kpi-pending").textContent = data.kpis.pending_reviews.toLocaleString();
        document.getElementById("kpi-confirmed").textContent = data.kpis.confirmed_matches.toLocaleString();
        document.getElementById("kpi-rejected").textContent = data.kpis.rejected_matches.toLocaleString();
        document.getElementById("kpi-today").textContent = data.kpis.today_processed.toLocaleString();
      }
    } catch (e) {
      console.error("Error loading KPIs:", e);
    }
  }

  // ── Entity Search ─────────────────────────────────────────────────────────
  async function loadCountries() {
    try {
      const res = await fetch("/api/source1/countries");
      const data = await res.json();
      if (data.success && data.countries) {
        searchCountrySelect.innerHTML = '<option value="">Country: All Countries</option>';
        data.countries.forEach(c => {
          const opt = document.createElement("option");
          opt.value = c;
          opt.textContent = `Country: ${c}`;
          searchCountrySelect.appendChild(opt);
        });
      }
    } catch (e) {
      console.error("Error loading countries:", e);
    }
  }

  async function performSearch() {
    const q = searchInput.value.trim();
    const country = searchCountrySelect.value.trim();

    searchResultsList.innerHTML = '<div class="empty-box"><p>Searching reference records in SQLite...</p></div>';
    searchResultsStatus.textContent = "Querying...";

    try {
      const url = `/api/source1/search?q=${encodeURIComponent(q)}&country=${encodeURIComponent(country)}&limit=25`;
      const res = await fetch(url);
      const data = await res.json();

      if (!data.success || !data.results || data.results.length === 0) {
        searchResultsList.innerHTML = `
          <div class="empty-box">
            <p>No reference businesses found matching "${q}". Try another keyword or country filter.</p>
          </div>
        `;
        searchResultsStatus.textContent = "0 entities found.";
        return;
      }

      searchResultsStatus.textContent = `Showing ${data.results.length} reference entities.`;
      searchResultsList.innerHTML = "";

      data.results.forEach(rec => {
        const card = document.createElement("div");
        card.className = "record-card";
        card.innerHTML = `
          <div class="record-info-main">
            <div class="record-title">
              <span>${rec.business_name}</span>
              <span class="entity-id-pill">${rec.entity_id}</span>
            </div>
            <div class="record-meta">
              <span>${rec.business_address || '(No address specified)'}</span>
              <span class="entity-id-pill">${rec.country}</span>
            </div>
          </div>
          <div>
            <button class="btn btn-primary btn-sm btn-select-record">
              Review Matches &rarr;
            </button>
          </div>
        `;

        card.querySelector(".btn-select-record").addEventListener("click", () => {
          openBusinessProfile(rec);
        });

        searchResultsList.appendChild(card);
      });
    } catch (e) {
      searchResultsList.innerHTML = `<div class="empty-box"><p class="text-error">Error: ${e.message}</p></div>`;
    }
  }

  btnDoSearch.addEventListener("click", performSearch);
  searchInput.addEventListener("keypress", (e) => {
    if (e.key === "Enter") performSearch();
  });
  searchCountrySelect.addEventListener("change", performSearch);

  // ── Business Profile & Matching Execution ─────────────────────────────────
  async function openBusinessProfile(record) {
    currentS1Record = record;
    profileBname.textContent = record.business_name;
    profileIdPill.textContent = record.entity_id;
    profileStatus.textContent = "Pending Review";
    profileStatus.className = "badge badge-neutral";

    s1FieldId.textContent = record.entity_id;
    s1FieldName.textContent = record.business_name;
    s1FieldAddr.textContent = record.business_address || "(No address specified)";
    s1FieldCtry.textContent = record.country;

    switchTab("tab-matching", "Matching Workspace");

    // Fetch next sequential entity ID for continuous workflow
    try {
      const res = await fetch(`/api/source1/next/${encodeURIComponent(record.entity_id)}`);
      const nextData = await res.json();
      currentNextId = nextData.next_id;
    } catch (e) {
      currentNextId = null;
    }

    // Automatically execute real-time matching
    runMatchingForCurrentProfile();
  }

  async function runMatchingForCurrentProfile() {
    if (!currentS1Record) return;

    btnReRunMatching.disabled = true;
    btnReRunMatching.innerHTML = "<span>⏳</span> Finding Matches...";
    candidatesCountSummary.textContent = "Executing normalization, candidate blocking against S2 & S3, and ML inference...";
    candidatesRankedList.innerHTML = '<div class="empty-box"><p>Searching for potential candidates...</p></div>';
    comparisonSection.style.display = "none";

    const thresh = parseFloat(settingThresholdRange ? settingThresholdRange.value : 0.95);

    try {
      const res = await fetch("/api/match", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          entity_id: currentS1Record.entity_id,
          business_name: currentS1Record.business_name,
          business_address: currentS1Record.business_address,
          country: currentS1Record.country,
          threshold: thresh
        })
      });

      const response = await res.json();
      btnReRunMatching.disabled = false;
      btnReRunMatching.innerHTML = "<span>⚡</span> Find Matches";

      if (!response.success) {
        throw new Error(response.error || "Matching request failed.");
      }

      renderCandidatesList(response.data);
    } catch (e) {
      btnReRunMatching.disabled = false;
      btnReRunMatching.innerHTML = "<span>⚡</span> Find Matches";
      candidatesRankedList.innerHTML = `<div class="empty-box"><p class="text-error">Matching Error: ${e.message}</p></div>`;
      candidatesCountSummary.textContent = "Error running matching engine.";
    }
  }

  btnReRunMatching.addEventListener("click", runMatchingForCurrentProfile);

  function renderCandidatesList(matchData) {
    currentCandidates = matchData.all_candidates || [];
    const count = currentCandidates.length;

    if (count === 0) {
      candidatesCountSummary.textContent = "0 candidates identified.";
      candidatesRankedList.innerHTML = `
        <div class="empty-box" style="padding: 24px 14px; text-align: left; background: var(--bg-card-secondary); border-radius: var(--radius-sm); border: 1px solid var(--border-color);">
          <div style="font-weight: 600; color: var(--text-primary); margin-bottom: 6px;">No reliable match found</div>
          <div style="font-size: 0.83rem; color: var(--text-secondary); line-height: 1.4;">
            The business appears to be a singleton reference entity or no candidates met indexing criteria.
          </div>
          <div style="margin-top: 14px;">
            <button id="btn-singleton-not-a-match" class="btn btn-secondary btn-sm">
              <span>✕</span> Confirm No Match (Singleton)
            </button>
          </div>
        </div>
      `;

      const btnSingleton = document.getElementById("btn-singleton-not-a-match");
      if (btnSingleton) {
        btnSingleton.addEventListener("click", () => {
          recordAnalystDecision("rejected", null, 0.0, "Verified as singleton reference entity");
        });
      }
      comparisonSection.style.display = "none";
      return;
    }

    candidatesCountSummary.textContent = `${count} potential candidate(s) found across Source 2 and Source 3. Select a candidate below to compare:`;
    candidatesRankedList.innerHTML = "";

    currentCandidates.forEach((cand, idx) => {
      const item = document.createElement("div");
      item.className = "candidate-card-item";
      if (idx === 0) item.classList.add("selected");

      item.innerHTML = `
        <div>
          <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 3px;">
            <span style="font-weight: 700; font-size: 0.82rem; color: var(--text-muted);">${idx + 1}.</span>
            <span class="entity-id-pill">${cand.target_id}</span>
            <span class="badge ${cand.badge_class}">${cand.confidence_tier} (${cand.confidence_pct}%)</span>
          </div>
          <div style="font-size: 0.95rem; font-weight: 600; color: var(--text-primary);">
            ${cand.business_name}
          </div>
          <div style="font-size: 0.8rem; color: var(--text-secondary);">
            ${cand.business_address || '(No address recorded)'} • <span class="entity-id-pill">${cand.country}</span>
          </div>
        </div>
        <div>
          <button class="btn btn-secondary btn-sm btn-select-cand">
            Select
          </button>
        </div>
      `;

      item.addEventListener("click", () => {
        document.querySelectorAll(".candidate-card-item").forEach(el => el.classList.remove("selected"));
        item.classList.add("selected");
        selectCandidateForComparison(cand);
      });

      candidatesRankedList.appendChild(item);
    });

    // Auto-select top candidate
    selectCandidateForComparison(currentCandidates[0]);
  }

  function selectCandidateForComparison(cand) {
    currentSelectedCandidate = cand;
    comparisonSection.style.display = "block";

    // Side-by-side attributes
    thCandidateHeader.innerHTML = `${cand.target_source} <span class="entity-id-pill">${cand.target_id}</span>`;
    compS1Name.textContent = currentS1Record.business_name;
    compCandName.textContent = cand.business_name;

    compS1Addr.textContent = currentS1Record.business_address || "(No address specified)";
    compCandAddr.textContent = cand.business_address || "(No address recorded)";

    compS1Ctry.textContent = currentS1Record.country;
    compCandCtry.textContent = cand.country;

    // Confidence badge
    comparisonOverallBadge.innerHTML = `
      <span class="badge ${cand.badge_class}" style="font-size: 0.85rem; padding: 5px 12px;">
        ${cand.confidence_pct}% Confidence (${cand.confidence_tier})
      </span>
    `;

    // Evidence bullets
    evidenceBulletsList.innerHTML = "";
    cand.evidence_bullets.forEach(bullet => {
      const li = document.createElement("li");
      if (bullet.startsWith("✓")) {
        li.className = "match-bullet";
      } else {
        li.className = "diff-bullet";
      }
      li.textContent = bullet;
      evidenceBulletsList.appendChild(li);
    });

    // Scroll smoothly to comparison
    comparisonSection.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  // ── Match Decision Actions ────────────────────────────────────────────────
  async function recordAnalystDecision(decisionType, cand = currentSelectedCandidate, conf = 0.0, notes = "") {
    if (!currentS1Record) return;

    const payload = {
      s1_id: currentS1Record.entity_id,
      s1_name: currentS1Record.business_name,
      decision: decisionType,
      candidate_id: cand ? cand.target_id : null,
      candidate_source: cand ? cand.target_source : null,
      candidate_name: cand ? cand.business_name : null,
      confidence: cand ? cand.confidence_score : conf,
      notes: notes,
      analyst: activeAnalyst
    };

    try {
      const res = await fetch("/api/decision", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const data = await res.json();

      if (data.success) {
        showToast(data.message, decisionType === "confirmed" ? "success" : "warning");
        profileStatus.textContent = decisionType.replace("_", " ").toUpperCase();
        profileStatus.className = decisionType === "confirmed" ? "badge badge-high" : (decisionType === "rejected" ? "badge badge-possible" : "badge badge-likely");

        currentNextId = data.next_id;
        loadKpis();

        // If user wants, advance to next business
        if (currentNextId) {
          btnNextBusinessTop.style.display = "inline-flex";
          btnNextInline.style.display = "inline-flex";
        }
      } else {
        showToast(data.error || "Decision error", "warning");
      }
    } catch (e) {
      showToast("Failed to record decision: " + e.message, "warning");
    }
  }

  btnConfirmMatch.addEventListener("click", () => {
    recordAnalystDecision("confirmed");
  });

  btnRejectMatch.addEventListener("click", () => {
    recordAnalystDecision("rejected");
  });

  btnReviewLater.addEventListener("click", () => {
    recordAnalystDecision("review_later");
  });

  async function advanceToNextBusiness() {
    if (!currentNextId) {
      showToast("Reached end of sequential records. Returning to Search.");
      switchTab("tab-search", "Entity Search");
      return;
    }

    try {
      const res = await fetch(`/api/source1/${encodeURIComponent(currentNextId)}`);
      const data = await res.json();
      if (data.success && data.record) {
        openBusinessProfile(data.record);
      } else {
        switchTab("tab-search", "Entity Search");
      }
    } catch (e) {
      switchTab("tab-search", "Entity Search");
    }
  }

  btnNextBusinessTop.addEventListener("click", advanceToNextBusiness);
  btnNextInline.addEventListener("click", advanceToNextBusiness);

  // ── Review Queue ──────────────────────────────────────────────────────────
  async function loadReviewQueue(filter = "all") {
    queueItemsContainer.innerHTML = '<div class="empty-box"><p>Loading review queue...</p></div>';

    try {
      const res = await fetch(`/api/queue?filter=${encodeURIComponent(filter)}&limit=50`);
      const data = await res.json();

      if (!data.success || !data.queue || data.queue.length === 0) {
        queueItemsContainer.innerHTML = `
          <div class="empty-box">
            <p>No items pending in the "${filter}" review queue.</p>
            <p style="font-size:0.8rem; margin-top:6px;">Click 'Load Pending Records' to populate the queue with reference entities.</p>
          </div>
        `;
        return;
      }

      queueItemsContainer.innerHTML = "";
      data.queue.forEach(item => {
        const confPct = Math.round(item.highest_confidence * 100);
        const badgeClass = confPct >= 90 ? "badge-high" : (confPct >= 70 ? "badge-likely" : "badge-possible");

        const card = document.createElement("div");
        card.className = "record-card";
        card.innerHTML = `
          <div class="record-info-main">
            <div class="record-title">
              <span>${item.s1_name}</span>
              <span class="entity-id-pill">${item.s1_id}</span>
              <span class="badge ${badgeClass}">${confPct}% Highest Confidence</span>
            </div>
            <div class="record-meta">
              <span>${item.s1_address || '(No address recorded)'}</span>
              <span class="entity-id-pill">${item.country}</span>
              <span>Potential candidates: ${item.candidates_count}</span>
            </div>
          </div>
          <div>
            <button class="btn btn-primary btn-sm btn-queue-review">
              Review &rarr;
            </button>
          </div>
        `;

        card.querySelector(".btn-queue-review").addEventListener("click", async () => {
          const s1Res = await fetch(`/api/source1/${encodeURIComponent(item.s1_id)}`);
          const s1Data = await s1Res.json();
          if (s1Data.success && s1Data.record) {
            openBusinessProfile(s1Data.record);
          }
        });

        queueItemsContainer.appendChild(card);
      });
    } catch (e) {
      queueItemsContainer.innerHTML = `<div class="empty-box"><p class="text-error">Queue Error: ${e.message}</p></div>`;
    }
  }

  queueTabs.forEach(tab => {
    tab.addEventListener("click", () => {
      queueTabs.forEach(t => t.classList.remove("active"));
      tab.classList.add("active");
      loadReviewQueue(tab.getAttribute("data-queue-filter"));
    });
  });

  btnSeedQueue.addEventListener("click", async () => {
    btnSeedQueue.disabled = true;
    btnSeedQueue.textContent = "Loading...";
    try {
      const res = await fetch("/api/queue/seed", { method: "POST" });
      const data = await res.json();
      if (data.success) {
        showToast(`Enqueued ${data.enqueued} reference records.`);
        loadReviewQueue("all");
        loadKpis();
      }
    } catch (e) {
      showToast("Error loading records: " + e.message, "warning");
    } finally {
      btnSeedQueue.disabled = false;
      btnSeedQueue.textContent = "+ Load Pending Records";
    }
  });

  // ── Batch Matching ────────────────────────────────────────────────────────
  btnStartBatch.addEventListener("click", () => {
    btnStartBatch.disabled = true;
    batchProgressContainer.style.display = "block";
    batchResultsBox.style.display = "none";
    batchProgressFill.style.width = "0%";
    batchProgressPct.textContent = "0%";
    batchProgressLabel.textContent = "Loading Source 1 records & generating candidates...";

    let progress = 0;
    const interval = setInterval(() => {
      progress += Math.floor(Math.random() * 15) + 10;
      if (progress > 95) progress = 95;
      batchProgressFill.style.width = progress + "%";
      batchProgressPct.textContent = progress + "%";
      if (progress > 50) batchProgressLabel.textContent = "Executing ML model inference on candidate pairs...";
    }, 200);

    fetch("/api/batch/run", { method: "POST" })
      .then(res => res.json())
      .then(data => {
        clearInterval(interval);
        batchProgressFill.style.width = "100%";
        batchProgressPct.textContent = "100%";
        batchProgressLabel.textContent = "Batch Matching Complete!";

        setTimeout(() => {
          btnStartBatch.disabled = false;
          batchProgressContainer.style.display = "none";
          batchResultsBox.style.display = "block";

          batchResTotal.textContent = data.total_records.toLocaleString();
          batchResMatches.textContent = data.potential_matches.toLocaleString();
          batchResNoMatches.textContent = data.no_matches.toLocaleString();
          loadKpis();
          showToast("Batch resolution completed successfully.");
        }, 500);
      })
      .catch(e => {
        clearInterval(interval);
        btnStartBatch.disabled = false;
        batchProgressLabel.textContent = "Batch error: " + e.message;
      });
  });

  btnBatchReviewResults.addEventListener("click", () => {
    switchTab("tab-search", "Entity Search");
  });

  // ── Resolved Entities ─────────────────────────────────────────────────────
  async function loadResolvedEntities(filter = "all") {
    resolvedTableBody.innerHTML = '<tr><td colspan="7" class="empty-box">Loading resolutions...</td></tr>';
    try {
      const res = await fetch(`/api/resolved?filter=${encodeURIComponent(filter)}&limit=50`);
      const data = await res.json();

      if (!data.success || !data.records || data.records.length === 0) {
        resolvedTableBody.innerHTML = '<tr><td colspan="7" class="empty-box">No resolved entities recorded yet.</td></tr>';
        return;
      }

      resolvedTableBody.innerHTML = "";
      data.records.forEach(r => {
        const tr = document.createElement("tr");
        const decBadge = r.decision === "confirmed" ? "badge-high" : (r.decision === "rejected" ? "badge-possible" : "badge-likely");
        const confText = r.confidence ? `${Math.round(r.confidence * 100)}%` : "--";

        tr.innerHTML = `
          <td><strong>${r.s1_name}</strong></td>
          <td><span class="entity-id-pill">${r.s1_id}</span></td>
          <td>${r.candidate_id ? `<span class="entity-id-pill">${r.candidate_id}</span> (${r.candidate_name || ''})` : '<span style="color:var(--text-muted);">(None / Singleton)</span>'}</td>
          <td><span class="badge ${decBadge}">${r.decision.replace('_', ' ').toUpperCase()}</span></td>
          <td><strong>${confText}</strong></td>
          <td>${r.analyst || 'Analyst'}</td>
          <td style="color:var(--text-muted); font-size:0.8rem;">${r.created_at}</td>
        `;
        resolvedTableBody.appendChild(tr);
      });
    } catch (e) {
      resolvedTableBody.innerHTML = `<tr><td colspan="7" class="empty-box text-error">Error: ${e.message}</td></tr>`;
    }
  }

  resolvedTabs.forEach(tab => {
    tab.addEventListener("click", () => {
      resolvedTabs.forEach(t => t.classList.remove("active"));
      tab.classList.add("active");
      loadResolvedEntities(tab.getAttribute("data-resolved-filter"));
    });
  });

  // ── Business History ──────────────────────────────────────────────────────
  async function loadHistory() {
    historyFeedContainer.innerHTML = '<div class="empty-box"><p>Loading audit history...</p></div>';
    try {
      const res = await fetch("/api/history?limit=50");
      const data = await res.json();

      if (!data.success || !data.history || data.history.length === 0) {
        historyFeedContainer.innerHTML = '<div class="empty-box"><p>No activity logged yet today.</p></div>';
        return;
      }

      historyFeedContainer.innerHTML = "";
      data.history.forEach(item => {
        const row = document.createElement("div");
        row.style.cssText = "padding: 12px 16px; border-bottom: 1px solid var(--border-color); display: flex; justify-content: space-between; align-items: center;";
        const timePart = item.created_at ? item.created_at.substring(11, 16) : "--:--";

        row.innerHTML = `
          <div style="display:flex; align-items:center; gap: 14px;">
            <span style="font-family:ui-monospace, monospace; font-size:0.82rem; color:var(--text-muted);">${timePart}</span>
            <div>
              <div style="font-weight:600; font-size:0.9rem; color:var(--text-primary);">
                ${item.s1_id ? `<span class="entity-id-pill" style="margin-right:6px;">${item.s1_id}</span>` : ''}
                ${item.business_name || 'System'}
              </div>
              <div style="font-size:0.8rem; color:var(--text-secondary); margin-top:2px;">
                ${item.details}
              </div>
            </div>
          </div>
          <span class="badge badge-neutral">${item.action_type.replace('_', ' ').toUpperCase()}</span>
        `;
        historyFeedContainer.appendChild(row);
      });
    } catch (e) {
      historyFeedContainer.innerHTML = `<div class="empty-box"><p class="text-error">Error: ${e.message}</p></div>`;
    }
  }

  // ── Settings & Technical Evaluation ───────────────────────────────────────
  async function loadSettings() {
    try {
      const res = await fetch("/api/settings");
      const data = await res.json();
      if (data.success && data.settings) {
        const s = data.settings;
        if (s.matching_threshold) {
          settingThresholdRange.value = s.matching_threshold;
          settingThresholdVal.textContent = parseFloat(s.matching_threshold).toFixed(2);
        }
        if (s.candidate_limit) settingCandLimit.value = s.candidate_limit;
        if (s.search_limit) settingSearchLimit.value = s.search_limit;
        if (s.analyst_name) {
          settingAnalystName.value = s.analyst_name;
          activeAnalyst = s.analyst_name;
          topbarAnalyst.textContent = `Analyst: ${s.analyst_name}`;
        }
      }
    } catch (e) {
      console.error("Settings load error:", e);
    }
  }

  if (settingThresholdRange) {
    settingThresholdRange.addEventListener("input", () => {
      settingThresholdVal.textContent = parseFloat(settingThresholdRange.value).toFixed(2);
    });
  }

  btnSaveSettings.addEventListener("click", async () => {
    const payload = {
      matching_threshold: settingThresholdRange.value,
      candidate_limit: settingCandLimit.value,
      search_limit: settingSearchLimit.value,
      analyst_name: settingAnalystName.value.trim() || "Operations Lead"
    };

    try {
      const res = await fetch("/api/settings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (data.success) {
        showToast("Settings saved to database.");
        activeAnalyst = payload.analyst_name;
        topbarAnalyst.textContent = `Analyst: ${activeAnalyst}`;
        loadKpis();
      }
    } catch (e) {
      showToast("Error saving settings: " + e.message, "warning");
    }
  });

  async function loadEvaluationMetrics() {
    const gridBody = document.getElementById("perf-grid-body");
    try {
      const res = await fetch("/api/evaluation");
      const data = await res.json();
      if (data.has_evaluation) {
        document.getElementById("perf-recall").textContent = data.candidate_recall;
        document.getElementById("perf-precision").textContent = (data.precision * 100).toFixed(2) + "%";
        document.getElementById("perf-rec").textContent = (data.recall * 100).toFixed(2) + "%";
        document.getElementById("perf-f05").textContent = data.macro_f05.toFixed(4);

        if (gridBody && data.threshold_comparison) {
          gridBody.innerHTML = "";
          data.threshold_comparison.forEach(row => {
            const isBest = row.threshold === data.selected_threshold;
            const tr = document.createElement("tr");
            tr.innerHTML = `
              <td><strong>${row.threshold.toFixed(2)}</strong></td>
              <td><strong style="color:var(--primary);">${row.macro_f05.toFixed(4)}</strong></td>
              <td>${(row.macro_precision * 100).toFixed(2)}%</td>
              <td>${(row.macro_recall * 100).toFixed(2)}%</td>
              <td>${isBest ? '<span class="badge badge-high">Optimal</span>' : '<span style="color:var(--text-muted);">Tested</span>'}</td>
            `;
            gridBody.appendChild(tr);
          });
        }
      }
    } catch (e) {
      console.error("Evaluation load error:", e);
    }
  }

  // ── Initial Boot ──────────────────────────────────────────────────────────
  loadCountries();
  loadKpis();
  performSearch();
});
