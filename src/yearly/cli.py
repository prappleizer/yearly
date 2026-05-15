"""
cli.py – console_scripts entry point.

After `pip install -e .` (or a regular install), run:
    yearly-serve
    yearly-serve --port 8080
    yearly-serve --host 0.0.0.0 --port 3000 --reload
"""

import argparse

import uvicorn


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="yearly-serve", description="Start the YearView server"
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=3000)
    parser.add_argument(
        "--reload", action="store_true", help="Enable auto-reload (dev mode)"
    )
    args = parser.parse_args()

    uvicorn.run(
        "yearly.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
