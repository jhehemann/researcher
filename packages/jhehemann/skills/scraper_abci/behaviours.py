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

"""This package contains round behaviours of HelloAbciApp."""

from abc import ABC
from typing import Generator, List, Set, Type, cast

from packages.jhehemann.skills.scraper_abci.models import Params, SharedState
from packages.jhehemann.skills.scraper_abci.payloads import (
    HelloPayload,
    SearchEnginePayload,
)
from packages.jhehemann.skills.scraper_abci.rounds import (
    ScraperAbciApp,
    HelloRound,
    SearchEngineRound,
    SynchronizedData,
)
from packages.valory.skills.abstract_round_abci.base import AbstractRound
from packages.valory.skills.abstract_round_abci.behaviours import (
    AbstractRoundBehaviour,
    BaseBehaviour,
)


class HelloBaseBehaviour(BaseBehaviour, ABC):  # pylint: disable=too-many-ancestors
    """Base behaviour for the hello_abci skill."""

    @property
    def synchronized_data(self) -> SynchronizedData:
        """Return the synchronized data."""
        return cast(SynchronizedData, super().synchronized_data)

    @property
    def params(self) -> Params:
        """Return the params."""
        return cast(Params, super().params)

    @property
    def local_state(self) -> SharedState:
        """Return the state."""
        return cast(SharedState, self.context.state)


class HelloBehaviour(HelloBaseBehaviour):  # pylint: disable=too-many-ancestors
    """HelloBehaviour"""

    matching_round: Type[AbstractRound] = HelloRound

    def async_act(self) -> Generator:
        """Do the act, supporting asynchronous execution."""

        with self.context.benchmark_tool.measure(self.behaviour_id).local():
            sender = self.context.agent_address
            payload_content = "Hello world!"
            self.context.logger.info(payload_content)
            payload = HelloPayload(sender=sender, content=payload_content)

        with self.context.benchmark_tool.measure(self.behaviour_id).consensus():
            yield from self.send_a2a_transaction(payload)
            yield from self.wait_until_round_end()

        self.set_done()


class SearchEngineBehaviour(HelloBaseBehaviour):  # pylint: disable=too-many-ancestors
    """Behaviour to request URLs from search engine"""

    matching_round: Type[AbstractRound] = SearchEngineRound     

    @property
    def params(self) -> Params:
        """Get the parameters."""
        return cast(Params, self.context.params)


    def get_payload_content(self, query: str) -> Generator:
        """Search Google using a custom search engine."""
        api_keys = self.params.api_keys
        google_api_key = api_keys["google_api_key"]
        google_engine_id = api_keys["google_engine_id"]
        print(f"google_api_key: {google_api_key}")
        print(f"google_engine_id: {google_engine_id}")
        
        num = 1



        method = "GET"
        url = "https://www.googleapis.com/customsearch/v1"
        parameters = {
            "key": google_api_key,
            "cx": google_engine_id,
            "q": query,
            "num": num,
        }
        response = yield from self.get_http_response(method, url, parameters)
        search = response.json()
        print(search)

        
        return [response["link"] for result in search.get("items", [])]


    def async_act(self) -> Generator:
        """Do the act, supporting asynchronous execution."""

        with self.context.benchmark_tool.measure(self.behaviour_id).local():
            sender = self.context.agent_address
            search_query = self.synchronized_data.hello_data
            payload_content = yield from self.get_payload_content(search_query)
            self.context.logger.info(payload_content)
            payload = SearchEnginePayload(sender=sender, content=payload_content)

        with self.context.benchmark_tool.measure(self.behaviour_id).consensus():
            yield from self.send_a2a_transaction(payload)
            yield from self.wait_until_round_end()

        self.set_done()


class ScraperRoundBehaviour(AbstractRoundBehaviour):
    """ScraperRoundBehaviour"""

    initial_behaviour_cls = HelloBehaviour
    abci_app_cls = ScraperAbciApp  # type: ignore
    behaviours: Set[Type[BaseBehaviour]] = [  # type: ignore
        HelloBehaviour,
        SearchEngineBehaviour,
    ]
