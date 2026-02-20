# backend/database/db.py
import os
import json
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
USE_DB = bool(DATABASE_URL)

# ─────────────────────────────────────────────────────
# Smart switch:
# No DATABASE_URL → uses JSON files (safe fallback)
# Has DATABASE_URL  → uses MySQL via SQLAlchemy
# ─────────────────────────────────────────────────────

if USE_DB:
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker

    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,       # auto-reconnect if connection drops
        pool_recycle=3600,        # recycle connections every hour
        echo=False                # set True to log all SQL queries
    )

    SessionLocal = sessionmaker(bind=engine)

    def query(sql: str, params: list = None, fetch: str = "all"):
        """
        Run a raw SQL query.
        fetch="all"  → list of dicts
        fetch="one"  → single dict or None
        fetch=None   → no return (INSERT/UPDATE/DELETE)
        """
        with engine.connect() as conn:
            result = conn.execute(text(sql), params or {})
            conn.commit()

            if fetch == "one":
                row = result.fetchone()
                return dict(row._mapping) if row else None
            elif fetch == "all":
                rows = result.fetchall()
                return [dict(r._mapping) for r in rows]
            return None

else:
    # ─── JSON fallback for when no DB is configured ───
    DATA_DIR = "data"
    os.makedirs(DATA_DIR, exist_ok=True)

    def load_json(filename: str) -> dict:
        path = os.path.join(DATA_DIR, filename)
        if not os.path.exists(path):
            with open(path, "w") as f:
                json.dump({}, f)
        with open(path, "r") as f:
            return json.load(f)

    def save_json(filename: str, data: dict):
        path = os.path.join(DATA_DIR, filename)
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    def query(sql: str, params: list = None, fetch: str = "all"):
        raise RuntimeError("No DATABASE_URL set. Add it to .env to use MySQL.")


# ─────────────────────────────────────────────────────
# MIGRATION: JSON files → MySQL
# Run: python database/db.py
# ─────────────────────────────────────────────────────

def migrate_json_to_mysql():
    if not USE_DB:
        print("❌ No DATABASE_URL in .env - set it first!")
        return

    DATA_DIR = "data"

    def load(f):
        path = os.path.join(DATA_DIR, f)
        if not os.path.exists(path):
            return {}
        with open(path) as file:
            return json.load(file)

    print("🔄 Migrating JSON data → MySQL...\n")

    # ─── Users ───
    try:
        users = load("users.json")
        count = 0
        for uid, u in users.items():
            query("""
                INSERT IGNORE INTO users
                    (uid, email, username, role, avatar_url, bio, credit_balance, created_at)
                VALUES
                    (:uid, :email, :username, :role, :avatar_url, :bio, :credit_balance, :created_at)
            """, {
                "uid": u["uid"],
                "email": u["email"],
                "username": u["username"],
                "role": u["role"],
                "avatar_url": u.get("avatar_url"),
                "bio": u.get("bio"),
                "credit_balance": u.get("credit_balance", 0),
                "created_at": u.get("created_at")
            }, fetch=None)
            count += 1
        print(f"  ✅ Migrated {count} users")
    except Exception as e:
        print(f"  ❌ Users error: {e}")

    # ─── Series ───
    try:
        series = load("series.json")
        count = 0
        for sid, s in series.items():
            query("""
                INSERT IGNORE INTO series
                    (id, creator_uid, title, description, cover_image_url,
                     genre, tags, is_published, view_count, created_at, published_at)
                VALUES
                    (:id, :creator_uid, :title, :description, :cover_image_url,
                     :genre, :tags, :is_published, :view_count, :created_at, :published_at)
            """, {
                "id": s["id"],
                "creator_uid": s["creator_uid"],
                "title": s["title"],
                "description": s.get("description"),
                "cover_image_url": s.get("cover_image_url"),
                "genre": s.get("genre"),
                "tags": s.get("tags"),
                "is_published": 1 if s.get("is_published") else 0,
                "view_count": s.get("view_count", 0),
                "created_at": s.get("created_at"),
                "published_at": s.get("published_at")
            }, fetch=None)
            count += 1
        print(f"  ✅ Migrated {count} series")
    except Exception as e:
        print(f"  ❌ Series error: {e}")

    # ─── Episodes ───
    try:
        episodes = load("episodes.json")
        count = 0
        for eid, ep in episodes.items():
            query("""
                INSERT IGNORE INTO episodes
                    (id, series_id, creator_uid, episode_number, title,
                     thumbnail_url, is_published, view_count, created_at, published_at)
                VALUES
                    (:id, :series_id, :creator_uid, :episode_number, :title,
                     :thumbnail_url, :is_published, :view_count, :created_at, :published_at)
            """, {
                "id": ep["id"],
                "series_id": ep["series_id"],
                "creator_uid": ep["creator_uid"],
                "episode_number": ep["episode_number"],
                "title": ep["title"],
                "thumbnail_url": ep.get("thumbnail_url"),
                "is_published": 1 if ep.get("is_published") else 0,
                "view_count": ep.get("view_count", 0),
                "created_at": ep.get("created_at"),
                "published_at": ep.get("published_at")
            }, fetch=None)
            count += 1
        print(f"  ✅ Migrated {count} episodes")
    except Exception as e:
        print(f"  ❌ Episodes error: {e}")

    # ─── Credits ───
    try:
        credits = load("credits.json")
        count = 0
        for uid, c in credits.items():
            query(
                "UPDATE users SET credit_balance = :bal WHERE uid = :uid",
                {"bal": c.get("balance", 0), "uid": uid},
                fetch=None
            )
            count += 1
        print(f"  ✅ Migrated {count} credit balances")
    except Exception as e:
        print(f"  ❌ Credits error: {e}")

    print("\n🎉 Migration complete! Your MySQL database is ready.")


if __name__ == "__main__":
    migrate_json_to_mysql()