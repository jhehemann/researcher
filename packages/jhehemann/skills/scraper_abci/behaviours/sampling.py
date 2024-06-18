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

"""Behaviour in which the agents sample a document."""

import random
from typing import Any, Generator, List, Type, Optional

from packages.valory.skills.abstract_round_abci.base import AbstractRound
from packages.jhehemann.skills.scraper_abci.payloads import SamplingPayload
from packages.jhehemann.skills.scraper_abci.rounds import SamplingRound
from packages.jhehemann.skills.scraper_abci.behaviours.base import ScraperBaseBehaviour
from packages.jhehemann.skills.documents_manager_abci.documents import Document, DocumentStatus

class SamplingBehaviour(ScraperBaseBehaviour):  # pylint: disable=too-many-ancestors
    """SamplingBehaviour"""

    matching_round: Type[AbstractRound] = SamplingRound

    def _sampled_doc_idx(self, urls_to_doc: List[Document]) -> int:
        """
        Sample a document and return its id.

        The sampling logic is relatively simple at the moment.
        It simply selects randomly an unprocessed document.

        :param documents: the documents' values to compare for the sampling.
        :return: the id of the sampled document, out of all the available documents, not only the given ones.
        """
        # return a random index of the unprocessed documents
        return self.urls_to_doc.index(random.choice(urls_to_doc))

    def _sample(self) -> Optional[int]:
        """Sample a document, mark it as processed, and return its index."""
        unprocessed_documents = list(self.unprocessed_documents)

        if len(unprocessed_documents) == 0:
            msg = "There were no unprocessed documents available to sample from!"
            self.context.logger.warning(msg)
            return None

        idx = self._sampled_doc_idx(unprocessed_documents)

        # if self.documents[idx].publication_date == :
        #     msg = "There were no unprocessed document with non-zero liquidity!"
        #     self.context.logger.warning(msg)
        #     return None

        # update the document's status for the given id to `PROCESSED`
        self.urls_to_doc[idx].status = DocumentStatus.PROCESSED
        #self.urls_to_doc[idx].status = DocumentStatus.PROCESSED
        msg = f"Sampled document: {self.urls_to_doc[idx]}"
        self.context.logger.info(msg)
        return idx

    def async_act(self) -> Generator:
        """Do the act, supporting asynchronous execution."""

        with self.context.benchmark_tool.measure(self.behaviour_id).local():
            sender = self.context.agent_address
            self.read_urls_to_doc()
            idx = self._sample()
            # self.store_sampled_doc()
            self.store_urls_to_doc()
            if idx is None:
                urls_to_doc_hash = None
            else:
                urls_to_doc_hash = self.hash_stored_urls_to_doc()

            payload = SamplingPayload(sender=sender, urls_to_doc_hash=urls_to_doc_hash, sampled_doc_index=idx)

        with self.context.benchmark_tool.measure(self.behaviour_id).consensus():
            yield from self.send_a2a_transaction(payload)
            yield from self.wait_until_round_end()

        self.set_done()

