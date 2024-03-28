import logging
import json
from typing import Any, Dict
import paho.mqtt.client as mqtt_client
from paho.mqtt.client import Client
from datetime import datetime
from socket import gethostname
from json import JSONDecodeError

from warwickd.config import Config
from warwickd.mailer import mailer

logger = logging.getLogger(__name__)


class daemon:
    def __init__(self, config: Dict[str, Any] | Any) -> None:
        # Attempt to parse the provided config, will attempt a variety of validation checks
        self.config = self._parse_config(config)

        self.mqtt_broker = self.config.mqtt_broker.server
        self.mqtt_port = self.config.mqtt_broker.port
        self.mqtt_name = gethostname()
        self.mqtt_client = self.connect_mqtt()
        self.topic_attribute_cache = {}

        # Create the mailer class that then can be used anywhere by calling the send_email func
        self.mailer = mailer(self.config)

    @staticmethod
    def _parse_config(config) -> Config:
        return Config.model_validate(config)

    def connect_mqtt(self) -> Client:
        def on_connect(client, userdata, flags, reason_code, properties):
            if reason_code != 0:
                logger.info(f"Failed to connect, return code {reason_code}")
            logger.info(f"Successfully connected to MQTT Broker")

        # mqtt doesn't explicitly export the CallbackAPIVersion even though it is required
        client = mqtt_client.Client(mqtt_client.CallbackAPIVersion.VERSION2, self.mqtt_name)  # type: ignore
        client.on_connect = on_connect
        client.connect(self.mqtt_broker, self.mqtt_port)
        return client

    def subscribe(self, topic):
        logger.info(f'Subscribe to topic "' + topic + '"')
        self.mqtt_client.subscribe(topic)

    def message_callback(self, client, userdata, message):
        logger.debug(
            "Topic '"
            + message.topic
            + "' received message '"
            + message.payload.decode()
            + "'"
        )

        if message.topic not in self.topic_attribute_cache:
            logger.info("NEw topic found '" + message.topic + "'")
            self.topic_attribute_cache[message.topic] = {
                "flags": [],
                "last_received_time": datetime.now(),
            }

            # Check to see if it matches any defined subscriptions
            for subscription in self.config.subscriptions:
                if mqtt_client.topic_matches_sub(
                    subscription.topic, message.topic
                ):
                    if subscription.heartbeat_watchdog or subscription.mail_alert:
                        category = "heartbeat_watchdog" if subscription.heartbeat_watchdog else "mail_alert"
                        logger.debug(f"Flag {category} cached to topic '{message.topic}'")
                        self.topic_attribute_cache.setdefault(message.topic, {"flags": []})["flags"].append(category)
 
        try:
            message_json = json.loads(message.payload.decode())
        except JSONDecodeError:
            return

        # Update topic metadata
        self.topic_attribute_cache[message.topic]["last_received_time"] = datetime.now()

        # Watchdogs
        if "hearbeat_watchdog" in self.topic_attribute_cache[message.topic]["flags"]:
            self.topic_attribute_cache[message.topic]["uptime"] = message_json[
                "seconds"
            ]

        # Alerts
        if "mail_alert" in self.topic_attribute_cache[message.topic]["flags"]:
            self.mailer.send_email("Alert triggered", str(message_json))

