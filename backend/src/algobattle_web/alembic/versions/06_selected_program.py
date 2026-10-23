"""Add selected programs and populate them from the latest uploads.

Revision ID: 9c2f6a1d4e8b
Revises: 8b7c5e2a1f94
"""

from datetime import datetime
from uuid import UUID

import sqlalchemy as sa
from alembic import op
from algobattle.util import Role
from sqlalchemy import select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column


class Base(DeclarativeBase):
    pass


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[UUID] = mapped_column(sa.Uuid(), primary_key=True)
    tournament_id: Mapped[UUID] = mapped_column(sa.Uuid())


class Problem(Base):
    __tablename__ = "problems"

    id: Mapped[UUID] = mapped_column(sa.Uuid(), primary_key=True)
    tournament_id: Mapped[UUID] = mapped_column(sa.Uuid())


class Program(Base):
    __tablename__ = "programs"

    id: Mapped[UUID] = mapped_column(sa.Uuid(), primary_key=True)
    team_id: Mapped[UUID] = mapped_column(sa.Uuid())
    problem_id: Mapped[UUID] = mapped_column(sa.Uuid())
    role: Mapped[str] = mapped_column(sa.String())
    creation_time: Mapped[datetime] = mapped_column(sa.DateTime())


class SelectedProgram(Base):
    __tablename__ = "selectedprograms"

    team_id: Mapped[UUID] = mapped_column(sa.Uuid(), primary_key=True)
    problem_id: Mapped[UUID] = mapped_column(sa.Uuid(), primary_key=True)
    generator_id: Mapped[UUID | None] = mapped_column(sa.Uuid(), nullable=True)
    solver_id: Mapped[UUID | None] = mapped_column(sa.Uuid(), nullable=True)


revision = "9c2f6a1d4e8b"
down_revision = "8b7c5e2a1f94"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "selectedprograms",
        sa.Column("team_id", sa.Uuid(), nullable=False),
        sa.Column("problem_id", sa.Uuid(), nullable=False),
        sa.Column("generator_id", sa.Uuid(), nullable=True),
        sa.Column("solver_id", sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(
            ["team_id"], ["teams.id"], name=op.f("fk_selectedprograms_team_id_teams")
        ),
        sa.ForeignKeyConstraint(
            ["problem_id"], ["problems.id"], name=op.f("fk_selectedprograms_problem_id_problems")
        ),
        sa.ForeignKeyConstraint(
            ["generator_id"],
            ["programs.id"],
            name=op.f("fk_selectedprograms_generator_id_programs"),
        ),
        sa.ForeignKeyConstraint(
            ["solver_id"], ["programs.id"], name=op.f("fk_selectedprograms_solver_id_programs")
        ),
        sa.PrimaryKeyConstraint(
            "team_id", "problem_id", name=op.f("pk_selectedprograms")
        ),
    )

    connection = op.get_bind()
    with Session(bind=connection) as session:
        teams = session.scalars(select(Team)).all()
        problems = session.scalars(select(Problem)).all()
        for team in teams:
            for problem in problems:
                if team.tournament_id != problem.tournament_id:
                    continue
                generators = (
                    select(Program)
                    .where(
                        Program.team_id == team.id,
                        Program.problem_id == problem.id,
                        Program.role == Role.generator.value,
                    )
                    .order_by(Program.creation_time.desc(), Program.id.desc())
                    .limit(1)
                )
                solvers = (
                    select(Program)
                    .where(
                        Program.team_id == team.id,
                        Program.problem_id == problem.id,
                        Program.role == Role.solver.value,
                    )
                    .order_by(Program.creation_time.desc(), Program.id.desc())
                    .limit(1)
                )
                generator = session.scalar(generators)
                solver = session.scalar(solvers)
                session.add(
                    SelectedProgram(
                        team_id=team.id,
                        problem_id=problem.id,
                        generator_id=generator.id if generator is not None else None,
                        solver_id=solver.id if solver is not None else None,
                    )
                )
        session.flush()


def downgrade() -> None:
    op.drop_table("selectedprograms")
