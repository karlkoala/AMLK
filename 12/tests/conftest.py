import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from mathkomp import db, importer  # noqa: E402

CONTENT = ROOT / "content"


@pytest.fixture(scope="session")
def conn():
    """Eine im Speicher aufgebaute Datenbank mit dem vollstaendigen Content."""
    connection = db.connect(":memory:")
    db.init_schema(connection)
    with db.transaction(connection):
        importer.import_all(connection, CONTENT)
    yield connection
    connection.close()


@pytest.fixture
def empty_conn():
    """Leere Datenbank nur mit Schema und Vokabularen - fuer Negativtests."""
    connection = db.connect(":memory:")
    db.init_schema(connection)
    import json
    data = json.loads((CONTENT / "vocabularies.json").read_text(encoding="utf-8"))
    rep = importer.ImportReport()
    with db.transaction(connection):
        importer.import_vocabularies(connection, data, rep)
    yield connection
    connection.close()
