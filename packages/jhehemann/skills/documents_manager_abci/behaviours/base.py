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
import pandas as pd
from abc import ABC
from json import JSONDecodeError
from datetime import datetime, timedelta
from typing import Any, Callable, Generator, Iterator, Optional, Set, Tuple, cast, List, Dict

from packages.valory.skills.abstract_round_abci.behaviours import (
    BaseBehaviour,
)
from packages.jhehemann.skills.documents_manager_abci.rounds import (
    UpdateDocumentsRound,
    SynchronizedData,
)
from packages.jhehemann.skills.documents_manager_abci.documents import (
    Document,
    DocumentStatus,
    DocumentsDecoder,
    serialize_documents,
    DocumentMapping,
    DocumentsMappingDecoder,
    serialize_document_mappings,
)
from packages.jhehemann.skills.documents_manager_abci.queries import (
    Query,
    QueryStatus,
    QueriesDecoder,
    serialize_queries,
)
from packages.valory.skills.abstract_round_abci.behaviour_utils import TimeoutException

from aea.helpers.ipfs.base import IPFSHashOnly

UNIX_DAY = 60 * 60 * 24
SAMPLED_DOCUMENT_FILENAME = "sampled_doc.json"
URLS_TO_DOC_FILENAME = "urls_to_doc.json"
IPFS_HASHES_FILENAME = "ipfs_hashes.json"
EMBEDDINGS_FILENAME = "embeddings.parquet"
QUERIES_FILENAME = "queries.json"
READ_MODE = "r"
WRITE_MODE = "w"


WaitableConditionType = Generator[None, None, bool]

