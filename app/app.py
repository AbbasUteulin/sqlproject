# Part 3: Flask web app for the conference / paper review database (Python + SQLAlchemy Core, textual SQL).
#   Chunks 1-2: foundation and READ pages (list + detail pages).
#   Chunks 3-4: CREATE / UPDATE / DELETE for users, papers, reviews and sessions,
#               the two Part 1 application checks, and one transaction per form submission.
#
# The same pattern is used by every write route:
#   GET  -> show the form (pre-filled from the database when editing).
#   POST -> run_tx(work) from transactions.py: every SQL statement of that form runs in ONE transaction.
#           success: COMMIT, flash a "success" message, redirect to the detail page (Post/Redirect/Get).
#           failure: ROLLBACK (nothing is saved), flash an "error" message that says why,
#                    and show the same form again with what the user typed (HTTP 400).
#
# Where the rules are enforced:
#   * PostgreSQL (sql1.sql): CHECK / UNIQUE / FOREIGN KEY constraints and self_review_trigger.
#     Their errors are turned into readable messages by transactions.describe_db_error.
#   * checks.py, the two Part 1 application checks, called INSIDE the same transaction:
#       1. no self-review:  is_self_review           (when a review is saved)
#                           author_has_reviewed_paper (when a paper's authors are saved)
#       2. valid session:   session_assignment_error  (when a paper is given a session)
#                           scheduled_paper_error     (re-check of each paper when a session is edited)
#
# Supporting tables (conferences, tracks, reviewer pools, hosts, labels) are read-only seed data,
# used only as selection lists (see lookups.py).
import os
from flask import Flask, render_template, abort, request, redirect, url_for, flash
from sqlalchemy import text
from db import engine
import checks
import lookups
from transactions import CheckFailed, run_tx, req_text, opt_text, req_int, opt_int, next_id

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-only-change-me")   # needed for flash messages


# ---------- small helpers ----------
def fetch_all(sql, params=None):
    """SELECT -> list of dictionaries (column name -> value)."""
    with engine.connect() as conn:
        return conn.execute(text(sql), params or {}).mappings().all()


def fetch_one(sql, params=None):
    rows = fetch_all(sql, params)
    return rows[0] if rows else None


def unique(items):
    """Strip, drop blanks and duplicates, keep the original order (for keywords and labels)."""
    result = []
    for item in items:
        item = item.strip()
        if item and item not in result:
            result.append(item)
    return result


def user_name(conn, user_id):
    name = conn.execute(text("SELECT given_name || ' ' || surname FROM APP_USER WHERE user_id = :id"),
                        {"id": user_id}).scalar()
    return name or f"user {user_id}"


def submit_form(work, template, context, done):
    """Create/edit forms: run work(conn) in one transaction.
    Success -> flash done(result)[0] and redirect to done(result)[1].
    Failure -> everything is rolled back; flash the reason and show the form again."""
    ok, result = run_tx(work)
    if ok:
        message, url = done(result)
        flash(message, "success")
        return redirect(url)
    flash(result, "error")
    return render_template(template, **context), 400


def run_and_redirect(work, ok_url, fail_url):
    """Delete buttons and the small version forms: one transaction, then redirect with a message."""
    ok, message = run_tx(work)
    flash(message, "success" if ok else "error")
    return redirect(ok_url if ok else fail_url)


def as_str(value):
    """Database value -> form value (forms always hold strings; None becomes empty)."""
    return "" if value is None else str(value)


@app.get("/")
def index():
    counts = {
        "users": fetch_one("SELECT COUNT(*) AS n FROM APP_USER")["n"],
        "papers": fetch_one("SELECT COUNT(*) AS n FROM PAPER")["n"],
        "reviews": fetch_one("SELECT COUNT(*) AS n FROM REVIEW")["n"],
        "sessions": fetch_one("SELECT COUNT(*) AS n FROM CONFERENCE_SESSION")["n"],
    }
    return render_template("index.html", **counts)


