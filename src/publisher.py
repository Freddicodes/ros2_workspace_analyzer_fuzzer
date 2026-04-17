from typing import Any


class Publisher:
    def __init__(self, msg_type: str, topic: str, qos_service_profile: str) -> None:
        self.__msg_type = msg_type
        self.__topic = topic
        self.__qos_service_profile = qos_service_profile

    def get_msg_type(self) -> str:
        return self.__msg_type

    def get_topic(self) -> str:
        return self.__topic

    def get_qos_service_profile(self) -> str:
        return self.__qos_service_profile

    def __str__(self):
        return f"{self.__msg_type} {self.__topic} {self.__qos_service_profile}"

    def __eq__(self, value: object) -> bool:
        if not isinstance(value, Publisher):
            return False
        if self.__msg_type != value.__msg_type:
            return False
        if self.__topic != value.__topic:
            return False
        if self.__qos_service_profile != value.__qos_service_profile:
            return False
        return True

    def to_dict(self) -> dict[str, str]:
        return {"msg_type": self.__msg_type, "topic": self.__topic, "qos_service_profile": self.__qos_service_profile}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Publisher":
        return cls(
            msg_type=str(data["msg_type"]),
            topic=str(data["topic"]),
            qos_service_profile=str(data["qos_service_profile"]),
        )