class DocumentsManagerBaseBehaviour(BaseBehaviour, ABC):  # pylint: disable=too-many-ancestors
    """Base behaviour for the scraper_abci skill."""

    def __init__(self, **kwargs: Any) -> None:
        """Initialize behaviour."""
        super().__init__(**kwargs)
        self.queries: List[Query] = []
        self.sampled_doc: Document = Document(url="")
        self.urls_to_doc: List[DocumentMapping] = []
        self.embeddings: pd.DataFrame = pd.DataFrame()
        self.ipfs_hashes: Dict[str, str] = {}
        self.queries_filepath: str = os.path.join(self.context.data_dir, QUERIES_FILENAME)
        self.sampled_doc_filepath: str = os.path.join(self.context.data_dir, SAMPLED_DOCUMENT_FILENAME)
        self.urls_to_doc_filepath: str = os.path.join(self.context.data_dir, URLS_TO_DOC_FILENAME)
        self.embeddings_filepath: str = os.path.join(self.context.data_dir, EMBEDDINGS_FILENAME)
        self.ipfs_hashes_filepath: str = os.path.join(self.context.data_dir, IPFS_HASHES_FILENAME)
        
    @property
    def synchronized_data(self) -> SynchronizedData:
        """Return the synchronized data."""
        return cast(SynchronizedData, super().synchronized_data)
    
    # @property
    # def params(self) -> DocumentsManagerParams:
    #     """Get the parameters."""
    #     return cast(DocumentsManagerParams, self.context.params)
    
    # @property
    # def local_state(self) -> SharedState:
    #     """Return the state."""
    #     return cast(SharedState, self.context.state)

    # @property
    # def embeddings_filepath(self) -> str:
    #     """Get the filepath to the metadata."""
    #     return str(Path(mkdtemp()) / EMBEDDINGS_FILENAME)
    
    @property
    def unprocessed_documents(self) -> Iterator[DocumentMapping]:
        """Get an iterator of the unprocessed documents."""
        self.urls_to_doc = [doc_map for doc_map in self.urls_to_doc]
        return filter(lambda doc_map: doc_map.status == DocumentStatus.UNPROCESSED, self.urls_to_doc)
    
    @property
    def unprocessed_queries(self) -> Iterator[Query]:
        """Get an iterator of the unprocessed queries."""
        self.queries = [query for query in self.queries]
        return filter(lambda query: query.status == QueryStatus.UNPROCESSED, self.queries)

    @property
    def synced_time(self) -> int:
        """Get the synchronized time among agents."""
        synced_time = self.shared_state.round_sequence.last_round_transition_timestamp
        return int(synced_time.timestamp())
    
    @property
    def sampled_query(self) -> Document:
        """Get the sampled query."""
        self.read_queries()
        return self.queries[self.synchronized_data.sampled_query_idx]
    
    def read_ipfs_hashes(self) -> None:
        """Read the IPFS hashes from the agent's data dir."""
        if not os.path.isfile(self.ipfs_hashes_filepath):
            self.context.logger.warning(
                f"No stored IPFS hashes file was detected in {self.ipfs_hashes_filepath}. Assuming local hashes are empty."
            )
            return
        
        try:
            with open(self.ipfs_hashes_filepath, READ_MODE) as ipfs_hashes_file:
                try:
                    self.ipfs_hashes = json.load(ipfs_hashes_file)
                    return
                except (JSONDecodeError, TypeError):
                    err = f"Error decoding file {self.ipfs_hashes_filepath!r} to a dictionary of IPFS hashes!"
        except (FileNotFoundError, PermissionError, OSError):
            err = f"Error opening file {self.ipfs_hashes_filepath!r} in read mode!"

        self.context.logger.error(err)

    def read_queries(self) -> None:
        """Read the queries from the agent's data dir as JSON."""
        self.queries = []

        if not os.path.isfile(self.queries_filepath):
            self.context.logger.warning(
                f"No stored queries file was detected in {self.queries_filepath}. Assuming local queries are empty."
            )
            return

        try:
            with open(self.queries_filepath, READ_MODE) as queries_file:
                try:
                    self.queries = json.load(queries_file, cls=QueriesDecoder)
                    return
                except (JSONDecodeError, TypeError):
                    err = f"Error decoding file {self.queries_filepath!r} to a list of queries!"
        except (FileNotFoundError, PermissionError, OSError):
            err = f"Error opening file {self.queries_filepath!r} in read mode!"

        self.context.logger.error(err)

    def read_urls_to_doc(self) -> None:
        """Read the urls_to_doc from the agent's data dir as JSON."""
        self.urls_to_doc = []

        if not os.path.isfile(self.urls_to_doc_filepath):
            self.context.logger.warning(
                f"No stored urls_to_doc file was detected in {self.urls_to_doc_filepath}. Assuming local urls_to_doc are empty."
            )
            return

        try:
            with open(self.urls_to_doc_filepath, READ_MODE) as urls_to_doc_file:
                try:
                    self.urls_to_doc = json.load(urls_to_doc_file, cls=DocumentsMappingDecoder)
                    return
                except (JSONDecodeError, TypeError):
                    err = (
                        f"Error decoding file {self.urls_to_doc_filepath!r} to a list of urls_to_doc!"
                    )
        except (FileNotFoundError, PermissionError, OSError):
            err = f"Error opening file {self.urls_to_doc_filepath!r} in read mode!"

        self.context.logger.error(err)


    def read_sampled_doc(self) -> None:
        """Read the sampled_doc from the agent's data dir as JSON."""
        self.sampled_doc = []

        if not os.path.isfile(self.sampled_doc_filepath):
            self.context.logger.warning(
                f"No stored sampled_doc file was detected in {self.sampled_doc_filepath}. Assuming local sampled_doc is empty."
            )
            return

        try:
            with open(self.sampled_doc_filepath, READ_MODE) as sampled_doc_file:
                try:
                    self.sampled_doc = json.load(sampled_doc_file, cls=DocumentsDecoder)
                    return
                except (JSONDecodeError, TypeError):
                    err = (
                        f"Error decoding file {self.sampled_doc_filepath!r} to a document!"
                    )
        except (FileNotFoundError, PermissionError, OSError):
            err = f"Error opening file {self.sampled_doc_filepath!r} in read mode!"

        self.context.logger.error(err)

    def read_embeddings(self) -> None:
        """Read the embeddings from the agent's data dir as Parquet."""
        if not os.path.isfile(self.embeddings_filepath):
            self.context.logger.warning(
                f"No stored embeddings file was detected in {self.embeddings_filepath}. Assuming local embeddings are empty."
            )
            return

        try:
            self.embeddings = pd.read_parquet(self.embeddings_filepath)
            return
        except Exception as e:
            err = f"Error reading file {self.embeddings_filepath!r}: {e}"
            self.context.logger.error(err)
    
    def store_ipfs_hashes(self) -> None:
        """Store the IPFS hashes to the agent's data dir as JSON."""
        if not self.ipfs_hashes:
            self.context.logger.warning("No IPFS hashes to store locally.")
            return

        try:
            with open(self.ipfs_hashes_filepath, WRITE_MODE) as ipfs_hashes_file:
                try:
                    json.dump(self.ipfs_hashes, ipfs_hashes_file)
                    return
                except (IOError, OSError):
                    err = f"Error writing to file {self.ipfs_hashes_filepath!r}!"
        except (FileNotFoundError, PermissionError, OSError):
            err = f"Error opening file {self.ipfs_hashes_filepath!r} in write mode!"

        self.context.logger.error(err)

    def store_queries(self) -> None:
        """Store the queries to the agent's data dir as JSON."""
        serialized = serialize_queries(self.queries)
        if serialized is None:
            self.context.logger.warning("No queries to store locally.")
            return

        try:
            with open(self.queries_filepath, WRITE_MODE) as queries_file:
                try:
                    queries_file.write(serialized)
                    return
                except (IOError, OSError):
                    err = f"Error writing to file {self.queries_filepath!r}!"
        except (FileNotFoundError, PermissionError, OSError):
            err = f"Error opening file {self.queries_filepath!r} in write mode!"

        self.context.logger.error(err)

    def store_urls_to_doc(self) -> None:
        """Store the urls_to_doc to the agent's data dir as JSON."""
        serialized = serialize_document_mappings(self.urls_to_doc)
        if serialized is None:
            self.context.logger.warning("No urls_to_doc to store locally.")
            return

        try:
            with open(self.urls_to_doc_filepath, WRITE_MODE) as urls_to_doc_file:
                try:
                    urls_to_doc_file.write(serialized)
                    return
                except (IOError, OSError):
                    err = f"Error writing to file {self.urls_to_doc_filepath!r}!"
        except (FileNotFoundError, PermissionError, OSError):
            err = f"Error opening file {self.urls_to_doc_filepath!r} in write mode!"

        self.context.logger.error(err)
        

    def store_sampled_doc(self) -> None:
        """Store the sampled_doc to the agent's data dir as JSON."""
        serialized = serialize_documents(self.sampled_doc)
        if serialized is None:
            self.context.logger.warning("No sampled_doc to store locally.")
            return

        try:
            with open(self.sampled_doc_filepath, WRITE_MODE) as sampled_doc_file:
                try:
                    sampled_doc_file.write(serialized)
                    return
                except (IOError, OSError):
                    err = f"Error writing to file {self.sampled_doc_filepath!r}!"
        except (FileNotFoundError, PermissionError, OSError):
            err = f"Error opening file {self.sampled_doc_filepath!r} in write mode!"

        self.context.logger.error(err)

    def store_embeddings(self) -> None:
        """Store the embeddings to the agent's data dir as Parquet."""
        if self.embeddings.empty:
            self.context.logger.warning("No embeddings to store locally.")
            return

        try:
            self.embeddings.to_parquet(self.embeddings_filepath, compression="snappy", index=True)
            return
        except Exception as e:
            err = f"Error writing to file {self.embeddings_filepath!r}: {e}"
            self.context.logger.error(err)

    def hash_stored_ipfs_hashes(self) -> str:
        """Get the hash of the stored IPFS hashes' file."""
        if not os.path.isfile(self.ipfs_hashes_filepath):
            self.context.logger.warning(
                f"No stored IPFS hashes file was detected in {self.ipfs_hashes_filepath}. Assuming local hashes are empty."
            )
            return ""
        return IPFSHashOnly.hash_file(self.ipfs_hashes_filepath)

    def hash_stored_queries(self) -> str:
        """Get the hash of the stored queries' file."""
        if not os.path.isfile(self.queries_filepath):
            self.context.logger.warning(
                f"No stored queries file was detected in {self.queries_filepath}. Assuming local queries are empty."
            )
            return ""
        return IPFSHashOnly.hash_file(self.queries_filepath)
    
    def hash_stored_sampled_doc(self) -> str:
        """Get the hash of the stored documents' file."""
        if not os.path.isfile(self.sampled_doc_filepath):
            self.context.logger.warning(
                f"No stored documents file was detected in {self.sampled_doc_filepath}. Assuming local documents are empty."
            )
            return ""
        return IPFSHashOnly.hash_file(self.sampled_doc_filepath)

    def hash_stored_urls_to_doc(self) -> str:
        """Get the hash of the stored documents' file."""
        if not os.path.isfile(self.urls_to_doc_filepath):
            self.context.logger.warning(
                f"No stored urls_to_doc file was detected in {self.urls_to_doc_filepath}. Assuming local urls_to_doc are empty."
            )
            return ""
        return IPFSHashOnly.hash_file(self.urls_to_doc_filepath)

    def hash_stored_embeddings(self) -> str:
        """Get the hash of the stored embeddings' file."""
        if not os.path.isfile(self.embeddings_filepath):
            self.context.logger.warning(
                f"No stored embeddings file was detected in {self.embeddings_filepath}. Assuming local embeddings are empty."
            )
            return ""
        return IPFSHashOnly.hash_file(self.embeddings_filepath)
    

class UpdateDocumentsBehaviour(DocumentsManagerBaseBehaviour):
    """Behaviour that fetches and updates the documents."""

    matching_round = UpdateDocumentsRound

    def __init__(self, **kwargs: Any) -> None:
        """Initialize `UpdateDocumentsBehaviour`."""
        super().__init__(**kwargs)

    @property
    def frozen_local_urls_to_doc(self) -> Iterator[DocumentMapping]:
        """Get the frozen, already existing, documents."""
        return filter(self.is_frozen_urls_to_doc, self.urls_to_doc)

    @property
    def frozen_urls_to_doc_and_urls(self) -> Tuple[List[DocumentMapping], Set[str]]:
        """Get the urls of the frozen, already existing, urls_to_doc."""
        mapping = []
        urls = set()
        for map in self.frozen_local_urls_to_doc:
            mapping.append(map)
            urls.add(map.url)
        return mapping, urls
    
    def is_frozen_urls_to_doc(self, urls_to_doc: DocumentMapping) -> bool:
        """Return if a document should not be updated."""
        return (
            #urls_to_doc.blacklist_expiration > self.synced_time
            urls_to_doc.status == DocumentStatus.BLACKLISTED
        ) or urls_to_doc.status == DocumentStatus.PROCESSED
    
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