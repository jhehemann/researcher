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

"""This module contains the base behaviour for the 'scraper_abci' skill."""

import os
import json
from abc import ABC
from json import JSONDecodeError
from datetime import datetime, timedelta
from typing import Any, Callable, Generator, Iterator, Optional, Set, Type, cast, List

from packages.valory.skills.abstract_round_abci.behaviours import (
    AbstractRoundBehaviour,
    BaseBehaviour,
)
from packages.jhehemann.skills.documents_manager_abci.models import DocumentsManagerParams, SharedState
from packages.jhehemann.skills.documents_manager_abci.rounds import (
    DocumentsManagerAbciApp,
    UpdateDocumentsRound,
    SearchEngineRound,
    SynchronizedData,
)
from packages.jhehemann.skills.documents_manager_abci.documents import (
    Document,
    DocumentStatus,
    DocumentsDecoder,
    serialize_documents,
)
from packages.valory.skills.abstract_round_abci.behaviour_utils import TimeoutException

from aea.helpers.ipfs.base import IPFSHashOnly

UNIX_DAY = 60 * 60 * 24
DOCUMENTS_FILENAME = "documents.json"
READ_MODE = "r"
WRITE_MODE = "w"

WaitableConditionType = Generator[None, None, bool]

class DocumentsManagerBaseBehaviour(BaseBehaviour, ABC):  # pylint: disable=too-many-ancestors
    """Base behaviour for the scraper_abci skill."""

    def __init__(self, **kwargs: Any) -> None:
        """Initialize behaviour."""
        super().__init__(**kwargs)
        self.documents: List[Document] = []
        self.documents_filepath: str = os.path.join(self.context.data_dir, DOCUMENTS_FILENAME)
    # @property
    # def synchronized_data(self) -> SynchronizedData:
    #     """Return the synchronized data."""
    #     return cast(SynchronizedData, super().synchronized_data)
    
    # @property
    # def params(self) -> DocumentsManagerParams:
    #     """Get the parameters."""
    #     return cast(DocumentsManagerParams, self.context.params)
    
    # @property
    # def local_state(self) -> SharedState:
    #     """Return the state."""
    #     return cast(SharedState, self.context.state)
    
    @property
    def unprocessed_documents(self) -> Iterator[Document]:
        """Get an iterator of the unprocessed documents."""
        self.documents = [document for document in self.documents]
        return filter(lambda document: document.status == DocumentStatus.UNPROCESSED, self.documents)
    
        
    def wait_for_condition_with_sleep(
        self,
        condition_gen: Callable[[], WaitableConditionType],
        timeout: Optional[float] = None,
    ) -> Generator[None, None, None]:
        """Wait for a condition to happen and sleep in-between checks.

        This is a modified version of the base `wait_for_condition` method which:
            1. accepts a generator that creates the condition instead of a callable
            2. sleeps in-between checks

        :param condition_gen: a generator of the condition to wait for
        :param timeout: the maximum amount of time to wait
        :yield: None
        """

        deadline = (
            datetime.now() + timedelta(0, timeout)
            if timeout is not None
            else datetime.max
        )

        while True:
            condition_satisfied = yield from condition_gen()
            if condition_satisfied:
                break
            if timeout is not None and datetime.now() > deadline:
                raise TimeoutException()
            self.context.logger.info(f"Retrying in {self.params.sleep_time} seconds.")
            yield from self.sleep(self.params.sleep_time)

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


