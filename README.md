# sqlproject
An sql project repository containing all parts from the ASSIGNMENT 3 of CSCI-341.

# PART 1

# REMAINING ISSUES

CHECK constraints for conference end dates not earlier than start dates, and session end times later than start times.

Identify versions by (paper_id, version_no); gaps are allowed and the highest number identifies
the current version. Use ON DELETE CASCADE from papers to their versions. Each paper may
be assigned to at most one session. In the reference schema, PAPER.session_id identifies that
session and is NULL if the paper is not assigned to a session.


Required application checks FROM PART 1 of the ASSIGNMENT 3 haven't been implemented yet.

Other Business rules FROM PART 1 of the ASSIGNMENT 3 haven't been implemented yet.

Some constraints inside a table need a refactor to put them below for comprehension and style [NOT MANDATORY]

