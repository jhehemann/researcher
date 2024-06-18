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

"""Behaviour in which the agents sample a query."""


from typing import Any, Generator, List, Type, Optional

from packages.valory.skills.abstract_round_abci.base import AbstractRound
from packages.jhehemann.skills.documents_manager_abci.payloads import SampleQueryPayload
from packages.jhehemann.skills.documents_manager_abci.rounds import SampleQueryRound
from packages.jhehemann.skills.documents_manager_abci.behaviours.base import DocumentsManagerBaseBehaviour
from packages.jhehemann.skills.documents_manager_abci.queries import Query, QueryStatus

class SampleQueryBehaviour(DocumentsManagerBaseBehaviour):  # pylint: disable=too-many-ancestors
    """SamplingBehaviour"""

    matching_round: Type[AbstractRound] = SampleQueryRound

    def _sampled_query_idx(self, queries: List[Query]) -> int:
        """
        Sample a query and return its id.

        The sampling logic is relatively simple at the moment.
        It simply selects the unprocessed query with the newest date.

        :param queries: the queries' values to compare for the sampling.
        :return: the id of the sampled query, out of all the available queries, not only the given ones.
        """
        return self.queries.index(min(queries))

    def _sample(self) -> Optional[int]:
        """Sample a query, mark it as processed, and return its index."""
        unprocessed_queries = list(self.unprocessed_queries)

        if len(unprocessed_queries) == 0:
            msg = "There were no unprocessed queries available to sample from!"
            self.context.logger.warning(msg)
            return None

        idx = self._sampled_query_idx(unprocessed_queries)

        # if self.queries[idx].publication_date == :
        #     msg = "There were no unprocessed query with non-zero liquidity!"
        #     self.context.logger.warning(msg)
        #     return None

        # update the query's status for the given id to `PROCESSED`
        self.queries[idx].status = QueryStatus.PROCESSED
        msg = f"Sampled query: {self.queries[idx]}"
        self.context.logger.info(msg)
        return idx

    def async_act(self) -> Generator:
        """Do the act, supporting asynchronous execution."""

        with self.context.benchmark_tool.measure(self.behaviour_id).local():
            sender = self.context.agent_address
            self.read_queries()
            idx = self._sample()
            self.store_queries()
            if idx is None:
                queries_hash = None
            else:
                queries_hash = self.hash_stored_queries()

            payload = SampleQueryPayload(sender=sender, queries_hash=queries_hash, sampled_query_idx=idx)

        with self.context.benchmark_tool.measure(self.behaviour_id).consensus():
            yield from self.send_a2a_transaction(payload)
            yield from self.wait_until_round_end()

        self.set_done()

