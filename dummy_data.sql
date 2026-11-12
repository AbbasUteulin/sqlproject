-- Dummy data for the schema in sql1.sql.
-- Run sql1.sql first, then this file. All people and organisations are fictional.
--
-- Coverage map (verified by tests.sql):
--   Users 1-12. Author-only: 2,3,4,10. Reviewer-only: 6,7,8,11. Both roles: 1,5,9,12.
--   Arman Armanov (user 1) is an author and a reviewer.
--   Amina Aminova (user 2) is an author; corresponding author of withdrawn papers 9 and 10.
--   Conferences: 1 = Astana, 2 = Almaty, 3 = Tashkent (no papers).
--   Empty tracks: 3 (Astana) and 6 (Tashkent).
--   Empty session: 3, in the Astana conference.
--   Statuses: accepted 1,2,3,4 | rejected 5 | under review 6,7 | submitted 8 | withdrawn 9,10.
--   Accepted with a session: 1,2,4. Accepted without a session: 3.
--   Reviews per paper: P1=3, P2=2, P3=1, P4=2, P5=3, P6=2, P7=2, P8/P9/P10=0.
--   Reviews per reviewer: R6=3, R7=3, R1=2, R9=2, R11=2, R12=2, R5=1, R8=0 (no reviews).
--   Under-review papers for a two-branch status update: P6 avg 4.5 (accept), P7 avg 1.5 (reject).

BEGIN;

INSERT INTO APP_USER (user_id, given_name, surname, email, affiliation, country, phone_number) VALUES
	(1,  'Arman',     'Armanov',    'arman.armanov@example.com',     'Steppe Institute of Tech',  'Kazakhstan', '+77011000001'),
	(2,  'Amina',     'Aminova',    'amina.aminova@example.com',     'Steppe Institute of Tech',  'Kazakhstan', '+77011000002'),
	(3,  'Dana',      'Bekova',     'dana.bekova@example.com',       'Altai State University',    'Kazakhstan', '+77011000003'),
	(4,  'Timur',     'Sadykov',    'timur.sadykov@example.com',     'Caspian Polytechnic',       'Kazakhstan', '+77011000004'),
	(5,  'Aliya',     'Nurlanova',  'aliya.nurlanova@example.com',   'Altai State University',    'Kazakhstan', '+77011000005'),
	(6,  'Yerlan',    'Kassymov',   'yerlan.kassymov@example.com',   'Caspian Polytechnic',       'Kazakhstan', '+77011000006'),
	(7,  'Saule',     'Omarova',    'saule.omarova@example.com',     'Silk Road University',      'Uzbekistan', '+998901000007'),
	(8,  'Daniyar',   'Zhakupov',   'daniyar.zhakupov@example.com',  'Steppe Institute of Tech',  'Kazakhstan', '+77011000008'),
	(9,  'Madina',    'Ospanova',   'madina.ospanova@example.com',   'Tien Shan Tech Academy',    'Kyrgyzstan', '+996551000009'),
	(10, 'Bauyrzhan', 'Seitkali',   'bauyrzhan.seitkali@example.com','Caspian Polytechnic',       'Kazakhstan', '+77011000010'),
	(11, 'Elena',     'Petrenko',   'elena.petrenko@example.com',    'Silk Road University',      'Uzbekistan', '+998901000011'),
	(12, 'Kairat',    'Mukhametov', 'kairat.mukhametov@example.com', 'Tien Shan Tech Academy',    'Kyrgyzstan', '+996551000012');

-- ORCIDs are stored without dashes because AUTHOR.orcid is varchar(16).
INSERT INTO AUTHOR (author_id, orcid) VALUES
	(1,  '0000000100000001'),
	(2,  '0000000100000002'),
	(3,  '0000000100000003'),
	(4,  '0000000100000004'),
	(5,  '0000000100000005'),
	(9,  '0000000100000009'),
	(10, NULL),
	(12, '0000000100000012');

INSERT INTO AUTHOR_RESEARCH_AREA (author_id, area_label) VALUES
	(1,  'Data Management'),
	(1,  'Machine Learning'),
	(2,  'Data Management'),
	(2,  'Software Engineering'),
	(3,  'Data Management'),
	(3,  'HCI'),
	(4,  'Distributed Systems'),
	(5,  'Machine Learning'),
	(9,  'Software Engineering'),
	(10, 'HCI'),
	(12, 'Software Engineering');

INSERT INTO REVIEWER (reviewer_id, years_exp) VALUES
	(1,  6),
	(5,  4),
	(6,  12),
	(7,  9),
	(8,  0),
	(9,  7),
	(11, 15),
	(12, 3);

INSERT INTO REVIEWER_EXPERTISE (reviewer_id, area_label) VALUES
	(1,  'Data Management'),
	(5,  'Machine Learning'),
	(6,  'Data Management'),
	(6,  'Machine Learning'),
	(7,  'Security'),
	(7,  'Machine Learning'),
	(8,  'Security'),
	(9,  'Software Engineering'),
	(11, 'HCI'),
	(11, 'Software Engineering'),
	(12, 'Software Engineering');

