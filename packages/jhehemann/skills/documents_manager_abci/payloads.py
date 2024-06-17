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

"""This module contains the transaction payloads of the ScraperAbciApp."""

from abc import ABC
from dataclasses import dataclass
from typing import Optional

from packages.valory.skills.abstract_round_abci.base import BaseTxPayload

@dataclass(frozen=True)
class UpdateQueriesPayload(BaseTxPayload, ABC):
    """Represent a transaction payload for the UpdateQueriesRound."""

    queries_hash: Optional[str]

@dataclass(frozen=True)
class UpdateFilesPayload(BaseTxPayload, ABC):
    """Represent a transaction payload for the UpdateFilesRound."""

    documents_hash: Optional[str]
    embeddings_hash: Optional[str]

@dataclass(frozen=True)
class UpdateDocumentsPayload(BaseTxPayload, ABC):
    """Represent a transaction payload for the UpdateDocumentsRound."""

    documents_hash: Optional[str]

@dataclass(frozen=True)
class CheckDocumentsPayload(BaseTxPayload):
    """Represent a transaction payload for the UpdateDocumentsRound."""

    num_unprocessed: Optional[int]

@dataclass(frozen=True)
class SampleQueryPayload(BaseTxPayload):
    """Represent a transaction payload for the SampleQueryRound."""

    queries_hash: str
    sampled_query_idx: str

@dataclass(frozen=True)
class SearchEnginePayload(BaseTxPayload):
    """Represent a transaction payload for the SearchEngineRound."""

    content: str
