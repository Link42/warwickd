from dataclasses import dataclass
from typing import List


@dataclass
class Mqtt_broker:
    server: str
    port: str


@dataclass
class Smtp:
    server: str
    port: str


@dataclass
class Mailer:
    from_name: str
    from_address: str
    to_address: str
    subject: str
    smtp: Smtp


@dataclass
class Topic:
    topic: str
    heartbeat_watchdog: bool = False
    mail_alert: bool = False


@dataclass
class Subscriptions:
    topics: List[Topic]


@dataclass
class Ntp_service:
    topic: str
    enabled: bool = False


@dataclass
class Config:
    mqtt_broker: Mqtt_broker
    mailer: Mailer
    subscription: Subscriptions
    ntp_service: Ntp_service
