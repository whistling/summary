import os
import asyncio
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.base import TaskResult
from autogen_agentchat.conditions import TextMentionTermination
from my_client import MyClient
from autogen_ext.models.openai import OpenAIChatCompletionClient


os.environ["OPENAI_BASE_URL"] = "http://localhost:3000"
os.environ["OPENAI_API_KEY"] = "sk-K7EupGRNt52NYeAP42Cc3d2eBc3f428cA4AeFb42D77eC204"


async def main() -> None:
    # model_client = OpenAIChatCompletionClient(
    #     model="gpt-4o",
    #     base_url="http://localhost:3000",
    #     api_key="sk-K7EupGRNt52NYeAP42Cc3d2eBc3f428cA4AeFb42D77eC204",
    #     model_info={
    #         "vision": False,
    #         "function_calling": False,
    #         "json_output": True,
    #         "family": "none",
    #     },)
    # agent = AssistantAgent("assistant", model_client=model_client)
    # result = await agent.run(task="Say 'Hello World!'")
    # print(result)

    # await model_client.close()

    # 定义Agent
    weather_agent = AssistantAgent(
        name="weather_agent",
        model_client=MyClient(
            create_args={
                "model": "gpt-4o",
                "api_key": "sk-K7EupGRNt52NYeAP42Cc3d2eBc3f428cA4AeFb42D77eC204",
                "base_url": "http://localhost:3000"
            },
        ),
        description="一个通过使用工具为用户提供天气信息的智能体。",
        system_message="你是一个乐于助人的AI智能助手。擅长使用工具解决任务。任务完成后，回复南哥AGI研习社",
        handoffs=None,
        # tools=[get_weather],
    )

    # # 定义终止条件  如果提到特定文本则终止对话
    # termination = TextMentionTermination("南哥AGI研习社")

    # # 定义Team Team的类型选择为RoundRobinGroupChat

    # # 1、run()方法运行team
    result = await weather_agent.run(task="上海的天气如何?")
    print(result)

    # # 2、run_stream()方法运行team
    # async for message in agent_team.run_stream(task="上海的天气如何?"):
    #     if isinstance(message, TaskResult):
    #         print("Stop Reason:", message.stop_reason)
    #     else:
    #         print(message)

    # # 3、run_stream()方法运行team并使用官方提供的Console工具以适当的格式输出
    # stream = agent_team.run_stream(task="上海的天气如何?")
    # await Console(stream)


if __name__ == "__main__":
    asyncio.run(main())


# Set up your API Endpoint(Azure Openai)
# config_list = [
#     {
#         'model': 'gpt-4o',
#         'api_key': 'sk-K7EupGRNt52NYeAP42Cc3d2eBc3f428cA4AeFb42D77eC204',
#         'base_url': "http://localhost:3000"
#     },
# ]
# os.environ["OAI_CONFIG_LIST"] = json.dumps(config_list)
# # Create a user agent
# user = autogen.UserProxyAgent(
#     "user proxy",
#     human_input_mode="ALWAYS",
#     code_execution_config={"use_docker": False}
# )
# # Create an assistant agent
# assistant = autogen.AssistantAgent(
#     "assistant",
#     system_message="You are a friendly AI assistant.",
#     llm_config={"config_list": config_list},
# )
# # Start the conversation
# user.initiate_chat(assistant, message="Write a program in Python and Rust that Sort the array with Bubble Sort: [1, 5, 2, 4, 2]")
