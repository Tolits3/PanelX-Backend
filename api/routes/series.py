# backend/api/routes/series.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List
import json, os, uuid

router = APIRouter()

SERIES_FILE = "data/series.json"
EPISODES_FILE = "data/episodes.json"
PANELS_FILE = "data/panels.json"

for f in [SERIES_FILE, EPISODES_FILE, PANELS_FILE]:
    os.makedirs("data", exist_ok=True)
    if not os.path.exists(f):
        with open(f, "w") as file:
            json.dump({}, file)

# ─────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────
def load(filepath):
    try:
        with open(filepath, "r") as f:
            return json.load(f)
    except:
        return {}

def save(filepath, data):
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)

def gen_id(prefix):
    return f"{prefix}_{uuid.uuid4().hex[:10]}"

# ─────────────────────────────────────────
# MODELS
# ─────────────────────────────────────────
class CreateSeriesRequest(BaseModel):
    creator_uid: str
    title: str
    description: Optional[str] = ""
    genre: Optional[str] = ""
    tags: Optional[str] = ""
    cover_image_url: Optional[str] = ""

class UpdateSeriesRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    genre: Optional[str] = None
    tags: Optional[str] = None
    cover_image_url: Optional[str] = None

class CreateEpisodeRequest(BaseModel):
    series_id: str
    creator_uid: str
    title: str
    episode_number: Optional[int] = None

class UpdateEpisodeRequest(BaseModel):
    title: Optional[str] = None
    thumbnail_url: Optional[str] = None

class SavePanelsRequest(BaseModel):
    episode_id: str
    creator_uid: str
    panels: List[dict]  # [{image_url, order, dialogues: [...]}]

# ─────────────────────────────────────────
# SERIES ROUTES
# ─────────────────────────────────────────

@router.post("/create")
async def create_series(req: CreateSeriesRequest):
    """Create a new series (starts as draft)"""
    series = load(SERIES_FILE)
    series_id = gen_id("series")

    series[series_id] = {
        "id": series_id,
        "creator_uid": req.creator_uid,
        "title": req.title,
        "description": req.description,
        "genre": req.genre,
        "tags": req.tags,
        "cover_image_url": req.cover_image_url,
        "is_published": False,
        "status": "ongoing",
        "view_count": 0,
        "like_count": 0,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "published_at": None,
    }

    save(SERIES_FILE, series)
    return {"success": True, "series": series[series_id]}

@router.get("/all")
async def get_all_published():
    """Get all published series for reader home"""
    series = load(SERIES_FILE)
    episodes = load(EPISODES_FILE)

    published = []
    for s in series.values():
        if s.get("is_published"):
            # Count published episodes
            ep_count = sum(
                1 for e in episodes.values()
                if e.get("series_id") == s["id"] and e.get("is_published")
            )
            s["episode_count"] = ep_count
            published.append(s)

    # Sort newest first
    published.sort(key=lambda x: x.get("published_at") or x["created_at"], reverse=True)
    return {"success": True, "series": published}

@router.get("/trending")
async def get_trending():
    """Get trending series (most viewed)"""
    series = load(SERIES_FILE)
    episodes = load(EPISODES_FILE)

    published = [s for s in series.values() if s.get("is_published")]

    for s in published:
        ep_count = sum(
            1 for e in episodes.values()
            if e.get("series_id") == s["id"] and e.get("is_published")
        )
        s["episode_count"] = ep_count

    # Sort by view count
    published.sort(key=lambda x: x.get("view_count", 0), reverse=True)
    return {"success": True, "series": published[:10]}  # Top 10

@router.get("/creator/{uid}")
async def get_creator_series(uid: str):
    """Get all series by a creator (drafts + published)"""
    series = load(SERIES_FILE)
    episodes = load(EPISODES_FILE)

    creator_series = []
    for s in series.values():
        if s.get("creator_uid") == uid:
            # Count all episodes (including drafts)
            all_eps = [e for e in episodes.values() if e.get("series_id") == s["id"]]
            published_eps = [e for e in all_eps if e.get("is_published")]
            s["total_episodes"] = len(all_eps)
            s["published_episodes"] = len(published_eps)
            creator_series.append(s)

    creator_series.sort(key=lambda x: x["created_at"], reverse=True)
    return {"success": True, "series": creator_series}

@router.get("/{series_id}")
async def get_series(series_id: str):
    """Get a single series with its episodes"""
    series = load(SERIES_FILE)
    episodes = load(EPISODES_FILE)

    if series_id not in series:
        raise HTTPException(status_code=404, detail="Series not found")

    s = series[series_id]

    # Get published episodes for this series
    eps = [
        e for e in episodes.values()
        if e.get("series_id") == series_id and e.get("is_published")
    ]
    eps.sort(key=lambda x: x.get("episode_number", 0))
    s["episodes"] = eps

    # Increment view count
    series[series_id]["view_count"] = s.get("view_count", 0) + 1
    save(SERIES_FILE, series)

    return {"success": True, "series": s}

@router.put("/{series_id}")
async def update_series(series_id: str, req: UpdateSeriesRequest):
    series = load(SERIES_FILE)
    if series_id not in series:
        raise HTTPException(status_code=404, detail="Series not found")

    for field, value in req.dict(exclude_none=True).items():
        series[series_id][field] = value
    series[series_id]["updated_at"] = datetime.now().isoformat()

    save(SERIES_FILE, series)
    return {"success": True, "series": series[series_id]}

