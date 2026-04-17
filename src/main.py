import sys
from pathlib import Path
from time import sleep

from file_entry_container import FileEntryContainer
from loader import get_py_files, parse_to_file_entry
from ros2_fuzzer.fuzzer import Fuzzer


def main_2():
    fuzzer = Fuzzer()
    print(fuzzer._load_msg_class("Battery"))


def main():

    source_path = sys.argv[1]
    input_path = Path(source_path)
    files = get_py_files(input_path)
    file_entries = parse_to_file_entry(files)

    container = FileEntryContainer()
    container.add_file_entries(file_entries)
    container.analyze()

    json_data = container.get_communication_json()

    fuzzer = Fuzzer()
    fuzzer.load(json_data)

    fuzzer.fuzz_node("nav_cmd_publisher")
    sleep(10)
    fuzzer.shutdown()


if __name__ == "__main__":
    main()
    # main_2()
