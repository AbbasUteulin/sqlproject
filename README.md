# sqlproject
An sql project repository containing all parts from the ASSIGNMENT 3 of CSCI-341.

# PART 2

Up until now, the part 1 of the task 2 .py file was using textual sql to execute commands. The documentation states that's not how sqlalchemy is usually operated, so in part 2 of the task 2 I am intending to use the Core way to work with it. The final deployed application may benefit from an ORM approach, but it is yet to be discussed. 

# PART 3
Framework: Flask with SQLAlchemy
Progress:
- [x] Chunk 1: foundation (database connection, Flask setup)
- [x] Chunk 2: read pages for users, papers, reviews and sessions
- [x] Chunk 3: create, update and delete
- [x] Chunk 4: the two application checks (self-review, session assignment) with transactions
- [ ] Chunk 5: deployment, links.txt (the local demo is done: `app/demo.py`)

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