# =====================================================================================
# USERS (the author and reviewer profiles are managed inside the user form)
# =====================================================================================
USER_LABELS = {"given_name": "Given name", "surname": "Surname", "email": "Email",
               "affiliation": "Affiliation", "country": "Country", "phone_number": "Phone number"}


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
        pools=fetch_all("""SELECT c.conference_id, c.acronym FROM CONFERENCE_REVIEWER cr
                           INNER JOIN CONFERENCE c ON c.conference_id = cr.conference_id
                           WHERE cr.reviewer_id = :id ORDER BY c.conference_id""", p),
        papers=fetch_all("""SELECT p.paper_id, p.title, p.status, pa.author_position, pa.is_corresponding
                            FROM PAPER_AUTHOR pa INNER JOIN PAPER p ON p.paper_id = pa.paper_id
                            WHERE pa.author_id = :id ORDER BY p.paper_id""", p),
        reviews=fetch_all("""SELECT rv.review_id, rv.paper_id, p.title, rv.overall_score, rv.recommendation
                             FROM REVIEW rv INNER JOIN PAPER p ON p.paper_id = rv.paper_id
                             WHERE rv.reviewer_id = :id ORDER BY rv.review_id""", p))


def blank_user_form():
    form = {k: "" for k in list(USER_LABELS) + ["orcid", "years_exp"]}
    form.update(is_author=False, areas=[], is_reviewer=False, expertise=[])
    return form


def user_form_from_db(user_id):
    p = {"id": user_id}
    user = fetch_one("SELECT * FROM APP_USER WHERE user_id = :id", p)
    if user is None:
        abort(404)
    author = fetch_one("SELECT orcid FROM AUTHOR WHERE author_id = :id", p)
    reviewer = fetch_one("SELECT years_exp FROM REVIEWER WHERE reviewer_id = :id", p)
    form = {k: as_str(user[k]) for k in USER_LABELS}
    form.update(
        is_author=author is not None,
        orcid=as_str(author["orcid"]) if author else "",
        areas=[r["area_label"] for r in fetch_all(
            "SELECT area_label FROM AUTHOR_RESEARCH_AREA WHERE author_id = :id", p)],
        is_reviewer=reviewer is not None,
        years_exp=as_str(reviewer["years_exp"]) if reviewer else "",
        expertise=[r["area_label"] for r in fetch_all(
            "SELECT area_label FROM REVIEWER_EXPERTISE WHERE reviewer_id = :id", p)])
    return form


def user_form_from_request():
    f = request.form
    form = {k: f.get(k, "") for k in list(USER_LABELS) + ["orcid", "years_exp"]}
    form.update(is_author="is_author" in f, areas=f.getlist("areas"),
                is_reviewer="is_reviewer" in f, expertise=f.getlist("expertise"))
    return form


def user_form_context(form, user_id=None):
    return dict(f=form, user_id=user_id, labels=lookups.label_options())


