--- PATCH: db/store.py upsert_austin_license ---
Replace the upsert_austin_license function. The original has two bugs:
1. A stray CREATE TABLE scottsdale_licenses inside the INSERT branch
2. Missing conn.commit() on the insert path (only commits on update)

Replace this block (lines starting at "def upsert_austin_license"):

OLD (buggy):
    if existing is None:
        conn.execute(
            """INSERT INTO austin_licenses ...""",
            (...)
        )
        conn.execute("""
        CREATE TABLE IF NOT EXISTS scottsdale_licenses (
            ...
        )
    """)
        return {"is_new": True, "was_revoked": False}

NEW (fixed):
    if existing is None:
        conn.execute(
            """INSERT INTO austin_licenses ...""",
            (...)
        )
        conn.commit()
        return {"is_new": True, "was_revoked": False}
