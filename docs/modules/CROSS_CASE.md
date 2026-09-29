# Module: Cross-Case Intelligence

## 1. Purpose
The Cross-Case Intelligence module detects coordinated disinformation campaigns, recurring threat actors, and re-used synthetic media assets across multiple distinct investigations without compromising tenant data confidentiality.

---

## 2. Input
- **Active Case Repository:** Collection of indexed cases, evidence items, and cryptographic fingerprints across the organization.
- **Query Item:** An evidence asset, hash, actor handle, or forensic signature being analyzed in an active investigation.

---

## 3. Processing Pipeline

1. **Fingerprint & Signature Indexing:**
   - Extracts and indexes invariant fingerprints for every processed asset: perceptual hashes (pHash), cryptographic hashes (SHA-256), audio acoustic centroids, and generator artifact signatures.
2. **Graph-Based Entity Resolution:**
   - Constructs a cross-case entity graph connecting cases, evidence files, threat actor personas, external URLs, and shared forensic traits.
3. **Similarity Clustering & Campaign Detection:**
   - Identifies clusters of cases sharing near-identical media or identical synthetic generation parameters.
   - Detects when the same synthetic voice model or generative seed is deployed across seemingly unrelated cases.
4. **Privacy-Preserving Cross-Case Correlation:**
   - Enables multi-investigator pattern matching while adhering to case permission boundaries; informs investigators of related cases without exposing restricted confidential details.

---

## 4. Output
- **Related Cases Matrix:** Ranked list of past cases sharing identical or derivative media assets.
- **Campaign Association Alert:** Notification when an asset matches known patterns of a recurring disinformation campaign.
- **Cross-Case Graph Visualization:** Interactive node-link diagram illustrating interconnected cases, shared media nodes, and threat vectors.

---

## 5. Evidence Generated
- Exact match indicators (identical SHA-256 discovered in earlier cases).
- Near-duplicate similarity scores and perceptual hash distance.
- Campaign cluster identifier and chronological propagation timeline.

---

## 6. Limitations
- Cross-case correlation effectiveness depends on the volume and diversity of historical cases stored in the platform's database.
- Completely novel, one-off attacks that share no common assets or technical signatures will not trigger cross-case linkages.
