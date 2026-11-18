from database import engine
from sqlalchemy import create_engine, text

#Part 2
#Inserts the seed data using the dummy_data sql file.
#If you wish to restoore this data set, execute the code cluster below
#table display uses sql statement and unions to display rows and tables.

with engine.connect() as conn:
    with open("dummy_data.sql") as file:
        query = text(file.read())
        conn.execute(query)
    with open("table_display.sql") as file_2:
        query_for_row_display = text(file_2.read())
        result = conn.execute(query_for_row_display)
    conn.commit()

#display the result
print("Second part of task 2: displaying row count of every table")
for row in result:
    print(f"table_name: {row.table_names} count: {row.row_count}")


#part 3: Update statements
#Bound parameters used
#Textual sql
email = "arman.armanov@example.com"
city = "Astana"
with engine.connect() as conn:
    conn.execute(text("UPDATE APP_USER SET phone_number = '+77773414141' WHERE email = :email"), {"email": email})
    conn.execute(text("UPDATE CONFERENCE  SET review_deadline =  CASE WHEN city = :city THEN review_deadline + interval '7 days' ELSE review_deadline + interval '3 days' END"), {"city": city})
    conn.commit()
    phone_upd = conn.execute(text("SELECT * FROM APP_USER WHERE email = :email"), {"email": email})
    print("Displaying updated phone number with corresponding email: ")
    row = phone_upd.fetchone()
    print(f"email: {row.email} phone number: {row.phone_number}")
    con_upd = conn.execute(text("SELECT * FROM CONFERENCE"))
    print("Displaying updated conferences: ")
    for row in con_upd:
        print(f"city: {row.city}  review deadline: {row.review_deadline}")

#part 4: Delete statements
#Bound parameters used
#Textual sql
#We will demonstarate all of Amina's papers after deletion.
#DELETEION is performed via nesting WHERE clauses
#Retival is performed via JOIN clauses and is allowed to repeat
#You could also execute * sql statements to confirm that every paper was deleted ON CASCADE
#Deletes empty sessions (which no paper belongs to) specifically in Astana
#since some of our rows in PAPER with can be NULL, we use NOT NULL clause specifically to prevent NOT IN generating 0 rows.

email_amina = "amina.aminova@example.com"

del_empty_sessions = text("DELETE FROM CONFERENCE_SESSION WHERE session_id NOT IN(SELECT session_id FROM PAPER WHERE session_id IS NOT NULL) AND conference_id IN (SELECT conference_id FROM CONFERENCE WHERE city = 'Astana')")

with engine.connect() as conn:
    conn.execute(text("DELETE FROM PAPER p WHERE p.status = 'withdrawn' AND p.paper_id IN (SELECT pa.paper_id FROM PAPER_AUTHOR pa WHERE pa.author_id = (SELECT a.author_id FROM AUTHOR a WHERE author_id = (SELECT user_id FROM APP_USER WHERE email = :email)))"),  {"email" : email_amina})
    result = conn.execute(text("SELECT u.email, p.status, pa.paper_id, pk.keyword, pv.version_no FROM PAPER p INNER JOIN PAPER_AUTHOR pa ON p.paper_id = pa.paper_id INNER JOIN PAPER_KEYWORD pk ON p.paper_id = pk.paper_id INNER JOIN PAPER_VERSION pv ON P.paper_id = pv.paper_id INNER JOIN AUTHOR a ON pa.author_id = a.author_id INNER JOIN APP_USER u ON a.author_id = u.user_id AND email = :email"), {"email" : email_amina})
    print("Displaying all the remaining papers from Amina:")
    for row in result:
        print(row)
    conn.execute(del_empty_sessions)
    conn.commit()

#part 5: Simple queries
#Bound parameters used
#Textual sql
#Each query is a plain SELECT, so nothing is committed here.

