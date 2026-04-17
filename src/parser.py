from typing import override, Iterator, Iterable

from file_entry import FileEntry
import re

from publisher import Publisher
from subscription import Subscription


class Parser:
    def __init__(self) -> None:
        pass

    def parse(self, file_entries: list[FileEntry]) -> None:
        raise NotImplementedError()


class SubscriptionParser(Parser):
    pattern: re.Pattern = re.compile(r"create_subscription\((\w+) *, *[\'\"]([/\w_]+)[\'\"] *, *([\w.]+) *, *(\d+)\)")

    def __init__(self) -> None:
        super().__init__()

    @override
    def parse(self, file_entries: Iterable[FileEntry]) -> None:
        for file_entry in file_entries:
            with file_entry.get_path().open() as f:
                content = f.read()
                matches: Iterator[re.Match] = self.pattern.finditer(content)
                for match in matches:
                    file_entry.add(
                        Subscription(
                            msg_type=match.group(1),
                            topic=match.group(2),
                            callback=match.group(3),
                            qos_service_profile=match.group(4),
                        )
                    )


class PublisherParser(Parser):
    pattern: re.Pattern = re.compile(r"create_publisher\((\w+) *, *[\'\"]([/\w_]+)[\'\"] *, *(\d+)\)")

    def __init__(self) -> None:
        super().__init__()

    @override
    def parse(self, file_entries: Iterable[FileEntry]) -> None:
        for file_entry in file_entries:
            with file_entry.get_path().open() as f:
                content = f.read()
                matches: Iterator[re.Match] = self.pattern.finditer(content)
                for match in matches:
                    msg_type = match.group(1)
                    topic = match.group(2)
                    qos_service_profile = match.group(3)
                    publisher = Publisher(msg_type, topic, qos_service_profile)
                    file_entry.add(publisher)
