# sqlproject
An sql project repository containing all parts from the ASSIGNMENT 3 of CSCI-341.

# PART 1

# Required database constraints
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

# Required application checks

1. Prevent self-reviews. Reject a review if its reviewer authored that paper. Check this when saving a
review and when changing the paper’s authors.

3. Validate session assignments. A scheduled paper must be accepted, and its track and session
must belong to the same conference. Check assignments and relevant changes to paper status,
track, or session conference; reject the change or remove the invalid assignment.
Simple application validation is sufficient for these two checks. Triggers and advanced concurrency
handling are not required.

# Other business rules

All remaining Assignment 1 business rules must hold in the sample data and be documented. Their
automatic enforcement is optional. Examples include every user having an author or reviewer role,
required child records, exactly one corresponding author per paper, and coordinators and chairs
belonging to their conference’s reviewer pool. State which optional rules your application enforces.


