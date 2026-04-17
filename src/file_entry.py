import pprint
from pathlib import Path
from typing import Any

from publisher import Publisher
from subscription import Subscription


class FileEntry:
    def __init__(self, path: Path) -> None:
        self.__path: Path = path
        self.__subscriptions: list[Subscription] = []
        self.__publishers: list[Publisher] = []

    def get_path(self) -> Path:
        return self.__path

    def get_subscriptions(self) -> list[Subscription]:
        return self.__subscriptions

    def get_publishers(self) -> list[Publisher]:
        return self.__publishers

    def get_name(self) -> str:
        return str(self.__path.name.split(".")[0])

    def add(self, entry: Subscription | Publisher) -> None:
        if isinstance(entry, Subscription):
            self.__add_subscription(entry)
        elif isinstance(entry, Publisher):
            self.__add_publisher(entry)
        else:
            raise TypeError(f"Expected Subscription or Publisher but got {type(entry)}")

    def __add_subscription(self, subscription: Subscription) -> None:
        assert isinstance(
            subscription, Subscription
        ), f"Expected subscription to be of type Subscription. Got: {type(subscription)}"
        self.__subscriptions.append(subscription)

    def __add_publisher(self, publisher: Publisher) -> None:
        assert isinstance(publisher, Publisher), f"Expected publisher to be of type Publisher. Got: {type(publisher)}"
        self.__publishers.append(publisher)

    def __str__(self):
        """_summary_

        Returns:
            _type_: _description_
        """
        return (
            f"{self.__path}"
            f"\n{pprint.pformat([str(sub) for sub in self.__subscriptions])}"
            f"\n\n"
            f"{pprint.pformat([str(pub) for pub in self.__publishers])}"
        )

    def __eq__(self, value: object, /) -> bool:
        """_summary_

        Args:
            value (object): _description_

        Returns:
            bool: _description_
        """
        if not isinstance(value, FileEntry):
            return False

        if self.__path != value.__path:
            return False
        if len(self.__subscriptions) != len(value.__subscriptions):
            return False
        if any(x != y for x, y in zip(self.__subscriptions, value.__subscriptions)):
            return False
        if any(x != y for x, y in zip(self.__publishers, value.__publishers)):
            return False
        return True

    def to_dict(self) -> dict[str, Any]:
        subscriptions = [subscription.to_dict() for subscription in self.__subscriptions]
        publishers = [publisher.to_dict() for publisher in self.__publishers]
        return {
            "name": self.get_name(),
            "path": str(self.__path),
            "subscriptions": subscriptions,
            "publishers": publishers,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FileEntry":
        file_entry = cls(path=Path(str(data["path"])))
        for subscription_data in data.get("subscriptions", []):
            file_entry.add(Subscription.from_dict(subscription_data))
        for publisher_data in data.get("publishers", []):
            file_entry.add(Publisher.from_dict(publisher_data))
        return file_entry
