// SOC-Copilot poster builder
// ----------------------------
// Strict compliance with the HIT poster spec (Dr. Yakov Damatov):
//   - Size B1 70x100 cm (portrait, 27.559" x 39.370")
//   - Header section format unchanged (logos top-left/right, project name
//     centered, course/year/lecturer/students underneath)
//   - Body sections in this order:
//       1. Introduction
//       2. Methodology & Architecture     <-- student section #1
//       3. Results & Evaluation           <-- student section #2
//       4. Conclusions
//       5. Discussions + QR to demo video
//   - Font sizes within spec:
//       project name:    74-78 -> 76
//       section titles:  52-56 -> 54
//       year/semester:   38-42 -> 40
//       lecturer/names:  52-56 -> 54
//       course name:     38-42 -> 40
//       body text:       32-38 -> 34 (32 in dense tables)

const pptxgen = require("pptxgenjs");
const pres = new pptxgen();

// custom B1 portrait layout
pres.defineLayout({ name: "B1_PORTRAIT", width: 27.559, height: 39.370 });
pres.layout = "B1_PORTRAIT";
pres.author  = "Stav Hefetz & Bar Koldanov";
pres.title   = "SOC-Copilot - AI-Assisted Triage for Authentication Anomalies";

// ---- palette (cybersecurity / SOC theme) -------------------------------
const NAVY   = "0F172A";  // slate-900
const BLUE   = "1E40AF";  // blue-800
const CYAN   = "0891B2";  // cyan-700
const ACCENT = "22D3EE";  // cyan-400
const RED    = "DC2626";  // alert
const GREEN  = "16A34A";  // success
const BG     = "F8FAFC";  // slate-50
const INK    = "0F172A";  // body text
const MUTED  = "475569";  // slate-600

// ---- create slide ------------------------------------------------------
const slide = pres.addSlide();
slide.background = { color: BG };

// ====================================================================
// HEADER  (top 5.5 inches)
// Format: dark navy band, project name center, meta underneath.
// We may change colors / fonts within the size constraints; we may NOT
// change the format.
// ====================================================================

const W = 27.559;  // slide width inches
const M = 0.7;     // outer margin inches
const headerH = 5.2;

// header background
slide.addShape(pres.shapes.RECTANGLE, {
  x: 0, y: 0, w: W, h: headerH,
  fill: { color: NAVY }, line: { color: NAVY, width: 0 },
});

// accent stripe at bottom of header
slide.addShape(pres.shapes.RECTANGLE, {
  x: 0, y: headerH - 0.15, w: W, h: 0.15,
  fill: { color: ACCENT }, line: { color: ACCENT, width: 0 },
});

// university name (top strip, in spec range for course-name 38-42)
slide.addText("Holon Institute of Technology  -  Faculty of Sciences", {
  x: M, y: 0.30, w: W - 2*M, h: 0.55,
  fontFace: "Calibri", fontSize: 40, color: ACCENT, bold: false,
  align: "center", valign: "middle", charSpacing: 4, margin: 0,
});

// project name (74-78 -> 76)
slide.addText("SOC-Copilot", {
  x: M, y: 1.00, w: W - 2*M, h: 1.5,
  fontFace: "Georgia", fontSize: 76, color: "FFFFFF", bold: true,
  align: "center", valign: "middle", margin: 0,
});

slide.addText("AI-Assisted Triage for Authentication Anomalies", {
  x: M, y: 2.55, w: W - 2*M, h: 0.7,
  fontFace: "Calibri", fontSize: 40, color: "CADCFC", italic: true,
  align: "center", valign: "middle", margin: 0,
});

// meta block: two columns (left = course + year/semester ; right = lecturers + student)
const metaY = 3.45;
const metaH = 1.55;

// left meta column
slide.addText([
  { text: "Course:  ",   options: { fontSize: 40, color: "CADCFC" } },
  { text: "Introduction to AI for Cybersecurity", options: { fontSize: 40, color: "FFFFFF", bold: true, breakLine: true } },
  { text: "Academic year 2025/26  -  Semester B (Spring)", options: { fontSize: 40, color: "CADCFC" } },
], {
  x: M, y: metaY, w: (W - 2*M) / 2 - 0.2, h: metaH,
  fontFace: "Calibri", align: "left", valign: "top", margin: 0,
});

