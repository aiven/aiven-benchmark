from aiven.client import AivenClient
from kafka.consumer import KafkaConsumer
from kafka.structs import TopicPartition

import json
import logging
import os
import time


def main():
    logger = logging.getLogger(os.path.basename(__file__))

    # Setup Aiven SDK
    logger.info("Setting up Aiven SDK")
    client = AivenClient(os.environ.get("AIVEN_URL") or "https://api.aiven.io")
    client.set_auth_token(os.environ["AIVEN_TOKEN"])

    # Lookup the target service
    logger.info("Looking up the target Aiven Kafka Service")
    service = client.get_service(project=os.environ["AIVEN_PROJECT"], service=os.environ["AIVEN_SERVICE"])
    if not service:
        raise SystemExit("Failed to look up the target service")

    # Store credentials on disk. This is using the main access certificates (avnadmin).
    logger.info("Storing Aiven service access credentials")
    with open("client.crt", "w") as fh:
        fh.write(service["connection_info"]["kafka_access_cert"])
    with open("client.key", "w") as fh:
        fh.write(service["connection_info"]["kafka_access_key"])

    # Project CA certificate
    logger.info("Fetching project CA certificate")
    result = client.get_project_ca(project=os.environ["AIVEN_PROJECT"])
    with open("ca.crt", "w") as fh:
        fh.write(result["certificate"])

    # Initialize Kafka client
    kafka_client = KafkaConsumer(
        bootstrap_servers=service["service_uri"],
        security_protocol="SSL",
        ssl_cafile="ca.crt",
        ssl_certfile="client.crt",
        ssl_keyfile="client.key",
    )

    partitions = kafka_client.partitions_for_topic(os.environ["AIVEN_TOPIC"])
    tps = [TopicPartition(os.environ["AIVEN_TOPIC"], partition) for partition in partitions]
    last_timestamp = time.monotonic()
    last_offsets = {}

    logger.info("Start result collection loop, break with CTRL-C")
    readings = []
    readings_60 = []
    readings_300 = []
    while True:
        delta = 0
        result = kafka_client.end_offsets(tps)
        timenow = time.monotonic()
        for tp, offset in result.items():
            if tp in last_offsets:
                delta += offset - last_offsets[tp]
            last_offsets[tp] = offset

        messages_per_second = int(delta/(timenow-last_timestamp))

        readings.append(messages_per_second)
        readings = readings[-30:]
        readings_60.append(messages_per_second)
        readings_60 = readings_60[-60:]
        readings_300.append(messages_per_second)
        readings_300 = readings_300[-300:]

        logger.info("%d messages/s, %d sample average %d messages/s, %d: %d m/s, %d: %d m/s",
            messages_per_second,
            len(readings), sum(readings)/len(readings),
            len(readings_60), sum(readings_60)/len(readings_60),
            len(readings_300), sum(readings_300)/len(readings_300),
            )
        last_timestamp = timenow
        time.sleep(2)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