def save_user(conn, user_id, form):
    """Insert (user_id is None) or update one user, together with their author and reviewer
    profiles. Runs inside run_tx, so the user row and both profiles are saved together or not at all."""
    values = {k: req_text(form[k], label) for k, label in USER_LABELS.items()}
    if user_id is None:
        user_id = next_id(conn, "APP_USER", "user_id")
        conn.execute(text("""
            INSERT INTO APP_USER (user_id, given_name, surname, email, affiliation, country, phone_number)
            VALUES (:id, :given_name, :surname, :email, :affiliation, :country, :phone_number)"""),
            {"id": user_id, **values})           # UNIQUE(email) is checked by the database
    else:
        updated = conn.execute(text("""
            UPDATE APP_USER SET given_name = :given_name, surname = :surname, email = :email,
                   affiliation = :affiliation, country = :country, phone_number = :phone_number
            WHERE user_id = :id"""), {"id": user_id, **values})
        if updated.rowcount == 0:
            raise CheckFailed(f"User {user_id} does not exist.")
    p = {"id": user_id}

    # Author profile = an AUTHOR row (ORCID) + AUTHOR_RESEARCH_AREA rows.
    if form["is_author"]:
        # ON CONFLICT: create the profile if it is new, otherwise just update the ORCID.
        conn.execute(text("""INSERT INTO AUTHOR (author_id, orcid) VALUES (:id, :orcid)
                             ON CONFLICT (author_id) DO UPDATE SET orcid = EXCLUDED.orcid"""),
                     {"id": user_id, "orcid": opt_text(form["orcid"])})
        # The ticked research areas replace the old ones.
        conn.execute(text("DELETE FROM AUTHOR_RESEARCH_AREA WHERE author_id = :id"), p)
        for label in unique(form["areas"]):
            conn.execute(text("INSERT INTO AUTHOR_RESEARCH_AREA (author_id, area_label) VALUES (:id, :label)"),
                         {"id": user_id, "label": label})
    else:
        # Removing the author role: ON DELETE CASCADE removes the research areas, but the foreign
        # key from PAPER_AUTHOR (no cascade) blocks this while the user still authors a paper.
        conn.execute(text("DELETE FROM AUTHOR WHERE author_id = :id"), p)

    # Reviewer profile = a REVIEWER row (years of experience) + REVIEWER_EXPERTISE rows.
    if form["is_reviewer"]:
        years = req_int(form["years_exp"], "Years of reviewing experience")   # >= 0 is a CHECK in the DB
        conn.execute(text("""INSERT INTO REVIEWER (reviewer_id, years_exp) VALUES (:id, :years)
                             ON CONFLICT (reviewer_id) DO UPDATE SET years_exp = EXCLUDED.years_exp"""),
                     {"id": user_id, "years": years})
        conn.execute(text("DELETE FROM REVIEWER_EXPERTISE WHERE reviewer_id = :id"), p)
        for label in unique(form["expertise"]):
            conn.execute(text("INSERT INTO REVIEWER_EXPERTISE (reviewer_id, area_label) VALUES (:id, :label)"),
                         {"id": user_id, "label": label})
    else:
        # Removing the reviewer role is blocked by the foreign keys while the user still has reviews,
        # is in a conference's reviewer pool, coordinates a track or chairs a session.
        conn.execute(text("DELETE FROM REVIEWER WHERE reviewer_id = :id"), p)
    return user_id


@app.route("/users/new", methods=["GET", "POST"])
def user_new():
    if request.method == "GET":
        return render_template("user_form.html", **user_form_context(blank_user_form()))
    form = user_form_from_request()
    return submit_form(lambda conn: save_user(conn, None, form), "user_form.html", user_form_context(form),
                       lambda uid: (f"User {uid} created.", url_for("user_detail", user_id=uid)))


@app.route("/users/<int:user_id>/edit", methods=["GET", "POST"])
def user_edit(user_id):
    if request.method == "GET":
        return render_template("user_form.html", **user_form_context(user_form_from_db(user_id), user_id))
    form = user_form_from_request()
    return submit_form(lambda conn: save_user(conn, user_id, form), "user_form.html",
                       user_form_context(form, user_id),
                       lambda uid: (f"User {uid} updated.", url_for("user_detail", user_id=uid)))


@app.post("/users/<int:user_id>/delete")
def user_delete(user_id):
    def work(conn):
        # AUTHOR, REVIEWER and their labels go with the user (ON DELETE CASCADE). Authorships,
        # reviews, pool membership and session chairs have no cascade, so they block the delete
        # and describe_db_error explains which one.
        if conn.execute(text("DELETE FROM APP_USER WHERE user_id = :id"), {"id": user_id}).rowcount == 0:
            raise CheckFailed(f"User {user_id} does not exist.")
        return f"User {user_id} deleted, together with their author/reviewer profiles."
    return run_and_redirect(work, url_for("users"), url_for("user_detail", user_id=user_id))


# =====================================================================================
# PAPERS (authorship, keywords and versions are managed inside the paper workflow)
# =====================================================================================
STATUSES = ["submitted", "under review", "accepted", "rejected", "withdrawn"]
PAPER_FIELDS = ["track_id", "title", "abstract", "status", "session_id", "corresponding", "keywords",
                "file_location"]


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


