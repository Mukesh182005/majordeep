# Module: AI-Assisted Investigation

## 1. Purpose
The AI-Assisted Investigation module acts as an intelligent forensic co-pilot, translating complex multi-signal forensic outputs into clear natural language explanations, formulating initial investigation hypotheses, and recommending targeted verification steps for human analysts.

---

## 2. Input
- **Forensic Pipeline Telemetry:** Raw risk scores, signal heatmaps, camera metadata, audio acoustics, and temporal video logs.
- **Investigator Queries:** Natural language inquiries submitted by the analyst (e.g., "Explain why the CFA score is low while the neural score is high", "Suggest next steps to verify this voice recording").
- **Case Context:** Current evidence list and case notes.

---

## 3. Processing Pipeline

1. **Telemetry Normalization & Context Structuring:**
   - Aggregates multi-modal telemetry into a structured JSON forensic fact sheet.
   - Formulates clear factual boundaries to prevent model hallucination (e.g., explicitly bounding confidence levels and noting unverified signals).
2. **Forensic Reasoner & Hypothesis Engine:**
   - Evaluates combinations of signals against established forensic heuristic rules (e.g., high compression + authentic CFA = likely legitimate social media upload; high FFT periodic peaks + missing CFA = likely synthetic GAN/diffusion output).
   - Generates ranked plausible hypotheses for investigator review.
3. **Natural Language Explanation Generation:**
   - Synthesizes findings into plain English explanations suitable for non-technical stakeholders, legal counsel, or academic reviewers.
4. **Interactive Analyst Q&A:**
   - Provides a conversational interface allowing analysts to probe specific technical anomalies, ask for clarification on terminology, and receive suggested verification checklists.

---

## 4. Output
- **Executive Technical Summary:** Concise 3-4 sentence explanation of the platform's findings.
- **Hypothesis Recommendations:** Formulated investigation angles with supporting/refuting points.
- **Actionable Next Steps:** Recommended manual verification actions (e.g., "Inspect audio background noise between seconds 0:14 and 0:18", "Request original camera memory card").
- **Conversational Responses:** Explanations of complex forensic terms (ELA, CFA, PRNU, ENF) in the context of the current file.

---

## 5. Evidence Generated
- AI Co-pilot reasoning trace linked to underlying mathematical signal values.
- Investigator query and assistant response log preserved in case audit trail.
- Generated hypothesis checklist items.

---

## 6. Limitations
- AI co-pilot explanations are advisory and assistive; they do not constitute autonomous expert witness testimony or judicial findings.
- The assistant is strictly grounded in the telemetry extracted from the file; it cannot speculate on intent, legal culpability, or real-world events beyond the technical data.
