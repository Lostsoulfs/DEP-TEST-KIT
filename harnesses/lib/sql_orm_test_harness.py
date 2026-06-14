#!/usr/bin/env python3
"""ORM-mapping constraint test harness (SQLAlchemy, in-memory SQLite).

WHY: Repository tests that run against a mocked Session pass even when the ORM
MODEL forgot `unique=True` (or `nullable=False`). The mock has no schema, so a
"deduplicating" store looks correct and still writes duplicates in production.
A real engine — even in-memory SQLite — executes the actual mapping and raises
IntegrityError. This is the ORM-layer sibling of the integration postgres_store
bug (CWE-Improper-Enforcement), caught without Docker.

HOW: `build_model(unique)` declares a `User` whose `email` column is UNIQUE only
when `unique=True`. `allows_duplicate(unique)` inserts the same email twice
against a fresh in-memory engine and reports whether the second insert was
accepted. The ORACLE (`unique=True`) rejects it (IntegrityError); the BUGGY
mapping (`unique=False`) silently accepts it (row count 2). The proof shows the
real engine exposes exactly the difference a mock hides.

WHERE: lib/ — dependency-backed (`sqlalchemy`) but in-process via `sqlite://`,
no external service. Adds `sqlalchemy` to the `lib` extra in pyproject.toml.

Self-test:
    python harnesses/lib/sql_orm_test_harness.py --self-test
"""

from __future__ import annotations

import argparse
import sys

from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, declarative_base


def build_model(unique: bool):
    """Build a fresh declarative base + User model. A new base per call avoids
    table/class registry collisions between the oracle and buggy variants."""
    Base = declarative_base()

    class User(Base):
        __tablename__ = "users"
        id = Column(Integer, primary_key=True)
        email = Column(String, unique=unique, nullable=False)

    return Base, User


def allows_duplicate(unique: bool) -> bool:
    """Insert the same email twice. True == the second insert was accepted
    (the missing-constraint bug); False == it was rejected (IntegrityError)."""
    Base, User = build_model(unique)
    engine = create_engine("sqlite://")  # in-memory, in-process
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(User(email="dup@example.com"))
        session.commit()
        session.add(User(email="dup@example.com"))
        try:
            session.commit()
            return True   # duplicate accepted -> constraint was never enforced
        except IntegrityError:
            session.rollback()
            return False  # real engine enforced UNIQUE


def run_self_test() -> int:
    failures = 0
    if allows_duplicate(unique=True):
        failures += 1
        print("FAIL: oracle model (unique=True) accepted a duplicate", file=sys.stderr)
    if not allows_duplicate(unique=False):
        failures += 1  # the planted bug must be caught — else vacuous green
        print("FAIL: buggy model (unique=False) did NOT produce a duplicate", file=sys.stderr)
    if failures:
        print(f"self-test: {failures} failure(s)", file=sys.stderr)
        return 1
    print("self-test: OK (UNIQUE enforced by oracle; missing-constraint bug caught)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="ORM-mapping constraint harness")
    parser.add_argument("--self-test", action="store_true")
    parser.parse_args(argv)
    return run_self_test()


if __name__ == "__main__":
    sys.exit(main())