def author_slots(form):
    """Slot numbers of the author_<n> fields, in order. Slot order = author position."""
    return sorted(int(k[7:]) for k in form if k.startswith("author_") and k[7:].isdigit())


def blank_paper_form():
    form = {k: "" for k in PAPER_FIELDS}
    form.update(status="submitted", corresponding="1")
    form.update({f"author_{slot}": "" for slot in range(1, 6)})      # 5 empty author slots
    return form


def paper_form_from_db(paper_id):
    p = {"id": paper_id}
    paper = fetch_one("SELECT * FROM PAPER WHERE paper_id = :id", p)
    if paper is None:
        abort(404)
    authors = fetch_all("""SELECT author_id, is_corresponding FROM PAPER_AUTHOR
                           WHERE paper_id = :id ORDER BY author_position""", p)
    keywords = fetch_all("SELECT keyword FROM PAPER_KEYWORD WHERE paper_id = :id ORDER BY keyword", p)
    form = {k: "" for k in PAPER_FIELDS}
    form.update(track_id=as_str(paper["track_id"]), title=paper["title"], abstract=paper["abstract"],
                status=paper["status"], session_id=as_str(paper["session_id"]),
                keywords=", ".join(k["keyword"] for k in keywords))
    # Always at least 5 slots, and 2 empty ones to add authors, so no existing author is ever lost.
    for slot in range(1, max(5, len(authors) + 2) + 1):
        form[f"author_{slot}"] = ""
    for slot, row in enumerate(authors, start=1):
        form[f"author_{slot}"] = as_str(row["author_id"])
        if row["is_corresponding"]:
            form["corresponding"] = str(slot)
    return form


def paper_form_from_request():
    f = request.form
    form = {k: f.get(k, "") for k in PAPER_FIELDS}
    form.update({k: v for k, v in f.items() if k.startswith("author_")})
    return form


def paper_form_context(form, paper_id=None):
    return dict(f=form, paper_id=paper_id, slots=author_slots(form), statuses=STATUSES,
                tracks=lookups.track_options(), sessions=lookups.session_options(),
                authors=lookups.author_options())


