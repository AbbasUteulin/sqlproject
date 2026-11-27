# sqlproject
An sql project repository containing all parts from the ASSIGNMENT 3 of CSCI-341.

## Software Versions
The project was developed and tested with the following software versions. 

| Component | Version Used | Verification Command |
| :--- | :--- | :--- |
| **Python** | 3.14.7 | `python --version` |
| **PostgreSQL** | 18.7 | `psql -h localhost -p 5431 -U postgres -c "SHOW server_version;"` |
| **Flask** | 3.1.3 | `python -c "import importlib.metadata; print(importlib.metadata.version('flask'))"` |
| **SQLAlchemy** | 2.0.45 | `python -c "import sqlalchemy; print(sqlalchemy.__version__)"` |
| **psycopg2-binary** | 2.9.13 | `python -m pip show psycopg2-binary` |
| **python-dotenv** | 1.2.1 | `python -c "import importlib.metadata; print(importlib.metadata.version('python-dotenv'))"` |


## How to Run the SQL Queries (Part 2)
Run from the repository root with PostgreSQL running and `database.py` pointing at it:
 
```
python p2.py      # tasks 1-5, 7, 8
python p2n.py     # task 6
```
 
Every run first rebuilds the schema (import of `database.py`) and loads `dummy_data.sql`, so each program starts from the original seed data. `database.py` sets `echo=True`, so SQLAlchemy prints every SQL statement (including the schema and the seed file) before the results. Task labels are in the printed headings.

## How to Run the Application (Part 3)
```
pip install -r app/requirements.txt
# set the connection (see 3.1), for example in PowerShell:
$env:DATABASE_URL = "postgresql://postgres:mysecretpassword@localhost:5431/postgres"
python app/resetdb.py     # once: schema + seed data (erases existing data)
python app/app.py         # Flask development server, debug mode: http://127.0.0.1:5000
```
 
The web app only connects (`app/db.py`); it never rebuilds the database. Restarting it keeps your data. Stop it with `Ctrl+C`.


## Database Schema and Keys 
Types: integer keys, `varchar(n)`/`text` for text, `timestamptz` for conference dates, deadlines, submission, upload and review dates; `date`/`time` for sessions. `PAPER.session_id` is NULL when the paper is not scheduled. "No action" below means the default `NO ACTION` (the delete is rejected while referenced).
 
| Table | Primary key | Foreign keys (delete action) | Notes |
|---|---|---|---|
| `APP_USER` | `user_id` | | `email` UNIQUE NOT NULL |
| `AUTHOR` | `author_id` | `author_id` → `APP_USER` (CASCADE) | `orcid` optional, UNIQUE |
| `AUTHOR_RESEARCH_AREA` | `(author_id, area_label)` | → `AUTHOR` (CASCADE) | multivalued attribute |
| `REVIEWER` | `reviewer_id` | → `APP_USER` (CASCADE) | `years_exp` CHECK >= 0 |
| `REVIEWER_EXPERTISE` | `(reviewer_id, area_label)` | → `REVIEWER` (CASCADE) | multivalued attribute |
| `CONFERENCE` | `conference_id` | | CHECK end_date >= start_date; CHECK submission_deadline <= review_deadline |
| `CONFERENCE_HOST` | `(conference_id, host_name)` | → `CONFERENCE` (CASCADE) | |
| `CONFERENCE_REVIEWER` | `(conference_id, reviewer_id)` | → `CONFERENCE` (CASCADE); → `REVIEWER` (no action) | the conference's reviewer pool |
| `TRACK` | `track_id` | `conference_id` → `CONFERENCE` (CASCADE); `coordinator_id` → `REVIEWER` (no action); `(conference_id, coordinator_id)` → `CONFERENCE_REVIEWER` (no action) | the composite key forces the coordinator into the conference's pool |
| `CONFERENCE_SESSION` | `session_id` | `conference_id` → `CONFERENCE` (CASCADE); `chair_id` → `REVIEWER` (no action); `(conference_id, chair_id)` → `CONFERENCE_REVIEWER` (no action) | CHECK end_time > start_time; chair must be in the pool |
| `PAPER` | `paper_id` | `track_id` → `TRACK` (no action); `session_id` → `CONFERENCE_SESSION` (SET NULL) | CHECK status in (submitted, under review, accepted, rejected, withdrawn); CHECK `scheduled_only_if_accepted` |
| `PAPER_KEYWORD` | `(paper_id, keyword)` | → `PAPER` (CASCADE) | |
| `PAPER_AUTHOR` | `(paper_id, author_id)` | → `PAPER` (CASCADE); `author_id` → `AUTHOR` (no action) | `UNIQUE (paper_id, author_position)`, CHECK position > 0, `is_corresponding`; partial unique index `one_corresponding_per_paper` |
| `PAPER_VERSION` | `(paper_id, version_no)` | → `PAPER` (CASCADE) | CHECK version_no > 0; `uploaded_at` default `now()`; gaps allowed, highest number = current version |
| `REVIEW` | `review_id` | → `PAPER` (CASCADE); `reviewer_id` → `REVIEWER` (no action) | `UNIQUE (paper_id, reviewer_id)`; CHECK score 1-5; CHECK recommendation in (accept, reject); all fields except `confidential_comments` NOT NULL (completed reviews only); trigger `self_review_trigger` |
 
