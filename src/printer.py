import json


class Printer:
    @staticmethod
    def format(json_string: str) -> None:
        json_obj = json.loads(json_string)
        print(json_obj)
