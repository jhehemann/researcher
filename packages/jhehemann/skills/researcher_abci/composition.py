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

"""This package contains round behaviours of ResearcherSkillAbciApp."""

import packages.jhehemann.skills.scraper_abci.rounds as ScraperAbciApp
import packages.jhehemann.skills.documents_manager_abci.rounds as DocumentsManagerAbciApp
import packages.valory.skills.transaction_settlement_abci.rounds as TransactionSubmissionAbciApp
import packages.valory.skills.registration_abci.rounds as RegistrationAbci
import packages.valory.skills.reset_pause_abci.rounds as ResetAndPauseAbci
from packages.valory.skills.abstract_round_abci.abci_app_chain import (
    AbciAppTransitionMapping,
    chain,
)
from packages.valory.skills.abstract_round_abci.base import BackgroundAppConfig
from packages.valory.skills.termination_abci.rounds import (
    BackgroundRound,
    Event,
    TerminationAbciApp,
)


abci_app_transition_mapping: AbciAppTransitionMapping = {
    RegistrationAbci.FinishedRegistrationRound: DocumentsManagerAbciApp.CheckDocumentsRound,
    DocumentsManagerAbciApp.FinishedDocumentsManagerRound: ScraperAbciApp.SamplingRound,
    ScraperAbciApp.FinishedScraperRound: TransactionSubmissionAbciApp.RandomnessTransactionSubmissionRound,
    ScraperAbciApp.FinishedWithoutScraping: ResetAndPauseAbci.ResetAndPauseRound,
    ScraperAbciApp.FinishedWithoutEmbeddingUpdate: ResetAndPauseAbci.ResetAndPauseRound,
    TransactionSubmissionAbciApp.FinishedTransactionSubmissionRound: ResetAndPauseAbci.ResetAndPauseRound,
    TransactionSubmissionAbciApp.FailedRound: ResetAndPauseAbci.ResetAndPauseRound,
    ResetAndPauseAbci.FinishedResetAndPauseRound: DocumentsManagerAbciApp.CheckDocumentsRound,
    ResetAndPauseAbci.FinishedResetAndPauseErrorRound: ResetAndPauseAbci.ResetAndPauseRound,
}

termination_config = BackgroundAppConfig(
    round_cls=BackgroundRound,
    start_event=Event.TERMINATE,
    abci_app=TerminationAbciApp,
)

ResearcherSkillAbciApp = chain(
    (
        RegistrationAbci.AgentRegistrationAbciApp,
        DocumentsManagerAbciApp.DocumentsManagerAbciApp,
        ScraperAbciApp.ScraperAbciApp,
        TransactionSubmissionAbciApp.TransactionSubmissionAbciApp,
        ResetAndPauseAbci.ResetPauseAbciApp,
    ),
    abci_app_transition_mapping,
).add_background_app(termination_config)
