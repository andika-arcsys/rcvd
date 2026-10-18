"""Jalankan engine: python -m deepinsight_engine"""

from __future__ import annotations

import uvicorn

from .api.app import create_app


def main() -> None:
    app = create_app()
    net = app.state.settings.app.engine
    uvicorn.run(app, host=net.host, port=net.port, log_config=None)


if __name__ == "__main__":
    main()
