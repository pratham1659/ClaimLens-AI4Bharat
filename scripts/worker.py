import sys
import os
import argparse

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from redis import Redis
from rq import Worker

from app.core.settings import get_settings


def main() -> None:
    settings = get_settings()
    connection = Redis.from_url(settings.redis_url)
    parser = argparse.ArgumentParser(description="ClaimLens RQ worker")
    parser.add_argument(
        "--queue",
        choices=["default", "dead_letter", "both"],
        default="default",
        help="Queue selection for worker",
    )
    args = parser.parse_args()

    queue_names = [settings.rq_default_queue]
    if args.queue == "dead_letter":
        queue_names = [settings.rq_dead_letter_queue]
    elif args.queue == "both":
        queue_names = [settings.rq_default_queue, settings.rq_dead_letter_queue]

    worker = Worker(queue_names, connection=connection)
    worker.work()


if __name__ == "__main__":
    main()
