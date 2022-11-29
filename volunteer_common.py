import sqlite3
from threading import Lock


class DB:
    def __init__(self):
        self.lock = Lock()  # writes should be protected
        self.con = sqlite3.connect(
            "volunteer_tasks.db",
            isolation_level=None,  # autocommit mode (a.k.a. implicit transactions)
            check_same_thread=False,
        )
        self.cur = self.con.cursor()

class Task:
    SHELTER = "SHELTER"
    TRANSPORT = "TRANSPORT"
    VOLUNTEER = "VOLUNTEER"
    QUESTION = "QUESTION"
    OTHER = "OTHER"

class TaskStatus:
    UNASSIGNED = "UNASSIGNED"
    ASSIGNED = "ASSIGNED"
    # TODO: Do we need the distinction between closed statuses? Done / Abandoned / WAI...
    CLOSED = "CLOSED"
