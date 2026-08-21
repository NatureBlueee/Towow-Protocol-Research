#!/usr/bin/env python3
"""Stateful Docker CLI test double used only by runner tests."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import pathlib
import sys
import time


FINAL_ID = "sha256:" + "1" * 64
BASE_ID = "sha256:" + "2" * 64
BASE_DIGEST = "node@sha256:" + "3" * 64
READY_FRAME = b"WAVE025_SUPERVISOR_READY_V1\n"


def canonical_bytes(value) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def directory_tree(path: pathlib.Path) -> dict:
    root_info = path.lstat()
    entries = [
        {
            "mode_octal": f"0o{root_info.st_mode & 0o7777:04o}",
            "path": ".",
            "size_bytes": str(root_info.st_size),
            "type": "directory",
        }
    ]
    for child in sorted(path.iterdir(), key=lambda item: item.name):
        info = child.lstat()
        entries.append(
            {
                "mode_octal": f"0o{info.st_mode & 0o7777:04o}",
                "path": child.name,
                "size_bytes": str(info.st_size),
                "type": (
                    "symlink" if child.is_symlink()
                    else "file" if child.is_file()
                    else "directory" if child.is_dir()
                    else "other"
                ),
            }
        )
    return {"available": True, "entries": entries, "errors": [], "truncated": False}


def collector_feature_bytes(value: dict) -> bytes:
    working_dir = value["Config"]["WorkingDir"]
    document = {
        "cwd": working_dir,
        "directory_trees": {},
        "schema": "WAVE025_LEAK_ONLY_FEATURES_V1",
        "visible_canaries": [],
    }
    if working_dir == "/shared-residue":
        residue = pathlib.Path(next(
            item["Source"] for item in value["Mounts"]
            if item["Destination"] == "/shared-residue"
        ))
        document["directory_trees"]["cwd"] = directory_tree(residue)
    challenge = pathlib.Path(next(
        item["Source"] for item in value["Mounts"] if item["Destination"] == "/challenge"
    ))
    document["directory_trees"]["challenge"] = directory_tree(challenge)
    for child in sorted(challenge.glob("WAVE025_CANARY_D1_CURRENT_*.txt")):
        token = child.read_text(encoding="utf-8").strip()
        document["visible_canaries"].extend(
            [
                {
                    "location": child.name,
                    "source": "challenge-entry-name",
                    "token_byte_length": len(token.encode("utf-8")),
                    "token_sha256": hashlib.sha256(token.encode("utf-8")).hexdigest(),
                },
                {
                    "location": child.name,
                    "source": "challenge-file-content",
                    "token_byte_length": len(token.encode("utf-8")),
                    "token_sha256": hashlib.sha256(token.encode("utf-8")).hexdigest(),
                },
            ]
        )
    return canonical_bytes(document)


def state_root() -> pathlib.Path:
    value = os.environ.get("FAKE_DOCKER_STATE")
    if not value:
        raise SystemExit("FAKE_DOCKER_STATE is required")
    root = pathlib.Path(value)
    root.mkdir(parents=True, exist_ok=True)
    return root


def state_path(name: str) -> pathlib.Path:
    return state_root() / (hashlib.sha256(name.encode()).hexdigest() + ".json")


def save(value: dict) -> None:
    state_path(value["Name"].lstrip("/")).write_text(json.dumps(value), encoding="utf-8")


def load(name: str) -> dict:
    path = state_path(name)
    if not path.exists():
        print(f"Error: No such container: {name}", file=sys.stderr)
        raise SystemExit(1)
    return json.loads(path.read_text(encoding="utf-8"))


def load_by_id(container_id: str) -> dict:
    for path in state_root().glob("*.json"):
        value = json.loads(path.read_text(encoding="utf-8"))
        if value.get("Id") == container_id:
            return value
    print(f"Error: No such container id: {container_id}", file=sys.stderr)
    raise SystemExit(1)


def append_event(
    value: dict,
    action: str,
    *,
    exec_id: str | None = None,
    exit_code: str | None = None,
    signal: str | None = None,
) -> None:
    attributes = {
        "image": value["Image"],
        "name": value["Name"].lstrip("/"),
        **(value.get("Config", {}).get("Labels") or {}),
    }
    if exec_id is not None:
        attributes["execID"] = exec_id
    if exit_code is not None:
        attributes["exitCode"] = exit_code
    if signal is not None:
        attributes["signal"] = signal
    timestamp = time.time_ns()
    value["Fake"]["events"].append(
        {
            "Type": "container",
            "Action": action,
            "Actor": {"ID": value["Id"], "Attributes": attributes},
            "scope": "local",
            "time": timestamp // 1_000_000_000,
            "timeNano": timestamp,
        }
    )


def option_values(arguments: list[str], key: str) -> list[str]:
    values = []
    index = 0
    while index < len(arguments):
        if arguments[index] == key:
            values.append(arguments[index + 1])
            index += 2
        else:
            index += 1
    return values


def option_value(arguments: list[str], key: str, default=None):
    values = option_values(arguments, key)
    return values[-1] if values else default


def image_inspect(reference: str) -> None:
    if reference in {"node:20-slim", BASE_ID, BASE_DIGEST}:
        value = {"Id": BASE_ID, "RepoDigests": [BASE_DIGEST]}
    else:
        value = {"Id": FINAL_ID, "RepoDigests": []}
    print(json.dumps([value], separators=(",", ":")))


def parse_mount(raw: str) -> dict:
    parts = raw.split(",")
    values = {}
    flags = set()
    for part in parts:
        if "=" in part:
            key, value = part.split("=", 1)
            values[key] = value
        else:
            flags.add(part)
    return {
        "Type": values.get("type"),
        "Source": values.get("src", ""),
        "Destination": values.get("dst"),
        "RW": "readonly" not in flags,
        "Mode": "ro" if "readonly" in flags else "rw",
        "Propagation": "rprivate",
    }


def create(arguments: list[str]) -> None:
    name = option_value(arguments, "--name")
    labels = {}
    for item in option_values(arguments, "--label"):
        key, value = item.split("=", 1)
        labels[key] = value
    mounts = [parse_mount(item) for item in option_values(arguments, "--mount")]
    tmpfs = {}
    for item in option_values(arguments, "--tmpfs"):
        destination, _, options = item.partition(":")
        tmpfs[destination] = options
    image_index = next(
        index for index, value in enumerate(arguments) if value in {FINAL_ID, BASE_ID}
    )
    command = arguments[image_index + 1 :]
    predecessor = labels.get("org.towow.wave025.owner") == "runner-v1-predecessor"
    container_id = hashlib.sha256(name.encode()).hexdigest()
    value = {
        "Id": container_id,
        "Name": "/" + name,
        "Image": FINAL_ID,
        "Created": "2026-08-01T00:00:00.000000000Z",
        "Config": {
            "Labels": labels,
            "Entrypoint": [option_value(arguments, "--entrypoint", "/bin/sh")],
            "Cmd": command,
            "Env": ["PATH=/usr/local/bin:/usr/bin:/bin", "NODE_VERSION=20"],
            "WorkingDir": option_value(arguments, "--workdir", "/app"),
            "User": option_value(arguments, "--user", ""),
            "Hostname": option_value(arguments, "--hostname", name[:63]),
        },
        "HostConfig": {
            "NetworkMode": option_value(arguments, "--network", "default"),
            "ReadonlyRootfs": "--read-only" in arguments,
            "CapDrop": option_values(arguments, "--cap-drop"),
            "SecurityOpt": option_values(arguments, "--security-opt"),
            "PidMode": option_value(arguments, "--pid", ""),
            "IpcMode": option_value(arguments, "--ipc", ""),
            "UTSMode": option_value(arguments, "--uts", ""),
            "UsernsMode": option_value(arguments, "--userns", ""),
            "PidsLimit": int(option_value(arguments, "--pids-limit", "0")),
            "Memory": int(option_value(arguments, "--memory", "0")),
            "NanoCpus": int(float(option_value(arguments, "--cpus", "0")) * 1_000_000_000),
            "Tmpfs": tmpfs,
        },
        "Mounts": mounts,
        "State": {
            "Running": False,
            "ExitCode": 0,
            "OOMKilled": False,
            "Error": "",
            "StartedAt": "0001-01-01T00:00:00Z",
            "FinishedAt": "0001-01-01T00:00:00Z",
        },
        "Fake": {
            "predecessor": predecessor,
            "collector_stdout_b64": None,
            "collector_stderr_b64": None,
            "features_b64": None,
            "control_stdout_b64": None,
            "control_stderr_b64": None,
            "ready_b64": None,
            "exit_code_b64": None,
            "exec_counter": 0,
            "events": [],
        },
    }
    append_event(value, "create")
    save(value)
    print(container_id)


def start(arguments: list[str]) -> None:
    name = arguments[-1]
    value = load(name)
    value["State"].update(
        {
            "Running": not value["Fake"]["predecessor"],
            "ExitCode": 0,
            "StartedAt": "2026-08-01T00:00:01.000000000Z",
            "FinishedAt": (
                "2026-08-01T00:00:02.000000000Z"
                if value["Fake"]["predecessor"]
                else "0001-01-01T00:00:00Z"
            ),
        }
    )
    if value["Fake"]["predecessor"]:
        marker_basename = value["Config"]["Cmd"][-1]
        residue = next(
            item["Source"] for item in value["Mounts"] if item["Destination"] == "/shared-residue"
        )
        marker = pathlib.Path(residue, marker_basename)
        marker.write_bytes(b"")
        marker.chmod(0o400)
        output = b""
    else:
        output = READY_FRAME
        feature_bytes = collector_feature_bytes(value)
        value["Fake"]["collector_stdout_b64"] = base64.b64encode(feature_bytes).decode("ascii")
        value["Fake"]["collector_stderr_b64"] = base64.b64encode(b"").decode("ascii")
        value["Fake"]["features_b64"] = base64.b64encode(feature_bytes).decode("ascii")
        value["Fake"]["control_stdout_b64"] = base64.b64encode(READY_FRAME).decode("ascii")
        value["Fake"]["control_stderr_b64"] = base64.b64encode(b"").decode("ascii")
        value["Fake"]["ready_b64"] = base64.b64encode(b"READY\n").decode("ascii")
        value["Fake"]["exit_code_b64"] = base64.b64encode(b"0\n").decode("ascii")
    append_event(value, "start")
    save(value)
    if value["Fake"]["predecessor"]:
        sys.stdout.buffer.write(output)
    else:
        print(name)


def exec_read(arguments: list[str]) -> None:
    if arguments[:3] != ["exec", "--user", "65534:65534"]:
        print("fake docker only accepts frozen non-root exec", file=sys.stderr)
        raise SystemExit(1)
    name = arguments[3]
    value = load(name)
    if not value["State"]["Running"]:
        print("container is not running", file=sys.stderr)
        raise SystemExit(1)
    if arguments[4] != "/bin/cat" or len(arguments) != 6:
        print("fake docker only accepts exact /bin/cat reads", file=sys.stderr)
        raise SystemExit(1)
    remote = arguments[5]
    if remote == "/out/collector-ready":
        payload = value["Fake"].get("ready_b64")
    elif remote == "/out/collector-exit-code":
        payload = value["Fake"].get("exit_code_b64")
    elif remote == "/out/collector-stdout":
        payload = value["Fake"].get("collector_stdout_b64")
    elif remote == "/out/collector-stderr":
        payload = value["Fake"].get("collector_stderr_b64")
    elif remote == "/out/leak-features.json":
        payload = value["Fake"].get("features_b64")
    else:
        print("path is not in frozen extraction allowlist", file=sys.stderr)
        raise SystemExit(1)
    if payload is None:
        raise SystemExit(1)
    value["Fake"]["exec_counter"] += 1
    exec_id = hashlib.sha256(
        f"{name}:{value['Fake']['exec_counter']}:{remote}".encode()
    ).hexdigest()
    command = f"/bin/cat {remote}"
    append_event(value, f"exec_create: {command}", exec_id=exec_id)
    append_event(value, f"exec_start: {command}", exec_id=exec_id)
    append_event(value, "exec_die", exec_id=exec_id, exit_code="0")
    save(value)
    sys.stdout.buffer.write(base64.b64decode(payload))


def stop_with_term(name: str) -> None:
    value = load(name)
    if not value["State"]["Running"]:
        print("container is not running", file=sys.stderr)
        raise SystemExit(1)
    value["State"].update(
        {
            "Running": False,
            "ExitCode": 0,
            "FinishedAt": "2026-08-01T00:00:03.000000000Z",
        }
    )
    append_event(value, "kill", signal="15")
    append_event(value, "die", exit_code="0")
    save(value)
    print(name)


def emit_events(arguments: list[str]) -> None:
    filter_value = option_value(arguments, "--filter", "")
    if not filter_value.startswith("container="):
        print("fake docker requires exact container filter", file=sys.stderr)
        raise SystemExit(1)
    value = load_by_id(filter_value.split("=", 1)[1])
    for event in value["Fake"]["events"]:
        print(json.dumps(event, separators=(",", ":")))


def main() -> int:
    arguments = sys.argv[1:]
    if arguments[:2] == ["image", "inspect"]:
        image_inspect(arguments[2])
    elif arguments and arguments[0] == "version":
        print(
            json.dumps(
                {
                    "Client": {"Version": "fake-1", "ApiVersion": "1.0"},
                    "Server": {
                        "Version": "fake-1",
                        "ApiVersion": "1.0",
                        "Os": "linux",
                        "Arch": "arm64",
                    },
                },
                separators=(",", ":"),
            )
        )
    elif arguments and arguments[0] == "create":
        create(arguments)
    elif arguments and arguments[0] == "inspect":
        print(json.dumps([load(arguments[1])], separators=(",", ":")))
    elif arguments and arguments[0] == "start":
        start(arguments)
    elif arguments and arguments[0] == "logs":
        value = load(arguments[1])
        sys.stdout.buffer.write(base64.b64decode(value["Fake"]["control_stdout_b64"] or ""))
        sys.stderr.buffer.write(base64.b64decode(value["Fake"]["control_stderr_b64"] or ""))
    elif arguments and arguments[0] == "exec":
        exec_read(arguments)
    elif arguments and arguments[0] == "kill":
        stop_with_term(arguments[-1])
    elif arguments and arguments[0] == "wait":
        value = load(arguments[1])
        print(value["State"]["ExitCode"])
    elif arguments and arguments[0] == "events":
        emit_events(arguments)
    elif arguments and arguments[0] == "rm":
        value = load(arguments[1])
        if value["State"]["Running"]:
            print("refuse running", file=sys.stderr)
            return 1
        state_path(arguments[1]).unlink()
        print(arguments[1])
    else:
        print(f"unsupported fake docker command: {arguments}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
