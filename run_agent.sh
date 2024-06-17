if test -d researcher_agent; then
  echo "Removing previous agent build"
  rm -r researcher_agent
fi

source .env

export INPUT_QUERY="Who will be the next president of the United States?"
# export SAFE_CONTRACT_ADDRESS="0x0C0b9642Ef7b94Fe20dC4a871fD3E5E661DEb86C"

find . -empty -type d -delete  # remove empty directories to avoid wrong hashes
autonomy packages lock
autonomy fetch --local --agent jhehemann/researcher_agent && cd researcher_agent

cp $PWD/../ethereum_private_key.txt .

mkdir ./logs
chmod 755 ./logs

# Copy .env file
# cp $PWD/../.env .
autonomy add-key ethereum ethereum_private_key.txt
autonomy issue-certificates
# aea -s -v DEBUG run
aea -s run
