import logging
import json
from typing import Any, Dict
from paho.mqtt import client as mqtt_client
from datetime import datetime
from socket import gethostname
from json import JSONDecodeError

from warwickd.config import Config
from warwickd.mailer import mailer
from warwickd.prometheus_metrics import prometheus_metrics

logger = logging.getLogger(__name__)

class daemon:
    def __init__(self, config: Dict[str, Any] | Any) -> None:
        # Attempt to parse the provided config, will attempt a variety of validation checks
        self.config = self._parse_config(config)

        # Prometheus client
        self.prometheus_client = prometheus_metrics(self.config)

        # MQTT
        self.mqtt_broker = self.config.mqtt_broker.server
        self.mqtt_port = self.config.mqtt_broker.port
        self.mqtt_name = gethostname()
        self.mqtt_client = self.connect_mqtt()
        self.topic_attribute_cache = {}    # The attribute cache is used to allow caching flags and relating messages to each other

        # Create the mailer class that then can be used anywhere by calling the send_email func
        self.mailer = mailer(self.config)
        # run on class creation
        self.run()

    def run(self):
        # Subscribe to alerts and watchdogs
        for subscription in self.config.subscriptions:
            logger.info('Registering ' + str(subscription) + '...')
            self.subscribe(subscription['topic'])

        # Start the loop
        self.mqtt_client.on_message = self.message_callback
        self.mqtt_client.loop_forever()

    @staticmethod
    def _parse_config(config) -> Config:
        return Config.model_validate(config)

    def connect_mqtt(self) -> mqtt_client.Client:
        def on_connect(client, userdata, flags, reason_code, properties):
            if reason_code != 0:
                logger.info(f"Failed to connect, return code {reason_code}")
            logger.info("Successfully connected to MQTT Broker")

        # mqtt doesn't explicitly export the CallbackAPIVersion even though it is required
        client = mqtt_client.Client(mqtt_client.CallbackAPIVersion.VERSION2, self.mqtt_name)  # type: ignore
        client.on_connect = on_connect
        client.connect(self.mqtt_broker, self.mqtt_port)
        return client

    def subscribe(self, topic):
        logger.info('Subscribe to topic "' + topic + '"')
        self.mqtt_client.subscribe(topic)

    def message_callback(self, client, userdata, message):
        logger.debug("Topic '" + message.topic + "' received message '" + message.payload.decode() + "'")

        # If its not in the cache this is the first time we are seeing it, add it to the attribute cache
        if message.topic not in self.topic_attribute_cache:
            logger.info("New topic found '" + message.topic + "'")
            self.topic_attribute_cache[message.topic] = {"flags": [], "last_received_time": datetime.now()}

            # Check to see if it matches any subscriptions defined in our config
            for subscription in self.config.subscriptions:
                if not mqtt_client.topic_matches_sub(subscription['topic'], message.topic):
                    continue

                # Now check if its a special catagory we have custom actions for
                for category in ['heartbeat_watchdog', 'mail_alert', 'metric']:
                    if not subscription.get(category):
                        continue

                    # Thats a match, start with adding the category as a flag
                    logger.debug("Flag '" + category + "' cached to topic '" + message.topic + "'")
                    self.topic_attribute_cache[message.topic]['flags'].append(category)

                    # Metrics cache thier types
                    if category == 'metric':
                        self.topic_attribute_cache[message.topic]['metrics'] = []
                        for metric in subscription['metric']:
                            logger.debug("New metric '" + message.topic + " - " + str(metric) + ' added to cache')
                            self.topic_attribute_cache[message.topic]['metrics'].append(metric)

        try:
            message_json = json.loads(message.payload.decode())
        except JSONDecodeError:
            return

        # Update topic metadata
        self.topic_attribute_cache[message.topic]["last_received_time"] = datetime.now()

        # Watchdogs
        if "hearbeat_watchdog" in self.topic_attribute_cache[message.topic]["flags"]:
            self.topic_attribute_cache[message.topic]["uptime"] = message_json["seconds"]

        # Alerts
        if "mail_alert" in self.topic_attribute_cache[message.topic]["flags"]:
            self.mailer.send_email("Alert triggered", str(message_json))

        # Metrics are sent to the prometheus client
        if "metric" in self.topic_attribute_cache[message.topic]["flags"]:
            try:
                self.prometheus_client.set_metric(self.topic_attribute_cache[message.topic]['metrics'], message.topic, json.loads(message.payload.decode()))
            except e:
                logger.warning('Failed to process metric!')
                logger.warning(str(e))



