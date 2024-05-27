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

from dataclasses import dataclass
from typing import Optional

from packages.valory.skills.abstract_round_abci.base import BaseTxPayload
from packages.jhehemann.skills.documents_manager_abci.payloads import UpdateDocumentsPayload


@dataclass(frozen=True)
class SamplingPayload(UpdateDocumentsPayload):
    """Represent a transaction payload for the SamplingRound."""

    index: Optional[int]

@dataclass(frozen=True)
class SearchEnginePayload(BaseTxPayload):
    """Represent a transaction payload for the SearchEngineRound."""

    content: str

@dataclass(frozen=True)
class WebScrapePayload(BaseTxPayload):
    """Represent a transaction payload for the WebScrapeRound."""

    content: str

@dataclass(frozen=True)
class ProcessHtmlPayload(BaseTxPayload):
    """Represent a transaction payload for the ProcessHtmlRound."""

    content: str