INSERT INTO CONFERENCE (conference_id, conference_name, acronym, description, city, country,
                        start_date, end_date, submission_deadline, review_deadline) VALUES
	(1, 'Astana Data Systems Conference', 'ADSC 2026',
	    'Data management, ML systems and privacy.', 'Astana', 'Kazakhstan',
	    '2026-06-15 09:00+05', '2026-06-17 18:00+05', '2026-03-01 23:59+05', '2026-04-15 23:59+05'),
	(2, 'Central Asia Software Engineering Forum', 'CASEF 2026',
	    'Software testing, tooling and human factors.', 'Almaty', 'Kazakhstan',
	    '2026-09-10 09:00+05', '2026-09-12 18:00+05', '2026-05-01 23:59+05', '2026-06-15 23:59+05'),
	(3, 'Silk Road AI Symposium', 'SRAIS 2027',
	    'Foundation models and applied AI.', 'Tashkent', 'Uzbekistan',
	    '2027-04-20 09:00+05', '2027-04-21 18:00+05', '2027-01-15 23:59+05', '2027-02-28 23:59+05');

INSERT INTO CONFERENCE_HOST (conference_id, host_name) VALUES
	(1, 'Steppe Institute of Tech'),
	(1, 'Astana Data Society'),
	(2, 'Almaty Software Guild'),
	(3, 'Silk Road AI Council');

INSERT INTO CONFERENCE_REVIEWER (conference_id, reviewer_id) VALUES
	(1, 1), (1, 5), (1, 6), (1, 7), (1, 8),
	(2, 1), (2, 6), (2, 9), (2, 11), (2, 12),
	(3, 7), (3, 11);

INSERT INTO TRACK (track_id, conference_id, track_name, description, research_area, coordinator_id) VALUES
	(1, 1, 'Databases',                'Storage, indexing and query processing.', 'Data Management',      5),
	(2, 1, 'Machine Learning Systems', 'Systems for training and serving models.', 'Machine Learning',    6),
	(3, 1, 'Data Privacy',             'Privacy-preserving data processing.',     'Security',             7),
	(4, 2, 'Software Testing',         'Test generation, flakiness, mutation.',   'Software Engineering', 9),
	(5, 2, 'Human Factors',            'Developer and end-user experience.',      'HCI',                 11),
	(6, 3, 'Foundation Models',        'Training and evaluating large models.',   'Machine Learning',     7);

INSERT INTO CONFERENCE_SESSION (session_id, conference_id, title, session_date, start_time, end_time, room_label, chair_id) VALUES
	(1, 1, 'Query Processing',    '2026-06-15', '10:00', '12:00', 'A-101',  5),
	(2, 1, 'Learning Systems',    '2026-06-16', '14:00', '16:00', 'B-204',  6),
	(3, 1, 'Open Problems',       '2026-06-17', '09:00', '10:30', 'C-310',  1),
	(4, 2, 'Testing in Practice', '2026-09-11', '10:00', '12:00', 'Hall 2', 9);

INSERT INTO PAPER (paper_id, track_id, title, abstract, submission_date, status, session_id) VALUES
	(1,  1, 'Adaptive Indexing for Streaming Workloads',
	        'Indexes that reorganise themselves as streaming queries arrive.',      '2026-02-10 12:00+05', 'accepted',     1),
	(2,  2, 'Federated Learning on Edge Clusters',
	        'Scheduling federated training rounds on heterogeneous edge nodes.',    '2026-02-18 09:30+05', 'accepted',     2),
	(3,  1, 'Cost Models for Hybrid Storage',
	        'Predicting query cost across SSD and object storage tiers.',           '2026-02-25 16:45+05', 'accepted',     NULL),
	(4,  4, 'Mutation Testing at Scale',
	        'Running mutation analysis over a monorepo with incremental builds.',   '2026-04-12 11:00+05', 'accepted',     4),
	(5,  4, 'Flaky Test Detection with Graphs',
	        'Detecting flaky tests from co-failure graphs.',                        '2026-04-20 10:15+05', 'rejected',     NULL),
	(6,  2, 'Explainable Anomaly Detection',
	        'Attributing anomaly scores to input features in telemetry streams.',   '2026-02-27 20:00+05', 'under review', NULL),
	(7,  5, 'Usability of Low-Code Tools',
	        'A study of how analysts build workflows in low-code environments.',    '2026-04-28 14:20+05', 'under review', NULL),
	(8,  5, 'Accessible Dashboards for Analysts',
	        'Design guidelines for screen-reader friendly dashboards.',             '2026-04-30 08:00+05', 'submitted',    NULL),
	(9,  1, 'Query Caching Revisited',
	        'Revisiting result caching for analytical workloads.',                  '2026-02-05 13:00+05', 'withdrawn',    NULL),
	(10, 4, 'Lightweight Contract Checking',
	        'Runtime contract checks with negligible overhead.',                    '2026-04-15 17:40+05', 'withdrawn',    NULL);

