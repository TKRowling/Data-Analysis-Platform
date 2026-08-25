# Database sources

The MVP supports PostgreSQL and MySQL through SQLAlchemy. Users provide host, port, database, username, password, and a single read-only `SELECT` query.

For production, use a dedicated read-only database role, a secrets manager, TLS, query timeouts, row limits, an allowlist of hosts, and an SQL parser rather than relying only on initial statement validation.

