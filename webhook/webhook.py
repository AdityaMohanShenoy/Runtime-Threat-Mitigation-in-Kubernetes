from flask import Flask, request, jsonify
import subprocess, json

app = Flask(__name__)

@app.route('/', methods=['POST'])
def webhook():
    print(json.dumps(request.json, indent=2))
    data = request.json
    rule = data.get("rule", "")
    pod = data.get("output_fields", {}).get("k8s.pod.name", "")
    ns = data.get("output_fields", {}).get("k8s.ns.name", "default")

    if "shell" in rule.lower() and pod:
        print(f"[+] Deleting pod {pod} in ns {ns}")
        subprocess.run(["kubectl", "delete", "pod", pod, "-n", ns, "--ignore-not-found"])
        return jsonify({"status": "deleted"}), 200

    return jsonify({"status": "ignored"}), 200

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)
