# Options for the <select> lists and checkboxes in the forms (chunk 3).
# Conferences, tracks, reviewer pools and research/expertise labels come from the seed script
# and are used read-only here, as the assignment allows.
from sqlalchemy import text
from db import engine


def _options(sql):
    """SELECT id, label -> list of (id, label) tuples."""
    with engine.connect() as conn:
        return [(row[0], row[1]) for row in conn.execute(text(sql))]


def conference_options():
    return _options("SELECT conference_id, acronym FROM CONFERENCE ORDER BY conference_id")


def track_options():
    return _options("""SELECT t.track_id, c.acronym || ' / ' || t.track_name
                       FROM TRACK t INNER JOIN CONFERENCE c ON c.conference_id = t.conference_id
                       ORDER BY t.track_id""")


def reviewer_options():
    return _options("""SELECT r.reviewer_id, u.given_name || ' ' || u.surname
                       FROM REVIEWER r INNER JOIN APP_USER u ON u.user_id = r.reviewer_id
                       ORDER BY r.reviewer_id""")


def author_options():
    return _options("""SELECT a.author_id, u.given_name || ' ' || u.surname
                       FROM AUTHOR a INNER JOIN APP_USER u ON u.user_id = a.author_id
                       ORDER BY a.author_id""")


def chair_options():
    """Reviewers, labelled with the conference pools they belong to, so it is visible
    which chairs are valid for which conference (the composite foreign key enforces it)."""
    return _options("""SELECT r.reviewer_id,
                              u.given_name || ' ' || u.surname ||
                              COALESCE(' (pool: ' || string_agg(c.acronym, ', ' ORDER BY c.conference_id) || ')',
                                       ' (in no pool)')
                       FROM REVIEWER r
                       INNER JOIN APP_USER u ON u.user_id = r.reviewer_id
                       LEFT JOIN CONFERENCE_REVIEWER cr ON cr.reviewer_id = r.reviewer_id
                       LEFT JOIN CONFERENCE c ON c.conference_id = cr.conference_id
                       GROUP BY r.reviewer_id, u.given_name, u.surname
                       ORDER BY r.reviewer_id""")


def paper_options():
    return _options("""SELECT p.paper_id, '#' || p.paper_id || ' ' || p.title || ' [' || c.acronym || ', ' || p.status || ']'
                       FROM PAPER p
                       INNER JOIN TRACK t ON t.track_id = p.track_id
                       INNER JOIN CONFERENCE c ON c.conference_id = t.conference_id
                       ORDER BY p.paper_id""")


def session_options():
    return _options("""SELECT s.session_id,
                              c.acronym || ' / #' || s.session_id || ' ' || s.title ||
                              ' (' || s.session_date || ' ' || to_char(s.start_time, 'HH24:MI') || ')'
                       FROM CONFERENCE_SESSION s
                       INNER JOIN CONFERENCE c ON c.conference_id = s.conference_id
                       ORDER BY s.session_id""")


def label_options():
    """Every research/expertise label already in the seed data (no separate label table exists)."""
    with engine.connect() as conn:
        return [row[0] for row in conn.execute(text("""
            SELECT area_label FROM AUTHOR_RESEARCH_AREA
            UNION SELECT area_label FROM REVIEWER_EXPERTISE
            UNION SELECT research_area FROM TRACK
            ORDER BY 1"""))]
