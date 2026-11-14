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
for row in result:
    print(f"table_name: {row.table_names} count: {row.row_count}")

