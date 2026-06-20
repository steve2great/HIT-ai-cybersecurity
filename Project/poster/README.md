# Poster - final steps

## Files

| File | Purpose |
|------|---------|
| `SOC-Copilot-Poster.pptx` | The poster (B1 portrait, 70×100 cm). Compliant with the HIT spec - header, section order, all font sizes. |
| `build_poster.js` | Source code that generates the .pptx via pptxgenjs. Re-runnable. |
| `qa_check.py` | Layout QA - verifies size, bounds, and required text. |
| `poster.md` | The poster *content* in markdown (kept for reference). |

## Compliance with the HIT poster spec (Dr. Yakov Damatov)

| Requirement | Status |
|---|---|
| Size B1 70×100 cm | **70.00 × 100.00 cm** verified via XML |
| PowerPoint format | `.pptx` |
| Header section format unchanged | Logos area / project name / course / year / lecturer / participants - all present |
| Project name 74-78 pt | **76 pt** |
| Section titles 52-56 pt | **54 pt** |
| Year & semester 38-42 pt | **40 pt** |
| Lecturer & participant names 52-56 pt | **54 pt** |
| Course name 38-42 pt | **40 pt** |
| Body text 32-38 pt | **32-34 pt** |
| Body order: Introduction → ≤2 student sections → Conclusions → Discussions | Introduction → Methodology & Architecture → Results & Evaluation → Conclusions → Discussions (with QR) |
| QR code to demo video | Placeholder in place - student replaces with real QR |
| Two submission files (PPTX + PDF) | PPTX done; PDF must be exported (see below) |

## Final manual steps the student must do

### 1. Replace the QR-code placeholder with the real one

The current QR area shows a checkerboard placeholder that says *"[ Replace with QR ]"*. Steps to fix:

1. Upload the demo video to YouTube as **Unlisted**.
2. Copy the YouTube URL.
3. Generate a QR code from that URL - e.g. <https://www.qr-code-generator.com/>, <https://qr.io/>, or PowerPoint's built-in "Insert > Pictures > Stock Images > Icons > QR" (PowerPoint 365).
4. In `SOC-Copilot-Poster.pptx`, right-click the checkerboard QR → **Change Picture > From File** and pick your QR.

### 2. (Optional) Replace the HIT logo placeholder

The spec says header *format* must be unchanged. The HIT template usually has the institute logo top-left and the faculty logo top-right. The current poster includes the textual "Holon Institute of Technology - Faculty of Sciences" band but no logo image. If the official poster template (which the email mentions is in accordance with the limitations) is distributed by the course, paste my body content into it - easier than reproducing their exact logo placement.

### 3. Export to PDF

Open in PowerPoint and: **File → Save As → PDF** (or **File → Export → Create PDF/XPS**). Both required submission files (`.pptx` + `.pdf`) live next to each other in `Project/poster/`.

## To rebuild the poster

```bash
cd Project/poster
# requires: node + pptxgenjs (`npm install -g pptxgenjs`)
node build_poster.js
python3 qa_check.py   # re-runs the layout check
```
