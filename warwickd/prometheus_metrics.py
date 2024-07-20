from prometheus_client import start_http_server, Summary, Gauge
import random
import time

import logging
logger = logging.getLogger(__name__)

from warwickd.config import Config

class prometheus_metrics:

	def __init__(self, config: Config):
		self.enabled = config.prometheus.enabled
		self.http_port = config.prometheus.http_port
		self.metric_cache = {}
		logger.warning("Initializing prometheus metrics, listening on " + str(self.http_port))

		start_http_server(self.http_port)

	def create_metric(self, metric_location, metric_key, metric_type):

		# Create the type of metric required
		if metric_type == 'gauge':
			new_metric = Gauge(metric_key, '', ['location'])

		# All metrics should come with a location
		new_metric.labels(location=metric_location)

		# Add to the cache
		self.metric_cache[metric_location][metric_key] = new_metric

	def set_metric(self, metric_schemas, message_topic, metric_data):

		# Extra common parameters from the metric
		location = metric_data.get('location')

		# Rotate throught the schema and look for matches in the metric data
		for metric in metric_schemas:

			# Only progress if we have metric data matching a key in the schmea
			if not metric_data.get(metric['key']):
				continue

			# If we haven't seen this location before add it to the cache
			if not self.metric_cache.get(location):
				self.metric_cache[location] = {}

			# If we haven't seen this metric in the location before add it to the cache and create the metric for it
			if not self.metric_cache[location].get(metric['key']):
				self.create_metric(location, metric['key'], metric['type'])

			# Finally set the value of the metric
			self.metric_cache[location][metric['key']].labels(location=location).set(float(metric_data[metric['key']]))

