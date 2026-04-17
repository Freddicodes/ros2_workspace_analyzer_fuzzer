import json
import random
import string
from pathlib import Path

import pytest

from file_entry import FileEntry
from file_entry_container import FileEntryContainer
from publisher import Publisher
from subscription import Subscription


# Source - https://stackoverflow.com/a/2257449
# Posted by Ignacio Vazquez-Abrams, modified by community. See post 'Timeline' for change history
# Retrieved 2026-04-17, License - CC BY-SA 4.0
def random_str(n: int = 5) -> str:
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=n))


def test_serialize_deserialize() -> None:
    a = FileEntryContainer()

    a.add_file_entries(
        [
            FileEntry(Path(random_str())),
            FileEntry(Path(random_str())),
            FileEntry(Path(random_str())),
            FileEntry(Path(random_str())),
            FileEntry(Path(random_str())),
        ]
    )

    json_s = a.serialize()
    b = FileEntryContainer()
    b.add_file_entries(FileEntryContainer.deserialize(json_s))

    assert a == b


def test_print() -> None:
    a = FileEntryContainer()

    a.add_file_entries(
        [
            FileEntry(Path(random_str())),
            FileEntry(Path(random_str())),
            FileEntry(Path(random_str())),
            FileEntry(Path(random_str())),
            FileEntry(Path(random_str())),
        ]
    )

    test_str = str(a)
    assert len(test_str) > 0


def test_file_entry_to_dict_is_json_serializable() -> None:
    file_entry = FileEntry(Path("node.py"))
    file_entry.add(Publisher("String", "/chatter", "10"))
    file_entry.add(Subscription("String", "/chatter", "on_chatter", "10"))

    serialized = file_entry.to_dict()

    assert isinstance(serialized["publishers"], list)
    assert isinstance(serialized["subscriptions"], list)
    assert serialized["publishers"][0]["topic"] == "/chatter"
    assert serialized["subscriptions"][0]["callback"] == "on_chatter"
    json.dumps(serialized)


def test_get_communication_groups_publishers_and_subscribers() -> None:
    pub_only = FileEntry(Path("publisher_node.py"))
    pub_only.add(Publisher("String", "/topic_a", "10"))

    sub_only = FileEntry(Path("subscriber_node.py"))
    sub_only.add(Subscription("String", "/topic_a", "on_topic_a", "10"))

    both = FileEntry(Path("bridge_node.py"))
    both.add(Publisher("String", "/topic_b", "10"))
    both.add(Subscription("String", "/topic_b", "on_topic_b", "10"))

    container = FileEntryContainer()
    container.add_file_entries([pub_only, sub_only, both])

    communication = container.get_communication()

    assert set(communication.keys()) == {"/topic_a", "/topic_b"}
    assert communication["/topic_a"]["publisher"] == [pub_only]
    assert communication["/topic_a"]["subscriber"] == [sub_only]
    assert communication["/topic_b"]["publisher"] == [both]
    assert communication["/topic_b"]["subscriber"] == [both]


def test_get_communication_json_returns_valid_json() -> None:
    pub = FileEntry(Path("publisher.py"))
    pub.add(Publisher("String", "/status", "10"))

    sub = FileEntry(Path("subscriber.py"))
    sub.add(Subscription("String", "/status", "on_status", "10"))

    container = FileEntryContainer()
    container.add_file_entries([pub, sub])

    payload = container.get_communication_json(indent=2)
    data = json.loads(payload)

    assert "/status" in data
    assert len(data["/status"]["publisher"]) == 1
    assert len(data["/status"]["subscriber"]) == 1
    assert data["/status"]["publisher"][0]["path"] == "publisher.py"
    assert data["/status"]["subscriber"][0]["path"] == "subscriber.py"


def test_deserialize_requires_top_level_array() -> None:
    with pytest.raises(ValueError, match="Expected top-level JSON array"):
        FileEntryContainer.deserialize('{"path": "node.py"}')
