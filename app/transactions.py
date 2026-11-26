# Part 3, chunk 4: transactions and clear error reporting for every write in the web app.
#
# The idea:
#   * Every form submission does ALL of its SQL inside ONE transaction (run_tx).
#     engine.begin() commits when the block finishes and rolls back if anything raises,
#     so a form is either saved completely or not at all (e.g. a paper's row, authors,
#     keywords and session assignment are saved together or not at all).
#   * A failure can come from two places, and both become a readable message:
#       1. CheckFailed     - raised by our own code: the Part 1 application checks
#                            (self-review, session assignment) or a missing/invalid form field.
#       2. DBAPIError      - raised by PostgreSQL: a CHECK / UNIQUE / FOREIGN KEY constraint,
#                            or the self_review_trigger. describe_db_error() turns it into words.
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from db import engine


class CheckFailed(Exception):
    """An application-level rule was broken. The message is shown to the user as-is."""


def run_tx(work):
    """Run work(conn) in one transaction.
    Returns (True, whatever work returned) after a COMMIT,
    or (False, error message) after a ROLLBACK."""
    try:
        with engine.begin() as conn:          # BEGIN ... COMMIT, or ROLLBACK on an exception
            return True, work(conn)
    except CheckFailed as e:
        return False, str(e)
    except DBAPIError as e:                    # IntegrityError, DataError, trigger RAISE EXCEPTION, ...
        return False, describe_db_error(e)


# ---------- turning PostgreSQL errors into plain words ----------
# Constraint names come from sql1.sql. Unnamed constraints get PostgreSQL's automatic names
# (<table>_<column>_key for UNIQUE, <table>_<columns>_fkey for FOREIGN KEY, <table>_pkey).

# Messages for INSERT/UPDATE that break a rule.
CONSTRAINT_MESSAGES = {
    "paper_status": "status must be one of: submitted, under review, accepted, rejected, withdrawn.",
    "scheduled_only_if_accepted": "only accepted papers can be assigned to a session.",
    "one_to_five": "the overall score must be between 1 and 5.",
    "recommendation_status": "the recommendation must be 'accept' or 'reject'.",
    "review_unique": "this reviewer has already reviewed this paper (one review per reviewer per paper).",
    "session_times_ok": "a session's end time must be after its start time.",
    "one_corresponding_per_paper": "a paper can have only one corresponding author.",
    "paper_author_unique": "two authors of a paper cannot have the same position.",
    "paper_author_pkey": "the same author is listed twice on this paper.",
    "positive_author_pos": "author positions must be positive.",
    "non_negative_rev_exp": "years of reviewing experience cannot be negative.",
    "pos_version_no": "version numbers must be positive.",
    "app_user_email_key": "another user already has this email address.",
    "author_orcid_key": "another author already has this ORCID.",
    "conference_session_conference_id_chair_id_fkey":
        "the session chair must be in the selected conference's reviewer pool.",
    "conference_session_chair_id_fkey": "the session chair must be a reviewer.",
    "conference_session_conference_id_fkey": "the selected conference does not exist.",
    "paper_track_id_fkey": "the selected track does not exist.",
    "paper_session_id_fkey": "the selected session does not exist.",
    "review_paper_id_fkey": "the selected paper does not exist.",
    "review_reviewer_id_fkey": "the selected reviewer does not exist.",
    "paper_author_author_id_fkey": "the selected author does not exist (the user needs an author profile).",
}

# Messages for DELETEs blocked because other rows still point at the row
# (these foreign keys have no ON DELETE CASCADE on purpose).
STILL_REFERENCED_MESSAGES = {
    "paper_author_author_id_fkey":
        "this user is still an author of at least one paper. Remove them from those papers first.",
    "review_reviewer_id_fkey":
        "this user still has reviews. Delete those reviews first.",
    "conference_reviewer_reviewer_id_fkey":
        "this user is in a conference's reviewer pool (pools are read-only seed data).",
    "track_coordinator_id_fkey": "this user still coordinates a track.",
    "track_conference_id_coordinator_id_fkey": "this user still coordinates a track.",
    "conference_session_chair_id_fkey": "this user still chairs a session. Change the session's chair first.",
    "conference_session_conference_id_chair_id_fkey":
        "this user still chairs a session. Change the session's chair first.",
}


def describe_db_error(e):
    """Build a readable message from a psycopg2 error (wrapped by SQLAlchemy)."""
    orig = getattr(e, "orig", None)
    diag = getattr(orig, "diag", None)
    code = getattr(orig, "pgcode", None)
    constraint = getattr(diag, "constraint_name", None)
    primary = getattr(diag, "message_primary", None) or str(orig or e).splitlines()[0]
    detail = getattr(diag, "message_detail", None) or ""

    if code == "P0001" and "self-review" in primary:      # RAISE EXCEPTION in self_review_trigger
        return "Rejected by the database trigger: an author of a paper cannot review it (self-review)."
    if code == "23503" and "still referenced" in detail and constraint in STILL_REFERENCED_MESSAGES:
        return f"Rejected: {STILL_REFERENCED_MESSAGES[constraint]} ({detail})"
    if constraint in CONSTRAINT_MESSAGES:
        return f"Rejected: {CONSTRAINT_MESSAGES[constraint]}"
    if code == "22001":                                     # string longer than its varchar(n)
        return f"Rejected: a value is too long ({primary})."
    # Anything else: show what PostgreSQL said, so nothing fails silently.
    return f"Rejected by the database: {primary}" + (f" ({detail})" if detail else "")


# ---------- form parsing helpers (raise CheckFailed with a clear message) ----------
def req_text(value, label):
    value = (value or "").strip()
    if not value:
        raise CheckFailed(f"{label} is required.")
    return value


def opt_text(value):
    value = (value or "").strip()
    return value or None


def req_int(value, label):
    value = req_text(value, label)
    try:
        return int(value)
    except ValueError:
        raise CheckFailed(f"{label} must be a whole number.")


def opt_int(value, label):
    if not (value or "").strip():
        return None
    return req_int(value, label)


def next_id(conn, table, column):
    """The primary keys in sql1.sql are plain int (no SERIAL), so new rows get MAX + 1.
    Runs inside the caller's transaction. Fine for this single-user demo app; a real
    multi-user app would use a sequence/IDENTITY column instead.
    table/column are always constants from our code, never user input."""
    return conn.execute(text(f"SELECT COALESCE(MAX({column}), 0) + 1 FROM {table}")).scalar()
