# backend/database/setup.py
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

def create_tables():
    engine = create_engine(DATABASE_URL)

    with engine.connect() as conn:
        print("🚀 Creating PanelX MySQL tables...")

        # ─── USERS ───
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS users (
                uid VARCHAR(128) PRIMARY KEY,
                email VARCHAR(255) UNIQUE NOT NULL,
                username VARCHAR(50) UNIQUE NOT NULL,
                role VARCHAR(20) NOT NULL,
                avatar_url VARCHAR(500),
                bio TEXT,
                credit_balance INT DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            );
        """))
        print("  ✅ users table")

        # ─── SERIES ───
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS series (
                id VARCHAR(50) PRIMARY KEY,
                creator_uid VARCHAR(128) NOT NULL,
                title VARCHAR(200) NOT NULL,
                description TEXT,
                cover_image_url VARCHAR(500),
                genre VARCHAR(100),
                tags VARCHAR(500),
                status VARCHAR(20) DEFAULT 'ongoing',
                is_published TINYINT(1) DEFAULT 0,
                view_count INT DEFAULT 0,
                like_count INT DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                published_at DATETIME,
                FOREIGN KEY (creator_uid) REFERENCES users(uid) ON DELETE CASCADE,
                INDEX idx_series_creator (creator_uid),
                INDEX idx_series_published (is_published)
            );
        """))
        print("  ✅ series table")

        # ─── EPISODES ───
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS episodes (
                id VARCHAR(50) PRIMARY KEY,
                series_id VARCHAR(50) NOT NULL,
                creator_uid VARCHAR(128) NOT NULL,
                episode_number INT NOT NULL,
                title VARCHAR(200) NOT NULL,
                thumbnail_url VARCHAR(500),
                is_published TINYINT(1) DEFAULT 0,
                view_count INT DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                published_at DATETIME,
                FOREIGN KEY (series_id) REFERENCES series(id) ON DELETE CASCADE,
                FOREIGN KEY (creator_uid) REFERENCES users(uid) ON DELETE CASCADE,
                UNIQUE KEY unique_episode (series_id, episode_number),
                INDEX idx_episodes_series (series_id),
                INDEX idx_episodes_creator (creator_uid)
            );
        """))
        print("  ✅ episodes table")

        # ─── PANELS ───
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS panels (
                id VARCHAR(50) PRIMARY KEY,
                episode_id VARCHAR(50) NOT NULL,
                panel_order INT NOT NULL,
                image_url VARCHAR(500) NOT NULL,
                width INT DEFAULT 800,
                height INT DEFAULT 1200,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (episode_id) REFERENCES episodes(id) ON DELETE CASCADE,
                INDEX idx_panels_episode (episode_id)
            );
        """))
        print("  ✅ panels table")

        # ─── DIALOGUES ───
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS dialogues (
                id VARCHAR(50) PRIMARY KEY,
                panel_id VARCHAR(50) NOT NULL,
                text_content TEXT NOT NULL,
                position_x FLOAT DEFAULT 10,
                position_y FLOAT DEFAULT 10,
                font_size INT DEFAULT 14,
                font_color VARCHAR(20) DEFAULT '#000000',
                bg_color VARCHAR(20) DEFAULT '#FFFFFF',
                dialogue_order INT DEFAULT 0,
                FOREIGN KEY (panel_id) REFERENCES panels(id) ON DELETE CASCADE,
                INDEX idx_dialogues_panel (panel_id)
            );
        """))
        print("  ✅ dialogues table")

        # ─── READING PROGRESS ───
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS reading_progress (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_uid VARCHAR(128) NOT NULL,
                series_id VARCHAR(50) NOT NULL,
                episode_id VARCHAR(50) NOT NULL,
                last_panel_viewed INT DEFAULT 0,
                completed TINYINT(1) DEFAULT 0,
                last_read_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (user_uid) REFERENCES users(uid) ON DELETE CASCADE,
                FOREIGN KEY (series_id) REFERENCES series(id) ON DELETE CASCADE,
                FOREIGN KEY (episode_id) REFERENCES episodes(id) ON DELETE CASCADE,
                UNIQUE KEY unique_progress (user_uid, episode_id),
                INDEX idx_progress_user (user_uid)
            );
        """))
        print("  ✅ reading_progress table")

        # ─── BOOKMARKS ───
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS bookmarks (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_uid VARCHAR(128) NOT NULL,
                series_id VARCHAR(50) NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_uid) REFERENCES users(uid) ON DELETE CASCADE,
                FOREIGN KEY (series_id) REFERENCES series(id) ON DELETE CASCADE,
                UNIQUE KEY unique_bookmark (user_uid, series_id),
                INDEX idx_bookmarks_user (user_uid)
            );
        """))
        print("  ✅ bookmarks table")

        # ─── LIKES ───
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS likes (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_uid VARCHAR(128) NOT NULL,
                series_id VARCHAR(50),
                episode_id VARCHAR(50),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_uid) REFERENCES users(uid) ON DELETE CASCADE,
                FOREIGN KEY (series_id) REFERENCES series(id) ON DELETE CASCADE,
                FOREIGN KEY (episode_id) REFERENCES episodes(id) ON DELETE CASCADE,
                UNIQUE KEY unique_like (user_uid, series_id, episode_id)
            );
        """))
        print("  ✅ likes table")

        # ─── CREDIT TRANSACTIONS ───
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS credit_transactions (
                id VARCHAR(50) PRIMARY KEY,
                user_uid VARCHAR(128) NOT NULL,
                transaction_type VARCHAR(20) NOT NULL,
                amount INT NOT NULL,
                balance_after INT NOT NULL,
                description TEXT,
                payment_id VARCHAR(100),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_uid) REFERENCES users(uid) ON DELETE CASCADE,
                INDEX idx_tx_user (user_uid)
            );
        """))
        print("  ✅ credit_transactions table")

        # ─── PAYMENTS ───
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS payments (
                id VARCHAR(50) PRIMARY KEY,
                user_uid VARCHAR(128) NOT NULL,
                payment_provider VARCHAR(30) DEFAULT 'paymongo',
                provider_payment_id VARCHAR(100) UNIQUE NOT NULL,
                amount_cents INT NOT NULL,
                credits_purchased INT NOT NULL,
                status VARCHAR(20) DEFAULT 'pending',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                completed_at DATETIME,
                FOREIGN KEY (user_uid) REFERENCES users(uid) ON DELETE CASCADE,
                INDEX idx_payments_user (user_uid)
            );
        """))
        print("  ✅ payments table")

        # ─── CREDIT PACKAGES ───
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS credit_packages (
                id VARCHAR(50) PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                credits INT NOT NULL,
                price_cents INT NOT NULL,
                price_display VARCHAR(20) NOT NULL,
                per_credit VARCHAR(20),
                badge VARCHAR(50),
                is_active TINYINT(1) DEFAULT 1,
                display_order INT DEFAULT 0
            );
        """))

        conn.execute(text("""
            INSERT IGNORE INTO credit_packages
                (id, name, credits, price_cents, price_display, per_credit, badge, display_order)
            VALUES
                ('starter', 'Starter', 50,   499,  '$4.99',  '$0.10/image', NULL,           1),
                ('creator', 'Creator', 150,  999,  '$9.99',  '$0.07/image', 'Most Popular', 2),
                ('pro',     'Pro',     400,  1999, '$19.99', '$0.05/image', 'Best Value',   3),
                ('studio',  'Studio',  1000, 3999, '$39.99', '$0.04/image', NULL,           4);
        """))
        print("  ✅ credit_packages table + default packages")

        conn.commit()

    print("\n🎉 All tables created successfully!")
    print("➡️  Next: run 'python database/db.py' to migrate your JSON data")


if __name__ == "__main__":
    try:
        create_tables()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\n🔧 Make sure:")
        print("  1. MySQL is running")
        print("  2. DATABASE_URL is set in .env")
        print("  3. panelx_db database exists")
        print("\n  Run in MySQL first:")
        print("  CREATE DATABASE panelx_db;")