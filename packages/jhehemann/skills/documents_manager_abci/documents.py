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


"""Structures for documents."""

import builtins
import dataclasses
import json
import sys
from datetime import datetime
from dateutil import parser
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Union


def parse_date(date_string: str) -> str:
    """Convert a date string to datetime object."""
    format_str = "%B %d, %Y, %I:%M %p %Z"
    try:
        # Parse the date string to datetime object
        parsed_date = parser.parse(date_string)

        # # Adjust for AM/PM format, removing leading 0 in hour for consistency
        # formatted_date = parsed_date.strftime(format_str).replace(" 0", " ").strip()
        return parsed_date
    except (ValueError, TypeError):
        return None


class DocumentStatus(Enum):
    """A document's status."""

    UNPROCESSED = auto()
    PROCESSED = auto()
    BLACKLISTED = auto()


@dataclasses.dataclass
class Document:
    """A document's structure."""

    url: str
    title: Optional[str] = None
    description: Optional[str] = None
    content: Optional[str] = None
    publisher: Optional[str] = None
    author: Optional[str] = None
    publication_date: Optional[datetime] = None
    modification_date: Optional[datetime] = None
    type: Optional[str] = None
    status: DocumentStatus = DocumentStatus.UNPROCESSED
    blacklist_expiration: float = -1

    def __post_init__(self) -> None:
        """Post initialization to adjust the values."""
        self._cast()
        self._convert_dates()

    def __lt__(self, other: "Document") -> bool:
        """Implements older than operator."""
        if self.publication_date and other.publication_date:
            return self.publication_date < other.publication_date
        # self.context.logger.warning(f"Cannot compare {self.publication_date} and {other.publication_date}")
        return None

    def _blacklist_forever(self) -> None:
        """Blacklist a document forever. Should only be used in cases when url is unsafe."""
        self.status = DocumentStatus.BLACKLISTED
        self.blacklist_expiration = sys.maxsize

    def _cast(self) -> None:
        """Cast the values of the instance."""
        if isinstance(self.status, int):
            self.status = DocumentStatus(self.status)

        types_to_cast = ("int", "float", "str")
        str_to_type = {getattr(builtins, type_): type_ for type_ in types_to_cast}
        for field, hinted_type in self.__annotations__.items():
            uncasted = getattr(self, field)
            if uncasted is None:
                continue

            for type_to_cast, type_name in str_to_type.items():
                if hinted_type == type_to_cast:
                    setattr(self, field, hinted_type(uncasted))
                if f"{str(List)}[{type_name}]" == str(hinted_type):
                    setattr(self, field, list(type_to_cast(val) for val in uncasted))

    def _convert_dates(self) -> None:
        """Format the publication and modification dates."""
        date_attributes = ("publication_date", "modification_date")
        for date_attribute in date_attributes:
            date = getattr(self, date_attribute)
            if date:
                setattr(self, date_attribute, parse_date(date))
                # if getattr(self, date_attribute) is None:
                #     self.context.logger.warning(f"Cannot convert {date} to datetime object.")


class DocumentsEncoder(json.JSONEncoder):
    """JSON encoder for documents."""

    def default(self, o: Any) -> Any:
        """The default encoder."""
        if isinstance(o, DocumentStatus):
            return o.value
        if dataclasses.is_dataclass(o):
            return dataclasses.asdict(o)
        return super().default(o)


class DocumentsDecoder(json.JSONDecoder):
    """JSON decoder for documents."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the Documents JSON decoder."""
        super().__init__(object_hook=self.hook, *args, **kwargs)

    @staticmethod
    def hook(data: Dict[str, Any]) -> Union[Document, Dict[str, Document]]:
        """Perform the custom decoding."""
        # if this is a `Document`
        status_attributes = Document.__annotations__.keys()
        if sorted(status_attributes) == sorted(data.keys()):
            return Document(**data)

        return data


def serialize_documents(documents: List[Document]) -> Optional[str]:
    """Get the documents serialized."""
    if len(documents) == 0:
        return None
    return json.dumps(documents, cls=DocumentsEncoder)
