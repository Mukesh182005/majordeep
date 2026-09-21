"""
Media Origin, Provenance & Circulation Intelligence (MOPCI) Engine.
Simulates internet-scale media forensics and source discovery.
"""

from __future__ import annotations

import random
from typing import Any
from datetime import datetime, timedelta

def generate_mopci_data(
    media_type: str, 
    is_fake: bool, 
    fake_prob: float, 
    file_dna: dict[str, Any]
) -> dict[str, Any]:
    """Generates procedurally structured MOPCI analysis data."""
    
    # 1. Provenance (C2PA)
    provenance = {
        "c2pa_present": random.choice([True, False]),
        "manifest_status": "Valid" if not is_fake else random.choice(["Valid", "Not detected", "Tampered"]),
        "signer": "Verified Publisher" if not is_fake else "Unknown Entity",
        "ai_assertion": is_fake,
        "editing_history": random.randint(0, 5)
    }

    # 2. Generation Attribution
    generation = {
        "likely_origin": "AI-generated" if is_fake else "Authentic / Camera",
        "generator_family": "Unknown",
        "confidence": round(fake_prob, 2),
        "evidence": []
    }
    
    if is_fake:
        if media_type == "image":
            generation["generator_family"] = random.choice(["Diffusion-based (SDXL/Flux)", "Midjourney v6", "DALL-E 3"])
            generation["evidence"] = ["Generator-specific frequency patterns", "Synthetic texture statistics", "Pixel-level artifacts"]
        elif media_type == "audio":
            generation["generator_family"] = random.choice(["Voice Cloning (ElevenLabs/VITS)", "Neural Vocoder", "TTS Synthesis"])
            generation["evidence"] = ["Phase discontinuities", "Glottal flow anomaly", "Vocoder artifacts"]
        elif media_type == "video":
            generation["generator_family"] = random.choice(["Face-Swap (Roop/Inswapper)", "Text-to-Video (Sora/Runway)", "Lip-Sync Manipulation"])
            generation["evidence"] = ["Temporal inconsistency", "Facial blending seams", "Motion anomalies"]
    else:
        generation["generator_family"] = file_dna.get("software", "Unknown Device/Software")
        generation["evidence"] = ["Natural sensor noise (PRNU)", "Standard codec signature", "Consistent physical lighting"]

    # 3. Source Discovery & Circulation
    base_date = datetime.now() - timedelta(days=random.randint(10, 300))
    
    source_candidates = [
        {
            "id": "src_1",
            "platform": "News Website" if not is_fake else "Obscure Forum",
            "url": "https://example.com/article/primary-source",
            "timestamp": base_date.strftime("%Y-%m-%d"),
            "similarity": 0.987,
            "transformation": "Original/Minor compression",
            "match_type": "Near-duplicate"
        },
        {
            "id": "src_2",
            "platform": "X (Twitter)",
            "url": "https://x.com/example/status/123",
            "timestamp": (base_date + timedelta(days=2)).strftime("%Y-%m-%d"),
            "similarity": 0.954,
            "transformation": "Crop + Resize",
            "match_type": "Near-duplicate"
        },
        {
            "id": "src_3",
            "platform": "Reddit",
            "url": "https://reddit.com/r/example/comments/456",
            "timestamp": (base_date + timedelta(days=5)).strftime("%Y-%m-%d"),
            "similarity": 0.912,
            "transformation": "Watermarked + Reposted",
            "match_type": "Perceptual Match"
        }
    ]

    earliest_source = source_candidates[0]
    
    # 4. Media Genealogy Graph
    nodes = [
        {"id": "origin", "label": "ORIGINAL GENERATION" if is_fake else "ORIGINAL CAPTURE", "type": "root"}
    ]
    edges = []
    
    prev_node = "origin"
    for i, src in enumerate(source_candidates):
        src_id = str(src["id"])
        nodes.append({"id": src_id, "label": f"{src['platform']} ({src['timestamp']})", "type": "node"})
        edges.append({"source": prev_node, "target": src_id, "label": "Circulated to" if i==0 else src["transformation"]})
        prev_node = src_id
        
    nodes.append({"id": "upload", "label": "User Upload", "type": "upload"})
    edges.append({"source": prev_node, "target": "upload", "label": "Current Copy"})

    genealogy = {
        "nodes": nodes,
        "edges": edges
    }

    # Assemble MOPCI payload
    return {
        "provenance": provenance,
        "generation_attribution": generation,
        "earliest_source": earliest_source,
        "source_candidates": source_candidates,
        "media_genealogy_graph": genealogy,
        "circulation_stats": {
            "websites": random.randint(2, 10),
            "social_platforms": random.randint(5, 25),
            "video_platforms": random.randint(0, 5),
            "versions_found": random.randint(10, 50)
        },
        "physical_world_consistency": {
            "lighting_shadows": "Inconsistent (Multiple light sources)" if is_fake and media_type != 'audio' else "Consistent",
            "perspective_geometry": "Anomalous" if is_fake and media_type != 'audio' else "Consistent",
            "temporal_motion": "Jitter detected" if is_fake and media_type == 'video' else "Consistent"
        }
    }
