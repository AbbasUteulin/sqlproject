# Part 3 demo: runs the CRUD operations and the required rejections through the REAL Flask routes
# (Flask's test client sends the same POST requests a browser form would), then checks the
# database after every step to prove what was saved and what was rolled back.
#
#   python app/demo.py          (DATABASE_URL must be set, exactly as for app.py)
#
# WARNING: it rebuilds the database from the seed data at the start AND at the end (resetdb.py),
# so any data you typed into the web app is replaced by the seed data.
# That is why it refuses to run against the deployed cloud database (only against this computer),
# unless --allow-remote is given on purpose.
import html
import re
import sys
from sqlalchemy import text
from db import engine, is_local_database
from resetdb import reset_database
import app as webapp

if not is_local_database() and "--allow-remote" not in sys.argv:
    sys.exit(f"Refusing to run: DATABASE_URL points at {engine.url.host}, not this computer.\n"
             "demo.py erases the database, so run it against the local Docker database instead.\n"
             "(Add --allow-remote only if you really want to wipe that database.)")

client = webapp.app.test_client()
FLASH = re.compile(r'<div class="flash (\w+)"><strong>\w+:</strong> (.*?)</div>', re.S)
failures = []


def scalar(sql, **params):
    with engine.connect() as conn:
        return conn.execute(text(sql), params).scalar()


def check(label, condition):
    print(f"  {'ok  ' if condition else 'FAIL'}  {label}")
    if not condition:
        failures.append(label)


def post(label, url, data, expect):
    """POST a form like the browser does, print the flashed message, and compare the outcome
    ("success" or "error") with what we expect."""
    response = client.post(url, data=as_post(data), follow_redirects=True)
    flashes = [(cat, html.unescape(msg)) for cat, msg in FLASH.findall(response.get_data(as_text=True))]
    outcome, message = flashes[-1] if flashes else (f"HTTP {response.status_code}", "(no message)")
    print(f"{'PASS' if outcome == expect else 'FAIL'}  {label}")
    print(f"        -> HTTP {response.status_code}, {outcome}: {message}")
    if outcome != expect:
        failures.append(label)


def read(label, url, must_contain):
    response = client.get(url)
    ok = response.status_code == 200 and must_contain in response.get_data(as_text=True)
    print(f"{'PASS' if ok else 'FAIL'}  {label} (GET {url} -> HTTP {response.status_code})")
    if not ok:
        failures.append(label)


def as_post(form):
    """Form dict -> POST data: True checkboxes are sent as "on", False ones are left out (like a browser)."""
    return {k: ("on" if v is True else v) for k, v in form.items() if v is not False}


print("== Resetting the database to the seed data ==")
reset_database()

# ------------------------------------------------------------------------------------------
print("\n== USERS: create, read, update (author/reviewer profiles are part of the user form) ==")
post("Create user 'Demo Person' with an author profile and a reviewer profile", "/users/new", {
    "given_name": "Demo", "surname": "Person", "email": "demo.person@example.com",
    "affiliation": "Demo University", "country": "Kazakhstan", "phone_number": "+77010000013",
    "is_author": True, "orcid": "0000000100000013", "areas": ["Data Management", "HCI"],
    "is_reviewer": True, "years_exp": "2", "expertise": ["Security"]}, "success")
uid = scalar("SELECT user_id FROM APP_USER WHERE email = 'demo.person@example.com'")
check(f"user {uid} exists with an AUTHOR row, a REVIEWER row and 2 research areas",
      scalar("SELECT COUNT(*) FROM AUTHOR WHERE author_id = :id", id=uid) == 1
      and scalar("SELECT COUNT(*) FROM REVIEWER WHERE reviewer_id = :id", id=uid) == 1
      and scalar("SELECT COUNT(*) FROM AUTHOR_RESEARCH_AREA WHERE author_id = :id", id=uid) == 2)
read("Read the user's page", f"/users/{uid}", "Demo Person")

form = webapp.user_form_from_db(uid)
form.update(phone_number="+77010000099", is_reviewer=False)
post("Update the user: new phone number, remove the reviewer profile", f"/users/{uid}/edit", form, "success")
check("phone number changed and the REVIEWER row is gone",
      scalar("SELECT phone_number FROM APP_USER WHERE user_id = :id", id=uid) == "+77010000099"
      and scalar("SELECT COUNT(*) FROM REVIEWER WHERE reviewer_id = :id", id=uid) == 0)

