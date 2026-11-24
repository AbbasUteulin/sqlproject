# Part 3, chunks 1-2: foundation and READ pages. 
import os
from flask import Flask, render_template, abort
from sqlalchemy import text
from db import engine

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-only-change-me")   # needed later for flash messages


def fetch_all(sql, params=None):
    """SELECT -> list of dictionaries (column name -> value)."""
    with engine.connect() as conn:
        return conn.execute(text(sql), params or {}).mappings().all()


def fetch_one(sql, params=None):
    rows = fetch_all(sql, params)
    return rows[0] if rows else None


@app.get("/")
def index():
    counts = {
        "users": fetch_one("SELECT COUNT(*) AS n FROM APP_USER")["n"],
        "papers": fetch_one("SELECT COUNT(*) AS n FROM PAPER")["n"],
        "reviews": fetch_one("SELECT COUNT(*) AS n FROM REVIEW")["n"],
        "sessions": fetch_one("SELECT COUNT(*) AS n FROM CONFERENCE_SESSION")["n"],
    }
    return render_template("index.html", **counts)


# ---------- users ----------
@app.get("/users")
def users():
    rows = fetch_all("""
        SELECT u.user_id, u.given_name || ' ' || u.surname AS full_name, u.email, u.affiliation,
               u.country, u.phone_number,
               concat_ws(', ', CASE WHEN a.author_id IS NOT NULL THEN 'author' END,
                               CASE WHEN r.reviewer_id IS NOT NULL THEN 'reviewer' END) AS roles
        FROM APP_USER u
        LEFT JOIN AUTHOR a ON a.author_id = u.user_id
        LEFT JOIN REVIEWER r ON r.reviewer_id = u.user_id
        ORDER BY u.user_id""")
    return render_template("users.html", rows=rows)


@app.get("/users/<int:user_id>")
def user_detail(user_id):
    p = {"id": user_id}
    user = fetch_one("SELECT * FROM APP_USER WHERE user_id = :id", p)
    if user is None:
        abort(404)
    return render_template(
        "user_detail.html", user=user,
        author=fetch_one("SELECT orcid FROM AUTHOR WHERE author_id = :id", p),
        areas=fetch_all("SELECT area_label FROM AUTHOR_RESEARCH_AREA WHERE author_id = :id ORDER BY area_label", p),
        reviewer=fetch_one("SELECT years_exp FROM REVIEWER WHERE reviewer_id = :id", p),
        expertise=fetch_all("SELECT area_label FROM REVIEWER_EXPERTISE WHERE reviewer_id = :id ORDER BY area_label", p),
        papers=fetch_all("""SELECT p.paper_id, p.title, p.status, pa.author_position, pa.is_corresponding
                            FROM PAPER_AUTHOR pa INNER JOIN PAPER p ON p.paper_id = pa.paper_id
                            WHERE pa.author_id = :id ORDER BY p.paper_id""", p),
        reviews=fetch_all("""SELECT rv.review_id, rv.paper_id, p.title, rv.overall_score, rv.recommendation
                             FROM REVIEW rv INNER JOIN PAPER p ON p.paper_id = rv.paper_id
                             WHERE rv.reviewer_id = :id ORDER BY rv.review_id""", p))


# ---------- papers ----------
@app.get("/papers")
def papers():
    rows = fetch_all("""
        SELECT p.paper_id, p.title, p.status, c.acronym AS conference, t.track_name AS track,
               corr.given_name || ' ' || corr.surname AS corresponding_author,
               p.session_id,
               (SELECT MAX(v.version_no) FROM PAPER_VERSION v WHERE v.paper_id = p.paper_id) AS current_version
        FROM PAPER p
        INNER JOIN TRACK t ON t.track_id = p.track_id
        INNER JOIN CONFERENCE c ON c.conference_id = t.conference_id
        LEFT JOIN PAPER_AUTHOR pa ON pa.paper_id = p.paper_id AND pa.is_corresponding
        LEFT JOIN APP_USER corr ON corr.user_id = pa.author_id
        ORDER BY p.paper_id""")
    return render_template("papers.html", rows=rows)


@app.get("/papers/<int:paper_id>")
def paper_detail(paper_id):
    p = {"id": paper_id}
    paper = fetch_one("""
        SELECT p.paper_id, p.title, p.abstract, p.status, p.submission_date, p.session_id,
               t.track_name, c.acronym AS conference,
               s.title AS session_title, s.session_date, s.start_time, s.end_time, s.room_label
        FROM PAPER p
        INNER JOIN TRACK t ON t.track_id = p.track_id
        INNER JOIN CONFERENCE c ON c.conference_id = t.conference_id
        LEFT JOIN CONFERENCE_SESSION s ON s.session_id = p.session_id
        WHERE p.paper_id = :id""", p)
    if paper is None:
        abort(404)
    return render_template(
        "paper_detail.html", paper=paper,
        authors=fetch_all("""SELECT pa.author_position, pa.author_id,
                                    u.given_name || ' ' || u.surname AS full_name, pa.is_corresponding
                             FROM PAPER_AUTHOR pa INNER JOIN APP_USER u ON u.user_id = pa.author_id
                             WHERE pa.paper_id = :id ORDER BY pa.author_position""", p),
        keywords=fetch_all("SELECT keyword FROM PAPER_KEYWORD WHERE paper_id = :id ORDER BY keyword", p),
        versions=fetch_all("""SELECT version_no, file_location, uploaded_at, change_note
                              FROM PAPER_VERSION WHERE paper_id = :id ORDER BY version_no DESC""", p),
        reviews=fetch_all("""SELECT rv.review_id, u.given_name || ' ' || u.surname AS reviewer,
                                    rv.overall_score, rv.recommendation
                             FROM REVIEW rv INNER JOIN APP_USER u ON u.user_id = rv.reviewer_id
                             WHERE rv.paper_id = :id ORDER BY rv.review_id""", p))


# ---------- reviews ----------
@app.get("/reviews")
def reviews():
    rows = fetch_all("""
        SELECT rv.review_id, rv.paper_id, p.title AS paper,
               u.given_name || ' ' || u.surname AS reviewer,
               rv.overall_score, rv.recommendation, rv.review_submission_date
        FROM REVIEW rv
        INNER JOIN PAPER p ON p.paper_id = rv.paper_id
        INNER JOIN APP_USER u ON u.user_id = rv.reviewer_id
        ORDER BY rv.review_id""")
    return render_template("reviews.html", rows=rows)


# ---------- sessions ----------
@app.get("/sessions")
def sessions():
    rows = fetch_all("""
        SELECT s.session_id, s.title, c.acronym AS conference, s.session_date, s.start_time, s.end_time,
               s.room_label, u.given_name || ' ' || u.surname AS chair,
               (SELECT COUNT(*) FROM PAPER p WHERE p.session_id = s.session_id) AS papers
        FROM CONFERENCE_SESSION s
        INNER JOIN CONFERENCE c ON c.conference_id = s.conference_id
        INNER JOIN APP_USER u ON u.user_id = s.chair_id
        ORDER BY s.session_id""")
    return render_template("sessions.html", rows=rows)


if __name__ == "__main__":
    app.run(debug=True)