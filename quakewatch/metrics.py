from prometheus_client import Counter, Gauge, Histogram

earthquakes_collected = Counter("quakewatch_earthquakes_collected_total", "New earthquakes saved by the collector")
collection_failures = Counter("quakewatch_collection_failures_total", "Collector runs that failed")
last_collection = Gauge("quakewatch_last_collection_timestamp_seconds", "Time of the last successful collection")
analyzer_runs = Counter("quakewatch_analyzer_runs_total", "Analyzer runs")
request_latency = Histogram("quakewatch_request_seconds", "Web request latency", ["endpoint"])
