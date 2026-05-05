"""Check database readiness from the command line."""

from __future__ import annotations

from frontier_ai_risk_observer.db.session import (
    DatabaseConfigurationError,
    DatabaseUnavailableError,
    check_database_connection,
)


def main() -> int:
    """CLI entrypoint for ``python -m frontier_ai_risk_observer.db.check``."""
    try:
        check_database_connection()
    except (DatabaseConfigurationError, DatabaseUnavailableError) as exc:
        print(exc)
        return 1

    print("Database connection ok.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
