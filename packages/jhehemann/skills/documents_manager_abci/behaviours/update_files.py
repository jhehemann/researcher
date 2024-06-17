# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------
#
#   Copyright 2024 Valory AG
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

"""This package contains round behaviours of HelloAbciApp."""

from typing import Any, Dict, Generator, Iterator, List, Optional, Set, Tuple, Type, cast
import pandas as pd
from aea.helpers.cid import CID

from packages.jhehemann.skills.documents_manager_abci.graph_tooling.requests import (
    FetchStatus,
    QueryingBehaviour,
)
from packages.valory.skills.abstract_round_abci.io_.store import SupportedFiletype
from packages.jhehemann.contracts.hash_checkpoint.contract import HashCheckpointContract
from packages.jhehemann.skills.documents_manager_abci.payloads import UpdateFilesPayload
from packages.jhehemann.skills.documents_manager_abci.payloads import UpdateQueriesPayload
from packages.jhehemann.skills.documents_manager_abci.rounds import UpdateFilesRound
from packages.jhehemann.skills.documents_manager_abci.rounds import UpdateQueriesRound
from packages.jhehemann.skills.documents_manager_abci.behaviours.base import UpdateDocumentsBehaviour
from packages.valory.protocols.contract_api.message import ContractApiMessage
from packages.valory.skills.abstract_round_abci.base import AbstractRound
from packages.jhehemann.skills.documents_manager_abci.behaviours.base import DocumentsManagerBaseBehaviour   
from packages.jhehemann.skills.documents_manager_abci.queries import Query, QueryStatus

ZERO_ETHER_VALUE = 0
ZERO_IPFS_HASH = (
    "f017012200000000000000000000000000000000000000000000000000000000000000000"
)

class UpdateFilesBehaviour(DocumentsManagerBaseBehaviour):
    """Behaviour that fetches and updates the documents."""

    matching_round = UpdateFilesRound 

    def __init__(self, **kwargs: Any) -> None:
        """Initialize `UpdateDocumentsBehaviour`."""
        super().__init__(**kwargs)

    def _get_latest_hash(
        self,
    ) -> Generator[None, None, Optional[Dict[str, Any]]]:
        """Get the latest IPFS embeddings hash from contract."""

        contract_api_msg = yield from self.get_contract_api_response(
            performative=ContractApiMessage.Performative.GET_STATE,  # type: ignore
            contract_address=self.params.hash_checkpoint_address,
            contract_id=str(HashCheckpointContract.contract_id),
            contract_callable="get_latest_hash",
            sender_address=self.synchronized_data.safe_contract_address,
        )
        if contract_api_msg.performative != ContractApiMessage.Performative.STATE:
            self.context.logger.warning(
                f"get_latest_hash unsuccessful!: {contract_api_msg}"
            )
            return None
        latest_ipfs_hash = cast(str, contract_api_msg.state.body["data"])
        
        if latest_ipfs_hash == ZERO_IPFS_HASH:
            return {}
        # format the hash
        ipfs_hash = str(CID.from_string(latest_ipfs_hash))
        self.context.logger.debug(f"Got latest IPFS CID hash: {latest_ipfs_hash}")
        return ipfs_hash

    def load_file_from_ipfs(self, ipfs_hash: str) -> Generator[None, None, Optional[Dict[str, str]]]:
        """Get the file from IPFS."""
        
        self.context.logger.info(f"Loading file from IPFS with cid hash: {ipfs_hash}")
        json_data = yield from self.get_from_ipfs(ipfs_hash, filetype=SupportedFiletype.JSON)
        
        if json_data is None:
            self.context.logger.warning(
                f"Could not get file from IPFS: {ipfs_hash}"
            )
            return None
        return json_data
    
    def load_embeddings_file(self) -> Generator:
        """Load the embeddings file from IPFS."""
        # check if self.ipfs_hashes is a Dict
        if not isinstance(self.ipfs_hashes, dict):
            self.context.logger.error(
                f"Embeddings file is not a dict. Type: {type(self.ipfs_hashes)}"
            )
            return
        
        embeddings_hash = self.ipfs_hashes.get("embeddings_json")
        embeddings = yield from self.load_file_from_ipfs(embeddings_hash)
        embeddings = pd.DataFrame(embeddings)
        self.context.logger.info(f"Downloaded embeddings dataframe: {embeddings.shape}")
        self.embeddings = embeddings.sort_index(axis=0).sort_index(axis=1)
        self.store_embeddings()

    def load_documents_file(self) -> Generator:
        """Load documents file from IPFS."""
        documents_hash = self.ipfs_hashes.get("documents_json")
        documents = yield from self.load_file_from_ipfs(documents_hash)
        self.context.logger.info(f"Downloaded documents: {documents}")
        self.documents = documents
        self.store_documents()

    def load_latest_files(self) -> Generator:
        """Load the latest files from IPFS."""
        # Get the latest IPFS hash from the contract
        # This IPFS hash points to a file containing the hashes of the other files
        ipfs_files_hashes_hash = yield from self._get_latest_hash()
        
        if ipfs_files_hashes_hash is None:
            self.context.logger.warning(
                "No hashes file found in contract. Assuming no files are stored on IPFS."
            )
            return
        
        # Load the file containing the hashes of the other files
        ipfs_files_hashes = yield from self.load_file_from_ipfs(ipfs_files_hashes_hash)
        if ipfs_files_hashes is None:
            return
        if not isinstance(ipfs_files_hashes, dict):
            self.context.logger.error(
                f"IPFS hashes file is not a dict. Type: {type(ipfs_files_hashes)}"
            )
            return

        self.ipfs_hashes = ipfs_files_hashes
        self.context.logger.info(f"Downloaded IPFS hashes: {ipfs_files_hashes}")
        yield from self.load_embeddings_file()
        yield from self.load_documents_file()

    def get_payload_content(self) -> Generator:
        """Get the payload content."""
        local_documents_hash = None
        local_embeddings_hash = None
        yield from self.load_latest_files()
        if self.ipfs_hashes is None:
            return None, None
        else:
            local_documents_hash = self.hash_stored_documents()
            self.context.logger.info(f"Local documents hash: {local_documents_hash}")
            local_embeddings_hash = self.hash_stored_embeddings()
            self.context.logger.info(f"Local embeddings hash: {local_embeddings_hash}")

        return local_documents_hash, local_embeddings_hash

    def async_act(self) -> Generator:
        """Do the action."""
        with self.context.benchmark_tool.measure(self.behaviour_id).local():
            documents_hash, embeddings_hash = yield from self.get_payload_content()
            sender = self.context.agent_address
            payload = UpdateFilesPayload(
                sender=sender,
                documents_hash=documents_hash,
                embeddings_hash=embeddings_hash,
            )
        with self.context.benchmark_tool.measure(self.behaviour_id).consensus():
            yield from self.send_a2a_transaction(payload)
            yield from self.wait_until_round_end()
            self.set_done()


