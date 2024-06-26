#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------
#
#   Copyright 2021-2024 Valory AG
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
# ------------------------------------------------------------------------------

"""Push NFT images to IPFS"""

import json
import os
from pathlib import Path

from aea_cli_ipfs.ipfs_utils import IPFSTool


MINT_PATH = Path(".", "mints")
MINT_FILE = "mints.json"
IPFS_NODE = "/dns/registry.autonolas.tech/tcp/443/https"
IPFS_GATEWAY = "https://gateway.autonolas.tech/ipfs/"


if __name__ == "__main__":
    ipfs_tool = IPFSTool(IPFS_NODE)
    image_to_hash = {}

    for file in os.listdir(MINT_PATH):
        if file.endswith(".jpg"):
            image_path = Path(MINT_PATH, file)

            _, hash_, _ = ipfs_tool.add(  # type: ignore
                dir_path=str(image_path), pin=True, wrap_with_directory=False
            )
            image_to_hash[image_path.stem] = {"id": None, "image_hash": hash_}
            print(f"Successfully stored {file}: {IPFS_GATEWAY}{hash_}")

    print(json.dumps(image_to_hash, indent=4, sort_keys=True))
    with open(Path(MINT_PATH, MINT_FILE), "w", encoding="utf-8") as out_file:
        json.dump(image_to_hash, out_file, indent=4, sort_keys=True)