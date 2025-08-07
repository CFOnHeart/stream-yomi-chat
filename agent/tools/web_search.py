from typing import Optional, Any, Coroutine
from envs.dra.Lib.typing import LiteralString
from googleapiclient.discovery import build
from langchain_core.callbacks import (
    AsyncCallbackManagerForToolRun,
    CallbackManagerForToolRun,
)
from langchain_core.tools import BaseTool
from langchain_core.tools.base import ArgsSchema
from pydantic import BaseModel, Field
from langchain_tavily import TavilySearch
import httpx

class BigModelSearchInput(BaseModel):
    query: str = Field(description="The search query")

class BigModelSearchTool(BaseTool):
    name: str = "BigModelSearch"
    description: str = "Search the web using ZhiPu Big Model. Use this tool to find current information, news, or answers to questions that require up-to-date data."
    args_schema: Optional[ArgsSchema] = BigModelSearchInput
    return_direct: bool = False  # 确保不直接返回，让agent总结

    api_key: str

    def _run(
            self, query: str, run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> list:
        """Use the tool."""
        with httpx.Client() as client:
            response = client.post(
                'https://open.bigmodel.cn/api/paas/v4/tools',
                headers={'Authorization': self.api_key},
                json={
                    'tool': 'web-search-pro',
                    'messages': [
                        {'role': 'user', 'content': query}
                    ],
                    'stream': False
                }
            )

        res_data = []
        for choice in response.json()['choices']:
            for message in choice['message']['tool_calls']:
                search_results = message.get('search_result')
                if not search_results:
                    continue
                for result in search_results:
                    res_data.append(result['content'])

        return '\n\n\n'.join(res_data)

    async def _arun(
        self,
        query: str,
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
    ) -> list:
        """Use the tool asynchronously."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                'https://open.bigmodel.cn/api/paas/v4/tools',
                headers={'Authorization': self.api_key},
                json={
                    'tool': 'web-search-pro',
                    'messages': [
                        {'role': 'user', 'content': query}
                    ],
                    'stream': False
                }
            )

            res_data = []
            for choice in response.json()['choices']:
                for message in choice['message']['tool_calls']:
                    search_results = message.get('search_result')
                    if not search_results:
                        continue
                    for result in search_results:
                        res_data.append(result['content'])

            return '\n\n\n'.join(res_data)

class TavilySearchInput(BaseModel):
    query: str = Field(description="The search query")

class TavilySearchTool(BaseTool):
    name: str = "TavilySearch"
    description: str = "Search the web using Tavily. Use this tool to find current information, news, or answers to questions that require up-to-date data."
    args_schema: Optional[ArgsSchema] = TavilySearchInput
    return_direct: bool = False  # 确保不直接返回，让agent总结
    api_key: str

    def _run(
        self, query: str, run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> list:
        """Use the tool."""
        client = TavilySearch(max_results=2)
        return client.invoke(query=query, api_key=self.api_key)

    async def _arun(
        self,
        query: str,
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
    ) -> list:
        """Use the tool asynchronously."""
        return self._run(query, run_manager=run_manager.get_sync())

