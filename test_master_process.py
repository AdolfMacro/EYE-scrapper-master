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
            name="test",
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

        print("\n=== CREATED ===")
        print(process)
        print(registry.get("test"))

        print("\n=== STARTING ===")

        manager.start("test")

        print(registry.get("test"))

        print(
            "\nPID:",
            process.pid,
        )

        print(
            "\nSTATUS:",
            manager.status("test"),
        )

        print("\n=== SNAPSHOT ===")

        print(
            manager.snapshot("test")
        )

        print("\n=== STOPPING ===")

        manager.stop(
            "test",
            timeout=5,
        )

        print("\n=== AFTER STOP ===")

        print(
            registry.get("test")
        )

        print(
            "\nFINAL STATUS:",
            manager.status("test"),
        )

        print("\n=== REMOVE ===")

        manager.remove("test")

        print(
            "EXISTS:",
            manager.exists("test"),
        )

        print(
            "REGISTRY EXISTS:",
            registry.exists("test"),
        )


if __name__ == "__main__":
    main()
