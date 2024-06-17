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

from abc import ABC
from enum import Enum
from typing import Dict, FrozenSet, Optional, Set, Tuple, cast

from packages.jhehemann.skills.documents_manager_abci.payloads import (
    UpdateQueriesPayload,
    UpdateFilesPayload,
    UpdateDocumentsPayload,
    CheckDocumentsPayload,
    SampleQueryPayload,
    SearchEnginePayload,
)

from packages.valory.skills.abstract_round_abci.base import (
    AbciApp,
    AbciAppTransitionFunction,
    AbstractRound,
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
    NONE = "none"
    TO_UPDATE = "to_update"
    NO_UPDATES = "no_updates"
    UPDATE_FAILED = "update_failed"
    NO_MAJORITY = "no_majority"
    ROUND_TIMEOUT = "round_timeout"
    FETCH_ERROR = "fetch_error"


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
    
    @property
    def embeddings_hash(self) -> Optional[str]:
        """Get the embeddings' hash."""
        return self.db.get("embeddings_hash", None)
    
    @property
    def queries_hash(self) -> str:
        """Get the most voted queries' hash."""
        return str(self.db.get_strict("queries_hash"))
    
    @property
    def sampled_query_idx(self) -> int:
        """Get the sampled query index."""
        return int(self.db.get_strict("sampled_query_idx"))

    @property
    def participant_to_queries_hash(self) -> DeserializedCollection:
        """Get the participants to queries' hash."""
        return self._get_deserialized("participant_to_queries")
    
    @property
    def participant_to_documents_hash(self) -> DeserializedCollection:
        """Get the participants to the documents' hash."""
        return self._get_deserialized("participant_to_documents_hash")
    
  

class DocumentsManagerAbstractRound(AbstractRound[Event], ABC):
    """Abstract round for the MarketManager skill."""

    @property
    def synchronized_data(self) -> SynchronizedData:
        """Return the synchronized data."""
        return cast(SynchronizedData, super().synchronized_data)

    def _return_no_majority_event(self) -> Tuple[SynchronizedData, Event]:
        """
        Trigger the `NO_MAJORITY` event.

        :return: the new synchronized data and a `NO_MAJORITY` event
        """
        return self.synchronized_data, Event.NO_MAJORITY


class UpdateQueriesRound(CollectSameUntilThresholdRound, DocumentsManagerAbstractRound):
    """A round for the queries fetching & updating."""

    payload_class = UpdateQueriesPayload
    done_event: Enum = Event.DONE
    none_event: Enum = Event.FETCH_ERROR
    no_majority_event: Enum = Event.NO_MAJORITY
    selection_key = get_name(SynchronizedData.queries_hash)
    collection_key = get_name(SynchronizedData.participant_to_queries_hash)
    synchronized_data_class = SynchronizedData

    def end_block(self) -> Optional[Tuple[BaseSynchronizedData, Enum]]:
        """Process the end of the block."""
        res = super().end_block()
        if res is None:
            return None

        synced_data, event = cast(Tuple[SynchronizedData, Enum], res)
        if event != Event.FETCH_ERROR:
            return res

        synced_data.update(SynchronizedData, queries=synced_data.db.get("queries_hash", ""))
        return synced_data, event

class UpdateFilesRound(CollectSameUntilThresholdRound):
    """UpdateFilesRound"""

    payload_class = UpdateFilesPayload
    synchronized_data_class = SynchronizedData
    done_event = Event.DONE
    none_event = Event.UPDATE_FAILED
    no_majority_event = Event.NO_MAJORITY
    collection_key = get_name(SynchronizedData.participant_to_documents_hash)
    selection_key = (
        get_name(SynchronizedData.documents_hash),
        get_name(SynchronizedData.embeddings_hash),
    )

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


class SampleQueryRound(CollectSameUntilThresholdRound):
    """SampleQueryRound"""

    payload_class = SampleQueryPayload
    synchronized_data_class = SynchronizedData
    done_event = Event.DONE
    none_event = Event.NONE
    no_majority_event = Event.NO_MAJORITY
    collection_key = get_name(SynchronizedData.participant_to_queries_hash)
    selection_key = (
        get_name(SynchronizedData.queries_hash),
        get_name(SynchronizedData.sampled_query_idx)
    )


class SearchEngineRound(CollectSameUntilThresholdRound):
    """SearchEngineRound"""

    payload_class = SearchEnginePayload
    synchronized_data_class = SynchronizedData
    done_event = Event.DONE
    none_event = Event.UPDATE_FAILED
    no_majority_event = Event.NO_MAJORITY
    collection_key = get_name(SynchronizedData.participant_to_documents_hash)
    selection_key = get_name(SynchronizedData.documents_hash)


class FinishedDocumentsManagerRound(DegenerateRound):
    """FinishedDocumentsManagerRound"""


class FailedDocumentsManagerRound(DegenerateRound):
    """FailedDocumentsManagerRound"""


class DocumentsManagerAbciApp(AbciApp[Event]):
    """DocumentsManagerAbciApp"""

    initial_round_cls: AppState = UpdateQueriesRound
    initial_states: Set[AppState] = {
        UpdateQueriesRound,
        CheckDocumentsRound,
    }
    transition_function: AbciAppTransitionFunction = {
        UpdateQueriesRound: {
            Event.DONE: UpdateFilesRound,
            Event.FETCH_ERROR: FailedDocumentsManagerRound,
            Event.ROUND_TIMEOUT: UpdateQueriesRound,
            Event.NO_MAJORITY: UpdateQueriesRound,
        },
        UpdateFilesRound: {
            Event.NO_MAJORITY: UpdateFilesRound,
            Event.ROUND_TIMEOUT: UpdateFilesRound,
            Event.UPDATE_FAILED: FailedDocumentsManagerRound,
            Event.DONE: CheckDocumentsRound,
        },
        CheckDocumentsRound: {
            Event.NO_MAJORITY: CheckDocumentsRound,
            Event.ROUND_TIMEOUT: CheckDocumentsRound,
            Event.NO_UPDATES: FinishedDocumentsManagerRound,
            Event.TO_UPDATE: SampleQueryRound,
        },
        SampleQueryRound: {
            Event.NO_MAJORITY: SampleQueryRound,
            Event.ROUND_TIMEOUT: SampleQueryRound,
            Event.DONE: UpdateQueriesRound,
            Event.NONE: FailedDocumentsManagerRound,
        },
        SearchEngineRound: {
            Event.NO_MAJORITY: SearchEngineRound,
            Event.ROUND_TIMEOUT: SearchEngineRound,
            Event.UPDATE_FAILED: FailedDocumentsManagerRound,
            Event.DONE: CheckDocumentsRound,
        },
        FinishedDocumentsManagerRound: {},
        FailedDocumentsManagerRound: {},
    }
    final_states: Set[AppState] = {
        FinishedDocumentsManagerRound,
        FailedDocumentsManagerRound,
    }
    event_to_timeout: EventToTimeout = {}
    cross_period_persisted_keys: FrozenSet[str] = frozenset()
    db_pre_conditions: Dict[AppState, Set[str]] = {
        UpdateQueriesRound: set(),
        CheckDocumentsRound: set(),
    }
    db_post_conditions: Dict[AppState, Set[str]] = {
        FinishedDocumentsManagerRound: {get_name(SynchronizedData.documents_hash)},
        FailedDocumentsManagerRound: set(),
    }
