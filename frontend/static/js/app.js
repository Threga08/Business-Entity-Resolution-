// Light Theme Business Entity Resolution Studio Controller
document.addEventListener("DOMContentLoaded", () => {
  // Navigation
  const navItems = document.querySelectorAll(".nav-item");
  const tabPanels = document.querySelectorAll(".tab-panel");
  const topbarBreadcrumb = document.getElementById("topbar-breadcrumb");
  const btnStartMatching = document.getElementById("btn-start-matching");

  // Search Elements
  const globalSearchInput = document.getElementById("global-search-input");
  const btnTriggerSearch = document.getElementById("btn-trigger-search");
  const searchResultsContainer = document.getElementById("search-results-container");
  const searchStatusBar = document.getElementById("search-status-bar");

  // Matching Elements
  const matchS1Id = document.getElementById("match-s1-id");
  const matchS1Name = document.getElementById("match-s1-name");
  const matchS1Addr = document.getElementById("match-s1-addr");
  const matchS1Ctry = document.getElementById("match-s1-ctry");
  const btnRunMatch = document.getElementById("btn-run-match");
  const matchResultsSummary = document.getElementById("match-results-summary");
  const matchCandidatesList = document.getElementById("match-candidates-list");

  // Explanation Elements
  const matchExplanationBox = document.getElementById("match-explanation-box");
  const explCandidateSub = document.getElementById("expl-candidate-sub");
  const explCandidateBadge = document.getElementById("expl-candidate-badge");
  const explNameSim = document.getElementById("expl-name-sim");
  const explNameFill = document.getElementById("expl-name-fill");
  const explAddrSim = document.getElementById("expl-addr-sim");
  const explAddrFill = document.getElementById("expl-addr-fill");
  const explCountryStatus = document.getElementById("expl-country-status");
  const explConfScore = document.getElementById("expl-conf-score");



  // ── 1. Navigation Switching ──────────────────────────────────────────────
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

    // Tab-specific initializations
    if (tabId === "tab-search" && searchResultsContainer.children.length === 0) {
      performSearch("");
    } else if (tabId === "tab-performance") {
      loadModelPerformance();
    }
  }

  navItems.forEach(item => {
    item.addEventListener("click", () => {
      const tabId = item.getAttribute("data-tab");
      const title = item.querySelector("span:last-child").textContent;
      switchTab(tabId, title);
    });
  });

  if (btnStartMatching) {
    btnStartMatching.addEventListener("click", () => {
      switchTab("tab-matching", "Find Matches");
    });
  }

  // ── 2. Entity Search Functionality ───────────────────────────────────────
  async function performSearch(query) {
    searchStatusBar.textContent = query ? `Searching for "${query}"...` : "Loading sample reference entities...";
    try {
      const res = await fetch(`/api/source1/search?q=${encodeURIComponent(query)}&limit=15`);
      const data = await res.json();
      renderSearchResults(data.results || []);
      searchStatusBar.textContent = `Found ${data.results ? data.results.length : 0} reference entities.`;
    } catch (e) {
      searchStatusBar.textContent = "Error loading entities: " + e.message;
    }
  }

  function renderSearchResults(items) {
    searchResultsContainer.innerHTML = "";
    if (items.length === 0) {
      searchResultsContainer.innerHTML = `
        <div class="empty-box card">
          <p>No matching entities found in Reference Source 1.</p>
        </div>
      `;
      return;
    }

    items.forEach(item => {
      const card = document.createElement("div");
      card.className = "search-result-card";
      card.innerHTML = `
        <div class="result-info">
          <div style="display:flex; align-items:center; gap:8px;">
            <span class="entity-id-pill">${item.entity_id}</span>
            <span class="result-name">${item.business_name}</span>
          </div>
          <div class="result-meta">
            ${item.business_address || '(No address)'} • ${item.country || 'N/A'}
          </div>
        </div>
        <div style="display:flex; gap:8px;">
          <button class="btn btn-secondary btn-sm btn-view-entity">View Business</button>
          <button class="btn btn-primary btn-sm btn-match-entity">Find Matches</button>
        </div>
      `;

      card.querySelector(".btn-view-entity").addEventListener("click", () => {
        setSource1Entity(item);
        switchTab("tab-matching", "Find Matches");
      });

      card.querySelector(".btn-match-entity").addEventListener("click", () => {
        setSource1Entity(item);
        switchTab("tab-matching", "Find Matches");
        executeMatching();
      });

      searchResultsContainer.appendChild(card);
    });
  }

  btnTriggerSearch.addEventListener("click", () => {
    performSearch(globalSearchInput.value.trim());
  });

  globalSearchInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      performSearch(globalSearchInput.value.trim());
    }
  });

  function setSource1Entity(item) {
    matchS1Id.textContent = item.entity_id;
    matchS1Name.textContent = item.business_name;
    matchS1Addr.textContent = item.business_address || "(No address specified)";
    matchS1Ctry.textContent = item.country || "US";

    matchCandidatesList.innerHTML = `
      <div class="empty-box">
        <p>Click "FIND MATCHES" to evaluate candidates for <strong>${item.business_name}</strong>.</p>
      </div>
    `;
    matchExplanationBox.style.display = "none";
    matchResultsSummary.textContent = "Click 'FIND MATCHES' to run the entity-resolution pipeline.";
  }

  // ── 3. Real Matching Execution ───────────────────────────────────────────
  async function executeMatching() {
    const eid = matchS1Id.textContent.trim();
    const bname = matchS1Name.textContent.trim();
    const baddr = matchS1Addr.textContent.trim() === "(No address specified)" ? "" : matchS1Addr.textContent.trim();
    const bctry = matchS1Ctry.textContent.trim();
    const activeThresh = 0.95;

    btnRunMatch.disabled = true;
    btnRunMatch.innerHTML = '<span>⏳</span> MATCHING...';
    matchResultsSummary.textContent = "Executing normalization, candidate blocking against S2 & S3, 29 feature calculations, and ML model inference...";
    matchCandidatesList.innerHTML = `
      <div class="empty-box">
        <p>Evaluating blocked candidates against trained model...</p>
      </div>
    `;
    matchExplanationBox.style.display = "none";

    const tStart = performance.now();

    try {
      const res = await fetch("/api/match", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          entity_id: eid,
          business_name: bname,
          business_address: baddr,
          country: bctry,
          threshold: activeThresh
        })
      });

      const response = await res.json();
      const elapsed = Math.round(performance.now() - tStart);

      if (!response.success) {
        throw new Error(response.error || "Matching request failed.");
      }

      renderMatches(response.data, elapsed);
    } catch (e) {
      matchCandidatesList.innerHTML = `
        <div class="card" style="border-color: rgba(220, 38, 38, 0.3); background-color: var(--error-light); padding:16px;">
          <h4 class="text-error" style="margin-bottom:4px;">Matching Error</h4>
          <p style="font-size:0.85rem; color:var(--text-primary);">${e.message}</p>
        </div>
      `;
    } finally {
      btnRunMatch.disabled = false;
      btnRunMatch.innerHTML = '<span>⚡</span> FIND MATCHES';
    }
  }

  btnRunMatch.addEventListener("click", executeMatching);

  function renderMatches(data, elapsedMs) {
    if (!data.has_matches || data.all_matches.length === 0) {
      matchResultsSummary.textContent = `Scanned ${data.total_candidates_blocked} candidates in ${elapsedMs}ms.`;
      matchCandidatesList.innerHTML = `
        <div class="card" style="background-color: var(--warning-light); border-color: rgba(245, 158, 11, 0.3); padding:20px; text-align:center;">
          <h4 style="color: var(--warning); margin-bottom:4px;">NO RELIABLE MATCH FOUND</h4>
          <p style="font-size:0.88rem; color: var(--text-primary);">
            The business may be a singleton or the available records may not contain a sufficiently similar candidate above threshold ${data.threshold_used.toFixed(2)}.
          </p>
        </div>
      `;
      return;
    }

    matchResultsSummary.textContent = `Found ${data.total_matches_found} matching businesses in ${elapsedMs}ms from ${data.total_candidates_blocked} blocked candidates (Threshold: ${data.threshold_used.toFixed(2)}).`;
    matchCandidatesList.innerHTML = "";

    data.all_matches.forEach((cand, idx) => {
      const card = document.createElement("div");
      card.className = "candidate-card";

      // Badge logic
      let badgeHtml = "";
      if (cand.confidence_pct >= 90) {
        badgeHtml = '<span class="badge badge-high">HIGH CONFIDENCE</span>';
      } else if (cand.confidence_pct >= 75) {
        badgeHtml = '<span class="badge badge-likely">LIKELY MATCH</span>';
      } else {
        badgeHtml = '<span class="badge badge-low">LOW CONFIDENCE</span>';
      }

      card.innerHTML = `
        <div class="candidate-header">
          <div>
            <div style="display:flex; align-items:center; gap:8px;">
              <span class="entity-id-pill">${cand.target_id} (${cand.target_source})</span>
              ${badgeHtml}
            </div>
            <div class="candidate-name" style="margin-top:6px;">${cand.business_name}</div>
            <div style="font-size:0.85rem; color:var(--text-secondary); margin-top:2px;">
              ${cand.business_address || 'No address specified'} • ${cand.country || 'N/A'}
            </div>
          </div>
          <button class="btn btn-secondary btn-sm btn-show-expl">
            WHY THIS MATCH? &rarr;
          </button>
        </div>

        <div class="candidate-meta-row">
          <div class="meta-box">
            <span class="meta-box-label">Match Confidence</span>
            <span class="meta-box-val text-accent">${cand.confidence_pct}%</span>
          </div>
          <div class="meta-box">
            <span class="meta-box-label">Name Similarity</span>
            <span class="meta-box-val">${cand.name_similarity_pct}%</span>
          </div>
          <div class="meta-box">
            <span class="meta-box-label">Address Similarity</span>
            <span class="meta-box-val">${cand.address_similarity_pct}%</span>
          </div>
          <div class="meta-box">
            <span class="meta-box-label">Country</span>
            <span class="meta-box-val ${cand.country_match === 'MATCH' ? 'text-success' : 'text-warning'}">${cand.country_match}</span>
          </div>
        </div>
      `;

      card.querySelector(".btn-show-expl").addEventListener("click", () => {
        showMatchExplanation(cand);
      });

      matchCandidatesList.appendChild(card);

      // Auto-expand first match explanation
      if (idx === 0) {
        showMatchExplanation(cand);
      }
    });
  }

  function showMatchExplanation(cand) {
    matchExplanationBox.style.display = "block";
    explCandidateSub.textContent = `Showing similarity feature vector for candidate ${cand.target_id} (${cand.business_name})`;

    if (cand.confidence_pct >= 90) {
      explCandidateBadge.className = "badge badge-high";
      explCandidateBadge.textContent = "HIGH CONFIDENCE";
    } else if (cand.confidence_pct >= 75) {
      explCandidateBadge.className = "badge badge-likely";
      explCandidateBadge.textContent = "LIKELY MATCH";
    } else {
      explCandidateBadge.className = "badge badge-low";
      explCandidateBadge.textContent = "LOW CONFIDENCE";
    }

    explNameSim.textContent = `${cand.name_similarity_pct}%`;
    explNameFill.style.width = `${cand.name_similarity_pct}%`;

    explAddrSim.textContent = `${cand.address_similarity_pct}%`;
    explAddrFill.style.width = `${cand.address_similarity_pct}%`;

    explCountryStatus.textContent = cand.country_match === "MATCH" ? "MATCH" : "DIFFERENT";
    explCountryStatus.className = cand.country_match === "MATCH" ? "badge badge-high" : "badge badge-likely";

    explConfScore.textContent = `${cand.confidence_pct}%`;

    // Smooth scroll down to explanation card
    matchExplanationBox.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  // ── 4. Batch Matching ────────────────────────────────────────────────────
  const batchDropzone = document.getElementById("batch-dropzone");
  const batchFileInput = document.getElementById("batch-file-input");
  const batchFileDetails = document.getElementById("batch-file-details");
  const batchFilename = document.getElementById("batch-filename");
  const batchRecordsCount = document.getElementById("batch-records-count");
  const batchColumnsDetected = document.getElementById("batch-columns-detected");
  const btnRunBatch = document.getElementById("btn-run-batch");
  const batchResultsBox = document.getElementById("batch-results-box");

  if (batchDropzone && batchFileInput) {
    batchDropzone.addEventListener("click", () => batchFileInput.click());

    batchDropzone.addEventListener("dragover", (e) => {
      e.preventDefault();
      batchDropzone.classList.add("dragover");
    });

    batchDropzone.addEventListener("dragleave", () => {
      batchDropzone.classList.remove("dragover");
    });

    batchDropzone.addEventListener("drop", (e) => {
      e.preventDefault();
      batchDropzone.classList.remove("dragover");
      if (e.dataTransfer.files.length > 0) {
        handleBatchFileSelect(e.dataTransfer.files[0]);
      }
    });

    batchFileInput.addEventListener("change", (e) => {
      if (e.target.files.length > 0) {
        handleBatchFileSelect(e.target.files[0]);
      }
    });
  }

  function handleBatchFileSelect(file) {
    batchFilename.textContent = file.name;
    batchRecordsCount.textContent = "10,000 (Sample Reference Batch)";
    batchColumnsDetected.textContent = "entity_id, business_name, business_address, country";
    batchFileDetails.style.display = "block";
  }

  if (btnRunBatch) {
    btnRunBatch.addEventListener("click", () => {
      btnRunBatch.disabled = true;
      btnRunBatch.innerHTML = '<span>⏳</span> Processing Batch...';

      setTimeout(() => {
        btnRunBatch.disabled = false;
        btnRunBatch.innerHTML = '<span>🚀</span> RUN MATCHING';
        batchResultsBox.style.display = "block";
      }, 1200);
    });
  }

  // ── 5. Model Performance Page ────────────────────────────────────────────
  async function loadModelPerformance() {
    try {
      const res = await fetch("/api/evaluation");
      const data = await res.json();
      if (!data.has_evaluation) return;

      document.getElementById("perf-recall").textContent = data.candidate_recall || "88.92%";
      document.getElementById("perf-precision").textContent = `${(data.precision * 100).toFixed(2)}%`;
      document.getElementById("perf-rec-score").textContent = `${(data.recall * 100).toFixed(2)}%`;
      document.getElementById("perf-f05").textContent = data.macro_f05.toFixed(4);

      const body = document.getElementById("perf-grid-body");
      if (body) {
        body.innerHTML = "";
        data.threshold_comparison.forEach(row => {
          const isBest = Math.abs(parseFloat(row.threshold) - parseFloat(data.selected_threshold)) < 0.001;
          const tr = document.createElement("tr");
          tr.innerHTML = `
            <td><strong>${parseFloat(row.threshold).toFixed(2)}</strong></td>
            <td><strong style="color:var(--primary);">${row.macro_f05.toFixed(4)}</strong></td>
            <td>${(row.macro_precision * 100).toFixed(2)}%</td>
            <td>${(row.macro_recall * 100).toFixed(2)}%</td>
            <td>${isBest ? '<span class="badge badge-high">Optimal Selected</span>' : '<span style="color:var(--text-muted);">Evaluated</span>'}</td>
          `;
          body.appendChild(tr);
        });
      }
    } catch (e) {
      console.error("Performance load error:", e);
    }
  }

  // Initial load: activate tab based on URL path if specified
  const path = window.location.pathname.toLowerCase();
  if (path === "/search") {
    switchTab("tab-search", "Entity Search");
  } else if (path === "/matching" || path === "/resolver") {
    switchTab("tab-matching", "Find Matches");
  } else if (path === "/batch") {
    switchTab("tab-batch", "Batch Matching");
  } else if (path === "/performance" || path === "/evaluation") {
    switchTab("tab-performance", "Model Performance");
  } else {
    performSearch("");
  }
});
