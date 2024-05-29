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
import os.path
from string import Template
from typing import Any, Generator, Optional, Type, Iterator, List, Set, Tuple

# from packages.jhehemann.skills.documents_manager_abci.behaviours.base import (
#     UpdateDocumentsBehaviour,
#     WaitableConditionType,
# )
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


    def _get_embeddings(self) -> WaitableConditionType:
        """Get the response data from embedding."""
        self.set_embedding_response_specs()

        chunks = self.sampled_doc.text_chunks
        self.context.logger.info(f"Text chunks: {chunks}")
        self.context.logger.info(f"Chunks data type: {type(chunks)}")
        model = "text-embedding-3-small"
        specs = self.embedding_response_api.get_spec()
        self.context.logger.info(f"Specs: {specs}")
        
        res_raw = yield from self.get_http_response(
            content=to_content(chunks, model),
            **specs
        )  
        res = self.embedding_response_api.process_response(res_raw)
        res = self._handle_response(res)
        self.context.logger.info(f"Response: {res}")

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

    def _update_sampled_doc(self) -> Generator:
        """Update the sampled document with embeddings."""

        yield from self.wait_for_condition_with_sleep(self._get_embeddings)

        embedding_response_items = self._embedding_response.data
        # print the first 100 and the last 100 characters with ... in between for each item in embedding_response.data in pretty format
        
        
        
        exit()

        if search_response_items is not None:
            initial_docs_count = len(self.documents)
            documents_updates = (
                Document(url=doc['link'], title=doc['title'])
                for doc in search_response_items
                if doc.get("link", "") not in existing_urls
            )
            self.documents.extend(documents_updates)
            
            docs_updated = len(self.documents) > initial_docs_count
            if not docs_updated:
                self.context.logger.warning(f"No new documents were added to the list.")
                return
            
        self.context.logger.info(f"Updated documents: {self.documents}")

    def async_act(self) -> Generator:
        """Do the act, supporting asynchronous execution."""

        with self.context.benchmark_tool.measure(self.behaviour_id).local():
            self.read_documents()
            sender = self.context.agent_address
            yield from self._update_sampled_doc()
            self.store_documents()
            documents_hash = self.hash_stored_documents()
            self.context.logger.info(f"Documents hash: {documents_hash}")
            payload = EmbeddingPayload(sender=sender, content=documents_hash)

        with self.context.benchmark_tool.measure(self.behaviour_id).consensus():
            yield from self.send_a2a_transaction(payload)
            yield from self.wait_until_round_end()

        self.set_done()
