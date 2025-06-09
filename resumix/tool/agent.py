from langchain.agents import initialize_agent, AgentType
from tool import tool_list
from utils.llm_client import LLMWrapper, LLMClient

client = LLMClient(base_url="http://localhost:11434/api/generate", model_name="llama3.2:3b")

agent = initialize_agent(
    tools=tool_list,
    llm=LLMWrapper(client=client),
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True
)

response = agent.run("请使用 local_llm_generate 改写以下项目经历...")
print(response)
