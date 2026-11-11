# sqlproject
An sql project repository containing all parts from the ASSIGNMENT 3 of CSCI-341.

#PART 1  — Required database constraints
• Define primary keys, foreign keys, and appropriate NOT NULL constraints. Enforce unique user
emails, unique author positions within each paper, and at most one review per reviewer and
paper. Store completed reviews only.
• Use CHECK constraints for paper status (submitted, under review, accepted, rejected, or
withdrawn), integer review scores from 1 to 5, and recommendations (accept or reject). Also check
positive integer author positions and version numbers, nonnegative reviewing experience,
conference end dates not earlier than start dates, and session end times later than start times.
• Identify versions by (paper_id, version_no); gaps are allowed and the highest number identifies
the current version. Use ON DELETE CASCADE from papers to their versions. Each paper may
be assigned to at most one session. In the reference schema, PAPER.session_id identifies that
session and is NULL if the paper is not assigned to a session.

