"""SQLAlchemy models mirroring the Prisma schema (PostgreSQL).

Table names are kept lowercase to match the existing database created by
Prisma migrations. Class names use PascalCase. Relationships are populated
where Prisma relations exist; the ``@relation`` foreign keys are preserved.
"""

from __future__ import annotations

from app.models.account import Account
from app.models.adressen import Adressen
from app.models.anlaesse import Anlaesse
from app.models.base import Base
from app.models.budget import Budget
from app.models.clubmeister import Clubmeister
from app.models.fiscalyear import Fiscalyear
from app.models.journal import Journal
from app.models.journal_receipt import JournalReceipt
from app.models.kegelkasse import Kegelkasse
from app.models.kegelmeister import Kegelmeister
from app.models.meisterschaft import Meisterschaft
from app.models.parameter import Parameter
from app.models.receipt import Receipt
from app.models.sessions import Sessions
from app.models.user import User

__all__ = [
    "Base",
    "Account",
    "Adressen",
    "Anlaesse",
    "Budget",
    "Clubmeister",
    "Fiscalyear",
    "Journal",
    "JournalReceipt",
    "Kegelkasse",
    "Kegelmeister",
    "Meisterschaft",
    "Parameter",
    "Receipt",
    "Sessions",
    "User",
]
