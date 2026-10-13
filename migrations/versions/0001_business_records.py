"""Initial owner-scoped business schema."""

from alembic import op

import web.models as _models
from web.database import Base

_MODEL_REGISTRY = (
    _models.User,
    _models.Project,
    _models.Drone,
    _models.Simulation,
    _models.Report,
    _models.LabSession,
    _models.UserSetting,
    _models.HardwareLog,
)

revision = "0001_business_records"
down_revision = None
branch_labels = None
depends_on = None
INITIAL_TABLES = (
    "users",
    "projects",
    "drones",
    "simulations",
    "reports",
    "lab_sessions",
    "user_settings",
)


def upgrade():
    Base.metadata.create_all(
        bind=op.get_bind(), tables=[Base.metadata.tables[name] for name in INITIAL_TABLES]
    )


def downgrade():
    Base.metadata.drop_all(
        bind=op.get_bind(), tables=[Base.metadata.tables[name] for name in reversed(INITIAL_TABLES)]
    )
