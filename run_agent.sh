if test -d researcher_agent; then
  echo "Removing previous agent build"
  rm -r researcher_agent
fi

source .env

export INPUT_QUERY="Who will be the next president of the United States?"

find . -empty -type d -delete  # remove empty directories to avoid wrong hashes
autonomy packages lock
autonomy fetch --local --agent jhehemann/researcher_agent && cd researcher_agent

cp $PWD/../ethereum_private_key.txt .

# Copy .env file
# cp $PWD/../.env .
autonomy add-key ethereum ethereum_private_key.txt
autonomy issue-certificates
# aea -s -v DEBUG run
aea -s run
