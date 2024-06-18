# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------
#
#   Copyright 2023-2024 Valory AG
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

"""This module contains the behaviour for extracting html from a web page."""



import json
from typing import Any, Generator, Optional, Type, Dict, cast
from abc import ABC

from aea.helpers.cid import to_v1
from multibase import multibase
from multicodec import multicodec

from packages.jhehemann.contracts.hash_checkpoint.contract import HashCheckpointContract
from packages.jhehemann.skills.documents_manager_abci.behaviours.base import (
    SAMPLED_DOCUMENT_FILENAME,
    URLS_TO_DOC_FILENAME,
    EMBEDDINGS_FILENAME,
    IPFS_HASHES_FILENAME,
    QUERIES_FILENAME,
)
from packages.jhehemann.skills.scraper_abci.behaviours.base import ScraperBaseBehaviour
from packages.jhehemann.skills.scraper_abci.payloads import PublishPayload
from packages.jhehemann.skills.scraper_abci.rounds import PublishRound
from packages.jhehemann.skills.documents_manager_abci.documents import (
    serialize_documents,
)
from packages.valory.contracts.gnosis_safe.contract import GnosisSafeContract
from packages.valory.protocols.contract_api.message import ContractApiMessage
from packages.valory.skills.abstract_round_abci.base import AbstractRound
from packages.valory.skills.abstract_round_abci.io_.store import SupportedFiletype


from packages.valory.skills.transaction_settlement_abci.payload_tools import (
    hash_payload_to_hex,
)


V1_HEX_PREFIX = "f01"
Ox = "0x"
ZERO_ETHER_VALUE = 0
ZERO_IPFS_HASH = (
    "f017012200000000000000000000000000000000000000000000000000000000000000000"
)
SAFE_GAS = 0

