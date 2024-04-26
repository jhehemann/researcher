# # -*- coding: utf-8 -*-
# # ------------------------------------------------------------------------------
# #
# #   Copyright 2024 Valory AG
# #
# #   Licensed under the Apache License, Version 2.0 (the "License");
# #   you may not use this file except in compliance with the License.
# #   You may obtain a copy of the License at
# #
# #       http://www.apache.org/licenses/LICENSE-2.0
# #
# #   Unless required by applicable law or agreed to in writing, software
# #   distributed under the License is distributed on an "AS IS" BASIS,
# #   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# #   See the License for the specific language governing permissions and
# #   limitations under the License.
# #
# # ------------------------------------------------------------------------------
# """A connection responsible for uploading and downloading files from IPFS."""
# import asyncio
# import os
# import tempfile
# from asyncio import Task
# from concurrent.futures import Executor
# from pathlib import Path
# from shutil import rmtree
# from typing import Any, Callable, Dict, Optional, cast

# import requests
# from aea.configurations.base import PublicId
# from aea.connections.base import Connection, ConnectionStates
# from aea.mail.base import Envelope
# from aea.protocols.base import Address, Message
# from aea.protocols.dialogue.base import Dialogue as BaseDialogue
# # from aea_cli_ipfs.exceptions import DownloadError
# # from aea_cli_ipfs.ipfs_utils import IPFSTool
# # from ipfshttpclient.exceptions import ErrorResponse

# # from packages.valory.protocols.ipfs import IpfsMessage
# # from packages.valory.protocols.ipfs.dialogues import IpfsDialogue
# # from packages.valory.protocols.ipfs.dialogues import IpfsDialogues as BaseIpfsDialogues


# PUBLIC_ID = PublicId.from_str("jhehemann/search_engine:0.1.0")


# class HttpDialogues(BaseHttpDialogues):
#     """The dialogues class keeps track of all http dialogues."""

#     def __init__(self) -> None:
#         """Initialize dialogues."""

#         def role_from_first_message(  # pylint: disable=unused-argument
#             message: Message, receiver_address: Address
#         ) -> BaseDialogue.Role:
#             """Infer the role of the agent from an incoming/outgoing first message

#             :param message: an incoming/outgoing first message
#             :param receiver_address: the address of the receiving agent
#             :return: The role of the agent
#             """
#             # The client connection maintains the dialogue on behalf of the server
#             return HttpDialogue.Role.SERVER

#         BaseHttpDialogues.__init__(
#             self,
#             self_address=str(HTTPClientConnection.connection_id),
#             role_from_first_message=role_from_first_message,
#             dialogue_class=HttpDialogue,
#         )


# class HTTPClientAsyncChannel:  # pylint: disable=too-many-instance-attributes
#     """A wrapper for a HTTPClient."""

#     DEFAULT_TIMEOUT = 300  # default timeout in seconds
#     DEFAULT_EXCEPTION_CODE = (
#         600  # custom code to indicate there was exception during request
#     )

#     def __init__(
#         self,
#         agent_address: Address,
#         address: str,
#         port: int,
#         connection_id: PublicId,
#     ):
#         """
#         Initialize an http client channel.

#         :param agent_address: the address of the agent.
#         :param address: server hostname / IP address
#         :param port: server port number
#         :param connection_id: the id of the connection
#         """
#         self.agent_address = agent_address
#         self.address = address
#         self.port = port
#         self.connection_id = connection_id
#         self._dialogues = HttpDialogues()

#         self._in_queue = None  # type: Optional[asyncio.Queue]  # pragma: no cover
#         self._loop = (
#             None
#         )  # type: Optional[asyncio.AbstractEventLoop]  # pragma: no cover
#         self.is_stopped = True
#         self._tasks: Set[Task] = set()

#         self.logger = _default_logger
#         self.logger.debug("Initialised the HTTP client channel")

#     async def connect(self, loop: AbstractEventLoop) -> None:
#         """
#         Connect channel using loop.

#         :param loop: asyncio event loop to use
#         """
#         self._loop = loop
#         self._in_queue = asyncio.Queue()
#         self.is_stopped = False

#     def _get_message_and_dialogue(
#         self, envelope: Envelope
#     ) -> Tuple[HttpMessage, Optional[HttpDialogue]]:
#         """
#         Get a message copy and dialogue related to this message.

#         :param envelope: incoming envelope

#         :return: Tuple[Message, Optional[Dialogue]]
#         """
#         message = cast(HttpMessage, envelope.message)
#         dialogue = cast(Optional[HttpDialogue], self._dialogues.update(message))
#         return message, dialogue

#     async def _http_request_task(self, request_envelope: Envelope) -> None:
#         """
#         Perform http request and send back response.

#         :param request_envelope: request envelope
#         """
#         if not self._loop:  # pragma: nocover
#             raise ValueError("Channel is not connected")