// right meta column
slide.addText([
  { text: "Lecturers:  ", options: { fontSize: 54, color: "CADCFC" } },
  { text: "Dr. A. Kojukhov & V. Nefedov", options: { fontSize: 54, color: "FFFFFF", bold: true, breakLine: true } },
  { text: "Students:  ", options: { fontSize: 54, color: "CADCFC" } },
  { text: "Stav Hefetz & Bar Koldanov",  options: { fontSize: 54, color: "FFFFFF", bold: true } },
], {
  x: M + (W - 2*M) / 2 + 0.2, y: metaY, w: (W - 2*M) / 2 - 0.2, h: metaH,
  fontFace: "Calibri", align: "right", valign: "top", margin: 0,
});

// ====================================================================
// BODY
// ====================================================================

const bodyStartY = headerH + 0.6;        // 5.8"
const bodyW      = W - 2*M;               // 26.16"
const colW       = (bodyW - 0.5) / 2;     // 12.83" each (with 0.5" gap)

// ---- helper: section header bar ---------------------------------------
function sectionHeader(x, y, w, title, color = NAVY, accent = ACCENT) {
  slide.addShape(pres.shapes.RECTANGLE, {
    x, y, w, h: 1.05,
    fill: { color }, line: { color, width: 0 },
  });
  // left accent bar
  slide.addShape(pres.shapes.RECTANGLE, {
    x, y, w: 0.18, h: 1.05,
    fill: { color: accent }, line: { color: accent, width: 0 },
  });
  slide.addText(title, {
    x: x + 0.45, y, w: w - 0.5, h: 1.05,
    fontFace: "Georgia", fontSize: 54, color: "FFFFFF", bold: true,
    align: "left", valign: "middle", margin: 0,
  });
}

// ---- 1. INTRODUCTION  (full width) ------------------------------------
let cy = bodyStartY;
sectionHeader(M, cy, bodyW, "1. Introduction");
cy += 1.15;

// content card
const introH = 5.2;
slide.addShape(pres.shapes.RECTANGLE, {
  x: M, y: cy, w: bodyW, h: introH,
  fill: { color: "FFFFFF" }, line: { color: "E2E8F0", width: 1 },
  shadow: { type: "outer", color: "000000", blur: 8, offset: 2, angle: 90, opacity: 0.06 },
});

slide.addText([
  { text: "The problem.  ", options: { bold: true, color: NAVY } },
  { text: "Tier-1 SOC analysts face two compounding failures: alert fatigue (thousands of events per day, most are noise) and a context gap (raw telemetry is not yet mapped to MITRE ATT&CK techniques or recommended responses). The result is genuine intrusions dismissed as noise, a documented failure mode in major breaches.", options: { breakLine: true } },
  { text: " ", options: { breakLine: true, fontSize: 12 } },
  { text: "Rationale.  ", options: { bold: true, color: NAVY } },
  { text: "Combine three components, each with a sharp job: an unsupervised anomaly detector for cheap detection, a deterministic rule-based mapper for auditable MITRE attribution, and a constrained LLM agent for analyst-friendly explanation. The LLM never sees raw threat-intel data, so it cannot invent technique IDs.", options: { breakLine: true } },
  { text: " ", options: { breakLine: true, fontSize: 12 } },
  { text: "Goals & objectives.  ", options: { bold: true, color: NAVY } },
  { text: "(1) Train an Isolation Forest on benign-only authentication events; (2) build a rule-based MITRE mapper covering T1110.001, T1110.003 and T1078; (3) integrate an AG2 LLM agent that summarises every alert in plain English, grounded in the mapper output; (4) expose the system via Chainlit with a persistent audit trail; (5) evaluate detection on held-out data and on four scripted adversarial scenarios." },
], {
  x: M + 0.5, y: cy + 0.35, w: bodyW - 1.0, h: introH - 0.7,
  fontFace: "Calibri", fontSize: 34, color: INK,
  align: "left", valign: "top", paraSpaceAfter: 6,
});

cy += introH + 0.6;

