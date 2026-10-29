"""Containerized ERP Simulator entrypoint."""

from __future__ import annotations

import logging

from erp.config import SimulationConfig
from erp.generator import OrderGenerator
from erp.simulator import ErpSimulator
from erp.storage import NoOpWriter, PostgresWriter


def main() -> None:
    config = SimulationConfig.from_environment()
    logging.basicConfig(
        level=config.log_level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    logger = logging.getLogger("erp_simulator")
    logger.info(
        "Starting ERP simulator: date=%s, history_2015_2022=%d, history_2023=%d, live_limit=%s.",
        config.today,
        config.postgres_old_history_orders,
        config.recent_history_orders,
        "unlimited" if config.live_order_limit == 0 else config.live_order_limit,
    )
    pg_writer = PostgresWriter(config.postgres_dsn) if config.postgres_dsn else NoOpWriter()
    simulator = ErpSimulator(
        config,
        OrderGenerator(),
        pg_writer,
        logger,
    )
    simulator.run()


if __name__ == "__main__":
    main()