def save_paper(conn, paper_id, form):
    """Insert (paper_id is None) or update a paper with its authors, keywords, first version and
    session, all in the caller's transaction. Any failed check rolls back the WHOLE submission."""
    creating = paper_id is None
    track_id = req_int(form["track_id"], "Track")
    title = req_text(form["title"], "Title")
    abstract = req_text(form["abstract"], "Abstract")
    status = req_text(form["status"], "Status")          # allowed values: CHECK paper_status
    session_id = opt_int(form["session_id"], "Session")

    # Authors: the filled slots, in slot order, become positions 1, 2, 3, ...
    authors, corresponding_id = [], None
    for slot in author_slots(form):
        author_id = opt_int(form[f"author_{slot}"], f"Author slot {slot}")
        if author_id is None:
            if form["corresponding"] == str(slot):
                raise CheckFailed(f"The corresponding author is set to slot {slot}, but that slot is empty.")
            continue
        if author_id in authors:
            raise CheckFailed(f"{user_name(conn, author_id)} is listed in more than one author slot.")
        authors.append(author_id)
        if form["corresponding"] == str(slot):
            corresponding_id = author_id
    if not authors:
        raise CheckFailed("A paper needs at least one author.")

    # Step 1: the paper row. session_id is written as NULL here and only set in step 5,
    # after application check 2 has approved it.
    params = {"id": paper_id, "track": track_id, "title": title, "abstract": abstract, "status": status}
    if creating:
        paper_id = params["id"] = next_id(conn, "PAPER", "paper_id")
        conn.execute(text("""
            INSERT INTO PAPER (paper_id, track_id, title, abstract, submission_date, status, session_id)
            VALUES (:id, :track, :title, :abstract, now(), :status, NULL)"""), params)
    else:
        updated = conn.execute(text("""
            UPDATE PAPER SET track_id = :track, title = :title, abstract = :abstract,
                   status = :status, session_id = NULL
            WHERE paper_id = :id"""), params)
        if updated.rowcount == 0:
            raise CheckFailed(f"Paper {paper_id} does not exist.")
    p = {"id": paper_id}

    # Step 2: authorship. The old list is replaced by the new one.
    conn.execute(text("DELETE FROM PAPER_AUTHOR WHERE paper_id = :id"), p)
    for position, author_id in enumerate(authors, start=1):
        # Application check 1, other direction: the database trigger only checks new REVIEWS,
        # so adding someone who already reviewed this paper as an AUTHOR is caught here.
        if checks.author_has_reviewed_paper(conn, paper_id, author_id):
            raise CheckFailed(f"Self-review rule: {user_name(conn, author_id)} has already reviewed this paper, "
                              f"so they cannot become one of its authors.")
        conn.execute(text("""
            INSERT INTO PAPER_AUTHOR (paper_id, author_id, author_position, is_corresponding)
            VALUES (:id, :author, :position, :corr)"""),
            {"id": paper_id, "author": author_id, "position": position, "corr": author_id == corresponding_id})

    # Step 3: keywords ("a, b, c"), replaced as a set.
    conn.execute(text("DELETE FROM PAPER_KEYWORD WHERE paper_id = :id"), p)
    for keyword in unique(form["keywords"].split(",")):
        conn.execute(text("INSERT INTO PAPER_KEYWORD (paper_id, keyword) VALUES (:id, :kw)"),
                     {"id": paper_id, "kw": keyword})

    # Step 4: the first version (only on the create form; later versions use the version form).
    file_location = opt_text(form.get("file_location"))
    if creating and file_location:
        conn.execute(text("""INSERT INTO PAPER_VERSION (paper_id, version_no, file_location)
                             VALUES (:id, 1, :file)"""), {"id": paper_id, "file": file_location})

    # Step 5: session assignment, application check 2. It runs after step 1 on purpose, so it
    # sees the paper's NEW status and track: the paper must be accepted, and its track's
    # conference must be the session's conference.
    if session_id is not None:
        error = checks.session_assignment_error(conn, paper_id, session_id)
        if error:
            raise CheckFailed(f"Invalid session assignment: {error}.")
        conn.execute(text("UPDATE PAPER SET session_id = :s WHERE paper_id = :id"),
                     {"s": session_id, "id": paper_id})
    return paper_id


@app.route("/papers/new", methods=["GET", "POST"])
def paper_new():
    if request.method == "GET":
        return render_template("paper_form.html", **paper_form_context(blank_paper_form()))
    form = paper_form_from_request()
    return submit_form(lambda conn: save_paper(conn, None, form), "paper_form.html", paper_form_context(form),
                       lambda pid: (f"Paper {pid} created.", url_for("paper_detail", paper_id=pid)))


@app.route("/papers/<int:paper_id>/edit", methods=["GET", "POST"])
def paper_edit(paper_id):
    if request.method == "GET":
        return render_template("paper_form.html", **paper_form_context(paper_form_from_db(paper_id), paper_id))
    form = paper_form_from_request()
    return submit_form(lambda conn: save_paper(conn, paper_id, form), "paper_form.html",
                       paper_form_context(form, paper_id),
                       lambda pid: (f"Paper {pid} updated.", url_for("paper_detail", paper_id=pid)))


@app.post("/papers/<int:paper_id>/delete")
def paper_delete(paper_id):
    def work(conn):
        # Authorship, keywords, versions and reviews are removed by ON DELETE CASCADE.
        if conn.execute(text("DELETE FROM PAPER WHERE paper_id = :id"), {"id": paper_id}).rowcount == 0:
            raise CheckFailed(f"Paper {paper_id} does not exist.")
        return f"Paper {paper_id} deleted, together with its authorship, keywords, versions and reviews."
    return run_and_redirect(work, url_for("papers"), url_for("paper_detail", paper_id=paper_id))


