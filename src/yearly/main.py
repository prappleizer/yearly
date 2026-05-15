"""
main.py – YearView FastAPI backend.

Run with:
    uvicorn yearly.main:app --reload --port 3000

public/ and data/ are resolved relative to cwd (the repo root).
Override with env vars:
    YEARVIEW_PUBLIC=/path/to/public
    YEARVIEW_DB=/path/to/yearview.db
"""

import os
from contextlib import asynccontextmanager
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import PlainTextResponse
from fastapi.staticfiles import StaticFiles

from yearly.database import init_db, query_all, query_one, run
from yearly.models import EventCreate, EventUpdate, TagCreate, TagUpdate


def _public_dir() -> Path | None:
    env = os.environ.get("YEARVIEW_PUBLIC")
    candidate = Path(env) if env else Path.cwd() / "public"
    return candidate if candidate.is_dir() else None


# ─── Startup ─────────────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="YearView", lifespan=lifespan)


# ─── TAG ROUTES ──────────────────────────────────────────────────────────────


@app.get("/api/tags")
def get_tags():
    return query_all("SELECT * FROM tags ORDER BY sort_order, name")


@app.post("/api/tags", status_code=201)
def create_tag(body: TagCreate):
    max_row = query_one("SELECT MAX(sort_order) as max FROM tags")
    sort_order = (max_row["max"] or 0) + 1 if max_row else 1
    try:
        rowid, _ = run(
            "INSERT INTO tags (name, color, sort_order) VALUES (?, ?, ?)",
            [body.name, body.color or "#6b7280", sort_order],
        )
    except Exception as e:
        if "UNIQUE constraint" in str(e):
            raise HTTPException(400, "Tag name already exists")
        raise HTTPException(500, str(e))
    return query_one("SELECT * FROM tags WHERE id = ?", [rowid])


@app.put("/api/tags/{tag_id}")
def update_tag(tag_id: int, body: TagUpdate):
    existing = query_one("SELECT * FROM tags WHERE id = ?", [tag_id])
    if not existing:
        raise HTTPException(404, "Tag not found")
    run(
        "UPDATE tags SET name = ?, color = ?, sort_order = ? WHERE id = ?",
        [
            body.name if body.name is not None else existing["name"],
            body.color if body.color is not None else existing["color"],
            body.sort_order if body.sort_order is not None else existing["sort_order"],
            tag_id,
        ],
    )
    return query_one("SELECT * FROM tags WHERE id = ?", [tag_id])


@app.delete("/api/tags/{tag_id}")
def delete_tag(tag_id: int):
    _, changes = run("DELETE FROM tags WHERE id = ?", [tag_id])
    if changes == 0:
        raise HTTPException(404, "Tag not found")
    return {"success": True}


# ─── EVENT ROUTES ─────────────────────────────────────────────────────────────

_EVENT_SELECT = """
    SELECT e.*, t.name as tag_name, t.color as tag_color
    FROM events e
    LEFT JOIN tags t ON e.tag_id = t.id
"""


@app.get("/api/events")
def get_events(
    start: Optional[str] = Query(None),
    end: Optional[str] = Query(None),
    tag_id: Optional[int] = Query(None),
):
    sql = _EVENT_SELECT + " WHERE 1=1"
    params: list = []
    if start:
        sql += " AND e.end_date >= ?"
        params.append(start)
    if end:
        sql += " AND e.start_date <= ?"
        params.append(end)
    if tag_id is not None:
        sql += " AND e.tag_id = ?"
        params.append(tag_id)
    sql += " ORDER BY e.start_date, e.title"
    return query_all(sql, params)


@app.get("/api/events/{event_id}")
def get_event(event_id: int):
    event = query_one(_EVENT_SELECT + " WHERE e.id = ?", [event_id])
    if not event:
        raise HTTPException(404, "Event not found")
    return event


@app.post("/api/events", status_code=201)
def create_event(body: EventCreate):
    rowid, _ = run(
        """
        INSERT INTO events
            (title, start_date, end_date, tag_id, is_travel, is_preliminary, description)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        [
            body.title,
            body.start_date,
            body.end_date,
            body.tag_id,
            1 if body.is_travel else 0,
            1 if body.is_preliminary else 0,
            body.description,
        ],
    )
    return query_one(_EVENT_SELECT + " WHERE e.id = ?", [rowid])


@app.put("/api/events/{event_id}")
def update_event(event_id: int, body: EventUpdate):
    existing = query_one("SELECT * FROM events WHERE id = ?", [event_id])
    if not existing:
        raise HTTPException(404, "Event not found")
    new_start = body.start_date or existing["start_date"]
    new_end = body.end_date or existing["end_date"]
    if new_start > new_end:
        raise HTTPException(400, "start_date must be <= end_date")
    run(
        """
        UPDATE events
        SET title = ?, start_date = ?, end_date = ?, tag_id = ?,
            is_travel = ?, is_preliminary = ?, description = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        [
            body.title if body.title is not None else existing["title"],
            new_start,
            new_end,
            body.tag_id if body.tag_id is not None else existing["tag_id"],
            (1 if body.is_travel else 0)
            if body.is_travel is not None
            else existing["is_travel"],
            (1 if body.is_preliminary else 0)
            if body.is_preliminary is not None
            else existing["is_preliminary"],
            body.description
            if body.description is not None
            else existing["description"],
            event_id,
        ],
    )
    return query_one(_EVENT_SELECT + " WHERE e.id = ?", [event_id])


