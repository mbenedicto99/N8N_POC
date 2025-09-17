# no diretório do repo N8N_POC
sudo apt-get update
sudo apt-get install -y python3.12-venv python3-dev build-essential

python -m pip install --upgrade pip setuptools wheel

cd /home/mbenedicto/Documents/CanopusAI/N8N_POC
python3 -m venv .venv
source .venv/bin/activate

python -m pip --version         # deve apontar para .../projeto/.venv/...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

