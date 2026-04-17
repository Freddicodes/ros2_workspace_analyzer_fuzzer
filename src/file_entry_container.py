import json
from parser import PublisherParser, SubscriptionParser
from pathlib import Path
from pprint import pp
from typing import Optional

from file_entry import FileEntry


class FileEntryContainer:
    subscription_parser = SubscriptionParser()
    publisher_parser = PublisherParser()

    def __init__(self):
        self.__file_entries: list[FileEntry] = []

    def add_file_entry(self, file_entry: FileEntry):
        self.__file_entries.append(file_entry)

    def add_file_entries(self, file_entries: list[FileEntry]):
        print(f"Adding {len(file_entries)} file entries to container")
        for file_entry in file_entries:
            self.add_file_entry(file_entry)

    def remove_file_entry(self, file_entry: FileEntry):
        self.__file_entries.remove(file_entry)

    def get_file_entries(self) -> list[FileEntry]:
        return self.__file_entries

    def get_file_entry_by_index(self, index: int) -> Optional[FileEntry]:
        if index >= len(self.__file_entries):
            return None
        return self.__file_entries[index]

    def get_file_entry_by_path(self, path: Path) -> tuple[bool, Optional[FileEntry]]:
        for file_entry in self.__file_entries:
            if file_entry.get_path() == path:
                return True, file_entry
        return False, None

    def get_communication(self) -> dict[str, dict[str, list[FileEntry]]]:
        """
        Return [
            "topic": {
                "publisher": [...]
                "subscriber": [...]
            }, ...
        ]
        """

        communication_pairs: dict[str, dict[str, list]] = {}

        for file_entry in self.__file_entries:
            for publisher in file_entry.get_publishers():
                topic = publisher.get_topic()
                if topic not in communication_pairs:
                    communication_pairs[topic] = {"publisher": [], "subscriber": []}
                communication_pairs[topic]["publisher"].append(file_entry)

            for subscription in file_entry.get_subscriptions():
                topic = subscription.get_topic()
                if topic not in communication_pairs:
                    communication_pairs[topic] = {"publisher": [], "subscriber": []}
                communication_pairs[topic]["subscriber"].append(file_entry)

        return communication_pairs

    def get_communication_json(self, indent: int = 2) -> str:
        communication = self.get_communication()
        serializable_communication = {}
        for topic, comm in communication.items():
            serializable_communication[topic] = {
                "publisher": [pub.to_dict() for pub in comm["publisher"]],
                "subscriber": [sub.to_dict() for sub in comm["subscriber"]],
            }
        pp(serializable_communication)
        return json.dumps(serializable_communication, indent=indent, ensure_ascii=False)

    def serialize(self, indent: int = 2) -> str:
        serialized = [file_entry.to_dict() for file_entry in self.__file_entries]
        return json.dumps(serialized, indent=indent, ensure_ascii=False)

    def analyze(self) -> None:
        self.subscription_parser.parse(self.__file_entries)
        self.publisher_parser.parse(self.__file_entries)

    @staticmethod
    def deserialize(payload: str) -> list[FileEntry]:
        raw_entries = json.loads(payload)
        if not isinstance(raw_entries, list):
            raise ValueError("Expected top-level JSON array")
        return [FileEntry.from_dict(entry) for entry in raw_entries]

    def __eq__(self, value: object) -> bool:
        """_summary_

        Args:
            value (object): _description_

        Returns:
            bool: _description_
        """
        if not isinstance(value, FileEntryContainer):
            return False
        if len(self.__file_entries) != len(value.__file_entries):
            return False
        if any(x != y for x, y in zip(self.__file_entries, value.__file_entries)):
            return False
        return True
