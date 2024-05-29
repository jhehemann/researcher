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

"""This module contains the round behaviour for the 'scraper_abci' skill."""

from typing import Set, Type

from packages.jhehemann.skills.scraper_abci.behaviours.sampling import SamplingBehaviour
from packages.jhehemann.skills.scraper_abci.behaviours.process_html import ProcessHtmlBehaviour
from packages.jhehemann.skills.scraper_abci.behaviours.web_scrape import WebScrapeBehaviour
from packages.jhehemann.skills.scraper_abci.behaviours.embedding import EmbeddingBehaviour
from packages.valory.skills.abstract_round_abci.behaviours import (
    AbstractRoundBehaviour,
    BaseBehaviour,
)
from packages.jhehemann.skills.scraper_abci.rounds import ScraperAbciApp


class ScraperRoundBehaviour(AbstractRoundBehaviour):
    """This behaviour manages the consensus stages for the scraping."""

    initial_behaviour_cls = SamplingBehaviour
    abci_app_cls = ScraperAbciApp  # type: ignore
    behaviours: Set[Type[BaseBehaviour]] = [  # type: ignore
        SamplingBehaviour,
        WebScrapeBehaviour,
        ProcessHtmlBehaviour,
        EmbeddingBehaviour,
    ]
