
schema = {
    "type": "object",
    "properties": {
        "disableEmptyOutputs": {"type": "boolean"},
        "outputs": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
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
