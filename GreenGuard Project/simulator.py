import random, time, math

class GreenSimulator:
    def __init__(self, base_kw=3.4, noise=0.3, attack_rate=0.03, attack_magnitude=3.2, interval_sec=1.0):
        self.base_kw = base_kw
        self.noise = noise
        self.attack_rate = attack_rate
        self.attack_magnitude = attack_magnitude
        self.interval_sec = interval_sec
        self.step_i = 0

    def _season(self):
        return 0.8 * math.sin(self.step_i / 60.0)

    def step(self, injected_kw=None):
        self.step_i += 1
        ts = time.time()
        if injected_kw is not None:
            kw = injected_kw
        else:
            kw = self.base_kw + self._season() + random.uniform(-self.noise, self.noise)
            if random.random() < self.attack_rate:
                if random.random() < 0.5:
                    kw += self.attack_magnitude
                else:
                    kw = max(0.0, kw - self.attack_magnitude)
        return {"timestamp": ts, "kw": max(0.0, kw)}

