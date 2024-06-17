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

import json
import os.path
from abc import ABC
from typing import Any, Dict, Generator, Iterator, List, Optional, Set, Tuple, Type, cast
import pandas as pd
from aea.helpers.cid import CID

from packages.valory.skills.abstract_round_abci.io_.store import SupportedFiletype
from packages.jhehemann.contracts.hash_checkpoint.contract import HashCheckpointContract
from packages.jhehemann.skills.documents_manager_abci.payloads import UpdateFilesPayload
from packages.jhehemann.skills.documents_manager_abci.rounds import UpdateFilesRound
from packages.jhehemann.skills.documents_manager_abci.behaviours.base import UpdateDocumentsBehaviour
from packages.valory.protocols.contract_api.message import ContractApiMessage
from packages.valory.skills.abstract_round_abci.base import AbstractRound
from packages.jhehemann.skills.documents_manager_abci.behaviours.base import DocumentsManagerBaseBehaviour   
from packages.jhehemann.skills.documents_manager_abci.documents import Document, DocumentStatus

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

    def update_embeddings(self) -> None:
        """Add new embeddings to the existing DataFrame and link them to text chunks in sampled document."""
        
        embeddings = [embedding.get('embedding') for embedding in self._embedding_response.data]
        text_chunks = self.sampled_doc.text_chunks
        if len(embeddings) != len(text_chunks):
            self.context.logger.error(
                "The number of new embeddings and corresponding text chunks do not match."
            )
            return
        
        if not embeddings or not text_chunks:
            self.context.logger.warning("No new embeddings or text chunks to add.")
            return

        # Create the columns for the new embeddings        
        embedding_columns = [f"dim{i+1}" for i in range(len(embeddings[0]))]
        # Create dictionary combining embeddings and text chunks
        data = {col: [emb[i] for emb in embeddings] for i, col in enumerate(embedding_columns)}
        data['text_chunk'] = text_chunks
        # Create the DataFrame
        embeddings_df = pd.DataFrame(data)
        self.context.logger.info(f"New Embeddings DF: {embeddings_df.shape}")
        self.context.logger.info(f"Previous Embeddings DF: {self.embeddings.shape}")
        
        # Concatenate the new embeddings with the existing ones
        self.embeddings = pd.concat([self.embeddings, embeddings_df], ignore_index=True)

        self.embeddings.drop_duplicates(subset=['text_chunk'], inplace=True)
        self.context.logger.info(
            f"Total new embeddings dataframe: {self.embeddings.shape}"
        )

    def load_latest_files(self) -> Generator:
        """Get the latest embeddings from IPFS."""
        ipfs_hash = yield from self._get_latest_hash()
        if ipfs_hash is None:
            self.context.logger.warning(
                "No files hash found. Assuming no files are stored on IPFS."
            )
            return

        self.context.logger.info(f"Getting files from IPFS with cid hash: {ipfs_hash}")

        files = yield from self.get_from_ipfs(
            ipfs_hash, filetype=SupportedFiletype.JSON
        )
        if files is None:
            self.context.logger.warning(
                f"Could not get files from IPFS: {ipfs_hash}"
            )
            return
        
        embeddings = pd.DataFrame(files)
        self.context.logger.info(f"Downloaded embeddings dataframe: {embeddings.shape}")
        self.embeddings = embeddings
    
    def async_act(self) -> Generator:
        """Do the action."""
        with self.context.benchmark_tool.measure(self.behaviour_id).local():
            yield from self.load_latest_files()
            self.embeddings = self.embeddings.sort_index(axis=0).sort_index(axis=1)
            self.store_embeddings()
            embeddings_hash = self.hash_stored_embeddings()
            self.context.logger.info(f"Local embeddings hash: {embeddings_hash}")
            sender = self.context.agent_address
            payload = UpdateFilesPayload(sender=sender, embeddings_hash=embeddings_hash, documents_hash=ZERO_IPFS_HASH)
          
        with self.context.benchmark_tool.measure(self.behaviour_id).consensus():
            yield from self.send_a2a_transaction(payload)
            yield from self.wait_until_round_end()
            self.set_done()
