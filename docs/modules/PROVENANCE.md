# Module: Provenance & Source Intelligence

## 1. Purpose
The Provenance & Source Intelligence module establishes the digital genealogy of media items, tracking earliest discovered appearances, reverse-image circulation histories, derivative manipulations, and cryptographic lineage across web platforms and social networks.

---

## 2. Input
- **Target Media Item:** Image or video file.
- **Perceptual Fingerprints:** Perceptual hashes (pHash, dHash, aHash) and deep visual feature embeddings.
- **Optional Context:** URLs, platform metadata, or claims regarding where the media originated.

---

## 3. Processing Pipeline

1. **Perceptual Fingerprint Generation:**
   - Computes robust 64-bit perceptual hashes (DCT-based pHash, gradient-based dHash, average aHash).
   - Generates high-dimensional visual feature vectors for similarity search invariant to minor resizing, cropping, or compression.
2. **Media Genealogy Graph Construction:**
   - Queries historical indexed media repositories for near-duplicate visual matches.
   - Evaluates Hamming distance between perceptual hashes (Hamming distance $\le 10$ flagged as derivative/match).
3. **Earliest Discovered Source Discovery:**
   - Orders all discovered instances chronologically by timestamp (file creation metadata, web crawl timestamps, platform upload dates).
   - Identifies the earliest discovered public appearance (strictly labeled "earliest discovered source", avoiding definitive claims of absolute original origin).
4. **Circulation Network Analysis:**
   - Maps the spread of the media across platforms, domains, and social networks over time.
   - Calculates circulation velocity and platform hop count.
5. **Transformation Tracking:**
   - Analyzes differences between the query item and discovered earlier variants to detect where visual alterations (text overlay, face modification, cropping) were introduced.

---

## 4. Output
- **Genealogy Graph:** Directed acyclic graph (DAG) showing relationships between ancestor and descendant media variants.
- **Earliest Discovered Source Record:** URL, timestamp, platform, and hash of earliest known version.
- **Perceptual Match List:** Ranked list of similar media items with similarity percentages and Hamming distances.
- **Circulation Velocity Metric:** Rate of spread across indexed platforms.

---

## 5. Evidence Generated
- Immutable perceptual hashes (pHash, dHash, aHash).
- Match confidence scores and modification diffs against ancestor versions.
- Interactive genealogy graph visualization nodes and edges.
- Timestamped provenance timeline.

---

## 6. Limitations
- Does not have real-time access to private messaging platforms (WhatsApp, Telegram private channels, Signal).
- Content behind authentication paywalls or deleted from web servers cannot be retroactively discovered.
- Significant cropping ($> 50\%$) or radical color inversions can shift perceptual hashes beyond automated matching thresholds.
