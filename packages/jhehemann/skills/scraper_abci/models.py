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
from packages.jhehemann.skills.documents_manager_abci.models import DocumentsManagerParams
from packages.valory.skills.abstract_round_abci.models import BaseParams
from packages.valory.skills.abstract_round_abci.models import ApiSpecs
from packages.valory.skills.abstract_round_abci.models import (
    BenchmarkTool as BaseBenchmarkTool,
)
from packages.valory.skills.abstract_round_abci.models import Requests as BaseRequests
from packages.valory.skills.abstract_round_abci.models import (
    SharedState as BaseSharedState,
)
from packages.valory.skills.abstract_round_abci.models import TypeCheckMixin
from collections import defaultdict
from typing import Any, Callable, Dict, List, Optional, cast

from aea.exceptions import enforce
from aea.skills.base import Model


class SharedState(BaseSharedState):
    """Keep the current shared state of the skill."""

    abci_app_cls = ScraperAbciApp


Requests = BaseRequests
BenchmarkTool = BaseBenchmarkTool


@dataclass
class MutableParams(TypeCheckMixin):
    """Collection for the mutable parameters."""

    latest_embeddings_hash: Optional[bytes] = None


class ScraperParams(DocumentsManagerParams):
    """A model to represent params for multiple abci apps."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the parameters object."""
        self._ipfs_address: str = self._ensure("ipfs_address", kwargs, str)
        self.hash_checkpoint_address: str = self._ensure("hash_checkpoint_address", kwargs, str)

        self.publish_mutable_params = MutableParams()
        super().__init__(*args, **kwargs)

    @property
    def ipfs_address(self) -> str:
        """Get the IPFS address."""
        if self._ipfs_address.endswith("/"):
            return self._ipfs_address
        return f"{self._ipfs_address}/"
    

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
    """A structure for the response of an embedding model interaction task."""

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




