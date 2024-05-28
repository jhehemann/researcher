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
    CheckDocumentsPayload,
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
        """Get the number of unprocessed documents."""
        return self.db.get("num_unprocessed", None)
    
    @property
    def documents_hash(self) -> Optional[str]:
        """Get the document's hash."""
        return self.db.get("documents_hash", None)
    
    # @property
    # def participant_to_unprocessed_documents(self) -> DeserializedCollection:
    #     """Get the participants to the unprocessed documents."""
    #     return self._get_deserialized("participant_to_unprocessed_documents")
    
    @property
    def participant_to_documents_hash(self) -> DeserializedCollection:
        """Get the participants to the documents' hash."""
        return self._get_deserialized("participant_to_documents_hash")
  

class UpdateDocumentsRound(CollectSameUntilThresholdRound):
    """CheckDocumentsRound"""

    payload_class = UpdateDocumentsPayload
    synchronized_data_class = SynchronizedData
    done_event = Event.DONE
    no_majority_event = Event.NO_MAJORITY
    collection_key = get_name(SynchronizedData.participant_to_documents_hash)
    selection_key = get_name(SynchronizedData.documents_hash)
    

class CheckDocumentsRound(CollectSameUntilThresholdRound):
    """CheckDocumentsRound"""

    payload_class = CheckDocumentsPayload
    synchronized_data_class = SynchronizedData
    done_event = Event.DONE
    no_majority_event = Event.NO_MAJORITY
    collection_key = get_name(SynchronizedData.participant_to_documents_hash)
    selection_key = (
        # get_name(SynchronizedData.documents_hash),
        get_name(SynchronizedData.num_unprocessed),
    )
    
    def end_block(self) -> Optional[Tuple[SynchronizedData, Enum]]:
        """Process the end of the block."""
        res = super().end_block()
        if res is None:
            return None

        synced_data, event = cast(Tuple[SynchronizedData, Enum], res)

        if event == Event.DONE and not synced_data.num_unprocessed:
            return synced_data, Event.TO_UPDATE
        
        if event == Event.DONE and synced_data.num_unprocessed != 0:
            return synced_data, Event.NO_UPDATES

        return synced_data, event

    # Event.ROUND_TIMEOUT  # this needs to be mentioned for static checkers


class SearchEngineRound(CollectSameUntilThresholdRound):
    """SearchEngineRound"""

    payload_class = SearchEnginePayload
    synchronized_data_class = SynchronizedData
    done_event = Event.DONE
    no_majority_event = Event.NO_MAJORITY
    collection_key = get_name(SynchronizedData.participant_to_documents_hash)
    selection_key = get_name(SynchronizedData.documents_hash)


class FinishedDocumentsManagerRound(DegenerateRound):
    """FinishedDocumentsManagerRound"""


class DocumentsManagerAbciApp(AbciApp[Event]):
    """DocumentsManagerAbciApp"""

    initial_round_cls: AppState = CheckDocumentsRound
    initial_states: Set[AppState] = {
        CheckDocumentsRound,
    }
    transition_function: AbciAppTransitionFunction = {
        CheckDocumentsRound: {
            Event.NO_MAJORITY: CheckDocumentsRound,
            Event.ROUND_TIMEOUT: CheckDocumentsRound,
            Event.NO_UPDATES: FinishedDocumentsManagerRound,
            Event.TO_UPDATE: SearchEngineRound,
        },
        SearchEngineRound: {
            Event.NO_MAJORITY: SearchEngineRound,
            Event.ROUND_TIMEOUT: SearchEngineRound,
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
        CheckDocumentsRound: set(),
    }
    db_post_conditions: Dict[AppState, Set[str]] = {
        FinishedDocumentsManagerRound: {get_name(SynchronizedData.documents_hash)},
    }
