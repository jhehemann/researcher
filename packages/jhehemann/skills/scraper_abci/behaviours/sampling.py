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

"""Behaviour in which the agents sample a document."""

import os.path
from abc import ABC
from json import JSONDecodeError
from typing import Any, Generator, Iterator, List, Set, Tuple, Type

from packages.valory.skills.abstract_round_abci.base import AbstractRound
from packages.jhehemann.skills.scraper_abci.payloads import SamplingPayload
from packages.jhehemann.skills.scraper_abci.rounds import SamplingRound
from packages.jhehemann.skills.scraper_abci.behaviours.base import ScraperBaseBehaviour
from packages.jhehemann.skills.documents_manager_abci.documents import Document, DocumentStatus

class SamplingBehaviour(ScraperBaseBehaviour):  # pylint: disable=too-many-ancestors
    """SamplingBehaviour"""

    matching_round: Type[AbstractRound] = SamplingRound

    def async_act(self) -> Generator:
        """Do the act, supporting asynchronous execution."""

        with self.context.benchmark_tool.measure(self.behaviour_id).local():
            sender = self.context.agent_address
            self.read_documents()

            payload_content = self.params.input_query
            self.context.logger.info(payload_content)
            payload = SamplingPayload(sender=sender, content=payload_content)

        with self.context.benchmark_tool.measure(self.behaviour_id).consensus():
            yield from self.send_a2a_transaction(payload)
            yield from self.wait_until_round_end()

        self.set_done()

