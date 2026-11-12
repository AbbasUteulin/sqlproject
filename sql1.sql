DROP TABLE IF EXISTS REVIEW, PAPER_VERSION, PAPER_AUTHOR, PAPER_KEYWORD, PAPER,
    CONFERENCE_SESSION, TRACK, CONFERENCE_REVIEWER, CONFERENCE_HOST, CONFERENCE,
    REVIEWER_EXPERTISE, REVIEWER, AUTHOR_RESEARCH_AREA, AUTHOR, APP_USER CASCADE;

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
	orcid varchar(16) UNIQUE,

	FOREIGN KEY (author_id) REFERENCES APP_USER (user_id) ON DELETE CASCADE
);

CREATE TABLE AUTHOR_RESEARCH_AREA (
	author_id int NOT NULL,
	area_label varchar(100) NOT NULL,

	PRIMARY KEY (author_id, area_label),

	FOREIGN KEY (author_id) REFERENCES AUTHOR (author_id) ON DELETE CASCADE
);

CREATE TABLE REVIEWER(
	reviewer_id int PRIMARY KEY,
	years_exp int CONSTRAINT non_negative_rev_exp CHECK (years_exp >= 0) NOT NULL,

	FOREIGN KEY (reviewer_id) REFERENCES APP_USER (user_id) ON DELETE CASCADE
);

CREATE TABLE REVIEWER_EXPERTISE (
	reviewer_id int NOT NULL,
	area_label varchar(100) NOT NULL,

	PRIMARY KEY(reviewer_id, area_label),

	FOREIGN KEY (reviewer_id) REFERENCES REVIEWER (reviewer_id) ON DELETE CASCADE
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
	review_deadline timestamptz NOT NULL,

	CONSTRAINT conf_dates_ok CHECK (end_date >= start_date),
    CONSTRAINT conf_deadline_order CHECK (submission_deadline <= review_deadline)
);

CREATE TABLE CONFERENCE_HOST (
	conference_id int NOT NULL,
	host_name VARCHAR(50) NOT NULL,

	PRIMARY KEY (conference_id, host_name),

	FOREIGN KEY (conference_id) REFERENCES CONFERENCE (conference_id) ON DELETE CASCADE
);

CREATE TABLE CONFERENCE_REVIEWER (
	conference_id int NOT NULL,
	reviewer_id int NOT NULL,

	PRIMARY KEY (conference_id, reviewer_id),

	FOREIGN KEY (conference_id) REFERENCES CONFERENCE (conference_id) ON DELETE CASCADE,
	FOREIGN KEY (reviewer_id) REFERENCES REVIEWER (reviewer_id)
);

CREATE TABLE TRACK (
	track_id int PRIMARY KEY,
	conference_id int NOT NULL,
	track_name varchar(50) NOT NULL,
	description text NOT NULL,
	research_area varchar(100) NOT NULL,
	coordinator_id int NOT NULL,

	FOREIGN KEY (conference_id) REFERENCES CONFERENCE (conference_id) ON DELETE CASCADE,
	FOREIGN KEY (coordinator_id) REFERENCES REVIEWER (reviewer_id),
	FOREIGN KEY (conference_id, coordinator_id)
		REFERENCES CONFERENCE_REVIEWER (conference_id, reviewer_id)
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

	FOREIGN KEY (conference_id) REFERENCES CONFERENCE (conference_id) ON DELETE CASCADE,
	FOREIGN KEY (chair_id) REFERENCES REVIEWER (reviewer_id),
	FOREIGN KEY (conference_id, chair_id) REFERENCES CONFERENCE_REVIEWER (conference_id, reviewer_id),
	CONSTRAINT session_times_ok CHECK (end_time > start_time)
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
	FOREIGN KEY (session_id) REFERENCES CONFERENCE_SESSION (session_id) ON DELETE SET NULL,
	CONSTRAINT paper_status CHECK (status = 'submitted' OR
													  status = 'under review' OR
													  status = 'accepted' OR
													  status = 'rejected' OR
													  status = 'withdrawn'),
	CONSTRAINT scheduled_only_if_accepted CHECK (session_id IS NULL OR status = 'accepted')
);

CREATE TABLE PAPER_KEYWORD (
	paper_id int NOT NULL,
	keyword text NOT NULL,

	FOREIGN KEY (paper_id) REFERENCES PAPER (paper_id) ON DELETE CASCADE,
	PRIMARY KEY (paper_id, keyword)
);

CREATE TABLE PAPER_AUTHOR (
	paper_id int NOT NULL,
	author_id int NOT NULL,
	author_position int NOT NULL,
	is_corresponding bool NOT NULL DEFAULT false,

	PRIMARY KEY (paper_id, author_id),

	FOREIGN KEY (paper_id) REFERENCES PAPER (paper_id) ON DELETE CASCADE, 
	FOREIGN KEY (author_id) REFERENCES AUTHOR (author_id),

	CONSTRAINT positive_author_pos CHECK (author_position > 0),
	CONSTRAINT paper_author_unique UNIQUE (paper_id, author_position)
);

CREATE UNIQUE INDEX one_corresponding_per_paper
    ON PAPER_AUTHOR (paper_id) WHERE is_corresponding;

CREATE TABLE PAPER_VERSION (
	paper_id int NOT NULL,
	version_no int NOT NULL,
	file_location text NOT NULL,
	uploaded_at timestamptz NOT NULL DEFAULT now(),
	change_note text,

	PRIMARY KEY (paper_id, version_no),
	
	FOREIGN KEY (paper_id) REFERENCES PAPER (paper_id) ON DELETE CASCADE,
	CONSTRAINT pos_version_no CHECK (version_no > 0)
);

CREATE TABLE REVIEW (
	review_id int PRIMARY KEY,
	paper_id int NOT NULL,
	reviewer_id int NOT NULL,
	overall_score int NOT NULL,
	recommendation text NOT NULL,
	comments_for_authors text NOT NULL,
	confidential_comments text,
	review_submission_date timestamptz NOT NULL,

	FOREIGN KEY (paper_id) REFERENCES PAPER (paper_id) ON DELETE CASCADE,
	FOREIGN KEY (reviewer_id) REFERENCES REVIEWER (reviewer_id),

	CONSTRAINT review_unique UNIQUE (paper_id, reviewer_id),
	CONSTRAINT recommendation_status CHECK (recommendation = 'accept' OR recommendation = 'reject'),
	CONSTRAINT one_to_five CHECK (overall_score BETWEEN 1 AND 5)
);

CREATE OR REPLACE FUNCTION  self_review_check()
RETURNS trigger AS $$
BEGIN
		IF EXISTS(
			SELECT 1 FROM PAPER_AUTHOR
			WHERE paper_id = NEW.paper_id
			AND
			author_id = NEW.reviewer_id
		)
		THEN RAISE EXCEPTION 'authors cannot self-review';
		END IF;
		return NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER self_review_trigger
BEFORE INSERT OR UPDATE OF reviewer_id, paper_id
ON REVIEW
FOR EACH ROW
EXECUTE FUNCTION self_review_check();


