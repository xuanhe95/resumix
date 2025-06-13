from langchain.tools import Tool
from utils.llm_client import LLMClient

# 初始化本地 LLM 客户端
llm_client = LLMClient()

# 包装为 LangChain 工具
llm_tool = Tool.from_function(
    name="local_llm_generate",
    func=llm_client,  # 支持 __call__，可直接传入
    description=(
        "调用本地语言模型进行文本生成。"
        " 输入应为字符串 prompt，可用于润色、总结、改写等任务。"
    ),
)

# 可选：工具列表（方便后续传入 agent）
tool_list = [llm_tool]
