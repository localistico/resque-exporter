import argparse
import json
import logging
import os
import signal
import sys
from time import sleep

from prometheus_client import start_http_server
from prometheus_client.core import REGISTRY

from .collector import ResqueCollector


def sigterm_handler(_signo, _stackframe):
    logging.info("Shutting down.")
    sys.exit(os.EX_OK)


def json_cmdline_value(val):
    if not val:
        return None
    return json.loads(val)


def main():
    signal.signal(signal.SIGTERM, sigterm_handler)
    logging.getLogger().setLevel(logging.INFO)

    parser = argparse.ArgumentParser(description="Resque exporter for Prometheus.")
    parser.add_argument('-a', '--address', dest='addr', type=str,
                        default=os.getenv('RESQUE_EXPORTER_ADDR', '0.0.0.0'),
                        help="IP address to expose metrics")
    parser.add_argument('-r', '--redis-url', dest='redis_url', type=str,
                        default=os.getenv('RESQUE_EXPORTER_REDIS_URL'),
                        help="Redis URL")
    parser.add_argument('--redis-sentinel-hosts', dest='redis_sentinel_hosts', type=str,
                        default=os.getenv('RESQUE_EXPORTER_REDIS_SENTINEL_HOSTS'),
                        help="Redis Sentinel hosts, e.g. 'host1:26379,host2:26379'")
    parser.add_argument('--redis-sentinel-masterset', dest='redis_sentinel_masterset', type=str,
                        default=os.getenv('RESQUE_EXPORTER_REDIS_SENTINEL_MASTERSET'),
                        help="Redis Sentinel master name")
    parser.add_argument('--redis-password', dest='redis_password', type=str,
                        default=os.getenv('RESQUE_EXPORTER_REDIS_PASSWORD'),
                        help="Redis password")
    parser.add_argument('-n', '--redis-namespace', dest='redis_ns', type=str,
                        default=os.getenv('RESQUE_EXPORTER_REDIS_NS'), help="Redis namespace")
    parser.add_argument('-p', '--port', dest='port', type=int,
                        default=os.getenv('RESQUE_EXPORTER_PORT', "9447"),
                        help="Port to expose metrics")
    parser.add_argument('-l', '--loglevel', dest='loglevel', choices=['INFO', 'DEBUG'],
                        default="INFO", help="Set application loglevel INFO, DEBUG")
    parser.add_argument('--custom-metrics', type=json_cmdline_value,
                        default=os.getenv('RESQUE_EXPORTER_CUSTOM_METRICS', None),
                        help=(
                            'Custom metrics to collect, e.g. '
                            '[{"type": "counter", "name": "mymetric",'
                            ' "redis_matcher": "mymetric:*", '
                            '"label_regex": "mymetric:(?P<mykey>.*)$"}]'
                        ))
    args = parser.parse_args()

    numeric_level = getattr(logging, args.loglevel)
    logging.basicConfig(level=numeric_level, format='%(asctime)s %(levelname)s:%(message)s')

    start_http_server(args.port, addr=args.addr)
    logging.info(f"HTTP server started on {args.addr}:{args.port}")

    r_collector = ResqueCollector(
        args.redis_url,
        namespace=args.redis_ns,
        custom_metrics=args.custom_metrics,
        redis_sentinel_hosts=args.redis_sentinel_hosts,
        redis_sentinel_masterset=args.redis_sentinel_masterset,
        redis_password=args.redis_password,
    )

    REGISTRY.register(r_collector)

    try:
        while True:
            sleep(5)
    except KeyboardInterrupt:
        pass