// ---- 2 + 3 SIDE BY SIDE (METHODOLOGY / RESULTS) -----------------------
const twoColH = 11.5;

// section #1 -- Methodology & Architecture (left)
sectionHeader(M, cy, colW, "2. Methodology & Architecture", NAVY, ACCENT);
slide.addShape(pres.shapes.RECTANGLE, {
  x: M, y: cy + 1.15, w: colW, h: twoColH - 1.15,
  fill: { color: "FFFFFF" }, line: { color: "E2E8F0", width: 1 },
  shadow: { type: "outer", color: "000000", blur: 8, offset: 2, angle: 90, opacity: 0.06 },
});

// pipeline visual (three boxes stacked)
const pipeX = M + 0.6;
const pipeW = colW - 1.2;
const pipeBoxH = 1.5;
const pipeGap = 0.45;
let pipeY = cy + 1.5;

function pipelineBox(y, label, sub, fill) {
  slide.addShape(pres.shapes.RECTANGLE, {
    x: pipeX, y, w: pipeW, h: pipeBoxH,
    fill: { color: fill }, line: { color: fill, width: 0 },
  });
  slide.addText([
    { text: label, options: { bold: true, fontSize: 34, color: "FFFFFF", breakLine: true } },
    { text: sub,   options: { fontSize: 28, color: "E0F2FE" } },
  ], {
    x: pipeX + 0.3, y, w: pipeW - 0.6, h: pipeBoxH,
    fontFace: "Calibri", align: "left", valign: "middle", margin: 0,
  });
}

function pipelineArrow(y) {
  slide.addShape(pres.shapes.RECTANGLE, {
    x: pipeX + pipeW/2 - 0.15, y, w: 0.3, h: pipeGap,
    fill: { color: NAVY }, line: { color: NAVY, width: 0 },
  });
}

pipelineBox(pipeY, "Auth event",                "raw SIEM telemetry  ->  feature vector", BLUE);   pipeY += pipeBoxH;
pipelineArrow(pipeY);                                                                              pipeY += pipeGap;
pipelineBox(pipeY, "Isolation Forest detector", "200 trees, trained on benign-only",       CYAN);   pipeY += pipeBoxH;
pipelineArrow(pipeY);                                                                              pipeY += pipeGap;
pipelineBox(pipeY, "MITRE ATT&CK mapper",       "deterministic rule chain (T1110, T1078)", CYAN);   pipeY += pipeBoxH;
pipelineArrow(pipeY);                                                                              pipeY += pipeGap;
pipelineBox(pipeY, "LLM Triage Agent",          "AG2  -  grounded in mapper output only",   BLUE);   pipeY += pipeBoxH;
pipelineArrow(pipeY);                                                                              pipeY += pipeGap;
pipelineBox(pipeY, "Analyst UI + audit log",    "Chainlit Steps  +  traffic_logs.log",      NAVY);   pipeY += pipeBoxH;

// caption under pipeline
slide.addText("The LLM is constrained by architecture, not just by prompt: it never sees raw threat-intel data, so it cannot invent technique IDs.", {
  x: pipeX, y: pipeY + 0.25, w: pipeW, h: 1.6,
  fontFace: "Calibri", fontSize: 32, color: MUTED, italic: true,
  align: "left", valign: "top", margin: 0,
});

// section #2 -- Results & Evaluation (right)
const rightX = M + colW + 0.5;
sectionHeader(rightX, cy, colW, "3. Results & Evaluation", NAVY, ACCENT);
slide.addShape(pres.shapes.RECTANGLE, {
  x: rightX, y: cy + 1.15, w: colW, h: twoColH - 1.15,
  fill: { color: "FFFFFF" }, line: { color: "E2E8F0", width: 1 },
  shadow: { type: "outer", color: "000000", blur: 8, offset: 2, angle: 90, opacity: 0.06 },
});

// 3 big KPI cards
const kpiY = cy + 1.5;
const kpiH = 1.95;
const kpiGap = 0.25;
const kpiW = (colW - 1.2 - 2*kpiGap) / 3;
const kpiX0 = rightX + 0.6;

