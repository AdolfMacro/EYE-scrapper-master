from master.master import Master
from gui import start_gui


def main() -> int:

    master = Master()

    return start_gui(
        manager=master.process_manager
    )


if __name__ == "__main__":

    raise SystemExit(
        main()
    )