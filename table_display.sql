SELECT 'app_user' table_names, COUNT(*) AS row_count FROM APP_USER
UNION
SELECT 'author', COUNT(*) from AUTHOR
UNION
SELECT 'author_research', COUNT(*) from AUTHOR_RESEARCH_AREA
UNION
SELECT 'conference', COUNT(*) from CONFERENCE
UNION
SELECT 'conference_host', COUNT(*) from CONFERENCE_HOST
UNION
SELECT 'conference_reviewer', COUNT(*) from CONFERENCE_REVIEWER
UNION
SELECT 'conference_session', COUNT(*) from CONFERENCE_SESSION
UNION
SELECT 'paper', COUNT(*) from PAPER
UNION
SELECT 'paper_author', COUNT(*) from PAPER_AUTHOR
UNION
SELECT 'paper_KEYWORD', COUNT(*) from PAPER_KEYWORD
UNION
SELECT 'paper_version', COUNT(*) from PAPER_VERSION
UNION
SELECT 'review', COUNT(*) from REVIEW
UNION
SELECT 'reviewer_expertise', COUNT(*) from REVIEWER_EXPERTISE
UNION
SELECT 'track', COUNT(*) from TRACK;