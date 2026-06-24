"""CodeDNA FastAPI REST service."""

from __future__ import annotations

import json
import os
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from codedna import __version__
from codedna.db import (
    get_commit_history,
    get_db_path,
    get_file_scores_for_commit,
    init_db,
    update_understanding_score,
)
from codedna.scorer import scan_repository
from codedna.git_hook import find_git_root

# ---------------------------------------------------------------------------
# Configuration from environment variables
# ---------------------------------------------------------------------------

def _repo_path() -> Path:
    """Return repo path from environment variable or by auto-detection."""
    env = os.environ.get("CODEDNA_REPO_PATH")
    if env:
        return Path(env).resolve()
    return find_git_root() or Path.cwd()


def _db_path() -> Path:
    """Return DB path from environment variable or relative to repo root."""
    env = os.environ.get("CODEDNA_DB_PATH")
    if env:
        return Path(env).resolve()
    return get_db_path(_repo_path())


# ---------------------------------------------------------------------------
# FastAPI application — lifespan pattern
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle — initialize DB on startup."""
    init_db(_db_path())
    yield


app = FastAPI(
    title="CodeDNA API",
    description="AI code transparency tool — REST API",
    version=__version__,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS — fully open for dashboard or external tools
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------
class SurveyInput(BaseModel):
    """Understanding survey input data."""
    score_1: float  # Can you explain this change 3 months from now? [1-5]
    score_2: float  # Could you debug it if a bug appeared? [1-5]
    score_3: float  # Could you explain how it works to someone else? [1-5]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health", tags=["System"])
async def health_check() -> dict:
    """Verify the service is running."""
    return {
        "status": "running",
        "version": __version__,
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/repo/summary", tags=["Repo"])
async def repo_summary() -> dict:
    """Repo-wide summary: average AI score, total commits, risk level."""
    db = _db_path()
    init_db(db)

    commits = get_commit_history(limit=1000, db_path=db)

    if not commits:
        return {
            "total_commits": 0,
            "avg_ai_score": None,
            "risk_level": "UNKNOWN",
            "commits_with_understanding": 0,
            "avg_understanding_score": None,
        }

    total = len(commits)
    understanding_scores = [
        float(c["understanding_score"])
        for c in commits
        if c["understanding_score"] is not None
    ]

    # Calculate average AI probability from file scores
    all_ai_scores: list[float] = []
    for commit in commits[:50]:  # Last 50 commits is sufficient
        files = get_file_scores_for_commit(commit["commit_hash"], db_path=db)
        for f in files:
            if f["ai_probability"] is not None:
                all_ai_scores.append(float(f["ai_probability"]))

    avg_ai = sum(all_ai_scores) / len(all_ai_scores) if all_ai_scores else None
    avg_understanding = sum(understanding_scores) / len(understanding_scores) if understanding_scores else None

    # Risk level
    if avg_ai is None:
        risk = "UNKNOWN"
    elif avg_ai >= 0.7:
        risk = "HIGH"
    elif avg_ai >= 0.4:
        risk = "MEDIUM"
    else:
        risk = "LOW"

    return {
        "total_commits": total,
        "avg_ai_score": round(avg_ai, 3) if avg_ai is not None else None,
        "avg_ai_percentage": round(avg_ai * 100, 1) if avg_ai is not None else None,
        "risk_level": risk,
        "commits_with_understanding": len(understanding_scores),
        "avg_understanding_score": round(avg_understanding, 2) if avg_understanding is not None else None,
    }


@app.get("/repo/files", tags=["Repo"])
async def repo_files(
    min_risk: float = Query(0.0, ge=0.0, le=1.0, description="Minimum AI probability filter"),
    max_files: int = Query(200, ge=1, le=1000, description="Maximum number of files"),
) -> dict:
    """Scan all supported files and return AI scores."""
    root = _repo_path()

    results = scan_repository(root, max_files=max_files)

    # Filter and sort
    if min_risk > 0:
        results = [s for s in results if s.ai_probability >= min_risk]
    results.sort(key=lambda s: s.ai_probability, reverse=True)

    files = []
    for s in results:
        # Calculate relative path
        try:
            relative = str(Path(s.file_path).relative_to(root))
        except ValueError:
            relative = s.file_path

        files.append({
            "file_path": relative,
            "ai_probability": round(s.ai_probability, 3),
            "ai_percentage": round(s.ai_probability * 100, 1),
            "complexity_score": round(s.complexity_score, 1),
            "complexity_label": s.complexity_label,
            "comment_ratio": round(s.comment_ratio, 3),
            "avg_function_length": round(s.avg_function_length, 1),
            "single_commit_ratio": round(s.single_commit_ratio, 3),
            "total_lines": s.total_lines,
            "function_count": s.function_count,
        })

    total_ai = sum(f["ai_probability"] for f in files)
    avg_ai = total_ai / len(files) if files else 0

    return {
        "total_files": len(files),
        "avg_ai_score": round(avg_ai, 3),
        "files": files,
    }


@app.get("/commits", tags=["Commit"])
async def commit_list(
    limit: int = Query(20, ge=1, le=100, description="Number of commits to return"),
) -> dict:
    """Return historical commit list."""
    db = _db_path()
    init_db(db)
    commits = get_commit_history(limit=limit, db_path=db)

    items = []
    for c in commits:
        items.append({
            "commit_hash": c["commit_hash"],
            "short_hash": c["commit_hash"][:8] if c["commit_hash"] else "",
            "author": c["author"],
            "timestamp": c["timestamp"],
            "date": (
                datetime.fromtimestamp(c["timestamp"]).strftime("%Y-%m-%d %H:%M")
                if c["timestamp"] else None
            ),
            "files_changed": c["files_changed"],
            "understanding_score": (
                round(float(c["understanding_score"]), 2)
                if c["understanding_score"] is not None else None
            ),
            "created_at": c["created_at"],
        })

    return {"total": len(items), "commits": items}


@app.get("/commits/{commit_hash}", tags=["Commit"])
async def commit_detail(commit_hash: str) -> dict:
    """Return single commit detail and related file scores."""
    db = _db_path()
    init_db(db)

    # Search by full or short hash
    commits = get_commit_history(limit=1000, db_path=db)
    found = None
    for c in commits:
        if c["commit_hash"] and (
            c["commit_hash"] == commit_hash
            or c["commit_hash"].startswith(commit_hash)
        ):
            found = c
            break

    if not found:
        raise HTTPException(
            status_code=404,
            detail=f"Commit '{commit_hash}' not found.",
        )

    files = get_file_scores_for_commit(found["commit_hash"], db_path=db)
    file_list = [
        {
            "file_path": f["file_path"],
            "ai_probability": round(float(f["ai_probability"]), 3) if f["ai_probability"] is not None else None,
            "complexity_score": round(float(f["complexity_score"]), 1) if f["complexity_score"] is not None else None,
            "comment_ratio": round(float(f["comment_ratio"]), 3) if f["comment_ratio"] is not None else None,
            "understanding_score": round(float(f["understanding_score"]), 2) if f["understanding_score"] is not None else None,
        }
        for f in files
    ]

    return {
        "commit_hash": found["commit_hash"],
        "author": found["author"],
        "date": (
            datetime.fromtimestamp(found["timestamp"]).strftime("%Y-%m-%d %H:%M")
            if found["timestamp"] else None
        ),
        "files_changed": found["files_changed"],
        "understanding_score": (
            round(float(found["understanding_score"]), 2)
            if found["understanding_score"] is not None else None
        ),
        "files": file_list,
    }


@app.post("/survey/{commit_hash}", tags=["Survey"])
async def save_survey(commit_hash: str, data: SurveyInput) -> dict:
    """Save understanding survey result."""
    # Validate scores
    for field, value in [("score_1", data.score_1), ("score_2", data.score_2), ("score_3", data.score_3)]:
        if not (1.0 <= value <= 5.0):
            raise HTTPException(
                status_code=422,
                detail=f"'{field}' must be between 1 and 5, got: {value}",
            )

    average = (data.score_1 + data.score_2 + data.score_3) / 3.0
    db = _db_path()
    init_db(db)

    # Check if commit exists
    commits = get_commit_history(limit=1000, db_path=db)
    found_hash = None
    for c in commits:
        if c["commit_hash"] and (
            c["commit_hash"] == commit_hash
            or c["commit_hash"].startswith(commit_hash)
        ):
            found_hash = c["commit_hash"]
            break

    if not found_hash:
        raise HTTPException(
            status_code=404,
            detail=f"Commit '{commit_hash}' not found.",
        )

    update_understanding_score(found_hash, average, db_path=db)

    return {
        "commit_hash": found_hash,
        "understanding_score": round(average, 2),
        "message": "Understanding score saved successfully.",
    }


@app.get("/report", tags=["Report"])
async def report(fmt: str = Query("json", description="Output format: 'json' or 'html'")) -> object:
    """Return repo summary report as JSON or HTML."""
    db = _db_path()
    init_db(db)
    root = _repo_path()

    # Collect data
    commits = get_commit_history(limit=50, db_path=db)
    file_results = scan_repository(root, max_files=100)
    file_results.sort(key=lambda s: s.ai_probability, reverse=True)

    all_ai = [s.ai_probability for s in file_results]
    avg_ai = sum(all_ai) / len(all_ai) if all_ai else 0.0

    understanding_scores = [
        float(c["understanding_score"])
        for c in commits
        if c["understanding_score"] is not None
    ]
    avg_understanding = sum(understanding_scores) / len(understanding_scores) if understanding_scores else None

    if avg_ai >= 0.7:
        risk = "HIGH"
    elif avg_ai >= 0.4:
        risk = "MEDIUM"
    else:
        risk = "LOW"

    if fmt == "html":
        html = _build_html_report(
            repo_name=root.name,
            total_files=len(file_results),
            avg_ai=avg_ai,
            risk=risk,
            avg_understanding=avg_understanding,
            total_commits=len(commits),
            files=file_results,
            commits=commits,
            root=root,
        )
        return HTMLResponse(content=html)

    # JSON format
    return {
        "repo": root.name,
        "date": datetime.utcnow().isoformat(),
        "summary": {
            "total_files": len(file_results),
            "avg_ai_score": round(avg_ai, 3),
            "risk_level": risk,
            "total_commits": len(commits),
            "avg_understanding_score": round(avg_understanding, 2) if avg_understanding else None,
        },
        "files": [
            {
                "path": str(Path(s.file_path).relative_to(root)) if Path(s.file_path).is_relative_to(root) else s.file_path,
                "ai_percentage": round(s.ai_probability * 100, 1),
                "complexity": s.complexity_label,
                "lines": s.total_lines,
            }
            for s in file_results[:20]
        ],
    }


# ---------------------------------------------------------------------------
# HTML report builder (no Jinja2 — f-string)
# ---------------------------------------------------------------------------
def _build_html_report(
    repo_name: str,
    total_files: int,
    avg_ai: float,
    risk: str,
    avg_understanding: Optional[float],
    total_commits: int,
    files: list,
    commits: list,
    root: Path,
) -> str:
    """Generate a plain HTML report with inline CSS."""
    date_str = datetime.now().strftime("%d %B %Y, %H:%M")
    risk_color = {"HIGH": "#e74c3c", "MEDIUM": "#f39c12", "LOW": "#27ae60"}.get(risk, "#95a5a6")

    understanding_str = f"{avg_understanding:.1f}/5" if avg_understanding is not None else "No data"

    # File rows
    file_rows = ""
    for s in files:
        try:
            path = str(Path(s.file_path).relative_to(root))
        except ValueError:
            path = s.file_path

        pct = s.ai_probability * 100
        if pct >= 70:
            color = "#e74c3c"
            emoji = "🔴"
        elif pct >= 40:
            color = "#f39c12"
            emoji = "🟡"
        else:
            color = "#27ae60"
            emoji = "🟢"

        file_rows += f"""
        <tr>
            <td style="font-family:monospace;font-size:13px">{path}</td>
            <td style="color:{color};font-weight:bold;text-align:center">{emoji} {pct:.0f}%</td>
            <td style="text-align:center">{s.complexity_label}</td>
            <td style="text-align:right">{s.total_lines}</td>
            <td style="text-align:right">{s.function_count}</td>
        </tr>"""

    # Commit rows
    commit_rows = ""
    for c in commits[:20]:
        date = (
            datetime.fromtimestamp(c["timestamp"]).strftime("%Y-%m-%d %H:%M")
            if c["timestamp"] else "?"
        )
        understanding = (
            f"{float(c['understanding_score']):.1f}/5"
            if c["understanding_score"] is not None else "—"
        )
        commit_rows += f"""
        <tr>
            <td style="font-family:monospace">{(c['commit_hash'] or '')[:8]}</td>
            <td>{c['author'] or '?'}</td>
            <td>{date}</td>
            <td style="text-align:right">{c['files_changed'] or 0}</td>
            <td style="text-align:center">{understanding}</td>
        </tr>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>🧬 CodeDNA Report — {repo_name}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
          background: #0f1117; color: #e2e8f0; padding: 32px; }}
  h1 {{ font-size: 28px; margin-bottom: 4px; }}
  h2 {{ font-size: 18px; margin: 32px 0 12px; color: #94a3b8; text-transform: uppercase;
        letter-spacing: 1px; font-size: 13px; }}
  .subtitle {{ color: #64748b; font-size: 14px; margin-bottom: 32px; }}
  .cards {{ display: flex; gap: 16px; flex-wrap: wrap; margin-bottom: 32px; }}
  .card {{ background: #1e2433; border-radius: 12px; padding: 20px 28px;
           min-width: 160px; flex: 1; border: 1px solid #2d3748; }}
  .card-label {{ font-size: 12px; color: #64748b; text-transform: uppercase;
                 letter-spacing: 1px; margin-bottom: 8px; }}
  .card-value {{ font-size: 28px; font-weight: 700; }}
  table {{ width: 100%; border-collapse: collapse; background: #1e2433;
           border-radius: 12px; overflow: hidden; border: 1px solid #2d3748; }}
  th {{ background: #252d3d; padding: 12px 16px; text-align: left;
        font-size: 12px; text-transform: uppercase; letter-spacing: 1px;
        color: #94a3b8; }}
  td {{ padding: 11px 16px; border-top: 1px solid #2d3748; font-size: 14px; }}
  tr:hover td {{ background: #252d3d; }}
  .badge {{ display: inline-block; padding: 3px 10px; border-radius: 20px;
            font-size: 12px; font-weight: 600; color: white;
            background: {risk_color}; }}
  footer {{ margin-top: 40px; color: #4a5568; font-size: 12px; text-align: center; }}
</style>
</head>
<body>
<h1>🧬 CodeDNA Report</h1>
<p class="subtitle">📁 {repo_name} &nbsp;·&nbsp; 📅 {date_str}</p>

<div class="cards">
  <div class="card">
    <div class="card-label">Total Files</div>
    <div class="card-value">{total_files}</div>
  </div>
  <div class="card">
    <div class="card-label">Avg. AI Score</div>
    <div class="card-value">{avg_ai*100:.0f}%</div>
  </div>
  <div class="card">
    <div class="card-label">Risk Level</div>
    <div class="card-value"><span class="badge">{risk}</span></div>
  </div>
  <div class="card">
    <div class="card-label">Total Commits</div>
    <div class="card-value">{total_commits}</div>
  </div>
  <div class="card">
    <div class="card-label">Avg. Understanding</div>
    <div class="card-value">{understanding_str}</div>
  </div>
</div>

<h2>File Analysis</h2>
<table>
  <thead>
    <tr>
      <th>File</th><th>AI Probability</th><th>Complexity</th>
      <th style="text-align:right">Lines</th><th style="text-align:right">Functions</th>
    </tr>
  </thead>
  <tbody>{file_rows}</tbody>
</table>

<h2>Commit History</h2>
<table>
  <thead>
    <tr>
      <th>Hash</th><th>Author</th><th>Date</th>
      <th style="text-align:right">Files</th><th style="text-align:center">Understanding</th>
    </tr>
  </thead>
  <tbody>{commit_rows}</tbody>
</table>

<footer>🧬 CodeDNA v{__version__} &nbsp;·&nbsp; generated by codedna report</footer>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Helper: plan 403 response
# ---------------------------------------------------------------------------
def _plan_403(feature: str, tr_message: str, en_message: str) -> HTTPException:
    """Generate a standard 403 error for plan restrictions."""
    return HTTPException(
        status_code=403,
        detail={
            "error": en_message,
            "feature": feature,
            "required_plan": "team",
        },
    )


# ---------------------------------------------------------------------------
# Bus Factor endpoints
# ---------------------------------------------------------------------------

@app.get("/bus-factor", tags=["Bus Factor"])
async def bus_factor_list(
    max_files: int = Query(200, ge=1, le=500, description="Maximum number of files"),
) -> dict:
    """Bus factor list for all files. Requires Team+ plan."""
    from codedna.plan import is_feature_available
    from codedna.bus_factor import calculate_bus_factor

    if not is_feature_available("bus_factor"):
        raise _plan_403(
            "bus_factor",
            "This feature is available on Team plan.",
            "This feature is available on Team plan.",
        )

    root = _repo_path()
    db = _db_path()
    init_db(db)

    results = calculate_bus_factor(root, db, max_files=max_files)

    return {
        "total_files": len(results),
        "critical_count": sum(1 for s in results if s.risk == "CRITICAL"),
        "risky_count": sum(1 for s in results if s.risk == "RISKY"),
        "files": [
            {
                "file_path": s.file_path,
                "bus_factor": s.bus_factor,
                "primary_owner": s.primary_owner,
                "ownership_percentage": s.ownership_percentage,
                "risk": s.risk,
                "knowledgeable_authors": s.knowledgeable_authors,
                "total_lines": s.total_lines,
            }
            for s in results
        ],
    }


@app.get("/bus-factor/critical", tags=["Bus Factor"])
async def bus_factor_critical() -> dict:
    """Return only critical files where bus_factor=1. Requires Team+ plan."""
    from codedna.plan import is_feature_available
    from codedna.bus_factor import get_at_risk_files

    if not is_feature_available("bus_factor"):
        raise _plan_403(
            "bus_factor",
            "This feature is available on Team plan.",
            "This feature is available on Team plan.",
        )

    root = _repo_path()
    db = _db_path()
    init_db(db)

    results = get_at_risk_files(root, db)

    return {
        "critical_count": len(results),
        "files": [
            {
                "file_path": s.file_path,
                "bus_factor": s.bus_factor,
                "primary_owner": s.primary_owner,
                "ownership_percentage": s.ownership_percentage,
                "risk": s.risk,
                "total_lines": s.total_lines,
            }
            for s in results
        ],
    }


# ---------------------------------------------------------------------------
# Technical Debt endpoints
# ---------------------------------------------------------------------------

@app.get("/debt/summary", tags=["Technical Debt"])
async def debt_summary(
    rate: float = Query(75.0, ge=1.0, le=1000.0, description="Hourly rate ($/hour)"),
) -> dict:
    """
    Repo-wide technical debt summary.
    Dollar amounts are masked on the Free plan.
    """
    from codedna.plan import get_current_plan, Plan
    from codedna.tech_debt import calculate_repo_debt

    root = _repo_path()
    db = _db_path()
    init_db(db)

    summary = calculate_repo_debt(root, db, hourly_rate=rate)
    current_plan = get_current_plan()
    hide_dollars = current_plan == Plan.FREE

    top_5 = []
    for d in summary.top_5_most_expensive:
        try:
            relative = str(Path(d.file_path).relative_to(root))
        except ValueError:
            relative = d.file_path

        top_5.append({
            "file_path": relative,
            "debt_hours": d.debt_hours,
            "monthly_cost_usd": None if hide_dollars else d.monthly_cost_usd,
            "risk_level": d.risk_level,
        })

    return {
        "total_debt_hours": summary.total_debt_hours,
        "total_monthly_cost_usd": None if hide_dollars else summary.total_monthly_cost_usd,
        "dollars_hidden": hide_dollars,
        "hourly_rate": rate,
        "total_files": summary.total_files,
        "top_5_most_expensive": top_5,
    }


@app.get("/debt/files", tags=["Technical Debt"])
async def debt_files(
    rate: float = Query(75.0, ge=1.0, le=1000.0, description="Hourly rate ($/hour)"),
    limit: int = Query(20, ge=1, le=100, description="Number of files to return"),
) -> dict:
    """
    Per-file technical debt list, sorted by most expensive.
    Dollar amounts are masked on the Free plan.
    """
    from codedna.plan import get_current_plan, Plan
    from codedna.tech_debt import calculate_repo_debt

    root = _repo_path()
    db = _db_path()
    init_db(db)

    summary = calculate_repo_debt(root, db, hourly_rate=rate)
    current_plan = get_current_plan()
    hide_dollars = current_plan == Plan.FREE

    # Get all files sorted by most expensive
    from codedna.tech_debt import calculate_file_debt
    from codedna.scorer import scan_repository

    scanned = scan_repository(root, max_files=200)
    scanned.sort(key=lambda s: s.ai_probability, reverse=True)

    file_list = []
    for s in scanned[:limit]:
        debt = calculate_file_debt(s.file_path, db, hourly_rate=rate)
        if debt is None:
            continue
        try:
            relative = str(Path(s.file_path).relative_to(root))
        except ValueError:
            relative = s.file_path

        file_list.append({
            "file_path": relative,
            "debt_hours": debt.debt_hours,
            "monthly_cost_usd": None if hide_dollars else debt.monthly_cost_usd,
            "risk_level": debt.risk_level,
            "ai_probability": debt.ai_probability,
            "complexity": debt.complexity,
            "total_lines": debt.total_lines,
        })

    file_list.sort(key=lambda d: d["debt_hours"], reverse=True)

    return {
        "total_files": len(file_list),
        "dollars_hidden": hide_dollars,
        "hourly_rate": rate,
        "files": file_list,
    }


# ---------------------------------------------------------------------------
# Sprint endpoints
# ---------------------------------------------------------------------------

class SprintInput(BaseModel):
    """New sprint creation input data."""
    sprint_name: str
    start_date: str   # ISO date: "2026-06-01"
    end_date: str     # ISO date: "2026-06-14"


@app.post("/sprints", tags=["Sprint"])
async def create_sprint(data: SprintInput) -> dict:
    """
    Create a new sprint record and calculate health score.
    Requires Team+ plan.
    """
    from codedna.plan import is_feature_available
    from codedna.sprint_health import calculate_sprint_health, save_sprint_result
    from datetime import datetime as dt

    if not is_feature_available("sprint_health"):
        raise _plan_403(
            "sprint_health",
            "This feature is available on Team plan.",
            "This feature is available on Team plan.",
        )

    try:
        start = dt.fromisoformat(data.start_date)
        end = dt.fromisoformat(data.end_date)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=f"Invalid date format: {e}")

    if end <= start:
        raise HTTPException(status_code=422, detail="End date must be after start date.")

    root = _repo_path()
    db = _db_path()
    init_db(db)

    result = calculate_sprint_health(root, db, start, end, data.sprint_name)
    sprint_id = save_sprint_result(result, db)

    return {
        "sprint_id": sprint_id,
        "sprint_name": result.sprint_name,
        "health_score": result.health_score,
        "status": result.status,
        "avg_understanding": result.avg_understanding,
        "ai_ratio": result.ai_ratio,
        "debt_delta_hours": result.debt_delta_hours,
        "total_commits": result.total_commits,
        "ai_human_ratio": result.ai_human_ratio_str,
    }


@app.get("/sprints/current/health", tags=["Sprint"])
async def current_sprint_health() -> dict:
    """
    Return the health score of the most recent sprint.
    Requires Team+ plan.
    """
    from codedna.plan import is_feature_available
    from codedna.db import get_latest_sprint

    if not is_feature_available("sprint_health"):
        raise _plan_403(
            "sprint_health",
            "This feature is available on Team plan.",
            "This feature is available on Team plan.",
        )

    db = _db_path()
    init_db(db)

    sprint = get_latest_sprint(db_path=db)
    if not sprint:
        raise HTTPException(status_code=404, detail="No sprint recorded yet.")

    return {
        "sprint_id": sprint["id"],
        "sprint_name": sprint["sprint_name"],
        "health_score": sprint["health_score"],
        "status": _sprint_status(sprint["health_score"]),
        "avg_understanding": sprint["avg_understanding"],
        "debt_delta_hours": sprint["debt_delta_hours"],
        "ai_lines": sprint["total_lines_ai"],
        "human_lines": sprint["total_lines_human"],
        "start_date": _ts_to_str(sprint["start_date"]),
        "end_date": _ts_to_str(sprint["end_date"]),
    }


@app.get("/sprints/history", tags=["Sprint"])
async def sprint_history(
    limit: int = Query(10, ge=1, le=50, description="Number of sprints to return"),
) -> dict:
    """Return historical sprint list. Requires Team+ plan."""
    from codedna.plan import is_feature_available
    from codedna.db import get_sprint_history as db_sprint_history

    if not is_feature_available("sprint_health"):
        raise _plan_403(
            "sprint_health",
            "This feature is available on Team plan.",
            "This feature is available on Team plan.",
        )

    db = _db_path()
    init_db(db)
    sprints = db_sprint_history(limit=limit, db_path=db)

    return {
        "total": len(sprints),
        "sprints": [
            {
                "id": s["id"],
                "sprint_name": s["sprint_name"],
                "start_date": _ts_to_str(s["start_date"]),
                "end_date": _ts_to_str(s["end_date"]),
                "health_score": s["health_score"],
                "status": _sprint_status(s["health_score"]),
                "avg_understanding": s["avg_understanding"],
                "debt_delta_hours": s["debt_delta_hours"],
                "ai_lines": s["total_lines_ai"],
                "human_lines": s["total_lines_human"],
            }
            for s in sprints
        ],
    }


# ---------------------------------------------------------------------------
# Jira webhook endpoint
# ---------------------------------------------------------------------------

@app.post("/integrations/jira/webhook", tags=["Integrations"])
async def jira_webhook(request: Request) -> dict:
    """
    Receive and process sprint events from Jira.
    HMAC-SHA256 signature verification is REQUIRED (Requires Team+ plan).
    """
    from codedna.integrations.jira import (
        get_or_create_secret,
        verify_signature,
        handle_jira_webhook,
    )
    from codedna.plan import is_feature_available

    # Plan check
    if not is_feature_available("sprint_health"):
        raise HTTPException(
            status_code=403,
            detail="Jira integration requires Team plan.",
        )

    body = await request.body()
    secret = get_or_create_secret()
    signature = request.headers.get("X-Hub-Signature-256", "")

    # Signature is REQUIRED — reject if missing or invalid
    if not signature or not verify_signature(body, signature, secret):
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing webhook signature.",
        )

    try:
        payload = json.loads(body)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload.")

    db = _db_path()
    init_db(db)
    result = handle_jira_webhook(payload, db)
    return result


@app.get("/integrations/jira/config", tags=["Integrations"])
async def jira_config() -> dict:
    """Return Jira webhook configuration. Requires Team+ plan."""
    from codedna.plan import is_feature_available
    from codedna.integrations.jira import get_or_create_secret

    if not is_feature_available("sprint_health"):
        raise _plan_403(
            "sprint_health",
            "This feature is available on Team plan.",
            "This feature is available on Team plan.",
        )

    secret = get_or_create_secret()
    return {
        "webhook_url": f"{_repo_path().name}/api/integrations/jira/webhook",
        "secret_exists": bool(secret),
        "secret_length": len(secret),
        "supported_events": ["sprint_started", "sprint_closed"],
    }


@app.post("/integrations/jira/rotate-secret", tags=["Integrations"])
async def jira_rotate_secret() -> dict:
    """Rotate webhook secret. Requires Team+ plan."""
    from codedna.plan import is_feature_available
    from codedna.integrations.jira import rotate_secret

    if not is_feature_available("sprint_health"):
        raise _plan_403(
            "sprint_health",
            "This feature is available on Team plan.",
            "This feature is available on Team plan.",
        )

    new_secret = rotate_secret()
    return {
        "message": "Webhook secret rotated.",
        "secret": new_secret,
    }


# ---------------------------------------------------------------------------
# Helper functions (for sprint)
# ---------------------------------------------------------------------------

def _sprint_status(score: Optional[float]) -> str:
    """Return status label based on score."""
    if score is None:
        return "UNKNOWN"
    if score >= 80:
        return "HEALTHY"
    elif score >= 50:
        return "WARNING"
    return "RISKY"


def _ts_to_str(ts: Optional[int]) -> Optional[str]:
    """Convert Unix timestamp to a readable date string."""
    if not ts:
        return None
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# AI Tool Comparison endpoint
# ---------------------------------------------------------------------------

@app.get("/ai-compare", tags=["AI Comparison"])
async def ai_tool_compare() -> dict:
    """Repo-wide AI tool comparison. Requires Enterprise plan."""
    from codedna.plan import is_feature_available
    from codedna.ai_fingerprint import compare_tools_in_repo

    if not is_feature_available("ai_comparison"):
        raise _plan_403(
            "ai_comparison",
            "This feature is available on Enterprise plan.",
            "This feature is available on Enterprise plan.",
        )

    root = _repo_path()
    db = _db_path()
    init_db(db)
    results = compare_tools_in_repo(root, db)
    return {
        "warning": "This detection is pattern-based estimation — not definitive.",
        "tools": results,
        "total_files": sum(v.get("file_count", 0) for v in results.values()),
    }


# ---------------------------------------------------------------------------
# Onboarding endpoints
# ---------------------------------------------------------------------------

@app.get("/onboarding/team", tags=["Onboarding"])
async def onboarding_team_summary() -> dict:
    """Ramp-up summary for all team authors. Requires Team+ plan."""
    from codedna.plan import is_feature_available
    from codedna.onboarding import team_onboarding_summary

    if not is_feature_available("sprint_health"):
        raise _plan_403("sprint_health", "This feature is available on Team plan.", "This feature is available on Team plan.")

    db = _db_path()
    init_db(db)
    summary = team_onboarding_summary(db)
    return {"total_authors": len(summary), "authors": summary}


@app.get("/onboarding/{author}", tags=["Onboarding"])
async def onboarding_author_curve(author: str) -> dict:
    """Onboarding timeline for a single author. Requires Team+ plan."""
    from codedna.plan import is_feature_available
    from codedna.onboarding import get_author_curve

    if not is_feature_available("sprint_health"):
        raise _plan_403("sprint_health", "This feature is available on Team plan.", "This feature is available on Team plan.")

    db = _db_path()
    init_db(db)
    curve = get_author_curve(author, db)

    if curve.total_commits == 0:
        raise HTTPException(status_code=404, detail=f"No commits found for author '{author}'.")

    return {
        "author": curve.author,
        "total_commits": curve.total_commits,
        "commits_with_understanding": curve.commits_with_understanding,
        "ramp_up_weeks": curve.ramp_up_weeks,
        "latest_avg_understanding": curve.latest_avg_understanding,
        "sufficient_data": curve.commits_with_understanding >= 5,
        "data_points": [
            {
                "commit_number": n.commit_no,
                "week_number": n.week_number,
                "date": n.date.strftime("%Y-%m-%d"),
                "understanding_score": n.understanding_score,
            }
            for n in curve.points
        ],
    }


# ---------------------------------------------------------------------------
# Protected Module endpoints
# ---------------------------------------------------------------------------

class ProtectedModuleInput(BaseModel):
    """Protected module creation input data."""
    file_path: str
    threshold: float = 3.5
    label: str = ""
    added_by: str = "api"


@app.post("/protected-modules", tags=["Protected Modules"])
async def add_protected_module(data: ProtectedModuleInput) -> dict:
    """Add a new protected module. Requires Team+ plan."""
    from codedna.plan import is_feature_available
    from codedna.protection import protect_module

    if not is_feature_available("bus_factor"):
        raise _plan_403("bus_factor", "This feature is available on Team plan.", "This feature is available on Team plan.")
    if not (1.0 <= data.threshold <= 5.0):
        raise HTTPException(status_code=422, detail="Threshold must be between 1.0 and 5.0.")

    db = _db_path()
    init_db(db)
    record_id = protect_module(data.file_path, data.threshold, data.label or data.file_path, data.added_by, db)
    return {"id": record_id, "file_path": data.file_path, "message": "Protected module added."}


@app.get("/protected-modules", tags=["Protected Modules"])
async def list_protected_modules() -> dict:
    """Return all protected modules and statuses. Requires Team+ plan."""
    from codedna.plan import is_feature_available
    from codedna.protection import check_protected_modules

    if not is_feature_available("bus_factor"):
        raise _plan_403("bus_factor", "This feature is available on Team plan.", "This feature is available on Team plan.")

    db = _db_path()
    init_db(db)
    modules = check_protected_modules(db)
    return {
        "total": len(modules),
        "violation_count": sum(1 for m in modules if m.status == "VIOLATION"),
        "modules": [
            {"file_path": m.file_path, "label": m.label, "threshold": m.threshold,
             "current_score": m.current_score, "status": m.status}
            for m in modules
        ],
    }


@app.delete("/protected-modules/{file_path:path}", tags=["Protected Modules"])
async def remove_protected_module(file_path: str) -> dict:
    """Remove a protected module. Requires Team+ plan."""
    from codedna.plan import is_feature_available
    from codedna.protection import unprotect_module

    if not is_feature_available("bus_factor"):
        raise _plan_403("bus_factor", "This feature is available on Team plan.", "This feature is available on Team plan.")

    db = _db_path()
    if unprotect_module(file_path, db):
        return {"message": "Protection removed.", "file_path": file_path}
    raise HTTPException(status_code=404, detail="Protected module not found.")


@app.get("/protected-modules/violations", tags=["Protected Modules"])
async def protected_module_violations() -> dict:
    """Return only protected modules in violation. Requires Team+ plan."""
    from codedna.plan import is_feature_available
    from codedna.protection import get_violations

    if not is_feature_available("bus_factor"):
        raise _plan_403("bus_factor", "This feature is available on Team plan.", "This feature is available on Team plan.")

    db = _db_path()
    init_db(db)
    violations = get_violations(db)
    return {
        "violation_count": len(violations),
        "violations": [
            {"file_path": m.file_path, "label": m.label, "threshold": m.threshold, "current_score": m.current_score}
            for m in violations
        ],
    }


# ---------------------------------------------------------------------------
# Interview endpoints
# ---------------------------------------------------------------------------

class InterviewStartInput(BaseModel):
    """Interview session start input data."""
    candidate_name: str
    difficulty: str = "medium"


@app.post("/interview/start", tags=["Interview"])
async def start_interview(data: InterviewStartInput) -> dict:
    """Start a new interview session. Requires Enterprise plan."""
    from codedna.plan import is_feature_available
    from codedna.interview import select_candidate_file, generate_questions, start_session

    if not is_feature_available("interview_tool"):
        raise _plan_403("interview_tool", "This feature is available on Enterprise plan.", "This feature is available on Enterprise plan.")
    if data.difficulty not in ("easy", "medium", "hard"):
        raise HTTPException(status_code=422, detail="Difficulty must be: easy | medium | hard")

    root = _repo_path()
    db = _db_path()
    init_db(db)
    candidate_file = select_candidate_file(root, db, data.difficulty)
    if not candidate_file:
        raise HTTPException(status_code=404, detail=f"No suitable file found for difficulty '{data.difficulty}'.")

    questions = generate_questions(candidate_file.anonymized_code)
    session_id = start_session(data.candidate_name, candidate_file.file_path, questions, db)
    return {
        "session_id": session_id,
        "candidate": data.candidate_name,
        "difficulty": data.difficulty,
        "complexity": candidate_file.complexity_score,
        "line_count": candidate_file.line_count,
        "anonymized_code": candidate_file.anonymized_code,
        "questions": questions,
        "warning": "This tool should not be used as the sole hiring decision factor.",
    }


class ScoreInput(BaseModel):
    """Interview score input data."""
    score: float
    evaluator_notes: str = ""


@app.post("/interview/{session_id}/score", tags=["Interview"])
async def save_interview_score(session_id: int, data: ScoreInput) -> dict:
    """Save human evaluator score. Requires Enterprise plan."""
    from codedna.plan import is_feature_available
    from codedna.interview import submit_score

    if not is_feature_available("interview_tool"):
        raise _plan_403("interview_tool", "This feature is available on Enterprise plan.", "This feature is available on Enterprise plan.")

    db = _db_path()
    try:
        return submit_score(session_id, data.score, data.evaluator_notes, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/interview/sessions", tags=["Interview"])
async def interview_sessions(limit: int = Query(20, ge=1, le=100)) -> dict:
    """Return past interview sessions. Requires Enterprise plan."""
    from codedna.plan import is_feature_available
    from codedna.interview import get_sessions

    if not is_feature_available("interview_tool"):
        raise _plan_403("interview_tool", "This feature is available on Enterprise plan.", "This feature is available on Enterprise plan.")

    db = _db_path()
    init_db(db)
    return {"sessions": get_sessions(db, limit=limit)}


# ---------------------------------------------------------------------------
# Auth endpoints
# ---------------------------------------------------------------------------

def _auth_db_path() -> Path:
    """Return auth database path."""
    import os
    env = os.environ.get("CODEDNA_AUTH_DB_PATH")
    return Path(env).resolve() if env else Path.home() / ".codedna" / "auth.db"


def _extract_token(request: Request) -> Optional[str]:
    """Extract token from Authorization: Bearer <token> header."""
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:].strip()
    return None


class RegisterInput(BaseModel):
    """Registration input data."""
    email: str
    password: str


class LoginInput(BaseModel):
    """Login input data."""
    email: str
    password: str


@app.post("/auth/register", tags=["Auth"])
async def auth_register(data: RegisterInput) -> dict:
    """Register a new user."""
    from codedna.auth import register_user, init_auth_db

    db = _auth_db_path()
    init_auth_db(db)
    try:
        result = register_user(data.email, data.password, db)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return {"user_id": result["user_id"], "token": result["token"], "plan": result["plan"], "message": "Registration successful."}


@app.post("/auth/login", tags=["Auth"])
async def auth_login(data: LoginInput, request: Request) -> dict:
    """Log in and return a JWT token. Rate limited by IP and email."""
    from codedna.auth import login_user, init_auth_db
    from codedna.rate_limit import login_limiter

    db = _auth_db_path()
    init_auth_db(db)
    ip = request.client.host if request.client else "unknown"
    email_key = f"email:{data.email.strip().lower()}"

    for key in (ip, email_key):
        allowed, remaining = login_limiter.kontrol_et(key)
        if not allowed:
            raise HTTPException(status_code=429, detail=f"Too many failed attempts. Please wait {remaining} seconds.")

    try:
        result = login_user(data.email, data.password, db)
        login_limiter.basarili_kaydet(ip)
        login_limiter.basarili_kaydet(email_key)
    except ValueError:
        login_limiter.basarisiz_kaydet(ip)
        login_limiter.basarisiz_kaydet(email_key)
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    return {"user_id": result["user_id"], "token": result["token"], "plan": result["plan"], "subscription_status": result["subscription_status"]}


@app.post("/auth/logout", tags=["Auth"])
async def auth_logout(request: Request) -> dict:
    """End the session."""
    from codedna.auth import logout_user

    token = _extract_token(request)
    if not token:
        raise HTTPException(status_code=401, detail="Token required.")
    db = _auth_db_path()
    logout_user(token, db)
    return {"message": "Logged out successfully."}


@app.get("/auth/me", tags=["Auth"])
async def auth_me(request: Request) -> dict:
    """Return current user information."""
    from codedna.auth import verify_token, get_user_by_id

    token = _extract_token(request)
    if not token:
        raise HTTPException(status_code=401, detail="Token required.")
    db = _auth_db_path()
    user = verify_token(token, db)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token.")
    detail = get_user_by_id(user["user_id"], db)
    if not detail:
        raise HTTPException(status_code=404, detail="User not found.")
    return {"user_id": detail["id"], "email": detail["email"], "plan": detail["plan"], "subscription_status": detail["subscription_status"]}


# ---------------------------------------------------------------------------
# Billing endpoints
# ---------------------------------------------------------------------------

class CheckoutInput(BaseModel):
    """Checkout request input data."""
    plan: str  # "pro" | "team" | "enterprise"


@app.post("/billing/checkout", tags=["Billing"])
async def billing_checkout(data: CheckoutInput, request: Request) -> dict:
    """Create a Lemon Squeezy checkout URL. Requires Authorization header."""
    from codedna.auth import verify_token
    from codedna.integrations.lemonsqueezy import create_checkout_url

    token = _extract_token(request)
    if not token:
        raise HTTPException(status_code=401, detail="Token required.")
    db = _auth_db_path()
    user = verify_token(token, db)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token.")
    if data.plan not in ("pro", "team", "enterprise"):
        raise HTTPException(status_code=422, detail="Invalid plan: pro | team | enterprise")

    try:
        checkout_url = create_checkout_url(data.plan, user["email"], user["user_id"])
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))
    return {"checkout_url": checkout_url, "plan": data.plan}


@app.post("/billing/webhook", tags=["Billing"])
async def billing_webhook(request: Request) -> dict:
    """Receive and process subscription events from Lemon Squeezy. Signature is REQUIRED."""
    from codedna.integrations.lemonsqueezy import verify_webhook_signature, handle_subscription_webhook

    body = await request.body()
    signature = request.headers.get("X-Signature", "")
    if not signature or not verify_webhook_signature(body, signature):
        raise HTTPException(status_code=401, detail="Invalid or missing webhook signature.")

    try:
        payload = json.loads(body)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload.")

    db = _auth_db_path()
    result = handle_subscription_webhook(payload, db)
    return result


@app.get("/billing/subscription", tags=["Billing"])
async def billing_subscription(request: Request) -> dict:
    """Return the current user's subscription status."""
    from codedna.auth import verify_token, get_user_by_id

    token = _extract_token(request)
    if not token:
        raise HTTPException(status_code=401, detail="Token required.")
    db = _auth_db_path()
    user = verify_token(token, db)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token.")
    detail = get_user_by_id(user["user_id"], db)
    if not detail:
        raise HTTPException(status_code=404, detail="User not found.")
    return {"plan": detail["plan"], "subscription_status": detail["subscription_status"], "lemonsqueezy_customer_id": detail["lemonsqueezy_customer_id"]}
