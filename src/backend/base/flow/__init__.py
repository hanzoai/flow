"""Flow backwards compatibility layer.

This module provides backwards compatibility by forwarding imports from
flow.* to lfx.* to maintain compatibility with existing code that
references the old flow module structure.
"""

from flow.helpers.windows_postgres_helper import configure_windows_postgres_event_loop

configure_windows_postgres_event_loop(source="package_init")

import importlib  # noqa: E402
import importlib.util  # noqa: E402
import sys  # noqa: E402
from types import ModuleType  # noqa: E402
from typing import Any  # noqa: E402


class FlowCompatibilityModule(ModuleType):
    """A module that forwards attribute access to the corresponding lfx module."""

    def __init__(self, name: str, lfx_module_name: str):
        super().__init__(name)
        self._lfx_module_name = lfx_module_name
        self._lfx_module = None

    def _get_lfx_module(self):
        """Lazily import and cache the lfx module."""
        if self._lfx_module is None:
            try:
                self._lfx_module = importlib.import_module(self._lfx_module_name)
            except ImportError as e:
                msg = f"Cannot import {self._lfx_module_name} for backwards compatibility with {self.__name__}"
                raise ImportError(msg) from e
        return self._lfx_module

    def __getattr__(self, name: str) -> Any:
        """Forward attribute access to the lfx module with caching."""
        lfx_module = self._get_lfx_module()
        try:
            attr = getattr(lfx_module, name)
        except AttributeError as e:
            msg = f"module '{self.__name__}' has no attribute '{name}'"
            raise AttributeError(msg) from e
        else:
            # Cache the attribute in our __dict__ for faster subsequent access
            setattr(self, name, attr)
            return attr

    def __dir__(self):
        """Return directory of the lfx module."""
        try:
            lfx_module = self._get_lfx_module()
            return dir(lfx_module)
        except ImportError:
            return []


