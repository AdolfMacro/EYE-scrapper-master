from pathlib import Path
from tempfile import TemporaryDirectory

from master.scraper_registry import ScraperRegistry
from master.process_manager import ProcessManager


def main():

    with TemporaryDirectory() as temp:

        temp = Path(temp)

        registry = ScraperRegistry(
            registry_file=temp / "scrapers.json"
        )

        manager = ProcessManager(
            registry=registry,
            runtime_dir=temp / "runtime",
        )

        process = manager.create(
            name="restart_test",
            providers=[
                "google",
            ],
            database=str(
                temp / "test.db"
            ),
            target="schools",
            config={
                "keyword": "مدرسه",
            },
        )

        print("\n=== CREATE ===")
        print(process)
        print(registry.get("restart_test"))

        print("\n=== START ===")

        manager.start(
            "restart_test"
        )

        first_pid = (
            process.pid
        )

        print(
            "PID:",
            first_pid,
        )

        print(
            "STATUS:",
            manager.status(
                "restart_test"
            ),
        )

        print("\n=== RESTART ===")

        new_process = manager.restart(
            "restart_test"
        )

        second_pid = (
            new_process.pid
        )

        print(
            "OLD PID:",
            first_pid,
        )

        print(
            "NEW PID:",
            second_pid,
        )

        print(
            "SAME PID:",
            first_pid == second_pid,
        )

        print(
            "STATUS:",
            manager.status(
                "restart_test"
            ),
        )

        print("\n=== STOP ===")

        manager.stop(
            "restart_test",
            timeout=5,
        )

        print(
            "FINAL STATUS:",
            manager.status(
                "restart_test"
            ),
        )

        print("\n=== REMOVE ===")

        manager.remove(
            "restart_test"
        )

        print(
            "PROCESS EXISTS:",
            manager.exists(
                "restart_test"
            ),
        )

        print(
            "REGISTRY EXISTS:",
            registry.exists(
                "restart_test"
            ),
        )


if __name__ == "__main__":
    main()
