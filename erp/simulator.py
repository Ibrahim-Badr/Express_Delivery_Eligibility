"""ERP scenario orchestration for historical seeding and live order streaming."""

from __future__ import annotations

import logging
import time
from datetime import date, timedelta

from erp.config import SimulationConfig
from erp.generator import OrderGenerator
from erp.storage import OrderCounter, OrderWriter


class ErpSimulator:
    def __init__(
        self,
        config: SimulationConfig,
        generator: OrderGenerator,
        postgres: OrderWriter,
        logger: logging.Logger,
    ) -> None:
        self.config = config
        self.generator = generator
        self.postgres = postgres
        self.logger = logger

    def run(self) -> None:
        try:
            self._write_history()
            self._write_live_stream()
        finally:
            self.postgres.close()
            self.logger.info("Database connection closed.")

    def _write_history(self) -> None:
        old_count = self.config.postgres_old_history_orders
        recent_count = self.config.recent_history_orders
        old_orders = self.generator.old_history(old_count, self.config.today, first_sequence=1)
        self.logger.info(
            "PostgreSQL legacy history (2015-2022) seeded: %d new orders.",
            self.postgres.write(old_orders),
        )

        recent_orders = self.generator.recent_history(
            recent_count, self.config.today, first_sequence=old_count + 1
        )
        self.logger.info(
            "PostgreSQL recent history (2023+) seeded: %d new orders.",
            self.postgres.write(recent_orders),
        )

        if isinstance(self.postgres, OrderCounter):
            count = self.postgres.count_from(date(2023, 1, 1), self.config.today)
            self.logger.info("PostgreSQL total orders since 2023: %d.", count)

    def _write_live_stream(self) -> None:
        minimum_sequence = (
            self.config.postgres_old_history_orders
            + self.config.recent_history_orders
            + 1
        )
        sequence = minimum_sequence
        if isinstance(self.postgres, OrderCounter):
            sequence = max(sequence, self.postgres.next_sequence() + 1)
            self.logger.info("Next live sequence: ERP-%08d.", sequence)
        simulation_date = self.config.today
        while self.config.live_order_limit == 0 or sequence <= self.config.live_order_limit:
            size = self._next_batch_size(sequence)
            orders = self.generator.live_batch(sequence, size, simulation_date)
            postgres_count = self.postgres.write(orders)
            self.logger.info(
                "Live batch written: PostgreSQL=%d, date=%s, last_order=%s.",
                postgres_count,
                orders[-1]["order_date"],
                orders[-1]["order_id"],
            )
            sequence += size
            simulation_date += timedelta(days=1)
            time.sleep(self.config.interval_seconds)
        self.logger.info("Live stream completed: LIVE_ORDER_LIMIT reached.")

    def _next_batch_size(self, sequence: int) -> int:
        remaining = self.config.live_order_limit - sequence + 1
        if self.config.live_order_limit:
            return min(self.config.batch_size, remaining)
        return self.config.batch_size
