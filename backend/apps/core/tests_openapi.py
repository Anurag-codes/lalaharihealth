import copy

import jsonschema
from django.test import SimpleTestCase
from drf_spectacular.generators import SchemaGenerator

METHODS = {'get', 'post', 'put', 'patch', 'delete'}


def _resolve(node, components, read_only_ok, depth=0):
    """Inline $refs and translate OpenAPI 3.0 keywords to JSON Schema."""
    if depth > 30 or not isinstance(node, (dict, list)):
        return node
    if isinstance(node, list):
        return [_resolve(item, components, read_only_ok, depth + 1) for item in node]
    if '$ref' in node:
        return _resolve(components[node['$ref'].split('/')[-1]], components, read_only_ok, depth + 1)
    node = {key: _resolve(value, components, read_only_ok, depth + 1) for key, value in node.items()}
    props = node.get('properties', {})
    skip = 'writeOnly' if read_only_ok else 'readOnly'
    if 'required' in node:
        node['required'] = [name for name in node['required'] if not props.get(name, {}).get(skip)]
    if node.pop('nullable', False):
        node = {'anyOf': [node, {'type': 'null'}]}
    if 'oneOf' in node:  # drf-spectacular uses oneOf for blank/URL choices that overlap without format checks
        node['anyOf'] = node.pop('oneOf')
    return node


def _examples(media):
    if 'example' in media:
        yield media['example']
    for example in media.get('examples', {}).values():
        yield example['value']


class OpenApiCompletenessTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.schema = SchemaGenerator().get_schema(request=None, public=True)
        cls.components = cls.schema['components']['schemas']

    def operations(self):
        for path, methods in self.schema['paths'].items():
            for method, op in methods.items():
                if method in METHODS:
                    yield f'{method.upper()} {path}', op

    def test_every_operation_is_documented_with_examples_and_errors(self):
        problems = []
        for key, op in self.operations():
            if not op.get('description'):
                problems.append(f'{key}: description')
            for media in op.get('requestBody', {}).get('content', {}).values():
                if not list(_examples(media)):
                    problems.append(f'{key}: request example')
            codes = op.get('responses', {})
            public = not op.get('security') or {} in op['security']
            takes_input = 'requestBody' in op or op.get('parameters')
            if (not public or takes_input) and not any(code.startswith('4') for code in codes):
                problems.append(f'{key}: error response')
            for code, response in codes.items():
                for content_type, media in response.get('content', {}).items():
                    if 'json' in content_type and not list(_examples(media)):
                        problems.append(f'{key}: {code} response example')
        self.assertEqual(problems, [])

    def test_examples_match_their_schemas(self):
        problems = []
        for key, op in self.operations():
            targets = [(media, False) for media in op.get('requestBody', {}).get('content', {}).values()]
            for code, response in op.get('responses', {}).items():
                targets += [(media, True) for ct, media in response.get('content', {}).items() if 'json' in ct]
            for media, is_response in targets:
                schema = _resolve(copy.deepcopy(media.get('schema', {})), self.components, is_response)
                for value in _examples(media):
                    error = jsonschema.exceptions.best_match(jsonschema.Draft7Validator(schema).iter_errors(value))
                    if error:
                        problems.append(f'{key}: {"/".join(map(str, error.absolute_path))} {error.message[:120]}')
        self.assertEqual(problems, [])
