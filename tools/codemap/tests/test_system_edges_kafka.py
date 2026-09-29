"""Тесты правила kafka: ключи конфигурации, роли и построение рёбер."""

from __future__ import annotations

from pathlib import Path

from tools.codemap.system_edges import (
    consumed_topics,
    contract_topics,
    kafka_edges,
    kafka_topic_names,
    produced_topics,
)

YAML = """kafka:
  topics:
    ausn:
      registration-out:
        destination: ${KAFKA_TOPIC_REGISTRATION_OUT:ausn.registration-out}
      registration-in:
        destination: ${KAFKA_TOPIC_REGISTRATION_IN:ausn.registration-in}
"""

PRODUCER = """package app

import org.springframework.beans.factory.annotation.Value
import org.springframework.kafka.core.KafkaTemplate

class RegistrationProducer(
    private val kafkaTemplate: KafkaTemplate<*, *>,
    @Value("\\${kafka.topics.ausn.registration-out.destination}")
    private val kafkaTopic: String,
) {
    fun send(message: String) {
        kafkaTemplate.send(message)
    }
}
"""

CONSUMER = """package app

import org.springframework.kafka.annotation.KafkaListener

class RegistrationConsumer {
    @KafkaListener(topics = ["\\${kafka.topics.ausn.registration-in.destination}"])
    fun consume(message: String) {}
}
"""


def build_service(root: Path) -> None:
    resources = root / "src/main/resources"
    resources.mkdir(parents=True)
    (resources / "application.yaml").write_text(YAML, encoding="utf-8")
    sources = root / "src/main/kotlin"
    sources.mkdir(parents=True)
    (sources / "RegistrationProducer.kt").write_text(PRODUCER, encoding="utf-8")
    (sources / "RegistrationConsumer.kt").write_text(CONSUMER, encoding="utf-8")


def test_topic_names_from_config(tmp_path: Path) -> None:
    build_service(tmp_path)
    names = kafka_topic_names(tmp_path)
    assert names["ausn.registration-out"] == "ausn.registration-out"
    assert names["ausn.registration-in"] == "ausn.registration-in"


def test_roles_resolve_keys_to_topics(tmp_path: Path) -> None:
    build_service(tmp_path)
    assert set(produced_topics(tmp_path)) == {"ausn.registration-out"}
    assert set(consumed_topics(tmp_path)) == {"ausn.registration-in"}
    assert produced_topics(tmp_path)["ausn.registration-out"].startswith("src/main/kotlin/RegistrationProducer.kt:")


def test_contract_topics_includes_config_names(tmp_path: Path) -> None:
    (tmp_path / "src/main/resources").mkdir(parents=True)
    (tmp_path / "src/main/resources/application.yaml").write_text(YAML, encoding="utf-8")
    assert contract_topics(tmp_path) >= {"ausn.registration-out", "ausn.registration-in"}


CATEGORIZER_YAML = """kafka:
  topics:
    operations: ${KAFKA_TOPIC_CATEGORIZER_IN:operation-categorizer.operation-in}
    ausn-core:
      operations: ${KAFKA_TOPIC_OPERATION_IN:ausn.operation-in}
"""

CATEGORIZER_LISTENER = """package app

import org.springframework.kafka.annotation.KafkaListener

class OperationKafkaListener {
    @KafkaListener(topics = ["\\${kafka.topics.operations}"])
    fun getOperation(message: String) {}

    @KafkaListener(topics = ["\\${kafka.topics.ausn-core.operations}"])
    fun getCoreOperation(message: String) {}
}
"""


def test_categorizer_style_without_destination(tmp_path: Path) -> None:
    resources = tmp_path / "src/main/resources"
    resources.mkdir(parents=True)
    (resources / "application.yaml").write_text(CATEGORIZER_YAML, encoding="utf-8")
    sources = tmp_path / "src/main/kotlin"
    sources.mkdir(parents=True)
    (sources / "OperationKafkaListener.kt").write_text(CATEGORIZER_LISTENER, encoding="utf-8")

    names = kafka_topic_names(tmp_path)
    assert names["operations"] == "operation-categorizer.operation-in"
    assert names["ausn-core.operations"] == "ausn.operation-in"
    assert set(consumed_topics(tmp_path)) == {"operation-categorizer.operation-in", "ausn.operation-in"}


def test_test_sources_are_skipped(tmp_path: Path) -> None:
    resources = tmp_path / "src/main/resources"
    resources.mkdir(parents=True)
    (resources / "application.yaml").write_text(YAML, encoding="utf-8")
    tests = tmp_path / "src/test/kotlin"
    tests.mkdir(parents=True)
    (tests / "RegistrationProducerTest.kt").write_text(PRODUCER, encoding="utf-8")
    assert produced_topics(tmp_path) == {}


def test_kafka_edge_between_services() -> None:
    edges = kafka_edges(
        producers={"ausn-core": {"ausn.registration-in": "P.kt:1"}},
        consumers={"ausn-front-module": {"ausn.registration-in": "C.kt:2"}},
        service_ids={"ausn-core", "ausn-front-module"},
    )
    assert edges == [
        {
            "from": "ausn-core",
            "to": "ausn-front-module",
            "type": "kafka",
            "label": "ausn.registration-in",
            "source": "code",
            "confidence": "resolved",
            "evidence": "P.kt:1",
            "note": "",
        }
    ]


def test_unknown_consumer_becomes_kafka_node() -> None:
    edges = kafka_edges(producers={"ausn-core": {"ausn.orphan": "P.kt:1"}}, consumers={}, service_ids={"ausn-core"})
    assert edges[0]["to"] == "kafka"
    assert edges[0]["confidence"] == "unresolved"
    assert "нет консьюмера" in edges[0]["note"]


def test_producer_is_not_its_own_consumer() -> None:
    edges = kafka_edges(
        producers={"ausn-core": {"ausn.loop": "P.kt:1"}},
        consumers={"ausn-core": {"ausn.loop": "C.kt:2"}},
        service_ids={"ausn-core"},
    )
    assert edges[0]["to"] == "kafka"
    assert edges[0]["confidence"] == "unresolved"