#5.1 Accepted papers with their corresponding author, track and conference.
#PAPER -> TRACK -> CONFERENCE gives the track name and conference ID/acronym.
#PAPER_AUTHOR filtered by is_corresponding = true picks the corresponding author;
#the unique index one_corresponding_per_paper guarantees at most one per paper, so we get one row per paper.
#LEFT JOINs on the author side keep an accepted paper even if no corresponding author is set (author columns are then NULL).
#The full name is built by joining given_name and surname with a space.
q_accepted_papers = text("""
    SELECT p.paper_id, p.title,
           u.given_name || ' ' || u.surname AS corresponding_author, u.email,
           t.track_name, c.conference_id, c.acronym
    FROM PAPER p
    INNER JOIN TRACK t ON p.track_id = t.track_id
    INNER JOIN CONFERENCE c ON t.conference_id = c.conference_id
    LEFT JOIN PAPER_AUTHOR pa ON pa.paper_id = p.paper_id AND pa.is_corresponding = true
    LEFT JOIN APP_USER u ON u.user_id = pa.author_id
    WHERE p.status = :status
    ORDER BY p.paper_id
""")

#5.2 Papers whose abstract contains a phrase, case-insensitive.
#ILIKE is PostgreSQL's case-insensitive LIKE; the % wildcards on both sides match the phrase anywhere in the abstract.
#The wildcards are added in Python so the phrase itself stays a bound parameter.
q_abstract_phrase = text("""
    SELECT paper_id, title
    FROM PAPER
    WHERE abstract ILIKE :pattern
    ORDER BY paper_id
""")

#5.3 All versions of a selected paper, newest version first.
#PAPER_VERSION already holds everything we need, so no joins are required.
#ORDER BY version_no DESC lists the highest version number first.
q_paper_versions = text("""
    SELECT version_no, file_location, uploaded_at
    FROM PAPER_VERSION
    WHERE paper_id = :paper_id
    ORDER BY version_no DESC
""")

#5.4 Reviewers in a selected conference's pool with a given expertise and enough experience.
#CONFERENCE_REVIEWER is the conference's reviewer pool; REVIEWER gives years_exp; APP_USER gives name and email.
#Expertise is checked with EXISTS instead of a join, so a reviewer with several matching rows is still returned only once.
#(CONFERENCE_REVIEWER's primary key (conference_id, reviewer_id) already prevents duplicates from the pool side.)
q_conf_reviewers = text("""
    SELECT r.reviewer_id, u.given_name || ' ' || u.surname AS full_name, u.email
    FROM CONFERENCE_REVIEWER cr
    INNER JOIN REVIEWER r ON cr.reviewer_id = r.reviewer_id
    INNER JOIN APP_USER u ON r.reviewer_id = u.user_id
    WHERE cr.conference_id = :conference_id
      AND r.years_exp >= :min_years
      AND EXISTS (SELECT 1 FROM REVIEWER_EXPERTISE re
                  WHERE re.reviewer_id = r.reviewer_id AND re.area_label = :area)
    ORDER BY r.reviewer_id
""")

#Parameters for the "selected" values; change these to query a different paper/conference.
selected_paper_id = 1
selected_conference_id = 1

with engine.connect() as conn:
    print("5.1 Accepted papers with corresponding author, track and conference:")
    for row in conn.execute(q_accepted_papers, {"status": "accepted"}):
        print(f"paper_id: {row.paper_id} title: {row.title} author: {row.corresponding_author} email: {row.email} "
              f"track: {row.track_name} conference_id: {row.conference_id} acronym: {row.acronym}")

    print("5.2 Papers whose abstract mentions 'machine learning':")
    for row in conn.execute(q_abstract_phrase, {"pattern": "%machine learning%"}):
        print(f"paper_id: {row.paper_id} title: {row.title}")

    print(f"5.3 Versions of paper {selected_paper_id} (newest first):")
    for row in conn.execute(q_paper_versions, {"paper_id": selected_paper_id}):
        print(f"version: {row.version_no} file: {row.file_location} uploaded_at: {row.uploaded_at}")

    print(f"5.4 Reviewers in conference {selected_conference_id}'s pool with Databases expertise and 3+ years of experience:")
    for row in conn.execute(q_conf_reviewers, {"conference_id": selected_conference_id, "min_years": 3, "area": "Databases"}):
        print(f"reviewer_id: {row.reviewer_id} name: {row.full_name} email: {row.email}")
