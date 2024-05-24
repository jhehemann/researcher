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

"""This module contains the behaviour for processing html text."""

from typing import Any, Generator, Optional, Type
from packages.jhehemann.skills.scraper_abci.behaviours.base import ScraperBaseBehaviour, WaitableConditionType
from packages.jhehemann.skills.scraper_abci.payloads import ProcessHtmlPayload
from packages.jhehemann.skills.scraper_abci.rounds import ProcessHtmlRound
from packages.valory.skills.abstract_round_abci.base import AbstractRound


class ProcessHtmlBehaviour(ScraperBaseBehaviour):  # pylint: disable=too-many-ancestors
    """Behaviour to process the html text."""

    matching_round: Type[AbstractRound] = ProcessHtmlRound     

    def __init__(self, **kwargs: Any) -> None:
        """Initialize behaviour."""
        super().__init__(**kwargs)
        self._web_scrape_response: Optional[str] = None
    


    def get_payload_content(self) -> Generator:
        """Process html text."""
        yield from self.wait_for_condition_with_sleep(self._get_response)
        html = self._web_scrape_response.html
    
        return html


    def async_act(self) -> Generator:
        """Do the act, supporting asynchronous execution."""

        with self.context.benchmark_tool.measure(self.behaviour_id).local():
            sender = self.context.agent_address
            html = self.synchronized_data.web_scrape_data
            print(f"PASSED PAYLOAD TO PROCESS: {html[:1000]}")
            exit()
            payload_content = yield from self.get_payload_content()
            payload = ProcessHtmlPayload(sender=sender, content=payload_content)

        with self.context.benchmark_tool.measure(self.behaviour_id).consensus():
            yield from self.send_a2a_transaction(payload)
            yield from self.wait_until_round_end()

        self.set_done()