@app.post("/papers/<int:paper_id>/versions")
def version_add(paper_id):
    file_location, change_note = request.form.get("file_location"), request.form.get("change_note")

    def work(conn):
        file = req_text(file_location, "File location")
        if conn.execute(text("SELECT 1 FROM PAPER WHERE paper_id = :id"), {"id": paper_id}).first() is None:
            raise CheckFailed(f"Paper {paper_id} does not exist.")
        # New version = highest existing number + 1 (numbers may have gaps; the highest is current).
        version_no = conn.execute(text("""SELECT COALESCE(MAX(version_no), 0) + 1 FROM PAPER_VERSION
                                          WHERE paper_id = :id"""), {"id": paper_id}).scalar()
        conn.execute(text("""INSERT INTO PAPER_VERSION (paper_id, version_no, file_location, change_note)
                             VALUES (:id, :no, :file, :note)"""),          # uploaded_at defaults to now()
                     {"id": paper_id, "no": version_no, "file": file, "note": opt_text(change_note)})
        return f"Version {version_no} added to paper {paper_id}."
    url = url_for("paper_detail", paper_id=paper_id)
    return run_and_redirect(work, url, url)


@app.post("/papers/<int:paper_id>/versions/<int:version_no>/delete")
def version_delete(paper_id, version_no):
    def work(conn):
        deleted = conn.execute(text("DELETE FROM PAPER_VERSION WHERE paper_id = :id AND version_no = :no"),
                               {"id": paper_id, "no": version_no}).rowcount
        if deleted == 0:
            raise CheckFailed(f"Paper {paper_id} has no version {version_no}.")
        return f"Version {version_no} of paper {paper_id} deleted."
    url = url_for("paper_detail", paper_id=paper_id)
    return run_and_redirect(work, url, url)


# =====================================================================================
# REVIEWS
# =====================================================================================
REVIEW_FIELDS = ["paper_id", "reviewer_id", "overall_score", "recommendation",
                 "comments_for_authors", "confidential_comments"]


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


@app.get("/reviews/<int:review_id>")
def review_detail(review_id):
    review = fetch_one("""
        SELECT rv.*, p.title AS paper_title, u.given_name || ' ' || u.surname AS reviewer
        FROM REVIEW rv
        INNER JOIN PAPER p ON p.paper_id = rv.paper_id
        INNER JOIN APP_USER u ON u.user_id = rv.reviewer_id
        WHERE rv.review_id = :id""", {"id": review_id})
    if review is None:
        abort(404)
    return render_template("review_detail.html", review=review)


def blank_review_form():
    form = {k: "" for k in REVIEW_FIELDS}
    form["recommendation"] = "accept"
    return form


def review_form_from_db(review_id):
    review = fetch_one("SELECT * FROM REVIEW WHERE review_id = :id", {"id": review_id})
    if review is None:
        abort(404)
    return {k: as_str(review[k]) for k in REVIEW_FIELDS}


def review_form_from_request():
    return {k: request.form.get(k, "") for k in REVIEW_FIELDS}


def review_form_context(form, review_id=None):
    return dict(f=form, review_id=review_id, papers=lookups.paper_options(),
                reviewers=lookups.reviewer_options())