@app.delete("/api/events/{event_id}")
def delete_event(event_id: int):
    _, changes = run("DELETE FROM events WHERE id = ?", [event_id])
    if changes == 0:
        raise HTTPException(404, "Event not found")
    return {"success": True}


# ─── STATS ROUTE ──────────────────────────────────────────────────────────────


def _date_range_days(
    start_str: str,
    end_str: str,
    clamp_start: str | None,
    clamp_end: str | None,
) -> set[str]:
    start = date.fromisoformat(start_str)
    end = date.fromisoformat(end_str)
    if clamp_start:
        cs = date.fromisoformat(clamp_start)
        if start < cs:
            start = cs
    if clamp_end:
        ce = date.fromisoformat(clamp_end)
        if end > ce:
            end = ce
    if start > end:
        return set()
    days: set[str] = set()
    cur = start
    while cur <= end:
        days.add(cur.isoformat())
        cur += timedelta(days=1)
    return days


@app.get("/api/stats")
def get_stats(year: Optional[str] = Query(None)):
    year_start = f"{year}-01-01" if year else None
    year_end = f"{year}-12-31" if year else None

    travel_sql = "SELECT start_date, end_date FROM events WHERE is_travel = 1"
    travel_params: list = []
    if year_start:
        travel_sql += " AND end_date >= ? AND start_date <= ?"
        travel_params = [year_start, year_end]

    travel_days: set[str] = set()
    for ev in query_all(travel_sql, travel_params):
        travel_days |= _date_range_days(
            ev["start_date"], ev["end_date"], year_start, year_end
        )

    tag_sql = """
        SELECT t.id, t.name, t.color, COUNT(e.id) as event_count
        FROM tags t
        LEFT JOIN events e ON t.id = e.tag_id
    """
    tag_params: list = []
    if year_start:
        tag_sql += " WHERE (e.id IS NULL OR (e.end_date >= ? AND e.start_date <= ?))"
        tag_params = [year_start, year_end]
    tag_sql += " GROUP BY t.id ORDER BY t.sort_order"

    tag_stats = query_all(tag_sql, tag_params)
    for tag in tag_stats:
        ev_sql = "SELECT start_date, end_date FROM events WHERE tag_id = ?"
        ev_params = [tag["id"]]
        if year_start:
            ev_sql += " AND end_date >= ? AND start_date <= ?"
            ev_params += [year_start, year_end]
        tag_days: set[str] = set()
        for ev in query_all(ev_sql, ev_params):
            tag_days |= _date_range_days(
                ev["start_date"], ev["end_date"], year_start, year_end
            )
        tag["total_days"] = len(tag_days)

    return {
        "travel_days": len(travel_days),
        "tag_stats": tag_stats,
        "year": year or "all",
    }


# ─── EXPORT ROUTE ─────────────────────────────────────────────────────────────


@app.get("/api/export")
def export_events(year: Optional[str] = Query(None)):
    sql = "SELECT e.*, t.name as tag_name FROM events e LEFT JOIN tags t ON e.tag_id = t.id"
    params: list = []
    if year:
        sql += " WHERE e.end_date >= ? AND e.start_date <= ?"
        params = [f"{year}-01-01", f"{year}-12-31"]
    sql += " ORDER BY e.start_date, e.title"

    events = query_all(sql, params)
    header = f"YEARVIEW EXPORT - {year}\n" if year else "YEARVIEW EXPORT - ALL EVENTS\n"
    lines = [header, "=" * 50, "\n"]

    for ev in events:
        s = date.fromisoformat(ev["start_date"])
        e = date.fromisoformat(ev["end_date"])
        fmt = lambda d: d.strftime("%a, %b %-d, %Y")
        dr = fmt(s) if s == e else f"{fmt(s)} - {fmt(e)}"

        labels: list[str] = []
        if ev.get("tag_name"):
            labels.append(ev["tag_name"])
        if ev["is_travel"]:
            labels.append("TRAVEL")
        if ev["is_preliminary"]:
            labels.append("TENTATIVE")

        lines.append(ev["title"])
        lines.append(f"  {dr}")
        if labels:
            lines.append(f"  [{', '.join(labels)}]")
        if ev.get("description"):
            lines.append(f"  {ev['description']}")
        lines.append("")

    filename = f"yearview-{year or 'all'}.txt"
    return PlainTextResponse(
        "\n".join(lines),
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ─── STATIC / CATCH-ALL ───────────────────────────────────────────────────────
# Mounted LAST so it never shadows /api/* routes.
# StaticFiles(html=True) handles /index.html, assets, and falls back to
# index.html for any unknown path (SPA behaviour).

_pub = _public_dir()
if _pub:
    app.mount("/", StaticFiles(directory=str(_pub), html=True), name="static")
