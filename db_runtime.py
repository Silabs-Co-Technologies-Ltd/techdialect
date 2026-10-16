"""Persistent DB connector for TechDialect.

Local development uses sqlite3. On Vercel, configure a remote Turso database;
the local filesystem is never used for writable application data.
"""
import os
import sqlite3

REMOTE_URL = os.getenv("TURSO_DATABASE_URL", "").strip()
REMOTE_TOKEN = os.getenv("TURSO_AUTH_TOKEN", "").strip()
IS_VERCEL = bool(os.getenv("VERCEL") or os.getenv("VERCEL_ENV"))


def validate_database_configuration():
    if bool(REMOTE_URL) != bool(REMOTE_TOKEN):
        raise RuntimeError("Both TURSO_DATABASE_URL and TURSO_AUTH_TOKEN must be configured.")
    if IS_VERCEL and not REMOTE_URL:
        raise RuntimeError("Vercel deployments require persistent TURSO_DATABASE_URL and TURSO_AUTH_TOKEN. Local SQLite is not safe.")
    if REMOTE_URL and not REMOTE_URL.startswith(("libsql://", "https://")):
        raise RuntimeError("TURSO_DATABASE_URL must be a libsql:// or https:// URL.")
    return bool(REMOTE_URL)


class ResultRow:
    """sqlite3.Row-compatible indexed and named access for remote DB-API rows."""
    __slots__ = ("_values", "_names")
    def __init__(self, values, names):
        self._values = tuple(values)
        self._names = tuple(names)

    def __getitem__(self, item):
        if isinstance(item, int):
            return self._values[item]
        if isinstance(item, slice):
            return self._values[item]
        field = str(item).lower()
        for i, name in enumerate(self._names):
            if name.lower() == field:
                return self._values[i]
        raise IndexError("Unknown result column: " + str(item))

    def __iter__(self):
        return iter(self._values)

    def __len__(self):
        return len(self._values)

    def keys(self):
        return list(self._names)


class CursorShim:
    def __init__(self, native):
        self.native = native

    def execute(self, sql, params=()):
        self.native.execute(sql, tuple(params))
        return self

    @property
    def description(self):
        return self.native.description

    @property
    def rowcount(self):
        return self.native.rowcount

    @property
    def lastrowid(self):
        return getattr(self.native, "lastrowid", None)

    def _convert(self, row):
        if row is None:
            return None
        # A remote backend may return sqlite3-like Row objects already.
        if hasattr(row, "keys") and callable(row.keys):
            return row
        names = [column[0] for column in (self.description or ())]
        return ResultRow(row, names) if names else row

    def fetchone(self):
        return self._convert(self.native.fetchone())

    def fetchall(self):
        return [self._convert(x) for x in self.native.fetchall()]

    def __iter__(self):
        for row in self.native:
            yield self._convert(row)


class ConnectionShim:
    def __init__(self, native):
        self.native = native
        self.row_factory = None

    def cursor(self):
        return CursorShim(self.native.cursor())

    def execute(self, sql, params=()):
        return self.cursor().execute(sql, params)

    def commit(self):
        return self.native.commit()

    def rollback(self):
        return self.native.rollback()

    def close(self):
        return self.native.close()


def connect(db_path):
    if validate_database_configuration():
        # Remote HTTP DB-API, no local database file in serverless compute.
        import turso_serverless
        remote = turso_serverless.connect(REMOTE_URL, auth_token=REMOTE_TOKEN)
        return ConnectionShim(remote)
    conn = sqlite3.connect(db_path, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=15000")
    return conn


def uses_remote_database():
    return bool(REMOTE_URL)
