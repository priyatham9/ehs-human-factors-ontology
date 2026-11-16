const $ = (id) => document.getElementById(id);
const escape = (s) =>
  String(s ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
const compact = (iri) =>
  iri.replace("http://www.w3.org/2004/02/skos/core#", "skos:");
const prettyStrength = (s) => s.replace("ehs:Match", "").toLowerCase();
let data, selection;
function reflectSelection() {
  const url = new URL(location.href);
  url.searchParams.set("factor", $("factor").value);
  url.searchParams.set("framework", $("framework").value);
  url.searchParams.set("gap", $("gap").value);
  history.replaceState(null, "", url);
}
function renderSelection() {
  const factor = $("factor").value,
    framework = $("framework").value;
  const f = data.factors.find((x) => x.id === factor),
    fw = data.frameworks.find((x) => x.id === framework);
  const rows = data.alignments.filter(
    (a) => a.localFactor === factor && a.framework === framework,
  );
  const absences = data.absences.filter(
    (a) => a.localFactor === factor && a.framework === framework,
  );
  const cell = data.cells.find(
    (c) => c.localFactor === factor && c.framework === framework,
  );
  $("selection-context").textContent = `${f.dimension} · ${f.id} → ${fw.label}`;
  const absent = cell.sourceStatus === "asserted-no-counterpart";
  const mapped = rows.length > 0;
  const sourceTitle = absent
    ? "No counterpart asserted"
    : mapped
      ? `${rows.length} proposed ${rows.length === 1 ? "alignment" : "alignments"}`
      : "Nothing asserted";
  $("source-status").textContent =
    cell.sourceStatus === "conflicting-assertions"
      ? "Conflicting source assertions"
      : sourceTitle;
  $("skos-status").textContent = mapped
    ? `${rows.length} mapping ${rows.length === 1 ? "expression" : "expressions"}`
    : "No mapping statement";
  $("sidecar-status").textContent = absent
    ? "Explicit absence restored"
    : mapped
      ? "Assertion context restored"
      : "Still unasserted";
  $("source-content").innerHTML = mapped
    ? rows
        .map(
          (r) =>
            `<div class="mapping-row"><strong>${escape(r.externalLabel)}</strong><span>${escape(prettyStrength(r.strength))} · ${escape(r.id)}</span><p>Source keys: ${escape(r.sourceRefs.join(", "))}</p>${r.comment ? `<p>${escape(r.comment)}</p>` : ""}</div>`,
        )
        .join("")
    : absent
      ? `<p>The author explicitly records that this local factor has no counterpart in ${escape(fw.label)}.</p><code>${escape(factor)}<br>ehs:noCounterpartIn<br>${escape(framework)}</code>`
      : "<p>The source records neither an alignment nor an explicit absence for this comparison.</p>";
  $("skos-content").innerHTML = mapped
    ? rows
        .map(
          (r) =>
            `<div class="mapping-row"><strong>${escape(r.externalLabel)}</strong><code>${escape(compact(r.skosPredicate))}</code><p>Endpoints and projected relationship retained. Original assertion ID, row-level source keys and comment are omitted.</p></div>`,
        )
        .join("")
    : "<p>Under open-world semantics, the missing mapping does not assert that no counterpart exists.</p><p>The export alone cannot distinguish an explicit absence from an unrecorded comparison.</p>";
  $("sidecar-content").innerHTML = mapped
    ? "<p>Original alignment resources survive with their local match strengths, source keys and comments. The standard SKOS graph remains separate and unchanged.</p><p>Recovering the assertion preserves what the author said; it does not validate the correspondence.</p>"
    : absent
      ? "<p>The original <code>ehs:noCounterpartIn</code> triple is retained. RDF reification identifies this statement; PROV links it to the exact source snapshot.</p><p>No row-level citation is invented. Source-file provenance is the available guarantee.</p>"
      : "<p>No absence is invented. The absence of both a mapping and an absence assertion remains an unrecorded comparison.</p>";
  $("selection-conclusion").textContent = absent
    ? "The exporter loses a distinction already present in the source: an asserted absence becomes indistinguishable from an unrecorded comparison. The sidecar restores that distinction without redefining SKOS."
    : mapped
      ? "The mapping count looks complete, but the individual assertion’s identity and evidential context disappear. The sidecar retains those original records without upgrading the strength of the proposed mapping."
      : "Missing information stays missing. A round-trip repair must not convert an unknown comparison into an asserted absence.";
  $("raw-source").textContent =
    [
      ...rows.flatMap((r) => r.sourceTriples),
      ...absences.map((a) => a.sourceTriple),
    ].join("\n") || "No relevant assertion in the source snapshot.";
  $("provenance-detail").textContent = absences.length
    ? absences.map((a) => a.provenanceScope).join(" ")
    : "Alignment source keys and comments above are copied from the original reified records. They remain author-proposed judgments, not independent validation.";
  selection = {
    source: data.source,
    factor: f,
    framework: fw,
    cell,
    alignments: rows,
    absences,
    conclusion: $("selection-conclusion").textContent,
    scope: data.scope,
    interpretation: data.interpretation,
  };
  $("export-status").textContent = "";
}
function renderGap() {
  const gap = data.coverageGaps.find((g) => g.id === $("gap").value);
  const mappings = data.alignments.filter((a) =>
    gap.coexistingAlignments.includes(a.id),
  );
  const mappingText = mappings.length
    ? mappings
        .map(
          (a) =>
            `${data.factors.find((f) => f.id === a.localFactor).label} → ${prettyStrength(a.strength)} → ${gap.label}`,
        )
        .join("; ")
    : "No PIF mapping is recorded to this external factor.";
  $("gap-view").innerHTML =
    `<h3 class="gap-heading">${escape(gap.label)}</h3><div class="gap-columns"><div><h4>RECORDED GAP IN THE SOURCE</h4><blockquote>${escape(gap.comment)}</blockquote><p class="small">${escape(gap.id)}<br>Source keys: ${escape(gap.sourceRefs.join(", "))}</p></div><div><h4>WHAT A SKOS CONSUMER RECEIVES</h4><p>${gap.skosConceptPresent ? "The external concept is present." : "The external concept is not present."} The explicit coverage-gap record and its rationale are omitted.</p><p>${escape(mappingText)}</p><p>${mappings.length ? "A partial correspondence does not remove this gap. “Mapped” cannot be read as “fully covered.”" : "An unmapped concept alone does not identify whether a gap was considered, the concept was out of scope, or no comparison was made."}</p><p class="small">The sidecar preserves this original gap record, its source keys and its rationale.</p></div></div>`;
}
async function start() {
  try {
    const response = await fetch("skos/translation-loss-report.json");
    if (!response.ok)
      throw new Error(`Audit file could not be loaded (${response.status}).`);
    data = await response.json();
    const c = data.counts;
    $("mapping-count").textContent =
      `${c.uniquePifSkosMappings} / ${c.pifAlignments}`;
    const absenceLoss = data.lossLedger.find(
      (r) => r.feature === "Explicit no-counterpart assertions",
    );
    const gapLoss = data.lossLedger.find(
      (r) => r.feature === "Explicit external coverage-gap records",
    );
    $("absence-count").textContent =
      `${absenceLoss.source - absenceLoss.skos} / ${absenceLoss.source}`;
    $("gap-count").textContent =
      `${gapLoss.source - gapLoss.skos} / ${gapLoss.source}`;
    $("counts-note").textContent =
      `The ${c.pifAlignments} PIF alignments express ${c.byStrength.close} close, ${c.byStrength.partial} partial and ${c.byStrength.broader} broader matches. The ${c.dimensionMappingsSeparate} dimension-to-IDHEAS-G mappings are counted separately. Across ${c.cells} PIF/framework cells, the source has ${c.sourceCellStatus.mapped || 0} mapped cells, ${c.sourceCellStatus["asserted-no-counterpart"] || 0} explicit absences and ${c.sourceCellStatus.unasserted || 0} unasserted comparisons. SKOS alone turns the explicit absences into unasserted cells.`;
    $("factor").innerHTML = data.factors
      .map((f) => `<option value="${escape(f.id)}">${escape(f.label)}</option>`)
      .join("");
    $("framework").innerHTML = data.frameworks
      .map((f) => `<option value="${escape(f.id)}">${escape(f.label)}</option>`)
      .join("");
    $("factor").value = "ehs:WorkplaceVisibility";
    $("framework").value = "xw:fw-SPARH";
    $("gap").innerHTML = data.coverageGaps
      .map(
        (g) =>
          `<option value="${escape(g.id)}">${escape(g.label)} · ${escape(data.frameworks.find((f) => f.id === g.framework)?.label || g.framework)}</option>`,
      )
      .join("");
    $("gap").value = "xw:gap-cream-TimeOfDay";
    const query = new URLSearchParams(location.search);
    for (const id of ["factor", "framework", "gap"]) {
      if ([...$(id).options].some((o) => o.value === query.get(id)))
        $(id).value = query.get(id);
    }
    $("loss-ledger").innerHTML = data.lossLedger
      .map(
        (r) =>
          `<tr><th scope="row">${escape(r.feature)}<small>${escape(r.meaning)}</small></th><td>${r.source}</td><td>${r.skos}</td><td>${r.sidecar}</td></tr>`,
      )
      .join("");
    $("roundtrip").textContent =
      `${data.roundTrip.recoveredTriples} / ${data.roundTrip.contractTriples} scoped triples recovered`;
    $("source-hash").textContent = data.source.sha256;
    renderSelection();
    renderGap();
    $("loading").hidden = true;
    $("audit").hidden = false;
  } catch (e) {
    $("loading").hidden = true;
    $("error").hidden = false;
    $("error").textContent = `${e.message} `;
    const link = document.createElement("a");
    link.href = "skos/translation-loss-report.json";
    link.textContent = "Open the generated audit report directly.";
    $("error").append(link);
  }
}
$("factor").addEventListener("change", () => {
  renderSelection();
  reflectSelection();
});
$("framework").addEventListener("change", () => {
  renderSelection();
  reflectSelection();
});
$("gap").addEventListener("change", () => {
  renderGap();
  reflectSelection();
});
$("export-selection").addEventListener("click", () => {
  if (!selection) return;
  const url = URL.createObjectURL(
    new Blob([JSON.stringify(selection, null, 2)], {
      type: "application/json",
    }),
  );
  const link = document.createElement("a");
  link.href = url;
  link.download = "crosswalk-translation-review.json";
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
  $("export-status").textContent =
    "Selected assertions, source hash and interpretation limits exported.";
});
start();
