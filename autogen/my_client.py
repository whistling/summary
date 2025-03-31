import os
import json
import aiohttp
from pydantic import Field
from autogen_core import (
    EVENT_LOGGER_NAME,
    TRACE_LOGGER_NAME,
    CancellationToken,
    Component,
    FunctionCall,
    Image,
)

from autogen_core.models import (
    AssistantMessage,
    ChatCompletionClient,
    ChatCompletionTokenLogprob,
    CreateResult,
    FunctionExecutionResultMessage,
    LLMMessage,
    ModelCapabilities,  # type: ignore
    ModelFamily,
    ModelInfo,
    RequestUsage,
    SystemMessage,
    TopLogprob,
    UserMessage,
    validate_model_info,
)

from autogen_core.tools import (Tool, ToolSchema)

from typing import (
    Any,
    AsyncGenerator,
    Dict,
    List,
    Mapping,
    Optional,
    Sequence,
    Set,
    Type,
    Union,
    cast,
)

class MyClientConfigModel():
    def __init__(self, model: str, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
    
    model: str = Field(description="The model to use for chat completion")
    api_key: Optional[str] = Field(default=None, description="The API key for authentication")
    base_url: Optional[str] = Field(default=None, description="The base URL for the API endpoint")

class MyClient(ChatCompletionClient):
    def __init__(
        self,
        *,
        create_args: Dict[str, Any],
    ):
        self._create_args = create_args
        self._total_tokens = 0
        self._actual_tokens = 0
        self.config = MyClientConfigModel(**create_args)
        self.api_key = self.config.api_key or os.getenv("OPENAI_API_KEY")
        self.base_url = self.config.base_url or os.getenv("OPENAI_BASE_URL")

    async def close(self) -> None:
        # 清理资源
        pass

    def actual_usage(self) -> RequestUsage:
        return RequestUsage(
            prompt_tokens=0, 
            completion_tokens=self._actual_tokens, 
            total_tokens=self._actual_tokens
        )

    def total_usage(self) -> RequestUsage:
        return RequestUsage(
            prompt_tokens=0,
            completion_tokens=self._total_tokens,
            total_tokens=self._total_tokens
        )

    def count_tokens(self, messages: Sequence[LLMMessage], *, tools: Sequence[Tool | ToolSchema] = []) -> int:
        # 简单实现：每个字符算一个token
        return sum(len(str(msg.content)) for msg in messages)

    def remaining_tokens(self, messages: Sequence[LLMMessage], *, tools: Sequence[Tool | ToolSchema] = []) -> int:
        # 假设最大token限制为4096
        max_tokens = 4096
        used_tokens = self.count_tokens(messages, tools=tools)
        return max_tokens - used_tokens

    @property
    def capabilities(self) -> ModelCapabilities:
        return {"vision": False, "function_calling": True, "json_output": True}

    @property
    def model_info(self) -> ModelInfo:
        return {
            "vision": False,
            "function_calling": True,
            "json_output": True,
            "family": ModelFamily.UNKNOWN
        }


    async def create(
        self,
        messages: Sequence[LLMMessage],
        *,
        tools: Sequence[Tool | ToolSchema] = [],
        json_output: Optional[bool] = None,
        extra_create_args: Mapping[str, Any] = {},
        cancellation_token: Optional[CancellationToken] = None,
    ) -> CreateResult:
        # Make sure all extra_create_args are valid
        extra_create_args_keys = set(extra_create_args.keys())
        create_kwargs = {"model", "temperature", "top_p", "n", "stream", "stop", "max_tokens",
                        "presence_penalty", "frequency_penalty", "logit_bias", "user", "response_format"}
        if not create_kwargs.issuperset(extra_create_args_keys):
            raise ValueError(f"Extra create args are invalid: {extra_create_args_keys - create_kwargs}")

        # Copy the create args and overwrite anything in extra_create_args
        create_args = {}
        create_args.update(extra_create_args)

        # TODO: allow custom handling.
        # For now we raise an error if images are present and vision is not supported
        model_info = {"vision": False, "json_output": True, "function_calling": True}
        if model_info["vision"] is False:
            for message in messages:
                if isinstance(message, UserMessage):
                    if isinstance(message.content, list) and any(isinstance(x, Image) for x in message.content):
                        raise ValueError("Model does not support vision and image was provided")

        if json_output is not None:
            if model_info["json_output"] is False and json_output is True:
                raise ValueError("Model does not support JSON output.")

            if json_output is True:
                create_args["response_format"] = {"type": "json_object"}
            else:
                create_args["response_format"] = {"type": "text"}

        if model_info["json_output"] is False and json_output is True:
            raise ValueError("Model does not support JSON output.")

        # Convert messages to OpenAI format
        oai_messages = []
        for msg in messages:
            if isinstance(msg, UserMessage):
                content = msg.content
                if isinstance(content, list):
                    # Handle image content
                    content_list = []
                    for item in content:
                        if isinstance(item, Image):
                            content_list.append({"type": "image_url", "image_url": {"url": item.url}})
                        else:
                            content_list.append({"type": "text", "text": str(item)})
                    oai_messages.append({"role": "user", "content": content_list})
                else:
                    oai_messages.append({"role": "user", "content": str(content)})
            elif isinstance(msg, AssistantMessage):
                msg_dict = {"role": "assistant", "content": msg.content}
                if msg.tool_calls:
                    msg_dict["tool_calls"] = msg.tool_calls
                oai_messages.append(msg_dict)
            elif isinstance(msg, FunctionExecutionResultMessage):
                oai_messages.append({"role": "tool", "content": str(msg.content), "tool_call_id": msg.tool_call_id})

        # Prepare request payload
        payload = {
            "messages": oai_messages,
            "stream": False,
            "model": self.config.model,
            "temperature": 1,
            "presence_penalty": 0,
            "frequency_penalty": 0,
            "top_p": 1,
            "max_tokens": 4000,
            **create_args
        }

        if tools:
            converted_tools = []
            for tool in tools:
                if isinstance(tool, Tool):
                    converted_tools.append({
                        "type": "function",
                        "function": {
                            "name": tool.name,
                            "description": tool.description,
                            "parameters": tool.parameters
                        }
                    })
                else:
                    converted_tools.append(tool)
            payload["tools"] = converted_tools

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/v1/chat/completions",
                headers=headers,
                json=payload
            ) as response:
                if response.status != 200:
                    raise Exception(f"API request failed with status {response.status}")
                
                response_data = await response.json()
                if response.status != 200:
                    raise Exception(f"API request failed with status {response.status}")
                
                choice = response_data["choices"][0]
                message = choice["message"]
                
                # 更新token计数
                self._actual_tokens = response_data["usage"]["completion_tokens"]
                self._total_tokens += self._actual_tokens
                
                return CreateResult(
                    content=message["content"],
                    role="assistant",
                    tool_calls=message.get("tool_calls", []),
                    token_usage={
                        "prompt_tokens": response_data["usage"]["prompt_tokens"],
                        "completion_tokens": response_data["usage"]["completion_tokens"],
                        "total_tokens": response_data["usage"]["total_tokens"]
                    },
                    model=response_data["model"],
                    finish_reason="stop",
                    usage=response_data["usage"],
                    cached=False
                )

    async def create_stream(
        self,
        messages: Sequence[LLMMessage],
        *,
        tools: Sequence[Tool | ToolSchema] = [],
        json_output: Optional[bool] = None,
        extra_create_args: Mapping[str, Any] = {},
        cancellation_token: Optional[CancellationToken] = None,
        max_consecutive_empty_chunk_tolerance: int = 0,
    ) -> AsyncGenerator[Union[str, CreateResult], None]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.config.model,
            "messages": [{
                "role": msg.role,
                "content": msg.content
            } for msg in messages],
            "stream": True
        }

        if tools:
            payload["tools"] = [tool.dict() for tool in tools]
        if tool_choice:
            payload["tool_choice"] = tool_choice

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/v1/chat/completions",
                headers=headers,
                json=payload
            ) as response:
                if response.status != 200:
                    raise Exception(f"API request failed with status {response.status}")
                
                async for line in response.content.iter_any():
                    if line:
                        try:
                            data = line.decode().strip()
                            if data.startswith("data: "):
                                data = data[6:]
                                if data == "[DONE]":
                                    break
                                
                                chunk = json.loads(data)
                                if chunk["code"] != "200":
                                    raise Exception(f"Stream error: {chunk.get('message', 'Unknown error')}")
                                
                                data = chunk["data"]
                                choice = data["choices"][0]
                                
                                if "delta" in choice:
                                    delta = choice["delta"]
                                    if "content" in delta:
                                        yield delta["content"]
                                    if "tool_calls" in delta:
                                        for tool_call in delta["tool_calls"]:
                                            yield ToolCall(**tool_call)
                                elif "message" in choice:
                                    message = choice["message"]
                                    if "content" in message:
                                        yield message["content"]
                                    if "tool_calls" in message:
                                        for tool_call in message["tool_calls"]:
                                            yield ToolCall(**tool_call)
                        except Exception as e:
                            print(f"Error processing stream: {e}")
                            continue

    @classmethod
    def create_from_config(cls, config: Dict[str, Any]) -> ChatCompletionClient:
        return cls(**config)