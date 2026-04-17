## ROS2 Analyzer

ROS2 Analyzer scans Python ROS2 node code, extracts publisher/subscriber relationships and provides tools to visualize and fuzz the resulting graph.

### What This Project Does

- Parses Python files for `create_publisher(...)` and `create_subscription(...)` usage.
- Builds a topic-centric communication model:
	- topic -> publishers
	- topic -> subscribers
- Serializes communication/file-entry data to JSON.
- Visualizes communication as an interactive graph in the browser.
- Streams graph updates via WebSocket/HTTP endpoints.
- Fuzzes selected ROS2 nodes by generating randomized ROS message payloads.

### Project Layout

- `main.py`: high-level entry point for scan -> analyze -> fuzz flow.
- `loader.py`: discovers Python files and wraps them as `FileEntry` objects.
- `parser.py`: regex-based publisher/subscriber extraction.
- `file_entry.py`: in-memory representation of one source file and its ROS2 interfaces.
- `file_entry_container.py`: aggregates entries, runs parsers, generates communication JSON.
- `publisher.py` / `subscription.py`: message metadata models.
- `ros2_fuzzer/fuzzer.py`: loads communication JSON and starts fuzzing for target node(s).
- `ros2_fuzzer/fuzzer_node.py`: creates randomized message instances and publishes/subscribes.
- `vis/ros2_graph.html`: interactive graph UI (pan/zoom/selection + settings panel).
- `vis/server.py`: WebSocket + HTTP push server for live graph updates.
- `communication.json`: example communication payload.

### Requirements

This project expects a ROS2-capable Python environment for runtime fuzzing.

Minimum Python packages:

- `pytest` (tests)
- `websockets` (visualization server)

ROS2 runtime requirements (from your ROS2 installation/workspace):

- `rclpy`
- `rosidl_runtime_py`
- message packages used by your graph (for example `std_msgs`, `geometry_msgs`, `sensor_msgs`, `nav_msgs`, custom messages)

Install basic Python tools in your active environment:

```bash
python -m pip install pytest websockets
```

### Quick Start

Run the analyzer from this `src` directory against a codebase of ROS2 Python nodes:

```bash
python main.py /path/to/ros2_ws
```

Current `main.py` flow:

- collects `*.py` files recursively
- parses publisher/subscriber calls
- builds communication JSON
- loads that JSON into the fuzzer
- starts fuzzing node `nav_cmd_publisher`

If your target node is different, change the node name in `main.py` before running.

### Communication JSON Format

Primary output shape (topic-centric):

```json
{
	"/topic/name": {
		"publisher": [
			{
				"name": "node_name",
				"path": "/path/to/node.py",
				"subscriptions": [],
				"publishers": [
					{
						"msg_type": "std_msgs/msg/String",
						"topic": "/topic/name",
						"qos_service_profile": "10"
					}
				]
			}
		],
		"subscriber": [
			{
				"name": "other_node",
				"path": "/path/to/other_node.py",
				"subscriptions": [
					{
						"msg_type": "std_msgs/msg/String",
						"topic": "/topic/name",
						"callback": "self.callback",
						"qos_service_profile": "10"
					}
				],
				"publishers": []
			}
		]
	}
}
```

### Visualization

Start the graph server (from project root):

```bash
python src/vis/server.py --file src/communication.json
```

Then open:

- `http://localhost:8766` (served by `server.py`), or
- open `src/vis/ros2_graph.html` directly and connect to `ws://localhost:8765`

Server features:

- WebSocket broadcast: `http://localhost:8765`
- Optional file watch mode:

```bash
python src/vis/server.py --watch src/communication.json
```

### Fuzzing

`ros2_fuzzer/fuzzer.py` loads communication JSON and registers publishers/subscribers for the chosen node.

Message type resolution supports:

Formats like:
- `std_msgs/msg/String`
- `std_msgs.msg.String`
- short names like `String` (searched across common message packages)

The fuzzer node generates randomized scalar, sequence/array, and nested message fields before publishing.

## Known Limitations

- Parsing is regex-based and focused on straightforward `create_publisher` / `create_subscription` call patterns.
- Dynamic/topic indirection patterns may not be detected.
- `main.py` currently hardcodes a fuzz target node name.
- Fuzzing requires ROS2 environment and available message packages in Python path.