def _setup_compatibility_modules():
    """Set up comprehensive compatibility modules for flow.base imports."""
    # First, set up the base attribute on this module (flow)
    current_module = sys.modules[__name__]

    # Define all the modules we need to support
    module_mappings = {
        # Core base module
        "flow.base": "lfx.base",
        # Inputs module - critical for class identity
        "flow.inputs": "lfx.inputs",
        "flow.inputs.inputs": "lfx.inputs.inputs",
        # Schema modules - also critical for class identity
        "flow.schema": "lfx.schema",
        "flow.schema.data": "lfx.schema.data",
        "flow.schema.serialize": "lfx.schema.serialize",
        # Template modules
        "flow.template": "lfx.template",
        "flow.template.field": "lfx.template.field",
        "flow.template.field.base": "lfx.template.field.base",
        # Components modules
        "flow.components": "lfx.components",
        "flow.components.helpers": "lfx.components.helpers",
        "flow.components.helpers.calculator_core": "lfx.components.helpers.calculator_core",
        "flow.components.helpers.create_list": "lfx.components.helpers.create_list",
        "flow.components.helpers.current_date": "lfx.components.helpers.current_date",
        "flow.components.helpers.id_generator": "lfx.components.helpers.id_generator",
        "flow.components.helpers.memory": "lfx.components.helpers.memory",
        "flow.components.helpers.output_parser": "lfx.components.helpers.output_parser",
        "flow.components.helpers.store_message": "lfx.components.helpers.store_message",
        # Individual modules that exist in lfx
        "flow.base.agents": "lfx.base.agents",
        "flow.base.chains": "lfx.base.chains",
        "flow.base.data": "lfx.base.data",
        "flow.base.data.utils": "lfx.base.data.utils",
        "flow.base.document_transformers": "lfx.base.document_transformers",
        "flow.base.embeddings": "lfx.base.embeddings",
        "flow.base.flow_processing": "lfx.base.flow_processing",
        "flow.base.io": "lfx.base.io",
        "flow.base.io.chat": "lfx.base.io.chat",
        "flow.base.io.text": "lfx.base.io.text",
        "flow.base.langchain_utilities": "lfx.base.langchain_utilities",
        "flow.base.memory": "lfx.base.memory",
        "flow.base.models": "lfx.base.models",
        "flow.base.models.google_generative_ai_constants": "lfx.base.models.google_generative_ai_constants",
        "flow.base.models.openai_constants": "lfx.base.models.openai_constants",
        "flow.base.models.anthropic_constants": "lfx.base.models.anthropic_constants",
        "flow.base.models.aiml_constants": "lfx.base.models.aiml_constants",
        "flow.base.models.aws_constants": "lfx.base.models.aws_constants",
        "flow.base.models.groq_constants": "lfx.base.models.groq_constants",
        "flow.base.models.novita_constants": "lfx.base.models.novita_constants",
        "flow.base.models.ollama_constants": "lfx.base.models.ollama_constants",
        "flow.base.models.sambanova_constants": "lfx.base.models.sambanova_constants",
        "flow.base.models.cometapi_constants": "lfx.base.models.cometapi_constants",
        "flow.base.prompts": "lfx.base.prompts",
        "flow.base.prompts.api_utils": "lfx.base.prompts.api_utils",
        "flow.base.prompts.utils": "lfx.base.prompts.utils",
        "flow.base.textsplitters": "lfx.base.textsplitters",
        "flow.base.tools": "lfx.base.tools",
        "flow.base.vectorstores": "lfx.base.vectorstores",
    }

    # Create compatibility modules for each mapping
    for flow_name, lfx_name in module_mappings.items():
        if flow_name not in sys.modules:
            # Check if the lfx module exists
            try:
                spec = importlib.util.find_spec(lfx_name)
                if spec is not None:
                    # Create compatibility module
                    compat_module = FlowCompatibilityModule(flow_name, lfx_name)
                    sys.modules[flow_name] = compat_module

                    # Set up the module hierarchy
                    parts = flow_name.split(".")
                    if len(parts) > 1:
                        parent_name = ".".join(parts[:-1])
                        parent_module = sys.modules.get(parent_name)
                        if parent_module is not None:
                            setattr(parent_module, parts[-1], compat_module)

                    # Special handling for top-level modules
                    if flow_name == "flow.base":
                        current_module.base = compat_module
                    elif flow_name == "flow.inputs":
                        current_module.inputs = compat_module
                    elif flow_name == "flow.schema":
                        current_module.schema = compat_module
                    elif flow_name == "flow.template":
                        current_module.template = compat_module
                    elif flow_name == "flow.components":
                        current_module.components = compat_module
            except (ImportError, ValueError):
                # Skip modules that don't exist in lfx
                continue

    # Handle modules that exist only in flow (like knowledge_bases)
    # These need special handling because they're not in lfx yet
    flow_only_modules = {
        "flow.base.data.kb_utils": "flow.base.data.kb_utils",
        "flow.base.knowledge_bases": "flow.base.knowledge_bases",
        "flow.components.knowledge_bases": "flow.components.knowledge_bases",
    }

    for flow_name in flow_only_modules:
        if flow_name not in sys.modules:
            try:
                # Try to find the actual physical module file
                from pathlib import Path

                base_dir = Path(__file__).parent

                if flow_name == "flow.base.data.kb_utils":
                    kb_utils_file = base_dir / "base" / "data" / "kb_utils.py"
                    if kb_utils_file.exists():
                        spec = importlib.util.spec_from_file_location(flow_name, kb_utils_file)
                        if spec is not None and spec.loader is not None:
                            module = importlib.util.module_from_spec(spec)
                            sys.modules[flow_name] = module
                            spec.loader.exec_module(module)

                            # Also add to parent module
                            parent_module = sys.modules.get("flow.base.data")
                            if parent_module is not None:
                                parent_module.kb_utils = module

                elif flow_name == "flow.base.knowledge_bases":
                    kb_dir = base_dir / "base" / "knowledge_bases"
                    kb_init_file = kb_dir / "__init__.py"
                    if kb_init_file.exists():
                        spec = importlib.util.spec_from_file_location(flow_name, kb_init_file)
                        if spec is not None and spec.loader is not None:
                            module = importlib.util.module_from_spec(spec)
                            sys.modules[flow_name] = module
                            spec.loader.exec_module(module)

                            # Also add to parent module
                            parent_module = sys.modules.get("flow.base")
                            if parent_module is not None:
                                parent_module.knowledge_bases = module

                elif flow_name == "flow.components.knowledge_bases":
                    components_kb_dir = base_dir / "components" / "knowledge_bases"
                    components_kb_init_file = components_kb_dir / "__init__.py"
                    if components_kb_init_file.exists():
                        spec = importlib.util.spec_from_file_location(flow_name, components_kb_init_file)
                        if spec is not None and spec.loader is not None:
                            module = importlib.util.module_from_spec(spec)
                            sys.modules[flow_name] = module
                            spec.loader.exec_module(module)

                            # Also add to parent module
                            parent_module = sys.modules.get("flow.components")
                            if parent_module is not None:
                                parent_module.knowledge_bases = module
            except (ImportError, AttributeError):
                # If direct file loading fails, skip silently
                continue


# Set up all the compatibility modules
_setup_compatibility_modules()