#         request_http_message, dialogue = self._get_message_and_dialogue(
#             request_envelope
#         )

#         if not dialogue:
#             self.logger.warning(
#                 f"Could not create dialogue for message={request_http_message}"
#             )
#             return

#         try:
#             resp = await asyncio.wait_for(
#                 self._perform_http_request(request_http_message),
#                 timeout=self.DEFAULT_TIMEOUT,
#             )
#             envelope = self.to_envelope(
#                 request_http_message,
#                 status_code=resp.status,
#                 headers=resp.headers,
#                 status_text=resp.reason,
#                 body=resp._body  # pylint: disable=protected-access
#                 if resp._body is not None  # pylint: disable=protected-access
#                 else b"",
#                 dialogue=dialogue,
#             )
#         except Exception:  # pylint: disable=broad-except
#             envelope = self.to_envelope(
#                 request_http_message,
#                 status_code=self.DEFAULT_EXCEPTION_CODE,
#                 headers=CIMultiDictProxy(CIMultiDict()),
#                 status_text="HTTPConnection request error.",
#                 body=format_exc().encode("utf-8"),
#                 dialogue=dialogue,
#             )

#         if self._in_queue is not None:
#             await self._in_queue.put(envelope)

#     async def _perform_http_request(
#         self, request_http_message: HttpMessage
#     ) -> ClientResponse:
#         """
#         Perform http request and return response.

#         :param request_http_message: HttpMessage with http request constructed.

#         :return: aiohttp.ClientResponse
#         """
#         try:
#             if request_http_message.is_set("headers") and request_http_message.headers:
#                 headers: Optional[dict] = dict(
#                     email.message_from_string(request_http_message.headers).items()
#                 )
#             else:
#                 headers = None
#             async with aiohttp.ClientSession() as session:
#                 async with session.request(
#                     method=request_http_message.method,
#                     url=request_http_message.url,
#                     headers=headers,
#                     data=request_http_message.body,
#                     ssl=ssl_context,
#                 ) as resp:
#                     await resp.read()
#                 return resp
#         except Exception as e:  # pragma: nocover # pylint: disable=broad-except
#             self.logger.debug(
#                 f"Exception raised during http call: {request_http_message.method} {request_http_message.url}, {e}"
#             )
#             raise

#     def send(self, request_envelope: Envelope) -> None:
#         """
#         Send an envelope with http request data to request.

#         Convert an http envelope into an http request.
#         Send the http request
#         Wait for and receive its response
#         Translate the response into a response envelop.
#         Send the response envelope to the in-queue.

#         :param request_envelope: the envelope containing an http request
#         """
#         if self._loop is None or self.is_stopped:
#             raise ValueError("Can not send a message! Channel is not started!")

#         if request_envelope is None:
#             return

#         enforce(
#             isinstance(request_envelope.message, HttpMessage),
#             "Message not of type HttpMessage",
#         )

#         request_http_message = cast(HttpMessage, request_envelope.message)

#         if (
#             request_http_message.performative != HttpMessage.Performative.REQUEST
#         ):  # pragma: nocover
#             self.logger.warning(
#                 "The HTTPMessage performative must be a REQUEST. Envelop dropped."
#             )
#             return

#         task = self._loop.create_task(self._http_request_task(request_envelope))
#         task.add_done_callback(self._task_done_callback)
#         self._tasks.add(task)

#     def _task_done_callback(self, task: Task) -> None:
#         """
#         Handle http request task completed.

#         Removes tasks from _tasks.

#         :param task: Task completed.
#         """
#         self._tasks.remove(task)
#         self.logger.debug(f"Task completed: {task}")

#     async def get_message(self) -> Optional["Envelope"]:
#         """
#         Get http response from in-queue.

#         :return: None or envelope with http response.
#         """
#         if self._in_queue is None:
#             raise ValueError("Looks like channel is not connected!")

#         try:
#             return await self._in_queue.get()
#         except CancelledError:  # pragma: nocover
#             return None

#     @staticmethod
#     def to_envelope(
#         http_request_message: HttpMessage,
#         status_code: int,
#         headers: CIMultiDictProxy,
#         status_text: Optional[Any],
#         body: bytes,
#         dialogue: HttpDialogue,
#     ) -> Envelope:
#         """
#         Convert an HTTP response object (from the 'requests' library) into an Envelope containing an HttpMessage (from the 'http' Protocol).

#         :param http_request_message: the message of the http request envelop
#         :param status_code: the http status code, int
#         :param headers: dict of http response headers
#         :param status_text: the http status_text, str
#         :param body: bytes of http response content
#         :param dialogue: the http dialogue

