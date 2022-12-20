# Copyright 2022 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import dataclasses
from typing import Optional

import inflection
import libcst

from gapic.configurable_snippetgen import libcst_utils
from gapic.configurable_snippetgen import snippet_config_language_pb2
from gapic.schema import api


class _AppendToSampleFunctionBody(libcst.CSTTransformer):
    def __init__(self, statement: libcst.BaseStatement):
        self.statement = statement

    def visit_IndentedBlock(self, node: libcst.IndentedBlock) -> bool:
        # Do not visit any nested indented blocks.
        return False

    def leave_IndentedBlock(
        self, original_node: libcst.IndentedBlock, updated_node: libcst.IndentedBlock
    ) -> libcst.IndentedBlock:
        del original_node
        # FunctionDef.body is an IndentedBlock, and IndentedBlock.body
        # is the actual sequence of statements.
        new_body = list(updated_node.body) + [self.statement]
        return updated_node.with_changes(body=new_body)


@dataclasses.dataclass
class ConfiguredSnippet:
    api_schema: api.API
    config: snippet_config_language_pb2.SnippetConfig
    api_version: str
    is_sync: bool

    def __post_init__(self) -> None:
        self._module: libcst.Module = libcst_utils.empty_module()
        self._sample_function_def: libcst.FunctionDef = libcst_utils.base_function_def(
            function_name=self.sample_function_name, is_sync=self.is_sync
        )

    @property
    def code(self) -> str:
        """The code of the configured snippet."""
        return self._module.code

    @property
    def gapic_module_name(self) -> str:
        """The GAPIC module name.

        For example:
            "speech_v1"
        """
        module_name = self.config.rpc.proto_package.split(".")[-1]
        return f"{module_name}_{self.api_version}"

    @property
    def region_tag(self) -> str:
        """The region tag of the snippet.

        For example:
            "speech_v1_config_Adaptation_CreateCustomClass_Basic_async"
        """
        service_name = self.config.rpc.service_name
        rpc_name = self.config.rpc.rpc_name
        config_id = self.config.metadata.config_id
        sync_or_async = "sync" if self.is_sync else "async"
        return f"{self.gapic_module_name}_config_{service_name}_{rpc_name}_{config_id}_{sync_or_async}"

    @property
    def sample_function_name(self) -> str:
        """The sample function's name.

        For example:
            "sample_create_custom_class_Basic"
        """
        snippet_method_name = self.config.signature.snippet_method_name
        config_id = self.config.metadata.config_id
        return f"sample_{snippet_method_name}_{config_id}"

    @property
    def client_class_name(self) -> str:
        """The service client's class name.

        For example:
            "AdaptationClient"
            "AdaptationAsyncClient"
        """
        if self.is_sync:
            client_class_name = f"{self.config.rpc.service_name}Client"
        else:
            client_class_name = f"{self.config.rpc.service_name}AsyncClient"
        return client_class_name

    @property
    def filename(self) -> str:
        """The snippet's file name.

        For example:
            "speech_v1_generated_Adaptation_create_custom_class_Basic_async.py"
        """
        service_name = self.config.rpc.service_name
        snake_case_rpc_name = inflection.underscore(self.config.rpc.rpc_name)
        config_id = self.config.metadata.config_id
        sync_or_async = "sync" if self.is_sync else "async"
        return f"{self.gapic_module_name}_generated_{service_name}_{snake_case_rpc_name}_{config_id}_{sync_or_async}.py"

    @property
    def api_endpoint(self) -> Optional[str]:
        """The api_endpoint in client_options."""
        host = (
            self.config.snippet.service_client_initialization.custom_service_endpoint.host
        )
        region = (
            self.config.snippet.service_client_initialization.custom_service_endpoint.region
        )

        if not host:
            return None
        elif not region:
            return host
        else:
            return f"{region}-{host}"

    def _append_to_sample_function_def_body(
        self, statement: libcst.BaseStatement
    ) -> None:
        """Appends the statement node to the current sample function def."""
        transformer = _AppendToSampleFunctionBody(statement)

        # The result of applying a transformer could be of a different type
        # in general, but we will only update the sample function def here.
        self._sample_function_def = self._sample_function_def.visit(
            transformer
        )  # type: ignore

    def _add_sample_function_parameters(self) -> None:
        # TODO: https://github.com/googleapis/gapic-generator-python/issues/1537, add typing annotation in sample function parameters.
        params = []
        for config_parameter in self.config.signature.parameters:
            params.append(libcst_utils.convert_parameter(config_parameter))
        parameters = libcst.Parameters(params=params)
        self._sample_function_def = self._sample_function_def.with_changes(
            params=parameters
        )

    def _append_service_client_initialization(self) -> None:
        if self.api_endpoint is not None:
            client_options_arg = libcst.Arg(
                keyword=libcst.Name("client_options"),
                value=libcst_utils.convert_py_dict(
                    [("api_endpoint", self.api_endpoint)]
                ),
            )
            initialization_call = libcst.helpers.parse_template_statement(
                f"client = {self.gapic_module_name}.{self.client_class_name}({{arg}})",
                arg=client_options_arg,
            )
        else:
            initialization_call = libcst.parse_statement(
                f"client = {self.gapic_module_name}.{self.client_class_name}()"
            )

        self._append_to_sample_function_def_body(initialization_call)

    def _build_sample_function(self) -> None:
        # TODO: https://github.com/googleapis/gapic-generator-python/issues/1536, add return type.
        # TODO: https://github.com/googleapis/gapic-generator-python/issues/1538, add docstring.
        # TODO: https://github.com/googleapis/gapic-generator-python/issues/1539, add sample function body.

        self._add_sample_function_parameters()

        # Each call below appends one or more statements to the sample
        # function's body.
        self._append_service_client_initialization()

    def _add_sample_function(self) -> None:
        self._module = self._module.with_changes(
            body=[self._sample_function_def])

    def generate(self) -> None:
        """Generates the snippet.

        This is the main entrypoint of a ConfiguredSnippet instance, calling
        other methods to update self._module.
        """
        self._build_sample_function()
        self._add_sample_function()
        # TODO: https://github.com/googleapis/gapic-generator-python/issues/1535, add imports.
        # TODO: https://github.com/googleapis/gapic-generator-python/issues/1534, add region tag.
        # TODO: https://github.com/googleapis/gapic-generator-python/issues/1533, add header.
