import random
import re
import string
from typing import Any

import rclpy
from quad_msgs.msg import Battery
from rclpy.node import Node, Publisher, Subscription


class RandomSource:

    def random_str(self, length: int = 10) -> str:
        return "".join(random.choices(string.ascii_letters + string.digits, k=length))

    def random_float(self, min_value: float = 0.0, max_value: float = 100.0) -> float:
        return random.uniform(min_value, max_value)

    def random_int(self, min_value: int = 0, max_value: int = 100) -> int:
        return random.randint(min_value, max_value)

    def random_list_of_str(self, list_length: int = 5, str_length: int = 10) -> list[str]:
        return [self.random_str(str_length) for _ in range(list_length)]

    def random_list_of_float(
        self, list_length: int = 5, min_value: float = 0.0, max_value: float = 100.0
    ) -> list[float]:
        return [self.random_float(min_value, max_value) for _ in range(list_length)]

    def random_list_of_int(self, list_length: int = 5, min_value: int = 0, max_value: int = 100) -> list[int]:
        return [self.random_int(min_value, max_value) for _ in range(list_length)]


class FuzzerNode(Node):

    rand_source = RandomSource()

    def __init__(self, node_name: str):
        super().__init__(node_name)
        self._registered_publishers: list[Publisher] = []
        self._registered_subscriptions: list[Subscription] = []

    def register_publisher(self, topic: str, data_type: object) -> None:
        self._registered_publishers.append(self.create_publisher(data_type, topic, 10))

    def register_subscription(self, topic: str, data_type: object) -> None:
        self._registered_subscriptions.append(self.create_subscription(data_type, topic, lambda _msg: print(_msg), 10))

    def _random_scalar_value(self, ros_type: str) -> Any | None:
        ros_type = ros_type.strip()

        if ros_type in {"string", "wstring"}:
            return self.rand_source.random_str()
        if ros_type in {"bool", "boolean"}:
            return bool(self.rand_source.random_int(0, 1))
        if ros_type in {"float32", "float64", "float", "double"}:
            return self.rand_source.random_float(-100.0, 100.0)
        if ros_type.startswith("int"):
            return self.rand_source.random_int(-100, 100)
        if ros_type.startswith("uint"):
            return self.rand_source.random_int(0, 100)
        if ros_type in {"byte", "char", "octet"}:
            return self.rand_source.random_int(0, 255)

        return None

    def _parse_collection_type(self, value_type: str) -> tuple[str, int | None] | None:
        # Handles fixed arrays and bounded/unbounded sequences.
        # Examples:
        # - float64[3]
        # - sequence<int32>
        # - sequence<string, 10>
        fixed = re.fullmatch(r"(.+)\[(\d+)\]", value_type)
        if fixed:
            return fixed.group(1).strip(), int(fixed.group(2))

        seq = re.fullmatch(r"sequence<\s*([^,>]+)\s*(?:,\s*(\d+))?\s*>", value_type)
        if seq:
            element_type = seq.group(1).strip()
            bound = int(seq.group(2)) if seq.group(2) else None
            return element_type, bound

        return None

    def _random_value_for_type(self, field_name: str, value_type: str, instance: object) -> Any:
        clean_type = value_type.split("<=", 1)[0].strip()

        collection = self._parse_collection_type(clean_type)
        if collection is not None:
            element_type, bound = collection
            list_size = min(bound if bound is not None else 3, 3)
            return [self._random_value_for_type(field_name, element_type, instance) for _ in range(list_size)]

        scalar_value = self._random_scalar_value(clean_type)
        if scalar_value is not None:
            return scalar_value

        # Nested ROS message type, for example std_msgs/Header.
        if "/" in clean_type:
            nested = getattr(instance, field_name, None)
            if nested is not None:
                self._populate_msg_instance(nested)
                return nested

        raise ValueError(f"Unsupported field type '{value_type}' for field '{field_name}'")

    def _populate_msg_instance(self, instance: object) -> None:
        if not hasattr(instance, "get_fields_and_field_types"):
            return

        fields = instance.get_fields_and_field_types()
        for key, value_type in fields.items():
            try:
                value = self._random_value_for_type(key, value_type, instance)
                setattr(instance, key, value)
            except ValueError as exc:
                print(f"{exc} in message type '{type(instance)}'. Skipping field.")

    def _create_msg(self, data_type: object) -> object:

        if not hasattr(data_type, "_fields_and_field_types"):
            raise ValueError(
                f"Data type '{data_type}' does not have '_fields_and_field_types' attribute. Cannot create message instance."
            )

        instance = data_type()
        self._populate_msg_instance(instance)
        return instance

    def _timer_callback(self) -> None:
        for pub in self._registered_publishers:
            msg = self._create_msg(pub.msg_type)
            print(f"Publishing message on topic '{pub.topic_name}': {msg}")
            pub.publish(msg)

    def start(self) -> None:
        assert len(self._registered_publishers) > 0, "No publishers registered. Cannot start fuzzer node."
        self.create_timer(1.0, self._timer_callback)


if __name__ == "__main__":
    rclpy.init()
    node = FuzzerNode("fuzzing_node")
    node.register_publisher("/battery", Battery)
    node.start()
    rclpy.spin(node)
