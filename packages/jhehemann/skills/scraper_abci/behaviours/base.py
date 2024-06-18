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

"""This module contains the base behaviour for the 'scraper_abci' skill."""

from abc import ABC
from datetime import datetime, timedelta
from typing import Any, Callable, Generator, Optional, cast

import multibase
import multicodec

from packages.jhehemann.skills.documents_manager_abci.behaviours.base import DocumentsManagerBaseBehaviour
from packages.jhehemann.skills.documents_manager_abci.documents import Document
from packages.jhehemann.skills.scraper_abci.models import ScraperParams, SharedState
from packages.jhehemann.skills.scraper_abci.rounds import SynchronizedData
from packages.valory.skills.abstract_round_abci.behaviour_utils import TimeoutException

WaitableConditionType = Generator[None, None, bool]

class ScraperBaseBehaviour(DocumentsManagerBaseBehaviour, ABC):  # pylint: disable=too-many-ancestors
    """Base behaviour for the scraper_abci skill."""

    @property
    def synchronized_data(self) -> SynchronizedData:
        """Return the synchronized data."""
        return cast(SynchronizedData, super().synchronized_data)
    
    @property
    def params(self) -> ScraperParams:
        """Get the parameters."""
        return cast(ScraperParams, self.context.params)
    
    @property
    def local_state(self) -> SharedState:
        """Return the state."""
        return cast(SharedState, self.context.state)
    
    @staticmethod
    def to_multihash(hash_string: str) -> str:
        """To multihash string."""
        # Decode the Base32 CID to bytes
        cid_bytes = multibase.decode(hash_string)
        # Remove the multicodec prefix (0x01) from the bytes
        multihash_bytes = multicodec.remove_prefix(cid_bytes)
        # Convert the multihash bytes to a hexadecimal string
        hex_multihash = multihash_bytes.hex()
        return hex_multihash[6:]
        
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
