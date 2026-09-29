"""Правила межсервисных рёбер: shared-lib, kafka, rest, db, auth.

Каждое правило детерминировано и оставляет evidence (файл:строка или конфиг).

Kafka в ПК АУСН: имя топика не пишется литералом в коде — оно берётся из конфигурации
(`kafka.topics.<ключ>.destination`), а код ссылается на ключ через
`@Value("${kafka.topics.<ключ>.destination}")` (продюсер) или
`@KafkaListener(topics = ["${kafka.topics.<ключ>.destination}"])` (консьюмер).
Поэтому правило сначала читает карту «ключ → топик» из конфигов, затем связывает ключи с ролями.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

BUILD_FILES = ("build.gradle.kts", "build.gradle", "settings.gradle.kts", "settings.gradle")
CONFIG_FILES = (
    "application.yaml",
    "application.yml",
    "application.properties",
    "bootstrap.yaml",
    "bootstrap.yml",
)
SKIP_DIRS = {".git", "build", "node_modules", "dist", ".gradle", "__pycache__"}

SEND_CALL = re.compile(r"kafkaTemplate\.send\s*\(")
LISTENER = re.compile(r"@KafkaListener\s*\(")
KEY_IN_TEXT = re.compile(r"kafka\.topics\.(?P<key>[A-Za-z0-9._-]+)\.destination")
ENV_DEFAULT = re.compile(r"\$\{[A-Za-z0-9_]+:(?P<name>[A-Za-z0-9._-]+)")


def _walk(repo_path: Path, predicate) -> list[Path]:
    found: list[Path] = []
    for current, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        found.extend(Path(current) / name for name in files if predicate(name))
    return sorted(found)


def _build_files(repo_path: Path) -> list[Path]:
    """Файлы сборки Gradle в репозитории (без служебных каталогов)."""
    return _walk(repo_path, lambda name: name in BUILD_FILES)


def _kotlin_files(repo_path: Path) -> list[Path]:
    """Файлы исходников (Kotlin/Java) без каталогов тестов."""
    found: list[Path] = []
    for current, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and d != "test"]
        found.extend(Path(current) / name for name in files if name.endswith((".kt", ".java")))
    return sorted(found)


def _config_files(repo_path: Path) -> list[Path]:
    return _walk(repo_path, lambda name: name in CONFIG_FILES)


def shared_lib_edges(service_id: str, repo_path: Path, markers: list[str]) -> list[dict]:
    """Рёбра shared-lib: упоминание библиотеки-маркера в файлах сборки."""
    edges: list[dict] = []
    for path in _build_files(repo_path):
        for number, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            for marker in markers:
                if marker in line:
                    edges.append(
                        {
                            "from": service_id,
                            "to": marker,
                            "type": "shared-lib",
                            "label": marker,
                            "source": "code",
                            "confidence": "resolved",
                            "evidence": f"{path.relative_to(repo_path).as_posix()}:{number}",
                            "note": "",
                        }
                    )
    return edges


def kafka_topic_names(repo_path: Path) -> dict[str, str]:
    """Карта «ключ конфигурации → имя топика» из `kafka.topics.*.destination`.

    Поддерживает вложенный YAML и плоский вид `<полный путь>=<значение>`.
    Значение вида `${ENV_VAR:имя-топика}` разворачивается в имя по умолчанию.
    """
    names: dict[str, str] = {}
    for path in _config_files(repo_path):
        stack: list[tuple[int, str]] = []
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or ":" not in stripped and "=" not in stripped:
                continue
            indent = len(line) - len(line.lstrip(" "))
            match = re.match(r"([A-Za-z0-9._-]+)\s*[:=]\s*(.*)$", stripped)
            if not match:
                continue
            key, value = match.group(1), match.group(2).strip()
            while stack and stack[-1][0] >= indent:
                stack.pop()
            stack.append((indent, key))
            if not value:
                continue
            if key == "destination":
                parents = [name for _, name in stack[:-1]]
                if parents[:2] != ["kafka", "topics"] or len(parents) < 3:
                    continue
                topic_key = ".".join(parents[2:])
            elif key.startswith("kafka.topics.") and key.endswith(".destination"):
                topic_key = key[len("kafka.topics.") : -len(".destination")]
            else:
                continue
            default = ENV_DEFAULT.search(value)
            names[topic_key] = default.group("name") if default else value.strip('"\'')
    return names


def produced_topics(repo_path: Path) -> dict[str, str]:
    """Топики, которые сервис отправляет: ключи `@Value` в классах с `kafkaTemplate.send`."""
    names = kafka_topic_names(repo_path)
    topics: dict[str, str] = {}
    for path in _kotlin_files(repo_path):
        text = path.read_text(encoding="utf-8", errors="replace")
        if not SEND_CALL.search(text):
            continue
        for match in KEY_IN_TEXT.finditer(text):
            topic = names.get(match.group("key"))
            if not topic:
                continue
            line = text[: match.start()].count("\n") + 1
            topics.setdefault(topic, f"{path.relative_to(repo_path).as_posix()}:{line}")
    return topics


def consumed_topics(repo_path: Path) -> dict[str, str]:
    """Топики, которые сервис слушает: ключи в файлах с `@KafkaListener`."""
    names = kafka_topic_names(repo_path)
    topics: dict[str, str] = {}
    for path in _kotlin_files(repo_path):
        text = path.read_text(encoding="utf-8", errors="replace")
        if not LISTENER.search(text):
            continue
        for match in KEY_IN_TEXT.finditer(text):
            topic = names.get(match.group("key"))
            if not topic:
                continue
            line = text[: match.start()].count("\n") + 1
            topics.setdefault(topic, f"{path.relative_to(repo_path).as_posix()}:{line}")
    return topics


def contract_topics(contracts_repo: Path) -> set[str]:
    """Топики контрактов: из конфигураций репозитория и литералов в исходниках."""
    topics = set(kafka_topic_names(contracts_repo).values())
    for path in _kotlin_files(contracts_repo) + _config_files(contracts_repo):
        text = path.read_text(encoding="utf-8", errors="replace")
        topics.update(re.findall(r"[\"']([a-z][a-z0-9-]+\.[a-z0-9._-]+)[\"']", text))
    return topics


def kafka_edges(
    producers: dict[str, dict[str, str]],
    consumers: dict[str, dict[str, str]],
    service_ids: set[str],
) -> list[dict]:
    """Рёбра kafka: сервис-продюсер → сервис-консьюмер (подпись ребра — топик).

    Если консьюмер в наших репозиториях не найден, ребро ведёт в узел `kafka`
    с пометкой и `confidence: unresolved`.
    """
    consumers_by_topic: dict[str, list[str]] = {}
    for service, topics in consumers.items():
        for topic in topics:
            consumers_by_topic.setdefault(topic, []).append(service)
    edges: list[dict] = []
    for producer, topics in producers.items():
        for topic, evidence in topics.items():
            targets = [item for item in consumers_by_topic.get(topic, []) if item != producer]
            if not targets:
                edges.append(
                    {
                        "from": producer,
                        "to": "kafka",
                        "type": "kafka",
                        "label": topic,
                        "source": "code",
                        "confidence": "unresolved",
                        "evidence": evidence,
                        "note": "нет консьюмера в наших репозиториях",
                    }
                )
                continue
            for target in targets:
                edges.append(
                    {
                        "from": producer,
                        "to": target,
                        "type": "kafka",
                        "label": topic,
                        "source": "code",
                        "confidence": "resolved",
                        "evidence": evidence,
                        "note": "",
                    }
                )
    return sorted(edges, key=lambda item: (item["from"], item["label"], item["to"]))
