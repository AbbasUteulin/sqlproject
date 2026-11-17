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

email_amina = "amina.aminova@example.com"

with engine.connect() as conn:
    conn.execute(text("DELETE FROM PAPER p WHERE p.status = 'withdrawn' AND p.paper_id IN (SELECT pa.paper_id FROM PAPER_AUTHOR pa WHERE pa.author_id = (SELECT a.author_id FROM AUTHOR a WHERE author_id = (SELECT user_id FROM APP_USER WHERE email = :email)))"),  {"email" : email_amina})
    result = conn.execute(text("SELECT u.email, p.status, pa.paper_id, pk.keyword, pv.version_no FROM PAPER p INNER JOIN PAPER_AUTHOR pa ON p.paper_id = pa.paper_id INNER JOIN PAPER_KEYWORD pk ON p.paper_id = pk.paper_id INNER JOIN PAPER_VERSION pv ON P.paper_id = pv.paper_id INNER JOIN AUTHOR a ON pa.author_id = a.author_id INNER JOIN APP_USER u ON a.author_id = u.user_id AND email = :email"), {"email" : email_amina})
    conn.commit()
    print("Displaying all the remaining papers from Amina:")
    for row in result:
        print(row)