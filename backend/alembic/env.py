"""Alembic environment configuration."""
import os
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

from database import Base
from models import User, ApiKey, Project, Dataset, Conversation, Message, Insight, Chart, Notebook, Cell
from models.skill import Skill, SkillExecution
from models.resource import Resource, ResourceReference
from models.run import Run, RunStep
from models.workflow import Workflow, WorkflowStep

config = context.config

# Override sqlalchemy.url with environment variable
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://nexa:nexa@localhost:5432/nexa")
config.set_main_option("sqlalchemy.url", DATABASE_URL)

target_metadata = Base.metadata


def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