# ------------------------------------------------------------------------------------------
print("\n== PAPERS: create, read, update, versions, delete (authorship and keywords are part of the paper form) ==")
form = webapp.blank_paper_form()
form.update(track_id="1", title="Demo Paper on Index Tuning", abstract="A short demo abstract.",
            status="submitted", author_1=str(uid), author_2="3", corresponding="1",
            keywords="indexing, demo", file_location="papers/demo/v1.pdf")
post("Create a paper with 2 authors, 2 keywords and version 1", "/papers/new", form, "success")
pid = scalar("SELECT paper_id FROM PAPER WHERE title = 'Demo Paper on Index Tuning'")
check(f"paper {pid} has 2 authors (Demo Person corresponding), 2 keywords, 1 version",
      scalar("SELECT COUNT(*) FROM PAPER_AUTHOR WHERE paper_id = :id", id=pid) == 2
      and scalar("SELECT author_id FROM PAPER_AUTHOR WHERE paper_id = :id AND is_corresponding", id=pid) == uid
      and scalar("SELECT COUNT(*) FROM PAPER_KEYWORD WHERE paper_id = :id", id=pid) == 2
      and scalar("SELECT COUNT(*) FROM PAPER_VERSION WHERE paper_id = :id", id=pid) == 1)
read("Read the paper's page", f"/papers/{pid}", "Demo Paper on Index Tuning")

form = webapp.paper_form_from_db(pid)
form.update(status="accepted", session_id="1", keywords="indexing, demo, tuning")
post("Update the paper: accept it, add a keyword, schedule it in session 1 (same conference: valid)",
     f"/papers/{pid}/edit", form, "success")
check("paper is accepted, in session 1, with 3 keywords",
      scalar("SELECT status FROM PAPER WHERE paper_id = :id", id=pid) == "accepted"
      and scalar("SELECT session_id FROM PAPER WHERE paper_id = :id", id=pid) == 1
      and scalar("SELECT COUNT(*) FROM PAPER_KEYWORD WHERE paper_id = :id", id=pid) == 3)

post("Add version 2 to the paper", f"/papers/{pid}/versions",
     {"file_location": "papers/demo/v2.pdf", "change_note": "Camera-ready"}, "success")
post("Delete version 1 of the paper", f"/papers/{pid}/versions/1/delete", {}, "success")
check("only version 2 is left",
      scalar("SELECT string_agg(version_no::text, ',') FROM PAPER_VERSION WHERE paper_id = :id", id=pid) == "2")

post("Delete the user while they are still an author of the paper (must be refused)",
     f"/users/{uid}/delete", {}, "error")
check("the user still exists (the failed delete was rolled back)",
      scalar("SELECT COUNT(*) FROM APP_USER WHERE user_id = :id", id=uid) == 1)

post("Delete the paper", f"/papers/{pid}/delete", {}, "success")
check("paper, authorship, keywords and versions are gone (ON DELETE CASCADE)",
      scalar("""SELECT (SELECT COUNT(*) FROM PAPER WHERE paper_id = :id)
                     + (SELECT COUNT(*) FROM PAPER_AUTHOR WHERE paper_id = :id)
                     + (SELECT COUNT(*) FROM PAPER_KEYWORD WHERE paper_id = :id)
                     + (SELECT COUNT(*) FROM PAPER_VERSION WHERE paper_id = :id)""", id=pid) == 0)

post("Delete the user (now allowed)", f"/users/{uid}/delete", {}, "success")
check("user and author profile are gone",
      scalar("SELECT COUNT(*) FROM APP_USER WHERE user_id = :id", id=uid) == 0
      and scalar("SELECT COUNT(*) FROM AUTHOR WHERE author_id = :id", id=uid) == 0)

# ------------------------------------------------------------------------------------------
print("\n== REVIEWS: create, read, update, delete ==")
post("Create a review of paper 3 by Saule Omarova (reviewer 7, not an author of paper 3)", "/reviews/new", {
    "paper_id": "3", "reviewer_id": "7", "overall_score": "4", "recommendation": "accept",
    "comments_for_authors": "Clear and useful cost model.", "confidential_comments": ""}, "success")
rid = scalar("SELECT review_id FROM REVIEW WHERE paper_id = 3 AND reviewer_id = 7")
check(f"review {rid} exists", rid is not None)
read("Read the review's page", f"/reviews/{rid}", "Clear and useful cost model.")

form = webapp.review_form_from_db(rid)
form.update(overall_score="5", comments_for_authors="Even better after the revision.")
post("Update the review: score 4 -> 5 and new comments", f"/reviews/{rid}/edit", form, "success")
check("score is now 5", scalar("SELECT overall_score FROM REVIEW WHERE review_id = :id", id=rid) == 5)

