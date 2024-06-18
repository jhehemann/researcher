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
        cid_bytes = cast(bytes, multibase.decode(v1_file_hash))
        multihash_bytes = multicodec.remove_prefix(cid_bytes)
        v1_file_hash_hex = V1_HEX_PREFIX + multihash_bytes.hex()
        self.ipfs_hashes['embeddings_json'] = v1_file_hash_hex
        ipfs_link = self.params.ipfs_address + v1_file_hash_hex
        self.context.logger.info(f"IPFS link from v1: {ipfs_link}")

        return ipfs_link

    def _send_urls_to_doc_to_ipfs(self) -> Generator[None, None, Optional[str]]:
        """Send Embeddings to IPFS."""
        urls_to_doc_str = serialize_documents(self.urls_to_doc)
        json_data = json.loads(urls_to_doc_str)
        ipfs_hash = yield from self.send_to_ipfs(
            URLS_TO_DOC_FILENAME, json_data, filetype=SupportedFiletype.JSON
        )
        if ipfs_hash is None:
            return None
        
        to_multihash_to_v1 = self.to_multihash(to_v1(ipfs_hash))
        self.context.logger.info(f"Documents uploaded to_multihash_to_v1: {to_multihash_to_v1}")
        v1_file_hash = to_v1(ipfs_hash)
        cid_bytes = cast(bytes, multibase.decode(v1_file_hash))
        multihash_bytes = multicodec.remove_prefix(cid_bytes)
        v1_file_hash_hex = V1_HEX_PREFIX + multihash_bytes.hex()
        self.ipfs_hashes['urls_to_doc_json'] = v1_file_hash_hex
        ipfs_link = self.params.ipfs_address + v1_file_hash_hex
        self.context.logger.info(f"IPFS link from v1: {ipfs_link}")

        return ipfs_link
    
    def _send_sampled_doc_to_ipfs(self) -> Generator[None, None, Optional[str]]:
        """Send Embeddings to IPFS."""
        sampled_doc_index = self.synchronized_data.sampled_doc_index
        sampled_doc = self.sampled_doc
        sampled_doc_str = serialize_documents(sampled_doc)
        json_data = json.loads(sampled_doc_str)
        ipfs_hash = yield from self.send_to_ipfs(
            SAMPLED_DOCUMENT_FILENAME, json_data, filetype=SupportedFiletype.JSON
        )
        if ipfs_hash is None:
            return None
        
        to_multihash_to_v1 = self.to_multihash(to_v1(ipfs_hash))
        self.context.logger.info(f"Sampled doc uploaded to_multihash_to_v1: {to_multihash_to_v1}")
        v1_file_hash = to_v1(ipfs_hash)
        cid_bytes = cast(bytes, multibase.decode(v1_file_hash))
        multihash_bytes = multicodec.remove_prefix(cid_bytes)
        v1_file_hash_hex = V1_HEX_PREFIX + multihash_bytes.hex()
        self.urls_to_doc[sampled_doc_index].ipfs_hash = v1_file_hash_hex
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
        cid_bytes = cast(bytes, multibase.decode(v1_file_hash))
        multihash_bytes = multicodec.remove_prefix(cid_bytes)
        v1_file_hash_hex = V1_HEX_PREFIX + multihash_bytes.hex()
        ipfs_link = self.params.ipfs_address + v1_file_hash_hex
        self.context.logger.info(f"IPFS link from v1: {ipfs_link}")

        return to_multihash_to_v1
        
    def _get_checkpoint_tx(
        self,
        hashcheckpoint_address: str,
        ipfs_hash: str,
    ) -> Generator[None, None, Optional[Dict[str, Any]]]:
        """Get the transfer tx."""
        contract_api_msg = yield from self.get_contract_api_response(
            performative=ContractApiMessage.Performative.GET_STATE,  # type: ignore
            contract_address=hashcheckpoint_address,
            contract_id=str(HashCheckpointContract.contract_id),
            contract_callable="get_checkpoint_data",
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
        self.read_sampled_doc()
        self.read_urls_to_doc()
        self.read_embeddings()
        self.read_ipfs_hashes()

    def get_payload_content(self) -> Generator:
        self.read_files()
        # should_update_hash = self._should_update_hash()
        # if not should_update_hash:
        #     return None
        if self.sampled_doc:
            yield from self._send_sampled_doc_to_ipfs() # First as it updates its hash in urls_to_doc
        else:
            self.context.logger.error(f"Sampled doc: {self.sampled_doc} is None.")

        self.store_urls_to_doc() # Store the updated mapping locally
        yield from self._send_embeddings_to_ipfs() # Second as it updates its hash in ipfs_hashes
        yield from self._send_urls_to_doc_to_ipfs() # Third as it updates its hash in ipfs_hashes
        self.store_ipfs_hashes() # Store the updated hashes locally
        ipfs_hash = yield from self._send_hashes_to_ipfs()
        hash_checkpoint_address = self.params.hash_checkpoint_address
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
