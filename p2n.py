from database import engine
from sqlalchemy import text

#Part 2, task 6: complex queries
#database.py rebuilds the empty tables when it is imported (runs sql1.sql),
#then the seed data is inserted, so these queries always run on the original data.
#echo=True in database.py 

with engine.connect() as conn:
    with open("dummy_data.sql") as file:
        conn.execute(text(file.read()))
    conn.commit()

#6a 
q_tracks = text("""
    SELECT t.track_id, t.track_name, t.conference_id,
           COUNT(DISTINCT p.paper_id) AS papers,
           COUNT(DISTINCT pa.author_id) AS authors
    FROM TRACK t
    LEFT JOIN PAPER p ON p.track_id = t.track_id
    LEFT JOIN PAPER_AUTHOR pa ON pa.paper_id = p.paper_id
    GROUP BY t.track_id, t.track_name, t.conference_id
    ORDER BY t.track_id
""")

#6b
q_reviewers = text("""
    SELECT r.reviewer_id, u.given_name || ' ' || u.surname AS full_name,
           COUNT(rv.review_id) AS review_count,
           AVG(rv.overall_score) AS avg_score
    FROM REVIEWER r
    INNER JOIN APP_USER u ON u.user_id = r.reviewer_id
    LEFT JOIN REVIEW rv ON rv.reviewer_id = r.reviewer_id
    GROUP BY r.reviewer_id, u.given_name, u.surname
    ORDER BY r.reviewer_id
""")

#6c
q_conferences = text("""
    SELECT c.conference_id, c.acronym,
           COUNT(DISTINCT p.paper_id) AS total_papers,
           COUNT(DISTINCT p.paper_id) FILTER (WHERE p.status = 'accepted') AS accepted_papers,
           AVG(rv.overall_score) AS avg_score
    FROM CONFERENCE c
    LEFT JOIN TRACK t ON t.conference_id = c.conference_id
    LEFT JOIN PAPER p ON p.track_id = t.track_id
    LEFT JOIN REVIEW rv ON rv.paper_id = p.paper_id
    GROUP BY c.conference_id, c.acronym
    ORDER BY c.conference_id
""")

#6d
q_above_average = text("""
    WITH reviewer_stats AS (
        SELECT r.reviewer_id, u.given_name || ' ' || u.surname AS full_name,
               COUNT(rv.review_id) AS review_count
        FROM REVIEWER r
        INNER JOIN APP_USER u ON u.user_id = r.reviewer_id
        LEFT JOIN REVIEW rv ON rv.reviewer_id = r.reviewer_id
        GROUP BY r.reviewer_id, u.given_name, u.surname
    )
    SELECT reviewer_id, full_name, review_count,
           (SELECT AVG(review_count) FROM reviewer_stats) AS avg_reviews_per_reviewer
    FROM reviewer_stats
    WHERE review_count > (SELECT AVG(review_count) FROM reviewer_stats)
    ORDER BY reviewer_id
""")

with engine.connect() as conn:
    print("6a Tracks with number of distinct papers and distinct authors:")
    for row in conn.execute(q_tracks):
        print(f"track_id: {row.track_id} name: {row.track_name} conference_id: {row.conference_id} "
              f"papers: {row.papers} authors: {row.authors}")

    print("6b Reviewers with number of completed reviews and average score:")
    for row in conn.execute(q_reviewers):
        print(f"reviewer_id: {row.reviewer_id} name: {row.full_name} reviews: {row.review_count} "
              f"average score: {row.avg_score}")

    print("6c Conferences with total papers, accepted papers and average review score:")
    for row in conn.execute(q_conferences):
        print(f"conference_id: {row.conference_id} acronym: {row.acronym} papers: {row.total_papers} "
              f"accepted: {row.accepted_papers} average score: {row.avg_score}")

    print("6d Reviewers with more reviews than the average reviewer:")
    for row in conn.execute(q_above_average):
        print(f"reviewer_id: {row.reviewer_id} name: {row.full_name} reviews: {row.review_count} "
              f"average reviews per reviewer: {row.avg_reviews_per_reviewer}")