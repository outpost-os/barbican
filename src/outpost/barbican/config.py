# SPDX-FileCopyrightText: 2024 Ledger SAS
#
# SPDX-License-Identifier: Apache-2.0

import json

from referencing import Registry, Resource
from jsonschema import Draft202012Validator

import typing as T


_SCM_GIT_SCHEMA = json.loads(
    """
{
    "$id": "urn:barbican:scm:git",
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
        "uri": {
            "type": "string",
            "format": "uri"
        },
        "revision": { "type": "string" }
    },
    "required": [ "uri", "revision"],
    "additionalProperties": false
}
"""
)


_SCM_SCHEMA = json.loads(
    """
{
    "$id": "urn:barbican:scm",
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "oneOf": [
        {
            "properties": {
                "git": {
                    "$ref": "urn:barbican:scm:git"
                }
            },
            "required": ["git"],
            "additionalProperties": false
        }
    ]
}
"""
)


_KERNEL_SCHEMA = json.loads(
    """
{
    "$id": "urn:barbican:kernel",
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
        "scm": { "$ref": "urn:barbican:scm" },
        "config": { "type": "string" },
        "build": {
            "type": "object",
            "properties": {
                "options": { "$ref": "urn:barbican:build#/properties/options" }
            },
            "required": [ "options" ]
        }
    },
    "required": [ "scm", "config" ],
    "additionalProperties": false
}
"""
)


_RUNTIME_SCHEMA = json.loads(
    """
{
    "$id": "urn:barbican:runtime",
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
        "scm": { "$ref": "urn:barbican:scm" },
        "config": { "type": "string" },
        "build": {
            "type": "object",
            "properties": {
                "options": { "$ref": "urn:barbican:build#/properties/options" }
            },
            "required": [ "options" ]
        }
    },
    "required": [ "scm", "config" ],
    "additionalProperties": false
}
"""
)


_BUILD_SCHEMA = json.loads(
    """
{
    "$id": "urn:barbican:build",
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
        "backend": {
            "type": "string",
            "enum": ["meson", "cargo"]
        },
        "options": {
            "type": "object",
            "properties": {
                "static_pie": { "type": "boolean" }
            },
            "additionalProperties": {
                "oneOf": [
                    { "type": "string" },
                    { "type": "boolean" },
                    { "type": "integer" }
                ]
            }
        }
    },
    "required": [ "backend" ],
    "additionalProperties": false
}
"""
)


_APPLICATION_SCHEMA = json.loads(
    """
{
    "$id": "urn:barbican:application",
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
        "scm": { "$ref": "urn:barbican:scm" },
        "config": { "type": "string" },
        "build": { "$ref": "urn:barbican:build" },
        "depends": {
            "type": "array",
            "items": { "type": "string" }
        },
        "provides": {
            "type": "array",
            "items": { "type": "string" }
        }
    },
    "required": [ "scm", "build", "provides" ],
    "additionalProperties": false
}
"""
)


# TODO:
#  - Add License validator

_PROJECT_SCHEMA = json.loads(
    """
{
    "$id": "urn:barbican:project",
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "barbican project TOML configuration",
    "type": "object",
    "properties": {
        "name": {
            "type": "string",
            "description": "Project Name"
        },
        "version": {
            "type": "string"
        },
        "license": {
            "type": "string",
            "description": "license identifier (must be a valid SPDX License Identifier)"
        },
        "license_file": {
            "type": "array",
            "items": {
                "type": "string"
            },
            "description": "license file name"
        },
        "dts": {
            "type": "string",
            "description": "DTS file"
        },
        "crossfile": {
            "type": "string",
            "description": "meson cross file for arch mcu"
        },
        "kernel": {
            "$ref": "urn:barbican:kernel"
        },
        "runtime": {
            "$ref": "urn:barbican:runtime"
        },
        "application": {
            "patternProperties": {
                ".*": {
                    "type": "object",
                    "$ref": "urn:barbican:application"
                }
            },
            "additionalProperties": false
        }
    },
    "required": [ "name", "dts", "kernel", "version", "version" ],
    "dependentRequired": {
        "license": ["license_file"],
        "license_file": ["license"]
    }
}
"""
)


def validate(config: dict[str, T.Any]) -> None:
    registry: Registry = Resource.from_contents(_APPLICATION_SCHEMA) @ Registry()
    registry = Resource.from_contents(_RUNTIME_SCHEMA) @ registry
    registry = Resource.from_contents(_KERNEL_SCHEMA) @ registry
    registry = Resource.from_contents(_SCM_SCHEMA) @ registry
    registry = Resource.from_contents(_SCM_GIT_SCHEMA) @ registry
    registry = Resource.from_contents(_BUILD_SCHEMA) @ registry
    registry = Resource.from_contents(_PROJECT_SCHEMA) @ registry

    validator = Draft202012Validator(
        _PROJECT_SCHEMA,
        registry=registry,
    )
    validator.validate(config)
