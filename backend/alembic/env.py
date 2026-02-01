"""
Alembic Environment Configuration (Task 77)
Configured for SQLModel and project settings.
"""
import sys
import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool
from sqlmodel import SQLModel

from alembic import context

# ============================================================
# Add project root to sys.path for model imports
# ============================================================
# env.py is at: backend/alembic/env.py
# We need to import from 'backend.models' and 'backend.core.config'
# So we add 'f:/health_ai_platform_2.0' (project root) to sys.path

# Get the directory containing alembic.ini (backend/)
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Get project root (parent of backend/)
project_root = os.path.dirname(backend_dir)

if project_root not in sys.path:
    sys.path.insert(0, project_root)

# ============================================================
# Import project settings and models
# ============================================================
from backend.core.config import settings
# Import ALL models to ensure they're registered with SQLModel.metadata
from backend.models import User, UserProfile, HealthRecord, IoTHealthData, MedicalDocument

# ============================================================
# Alembic Config object
# ============================================================
config = context.config

# Override sqlalchemy.url with our project's database URI
config.set_main_option("sqlalchemy.url", settings.SQLALCHEMY_DATABASE_URI)

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ============================================================
# Set target_metadata for autogenerate support
# ============================================================
target_metadata = SQLModel.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,  # SQLite compatibility
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, 
            target_metadata=target_metadata,
            render_as_batch=True,  # SQLite compatibility
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
