"""Jalankan engine: python -m deepinsight_engine"""

from __future__ import annotations

import uvicorn

from .api.app import create_app
from .stop import run_until_stopped


def main() -> None:
    app = create_app()
    net = app.state.settings.app.engine
    run_until_stopped(lambda: uvicorn.run(app, host=net.host, port=net.port, log_config=None))


if __name__ == "__main__":
    main()