class UpdateQueriesBehaviour(DocumentsManagerBaseBehaviour, QueryingBehaviour):
    """Behaviour that fetches and updates the queries."""

    matching_round = UpdateQueriesRound

    def __init__(self, **kwargs: Any) -> None:
        """Initialize `UpdateQueriesBehaviour`."""
        super().__init__(**kwargs)

    def is_frozen_query(self, query: Query) -> bool:
        """Return if a query should not be updated."""
        return (
            query.blacklist_expiration > self.synced_time
            and query.status == QueryStatus.BLACKLISTED
        ) or query.status == QueryStatus.PROCESSED

    @property
    def frozen_local_queries(self) -> Iterator[Query]:
        """Get the frozen, already existing, queries."""
        return filter(self.is_frozen_query, self.queries)

    @property
    def frozen_queries_and_ids(self) -> Tuple[List[Query], Set[str]]:
        """Get the ids of the frozen, already existing, queries."""
        queries = []
        ids = set()
        for query in self.frozen_local_queries:
            queries.append(query)
            ids.add(query.id)
        return queries, ids

    def _update_queries(
        self,
    ) -> Generator:
        """Fetch the questions from all the prediction markets and update the local copy of the queries."""
        self.queries, existing_ids = self.frozen_queries_and_ids

        while True:
            can_proceed = self._prepare_fetching()
            if not can_proceed:
                break

            queries_market_chunk = yield from self._fetch_queries()
            if queries_market_chunk is not None:
                queries_updates = (
                    Query(**query, market=self._current_market)
                    for query in queries_market_chunk
                    if query.get("id", "") not in existing_ids
                )
                self.queries.extend(queries_updates)

        if self._fetch_status != FetchStatus.SUCCESS:
            self.queries = []

        self.context.logger.info(f"Updated queries: {len(self.queries)}")

    def async_act(self) -> Generator:
        """Do the action."""
        with self.context.benchmark_tool.measure(self.behaviour_id).local():
            self.read_queries()
            yield from self._update_queries()
            self.store_queries()
            queries_hash = self.hash_stored_queries()
            payload = UpdateQueriesPayload(self.context.agent_address, queries_hash)

        with self.context.benchmark_tool.measure(self.behaviour_id).consensus():
            yield from self.send_a2a_transaction(payload)
            yield from self.wait_until_round_end()
            self.set_done()