**Deletion actions:** deleting a paper removes its authorship, keywords, versions and reviews; deleting a session unschedules its papers; deleting a conference removes its hosts, pool, tracks and sessions (cascade) but is rejected while a track still has papers (`PAPER.track_id`); users/reviewers are never deleted by a conference delete; deleting a user removes the author/reviewer profile rows but is rejected while the user authors a paper, wrote a review, is in a pool, coordinates a track or chairs a session. Foreign keys are never disabled. The web app has no conference delete, so the conference rule follows from the foreign-key definitions only.


## Required Checks and Validation
 
### Required database constraints (enforced by `sql1.sql`) 
| Requirement | Mechanism | How to check it manually (psql, run inside `BEGIN; ... ROLLBACK;`) | Expected result |
|---|---|---|---|
| Unique author position within a paper | `UNIQUE (paper_id, author_position)` | `INSERT INTO PAPER_AUTHOR VALUES (1, 4, 1, false);` | duplicate key `paper_author_unique` |
| Positive author position | CHECK `positive_author_pos` | `INSERT INTO PAPER_AUTHOR VALUES (1, 4, 0, false);` | check violation |
| Score 1-5 | CHECK `one_to_five` | insert a `REVIEW` with `overall_score = 6` | check violation |
| Paper must be accepted to be scheduled | CHECK `scheduled_only_if_accepted` | `UPDATE PAPER SET session_id = 1 WHERE paper_id = 6;` | check violation |
| Chair/coordinator in the conference's pool | composite foreign keys | insert a `CONFERENCE_SESSION` for conference 1 with `chair_id = 9` | foreign-key violation `conference_session_conference_id_chair_id_fkey` |
| Delete a paper cascades | `ON DELETE CASCADE` | `DELETE FROM PAPER WHERE paper_id = 1;` then count versions and reviews of paper 1 | 0 and 0 |
 
Other required constraints (keys, NOT NULL, unique email, one review per reviewer and paper, status/recommendation checks, experience >= 0, conference and session time checks, positive version numbers) are defined in `sql1.sql`. They are exercised only indirectly (through the web forms and error translation); **no automated test for them is in the repository.**
 
### Required application checks (Part 1)
| Check | Implemented in | Rejected case | Expected result |
|---|---|---|---|
| 1. No self-review, when saving a review | `save_review` calls `checks.is_self_review`; the database trigger `self_review_trigger` is a backup | Arman Armanov (author of paper 1) reviews paper 1 | error message, no review stored |
| 1. No self-review, when changing a paper's authors | `save_paper` calls `checks.author_has_reviewed_paper` | add Aliya Nurlanova (reviewer of paper 1) as an author of paper 1 | error message, authorship unchanged |
| 2. Valid session assignment | `save_paper` calls `checks.session_assignment_error` (paper must be accepted; paper's track conference = session's conference), using the paper's new status and track | paper 3 (ADSC) into session 4 (CASEF); paper 6 (under review) into session 1 | error message, whole form rolled back (title change included) |
| 2. Re-check when a session changes | `save_session` calls `checks.scheduled_paper_error` for every paper in the session | move session 1 (holds ADSC paper 1) to CASEF | edit rejected |
 
**How to perform:** automatically with `python app/demo.py` (all cases above print `PASS` and verify the database did not change), or manually in the browser after `python app/resetdb.py`:
 
1. Reviews > New review > paper 1, reviewer Arman Armanov > Save: error, no review added.
2. Papers > 3 > Edit > session "CASEF 2026 / #4 ..." > Save: error that paper and session belong to different conferences.
3. Papers > 6 > Edit > session "ADSC 2026 / #1 ..." > Save: error that only accepted papers can be scheduled.
4. Papers > 3 > Edit > session "ADSC 2026 / #3 Open Problems" > Save: accepted, the paper is shown in session 3.
**Code vs manual:** all four application checks are implemented in code (`app/checks.py`, called from `app/app.py`) and tested by `app/demo.py`. The database-level constraints are checked manually. The database alone does **not** enforce "same conference" (psql: `UPDATE PAPER SET session_id = 4 WHERE paper_id = 2;` succeeds) or the second direction of the self-review rule (inserting a reviewer who already reviewed the paper into `PAPER_AUTHOR` succeeds); those depend on the application checks.

