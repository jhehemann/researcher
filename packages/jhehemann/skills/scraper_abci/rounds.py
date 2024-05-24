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

"""This package contains the rounds of HelloAbciApp."""

from enum import Enum
from typing import Dict, FrozenSet, Optional, Set

from packages.jhehemann.skills.scraper_abci.payloads import (
    HelloPayload,
    SearchEnginePayload,
    WebScrapePayload,
    ProcessHtmlPayload,
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


class Event(Enum):
    """HelloAbciApp Events"""

    DONE = "done"
    NO_MAJORITY = "no_majority"
    ROUND_TIMEOUT = "round_timeout"


class SynchronizedData(BaseSynchronizedData):
    """
    Class to represent the synchronized data.

    This data is replicated by the tendermint application.
    """

    def _get_deserialized(self, key: str) -> DeserializedCollection:
        """Strictly get a collection and return it deserialized."""
        serialized = self.db.get_strict(key)
        return CollectionRound.deserialize_collection(serialized)

    @property
    def hello_data(self) -> Optional[str]:
        """Get the hello_data."""
        return self.db.get("hello_data", None)
    
    @property
    def search_engine_data(self) -> Optional[str]:
        """Get the search_engine_data."""
        return self.db.get("search_engine_data", None)
    
    @property
    def web_scrape_data(self) -> Optional[str]:
        """Get the web_scrape_data."""
        return self.db.get("web_scrape_data", None)

    @property
    def process_html_data(self) -> Optional[str]:
        """Get the web_scrape_data."""
        return self.db.get("process_html_data", None)

    @property
    def participant_to_hello_round(self) -> DeserializedCollection:
        """Get the participants to the hello round."""
        return self._get_deserialized("participant_to_hello_round")
    
    @property
    def participant_to_search_engine_round(self) -> DeserializedCollection:
        """Get the participants to the search_engine round."""
        return self._get_deserialized("participant_to_search_engine_round")
    
    @property
    def participant_to_web_scrape_round(self) -> DeserializedCollection:
        """Get the participants to the web_scrape round."""
        return self._get_deserialized("participant_to_web_scrape_round")
    
    @property
    def participant_to_process_html_round(self) -> DeserializedCollection:
        """Get the participants to the participant_to_process_html round."""
        return self._get_deserialized("participant_to_process_html_round")


class HelloRound(CollectSameUntilThresholdRound):
    """HelloRound"""

    payload_class = HelloPayload
    synchronized_data_class = SynchronizedData
    done_event = Event.DONE
    no_majority_event = Event.NO_MAJORITY
    collection_key = get_name(SynchronizedData.participant_to_hello_round)
    selection_key = get_name(SynchronizedData.hello_data)

    # Event.ROUND_TIMEOUT  # this needs to be mentioned for static checkers


class SearchEngineRound(CollectSameUntilThresholdRound):
    """SearchEngineRound"""

    payload_class = SearchEnginePayload
    synchronized_data_class = SynchronizedData
    done_event = Event.DONE
    no_majority_event = Event.NO_MAJORITY
    collection_key = get_name(SynchronizedData.participant_to_search_engine_round)
    selection_key = get_name(SynchronizedData.search_engine_data)


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


class FinishedHelloRound(DegenerateRound):
    """FinishedHelloRound"""


class ScraperAbciApp(AbciApp[Event]):
    """ScraperAbciApp"""

    initial_round_cls: AppState = HelloRound
    initial_states: Set[AppState] = {
        HelloRound,
    }
    transition_function: AbciAppTransitionFunction = {
        HelloRound: {
            Event.NO_MAJORITY: HelloRound,
            Event.ROUND_TIMEOUT: HelloRound,
            Event.DONE: SearchEngineRound,
        },
        SearchEngineRound: {
            Event.NO_MAJORITY: SearchEngineRound,
            Event.ROUND_TIMEOUT: SearchEngineRound,
            Event.DONE: WebScrapeRound,
        },
        WebScrapeRound: {
            Event.NO_MAJORITY: WebScrapeRound,
            Event.ROUND_TIMEOUT: WebScrapeRound,
            Event.DONE: ProcessHtmlRound,
        },
        ProcessHtmlRound: {
            Event.NO_MAJORITY: ProcessHtmlRound,
            Event.ROUND_TIMEOUT: ProcessHtmlRound,
            Event.DONE: FinishedHelloRound,
        },
        FinishedHelloRound: {},
    }
    final_states: Set[AppState] = {
        FinishedHelloRound,
    }
    event_to_timeout: EventToTimeout = {}
    cross_period_persisted_keys: FrozenSet[str] = frozenset()
    db_pre_conditions: Dict[AppState, Set[str]] = {
        HelloRound: set(),
    }
    db_post_conditions: Dict[AppState, Set[str]] = {
        FinishedHelloRound: set(),
    }
