if [[ `hostname` == *"kesch"* ]]; then
  module load PE/17.06
  module load python/3.6.2-gmvolf-17.02
fi
python3 -m venv env
source env/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
deactivate
