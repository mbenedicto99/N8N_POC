sudo apt update
sudo apt install -y python3 python3-venv python3-pip

cd /home/mbenedicto/Documents/CanopusAI/N8N_POC
python3 -m venv .venv
source .venv/bin/activate

python -m pip --version         # deve apontar para .../projeto/.venv/...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

