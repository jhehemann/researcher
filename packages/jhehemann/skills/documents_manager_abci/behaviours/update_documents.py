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
from typing import Any, Generator, Iterator, List, Set, Tuple, Type


from packages.jhehemann.skills.documents_manager_abci.payloads import UpdateDocumentsPayload
from packages.jhehemann.skills.documents_manager_abci.rounds import UpdateDocumentsRound
from packages.valory.skills.abstract_round_abci.base import AbstractRound
from packages.jhehemann.skills.documents_manager_abci.behaviours.base import DocumentsManagerBaseBehaviour   
from packages.jhehemann.skills.documents_manager_abci.documents import (
    Document,
    DocumentStatus,
)


# class DocumentsManagerBehaviour(DocumentsManagerBaseBehaviour, ABC):
#     """Abstract behaviour responsible for documents management, such as storing, hashing, reading."""

#     def __init__(self, **kwargs: Any) -> None:
#         """Initialize `DocumentsManagerBehaviour`."""
#         super().__init__(**kwargs)
#         self.documents: List[Document] = []
#         self.documents_filepath: str = os.path.join(self.context.data_dir, DOCUMENTS_FILENAME)


class UpdateDocumentsBehaviour(DocumentsManagerBaseBehaviour):
    """Behaviour that fetches and updates the documents."""

    matching_round = UpdateDocumentsRound

    def __init__(self, **kwargs: Any) -> None:
        """Initialize `UpdateDocumentsBehaviour`."""
        super().__init__(**kwargs)

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
    def frozen_documents_and_ids(self) -> Tuple[List[Document], Set[str]]:
        """Get the ids of the frozen, already existing, documents."""
        documents = []
        ids = set()
        for document in self.frozen_local_documents:
            documents.append(document)
            ids.add(document.id)
        return documents, ids

 
    def async_act(self) -> Generator:
        """Do the action."""
        with self.context.benchmark_tool.measure(self.behaviour_id).local():
            self.read_documents()
            unprocessed_docs = list(self.unprocessed_documents)
            num_unprocessed = len(unprocessed_docs)
            self.context.logger.info(f"Number of unprocessed documents: {num_unprocessed}")
            payload = UpdateDocumentsPayload(self.context.agent_address, num_unprocessed)

        with self.context.benchmark_tool.measure(self.behaviour_id).consensus():
            yield from self.send_a2a_transaction(payload)
            yield from self.wait_until_round_end()
            self.set_done()
