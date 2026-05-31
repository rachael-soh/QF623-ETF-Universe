import wrds

WRDS_USERNAME = "sohrac"


def get_wrds_connection() -> wrds.Connection:
    """Return an authenticated WRDS connection."""
    db = wrds.Connection(wrds_username=WRDS_USERNAME)
    return db
