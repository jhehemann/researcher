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
from typing import Dict, FrozenSet, Optional, Set, Tuple, cast

from packages.jhehemann.skills.documents_manager_abci.payloads import (
    UpdateDocumentsPayload,
    SearchEnginePayload,
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
    """DocumentsManagerAbciApp Events"""

    DONE = "done"
    TO_UPDATE = "to_update"
    NO_UPDATES = "no_updates"
    FETCH_ERROR = "fetch_error"
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
    def num_unprocessed(self) -> Optional[int]:
        """Get the number of unprocessed bets."""
        return self.db.get("num_unprocessed", None)
    
    @property
    def search_engine_data(self) -> Optional[str]:
        """Get the search_engine_data."""
        return self.db.get("search_engine_data", None)
    
    @property
    def participant_to_update_documents_round(self) -> DeserializedCollection:
        """Get the participants to the update_documents round."""
        return self._get_deserialized("participant_to_update_documents_round")
    
    @property
    def participant_to_search_engine_round(self) -> DeserializedCollection:
        """Get the participants to the search_engine round."""
        return self._get_deserialized("participant_to_search_engine_round")
  

class UpdateDocumentsRound(CollectSameUntilThresholdRound):
    """HelloRound"""

    payload_class = UpdateDocumentsPayload
    synchronized_data_class = SynchronizedData
    done_event = Event.TO_UPDATE
    none_event = Event.NO_UPDATES
    no_majority_event = Event.NO_MAJORITY
    collection_key = get_name(SynchronizedData.participant_to_update_documents_round)
    selection_key = get_name(SynchronizedData.update_documents_data)
    
    def end_block(self) -> Optional[Tuple[SynchronizedData, Enum]]:
        """Process the end of the block."""
        res = super().end_block()
        if res is None:
            return None

        synced_data, event = cast(Tuple[SynchronizedData, Enum], res)

        if synced_data.num_unprocessed is None:
            return synced_data, Event.TIE

        if event == Event.DONE and not synced_data.is_profitable:
            return synced_data, Event.UNPROFITABLE

        return synced_data, event

    # Event.ROUND_TIMEOUT  # this needs to be mentioned for static checkers


class SearchEngineRound(CollectSameUntilThresholdRound):
    """SearchEngineRound"""

    payload_class = SearchEnginePayload
    synchronized_data_class = SynchronizedData
    done_event = Event.DONE
    none_event = Event.FETCH_ERROR
    no_majority_event = Event.NO_MAJORITY
    collection_key = get_name(SynchronizedData.participant_to_search_engine_round)
    selection_key = get_name(SynchronizedData.search_engine_data)


class FinishedDocumentsManagerRound(DegenerateRound):
    """FinishedDocumentsManagerRound"""

class FailedDocumentsManagerRound(DegenerateRound):
    """FailedDocumentsManagerRound"""


class DocumentsManagerAbciApp(AbciApp[Event]):
    """DocumentsManagerAbciApp"""

    initial_round_cls: AppState = UpdateDocumentsRound
    initial_states: Set[AppState] = {
        UpdateDocumentsRound,
    }
    transition_function: AbciAppTransitionFunction = {
        UpdateDocumentsRound: {
            Event.NO_MAJORITY: UpdateDocumentsRound,
            Event.ROUND_TIMEOUT: UpdateDocumentsRound,
            Event.NO_UPDATES: FinishedDocumentsManagerRound,
            Event.TO_UPDATE: SearchEngineRound,
        },
        SearchEngineRound: {
            Event.NO_MAJORITY: SearchEngineRound,
            Event.ROUND_TIMEOUT: SearchEngineRound,
            Event.FETCH_ERROR: FailedDocumentsManagerRound,
            Event.DONE: FinishedDocumentsManagerRound,
        },
        FinishedDocumentsManagerRound: {},
    }
    final_states: Set[AppState] = {
        FinishedDocumentsManagerRound,
    }
    event_to_timeout: EventToTimeout = {}
    cross_period_persisted_keys: FrozenSet[str] = frozenset()
    db_pre_conditions: Dict[AppState, Set[str]] = {
        UpdateDocumentsRound: set(),
    }
    db_post_conditions: Dict[AppState, Set[str]] = {
        FinishedDocumentsManagerRound: set(),
    }