class PublishBehaviour(ScraperBaseBehaviour):  # pylint: disable=too-many-ancestors
    """Behaviour to get content from web pages"""

    matching_round: Type[AbstractRound] = PublishRound     

    def __init__(self, **kwargs: Any) -> None:
        """Initialize behaviour."""
        super().__init__(**kwargs)
        # self._web_scrape_response: Optional[WebScrapeInteractionResponse] = None
    
    # @property
    # def web_scrape_response_api(self) -> WebScrapeResponseSpecs:
    #     """Get the web page's response api specs."""
    #     return self.context.web_scrape_response
    
    # def set_web_scrape_response_specs(self, url) -> None:
    #     """Set the web page's response specs."""        
    #     self.web_scrape_response_api.__dict__["_frozen"] = False
    #     self.web_scrape_response_api.url = url
    #     self.web_scrape_response_api.__dict__["_frozen"] = True

    # def _get_latest_hash(self) -> str:
    #     """Get latest update hash."""
    #     ## Right now only stored locally by agents - No access across runs
    #     ## Should be stored in smart contract later and dynamically loaded 
        
    #     # contract_api_msg = yield from self.get_contract_api_response(
    #     #     performative=ContractApiMessage.Performative.GET_STATE,  # type: ignore
    #     #     contract_address=self.params.agent_registry_address,
    #     #     contract_id=str(AgentRegistryContract.contract_id),
    #     #     contract_callable="get_token_hash",
    #     #     token_id=self.params.agent_id,
    #     # )
    #     # if (
    #     #     contract_api_msg.performative != ContractApiMessage.Performative.STATE
    #     # ):  # pragma: nocover
    #     #     self.context.logger.warning(
    #     #         f"get_token_hash unsuccessful!: {contract_api_msg}"
    #     #     )
    #     #     return None

    #     # latest_hash = cast(bytes, contract_api_msg.state.body["data"])


    #     return self.params.publish_mutable_params.latest_embeddings_hash

    def _should_update_hash(self) -> Generator:
        """Check if the agent should update the hash."""
        latest_hash = self.params.publish_mutable_params.latest_embeddings_hash
        new_hash = self.synchronized_data.embeddings_hash

        return new_hash != latest_hash

    # def _handle_response(
    #     self,
    #     res: Optional[str],
    # ) -> Optional[Any]:
    #     """Handle the response from the web page.

    #     :param res: the response to handle.
    #     :return: the response's result, using the given keys. `None` if response is `None` (has failed).
    #     """
    #     if res is None:
    #         msg = f"Could not get the web page's response from {self.web_scrape_response_api.api_id}"
    #         self.context.logger.error(msg)
    #         self.web_scrape_response_api.increment_retries()
    #         return None

    #     self.context.logger.info(f"Retrieved the web page's response. Number of characters: {len(res)}")
    #     # self.context.logger.info(f"Response: {res}")
    #     self.web_scrape_response_api.reset_retries()
    #     return res
    

    def _send_embeddings_to_ipfs(self) -> Generator[None, None, Optional[str]]:
        """Send Embeddings to IPFS."""
        embeddings = self.embeddings
        json_data = embeddings.to_dict(orient='records')
        ipfs_hash = yield from self.send_to_ipfs(
            EMBEDDINGS_FILENAME, json_data, filetype=SupportedFiletype.JSON
        )
        if ipfs_hash is None:
            return None
        
        to_multihash_to_v1 = self.to_multihash(to_v1(ipfs_hash))
        self.context.logger.info(f"Embeddings uploaded to_multihash_to_v1: {to_multihash_to_v1}")
        

        v1_file_hash = to_v1(ipfs_hash)
        self.context.logger.info(f"Embeddings uploaded v1 hash: {v1_file_hash}")
        cid_bytes = cast(bytes, multibase.decode(v1_file_hash))
        self.context.logger.info(f"Embeddings uploaded cid bytes: {cid_bytes}")
        multihash_bytes = multicodec.remove_prefix(cid_bytes)
        self.context.logger.info(f"Embeddings uploaded multicodec remove prefix hex: {multihash_bytes.hex()}")

        v1_file_hash_hex = V1_HEX_PREFIX + multihash_bytes.hex()
        self.ipfs_hashes['embeddings_json'] = v1_file_hash_hex

        self.context.logger.info(f"Embeddings uploaded hex v1 hash: {v1_file_hash_hex}")
        ipfs_link = self.params.ipfs_address + v1_file_hash_hex
        self.context.logger.info(f"IPFS link from v1: {ipfs_link}")

        return ipfs_link

    def _send_urls_to_doc_to_ipfs(self) -> Generator[None, None, Optional[str]]:
        """Send Embeddings to IPFS."""
        #json_data = self.documents
        urls_to_doc = serialize_documents(self.urls_to_doc)
        json_data = json.loads(urls_to_doc)
        ipfs_hash = yield from self.send_to_ipfs(
            URLS_TO_DOC_FILENAME, json_data, filetype=SupportedFiletype.JSON
        )
        if ipfs_hash is None:
            return None
        
        to_multihash_to_v1 = self.to_multihash(to_v1(ipfs_hash))
        self.context.logger.info(f"Documents uploaded to_multihash_to_v1: {to_multihash_to_v1}")
        

        v1_file_hash = to_v1(ipfs_hash)
        # self.context.logger.info(f"Embeddings uploaded v1 hash: {v1_file_hash}")
        cid_bytes = cast(bytes, multibase.decode(v1_file_hash))
        # self.context.logger.info(f"Embeddings uploaded cid bytes: {cid_bytes}")
        multihash_bytes = multicodec.remove_prefix(cid_bytes)
        # self.context.logger.info(f"Embeddings uploaded multicodec remove prefix hex: {multihash_bytes.hex()}")
        v1_file_hash_hex = V1_HEX_PREFIX + multihash_bytes.hex()
        self.ipfs_hashes['urls_to_doc_json'] = v1_file_hash_hex

        # self.context.logger.info(f"Embeddings uploaded hex v1 hash: {v1_file_hash_hex}")
        ipfs_link = self.params.ipfs_address + v1_file_hash_hex
        self.context.logger.info(f"IPFS link from v1: {ipfs_link}")

        return ipfs_link
    
    def _send_hashes_to_ipfs(self) -> Generator[None, None, Optional[str]]:
        """Send hashes to IPFS."""
        json_data = self.ipfs_hashes
        ipfs_hash = yield from self.send_to_ipfs(
            IPFS_HASHES_FILENAME, json_data, filetype=SupportedFiletype.JSON
        )
        if ipfs_hash is None:
            return None
        
        to_multihash_to_v1 = self.to_multihash(to_v1(ipfs_hash))
        self.context.logger.info(f"Files hashes uploaded to_multihash_to_v1: {to_multihash_to_v1}")

        v1_file_hash = to_v1(ipfs_hash)
        # self.context.logger.info(f"Embeddings uploaded v1 hash: {v1_file_hash}")
        cid_bytes = cast(bytes, multibase.decode(v1_file_hash))
        # self.context.logger.info(f"Embeddings uploaded cid bytes: {cid_bytes}")
        multihash_bytes = multicodec.remove_prefix(cid_bytes)
        # self.context.logger.info(f"Embeddings uploaded multicodec remove prefix hex: {multihash_bytes.hex()}")
        v1_file_hash_hex = V1_HEX_PREFIX + multihash_bytes.hex()
        # self.context.logger.info(f"Embeddings uploaded hex v1 hash: {v1_file_hash_hex}")
        ipfs_link = self.params.ipfs_address + v1_file_hash_hex
        self.context.logger.info(f"IPFS link from v1: {ipfs_link}")

        return to_multihash_to_v1
        
    def _get_checkpoint_tx(
        self,
        hashcheckpoint_address: str,
        ipfs_hash: str,
    ) -> Generator[None, None, Optional[Dict[str, Any]]]:
        """Get the transfer tx."""
        self.context.logger.info(f"IPFS hash in _get_checkpoint_tx: {ipfs_hash}")
        self.context.logger.info(f"Bytes from hex: {bytes.fromhex(ipfs_hash)}")
        contract_api_msg = yield from self.get_contract_api_response(
            performative=ContractApiMessage.Performative.GET_STATE,  # type: ignore
            contract_address=hashcheckpoint_address,
            contract_id=str(HashCheckpointContract.contract_id),
            contract_callable="get_checkpoint_data",
            #data=bytes.fromhex("f02d773780ee38a64657f824472c7328ff389e845ff0f9d5c4585f955c8b2c4e"),
            data=bytes.fromhex(ipfs_hash),
        )
        if (
            contract_api_msg.performative != ContractApiMessage.Performative.STATE
        ):  # pragma: nocover
            self.context.logger.warning(
                f"get_checkpoint_data unsuccessful!: {contract_api_msg}"
            )
            return None

        self.context.logger.info(f"Retrieved the checkpoint data: {contract_api_msg}")

        data = cast(bytes, contract_api_msg.state.body["data"])
        return {
            "to": hashcheckpoint_address,
            "value": ZERO_ETHER_VALUE,
            "data": data,
        }
    
    def _get_safe_tx_hash(self, data: bytes) -> Generator[None, None, Optional[str]]:
        """
        Prepares and returns the safe tx hash.

        This hash will be signed later by the agents, and submitted to the safe contract.
        Note that this is the transaction that the safe will execute, with the provided data.

        :param data: the safe tx data.
        :return: the tx hash
        """
        response = yield from self.get_contract_api_response(
            performative=ContractApiMessage.Performative.GET_STATE,  # type: ignore
            contract_address=self.synchronized_data.safe_contract_address,
            contract_id=str(GnosisSafeContract.contract_id),
            contract_callable="get_raw_safe_transaction_hash",
            to_address=self.params.hash_checkpoint_address,
            value=ZERO_ETHER_VALUE,
            data=data,
            safe_tx_gas=SAFE_GAS,
        )

        if response.performative != ContractApiMessage.Performative.STATE:
            self.context.logger.error(
                f"Couldn't get safe hash. "
                f"Expected response performative {ContractApiMessage.Performative.STATE.value}, "  # type: ignore
                f"received {response.performative.value}."
            )
            return None

        # strip "0x" from the response hash
        tx_hash = cast(str, response.state.body["tx_hash"])[2:]
        return tx_hash

    def read_files(self) -> None:
        """Read local files from the agent's data dir."""
        self.read_ipfs_hashes()
        self.read_urls_to_doc()
        self.read_embeddings()

    def get_payload_content(self) -> Generator:
        self.read_files()
        should_update_hash = self._should_update_hash()
        if not should_update_hash:
            return None
        
        hash_checkpoint_address = self.params.hash_checkpoint_address
        yield from self._send_embeddings_to_ipfs()
        yield from self._send_urls_to_doc_to_ipfs()
        self.store_ipfs_hashes()
        ipfs_hash = yield from self._send_hashes_to_ipfs()
        self.context.logger.info(f"IPFS hash to lock in contract: {ipfs_hash}")
        update_checkpoint_tx = yield from self._get_checkpoint_tx(hash_checkpoint_address, ipfs_hash)
        self.context.logger.info(f"Update checkpoint tx: {update_checkpoint_tx}")
        tx_data_str = (cast(str, update_checkpoint_tx)["data"])[2:]
        self.context.logger.info(f"Tx data str: {tx_data_str}")
        tx_data = bytes.fromhex(cast(str, tx_data_str))
        tx_hash = yield from self._get_safe_tx_hash(tx_data)
        if tx_hash is None:
            # something went wrong
            return None
        
        payload_data = hash_payload_to_hex(
            safe_tx_hash=tx_hash,
            ether_value=ZERO_ETHER_VALUE,
            safe_tx_gas=SAFE_GAS,
            to_address=hash_checkpoint_address,
            data=tx_data,
            #gas_limit=self.params.manual_gas_limit,
        )
        self.context.logger.info(f"Payload data: {payload_data}")
        return payload_data
      
    def async_act(self) -> Generator:
        """Do the act, supporting asynchronous execution."""

        with self.context.benchmark_tool.measure(self.behaviour_id).local():
            sender = self.context.agent_address
            payload_content = yield from self.get_payload_content()
            payload = PublishPayload(sender=sender, content=payload_content)

        with self.context.benchmark_tool.measure(self.behaviour_id).consensus():
            yield from self.send_a2a_transaction(payload)
            yield from self.wait_until_round_end()

        self.set_done()