#         :return: Envelope with http response data.
#         """
#         http_message = dialogue.reply(
#             performative=HttpMessage.Performative.RESPONSE,
#             target_message=http_request_message,
#             status_code=status_code,
#             headers=headers_to_string(headers),
#             status_text=status_text,
#             body=body,
#             version="",
#         )
#         envelope = Envelope(
#             to=http_message.to,
#             sender=http_message.sender,
#             message=http_message,
#         )
#         return envelope

#     async def _cancel_tasks(self) -> None:
#         """Cancel all requests tasks pending."""
#         for task in list(self._tasks):
#             if task.done():  # pragma: nocover
#                 continue
#             task.cancel()

#         for task in list(self._tasks):
#             try:
#                 await task
#             except KeyboardInterrupt:  # pragma: nocover
#                 raise
#             except BaseException:  # pragma: nocover # pylint: disable=broad-except
#                 pass  # nosec

#     async def disconnect(self) -> None:
#         """Disconnect."""
#         if not self.is_stopped:
#             self.logger.info(f"HTTP Client has shutdown on port: {self.port}.")
#             self.is_stopped = True

#             await self._cancel_tasks()



# class SearchEngineConnection(Connection):
#     """An async connection for sending and receiving files to IPFS."""

#     connection_id = PUBLIC_ID

#     def __init__(self, **kwargs: Any) -> None:
#         """
#         Initialize the connection.

#         :param kwargs: keyword arguments passed to component base.
#         """
#         super().__init__(**kwargs)  # pragma: no cover
#         # ipfs_domain = self.configuration.config.get("ipfs_domain")
#         # self.ipfs_tool: IPFSTool = IPFSTool(ipfs_domain)
#         self.task_to_request: Dict[asyncio.Future, Envelope] = {}
#         self.loop_executor: Optional[Executor] = None
#         # self.dialogues = IpfsDialogues(connection_id=PUBLIC_ID)
#         self._response_envelopes: Optional[asyncio.Queue] = None

#     @property
#     def response_envelopes(self) -> asyncio.Queue:
#         """Returns the response envelopes queue."""
#         if self._response_envelopes is None:
#             raise ValueError(
#                 "`IPFSConnection.response_envelopes` is not yet initialized. Is the connection setup?"
#             )
#         return self._response_envelopes

#     async def connect(self) -> None:
#         """Set up the connection."""
#         self.ipfs_tool.check_ipfs_node_running()
#         self._response_envelopes = asyncio.Queue()
#         self.state = ConnectionStates.connected

#     async def disconnect(self) -> None:
#         """Tear down the connection."""
#         if self.is_disconnected:  # pragma: nocover
#             return

#         self.state = ConnectionStates.disconnecting

#         for task in self.task_to_request.keys():
#             if not task.cancelled():  # pragma: nocover
#                 task.cancel()
#         self._response_envelopes = None

#         self.state = ConnectionStates.disconnected

#     async def send(self, envelope: Envelope) -> None:
#         """Send an envelope."""
#         task = self._handle_envelope(envelope)
#         task.add_done_callback(self._handle_done_task)
#         self.task_to_request[task] = envelope

#     async def receive(self, *args: Any, **kwargs: Any) -> Optional[Envelope]:
#         """Receive an envelope."""
#         return await self.response_envelopes.get()

#     def run_async(
#         self, func: Callable, *args: Any, timeout: Optional[float] = None
#     ) -> Task:
#         """Run a function asynchronously by using threads."""
#         ipfs_operation = self.loop.run_in_executor(
#             self.loop_executor,
#             func,
#             *args,
#         )
#         timely_operation = asyncio.wait_for(ipfs_operation, timeout=timeout)
#         task = self.loop.create_task(timely_operation)
#         return task

#     def _handle_envelope(self, envelope: Envelope) -> Task:
#         """Handle incoming envelopes by dispatching background tasks."""
#         message = cast(IpfsMessage, envelope.message)
#         performative = message.performative
#         handler = getattr(self, f"_handle_{performative.value}", None)
#         if handler is None:
#             err = f"Performative `{performative.value}` is not supported."
#             self.logger.error(err)
#             task = self.run_async(self._handle_error, err)
#             return task
#         dialogue = self.dialogues.update(message)
#         task = self.run_async(handler, message, dialogue)
#         return task

#     def _handle_store_files(
#         self, message: IpfsMessage, dialogue: BaseDialogue
#     ) -> IpfsMessage:
#         """
#         Handle a STORE_FILES performative.

#         Uploads the provided files to ipfs.

