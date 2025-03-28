from hanzoflow.components.data import FileComponent
from hanzoflow.components.inputs import ChatInput
from hanzoflow.components.models import OpenAIModelComponent
from hanzoflow.components.outputs import ChatOutput
from hanzoflow.components.processing import ParseDataComponent
from hanzoflow.components.prompts import PromptComponent
from hanzoflow.graph import Graph


def document_qa_graph(template: str | None = None):
    if template is None:
        template = """Answer user's questions based on the document below:

---

{Document}

---

Question:
{Question}

Answer:
"""
    file_component = FileComponent()
    parse_data_component = ParseDataComponent()
    parse_data_component.set(data=file_component.load_files)

    chat_input = ChatInput()
    prompt_component = PromptComponent()
    prompt_component.set(
        template=template,
        context=parse_data_component.parse_data,
        question=chat_input.message_response,
    )

    openai_component = OpenAIModelComponent()
    openai_component.set(input_value=prompt_component.build_prompt)

    chat_output = ChatOutput()
    chat_output.set(input_value=openai_component.text_response)

    return Graph(start=chat_input, end=chat_output)
