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

"""This module contains the behaviour for getting links from a embedding."""

import json
from pathlib import Path
from tempfile import mkdtemp
import pandas as pd
import os.path
from string import Template
from typing import Any, Generator, Optional, Type, Iterator, List, Set, Tuple

from aea.helpers.cid import CID, to_v1

from packages.valory.skills.abstract_round_abci.io_.store import SupportedFiletype
from packages.jhehemann.skills.documents_manager_abci.behaviours.base import WaitableConditionType
from packages.jhehemann.skills.scraper_abci.behaviours.base import ScraperBaseBehaviour
from packages.jhehemann.skills.scraper_abci.models import EmbeddingInteractionResponse, EmbeddingResponseSpecs
from packages.jhehemann.skills.scraper_abci.payloads import EmbeddingPayload
from packages.jhehemann.skills.scraper_abci.rounds import EmbeddingRound
from packages.valory.skills.abstract_round_abci.base import AbstractRound
from packages.jhehemann.skills.documents_manager_abci.documents import (
    Document,
    DocumentStatus,
)

# IPFSFILENAME = "embeddings.parquet"

def to_content(input: list, model: str) -> bytes:
    """Convert the given query string to payload content, i.e., add it under a `queries` key and convert it to bytes."""
    finalized_query = {
        "input": input,
        "model": model
    }
    encoded_query = json.dumps(finalized_query, sort_keys=True).encode("utf-8")

    return encoded_query

def to_openai_list(li: list) -> str:
    """Convert the given list to a string representing a list for a GraphQL query."""
    return repr(li).replace("'", '"')


class EmbeddingBehaviour(ScraperBaseBehaviour):  # pylint: disable=too-many-ancestors
    """Behaviour to request URLs from embedding"""

    matching_round: Type[AbstractRound] = EmbeddingRound     

    def __init__(self, **kwargs: Any) -> None:
        """Initialize behaviour."""
        super().__init__(**kwargs)

    # @property
    # def embeddings_filepath(self) -> str:
    #     """Get the filepath to the embeddings."""
    #     return str(Path(mkdtemp()) / IPFSFILENAME)
    
    @property
    def embedding_response_api(self) -> EmbeddingResponseSpecs:
        """Get the embedding response api specs."""
        return self.context.embedding_response
    
    def set_embedding_response_specs(self) -> None:
        """Set the embedding's response specs."""
        api_keys = self.params.api_keys
        openai_api_key = api_keys["openai"]

        # The url must be dynamically generated as it depends on the ipfs hash
        self.embedding_response_api.__dict__["_frozen"] = False
        self.embedding_response_api.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {openai_api_key}"
        }
        self.embedding_response_api.__dict__["_frozen"] = True

    def _handle_response(
        self,
        res: Optional[str],
    ) -> Optional[Any]:
        """Handle the response from the embedding.

        :param res: the response to handle.
        :return: the response's result, using the given keys. `None` if response is `None` (has failed).
        """
        if res is None:
            msg = f"Could not get the embedding's response from {self.embedding_response_api.api_id}"
            self.context.logger.error(msg)
            self.embedding_response_api.increment_retries()
            return None

        self.context.logger.info(f"Retrieved the embedding's response.")
        self.embedding_response_api.reset_retries()
        return res

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
        self.context.logger.info(
            f"Total new embeddings: {self.embeddings.shape}"
        )
        self.context.logger.info(
            f"\n{self.embeddings}"
        )        

    def _get_embeddings(self) -> WaitableConditionType:
        """Get the response data from embedding."""
        self.set_embedding_response_specs()

        specs = self.embedding_response_api.get_spec()
        chunks = self.sampled_doc.text_chunks
        model = "text-embedding-3-small"

        res_raw = yield from self.get_http_response(
            content=to_content(chunks, model),
            **specs
        )  
        res = self.embedding_response_api.process_response(res_raw)
        res = self._handle_response(res)
        # self.context.logger.info(f"Response: {res}")

        if self.embedding_response_api.is_retries_exceeded():
            error = "Retries were exceeded while trying to get the embeddings's response."
            self._embedding_response = EmbeddingInteractionResponse(error=error)
            return True

        if res is None:
            return False
        
        try:
            self._embedding_response = EmbeddingInteractionResponse(**res)
        except (ValueError, TypeError, KeyError):
            self._embedding_response = EmbeddingInteractionResponse.incorrect_format(res)

        return True

    def load_latest_embeddings(self) -> Generator:
        """Get the latest embeddings from IPFS."""
        ipfs_hash = self.params.publish_mutable_params.latest_embeddings_hash
        self.context.logger.info(f"Latest embeddings hash: {ipfs_hash}")
        if ipfs_hash is None:
            self.context.logger.warning(
                "No embeddings hash found. Assuming no embeddings are stored on IPFS."
            )
            return

        ipfs_hash = str(CID.from_string(ipfs_hash))
        self.context.logger.info(f"Getting embeddings from IPFS with cid hash: {ipfs_hash}")
        embeddings_json = yield from self.get_from_ipfs(
            ipfs_hash, filetype=SupportedFiletype.JSON
        )
        if embeddings_json is None:
            self.context.logger.warning(
                f"Could not get embeddings from IPFS: {ipfs_hash}"
            )
            return
        
        embeddings = pd.DataFrame(embeddings_json)
        self.context.logger.info(f"Downloaded embeddings dataframe: {embeddings.shape}")
        self.embeddings = embeddings

    def async_act(self) -> Generator:
        """Do the act, supporting asynchronous execution."""

        with self.context.benchmark_tool.measure(self.behaviour_id).local():
            yield from self.load_latest_embeddings()
            self.store_embeddings()
            embeddings_hash_prev = self.hash_stored_embeddings()
            self.read_documents()
            yield from self.wait_for_condition_with_sleep(self._get_embeddings)
            self.update_embeddings()
            self.store_embeddings()
            embeddings_hash = self.hash_stored_embeddings()
            if  embeddings_hash != embeddings_hash_prev:
                self.context.logger.info(f"Updated local embeddings hash: {embeddings_hash}")
            else:
                self.context.logger.info("No new embeddings were added.")

            sender = self.context.agent_address
            payload = EmbeddingPayload(sender=sender, content=embeddings_hash)

        with self.context.benchmark_tool.measure(self.behaviour_id).consensus():
            yield from self.send_a2a_transaction(payload)
            yield from self.wait_until_round_end()

        self.set_done()