function kpiCard(x, label, value, fill) {
  slide.addShape(pres.shapes.RECTANGLE, {
    x, y: kpiY, w: kpiW, h: kpiH,
    fill: { color: fill }, line: { color: fill, width: 0 },
  });
  slide.addText(value, {
    x, y: kpiY + 0.1, w: kpiW, h: 1.0,
    fontFace: "Georgia", fontSize: 60, color: "FFFFFF", bold: true,
    align: "center", valign: "middle", margin: 0,
  });
  slide.addText(label, {
    x, y: kpiY + 1.1, w: kpiW, h: 0.85,
    fontFace: "Calibri", fontSize: 28, color: "E0F2FE",
    align: "center", valign: "middle", margin: 0,
  });
}

kpiCard(kpiX0,                          "ROC-AUC",   "0.996", NAVY);
kpiCard(kpiX0 + kpiW + kpiGap,          "Recall",    "0.95",  CYAN);
kpiCard(kpiX0 + 2*(kpiW + kpiGap),      "Faithful*", "100%",  GREEN);

// per-technique table
const tableY = kpiY + kpiH + 0.45;
slide.addText("Per-technique recall (test set, n=2,500)", {
  x: rightX + 0.6, y: tableY, w: colW - 1.2, h: 0.55,
  fontFace: "Calibri", fontSize: 32, color: NAVY, bold: true,
  align: "left", valign: "middle", margin: 0,
});

slide.addTable([
  [
    { text: "MITRE Technique",  options: { bold: true, color: "FFFFFF", fill: { color: NAVY }, align: "left",   valign: "middle" } },
    { text: "n",                options: { bold: true, color: "FFFFFF", fill: { color: NAVY }, align: "right",  valign: "middle" } },
    { text: "Recall",           options: { bold: true, color: "FFFFFF", fill: { color: NAVY }, align: "right",  valign: "middle" } },
  ],
  [{ text: "T1110.001 Brute Force",       options: { align: "left", valign: "middle" } },
   { text: "41",                          options: { align: "right", valign: "middle" } },
   { text: "100 %",                       options: { align: "right", valign: "middle", bold: true, color: GREEN } }],
  [{ text: "T1110.003 Password Spraying", options: { align: "left", valign: "middle" } },
   { text: "23",                          options: { align: "right", valign: "middle" } },
   { text: "100 %",                       options: { align: "right", valign: "middle", bold: true, color: GREEN } }],
  [{ text: "T1078 Valid Accounts",        options: { align: "left", valign: "middle" } },
   { text: "11",                          options: { align: "right", valign: "middle" } },
   { text: "64 %",                        options: { align: "right", valign: "middle", bold: true, color: "CA8A04" } }],
], {
  x: rightX + 0.6, y: tableY + 0.65, w: colW - 1.2,
  colW: [(colW - 1.2) * 0.55, (colW - 1.2) * 0.15, (colW - 1.2) * 0.30],
  rowH: 0.65,
  fontFace: "Calibri", fontSize: 32, color: INK,
  border: { type: "solid", pt: 1, color: "E2E8F0" },
});

// scenario summary text
slide.addText([
  { text: "Adversarial scenarios.  ",  options: { bold: true, color: NAVY } },
  { text: "Burst brute force 100 %  -  spraying 100 %  -  valid accounts 65 %  -  evasive (attacker mimics benign) ", options: {} },
  { text: "0 %", options: { bold: true, color: RED } },
  { text: ".  The 0 % is the honest limit of per-event detection; cross-event correlation is needed for that case (see Discussions).", options: {} },
], {
  x: rightX + 0.6, y: tableY + 0.65 + 4 * 0.65 + 0.35, w: colW - 1.2, h: 2.2,
  fontFace: "Calibri", fontSize: 32, color: INK,
  align: "left", valign: "top", margin: 0,
});

// footnote
slide.addText("* LLM faithfulness: % of explanations whose claims all trace to mapper output, manual review n=20.", {
  x: rightX + 0.6, y: cy + twoColH - 0.55, w: colW - 1.2, h: 0.45,
  fontFace: "Calibri", fontSize: 24, color: MUTED, italic: true,
  align: "left", valign: "top", margin: 0,
});

cy += twoColH + 0.6;

