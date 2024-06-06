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

"""This package contains the rounds of ScraperAbciApp."""

from enum import Enum
from typing import Any, Dict, FrozenSet, Optional, Set

from packages.jhehemann.skills.scraper_abci.payloads import (
    SamplingPayload,
    WebScrapePayload,
    ProcessHtmlPayload,
    EmbeddingPayload,
    PublishPayload,
)

from packages.valory.skills.abstract_round_abci.base import (
    AbciApp,
    AbciAppTransitionFunction,
    AppState,
    BaseSynchronizedData,
    CollectSameUntilThresholdRound,
    CollectionRound,
    DegenerateRound,
    DeserializedCollection,
    EventToTimeout,
    get_name,
)
from packages.jhehemann.skills.documents_manager_abci.rounds import (
    UpdateDocumentsRound,
    SynchronizedData as DocumentsManagerSyncedData,
)


class Event(Enum):
    """ScraperAbciApp Events"""

    DONE = "done"
    NONE = "none"
    NO_MAJORITY = "no_majority"
    ROUND_TIMEOUT = "round_timeout"


class SynchronizedData(DocumentsManagerSyncedData):
    """
    Class to represent the synchronized data.

    This data is replicated by the tendermint application.
    """

    def _get_deserialized(self, key: str) -> DeserializedCollection:
        """Strictly get a collection and return it deserialized."""
        serialized = self.db.get_strict(key)
        return CollectionRound.deserialize_collection(serialized)

    @property
    def sampled_doc_index(self) -> int:
        """Get the index of the sampled document."""
        return int(self.db.get_strict("sampled_doc_index"))
    
    @property
    def web_scrape_data(self) -> Optional[str]:
        """Get the web_scrape_data."""
        return self.db.get("web_scrape_data", None)

    @property
    def process_html_data(self) -> Optional[str]:
        """Get the process_html_data."""
        return self.db.get("process_html_data", None)
    
    @property
    def embeddings(self) -> Optional[str]:
        """Get the embeddings."""
        return self.db.get("embeddings", None)
    
    @property
    def embeddings_hash(self) -> str:
        """Get the embeddings hash."""
        return self.db.get("embeddings_hash", None)
    
    @property
    def embeddings_ipfs_link(self) -> str:
        """Get the embeddings ipfs link."""
        return self.db.get("embeddings_ipfs_link", None)
    
    @property
    def participant_to_web_scrape_round(self) -> DeserializedCollection:
        """Get the participants to the web_scrape round."""
        return self._get_deserialized("participant_to_web_scrape_round")
    
    @property
    def participant_to_process_html_round(self) -> DeserializedCollection:
        """Get the participants to the participant_to_process_html round."""
        return self._get_deserialized("participant_to_process_html_round")
    
    @property
    def participant_to_embedding_round(self) -> DeserializedCollection:
        """Get the participants to the participant_to_embedding round."""
        return self._get_deserialized("participant_to_embedding_round")
    
    @property
    def participant_to_publish_round(self) -> DeserializedCollection:
        """Get the participants to the participant_to_publish round."""
        return self._get_deserialized("participant_to_publish_round")


class SamplingRound(UpdateDocumentsRound):
    """SamplingRound"""

    payload_class = SamplingPayload
    synchronized_data_class = SynchronizedData
    done_event = Event.DONE
    none_event = Event.NONE
    no_majority_event = Event.NO_MAJORITY
    selection_key: Any = (
        UpdateDocumentsRound.selection_key,
        get_name(SynchronizedData.sampled_doc_index),
    )

    # Event.ROUND_TIMEOUT  # this needs to be mentioned for static checkers


class WebScrapeRound(CollectSameUntilThresholdRound):
    """SearchEngineRound"""

    payload_class = WebScrapePayload
    synchronized_data_class = SynchronizedData
    done_event = Event.DONE
    no_majority_event = Event.NO_MAJORITY
    collection_key = get_name(SynchronizedData.participant_to_web_scrape_round)
    selection_key = get_name(SynchronizedData.web_scrape_data)


class ProcessHtmlRound(CollectSameUntilThresholdRound):
    """ProcessHtmlRound"""

    payload_class = ProcessHtmlPayload
    synchronized_data_class = SynchronizedData
    done_event = Event.DONE
    no_majority_event = Event.NO_MAJORITY
    collection_key = get_name(SynchronizedData.participant_to_process_html_round)
    selection_key = get_name(SynchronizedData.process_html_data)


class EmbeddingRound(CollectSameUntilThresholdRound):
    """ProcessHtmlRound"""

    payload_class = EmbeddingPayload
    synchronized_data_class = SynchronizedData
    done_event = Event.DONE
    no_majority_event = Event.NO_MAJORITY
    collection_key = get_name(SynchronizedData.participant_to_embedding_round)
    selection_key = get_name(SynchronizedData.embeddings_hash)


class PublishRound(CollectSameUntilThresholdRound):
    """ProcessHtmlRound"""

    payload_class = PublishPayload
    synchronized_data_class = SynchronizedData
    done_event = Event.DONE
    no_majority_event = Event.NO_MAJORITY
    collection_key = get_name(SynchronizedData.participant_to_publish_round)
    selection_key = get_name(SynchronizedData.embeddings_ipfs_link)


class FinishedScraperRound(DegenerateRound):
    """FinishedScraperRound"""

class FinishedWithoutScraping(DegenerateRound):
    """FinishedWithoutScraping"""


class ScraperAbciApp(AbciApp[Event]):
    """ScraperAbciApp"""

    initial_round_cls: AppState = SamplingRound
    initial_states: Set[AppState] = {
        SamplingRound,
    }
    transition_function: AbciAppTransitionFunction = {
        SamplingRound: {
            Event.NO_MAJORITY: SamplingRound,
            Event.ROUND_TIMEOUT: SamplingRound,
            Event.DONE: WebScrapeRound,
            Event.NONE: FinishedWithoutScraping,
        },
        WebScrapeRound: {
            Event.NO_MAJORITY: WebScrapeRound,
            Event.ROUND_TIMEOUT: WebScrapeRound,
            Event.DONE: ProcessHtmlRound,
        },
        ProcessHtmlRound: {
            Event.NO_MAJORITY: ProcessHtmlRound,
            Event.ROUND_TIMEOUT: ProcessHtmlRound,
            Event.DONE: EmbeddingRound,
        },
        EmbeddingRound: {
            Event.NO_MAJORITY: EmbeddingRound,
            Event.ROUND_TIMEOUT: EmbeddingRound,
            Event.DONE: PublishRound,
        },
        PublishRound: {
            Event.NO_MAJORITY: PublishRound,
            Event.ROUND_TIMEOUT: PublishRound,
            Event.DONE: FinishedScraperRound,
        },
        FinishedScraperRound: {},
        FinishedWithoutScraping: {},
    }
    final_states: Set[AppState] = {
        FinishedScraperRound,
        FinishedWithoutScraping,
    }
    event_to_timeout: EventToTimeout = {}
    cross_period_persisted_keys: FrozenSet[str] = frozenset()
    db_pre_conditions: Dict[AppState, Set[str]] = {
        SamplingRound: set(),
    }
    db_post_conditions: Dict[AppState, Set[str]] = {
        FinishedScraperRound: set(),
        FinishedWithoutScraping: set(),
    }
