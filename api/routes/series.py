from fastapi import APIRouter
from database.memory_optimized import query_optimized, cleanup_connections

router = APIRouter()

@router.get("/all")
def get_all_series():
    try:
        series = query_optimized(
            "SELECT id, title, description, cover_image_url, genre, tags, view_count, like_count, creator_uid FROM series WHERE is_published = 1 ORDER BY created_at DESC LIMIT 50",
            fetch="all"
        )
        return {"success": True, "series": series}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        cleanup_connections()