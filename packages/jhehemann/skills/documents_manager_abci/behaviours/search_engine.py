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

import os.path
from typing import Any, Generator, Optional, Type, Iterator, List, Set, Tuple

from packages.jhehemann.skills.documents_manager_abci.behaviours.base import (
    UpdateDocumentsBehaviour,
    WaitableConditionType,
)
from packages.jhehemann.skills.documents_manager_abci.models import SearchEngineInteractionResponse, SearchEngineResponseSpecs
from packages.jhehemann.skills.documents_manager_abci.payloads import SearchEnginePayload
from packages.jhehemann.skills.documents_manager_abci.rounds import SearchEngineRound
from packages.valory.skills.abstract_round_abci.base import AbstractRound
from packages.jhehemann.skills.documents_manager_abci.documents import (
    Document,
    DocumentStatus,
)


class SearchEngineBehaviour(UpdateDocumentsBehaviour):  # pylint: disable=too-many-ancestors
    """Behaviour to request URLs from search engine"""

    matching_round: Type[AbstractRound] = SearchEngineRound     

    def __init__(self, **kwargs: Any) -> None:
        """Initialize behaviour."""
        super().__init__(**kwargs)
    
    @property
    def search_engine_response_api(self) -> SearchEngineResponseSpecs:
        """Get the search engine response api specs."""
        return self.context.search_engine_response
    
    def set_search_engine_response_specs(self) -> None:
        """Set the search engine's response specs."""
        api_keys = self.params.api_keys
        google_api_key = api_keys["google_api_key"]
        google_engine_id = api_keys["google_engine_id"]
        query = self.params.input_query
        self.context.logger.info(f"Search query: {query}")

        num = 3

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
        print(f"HEADERS: {self.search_engine_response_api.headers}")

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


    def _fetch_documents(self) -> WaitableConditionType:
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

    def _update_documents(self) -> Generator:
        """Search Google using a custom search engine."""
        
        # # Temporarily used for testing purposes. Remove both lines when done.
        # self.documents = [Document(url="www.google.com", title="Hi", status=DocumentStatus.PROCESSED)]
        # return
        
        self.documents, existing_urls = self.frozen_documents_and_urls

        yield from self.wait_for_condition_with_sleep(self._fetch_documents)

        search_response_items = self._search_engine_response.items
        # print the search response items in pretty format
        # self.context.logger.info(f"Search response items: {json.dumps(search_response_items, indent=4)}")

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
            yield from self._update_documents()
            self.store_documents()
            documents_hash = self.hash_stored_documents()
            self.context.logger.info(f"Documents hash: {documents_hash}")
            payload = SearchEnginePayload(sender=sender, content=documents_hash)

        with self.context.benchmark_tool.measure(self.behaviour_id).consensus():
            yield from self.send_a2a_transaction(payload)
            yield from self.wait_until_round_end()

        self.set_done()
