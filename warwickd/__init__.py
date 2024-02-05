# System libraries
import json
from datetime import datetime
from socket import gethostname
from paho.mqtt import client as mqtt_client

# Our libraries
from warwickd.mailer import mailer

class daemon:

	def __init__(self, logger, config):
		self.logger = logger
		self.config = config

		self.mqtt_broker = self.config['mqtt_broker']['server']
		self.mqtt_port = self.config['mqtt_broker']['port']
		self.mqtt_name = gethostname()
		self.mqtt_client = self.connect_mqtt()
		self.topic_attribute_cache = {}

		# Subscribe to alerts and watchdogs
		for subscription_parameters in self.config['subscriptions']:
			self.logger.info('Registering ' + str(subscription_parameters) + '...')
			self.subscribe(subscription_parameters['topic'])

		# Start the loop
		self.mqtt_client.on_message = self.message_callback
		self.mqtt_client.loop_forever()

	def connect_mqtt(self) -> mqtt_client:
		def on_connect(client, userdata, flags, rc):
			if rc == 0:
				self.logger.info("Connected to MQTT Broker!")
			else:
				self.logger.info("Failed to connect, return code %d\n", rc)

		client = mqtt_client.Client(self.mqtt_name)
		client.on_connect = on_connect
		client.connect(self.mqtt_broker, self.mqtt_port)
		return client

	def subscribe(self, topic):
		self.logger.info('Subscribing to topic "' + topic + '"')
		self.mqtt_client.subscribe(topic)

	# Anyime a message is recieved this function is run
	def message_callback(self, client, userdata, message):
		self.logger.debug("Topic '" + message.topic + "' received message '" + message.payload.decode() + "'")

		# Try to decode message as json
		message_json = None
		try:
			message_json = json.loads(message.payload.decode())
		except:
			self.logger.warning("Unable to parse message from '" + message.topic + "' as json")

		# If this is the first time we have seen this topic, flag attributes for it
		if message.topic not in self.topic_attribute_cache:
			self.logger.info("New topic found '" + message.topic + "'")
			self.topic_attribute_cache[message.topic] = {'flags': [], 'last_received_time': datetime.now()}

			# Check to see if it matches any defined subscriptions
			for subscription in self.config['subscriptions']:
				if mqtt_client.topic_matches_sub(subscription['topic'], message.topic):

					# Check special categories
					for category in ['heartbeat_watchdog', 'mail_alert']:
						if subscription.get(category):
							self.logger.debug("Flag '" + category + "' cached to topic '" + message.topic + "'")
							self.topic_attribute_cache[message.topic]['flags'].append(category)

		# We can only do anything from here if the message is json
		if message_json is None:
			return

		# Update topic metadata
		self.topic_attribute_cache[message.topic]['last_received_time'] = datetime.now()

		# Watchdogs
		if 'hearbeat_watchdog' in self.topic_attribute_cache[message.topic]['flags']:
			self.topic_attribute_cache[message.topic]['uptime'] = message_json['seconds']

		# Alerts
		if 'mail_alert' in self.topic_attribute_cache[message.topic]['flags']:
			mailer(self.config, self.logger, "Alert triggered", str(message_json))

