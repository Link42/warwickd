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
		logger.warning("Initializing prometheus metrics, listening on " + str(self.http_port))

		start_http_server(self.http_port)

	def set_metric(self, metric_type, metric_data):

		# Create a metric to track time spent and requests made.
		logger.info("Setting " + metric_type + " metric: " + str(metric_data))

		if metric_type == 'gauge':
			metric = Gauge(metric_data['subject'], metric_data['description'])
			metric.set(metric_data['value'])
			metric.set_to_current_time()

