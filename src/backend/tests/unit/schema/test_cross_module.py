"""Unit tests for cross-module isinstance functionality.

These tests verify that isinstance checks work correctly when classes are
re-exported from different modules (e.g., lfx.schema.Message vs flow.schema.Message).
"""

from flow.schema import Data as FlowData
from flow.schema import Message as FlowMessage
from lfx.schema.data import Data as LfxData
from lfx.schema.message import Message as LfxMessage


class TestDuckTypingData:
    """Tests for duck-typing Data class across module boundaries."""

    def test_lfx_data_isinstance_flow_data(self):
        """Test that lfx.Data instance is recognized as flow.Data."""
        lfx_data = LfxData(data={"key": "value"})
        assert isinstance(lfx_data, FlowData)

    def test_flow_data_isinstance_lfx_data(self):
        """Test that flow.Data instance is recognized as lfx.Data."""
        flow_data = FlowData(data={"key": "value"})
        assert isinstance(flow_data, LfxData)

    def test_data_equality_across_modules(self):
        """Test that Data objects from different modules are equal."""
        lfx_data = LfxData(data={"key": "value"})
        flow_data = FlowData(data={"key": "value"})
        assert lfx_data == flow_data

    def test_data_interchangeable_in_functions(self):
        """Test that Data from different modules work interchangeably."""

        def process_data(data: FlowData) -> str:
            return data.get_text()

        lfx_data = LfxData(data={"text": "hello"})
        # Should not raise type error
        result = process_data(lfx_data)
        assert result == "hello"

    def test_data_model_dump_compatible(self):
        """Test that model_dump works across module boundaries."""
        lfx_data = LfxData(data={"key": "value"})
        flow_data = FlowData(**lfx_data.model_dump())
        assert flow_data.data == {"key": "value"}


class TestDuckTypingMessage:
    """Tests for duck-typing Message class across module boundaries."""

    def test_lfx_message_isinstance_flow_message(self):
        """Test that lfx.Message instance is recognized as flow.Message."""
        lfx_message = LfxMessage(text="hello")
        assert isinstance(lfx_message, FlowMessage)

    def test_flow_message_isinstance_lfx_message(self):
        """Test that flow.Message instance is recognized as lfx.Message."""
        flow_message = FlowMessage(text="hello")
        assert isinstance(flow_message, LfxMessage)

    def test_message_equality_across_modules(self):
        """Test that Message objects from different modules are equal."""
        lfx_message = LfxMessage(text="hello", sender="user")
        flow_message = FlowMessage(text="hello", sender="user")
        # Note: Direct equality might not work due to timestamps
        assert lfx_message.text == flow_message.text
        assert lfx_message.sender == flow_message.sender

    def test_message_interchangeable_in_functions(self):
        """Test that Message from different modules work interchangeably."""

        def process_message(msg: FlowMessage) -> str:
            return f"Processed: {msg.text}"

        lfx_message = LfxMessage(text="hello")
        # Should not raise type error
        result = process_message(lfx_message)
        assert result == "Processed: hello"

    def test_message_model_dump_compatible(self):
        """Test that model_dump works across module boundaries."""
        lfx_message = LfxMessage(text="hello", sender="user")
        dump = lfx_message.model_dump()
        flow_message = FlowMessage(**dump)
        assert flow_message.text == "hello"
        assert flow_message.sender == "user"

    def test_message_inherits_data_duck_typing(self):
        """Test that Message inherits duck-typing from Data."""
        lfx_message = LfxMessage(text="hello")
        # Should work as Data too
        assert isinstance(lfx_message, FlowData)
        assert isinstance(lfx_message, LfxData)


class TestDuckTypingWithInputs:
    """Tests for duck-typing with input validation."""

    def test_message_input_accepts_lfx_message(self):
        """Test that MessageInput accepts lfx.Message."""
        from lfx.inputs.inputs import MessageInput

        lfx_message = LfxMessage(text="hello")
        msg_input = MessageInput(name="test", value=lfx_message)
        assert isinstance(msg_input.value, (LfxMessage, FlowMessage))

    def test_message_input_converts_cross_module(self):
        """Test that MessageInput handles cross-module Messages."""
        from lfx.inputs.inputs import MessageInput

        flow_message = FlowMessage(text="hello")
        msg_input = MessageInput(name="test", value=flow_message)
        # Should recognize it as a Message
        assert msg_input.value.text == "hello"

    def test_data_input_accepts_lfx_data(self):
        """Test that DataInput accepts lfx.Data."""
        from lfx.inputs.inputs import DataInput

        lfx_data = LfxData(data={"key": "value"})
        data_input = DataInput(name="test", value=lfx_data)
        assert data_input.value == lfx_data


class TestDuckTypingEdgeCases:
    """Tests for edge cases in cross-module isinstance checks."""

    def test_different_class_name_not_cross_module(self):
        """Test that objects with different class names are not recognized as cross-module compatible."""
        from lfx.schema.cross_module import CrossModuleModel

        class CustomModel(CrossModuleModel):
            value: str

        custom = CustomModel(value="test")
        # Should not be considered a Data
        assert not isinstance(custom, LfxData)
        assert not isinstance(custom, FlowData)

    def test_non_pydantic_model_not_cross_module(self):
        """Test that non-Pydantic objects are not recognized as cross-module compatible."""

        class FakeData:
            def __init__(self):
                self.data = {}

        fake = FakeData()
        assert not isinstance(fake, LfxData)
        assert not isinstance(fake, FlowData)

    def test_missing_fields_not_cross_module(self):
        """Test that objects missing required fields are not recognized as cross-module compatible."""
        from lfx.schema.cross_module import CrossModuleModel

        class PartialData(CrossModuleModel):
            text_key: str

        partial = PartialData(text_key="text")
        # Should not be considered a full Data (missing data field)
        assert not isinstance(partial, LfxData)
        assert not isinstance(partial, FlowData)


class TestDuckTypingInputMixin:
    """Tests for cross-module isinstance checks in BaseInputMixin and subclasses."""

    def test_base_input_mixin_is_cross_module(self):
        """Test that BaseInputMixin uses CrossModuleModel."""
        from lfx.inputs.input_mixin import BaseInputMixin
        from lfx.schema.cross_module import CrossModuleModel

        # Check that BaseInputMixin inherits from CrossModuleModel
        assert issubclass(BaseInputMixin, CrossModuleModel)

    def test_input_subclasses_inherit_cross_module(self):
        """Test that all input types inherit cross-module support."""
        from lfx.inputs.inputs import (
            BoolInput,
            DataInput,
            FloatInput,
            IntInput,
            MessageInput,
            StrInput,
        )
        from lfx.schema.cross_module import CrossModuleModel

        for input_class in [StrInput, IntInput, FloatInput, BoolInput, DataInput, MessageInput]:
            assert issubclass(input_class, CrossModuleModel)

    def test_input_instances_work_across_modules(self):
        """Test that input instances work with duck-typing."""
        from lfx.inputs.inputs import MessageInput

        # Create with lfx Message
        lfx_msg = LfxMessage(text="hello")
        input1 = MessageInput(name="test1", value=lfx_msg)

        # Create with flow Message
        flow_msg = FlowMessage(text="world")
        input2 = MessageInput(name="test2", value=flow_msg)

        # Both should work
        assert input1.value.text == "hello"
        assert input2.value.text == "world"