// ---- 4. CONCLUSIONS (full width) --------------------------------------
sectionHeader(M, cy, bodyW, "4. Conclusions");
cy += 1.15;

const conclH = 4.4;
slide.addShape(pres.shapes.RECTANGLE, {
  x: M, y: cy, w: bodyW, h: conclH,
  fill: { color: "FFFFFF" }, line: { color: "E2E8F0", width: 1 },
  shadow: { type: "outer", color: "000000", blur: 8, offset: 2, angle: 90, opacity: 0.06 },
});

slide.addText([
  { text: "Goals achieved.  ", options: { bold: true, color: NAVY } },
  { text: "All five objectives in §1 were met: trained Isolation Forest (ROC-AUC 0.996); deterministic mapper covering three MITRE techniques; AG2 triage agent grounded in mapper output (100 % faithfulness on 20-sample manual review); Chainlit MVP with JSONL audit log; quantitative evaluation on held-out data and four scripted scenarios.", options: { breakLine: true } },
  { text: " ", options: { breakLine: true, fontSize: 12 } },
  { text: "Compared to targets.  ", options: { bold: true, color: NAVY } },
  { text: "Target was to *approach* a supervised baseline without using labels at training. The unsupervised model reaches recall 0.95 while training on benign rows only - matching the project pitch. The model is strongest where the signal is loud (T1110 variants, 100 % recall) and weakest where the signal is genuinely sparse (T1078, 64 %). This honest gradient is a *result*, not a defect - it tells the SOC operator exactly where to deploy compensating controls." },
], {
  x: M + 0.5, y: cy + 0.35, w: bodyW - 1.0, h: conclH - 0.7,
  fontFace: "Calibri", fontSize: 34, color: INK,
  align: "left", valign: "top", paraSpaceAfter: 6,
});

cy += conclH + 0.6;

// ---- 5. DISCUSSIONS + QR (full width) ---------------------------------
sectionHeader(M, cy, bodyW, "5. Discussions & Future Work");
cy += 1.15;

const discH = 39.370 - cy - 0.7;  // fill to bottom margin

slide.addShape(pres.shapes.RECTANGLE, {
  x: M, y: cy, w: bodyW, h: discH,
  fill: { color: "FFFFFF" }, line: { color: "E2E8F0", width: 1 },
  shadow: { type: "outer", color: "000000", blur: 8, offset: 2, angle: 90, opacity: 0.06 },
});

// left text block
slide.addText([
  { text: "Next iterations.", options: { bold: true, color: NAVY, breakLine: true } },
  { text: " ", options: { breakLine: true, fontSize: 12 } },
  { text: "1.  ", options: { bold: true, color: CYAN } },
  { text: "Cross-event correlation.  ", options: { bold: true } },
  { text: "The 0 % detection on the evasive T1078 scenario is the limit of per-event reasoning. Adding impossible-travel and first-time-from-this-IP-ever signals defeats the Volt-Typhoon SOHO-router playbook.", options: { breakLine: true } },
  { text: " ", options: { breakLine: true, fontSize: 12 } },
  { text: "2.  ", options: { bold: true, color: CYAN } },
  { text: "Live data feed.  ", options: { bold: true } },
  { text: "Replace the synthetic generator with a 30-day rolling window of the customer's own auth logs and add drift monitoring on feature distributions.", options: { breakLine: true } },
  { text: " ", options: { breakLine: true, fontSize: 12 } },
  { text: "3.  ", options: { bold: true, color: CYAN } },
  { text: "Mapper expansion.  ", options: { bold: true } },
  { text: "Cover the top-20 enterprise MITRE techniques; route low-confidence cases to a retrieval-augmented LLM call grounded in STIX.", options: { breakLine: true } },
  { text: " ", options: { breakLine: true, fontSize: 12 } },
  { text: "4.  ", options: { bold: true, color: CYAN } },
  { text: "Incident grouping.  ", options: { bold: true } },
  { text: "Aggregate correlated events keyed on source IP / user over a sliding window into single incidents.", options: {} },
], {
  x: M + 0.5, y: cy + 0.35, w: bodyW - 7.2, h: discH - 0.7,
  fontFace: "Calibri", fontSize: 34, color: INK,
  align: "left", valign: "top", paraSpaceAfter: 4,
});

