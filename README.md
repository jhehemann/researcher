# Dev-template

A template for development with the open-autonomy framework. Find the documentation [here](https://docs.autonolas.network).

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

## This repository contains:

- A directory, `packages`, which acts as the local registry

- Pre-filled in third-party core packages

- Basic example of a simple skill, a chained skill, an agent and a service

- .env sample file with Python path updated to include packages directory

## How to use

1. Create a virtual environment with all development dependencies:

    ```bash
    poetry shell
    poetry install
    autonomy packages sync --update-packages
    ```

2. Prepare an `ethereum_private_key.txt` (for agents) file and `keys.json` (for services) files containing wallet address and/or the private key for each of the agents. You can generate a new key by running `autonomy generate-key ethereum`. This is how those files hsould look like:

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

5. Fill in the required environment variables in .env. You'll need a Ethereum RPC. `ALL_PARTICIPANTS` needs to contain your agent's public address.


6. Test the agent

    ```bash
    bash run_agent.py
    ```

    and in other terminal run Tendermint:

    ```bash
    make tm
    ```

7. Test the service

    ```bash
    bash run_service.py
    ```

8. Get developing...

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
