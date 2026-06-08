import wrds

WRDS_USERNAME = "ngchunyue"


def get_wrds_connection() -> wrds.Connection:
    """Return an authenticated WRDS connection."""
    db = wrds.Connection(wrds_username=WRDS_USERNAME)
    return db