def save_review(conn, review_id, form):
    paper_id = req_int(form["paper_id"], "Paper")
    reviewer_id = req_int(form["reviewer_id"], "Reviewer")
    params = {
        "id": review_id, "paper": paper_id, "reviewer": reviewer_id,
        "score": req_int(form["overall_score"], "Overall score"),            # 1..5: CHECK one_to_five
        "rec": req_text(form["recommendation"], "Recommendation"),          # CHECK recommendation_status
        "comments": req_text(form["comments_for_authors"], "Comments for authors"),
        "confidential": opt_text(form["confidential_comments"]),
    }
    # Application check 1: an author of the paper cannot review it. Checked before writing, so the
    # user gets a clear message; self_review_trigger in the database is the safety net.
    if checks.is_self_review(conn, paper_id, reviewer_id):
        raise CheckFailed(f"Self-review rejected: {user_name(conn, reviewer_id)} is an author of "
                          f"paper {paper_id}, so they cannot review it.")
    if review_id is None:
        review_id = params["id"] = next_id(conn, "REVIEW", "review_id")
        conn.execute(text("""
            INSERT INTO REVIEW (review_id, paper_id, reviewer_id, overall_score, recommendation,
                                comments_for_authors, confidential_comments, review_submission_date)
            VALUES (:id, :paper, :reviewer, :score, :rec, :comments, :confidential, now())"""), params)
    else:
        updated = conn.execute(text("""
            UPDATE REVIEW SET paper_id = :paper, reviewer_id = :reviewer, overall_score = :score,
                   recommendation = :rec, comments_for_authors = :comments,
                   confidential_comments = :confidential
            WHERE review_id = :id"""), params)                 # UNIQUE(paper_id, reviewer_id) in the DB
        if updated.rowcount == 0:
            raise CheckFailed(f"Review {review_id} does not exist.")
    return review_id


@app.route("/reviews/new", methods=["GET", "POST"])
def review_new():
    if request.method == "GET":
        form = blank_review_form()
        form["paper_id"] = request.args.get("paper_id", "")      # "Add review" link on a paper page
        return render_template("review_form.html", **review_form_context(form))
    form = review_form_from_request()
    return submit_form(lambda conn: save_review(conn, None, form), "review_form.html", review_form_context(form),
                       lambda rid: (f"Review {rid} created.", url_for("review_detail", review_id=rid)))


@app.route("/reviews/<int:review_id>/edit", methods=["GET", "POST"])
def review_edit(review_id):
    if request.method == "GET":
        return render_template("review_form.html", **review_form_context(review_form_from_db(review_id), review_id))
    form = review_form_from_request()
    return submit_form(lambda conn: save_review(conn, review_id, form), "review_form.html",
                       review_form_context(form, review_id),
                       lambda rid: (f"Review {rid} updated.", url_for("review_detail", review_id=rid)))


@app.post("/reviews/<int:review_id>/delete")
def review_delete(review_id):
    def work(conn):
        if conn.execute(text("DELETE FROM REVIEW WHERE review_id = :id"), {"id": review_id}).rowcount == 0:
            raise CheckFailed(f"Review {review_id} does not exist.")
        return f"Review {review_id} deleted."
    return run_and_redirect(work, url_for("reviews"), url_for("review_detail", review_id=review_id))


# =====================================================================================
# SESSIONS
# =====================================================================================
SESSION_FIELDS = ["conference_id", "title", "session_date", "start_time", "end_time", "room_label", "chair_id"]


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


@app.get("/sessions/<int:session_id>")
def session_detail(session_id):
    p = {"id": session_id}
    sess = fetch_one("""
        SELECT s.*, c.acronym, u.given_name || ' ' || u.surname AS chair
        FROM CONFERENCE_SESSION s
        INNER JOIN CONFERENCE c ON c.conference_id = s.conference_id
        INNER JOIN APP_USER u ON u.user_id = s.chair_id
        WHERE s.session_id = :id""", p)
    if sess is None:
        abort(404)
    return render_template("session_detail.html", sess=sess, papers=fetch_all("""
        SELECT p.paper_id, p.title, p.status, t.track_name
        FROM PAPER p INNER JOIN TRACK t ON t.track_id = p.track_id
        WHERE p.session_id = :id ORDER BY p.paper_id""", p))


def blank_session_form():
    return {k: "" for k in SESSION_FIELDS}


def session_form_from_db(session_id):
    row = fetch_one("SELECT * FROM CONFERENCE_SESSION WHERE session_id = :id", {"id": session_id})
    if row is None:
        abort(404)
    form = {k: as_str(row[k]) for k in SESSION_FIELDS}
    form["start_time"] = row["start_time"].strftime("%H:%M")      # what <input type="time"> expects
    form["end_time"] = row["end_time"].strftime("%H:%M")
    return form


