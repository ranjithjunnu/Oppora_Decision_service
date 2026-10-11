"""Prepare Pydantic JSON schemas for strict compatible chat providers."""


def strict_schema(node):
    if isinstance(node, dict):
        node.pop('default', None)
        if node.get('type') == 'object' and 'properties' in node:
            node['required'] = list(node['properties'])
            node['additionalProperties'] = False
        for value in node.values():
            strict_schema(value)
    elif isinstance(node, list):
        for value in node:
            strict_schema(value)

