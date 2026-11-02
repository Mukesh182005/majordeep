"""Store media_type, status and verdict as strings, as the models do.

The initial schema created PostgreSQL enum types (mediatype, jobstatus, verdict) with upper-case
member names, but ``app.models.SafeEnum`` writes the lower-case values as VARCHAR, so on PostgreSQL
every upload failed ("column media_type is of type mediatype but expression is of type character
varying"). SQLite stores these columns as VARCHAR already, so nothing changes there.

Revision ID: 7c2a1f0e9b31
Revises: 46ef908783bf
Create Date: 2026-11-02 14:30:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "7c2a1f0e9b31"
down_revision: str | None = "46ef908783bf"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

COLUMNS = (("media_type", "mediatype", 16), ("status", "jobstatus", 16), ("verdict", "verdict", 32))


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    for column, enum_name, length in COLUMNS:
        op.alter_column("jobs", column, type_=sa.String(length=length), postgresql_using=f"{column}::text")
        op.execute(f"DROP TYPE IF EXISTS {enum_name}")
    # The app queries the lower-case values (MediaType, JobStatus); verdicts are already upper-case.
    op.execute("UPDATE jobs SET media_type = lower(media_type), status = lower(status)")


def downgrade() -> None:
    # Values written since the upgrade are lower-case or outside the old enums; the columns stay strings.
    pass