# PART 2

Up until now, the part 1 of the task 2 .py file was using textual sql to execute commands. The documentation states that's not how sqlalchemy is usually operated, so in part 2 of the task 2 I am intending to use the Core way to work with it. The final deployed application may benefit from an ORM approach, but it is yet to be discussed. 

# PART 3
Framework: Flask with SQLAlchemy
Progress:
- [x] Chunk 1: foundation (database connection, Flask setup)
- [x] Chunk 2: read pages for users, papers, reviews and sessions
- [x] Chunk 3: create, update and delete
- [x] Chunk 4: the two application checks (self-review, session assignment) with transactions
- [ ] Chunk 5: deployment (code and instructions ready, see "Deployment" below; tick when the URL is live and in `links.txt`)

## Running it locally
```
pip install -r app/requirements.txt
set DATABASE_URL=postgresql://postgres:mysecretpassword@localhost:5431/postgres   (PowerShell: $env:DATABASE_URL="...")
python app/resetdb.py      # rebuilds the schema (sql1.sql) and the seed data (dummy_data.sql)
python app/app.py          # http://127.0.0.1:5000
python app/demo.py         # scripted demo (see below); it resets the database at the start and at the end
```

## Files
| file | what it does |
|---|---|
| `app/app.py` | every route: list/detail pages and create/edit/delete forms |
| `app/transactions.py` | `run_tx` (one transaction per form), `CheckFailed`, and the translation of PostgreSQL errors into readable messages |
| `app/checks.py` | the two Part 1 application checks |
| `app/lookups.py` | options for the select lists (tracks, sessions, authors, reviewers, chairs, labels) |
| `app/resetdb.py` | rebuilds the database on purpose (the web app never does this) |
| `app/demo.py` | runs every CRUD operation and every required rejection, and checks the database after each one |
| `app/templates/` | plain HTML pages (appearance is not graded) |

## What can be managed
| entity | pages | handled in the same form |
|---|---|---|
| Users | `/users`, `/users/<id>`, `/users/new`, `/users/<id>/edit`, delete button | author profile (ORCID, research areas), reviewer profile (years of experience, expertise) |
| Papers | `/papers`, `/papers/<id>`, `/papers/new`, `/papers/<id>/edit`, delete button | authorship (slot order = position, one corresponding author), keywords, session; versions are added and deleted on the paper page |
| Reviews | `/reviews`, `/reviews/<id>`, `/reviews/new`, `/reviews/<id>/edit`, delete button | – |
| Sessions | `/sessions`, `/sessions/<id>`, `/sessions/new`, `/sessions/<id>/edit`, delete button | the scheduled papers are listed on the session page |

Conferences, tracks, reviewer pools, host institutions and research/expertise labels come from the seed script. They are read-only and are only used as selection lists.

## How transactions and errors work
Each form submission runs **all** of its SQL inside one transaction (`run_tx`, which uses `engine.begin()`).
- If everything succeeds, the transaction is committed and the app redirects to the detail page with a green "success" message.
- If anything fails, the transaction is rolled back and nothing is saved. The same form is shown again with what the user typed (HTTP 400), plus an "error" message that says why.

For example, saving a paper writes the paper row, its authors, its keywords and its session as one unit. If the session assignment is invalid, the title change in the same form is undone as well.

Failures come from two places, and both are reported as plain sentences:
1. **Our own checks** (`CheckFailed`): the two application checks and missing or invalid form fields.
2. **PostgreSQL**: every CHECK / UNIQUE / FOREIGN KEY constraint and the `self_review_trigger` from `sql1.sql`. `describe_db_error` turns the constraint name into a message, for example "the session chair must be in the selected conference's reviewer pool".

Deletes that would leave dangling rows are refused by the foreign keys, for example deleting a user who still authors a paper. Deletes that are meant to remove dependent rows use ON DELETE CASCADE: deleting a paper removes its authorship, keywords, versions and reviews. Deleting a session uses ON DELETE SET NULL, so its papers become unscheduled.

## The two application checks (from Part 1)
| check | where | what is rejected |
|---|---|---|
| 1. No self-review | `save_review` → `checks.is_self_review` | a reviewer who is an author of the paper (the database trigger is the backup) |
| | `save_paper` → `checks.author_has_reviewed_paper` | adding, as an author, someone who already reviewed the paper (the trigger only watches REVIEW, so this direction is checked by the app) |
| 2. Valid session assignment | `save_paper` → `checks.session_assignment_error` | a paper that is not accepted, or whose track belongs to a different conference than the session |
| | `save_session` → `checks.scheduled_paper_error` | editing a session (e.g. moving it to another conference) so that a paper already in it becomes invalid |

