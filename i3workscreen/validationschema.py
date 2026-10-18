
schema = {
    "type": "object",
    "properties": {
        "disableEmptyOutputs": {"type": "boolean"},
        "outputs": {
            "type": "array",
            "items": {
                "type": "object",
                "anyOf": [
                    {"required": ["name"]},
                    {"required": ["edid"]},
                ],
                "properties": {
                    "name": {"type": "string"},
                    "edid": {
                        "type": "object",
                        "properties": {
                            "model": {"type": "string"},
                            "serial": {"type": "string"},
                        },
                        "additionalProperties": False,
                        "minProperties": 1,
                    },
                    "xrandr": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "workspaces": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                }
            }
        }
    }
}
