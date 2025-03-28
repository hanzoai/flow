from typing import TYPE_CHECKING

from hanzoflow.utils import validate

if TYPE_CHECKING:
    from hanzoflow.custom import CustomComponent


def eval_custom_component_code(code: str) -> type["CustomComponent"]:
    """Evaluate custom component code."""
    class_name = validate.extract_class_name(code)
    return validate.create_class(code, class_name)
