from prometheus_client import start_http_server, Summary, Gauge
import random
import time
import datetime

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
			new_metric = Gauge(metric_key + '_' + metric_location, '', ['location'])

		# All metrics should come with a location
		new_metric.labels(location=metric_location)

		# Add to the cache
		self.metric_cache[metric_location][metric_key] = {'metric': new_metric, 'last_reported': datetime.datetime.now()}

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
			self.metric_cache[location][metric['key']]['metric'].labels(location=location).set(float(metric_data[metric['key']]))
			self.metric_cache[location][metric['key']]['last_reported'] = datetime.datetime.now()

	def check_stale_metrics(self):
		while True:

			# Iterrate through the cache and evict anything stale
			metrics_to_evict = []
			for location in self.metric_cache:
				for metric_name in self.metric_cache[location]:

					# A metric at -1 is already evicted, ignore it
					if self.metric_cache[location][metric_name]['last_reported'] == -1:
						continue

					if self.metric_cache[location][metric_name]['last_reported'] < datetime.datetime.now()-datetime.timedelta(seconds=300):
						logger.warning('Metric ' + location + '/' + metric_name + ' has gone stale, evicting')
						metrics_to_evict.append((location, metric_name))

			for location, metric_name in metrics_to_evict:
				self.metric_cache[location][metric_name]['metric'].clear()
				self.metric_cache[location][metric_name]['last_reported'] = -1

			time.sleep(60)


