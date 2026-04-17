from __future__ import annotations

import importlib
import threading
from pathlib import Path
from time import sleep
from typing import Any

import rclpy

try:
    from ros2_fuzzer.fuzzer_node import FuzzerNode
except ImportError:
    from fuzzer_node import FuzzerNode


class Fuzzer:
    _COMMON_MSG_PACKAGES = ("std_msgs", "geometry_msgs", "sensor_msgs", "nav_msgs", "builtin_interfaces", "quad_msgs")

    def __init__(self) -> None:
        self.__data: dict[str, dict[str, list[dict[str, Any]]]] = {}
        self._threads: list[threading.Thread] = []

        rclpy.init()

    def load(self, data: str):
        import json

        self.load_data(json.loads(data))

    def load_data(self, data: dict[str, dict[str, list[dict[str, Any]]]]) -> None:
        # Take input from this method:
        # def get_communication(self) -> dict[str, dict[str, list[FileEntry]]]:
        # Return [
        #     "topic": {
        #         "publisher": [...]
        #         "subscriber": [...]
        #     }, ...
        # ]

        self.__data = data

    def _load_msg_class(self, data_type: str) -> Any:
        """
        Resolve a ROS message class from a type string.

        Supported formats:
        - std_msgs/msg/String
        - std_msgs.msg.String
        - String (searched in common ROS message packages)
        """
        if "/" in data_type:
            from rosidl_runtime_py.utilities import get_message

            return get_message(data_type)

        if data_type.count(".") >= 2:
            package, _, msg_name = data_type.rpartition(".")
            module = importlib.import_module(package)
            return getattr(module, msg_name)

        for package in self._COMMON_MSG_PACKAGES:
            module = importlib.import_module(f"{package}.msg")
            if hasattr(module, data_type):
                return getattr(module, data_type)

        raise ValueError(
            f"Could not resolve message type '{data_type}'. " "Use a fully-qualified type like 'std_msgs/msg/String'."
        )

    @staticmethod
    def _entry_matches_node_name(entry: dict[str, Any], node_name: str) -> bool:
        entry_name = str(entry.get("name", ""))
        if entry_name == node_name:
            return True

        path = str(entry.get("path", ""))
        if path and Path(path).stem == node_name:
            return True

        return False

    @staticmethod
    def _extract_msg_type_for_topic(entry: dict[str, Any], topic: str, direction: str) -> str | None:
        if direction == "publisher":
            items = entry.get("publishers", [])
        else:
            items = entry.get("subscriptions", [])

        for item in items:
            if item.get("topic") == topic:
                return str(item.get("msg_type"))

        return None

    def fuzz_node(self, node_name: str) -> None:
        node = FuzzerNode(node_name)
        for topic, comm in self.__data.items():
            for publisher_entry in comm.get("publisher", []):
                if self._entry_matches_node_name(publisher_entry, node_name):
                    msg_type_str = self._extract_msg_type_for_topic(publisher_entry, topic, "publisher")
                    if msg_type_str:
                        msg_class = self._load_msg_class(msg_type_str)
                        node.register_publisher(topic, msg_class)
                    else:
                        print(f"Could not find message type for publisher entry '{publisher_entry}' on topic '{topic}'")

            for subscriber_entry in comm.get("subscriber", []):
                if self._entry_matches_node_name(subscriber_entry, node_name):
                    msg_type_str = self._extract_msg_type_for_topic(subscriber_entry, topic, "subscriber")
                    if msg_type_str:
                        msg_class = self._load_msg_class(msg_type_str)
                        node.register_subscription(topic, msg_class)
                    else:
                        print(
                            f"Could not find message type for subscriber entry '{subscriber_entry}' on topic '{topic}'"
                        )

        node.start()
        thread = threading.Thread(target=rclpy.spin, args=(node,), daemon=True)
        thread.start()
        self._threads.append(thread)

    def shutdown(self) -> None:
        rclpy.shutdown()
        for thread in self._threads:
            thread.join()


if __name__ == "__main__":
    fuzzer = Fuzzer()
    fuzzer._Fuzzer__data = {
        "/chatter": {
            "publisher": [
                {
                    "name": "example_node",
                    "path": "/path/to/talker_node.py",
                    "subscriptions": [],
                    "publishers": [
                        {
                            "topic": "/chatter",
                            "msg_type": "std_msgs/msg/String",
                        }
                    ],
                }
            ],
            "subscriber": [
                {
                    "name": "listener_node",
                    "path": "/path/to/listener_node.py",
                    "msg_type": "std_msgs/msg/String",
                }
            ],
        }
    }
    fuzzer.fuzz_node("example_node")
    sleep(10)
    fuzzer.shutdown()
