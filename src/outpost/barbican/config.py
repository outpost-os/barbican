# SPDX-FileCopyrightText: 2024 Ledger SAS
#
# SPDX-License-Identifier: Apache-2.0

import json

from referencing import Registry, Resource
from jsonschema import Draft202012Validator

import typing as T


_APPLICATION_SCHEMA = json.loads(
    """
{
    "$id": "urn:barbican:application",
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object"
}
"""
)


_LIBSHIELD_SCHEMA = json.loads(
    """
{
    "$id": "urn:barbican:libshield",
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object"
}
"""
)


_SENTRY_SCHEMA = json.loads(
    """
{
    "$id": "urn:barbican:sentry",
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object"
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
        "sentry": {
            "$ref": "urn:barbican:sentry"
        },
        "libshield": {
            "$ref": "urn:barbican:libshield"
        },
        "app": {
            "patternProperties": {
                ".*": {
                    "type": "object",
                    "$ref": "urn:barbican:application"
                }
            },
            "additionalProperties": false
        }
    },
    "required": [ "name", "dts", "sentry", "libshield", "version" ],
    "dependentRequired": {
        "license": ["license_file"],
        "license_file": ["license"]
    }
}
"""
)


def validate(config: dict[str, T.Any]) -> None:
    registry: Registry = Resource.from_contents(_APPLICATION_SCHEMA) @ Registry()
    registry = Resource.from_contents(_LIBSHIELD_SCHEMA) @ registry
    registry = Resource.from_contents(_SENTRY_SCHEMA) @ registry
    registry = Resource.from_contents(_PROJECT_SCHEMA) @ registry
    validator = Draft202012Validator(
        _PROJECT_SCHEMA,
        registry=registry,
    )
    validator.validate(config)
