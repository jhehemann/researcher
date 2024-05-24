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

"""This module contains the behaviour for extracting html from a web page."""



from typing import Any, Generator, Optional, Type
from packages.jhehemann.skills.scraper_abci.models import WebScrapeResponseSpecs
from packages.jhehemann.skills.scraper_abci.behaviours.base import ScraperBaseBehaviour, WaitableConditionType
from packages.jhehemann.skills.scraper_abci.models import WebScrapeInteractionResponse
from packages.jhehemann.skills.scraper_abci.payloads import WebScrapePayload
from packages.jhehemann.skills.scraper_abci.rounds import WebScrapeRound
from packages.valory.skills.abstract_round_abci.base import AbstractRound


class WebScrapeBehaviour(ScraperBaseBehaviour):  # pylint: disable=too-many-ancestors
    """Behaviour to get content from web pages"""

    matching_round: Type[AbstractRound] = WebScrapeRound     

    def __init__(self, **kwargs: Any) -> None:
        """Initialize behaviour."""
        super().__init__(**kwargs)
        self._web_scrape_response: Optional[WebScrapeInteractionResponse] = None
    
    @property
    def web_scrape_response_api(self) -> WebScrapeResponseSpecs:
        """Get the web page's response api specs."""
        return self.context.web_scrape_response
    
    def set_web_scrape_response_specs(self, url) -> None:
        """Set the web page's response specs."""        
        self.web_scrape_response_api.__dict__["_frozen"] = False
        self.web_scrape_response_api.url = url
        self.web_scrape_response_api.__dict__["_frozen"] = True

    def _handle_response(
        self,
        res: Optional[str],
    ) -> Optional[Any]:
        """Handle the response from the web page.

        :param res: the response to handle.
        :return: the response's result, using the given keys. `None` if response is `None` (has failed).
        """
        if res is None:
            msg = f"Could not get the web page's response from {self.web_scrape_response_api.api_id}"
            self.context.logger.error(msg)
            self.web_scrape_response_api.increment_retries()
            return None

        self.context.logger.info(f"Retrieved the web page's response. Number of characters: {len(res)}")
        self.web_scrape_response_api.reset_retries()
        return res
    

    def _get_response(self) -> WaitableConditionType:
        """Get the response data from web page."""
        url = self.synchronized_data.search_engine_data.split('|')[0]
        self.set_web_scrape_response_specs(url)
        specs = self.web_scrape_response_api.get_spec()
        res_raw = yield from self.get_http_response(**specs)
        
        # Decode response body from bytes to html string
        res = res_raw.body.decode()
        res = self._handle_response(res)

        if self.web_scrape_response_api.is_retries_exceeded():
            error = "Retries were exceeded while trying to get the web page's response."
            self._web_scrape_response = WebScrapeInteractionResponse(error=error)
            return True
        
        if res is None:
            return False
        
        try:
            self._web_scrape_response = WebScrapeInteractionResponse(html=res)
        except (ValueError, TypeError, KeyError):
            self._web_scrape_response = WebScrapeInteractionResponse.incorrect_format(res)

        return True

    def get_payload_content(self) -> Generator:
        """Extract html text from website"""
        yield from self.wait_for_condition_with_sleep(self._get_response)
        html = self._web_scrape_response.html
    
        return html


    def async_act(self) -> Generator:
        """Do the act, supporting asynchronous execution."""

        with self.context.benchmark_tool.measure(self.behaviour_id).local():
            sender = self.context.agent_address
            payload_content = yield from self.get_payload_content()
            payload = WebScrapePayload(sender=sender, content=payload_content)

        with self.context.benchmark_tool.measure(self.behaviour_id).consensus():
            yield from self.send_a2a_transaction(payload)
            yield from self.wait_until_round_end()

        self.set_done()