@router.post("/{series_id}/publish")
async def toggle_publish_series(series_id: str):
    """Toggle series published status"""
    series = load(SERIES_FILE)
    if series_id not in series:
        raise HTTPException(status_code=404, detail="Series not found")

    current = series[series_id]["is_published"]
    series[series_id]["is_published"] = not current
    series[series_id]["updated_at"] = datetime.now().isoformat()

    if not current:  # Publishing now
        series[series_id]["published_at"] = datetime.now().isoformat()

    save(SERIES_FILE, series)

    action = "published" if not current else "unpublished"
    return {
        "success": True,
        "is_published": not current,
        "message": f"Series {action} successfully"
    }

@router.delete("/{series_id}")
async def delete_series(series_id: str):
    series = load(SERIES_FILE)
    if series_id not in series:
        raise HTTPException(status_code=404, detail="Series not found")
    del series[series_id]
    save(SERIES_FILE, series)
    return {"success": True, "message": "Series deleted"}

# ─────────────────────────────────────────
# EPISODE ROUTES
# ─────────────────────────────────────────

@router.post("/episode/create")
async def create_episode(req: CreateEpisodeRequest):
    """Create a new episode under a series"""
    episodes = load(EPISODES_FILE)
    series = load(SERIES_FILE)

    if req.series_id not in series:
        raise HTTPException(status_code=404, detail="Series not found")

    # Auto-assign episode number
    existing = [e for e in episodes.values() if e.get("series_id") == req.series_id]
    ep_number = req.episode_number or (len(existing) + 1)

    ep_id = gen_id("ep")
    episodes[ep_id] = {
        "id": ep_id,
        "series_id": req.series_id,
        "creator_uid": req.creator_uid,
        "episode_number": ep_number,
        "title": req.title,
        "thumbnail_url": "",
        "is_published": False,
        "view_count": 0,
        "created_at": datetime.now().isoformat(),
        "published_at": None,
    }

    save(EPISODES_FILE, episodes)
    return {"success": True, "episode": episodes[ep_id]}

@router.get("/episode/creator/{uid}")
async def get_creator_episodes(uid: str):
    """Get all episodes by creator"""
    episodes = load(EPISODES_FILE)
    series = load(SERIES_FILE)

    eps = []
    for e in episodes.values():
        if e.get("creator_uid") == uid:
            # Add series title
            s = series.get(e["series_id"], {})
            e["series_title"] = s.get("title", "Unknown Series")
            e["series_cover"] = s.get("cover_image_url", "")
            eps.append(e)

    eps.sort(key=lambda x: x["created_at"], reverse=True)
    return {"success": True, "episodes": eps}

@router.get("/episode/{episode_id}")
async def get_episode(episode_id: str):
    """Get episode with its panels"""
    episodes = load(EPISODES_FILE)
    panels_data = load(PANELS_FILE)

    if episode_id not in episodes:
        raise HTTPException(status_code=404, detail="Episode not found")

    ep = episodes[episode_id]

    # Get panels sorted by order
    panels = [
        p for p in panels_data.values()
        if p.get("episode_id") == episode_id
    ]
    panels.sort(key=lambda x: x.get("panel_order", 0))
    ep["panels"] = panels

    # Increment view count
    episodes[episode_id]["view_count"] = ep.get("view_count", 0) + 1
    save(EPISODES_FILE, episodes)

    return {"success": True, "episode": ep}

@router.post("/episode/{episode_id}/publish")
async def toggle_publish_episode(episode_id: str):
    """Toggle episode published status"""
    episodes = load(EPISODES_FILE)
    if episode_id not in episodes:
        raise HTTPException(status_code=404, detail="Episode not found")

    current = episodes[episode_id]["is_published"]
    episodes[episode_id]["is_published"] = not current
    if not current:
        episodes[episode_id]["published_at"] = datetime.now().isoformat()

    save(EPISODES_FILE, episodes)

    action = "published" if not current else "unpublished"
    return {
        "success": True,
        "is_published": not current,
        "message": f"Episode {action} successfully"
    }

# ─────────────────────────────────────────
# PANELS ROUTES
# ─────────────────────────────────────────

@router.post("/episode/{episode_id}/panels/save")
async def save_panels(episode_id: str, req: SavePanelsRequest):
    """Save/reorder panels for an episode"""
    panels_data = load(PANELS_FILE)
    episodes = load(EPISODES_FILE)

    if episode_id not in episodes:
        raise HTTPException(status_code=404, detail="Episode not found")

    # Remove existing panels for this episode
    panels_data = {
        k: v for k, v in panels_data.items()
        if v.get("episode_id") != episode_id
    }

    # Save new panels with order
    for i, panel in enumerate(req.panels):
        panel_id = panel.get("id") or gen_id("panel")
        panels_data[panel_id] = {
            "id": panel_id,
            "episode_id": episode_id,
            "panel_order": i,
            "image_url": panel.get("image_url", ""),
            "dialogues": panel.get("dialogues", []),
            "width": panel.get("width", 800),
            "height": panel.get("height", 1200),
            "created_at": datetime.now().isoformat(),
        }

    save(PANELS_FILE, panels_data)

    # Update episode thumbnail to first panel
    if req.panels and req.panels[0].get("image_url"):
        episodes[episode_id]["thumbnail_url"] = req.panels[0]["image_url"]
        save(EPISODES_FILE, episodes)

    return {
        "success": True,
        "panels_saved": len(req.panels),
        "message": "Panels saved successfully"
    }