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

from packages.jhehemann.skills.scraper_abci.rounds import ScraperAbciApp
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

    abci_app_cls = ScraperAbciApp


Requests = BaseRequests
BenchmarkTool = BaseBenchmarkTool
#Params = BaseParams

class ScraperParams(BaseParams):
    """A model to represent params for multiple abci apps."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the parameters object."""
       
        self.api_keys: Dict = self._nested_list_todict_workaround(
            kwargs, "api_keys_json"
        )
        self._ipfs_address: str = self._ensure("ipfs_address", kwargs, str)

        self.input_query = kwargs.get("input_query", None)
        enforce(self.input_query is not None, "input_query must be set!")
        self.polling_interval = kwargs.get("polling_interval", 30.0)
        self.task_deadline = kwargs.get("task_deadline", 240.0)
        self.num_agents = kwargs.get("num_agents", None)
        self.request_count: int = 0
        self.cleanup_freq = kwargs.get("cleanup_freq", 50)
        enforce(self.num_agents is not None, "num_agents must be set!")
        self.agent_index = kwargs.get("agent_index", None)
        enforce(self.agent_index is not None, "agent_index must be set!")
        self.from_block_range = kwargs.get("from_block_range", None)
        enforce(self.from_block_range is not None, "from_block_range must be set!")
        self.timeout_limit = kwargs.get("timeout_limit", None)
        enforce(self.timeout_limit is not None, "timeout_limit must be set!")
        self.max_block_window = kwargs.get("max_block_window", None)
        enforce(self.max_block_window is not None, "max_block_window must be set!")
        # maps the request id to the number of times it has timed out
        self.request_id_to_num_timeouts: Dict[int, int] = defaultdict(lambda: 0)
        #self.mech_to_config: Dict[str, MechConfig] = self._parse_mech_configs(kwargs)
        super().__init__(*args, **kwargs)

    @property
    def ipfs_address(self) -> str:
        """Get the IPFS address."""
        if self._ipfs_address.endswith("/"):
            return self._ipfs_address
        return f"{self._ipfs_address}/"

    def _nested_list_todict_workaround(
        self,
        kwargs: Dict,
        key: str,
    ) -> Dict:
        """Get a nested list from the kwargs and convert it to a dictionary."""
        values = cast(List, kwargs.get(key))
        if len(values) == 0:
            raise ValueError(f"No {key} specified!")
        return {value[0]: value[1] for value in values}


class WebScrapeResponseSpecs(ApiSpecs):
    """A model that wraps ApiSpecs for the web scraping response specifications."""


class EmbeddingResponseSpecs(ApiSpecs):
    """A model that wraps ApiSpecs for the embedding response specifications."""


@dataclass(init=False)
class WebScrapeInteractionResponse:
    """A structure for the response of a search engine interaction task."""

    html: str
    error: str

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the search engine's response ignoring extra keys."""
        self.html = kwargs.pop("html", "Unknown")
        self.error = kwargs.pop("error", "Unknown")

    @classmethod
    def incorrect_format(cls, res: Any) -> "WebScrapeInteractionResponse":
        """Return an incorrect format response."""
        response = cls()
        response.error = f"The response's format was unexpected: {res}"
        return response
    

@dataclass(init=False)
class EmbeddingInteractionResponse:
    """A structure for the response of a search engine interaction task."""

    object: str
    data: list
    model: str
    usage: dict
    error: str

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the search engine's response ignoring extra keys."""
        self.object = kwargs.pop("object", "Unknown")
        self.data = kwargs.pop("data", "Unknown")
        self.model = kwargs.pop("model", "Unknown")
        self.usage = kwargs.pop("usage", "Unknown")
        self.error = kwargs.pop("error", "Unknown")

    @classmethod
    def incorrect_format(cls, res: Any) -> "EmbeddingInteractionResponse":
        """Return an incorrect format response."""
        response = cls()
        response.error = f"The response's format was unexpected: {res}"
        return response




