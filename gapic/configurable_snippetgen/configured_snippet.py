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

import libcst
import inflection

from gapic.configurable_snippetgen import snippet_config_language_pb2 as snippet_config
from gapic.schema import api


def _make_empty_module() -> libcst.Module:
    return libcst.Module(body=[])


@dataclasses.dataclass(frozen=True)
class ConfiguredSnippet:
    api_schema: api.API
    config: snippet_config.SnippetConfig
    api_version: str
    is_sync: bool
    _module: libcst.Module = dataclasses.field(
        default_factory=_make_empty_module, init=False
    )

    @property
    def code(self) -> str:
        """The code of the configured snippet."""
        return self._module.code

    @property
    def region_tag(self) -> str:
        """The region tag of the snippet.

        For example:
            "speech_v1_generated_Adaptation_CreateCustomClass_Basic_async"
        """
        proto_package_name = self.config.rpc.proto_package.split(".")[-1]
        service_name = self.config.rpc.service_name
        rpc_name = self.config.rpc.rpc_name
        config_id = self.config.metadata.config_id
        sync_or_async = "sync" if self.is_sync else "async"
        return f"{proto_package_name}_{self.api_version}_generated_{service_name}_{rpc_name}_{config_id}_{sync_or_async}"

    @property
    def sample_function_name(self) -> str:
        """The sample function's name.

        For example:
            "sample_create_custom_class_basic"
        """
        snippet_method_name = self.config.signature.snippet_method_name
        config_id = self.config.metadata.config_id
        return f"sample_{snippet_method_name}_{config_id.lower()}"