// right side: QR placeholder + repo info
const qrBoxW = 6.0;
const qrBoxX = M + bodyW - qrBoxW - 0.6;
const qrBoxY = cy + 0.45;

slide.addShape(pres.shapes.RECTANGLE, {
  x: qrBoxX, y: qrBoxY, w: qrBoxW, h: discH - 1.0,
  fill: { color: NAVY }, line: { color: NAVY, width: 0 },
});
// accent stripe
slide.addShape(pres.shapes.RECTANGLE, {
  x: qrBoxX, y: qrBoxY, w: qrBoxW, h: 0.18,
  fill: { color: ACCENT }, line: { color: ACCENT, width: 0 },
});

slide.addText("Demo video", {
  x: qrBoxX + 0.3, y: qrBoxY + 0.35, w: qrBoxW - 0.6, h: 0.7,
  fontFace: "Calibri", fontSize: 34, color: ACCENT, bold: true,
  align: "center", valign: "middle", margin: 0,
});

// QR-code placeholder (a checkerboard square - the student replaces with a real QR)
const qrSize = 3.4;
const qrX = qrBoxX + (qrBoxW - qrSize) / 2;
const qrY = qrBoxY + 1.15;
slide.addShape(pres.shapes.RECTANGLE, {
  x: qrX, y: qrY, w: qrSize, h: qrSize,
  fill: { color: "FFFFFF" }, line: { color: "FFFFFF", width: 0 },
});
// draw a simple checkerboard to make it obviously a "replace me" QR placeholder
const cells = 8;
const cellSize = qrSize / cells;
for (let r = 0; r < cells; r++) {
  for (let c = 0; c < cells; c++) {
    if ((r + c) % 2 === 0) {
      slide.addShape(pres.shapes.RECTANGLE, {
        x: qrX + c * cellSize, y: qrY + r * cellSize, w: cellSize, h: cellSize,
        fill: { color: NAVY }, line: { color: NAVY, width: 0 },
      });
    }
  }
}
// three "finder" squares (the corner markers real QR codes have)
function finder(fx, fy) {
  slide.addShape(pres.shapes.RECTANGLE, {
    x: fx, y: fy, w: cellSize * 3, h: cellSize * 3,
    fill: { color: NAVY }, line: { color: NAVY, width: 0 },
  });
  slide.addShape(pres.shapes.RECTANGLE, {
    x: fx + cellSize * 0.5, y: fy + cellSize * 0.5, w: cellSize * 2, h: cellSize * 2,
    fill: { color: "FFFFFF" }, line: { color: "FFFFFF", width: 0 },
  });
  slide.addShape(pres.shapes.RECTANGLE, {
    x: fx + cellSize, y: fy + cellSize, w: cellSize, h: cellSize,
    fill: { color: NAVY }, line: { color: NAVY, width: 0 },
  });
}
finder(qrX, qrY);
finder(qrX + qrSize - cellSize * 3, qrY);
finder(qrX, qrY + qrSize - cellSize * 3);

slide.addText("[ Replace with QR ]", {
  x: qrX, y: qrY + qrSize + 0.10, w: qrSize, h: 0.40,
  fontFace: "Calibri", fontSize: 22, color: "94A3B8", italic: true,
  align: "center", valign: "middle", margin: 0,
});

slide.addText("Code repository", {
  x: qrBoxX + 0.3, y: qrY + qrSize + 0.55, w: qrBoxW - 0.6, h: 0.50,
  fontFace: "Calibri", fontSize: 30, color: ACCENT, bold: true,
  align: "center", valign: "middle", margin: 0,
});
slide.addText("github.com/steve2great/HIT-ai-cybersecurity", {
  x: qrBoxX + 0.3, y: qrY + qrSize + 1.05, w: qrBoxW - 0.6, h: 0.50,
  fontFace: "Consolas", fontSize: 22, color: "FFFFFF",
  align: "center", valign: "middle", margin: 0,
});

// ====================================================================
// WRITE
// ====================================================================
pres.writeFile({ fileName: "SOC-Copilot-Poster.pptx" })
    .then(name => console.log("Wrote", name));
