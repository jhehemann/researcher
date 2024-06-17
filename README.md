# Researcher

A researcher service that searches for relevant news on the internet, generates embeddings and stores them on IPFS.

## System requirements

- Python `>=3.8`
- [Tendermint](https://docs.tendermint.com/v0.34/introduction/install.html) `==0.34.19`
- [IPFS node](https://docs.ipfs.io/install/command-line/#official-distributions) `==0.6.0`
- [Pip](https://pip.pypa.io/en/stable/installation/)
- [Poetry](https://python-poetry.org/)
- [Docker Engine](https://docs.docker.com/engine/install/)
- [Docker Compose](https://docs.docker.com/compose/install/)

Alternatively, you can fetch this docker image with the relevant requirements satisfied:

> **_NOTE:_**  Tendermint and IPFS dependencies are missing from the image at the moment.

```bash
docker pull valory/open-autonomy-user:latest
docker container run -it valory/open-autonomy-user:latest
```

## How to use

1. Create a virtual environment with all development dependencies:

    ```bash
    poetry shell
    poetry install
    autonomy packages sync --update-packages
    ```

2. Prepare an `ethereum_private_key.txt` (for agents) file and `keys.json` (for services) files containing wallet address and/or the private key for each of the agents. You can generate a new key by running `autonomy generate-key ethereum`. This is how those files should look like:

    ethereum_private_key.txt (check that there are no newlines at the end)

    ```
    0x47e179ec197488593b187f80a00eb0da91f1b9d0b13f8733639f19c30a34926a
    ```

    keys.json
    ```
    [
        {
            "address": "0x15d34AAf54267DB7D7c367839AAf71A00a2C6A65",
            "private_key": "0x47e179ec197488593b187f80a00eb0da91f1b9d0b13f8733639f19c30a34926a"
        }
    ]
    ```

3. Modify `packages/author/agents/demo_agent/aea-config.yaml` so `all_participants` contains your agent's public address.


5. Make a copy of the env file:

    ```cp sample.env .env```

5. Fill in the required environment variables in .env. You'll need
- Ethereum RPC
- `ALL_PARTICIPANTS` needs to contain your agent's public address
- API keys: OpenAI, Google, Google custom search engine ID


6. Test the agent
    1. Add upper case env variables to aea-config.yaml.
    ```yaml
    public_id: jhehemann/researcher_abci:0.1.0
    type: skill
    models:
        params:
            args:
            input_query: ${INPUT_QUERY:str:Search for relevant information about current topics of interest.}
            api_keys_json: ${API_KEYS:list:[]}
    ```
    2. Open terminal and run the agent:
    ```bash
    bash run_agent.py
    ```
    3. In different terminal run Tendermint:

    ```bash
    make tm
    ```

7. Test the service (NOT FUNCTIONAL ATM)
    1. Remove upper case env variables from aea-config.yaml that are automatically overridden when service is run.
    ```yaml
    public_id: jhehemann/researcher_abci:0.1.0
    type: skill
    models:
        params:
            args:
            input_query: ${str:Search for relevant information about current topics of interest.}
            api_keys_json: ${list:[]}
    ```
    2. Open terminal and run the service:
    ```bash
    bash run_service.py
    ```

## Useful commands:

Docker logs:
```bash
docker logs researcherservice_abci_0 --follow
```
State transitions:
```bash
poetry run autonomy analyse logs --from-dir researcher_service/abci_build/persistent_data/logs/ --agent aea_0 --fsm --reset-db
```

### Makefile
Check out the `Makefile` for useful commands, e.g. `make formatters`, `make generators`, `make code-checks`, as well
as `make common-checks-1`. To run tests use the `autonomy test` command. Run `autonomy test --help` for help about its usage.
