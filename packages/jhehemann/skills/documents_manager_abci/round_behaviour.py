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

"""This module contains the round behaviour for the 'documents_manager_abci' skill."""

from typing import Set, Type

from packages.jhehemann.skills.documents_manager_abci.behaviours.update_files import (
    UpdateQueriesBehaviour,
    UpdateFilesBehaviour,
)
from packages.jhehemann.skills.documents_manager_abci.behaviours.sample_query import SampleQueryBehaviour
from packages.jhehemann.skills.documents_manager_abci.behaviours.check_documents import CheckDocumentsBehaviour
from packages.jhehemann.skills.documents_manager_abci.behaviours.search_engine import SearchEngineBehaviour
from packages.valory.skills.abstract_round_abci.behaviours import (
    AbstractRoundBehaviour,
    BaseBehaviour,
)
from packages.jhehemann.skills.documents_manager_abci.rounds import DocumentsManagerAbciApp


class DocumentsManagerRoundBehaviour(AbstractRoundBehaviour):
    """This behaviour manages the consensus stages for the documents management."""

    initial_behaviour_cls = CheckDocumentsBehaviour
    abci_app_cls = DocumentsManagerAbciApp  # type: ignore
    behaviours: Set[Type[BaseBehaviour]] = [  # type: ignore
        UpdateQueriesBehaviour,
        UpdateFilesBehaviour,
        CheckDocumentsBehaviour,
        SampleQueryBehaviour,
        SearchEngineBehaviour,
    ]
