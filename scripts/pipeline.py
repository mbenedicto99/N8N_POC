#!/usr/bin/env python3
import os, sys, subprocess

BASE = os.path.join(os.path.dirname(__file__), "..")

def run(cmd):
    print("+", " ".join(cmd)); subprocess.check_call(cmd)

run([sys.executable, os.path.join(BASE, "scripts", "etl.py")])

try:
    run([sys.executable, os.path.join(BASE, "scripts", "train_isoforest.py")])
except Exception as e:
    print("Aviso: não foi possível treinar IsolationForest. Seguindo com Z-score.", e)

run([sys.executable, os.path.join(BASE, "scripts", "detect_anomalies.py")])
print("Pipeline concluída.")
