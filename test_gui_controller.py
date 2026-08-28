from pathlib import Path
from tempfile import TemporaryDirectory

from master.scraper_registry import ScraperRegistry
from master.process_manager import ProcessManager
from gui.controller import GUIController


def main():

    with TemporaryDirectory() as temp:

        temp = Path(temp)

        registry = ScraperRegistry(
            registry_file=temp / "registry.json"
        )

        manager = ProcessManager(
            registry=registry,
            runtime_dir=temp / "runtime",
        )

        controller = GUIController(
            manager
        )

        print("=== CONTROLLER TEST ===")

        controller.create_scraper(
            name="gui_test",
            providers=["google"],
            target="schools",
            config={
                "keyword": "مدرسه"
            },
        )

        print(
            "COUNT:",
            controller.count()
        )

        print(
            "EXISTS:",
            controller.exists("gui_test")
        )

        print(
            "STATUS:",
            controller.status_text("gui_test")
        )

        print(
            "ROLE:",
            controller.status_role("gui_test")
        )

        print(
            "ACTIONS:",
            controller.available_actions(
                "gui_test"
            )
        )

        print("\n=== START ===")

        controller.start(
            "gui_test"
        )

        print(
            "RUNNING:",
            controller.is_running(
                "gui_test"
            )
        )

        print(
            "STATUS:",
            controller.status_text(
                "gui_test"
            )
        )

        print(
            "PID:",
            controller.get_process(
                "gui_test"
            ).pid
        )

        print("\n=== SNAPSHOT ===")

        print(
            controller.snapshot(
                "gui_test"
            )
        )

        print("\n=== STOP ===")

        controller.stop(
            "gui_test",
            timeout=5,
        )

        print(
            "FINAL:",
            controller.status_text(
                "gui_test"
            )
        )

        print("\n=== REMOVE ===")

        controller.remove(
            "gui_test"
        )

        print(
            "PROCESS EXISTS:",
            controller.exists(
                "gui_test"
            )
        )

        print(
            "REGISTRY EXISTS:",
            registry.exists(
                "gui_test"
            )
        )

        print("\n=== DONE ===")


if __name__ == "__main__":
    main()