## Demo
`python app/demo.py` sends the same POST requests a browser would, through Flask's test client. After every step it queries the database to show the result, printing PASS/FAIL. It covers:
- **Valid CRUD:**
  - **Users:** create a user with both profiles, read, update (and remove the reviewer profile), delete.
  - **Papers:** create a paper with 2 authors, keywords and version 1. Read it, then update it: accept it and schedule it in a session of the same conference. Add v2, delete v1, delete the paper.
  - **Reviews:** create, read, update, delete.
  - **Sessions:** create, read, update. Schedule paper 3 into the new session, then delete the session, which unschedules paper 3.
- **Rejections.** For each one the demo also checks that the database did not change:
  - **Self-review:** Arman Armanov (an author of paper 1) reviews paper 1.
  - **Self-review, other direction:** add Aliya Nurlanova (who reviewed paper 1) as an author of paper 1.
  - **Invalid session assignment:** paper 3 (ADSC) goes into session 4 (CASEF), with a title change in the same form. The title change is rolled back too.
  - **Invalid session assignment:** paper 6 (under review) goes into session 1.
  - **Invalid session edit:** session 1, which holds ADSC paper 1, is moved to CASEF.
  - **Blocked delete:** deleting a user who still authors a paper is refused.

The same scenarios by hand in the browser, after `python app/resetdb.py`:
1. **Self-review:** Reviews → New review → paper #1, reviewer Arman Armanov → Save. An error appears and no review is added.
2. **Invalid session assignment:** Papers → 3 → Edit → Session "CASEF 2026 / #4 ..." → Save. The error says the paper and session belong to different conferences.
3. **Invalid session assignment:** Papers → 6 → Edit → Session "ADSC 2026 / #1 ..." → Save. The error says only accepted papers can be scheduled.
4. **Valid assignment:** Papers → 3 → Edit → Session "ADSC 2026 / #3 Open Problems" → Save. The paper is now shown in session 3.
## Deployment
The app runs on **Render** (free web service) and stores its data in **Neon** (free PostgreSQL). The URL is in `links.txt`.

Why these two:
- **Neon's free storage is persistent and doesn't expire** (1 GB per project). Render's own free PostgreSQL is deleted after 30 days, which could fall in the middle of grading.
- **Render's free web service** sleeps after 15 minutes without traffic and takes about a minute to wake up. An uptime monitor pings `/health` every 5 minutes so it stays awake. `/health` does not query the database, so Neon can still scale to zero when idle and stays well inside its 100 compute-hours a month.

### One-time setup
1. **Neon** (neon.tech): create a project, then copy the **direct** connection string (the host without `-pooler`), e.g. `postgresql://user:pass@ep-xxx.aws.neon.tech/neondb?sslmode=require`.
2. **Seed it once** from your own computer. `resetdb.py` asks you to type `yes` because the host is not local:
   ```powershell
   $env:DATABASE_URL = "<neon connection string>"
   python app/resetdb.py
   ```
3. **Render** (render.com): New → Web Service → this GitHub repo, with these settings:

   | setting | value |
   |---|---|
   | Branch | `main` |
   | Root Directory | `app` |
   | Runtime | Python |
   | Build Command | `pip install -r requirements.txt` |
   | Start Command | `gunicorn app:app` |
   | Instance Type | Free |
   | Environment | `DATABASE_URL` = Neon connection string, `SECRET_KEY` = any long random string, `PYTHON_VERSION` = `3.12.10` |
4. **UptimeRobot** (uptimerobot.com, free): add an HTTP(s) monitor on `https://<service>.onrender.com/health`, checking every 5 minutes, with email alerts on.
5. Put the URL into `links.txt`.

The Part 2 programs (`p2.py`, `p2n.py`) stay separate and still run locally against Docker.

### Keeping it available during grading
- **Don't erase the live data.**
  - `demo.py` refuses to run against a non-local database.
  - Run `resetdb.py` against Neon only before grading starts, or if the data is badly broken. It wipes the graders' changes.
- **Don't break the deploy.**
  - Render redeploys on every push to `main`, so only merge tested changes during grading, or turn off Auto-Deploy in the Render settings.
  - After a deploy, check Render → Logs and open the site.
- **Watch the free limits.**
  - Render's 750 free hours a month are shared by all free services in the same Render workspace, and one service running 24/7 needs about 744. Don't run other free services in that workspace.
  - Neon: glance at the Usage page now and then.
- **If it goes down:**
  - UptimeRobot emails you.
  - Check Render → Logs, then Manual Deploy → Restart service.
  - Check Neon's dashboard, in case compute was suspended.
  - If the monitor missed a ping, the first request after a sleep takes about a minute.
- **Before grading:** open the URL in a private window, click through users, papers, reviews and sessions, and check that `/health` shows `ok`.