#         :param message: The ipfs request.
#         :returns: the hash of the uploaded files.
#         """
#         files = message.files
#         if len(files) == 0:
#             err = "No files were present."
#             self.logger.error(err)
#             return self._handle_error(err, dialogue)
#         if len(files) == 1:
#             # a single file needs to be stored,
#             # we don't need to create a dir
#             path, data = files.popitem()
#             self.__create_file(path, data)
#         else:
#             # multiple files are present, which means that it's a directory
#             # we begin by checking that they belong to the same directory
#             dirs = {os.path.dirname(path) for path in files.keys()}
#             if len(dirs) > 1:
#                 err = f"Received files from different dirs {dirs}. "
#                 self.logger.error(err)
#                 self.logger.info(
#                     "If you want to send multiple files as a single dir, "
#                     "make sure the their path matches to one directory only."
#                 )
#                 return self._handle_error(err, dialogue)

#             # "path" is the directory, it's the same for all the files
#             path = dirs.pop()
#             os.makedirs(path, exist_ok=True)
#             for file_path, data in files.items():
#                 self.__create_file(file_path, data)
#         try:
#             # note that path will be a dir if multiple files
#             # are being uploaded.
#             _, hash_, _ = self.ipfs_tool.add(path)
#             self.logger.debug(f"Successfully stored files with hash: {hash_}.")
#         except (
#             ValueError,
#             requests.exceptions.ChunkedEncodingError,
#         ) as e:  # pragma: no cover
#             err = str(e)
#             self.logger.error(err)
#             return self._handle_error(err, dialogue)
#         finally:
#             self.__remove_filepath(path)
#         response_message = cast(
#             IpfsMessage,
#             dialogue.reply(
#                 performative=IpfsMessage.Performative.IPFS_HASH,
#                 target_message=message,
#                 ipfs_hash=hash_,
#             ),
#         )
#         return response_message

#     def _handle_get_files(
#         self, message: IpfsMessage, dialogue: BaseDialogue
#     ) -> IpfsMessage:
#         """
#         Handle GET_FILES performative.

#         Downloads and returns the files resulting from the ipfs hash.

#         :param message: The ipfs request.
#         :returns: the downloaded files.
#         """
#         response_body: Dict[str, str] = {}
#         ipfs_hash = message.ipfs_hash
#         with tempfile.TemporaryDirectory() as tmp_dir:
#             try:
#                 self.ipfs_tool.download(ipfs_hash, tmp_dir)
#             except (
#                 DownloadError,
#                 PermissionError,
#                 ErrorResponse,
#             ) as e:
#                 err = str(e)
#                 self.logger.error(err)
#                 return self._handle_error(err, dialogue)

#             files = os.listdir(tmp_dir)
#             if len(files) > 1:
#                 self.logger.warning(
#                     f"Multiple files or dirs found in {tmp_dir}. "
#                     f"The first will be used. "
#                 )
#             downloaded_file = files.pop()
#             files_to_be_read = [downloaded_file]
#             base_dir = Path(tmp_dir)
#             if os.path.isdir(base_dir / downloaded_file):
#                 base_dir = base_dir / downloaded_file
#                 files_to_be_read = os.listdir(base_dir)

#             for file_path in files_to_be_read:
#                 with open(base_dir / file_path, encoding="utf-8", mode="r") as file:
#                     response_body[file_path] = file.read()

#             response_message = cast(
#                 IpfsMessage,
#                 dialogue.reply(
#                     performative=IpfsMessage.Performative.FILES,
#                     files=response_body,
#                     target_message=message,
#                 ),
#             )
#             return response_message

#     def _handle_error(  # pylint: disable=no-self-use
#         self, reason: str, dialogue: BaseDialogue
#     ) -> IpfsMessage:
#         """Handler for error messages."""
#         message = cast(
#             IpfsMessage,
#             dialogue.reply(
#                 performative=IpfsMessage.Performative.ERROR,
#                 reason=reason,
#             ),
#         )
#         return message

#     def _handle_done_task(self, task: asyncio.Future) -> None:
#         """
#         Process a done receiving task.

#         :param task: the done task.
#         """
#         request = self.task_to_request.pop(task)
#         response_message: Optional[Message] = task.result()

#         response_envelope = None
#         if response_message is not None:
#             response_envelope = Envelope(
#                 to=request.sender,
#                 sender=request.to,
#                 message=response_message,
#                 context=request.context,
#             )

#         # not handling `asyncio.QueueFull` exception, because the maxsize we defined for the Queue is infinite
#         self.response_envelopes.put_nowait(response_envelope)

#     @staticmethod
#     def __create_file(path: str, data: str) -> None:
#         """Creates a file in the specified path."""
#         with open(path, "w", encoding="utf-8") as f:
#             f.write(data)

#     def __remove_filepath(self, filepath: str) -> None:
#         """Remove a file or a folder. If filepath is not a file or a folder, an `IPFSInteractionError` is raised."""
#         if os.path.isfile(filepath):
#             os.remove(filepath)
#         elif os.path.isdir(filepath):
#             rmtree(filepath)
#         else:  # pragma: no cover
#             self.logger.error(f"`{filepath}` is not an existing filepath!")
