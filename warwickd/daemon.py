import datetime
import logging
import json
import paho.mqtt.client as mqtt_client
from socket import gethostname
from json import JSONDecodeError
from .mailer import mailer

logger = logging.getLogger(__name__)


class daemon:
    def __init__(self, config) -> None:
        self.config = config

        self.mqtt_broker = self.config["mqtt_broker"]["server"]
        self.mqtt_port = self.config["mqtt_broker"]["port"]
        self.mqtt_name = gethostname()
        self.mqtt_client = self.connect_mqtt()
        self.topic_attribute_cache = {}

    def connect_mqtt(self) -> mqtt_client:
        def on_connect(client, userdata, flags, reason_code, properties):
            if reason_code != 0:
                logger.info(f"Failed to connect, return code {reason_code}")
            logger.info(f"Successfully connected to MQTT Broker")

        client = mqtt_client.Client(self.mqtt_name)
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
            for subscription in self.config.get("subscriptions", []):
                if mqtt_client.topic_matches_sub(
                    subscription.get("topic", ""), message.topic
                ):
                    # Check special categories
                    for category in ("heartbeat_watchdog", "mail_alert"):
                        if subscription.get(category):
                            logger.debug(
                                f"Flag '{category}' cached to topic '{message.topic}'"
                            )
                            self.topic_attribute_cache.setdefault(
                                message.topic, {"flags": []}
                            )["flags"].append(category)

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
            mailer(self.config, self.logger, "Alert triggered", str(message_json))
