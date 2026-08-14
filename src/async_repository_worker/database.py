from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import aiosqlite


class Database:
    def __init__(self, path: str = "repositories.db") -> None:
        self._path = path
        self._conn: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        self._conn = await aiosqlite.connect(self._path)
        self._conn.row_factory = aiosqlite.Row

        await self._conn.execute("PRAGMA foreign_keys = ON")
        await self._conn.execute("PRAGMA journal_mode = WAL")

        await self._init_tables()

    async def _init_tables(self) -> None:
        await self._conn.execute("""
            CREATE TABLE IF NOT EXISTS repositories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner TEXT NOT NULL,
                name TEXT NOT NULL,
                full_name TEXT NOT NULL UNIQUE,
                description TEXT,
                language TEXT,
                stars INTEGER DEFAULT 0,
                forks INTEGER DEFAULT 0,
                open_issues INTEGER DEFAULT 0,
                topics TEXT,
                created_at TEXT,
                updated_at TEXT,
                pushed_at TEXT,
                homepage TEXT,
                license_name TEXT,
                archived INTEGER DEFAULT 0,
                disabled INTEGER DEFAULT 0,
                last_fetched TEXT NOT NULL
            )
        """)

        await self._conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS repositories_fts
            USING fts5(
                full_name,
                description,
                topics,
                content='repositories',
                content_rowid='id'
            )
        """)

        await self._conn.execute("""
            CREATE TRIGGER IF NOT EXISTS repositories_after_insert
            AFTER INSERT ON repositories
            BEGIN
                INSERT INTO repositories_fts(
                    rowid,
                    full_name,
                    description,
                    topics
                )
                VALUES (
                    NEW.id,
                    NEW.full_name,
                    NEW.description,
                    NEW.topics
                );
            END
        """)

        await self._conn.execute("""
            CREATE TRIGGER IF NOT EXISTS repositories_after_update
            AFTER UPDATE ON repositories
            BEGIN
                UPDATE repositories_fts
                SET
                    full_name = NEW.full_name,
                    description = NEW.description,
                    topics = NEW.topics
                WHERE rowid = NEW.id;
            END
        """)

        await self._conn.commit()

    async def insert_or_update(self, data: dict[str, Any]) -> int:
        now = datetime.now(timezone.utc).isoformat()

        license_name = None
        if data.get("license") and isinstance(data["license"], dict):
            license_name = data["license"].get("name")

        topics = data.get("topics", [])
        if not isinstance(topics, list):
            topics = []

        owner = data["owner"]
        if isinstance(owner, dict):
            owner = owner.get("login", "")

        cursor = await self._conn.execute("""
            INSERT INTO repositories (
                owner, name, full_name, description, language,
                stars, forks, open_issues, topics,
                created_at, updated_at, pushed_at, homepage,
                license_name, archived, disabled, last_fetched
            ) VALUES (
                :owner, :name, :full_name, :description, :language,
                :stars, :forks, :open_issues, :topics,
                :created_at, :updated_at, :pushed_at, :homepage,
                :license_name, :archived, :disabled, :last_fetched
            )
            ON CONFLICT(full_name) DO UPDATE SET
                description = excluded.description,
                language = excluded.language,
                stars = excluded.stars,
                forks = excluded.forks,
                open_issues = excluded.open_issues,
                topics = excluded.topics,
                updated_at = excluded.updated_at,
                pushed_at = excluded.pushed_at,
                license_name = excluded.license_name,
                archived = excluded.archived,
                disabled = excluded.disabled,
                last_fetched = excluded.last_fetched
        """, {
            "owner": owner,
            "name": data["name"],
            "full_name": data["full_name"],
            "description": data.get("description"),
            "language": data.get("language"),
            "stars": data.get("stargazers_count", 0),
            "forks": data.get("forks_count", 0),
            "open_issues": data.get("open_issues_count", 0),
            "topics": json.dumps(topics),
            "created_at": data.get("created_at"),
            "updated_at": data.get("updated_at"),
            "pushed_at": data.get("pushed_at"),
            "homepage": data.get("homepage"),
            "license_name": license_name,
            "archived": 1 if data.get("archived", False) else 0,
            "disabled": 1 if data.get("disabled", False) else 0,
            "last_fetched": now,
        })

        await self._conn.commit()
        return cursor.lastrowid

    async def search(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        cursor = await self._conn.execute("""
            SELECT
                r.id, r.owner, r.name, r.full_name,
                r.description, r.language, r.stars, r.forks,
                r.topics, r.updated_at, r.pushed_at, r.license_name
            FROM repositories r
            JOIN repositories_fts fts ON r.id = fts.rowid
            WHERE repositories_fts MATCH ?
            ORDER BY r.stars DESC
            LIMIT ?
        """, (query, limit))

        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def get_by_full_name(self, full_name: str) -> dict[str, Any] | None:
        cursor = await self._conn.execute(
            "SELECT * FROM repositories WHERE full_name = ?",
            (full_name,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def close(self) -> None:
        if self._conn:
            await self._conn.close()