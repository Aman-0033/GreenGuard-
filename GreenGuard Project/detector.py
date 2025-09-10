import math
from collections import deque

class GreenGuardDetector:
    def __init__(self, z_window=30, z_threshold=2.5, ewma_alpha=0.1, rate_limit_sec=4.0):
        self.window = deque(maxlen=z_window)
        self.z_threshold = z_threshold
        self.ewma_alpha = ewma_alpha
        self.ewma = None
        self.rate_limit_sec = rate_limit_sec
        self.last_alert_ts = 0.0

    def _mean_std(self):
        n = len(self.window)
        if n == 0:
            return 0.0, 1.0
        mu = sum(self.window) / n
        var = sum((x - mu) ** 2 for x in self.window) / max(1, (n - 1))
        sigma = math.sqrt(var) if var > 1e-12 else 1.0
        return mu, sigma

    def _z(self, x):
        mu, sigma = self._mean_std()
        return (x - mu) / sigma

    def _ewma_update(self, x):
        self.ewma = x if self.ewma is None else (self.ewma_alpha * x + (1 - self.ewma_alpha) * self.ewma)
        return self.ewma

    def check(self, x, ts):
        self.window.append(x)
        z = self._z(x)
        ew = self._ewma_update(x)
        anomaly = (abs(z) >= self.z_threshold) or (abs(x - ew) > 2.0)
        typ = "normal"
        deviation = x - ew

        if anomaly:
            if (ts - self.last_alert_ts) >= self.rate_limit_sec:
                self.last_alert_ts = ts
                typ = "attack" if (abs(z) >= self.z_threshold * 1.5 or abs(deviation) > 3.5) else "suspicious"
            else:
                typ = "suspicious"

        return {"anomaly": anomaly, "type": typ, "z": z, "ewma": ew, "deviation_kw": deviation}

    def recommend_action(self, verdict):
        if verdict["type"] == "attack":
            return "Isolate node → safe mode → rotate keys"
        if verdict["type"] == "suspicious":
            return "Rate-limit, verify signatures, increase sampling"
        return "Monitor"

    def set_params(self, z_threshold=None, ewma_alpha=None):
        if z_threshold is not None:
            self.z_threshold = float(z_threshold)
        if ewma_alpha is not None:
            self.ewma_alpha = float(ewma_alpha)



