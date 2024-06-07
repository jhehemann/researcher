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



from typing import Any, Generator, Optional, Type, cast
from abc import ABC

from aea.helpers.cid import to_v1

import multibase
import multicodec

# from packages.jhehemann.skills.scraper_abci.models import PublishResponseSpecs
from packages.jhehemann.skills.scraper_abci.behaviours.base import ScraperBaseBehaviour, WaitableConditionType
# from packages.jhehemann.skills.scraper_abci.models import PublishInteractionResponse
from packages.jhehemann.skills.scraper_abci.payloads import PublishPayload
from packages.jhehemann.skills.scraper_abci.rounds import PublishRound
from packages.valory.skills.abstract_round_abci.base import AbstractRound
from packages.valory.skills.abstract_round_abci.io_.store import SupportedFiletype

V1_HEX_PREFIX = "f01"
Ox = "0x"
EMBEDDINGS_FILENAME = "embeddings.json"

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

    def _get_latest_hash(self) -> str:
        """Get latest update hash."""
        ## Right now only stored locally by agents - No access across runs
        ## Should be stored in smart contract later and dynamically loaded 
        
        # contract_api_msg = yield from self.get_contract_api_response(
        #     performative=ContractApiMessage.Performative.GET_STATE,  # type: ignore
        #     contract_address=self.params.agent_registry_address,
        #     contract_id=str(AgentRegistryContract.contract_id),
        #     contract_callable="get_token_hash",
        #     token_id=self.params.agent_id,
        # )
        # if (
        #     contract_api_msg.performative != ContractApiMessage.Performative.STATE
        # ):  # pragma: nocover
        #     self.context.logger.warning(
        #         f"get_token_hash unsuccessful!: {contract_api_msg}"
        #     )
        #     return None

        # latest_hash = cast(bytes, contract_api_msg.state.body["data"])


        return self.params.publish_mutable_params.latest_embeddings_hash

    def _should_update_hash(self) -> Generator:
        """Check if the agent should update the hash."""
        latest_hash = self.params.publish_mutable_params.latest_embeddings_hash
        new_hash = self.synchronized_data.embeddings_hash

        return new_hash != latest_hash

    def _handle_response(
        self,
        res: Optional[str],
    ) -> Optional[Any]:
        """Handle the response from the web page.

        :param res: the response to handle.
        :return: the response's result, using the given keys. `None` if response is `None` (has failed).
        """
        if res is None:
            msg = f"Could not get the web page's response from {self.web_scrape_response_api.api_id}"
            self.context.logger.error(msg)
            self.web_scrape_response_api.increment_retries()
            return None

        self.context.logger.info(f"Retrieved the web page's response. Number of characters: {len(res)}")
        # self.context.logger.info(f"Response: {res}")
        self.web_scrape_response_api.reset_retries()
        return res
    

    def _send_embeddings_to_ipfs(
        self,
    ) -> WaitableConditionType:
        """Send Embeddings to IPFS."""
        embeddings = self.embeddings
        json_data = embeddings.to_dict(orient='records')
        ipfs_hash = yield from self.send_to_ipfs(
            EMBEDDINGS_FILENAME, json_data, filetype=SupportedFiletype.JSON
        )
        if ipfs_hash is None:
            return None
        
        self.context.logger.info(f"IPFS hash from upload: {ipfs_hash}")
        
        # v1_file_hash_hex = self.to_multihash(to_v1(ipfs_hash))

        v1_file_hash = to_v1(ipfs_hash)
        self.context.logger.info(f"Embeddings uploaded v1 hash: {v1_file_hash}")
        cid_bytes = cast(bytes, multibase.decode(v1_file_hash))
        multihash_bytes = multicodec.remove_prefix(cid_bytes)
        v1_file_hash_hex = V1_HEX_PREFIX + multihash_bytes.hex()
        ipfs_link = self.params.ipfs_address + v1_file_hash_hex



        # v1_file_hash = to_v1(embeddings_hash_live)
        # cid_bytes = cast(bytes, multibase.decode(v1_file_hash))
        # multihash_bytes = multicodec.remove_prefix(cid_bytes)
        # v1_file_hash_hex = V1_HEX_PREFIX + multihash_bytes.hex()
        
        # ipfs_link = self.params.ipfs_address + v1_file_hash_hex
        
        self.context.logger.info(f"IPFS link from v1: {ipfs_link}")
        # mech_request_data = v1_file_hash_hex[9:]
        # self._v1_hex_truncated = Ox + mech_request_data
        return v1_file_hash_hex

    def get_payload_content(self) -> Generator:
        """Extract html text from website"""
        should_update_hash = self._should_update_hash()
        if not should_update_hash:
            return None
        
        embeddings_ipfs_hash = yield from self._send_embeddings_to_ipfs()
        
        # self.read_embeddings()

        # # should_update_hash = self._should_update_hash()
        # # if not should_update_hash:
        # #     return None
        
        # ipfs_link = yield from self._send_embeddings_to_ipfs()
        
        return embeddings_ipfs_hash

    def async_act(self) -> Generator:
        """Do the act, supporting asynchronous execution."""

        with self.context.benchmark_tool.measure(self.behaviour_id).local():
            sender = self.context.agent_address
            payload_content = yield from self.get_payload_content()
            payload = PublishPayload(sender=sender, embeddings_ipfs_hash=payload_content)

        with self.context.benchmark_tool.measure(self.behaviour_id).consensus():
            yield from self.send_a2a_transaction(payload)
            yield from self.wait_until_round_end()

        self.set_done()