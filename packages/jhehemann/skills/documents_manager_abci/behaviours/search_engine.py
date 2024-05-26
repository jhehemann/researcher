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

"""This module contains the behaviour for getting links from a search engine."""

import json
import os.path
from abc import ABC
from json import JSONDecodeError
from typing import Any, Generator, Optional, Type, Iterator, List, Set, Tuple

from aea.helpers.ipfs.base import IPFSHashOnly

from packages.jhehemann.skills.documents_manager_abci.behaviours.base import DocumentsManagerBaseBehaviour, WaitableConditionType
from packages.jhehemann.skills.documents_manager_abci.models import SearchEngineInteractionResponse, SearchEngineResponseSpecs
from packages.jhehemann.skills.documents_manager_abci.payloads import SearchEnginePayload
from packages.jhehemann.skills.documents_manager_abci.rounds import SearchEngineRound
from packages.valory.skills.abstract_round_abci.base import AbstractRound
from packages.jhehemann.skills.documents_manager_abci.documents import (
    Document,
    DocumentStatus,
    DocumentsDecoder,
    serialize_documents,
)


DOCUMENTS_FILENAME = "documents.json"
READ_MODE = "r"
WRITE_MODE = "w"


class DocumentsManagerBehaviour(DocumentsManagerBaseBehaviour, ABC):
    """Abstract behaviour responsible for documents management, such as storing, hashing, reading."""

    def __init__(self, **kwargs: Any) -> None:
        """Initialize `DocumentsManagerBehaviour`."""
        super().__init__(**kwargs)
        self.documents: List[Document] = []
        self.documents_filepath: str = os.path.join(self.context.data_dir, DOCUMENTS_FILENAME)

    def store_documents(self) -> None:
        """Store the documents to the agent's data dir as JSON."""
        serialized = serialize_documents(self.documents)
        if serialized is None:
            self.context.logger.warning("No documents to store.")
            return

        try:
            with open(self.documents_filepath, WRITE_MODE) as documents_file:
                try:
                    documents_file.write(serialized)
                    return
                except (IOError, OSError):
                    err = f"Error writing to file {self.documents_filepath!r}!"
        except (FileNotFoundError, PermissionError, OSError):
            err = f"Error opening file {self.documents_filepath!r} in write mode!"

        self.context.logger.error(err)

    def read_documents(self) -> None:
        """Read the documents from the agent's data dir as JSON."""
        self.documents = []

        if not os.path.isfile(self.documents_filepath):
            self.context.logger.warning(
                f"No stored documents file was detected in {self.documents_filepath}. Assuming documents are empty."
            )
            return

        try:
            with open(self.documents_filepath, READ_MODE) as documents_file:
                try:
                    self.documents = json.load(documents_file, cls=DocumentsDecoder)
                    return
                except (JSONDecodeError, TypeError):
                    err = (
                        f"Error decoding file {self.documents_filepath!r} to a list of documents!"
                    )
        except (FileNotFoundError, PermissionError, OSError):
            err = f"Error opening file {self.documents_filepath!r} in read mode!"

        self.context.logger.error(err)

    def hash_stored_documents(self) -> str:
        """Get the hash of the stored documents' file."""
        return IPFSHashOnly.hash_file(self.documents_filepath)


