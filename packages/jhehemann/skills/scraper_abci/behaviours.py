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

import json
from abc import ABC
from datetime import datetime, timedelta
from typing import Any, Callable, Generator, Optional, Set, Type, cast

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
from packages.valory.skills.abstract_round_abci.behaviour_utils import TimeoutException
# from packages.valory.skills.decision_maker_abci.io_.loader import ComponentPackageLoader
from packages.jhehemann.skills.scraper_abci.models import (
    SearchEngineInteractionResponse,
    SearchEngineResponseSpecs,
)

WaitableConditionType = Generator[None, None, bool]


class HelloBaseBehaviour(BaseBehaviour, ABC):  # pylint: disable=too-many-ancestors
    """Base behaviour for the scraper_abci skill."""

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

    def __init__(self, **kwargs: Any) -> None:
        """Initialize behaviour."""
        super().__init__(**kwargs)
        self._search_engine_response: Optional[SearchEngineInteractionResponse] = None

    @property
    def params(self) -> Params:
        """Get the parameters."""
        return cast(Params, self.context.params)
    
    @property
    def search_engine_response_api(self) -> SearchEngineResponseSpecs:
        """Get the search engine response api specs."""
        return self.context.search_engine_response
    
    def wait_for_condition_with_sleep(
        self,
        condition_gen: Callable[[], WaitableConditionType],
        timeout: Optional[float] = None,
    ) -> Generator[None, None, None]:
        """Wait for a condition to happen and sleep in-between checks.

        This is a modified version of the base `wait_for_condition` method which:
            1. accepts a generator that creates the condition instead of a callable
            2. sleeps in-between checks

        :param condition_gen: a generator of the condition to wait for
        :param timeout: the maximum amount of time to wait
        :yield: None
        """

        deadline = (
            datetime.now() + timedelta(0, timeout)
            if timeout is not None
            else datetime.max
        )

        while True:
            condition_satisfied = yield from condition_gen()
            if condition_satisfied:
                break
            if timeout is not None and datetime.now() > deadline:
                raise TimeoutException()
            self.context.logger.info(f"Retrying in {self.params.sleep_time} seconds.")
            yield from self.sleep(self.params.sleep_time)
    
    def set_search_engine_response_specs(self) -> None:
        """Set the search engine's response specs."""
        api_keys = self.params.api_keys
        google_api_key = api_keys["google_api_key"]
        google_engine_id = api_keys["google_engine_id"]
        query = self.synchronized_data.hello_data
        num = 2

        parameters = {
            "key": google_api_key,
            "cx": google_engine_id,
            "q": query,
            "num": num,
        }
        # The url must be dynamically generated as it depends on the ipfs hash
        self.search_engine_response_api.__dict__["_frozen"] = False
        self.search_engine_response_api.parameters = parameters
        self.search_engine_response_api.__dict__["_frozen"] = True

    def _handle_response(
        self,
        res: Optional[str],
    ) -> Optional[Any]:
        """Handle the response from the search engine.

        :param res: the response to handle.
        :return: the response's result, using the given keys. `None` if response is `None` (has failed).
        """
        if res is None:
            msg = f"Could not get the search engine's response from {self.search_engine_response_api.api_id}"
            self.context.logger.error(msg)
            self.search_engine_response_api.increment_retries()
            return None

        self.context.logger.info(f"Retrieved the search engine's response: {res}.")
        self.search_engine_response_api.reset_retries()
        return res

    def _get_response(self) -> WaitableConditionType:
        """Get the response data from search engine."""
        self.set_search_engine_response_specs()
        specs = self.search_engine_response_api.get_spec()
        
        res_raw = yield from self.get_http_response(**specs)        
        res = self.search_engine_response_api.process_response(res_raw)
        res = self._handle_response(res)

        if self.search_engine_response_api.is_retries_exceeded():
            error = "Retries were exceeded while trying to get the mech's response."
            self._search_engine_response = SearchEngineInteractionResponse(error=error)
            return True

        if res is None:
            return False
        
        print(f"PRETTY SE RESPONSE:\n{json.dumps(res, indent=4)}")

        try:
            self._search_engine_response = SearchEngineInteractionResponse(**res)
        except (ValueError, TypeError, KeyError):
            self._search_engine_response = SearchEngineInteractionResponse.incorrect_format(res)

        return True

    def get_payload_content(self, query: str) -> Generator:
        """Search Google using a custom search engine."""
        yield from self.wait_for_condition_with_sleep(self._get_response)

        search_response_items = self._search_engine_response.items
        links_list = [
            item['link'] for item in search_response_items if 'link' in item
        ]
        
        # Use a pipe as a separator for joining as it is not a valid character in a URL
        links_string = '|'.join(links_list)
        self.context.logger.info(f"Response links: {links_string}")
                
        return links_string


    def async_act(self) -> Generator:
        """Do the act, supporting asynchronous execution."""

        with self.context.benchmark_tool.measure(self.behaviour_id).local():
            sender = self.context.agent_address
            search_query = self.synchronized_data.hello_data
            payload_content = yield from self.get_payload_content(search_query)
            self.context.logger.info(f"PAYLOAD CONTENT: {payload_content}")
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
