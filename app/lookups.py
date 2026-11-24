# for chunk 3
from sqlalchemy import text
from db import engine


def _options(sql):
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