class SearchEngineBehaviour(DocumentsManagerBehaviour):  # pylint: disable=too-many-ancestors
    """Behaviour to request URLs from search engine"""

    matching_round: Type[AbstractRound] = SearchEngineRound     

    def __init__(self, **kwargs: Any) -> None:
        """Initialize behaviour."""
        super().__init__(**kwargs)
        self._search_engine_response: Optional[SearchEngineInteractionResponse] = None
        self.documents: List[Document] = []
        self.documents_filepath: str = os.path.join(self.context.data_dir, DOCUMENTS_FILENAME)
    
    @property
    def search_engine_response_api(self) -> SearchEngineResponseSpecs:
        """Get the search engine response api specs."""
        return self.context.search_engine_response
    
    def set_search_engine_response_specs(self) -> None:
        """Set the search engine's response specs."""
        api_keys = self.params.api_keys
        google_api_key = api_keys["google_api_key"]
        google_engine_id = api_keys["google_engine_id"]
        query = self.synchronized_data.hello_data
        num = 1

        parameters = {
            "key": google_api_key,
            "cx": google_engine_id,
            "q": query,
            "num": num,
        }
        # The url must be dynamically generated as it depends on the ipfs hash
        self.search_engine_response_api.__dict__["_frozen"] = False
        self.search_engine_response_api.parameters = parameters
        self.search_engine_response_api.__dict__["_frozen"] = True

    def is_frozen_document(self, document: Document) -> bool:
        """Return if a document should not be updated."""
        return (
            document.blacklist_expiration > self.synced_time
            and document.status == DocumentStatus.BLACKLISTED
        ) or document.status == DocumentStatus.PROCESSED

    @property
    def frozen_local_documents(self) -> Iterator[Document]:
        """Get the frozen, already existing, documents."""
        return filter(self.is_frozen_document, self.documents)

    @property
    def frozen_documents_and_urls(self) -> Tuple[List[Document], Set[str]]:
        """Get the urls of the frozen, already existing, documents."""
        documents = []
        urls = set()
        for document in self.frozen_local_documents:
            documents.append(document)
            urls.add(document.url)
        return documents, urls

    def _handle_response(
        self,
        res: Optional[str],
    ) -> Optional[Any]:
        """Handle the response from the search engine.

        :param res: the response to handle.
        :return: the response's result, using the given keys. `None` if response is `None` (has failed).
        """
        if res is None:
            msg = f"Could not get the search engine's response from {self.search_engine_response_api.api_id}"
            self.context.logger.error(msg)
            self.search_engine_response_api.increment_retries()
            return None

        self.context.logger.info(f"Retrieved the search engine's response.")
        self.search_engine_response_api.reset_retries()
        return res


    def _get_response(self) -> WaitableConditionType:
        """Get the response data from search engine."""
        self.set_search_engine_response_specs()
        specs = self.search_engine_response_api.get_spec()
        
        res_raw = yield from self.get_http_response(**specs)  
        res = self.search_engine_response_api.process_response(res_raw)
        res = self._handle_response(res)

        if self.search_engine_response_api.is_retries_exceeded():
            error = "Retries were exceeded while trying to get the search engines's response."
            self._search_engine_response = SearchEngineInteractionResponse(error=error)
            return True

        if res is None:
            return False
        
        try:
            self._search_engine_response = SearchEngineInteractionResponse(**res)
        except (ValueError, TypeError, KeyError):
            self._search_engine_response = SearchEngineInteractionResponse.incorrect_format(res)

        return True

    def get_payload_content(self, query: str) -> Generator:
        """Search Google using a custom search engine."""
        yield from self.wait_for_condition_with_sleep(self._get_response)

        search_response_items = self._search_engine_response.items
        links_list = [
            item['link'] for item in search_response_items if 'link' in item
        ]
        
        # Use a pipe as a separator for joining as it is not a valid character in a URL
        links_string = '|'.join(links_list)
        self.context.logger.info(f"Response links: {links_string}")
                
        return links_string


    def async_act(self) -> Generator:
        """Do the act, supporting asynchronous execution."""

        with self.context.benchmark_tool.measure(self.behaviour_id).local():
            self.read_documents()
            
            sender = self.context.agent_address
            search_query = self.synchronized_data.hello_data
            payload_content = yield from self.get_payload_content(search_query)
            payload = SearchEnginePayload(sender=sender, content=payload_content)

        with self.context.benchmark_tool.measure(self.behaviour_id).consensus():
            yield from self.send_a2a_transaction(payload)
            yield from self.wait_until_round_end()

        self.set_done()


# class UpdateDocumentsBehaviour(DocumentsManagerBehaviour, QueryingBehaviour):
#     """Behaviour that fetches and updates the documents."""

#     matching_round = UpdateDocumentsRound

#     def __init__(self, **kwargs: Any) -> None:
#         """Initialize `UpdateDocumentsBehaviour`."""
#         super().__init__(**kwargs)

    

#     def _update_documents(
#         self,
#     ) -> Generator:
#         """Fetch the questions from all the prediction markets and update the local copy of the documents."""
#         self.documents, existing_ids = self.frozen_documents_and_urls

#         while True:
#             can_proceed = self._prepare_fetching()
#             if not can_proceed:
#                 break

#             documents_market_chunk = yield from self._fetch_documents()
#             if documents_market_chunk is not None:
#                 documents_updates = (
#                     Document(**document, market=self._current_market)
#                     for document in documents_market_chunk
#                     if document.get("id", "") not in existing_ids
#                 )
#                 self.documents.extend(documents_updates)

#         if self._fetch_status != FetchStatus.SUCCESS:
#             self.documents = []

#         self.context.logger.info(f"Updated documents: {self.documents}")

#     def async_act(self) -> Generator:
#         """Do the action."""
#         with self.context.benchmark_tool.measure(self.behaviour_id).local():
#             self.read_documents()
#             yield from self._update_documents()
#             self.store_documents()
#             documents_hash = self.hash_stored_documents()
#             payload = UpdateDocumentsPayload(self.context.agent_address, documents_hash)

#         with self.context.benchmark_tool.measure(self.behaviour_id).consensus():
#             yield from self.send_a2a_transaction(payload)
#             yield from self.wait_until_round_end()
#             self.set_done()