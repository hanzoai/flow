import re
from unittest.mock import patch

import pytest
from hanzoflow.components.helpers.structured_output import StructuredOutputComponent
from hanzoflow.helpers.base_model import build_model_from_schema
from hanzoflow.inputs.inputs import TableInput
from pydantic import BaseModel

from tests.base import ComponentTestBaseWithoutClient
from tests.unit.mock_language_model import MockLanguageModel


class TestStructuredOutputComponent(ComponentTestBaseWithoutClient):
    @pytest.fixture
    def component_class(self):
        """Return the component class to test."""
        return StructuredOutputComponent

    @pytest.fixture
    def default_kwargs(self):
        """Return the default kwargs for the component."""
        return {
            "llm": MockLanguageModel(),
            "input_value": "Test input",
            "schema_name": "TestSchema",
            "output_schema": [{"name": "field", "type": "str", "description": "A test field"}],
            "multiple": False,
            "system_prompt": "Test system prompt",
        }

    @pytest.fixture
    def file_names_mapping(self):
        """Return the file names mapping for version-specific files."""

    def test_successful_structured_output_generation_with_patch_with_config(self):
        def mock_get_chat_result(runnable, system_message, input_value, config):  # noqa: ARG001
            class MockBaseModel(BaseModel):
                def model_dump(self, **__):
                    return {"objects": [{"field": "value"}]}

            return MockBaseModel()

        component = StructuredOutputComponent(
            llm=MockLanguageModel(),
            input_value="Test input",
            schema_name="TestSchema",
            output_schema=[{"name": "field", "type": "str", "description": "A test field"}],
            multiple=False,
            system_prompt="Test system prompt",
        )

        with patch("hanzoflow.components.helpers.structured_output.get_chat_result", mock_get_chat_result):
            result = component.build_structured_output_base()
            assert isinstance(result, list)
            assert result == [{"field": "value"}]

    def test_raises_value_error_for_unsupported_language_model(self):
        # Mocking an incompatible language model
        class MockLanguageModel:
            pass

        # Creating an instance of StructuredOutputComponent
        component = StructuredOutputComponent(
            llm=MockLanguageModel(),
            input_value="Test input",
            schema_name="TestSchema",
            output_schema=[{"name": "field", "type": "str", "description": "A test field"}],
            multiple=False,
        )

        with pytest.raises(TypeError, match=re.escape("Language model does not support structured output.")):
            component.build_structured_output()

    def test_correctly_builds_output_model(self):
        # Setup
        component = StructuredOutputComponent()
        schema = [
            {
                "name": "name",
                "display_name": "Name",
                "type": "str",
                "description": "Specify the name of the output field.",
            },
            {
                "name": "description",
                "display_name": "Description",
                "type": "str",
                "description": "Describe the purpose of the output field.",
            },
            {
                "name": "type",
                "display_name": "Type",
                "type": "str",
                "description": (
                    "Indicate the data type of the output field (e.g., str, int, float, bool, list, dict)."
                ),
            },
            {
                "name": "multiple",
                "display_name": "Multiple",
                "type": "boolean",
                "description": "Set to True if this output field should be a list of the specified type.",
            },
        ]
        component.output_schema = TableInput(name="output_schema", display_name="Output Schema", table_schema=schema)

        # Assertion
        output_model = build_model_from_schema(schema)
        assert isinstance(output_model, type)

    def test_handles_multiple_outputs(self):
        # Setup
        component = StructuredOutputComponent()
        schema = [
            {
                "name": "name",
                "display_name": "Name",
                "type": "str",
                "description": "Specify the name of the output field.",
            },
            {
                "name": "description",
                "display_name": "Description",
                "type": "str",
                "description": "Describe the purpose of the output field.",
            },
            {
                "name": "type",
                "display_name": "Type",
                "type": "str",
                "description": (
                    "Indicate the data type of the output field (e.g., str, int, float, bool, list, dict)."
                ),
            },
            {
                "name": "multiple",
                "display_name": "Multiple",
                "type": "boolean",
                "description": "Set to True if this output field should be a list of the specified type.",
            },
        ]
        component.output_schema = TableInput(name="output_schema", display_name="Output Schema", table_schema=schema)
        component.multiple = True

        # Assertion
        output_model = build_model_from_schema(schema)
        assert isinstance(output_model, type)

    def test_empty_output_schema(self):
        component = StructuredOutputComponent(
            llm=MockLanguageModel(),
            input_value="Test input",
            schema_name="EmptySchema",
            output_schema=[],
            multiple=False,
        )

        with pytest.raises(ValueError, match="Output schema cannot be empty"):
            component.build_structured_output()

    def test_invalid_output_schema_type(self):
        component = StructuredOutputComponent(
            llm=MockLanguageModel(),
            input_value="Test input",
            schema_name="InvalidSchema",
            output_schema=[{"name": "field", "type": "invalid_type", "description": "Invalid field"}],
            multiple=False,
        )

        with pytest.raises(ValueError, match="Invalid type: invalid_type"):
            component.build_structured_output()

    @patch("hanzoflow.components.helpers.structured_output.get_chat_result")
    def test_nested_output_schema(self, mock_get_chat_result):
        class ChildModel(BaseModel):
            child: str = "value"

        class ParentModel(BaseModel):
            objects: list[dict] = [{"parent": {"child": "value"}}]

            def model_dump(self, **__):
                return {"objects": self.objects}

        mock_llm = MockLanguageModel()
        mock_get_chat_result.return_value = ParentModel()

        component = StructuredOutputComponent(
            llm=mock_llm,
            input_value="Test input",
            schema_name="NestedSchema",
            output_schema=[
                {
                    "name": "parent",
                    "type": "dict",
                    "description": "Parent field",
                    "fields": [{"name": "child", "type": "str", "description": "Child field"}],
                }
            ],
            multiple=False,
            system_prompt="Test system prompt",
        )

        result = component.build_structured_output_base()
        assert isinstance(result, list)
        assert result == [{"parent": {"child": "value"}}]

    @patch("hanzoflow.components.helpers.structured_output.get_chat_result")
    def test_large_input_value(self, mock_get_chat_result):
        large_input = "Test input " * 1000

        class MockBaseModel(BaseModel):
            objects: list[dict] = [{"field": "value"}]

            def model_dump(self, **__):
                return {"objects": self.objects}

        mock_get_chat_result.return_value = MockBaseModel()

        component = StructuredOutputComponent(
            llm=MockLanguageModel(),
            input_value=large_input,
            schema_name="LargeInputSchema",
            output_schema=[{"name": "field", "type": "str", "description": "A test field"}],
            multiple=False,
            system_prompt="Test system prompt",
        )

        result = component.build_structured_output_base()
        assert isinstance(result, list)
        assert result == [{"field": "value"}]
        mock_get_chat_result.assert_called_once()