def session_form_from_request():
    return {k: request.form.get(k, "") for k in SESSION_FIELDS}


def session_form_context(form, session_id=None):
    return dict(f=form, session_id=session_id, conferences=lookups.conference_options(),
                chairs=lookups.chair_options())


def save_session(conn, session_id, form):
    params = {
        "id": session_id,
        "conf": req_int(form["conference_id"], "Conference"),
        "title": req_text(form["title"], "Title"),
        "date": req_text(form["session_date"], "Date"),       # PostgreSQL parses and validates the date/time
        "start": req_text(form["start_time"], "Start time"),
        "end": req_text(form["end_time"], "End time"),        # end > start: CHECK session_times_ok
        "room": req_text(form["room_label"], "Room"),
        "chair": req_int(form["chair_id"], "Chair"),          # must be in the conference's pool: composite FK
    }
    if session_id is None:
        session_id = params["id"] = next_id(conn, "CONFERENCE_SESSION", "session_id")
        conn.execute(text("""
            INSERT INTO CONFERENCE_SESSION (session_id, conference_id, title, session_date, start_time,
                                            end_time, room_label, chair_id)
            VALUES (:id, :conf, :title, :date, :start, :end, :room, :chair)"""), params)
    else:
        updated = conn.execute(text("""
            UPDATE CONFERENCE_SESSION SET conference_id = :conf, title = :title, session_date = :date,
                   start_time = :start, end_time = :end, room_label = :room, chair_id = :chair
            WHERE session_id = :id"""), params)
        if updated.rowcount == 0:
            raise CheckFailed(f"Session {session_id} does not exist.")
        # Application check 2, re-check: if the session moved to another conference, the papers
        # already scheduled in it may no longer be valid. One invalid paper rolls back the edit.
        for paper in conn.execute(text("SELECT paper_id, title FROM PAPER WHERE session_id = :id ORDER BY paper_id"),
                                  {"id": session_id}).all():
            error = checks.scheduled_paper_error(conn, paper.paper_id)
            if error:
                raise CheckFailed(f"Rejected: paper {paper.paper_id} ('{paper.title}') is scheduled in this "
                                  f"session, but {error}. Unschedule or move that paper first.")
    return session_id


@app.route("/sessions/new", methods=["GET", "POST"])
def session_new():
    if request.method == "GET":
        return render_template("session_form.html", **session_form_context(blank_session_form()))
    form = session_form_from_request()
    return submit_form(lambda conn: save_session(conn, None, form), "session_form.html",
                       session_form_context(form),
                       lambda sid: (f"Session {sid} created.", url_for("session_detail", session_id=sid)))


@app.route("/sessions/<int:session_id>/edit", methods=["GET", "POST"])
def session_edit(session_id):
    if request.method == "GET":
        return render_template("session_form.html",
                               **session_form_context(session_form_from_db(session_id), session_id))
    form = session_form_from_request()
    return submit_form(lambda conn: save_session(conn, session_id, form), "session_form.html",
                       session_form_context(form, session_id),
                       lambda sid: (f"Session {sid} updated.", url_for("session_detail", session_id=sid)))


@app.post("/sessions/<int:session_id>/delete")
def session_delete(session_id):
    def work(conn):
        p = {"id": session_id}
        scheduled = conn.execute(text("SELECT COUNT(*) FROM PAPER WHERE session_id = :id"), p).scalar()
        # PAPER.session_id is ON DELETE SET NULL: the papers stay, they just become unscheduled.
        if conn.execute(text("DELETE FROM CONFERENCE_SESSION WHERE session_id = :id"), p).rowcount == 0:
            raise CheckFailed(f"Session {session_id} does not exist.")
        return f"Session {session_id} deleted; {scheduled} paper(s) in it are now unscheduled."
    return run_and_redirect(work, url_for("sessions"), url_for("session_detail", session_id=session_id))


if __name__ == "__main__":
    app.run(debug=True)
