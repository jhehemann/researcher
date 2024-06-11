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

"""This module contains the shared state for the abci skill of ScraperAbciApp."""

import json
from dataclasses import dataclass

from packages.jhehemann.skills.documents_manager_abci.rounds import DocumentsManagerAbciApp
from packages.valory.skills.abstract_round_abci.models import BaseParams
from packages.valory.skills.abstract_round_abci.models import ApiSpecs
from packages.valory.skills.abstract_round_abci.models import (
    BenchmarkTool as BaseBenchmarkTool,
)
from packages.valory.skills.abstract_round_abci.models import Requests as BaseRequests
from packages.valory.skills.abstract_round_abci.models import (
    SharedState as BaseSharedState,
)
from collections import defaultdict
from typing import Any, Callable, Dict, List, Optional, cast

from aea.exceptions import enforce
from aea.skills.base import Model

class SharedState(BaseSharedState):
    """Keep the current shared state of the skill."""

    abci_app_cls = DocumentsManagerAbciApp


Requests = BaseRequests
BenchmarkTool = BaseBenchmarkTool
#Params = BaseParams

class DocumentsManagerParams(BaseParams):
    """A model to represent params for multiple abci apps."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the parameters object."""
    
        self.api_keys: Dict = self._nested_list_todict_workaround(
            kwargs, "api_keys_json"
        )

        self.input_query: str = self._ensure("input_query", kwargs, str)
        super().__init__(*args, **kwargs)

    def _nested_list_todict_workaround(
        self,
        kwargs: Dict,
        key: str,
    ) -> Dict:
        """Get a nested list from the kwargs and convert it to a dictionary."""
        values = cast(List, self._ensure(key, kwargs, list))
        if len(values) == 0:
            raise ValueError(f"No {key} specified!")
        return {value[0]: value[1] for value in values}

class SearchEngineResponseSpecs(ApiSpecs):
    """A model that wraps ApiSpecs for the search engines's response specifications."""

@dataclass(init=False)
class SearchEngineInteractionResponse:
    """A structure for the response of a search engine interaction task."""

    kind: str
    url: dict
    queries: dict
    search_context: dict
    search_information: dict
    items: List[dict]
    error: str

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the search engine's response ignoring extra keys."""
        self.kind = kwargs.pop("kind", "Unknown")
        self.url = kwargs.pop("url", {})
        self.queries = kwargs.pop("queries", {})
        self.search_context = kwargs.pop("context", {})
        self.search_information = kwargs.pop("searchInformation", {})
        self.items = kwargs.pop("items", [])
        self.error = kwargs.pop("error", "Unknown")

    @classmethod
    def incorrect_format(cls, res: Any) -> "SearchEngineInteractionResponse":
        """Return an incorrect format response."""
        response = cls()
        response.error = f"The response's format was unexpected: {res}"
        return response
