import json
from pathlib import Path


class MetricsLogger:
    def __init__(self, config=None):
        self.enabled = bool(getattr(config, "METRICS_LOGGING_ENABLED", False))
        self.path = None

        if self.enabled:
            log_path = getattr(config, "METRICS_LOG_PATH", "logs/mission_metrics.jsonl")
            self.path = Path(log_path)
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text("", encoding="utf-8")

    def log_step(self, metrics):
        if not self.enabled or self.path is None:
            return

        line = json.dumps(metrics, separators=(",", ":"))
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
