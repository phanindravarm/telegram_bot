Add a new database table called "$ARGUMENTS" to the project.

1. In `db.py`, inside `init_db()`, add a new `CREATE TABLE IF NOT EXISTS $ARGUMENTS` statement with appropriate columns (ask if schema is unclear).

2. In `db.py`, add CRUD helper functions following the existing `_connect()` pattern:
   - `save_$ARGUMENTS(...)` — INSERT
   - `get_$ARGUMENTS(...)` — SELECT
   - `delete_$ARGUMENTS(...)` — DELETE
   Each function should open a connection with `_connect()`, execute the query, commit (for writes), and close the connection.

3. In `tests/test_db.py`, add tests for the new CRUD functions. Use a temporary database or clean up after tests.

After creating everything, run `source env/bin/activate && pytest tests/test_db.py -v` to verify.