INSERT INTO PAPER_KEYWORD (paper_id, keyword) VALUES
	(1, 'indexing'), (1, 'streaming'),
	(2, 'federated learning'), (2, 'edge computing'),
	(3, 'cost model'), (3, 'storage'),
	(4, 'mutation testing'),
	(5, 'flaky tests'), (5, 'graphs'),
	(6, 'anomaly detection'), (6, 'explainability'),
	(7, 'low-code'), (7, 'usability'),
	(8, 'accessibility'),
	(9, 'caching'),
	(10, 'contracts');

INSERT INTO PAPER_AUTHOR (paper_id, author_id, author_position, is_corresponding) VALUES
	(1,  3,  1, true),  (1,  1,  2, false),
	(2,  5,  1, true),  (2,  4,  2, false), (2, 10, 3, false),
	(3,  4,  1, true),
	(4,  9,  1, true),  (4,  3,  2, false),
	(5,  12, 1, true),
	(6,  2,  1, true),  (6,  10, 2, false),
	(7,  3,  1, true),
	(8,  10, 1, true),  (8,  2,  2, false),
	(9,  2,  1, true),  (9,  4,  2, false),
	(10, 2,  1, true);

-- Version numbers may have gaps; the highest number is the current version (paper 3 has 1 and 3).
INSERT INTO PAPER_VERSION (paper_id, version_no, file_location, uploaded_at, change_note) VALUES
	(1,  1, 'papers/1/v1.pdf',  '2026-02-10 12:00+05', NULL),
	(1,  2, 'papers/1/v2.pdf',  '2026-05-01 10:00+05', 'Camera-ready version'),
	(2,  1, 'papers/2/v1.pdf',  '2026-02-18 09:30+05', NULL),
	(3,  1, 'papers/3/v1.pdf',  '2026-02-25 16:45+05', NULL),
	(3,  3, 'papers/3/v3.pdf',  '2026-05-03 11:00+05', 'Fixed cost model figures'),
	(4,  1, 'papers/4/v1.pdf',  '2026-04-12 11:00+05', NULL),
	(4,  2, 'papers/4/v2.pdf',  '2026-07-01 09:00+05', 'Addressed reviewer comments'),
	(5,  1, 'papers/5/v1.pdf',  '2026-04-20 10:15+05', NULL),
	(6,  1, 'papers/6/v1.pdf',  '2026-02-27 20:00+05', NULL),
	(7,  1, 'papers/7/v1.pdf',  '2026-04-28 14:20+05', NULL),
	(8,  1, 'papers/8/v1.pdf',  '2026-04-30 08:00+05', NULL),
	(9,  1, 'papers/9/v1.pdf',  '2026-02-05 13:00+05', NULL),
	(10, 1, 'papers/10/v1.pdf', '2026-04-15 17:40+05', NULL);

-- No reviewer reviews a paper they authored, and every reviewer is on that conference's committee.
INSERT INTO REVIEW (review_id, paper_id, reviewer_id, overall_score, recommendation,
                    comments_for_authors, confidential_comments, review_submission_date) VALUES
	(1,  1, 6,  5, 'accept', 'Strong evaluation on real workloads.',        NULL,                         '2026-03-20 10:00+05'),
	(2,  1, 7,  4, 'accept', 'Clear writing; add a scalability plot.',      NULL,                         '2026-03-22 15:30+05'),
	(3,  1, 5,  4, 'accept', 'Solid contribution.',                         'Close to an existing paper.','2026-03-25 09:10+05'),
	(4,  2, 7,  4, 'accept', 'Good system design.',                         NULL,                         '2026-03-28 11:00+05'),
	(5,  2, 1,  5, 'accept', 'Convincing results on real devices.',         NULL,                         '2026-04-02 18:45+05'),
	(6,  3, 6,  4, 'accept', 'Useful model; validate on more tiers.',       NULL,                         '2026-04-05 13:20+05'),
	(7,  4, 11, 5, 'accept', 'Impressive scale.',                           NULL,                         '2026-05-20 10:00+05'),
	(8,  4, 12, 4, 'accept', 'Practical and well evaluated.',               NULL,                         '2026-05-22 16:00+05'),
	(9,  5, 9,  2, 'reject', 'Graph construction is under-specified.',      'Baselines look weak.',       '2026-05-18 09:00+05'),
	(10, 5, 11, 1, 'reject', 'Evaluation does not support the claims.',     NULL,                         '2026-05-25 14:00+05'),
	(11, 5, 6,  2, 'reject', 'Interesting idea, needs more work.',          NULL,                         '2026-06-01 12:00+05'),
	(12, 6, 1,  5, 'accept', 'Excellent explanations of anomalies.',        NULL,                         '2026-04-08 17:00+05'),
	(13, 6, 7,  4, 'accept', 'Good paper; minor clarity issues.',           NULL,                         '2026-04-10 10:30+05'),
	(14, 7, 12, 2, 'reject', 'Sample size is too small.',                   NULL,                         '2026-06-05 15:00+05'),
	(15, 7, 9,  1, 'reject', 'Study design has confounds.',                 'Possible duplicate submission.','2026-06-10 11:45+05');

COMMIT;
