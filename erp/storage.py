"""PostgreSQL persistence adapter for the ERP simulator."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from typing import Any, Protocol, runtime_checkable

Order = dict[str, object]


class NoOpWriter:
    def write(self, orders: Sequence[Order]) -> int:
        return 0

    def close(self) -> None:
        pass


class OrderWriter(Protocol):
    def write(self, orders: Sequence[Order]) -> int:
        """Write orders and return the count of newly inserted records."""

    def close(self) -> None:
        """Release database connection resources."""


@runtime_checkable
class OrderCounter(Protocol):
    def count_from(self, start: date, end: date) -> int:
        """Count orders in a date range."""

    def next_sequence(self) -> int:
        """Return the highest existing ERP sequence number."""


class PostgresWriter:
    def __init__(self, dsn: str) -> None:
        import psycopg  # type: ignore[import-not-found]
        from psycopg.rows import dict_row  # type: ignore[import-not-found]

        self.connection: Any = psycopg.connect(dsn, row_factory=dict_row)
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS orders (
            order_id TEXT PRIMARY KEY, order_date DATE, hour INTEGER NOT NULL,
            day_of_week INTEGER NOT NULL, weekend INTEGER,
            distance_km DOUBLE PRECISION NOT NULL, order_value_eur DOUBLE PRECISION NOT NULL,
            weight_kg DOUBLE PRECISION NOT NULL, stock_available INTEGER NOT NULL,
            preparation_time_min DOUBLE PRECISION, carrier_capacity DOUBLE PRECISION NOT NULL,
            weather TEXT NOT NULL, delivery_zone TEXT NOT NULL, customer_type TEXT NOT NULL)"""
        )
        self.connection.execute("ALTER TABLE orders ADD COLUMN IF NOT EXISTS order_date DATE")
        self.connection.execute("ALTER TABLE orders ALTER COLUMN weekend DROP NOT NULL")
        self.connection.execute(
            "ALTER TABLE orders ALTER COLUMN preparation_time_min DROP NOT NULL"
        )
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            description TEXT NOT NULL)"""
        )
        self.connection.execute(
            """INSERT INTO schema_migrations (version, description) VALUES
            (2015, 'Added weekend column'),
            (2017, 'Added preparation_time_min column'),
            (2023, 'Extended schema for current live stream')
            ON CONFLICT (version) DO NOTHING"""
        )
        self.connection.commit()

    def write(self, orders: Sequence[Order]) -> int:
        inserted = 0
        with self.connection.transaction():
            for order in orders:
                columns = tuple(order)
                placeholders = ", ".join(["%s"] * len(columns))
                col_names = ", ".join(columns)
                cursor = self.connection.execute(
                    f"INSERT INTO orders ({col_names}) VALUES ({placeholders}) "
                    "ON CONFLICT (order_id) DO NOTHING",
                    tuple(order[column] for column in columns),
                )
                inserted += cursor.rowcount
        self.connection.commit()
        return inserted

    def count_from(self, start: date, end: date) -> int:
        row = self.connection.execute(
            "SELECT COUNT(*) AS count FROM orders WHERE order_date >= %s AND order_date < %s",
            (start, end),
        ).fetchone()
        self.connection.commit()
        return int(row["count"])

    def next_sequence(self) -> int:
        row = self.connection.execute(
            """SELECT COALESCE(MAX(
                CASE WHEN order_id ~ '^ERP-[0-9]+$'
                THEN SUBSTRING(order_id FROM 5)::BIGINT ELSE 0 END
            ), 0) AS max_sequence FROM orders"""
        ).fetchone()
        self.connection.commit()
        return int(row["max_sequence"])

    def close(self) -> None:
        self.connection.close()
