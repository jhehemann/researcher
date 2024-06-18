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

import re
from typing import Any, Generator, Optional, Type
from readability import Document
from markdownify import markdownify as md


from packages.jhehemann.skills.scraper_abci.behaviours.base import ScraperBaseBehaviour
from packages.jhehemann.skills.scraper_abci.payloads import ProcessHtmlPayload
from packages.jhehemann.skills.scraper_abci.rounds import ProcessHtmlRound
from packages.valory.skills.abstract_round_abci.base import AbstractRound

MAX_TOKENS = 400
OVERLAP = 50


class ProcessHtmlBehaviour(ScraperBaseBehaviour):  # pylint: disable=too-many-ancestors
    """Behaviour to process the html text."""

    matching_round: Type[AbstractRound] = ProcessHtmlRound     

    def __init__(self, **kwargs: Any) -> None:
        """Initialize behaviour."""
        super().__init__(**kwargs)
        self._process_html_response: Optional[str] = None
    
    def recursive_character_text_splitter(self, text) -> list[str]:
        if len(text) <= MAX_TOKENS:
            return [text]
        else:
            return [text[i:i+MAX_TOKENS] for i in range(0, len(text), MAX_TOKENS - OVERLAP)]

    def _process_html(self) -> Optional[bool]:
        """Process the html text."""
        sampled_doc_index = self.synchronized_data.sampled_doc_index
        sampled_doc = self.documents[sampled_doc_index]
        html = self.synchronized_data.web_scrape_data

        # create readability document and extract main content
        doc_html2str = Document(html)
        doc_sum = doc_html2str.summary()
        
        # remove irrelevant tags and convert to markdown
        text = md(doc_sum, strip=['a', 'b', 'strong', 'em', 'img', 'i', 'mark', 'small', 'u'], heading_style="ATX")
        text = "  ".join([x.strip() for x in text.split("\n")])
        text = re.sub(r'\s+', ' ', text)

        if text is None:
            self.context.logger.error("Text could not be extracted from html.")
            return None
        sampled_doc.content = text

        # split text into chunks and join with separator for 
        text_chunks = self.recursive_character_text_splitter(text)
        if not any(entry.strip() for entry in text_chunks):
            sampled_doc.text_chunks = []
            self.context.logger.error("Extracted text is empty.")
            return False
        len_text_chunks = len(text_chunks)
        self.context.logger.info(f"Generated {len_text_chunks} text chunks.")
        sampled_doc.text_chunks = text_chunks
        self.context.logger.info(f"Text chunks: {sampled_doc.text_chunks}")
        return True

    def async_act(self) -> Generator:
        """Do the act, supporting asynchronous execution."""

        with self.context.benchmark_tool.measure(self.behaviour_id).local():
            sender = self.context.agent_address
            self.read_documents()
            text_chunks = self._process_html()
            self.store_documents()
            documents_hash = self.hash_stored_documents()

            payload = ProcessHtmlPayload(sender=sender, documents_hash=documents_hash, text_chunks=text_chunks)

        with self.context.benchmark_tool.measure(self.behaviour_id).consensus():
            yield from self.send_a2a_transaction(payload)
            yield from self.wait_until_round_end()

        self.set_done()