from database import engine
from sqlalchemy import create_engine, text

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
    

