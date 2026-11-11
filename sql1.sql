CREATE TABLE APP_USER (
	user_id int PRIMARY KEY,
	given_name varchar(100) NOT NULL,
	surname varchar(100) NOT NULL,
	email text UNIQUE NOT NULL,
	affiliation varchar(30) NOT NULL,
	country varchar(30) NOT NULL,
	phone_number varchar(16) NOT NULL
);

CREATE TABLE AUTHOR (
	author_id int PRIMARY KEY,
	orcid varchar(16),

	FOREIGN KEY (author_id) REFERENCES APP_USER (user_id)
);

CREATE TABLE AUTHOR_RESEARCH_AREA (
	author_id int NOT NULL,
	area_label varchar(100) NOT NULL,

	PRIMARY KEY (author_id, area_label),

	FOREIGN KEY (author_id) REFERENCES AUTHOR (author_id)
);

CREATE TABLE REVIEWER(
	reviewer_id int PRIMARY KEY,
	years_exp int CONSTRAINT non_negative_rev_exp CHECK (years_exp >= 0) NOT NULL,

	FOREIGN KEY (reviewer_id) REFERENCES APP_USER (user_id)
);

CREATE TABLE REVIEWER_EXPERTISE (
	reviewer_id int NOT NULL,
	area_label varchar(100) NOT NULL,

	PRIMARY KEY(reviewer_id, area_label),

	FOREIGN KEY (reviewer_id) REFERENCES REVIEWER (reviewer_id)
);

CREATE TABLE CONFERENCE(
	conference_id int PRIMARY KEY,
	conference_name varchar(100) NOT NULL,
	acronym varchar(10) NOT NULL,
	description text NOT NULL,
	city varchar(60) NOT NULL,
	country varchar(30) NOT NULL,
	start_date timestamptz NOT NULL,
	end_date timestamptz NOT NULL,
	submission_deadline timestamptz NOT NULL,
	review_deadline timestamptz NOT NULL
);

CREATE TABLE CONFERENCE_HOST (
	conference_id int NOT NULL,
	host_name VARCHAR(50) NOT NULL,

	PRIMARY KEY (conference_id, host_name),

	FOREIGN KEY (conference_id) REFERENCES CONFERENCE (conference_id)
);

CREATE TABLE CONFERENCE_REVIEWER (
	conference_id int NOT NULL,
	reviewer_id int NOT NULL,

	PRIMARY KEY (conference_id, reviewer_id),

	FOREIGN KEY (conference_id) REFERENCES CONFERENCE (conference_id),
	FOREIGN KEY (reviewer_id) REFERENCES REVIEWER (reviewer_id)
);

CREATE TABLE TRACK (
	track_id int PRIMARY KEY,
	conference_id int NOT NULL,
	track_name varchar(50) NOT NULL,
	description text NOT NULL,
	research_area varchar(20) NOT NULL,
	coordinator_id int NOT NULL,

	FOREIGN KEY (conference_id) REFERENCES CONFERENCE (conference_id),
	FOREIGN KEY (coordinator_id) REFERENCES REVIEWER (reviewer_id)
);

CREATE TABLE CONFERENCE_SESSION (
	session_id int PRIMARY KEY,
	conference_id int NOT NULL,
	title varchar(100) NOT NULL,
	session_date date NOT NULL,
	start_time time NOT NULL,
	end_time time NOT NULL,
	room_label varchar(10) NOT NULL,
	chair_id int NOT NULL,

	FOREIGN KEY (conference_id) REFERENCES CONFERENCE (conference_id),
	FOREIGN KEY (chair_id) REFERENCES REVIEWER (reviewer_id)
);

CREATE TABLE PAPER (
	paper_id int PRIMARY KEY,
	track_id int NOT NULL,
	title varchar(100) NOT NULL,
	abstract TEXT NOT NULL,
	submission_date timestamptz NOT NULL,
	status varchar(20) NOT NULL,
	session_id int,

	FOREIGN KEY (track_id) REFERENCES TRACK (track_id),
	FOREIGN KEY (session_id) REFERENCES CONFERENCE_SESSION (session_id),
	CONSTRAINT paper_status CHECK (status = 'submitted' OR
													  status = 'under review' OR
													  status = 'accepted' OR
													  status = 'rejected' OR
													  status = 'withdrawn')
);

CREATE TABLE PAPER_KEYWORD (
	paper_id int NOT NULL,
	keyword text NOT NULL,

	FOREIGN KEY (paper_id) REFERENCES PAPER (paper_id),
	PRIMARY KEY (paper_id, keyword)
);

CREATE TABLE PAPER_AUTHOR (
	paper_id int NOT NULL,
	author_id int NOT NULL,
	author_position int CONSTRAINT non_negative_author_pos CHECK (author_position >= 0) NOT NULL UNIQUE,
	is_corresponding bool NOT NULL,

	PRIMARY KEY (paper_id, author_id),

	FOREIGN KEY (paper_id) REFERENCES PAPER (paper_id),
	FOREIGN KEY (author_id) REFERENCES AUTHOR (author_id),

	CONSTRAINT paper_author_unique UNIQUE (paper_id, author_position)
);

CREATE TABLE PAPER_VERSION (
	paper_id int NOT NULL,
	version_no numeric CONSTRAINT pos_version_no CHECK(version_no > 0),
	file_location text NOT NULL,
	uploaded_at varchar(100) NOT NULL,
	change_note text,

	PRIMARY KEY (paper_id, version_no),
	
	FOREIGN KEY (paper_id) REFERENCES PAPER (paper_id)
);

CREATE TABLE REVIEW (
	review_id int PRIMARY KEY,
	paper_id int NOT NULL,
	reviewer_id int NOT NULL,
	overall_score int CONSTRAINT one_to_five CHECK(overall_score >= 1 AND overall_score <= 5) NOT NULL,
	recommendation text NOT NULL,
	comments_for_authors text NOT NULL,
	cofidential_comments text,
	review_submission_date timestamptz NOT NULL,

	FOREIGN KEY (paper_id) REFERENCES PAPER (paper_id),
	FOREIGN KEY (reviewer_id) REFERENCES REVIEWER (reviewer_id),

	CONSTRAINT review_unique UNIQUE (paper_id, reviewer_id),
	CONSTRAINT recommendation_status CHECK (recommendation = 'accept' OR recommendation = 'reject')
);