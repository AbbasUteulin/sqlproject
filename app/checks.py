# Every function takes an open SQLAlchemy connection and only READS data.
# A check that fails returns a message (or True); the caller must then reject the change.
from sqlalchemy import text


def is_self_review(conn, paper_id, reviewer_id):
    """Check 1a: True if the reviewer is an author of the paper (a review by them must be rejected).
    Use it when saving or editing a review."""
    row = conn.execute(
        text("SELECT 1 FROM PAPER_AUTHOR WHERE paper_id = :p AND author_id = :r"),
        {"p": paper_id, "r": reviewer_id},
    ).first()
    return row is not None


def author_has_reviewed_paper(conn, paper_id, author_id):
    """Check 1b: True if this person already reviewed the paper, so making them an author
    would create a self-review. Use it when adding or changing a paper's authors."""
    row = conn.execute(
        text("SELECT 1 FROM REVIEW WHERE paper_id = :p AND reviewer_id = :a"),
        {"p": paper_id, "a": author_id},
    ).first()
    return row is not None


def session_assignment_error(conn, paper_id, session_id):
    """Check 2: returns None if the paper may be in the session, otherwise the reason it may not.
    A scheduled paper must be accepted and its track's conference must be the session's conference.
    Use it when assigning a paper to a session."""
    row = conn.execute(
        text("""
            SELECT p.status, t.conference_id AS paper_conf, s.conference_id AS session_conf
            FROM PAPER p
            INNER JOIN TRACK t ON t.track_id = p.track_id
            CROSS JOIN CONFERENCE_SESSION s
            WHERE p.paper_id = :p AND s.session_id = :s
        """),
        {"p": paper_id, "s": session_id},
    ).first()
    if row is None:
        return "paper or session not found"
    if row.status != "accepted":
        return "only accepted papers can be scheduled"
    if row.paper_conf != row.session_conf:
        return "paper and session belong to different conferences"
    return None


def scheduled_paper_error(conn, paper_id):
    """Check 2, re-check: use it AFTER a paper's status or track changed, or a session's conference
    changed. Returns None if the paper has no session or its session is still valid."""
    row = conn.execute(
        text("SELECT session_id FROM PAPER WHERE paper_id = :p"), {"p": paper_id}
    ).first()
    if row is None or row.session_id is None:
        return None
    return session_assignment_error(conn, paper_id, row.session_id)