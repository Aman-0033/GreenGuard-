from flask import Flask, jsonify, render_template, request
from threading import Thread, Event, Lock
import time, random

from simulator import GreenSimulator
from detector import GreenGuardDetector

app = Flask(__name__)

buf_lock = Lock()
data_buf = []
alerts_buf = []
stop_evt = Event()
demo_queue = []

detector = GreenGuardDetector(z_window=30, z_threshold=2.5, ewma_alpha=0.1, rate_limit_sec=4.0)
sim = GreenSimulator(base_kw=3.4, noise=0.30, attack_rate=0.03, attack_magnitude=3.2, interval_sec=1.0)

def pipeline_loop():
    emission_factor = 0.7
    avoided_emissions_total = 0.0
    while not stop_evt.is_set():
        # If demo queue has injections, use them (FIFO)
        inj = None
        if demo_queue:
            inj = demo_queue.pop(0)

        point = sim.step(injected_kw=inj)   # now step accepts injected_kw
        verdict = detector.check(point["kw"], point["timestamp"])

        if verdict["anomaly"]:
            avoided_kwh = max(0.0, abs(verdict["deviation_kw"])) * (10.0/3600.0)
            avoided_emissions = avoided_kwh * emission_factor
            avoided_emissions_total += avoided_emissions
            action = detector.recommend_action(verdict)
            severity = "critical" if verdict["type"] == "attack" else "warning"
            with buf_lock:
                alerts_buf.append({
                    "timestamp": point["timestamp"],
                    "message": f"{verdict['type'].upper()} Δ≈{verdict['deviation_kw']:.2f} kW — Action: {action}",
                    "avoided_emissions": avoided_emissions,
                    "severity": severity
                })
                if len(alerts_buf) > 120:
                    alerts_buf[:] = alerts_buf[-120:]

        out = {
            **point,
            "anomaly": verdict["anomaly"],
            "type": verdict["type"],
            "avoided_emissions_total": avoided_emissions_total
        }

        with buf_lock:
            data_buf.append(out)
            if len(data_buf) > 600:
                data_buf[:] = data_buf[-600:]

        time.sleep(sim.interval_sec)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/stream")
def api_stream():
    with buf_lock:
        return jsonify({"data": data_buf[-180:], "alerts": alerts_buf[-30:]})

@app.route("/api/tune", methods=["POST"])
def api_tune():
    payload = request.get_json(force=True)
    detector.set_params(z_threshold=float(payload.get("z_threshold", detector.z_threshold)),
                        ewma_alpha=float(payload.get("ewma_alpha", detector.ewma_alpha)))
    return jsonify({"ok": True, "z_threshold": detector.z_threshold, "ewma_alpha": detector.ewma_alpha})

@app.route("/demo", methods=["POST"])
def demo():
    # enqueue alternating spikes & dips to ensure visible anomalies
    spikes = [random.uniform(6.5, 8.0), random.uniform(0.0, 0.4)]
    for i in range(6):
        demo_queue.append(spikes[i % 2])
    return jsonify({"message": "Demo injected (spikes & drops)."})


def start_background():
    t = Thread(target=pipeline_loop, daemon=True)
    t.start()
    return t

if __name__ == "__main__":
    start_background()
    app.run(host="0.0.0.0", port=5000, debug=True)