post("Delete the review", f"/reviews/{rid}/delete", {}, "success")
check("review is gone", scalar("SELECT COUNT(*) FROM REVIEW WHERE review_id = :id", id=rid) == 0)

# ------------------------------------------------------------------------------------------
print("\n== SESSIONS: create, read, update, delete ==")
post("Create a session in ADSC 2026 (conference 1) chaired by Arman Armanov (in its pool)", "/sessions/new", {
    "conference_id": "1", "title": "Demo Session", "session_date": "2026-06-17", "start_time": "11:00",
    "end_time": "12:30", "room_label": "D-100", "chair_id": "1"}, "success")
sid = scalar("SELECT session_id FROM CONFERENCE_SESSION WHERE title = 'Demo Session'")
check(f"session {sid} exists", sid is not None)
read("Read the session's page", f"/sessions/{sid}", "Demo Session")

form = webapp.session_form_from_db(sid)
form["room_label"] = "D-200"
post("Update the session: room D-100 -> D-200", f"/sessions/{sid}/edit", form, "success")
check("room is now D-200",
      scalar("SELECT room_label FROM CONFERENCE_SESSION WHERE session_id = :id", id=sid) == "D-200")

form = webapp.paper_form_from_db(3)
form["session_id"] = str(sid)
post("Valid session assignment: accepted paper 3 (ADSC) into the new ADSC session", "/papers/3/edit", form, "success")
check("paper 3 is in the new session", scalar("SELECT session_id FROM PAPER WHERE paper_id = 3") == sid)

post("Delete the session", f"/sessions/{sid}/delete", {}, "success")
check("session is gone and paper 3 is unscheduled again (ON DELETE SET NULL)",
      scalar("SELECT COUNT(*) FROM CONFERENCE_SESSION WHERE session_id = :id", id=sid) == 0
      and scalar("SELECT session_id FROM PAPER WHERE paper_id = 3") is None)

# ------------------------------------------------------------------------------------------
print("\n== REQUIRED REJECTIONS (each must fail AND leave the database unchanged) ==")
reviews_before = scalar("SELECT COUNT(*) FROM REVIEW")
post("Self-review: Arman Armanov (author of paper 1) tries to review paper 1", "/reviews/new", {
    "paper_id": "1", "reviewer_id": "1", "overall_score": "5", "recommendation": "accept",
    "comments_for_authors": "Great paper!", "confidential_comments": ""}, "error")
check("no review was added", scalar("SELECT COUNT(*) FROM REVIEW") == reviews_before)

form = webapp.paper_form_from_db(1)
form["author_3"] = "5"
post("Self-review (other direction): add Aliya Nurlanova, who already reviewed paper 1, as its author",
     "/papers/1/edit", form, "error")
check("paper 1 still has its 2 original authors",
      scalar("SELECT COUNT(*) FROM PAPER_AUTHOR WHERE paper_id = 1") == 2)

title_before = scalar("SELECT title FROM PAPER WHERE paper_id = 3")
form = webapp.paper_form_from_db(3)
form.update(title="TITLE CHANGED BY THE DEMO", session_id="4")
post("Invalid session: paper 3 (ADSC, conference 1) into session 4 (CASEF, conference 2), "
     "with a title change in the same form", "/papers/3/edit", form, "error")
check("rolled back: paper 3 has its old title and still no session",
      scalar("SELECT title FROM PAPER WHERE paper_id = 3") == title_before
      and scalar("SELECT session_id FROM PAPER WHERE paper_id = 3") is None)

form = webapp.paper_form_from_db(6)
form["session_id"] = "1"
post("Invalid session: paper 6 (status 'under review') into session 1", "/papers/6/edit", form, "error")
check("paper 6 is still unscheduled", scalar("SELECT session_id FROM PAPER WHERE paper_id = 6") is None)

form = webapp.session_form_from_db(1)
form.update(conference_id="2", chair_id="9")
post("Invalid session (re-check on session edit): move session 1, which holds ADSC paper 1, to CASEF",
     "/sessions/1/edit", form, "error")
check("session 1 still belongs to conference 1",
      scalar("SELECT conference_id FROM CONFERENCE_SESSION WHERE session_id = 1") == 1)

# ------------------------------------------------------------------------------------------
print("\n== Restoring the seed data ==")
reset_database()
if failures:
    print(f"\n{len(failures)} step(s) did not behave as expected:")
    for label in failures:
        print(f"  - {label}")
    sys.exit(1)
print("\nAll demo steps behaved as expected.")
