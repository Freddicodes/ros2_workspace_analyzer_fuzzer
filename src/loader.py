from pathlib import Path

from file_entry import FileEntry


def get_py_files(path: Path) -> list[Path]:
    return_list: list[Path] = []
    for path in path.rglob("*.py"):
        return_list.append(path)
    return return_list


def parse_to_file_entry(paths: list[Path]) -> list[FileEntry]:
    file_entries: list[FileEntry] = []
    for path in paths:
        file_entry = FileEntry(path)
        file_entries.append(file_entry)
    return file_entries
