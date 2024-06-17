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

from packages.jhehemann.skills.documents_manager_abci.payloads import CheckDocumentsPayload
from packages.jhehemann.skills.documents_manager_abci.rounds import CheckDocumentsRound
from packages.jhehemann.skills.documents_manager_abci.behaviours.base import UpdateDocumentsBehaviour
from packages.valory.skills.abstract_round_abci.base import AbstractRound
from packages.jhehemann.skills.documents_manager_abci.behaviours.base import DocumentsManagerBaseBehaviour   
from packages.jhehemann.skills.documents_manager_abci.documents import Document, DocumentStatus


class CheckDocumentsBehaviour(DocumentsManagerBaseBehaviour):
    """Behaviour that fetches and updates the documents."""

    matching_round = CheckDocumentsRound 

    def __init__(self, **kwargs: Any) -> None:
        """Initialize `UpdateDocumentsBehaviour`."""
        super().__init__(**kwargs)
    
    def async_act(self) -> Generator:
        """Do the action."""
        with self.context.benchmark_tool.measure(self.behaviour_id).local():
            self.read_documents()
            unprocessed_docs = list(self.unprocessed_documents)
            num_unprocessed = len(unprocessed_docs)
            self.context
            self.context.logger.info(f"Number of unprocessed documents: {num_unprocessed}")

            payload = CheckDocumentsPayload(
                self.context.agent_address,
                num_unprocessed=num_unprocessed,
            )
        with self.context.benchmark_tool.measure(self.behaviour_id).consensus():
            yield from self.send_a2a_transaction(payload)
            yield from self.wait_until_round_end()
            self.set_done()
