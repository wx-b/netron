''' scikit-learn metadata script '''

import json
import os
import pydoc
import re
import sys

def _split_docstring(value):
    headers = {}
    current_header = ''
    current_lines = []
    lines = value.split('\n')
    index = 0
    while index < len(lines):
        if index + 1 < len(lines) and len(lines[index + 1].strip(' ')) > 0 and \
            len(lines[index + 1].strip(' ').strip('-')) == 0:
            headers[current_header] = current_lines
            current_header = lines[index].strip(' ')
            current_lines = []
            index = index + 1
        else:
            current_lines.append(lines[index])
        index = index + 1
    headers[current_header] = current_lines
    return headers

def _update_description(schema, lines):
    if len(''.join(lines).strip(' ')) > 0:
        for i, value in enumerate(lines):
            lines[i] = value.lstrip(' ')
        schema['description'] = '\n'.join(lines)

def _attribute_value(attribute_type, attribute_value):
    if attribute_type == 'float32':
        if attribute_value == 'None':
            return None
        if attribute_value != "'auto'":
            return float(attribute_value)
        return attribute_value.strip("'").strip('"')
    if attribute_type == 'int32':
        if attribute_value == 'None':
            return None
        if attribute_value in ("'auto'", '"auto"'):
            return attribute_value.strip("'").strip('"')
        return int(attribute_value)
    if attribute_type == 'string':
        return attribute_value.strip("'").strip('"')
    if attribute_type == 'boolean':
        if attribute_value == 'True':
            return True
        if attribute_value == 'False':
            return False
        if attribute_value == "'auto'":
            return attribute_value.strip("'").strip('"')
        raise Exception("Unknown boolean default value '" + str(attribute_value) + "'.")
    if attribute_type:
        raise Exception("Unknown default type '" + attribute_type + "'.")
    if attribute_value == 'None':
        return None
    return attribute_value.strip("'")

def _update_attribute(schema, name, description, attribute_type, optional, default_value):
    attribute = None
    if not 'attributes' in schema:
        schema['attributes'] = []
    for current_attribute in schema['attributes']:
        if 'name' in current_attribute and current_attribute['name'] == name:
            attribute = current_attribute
            break
    if not attribute:
        attribute = {}
        attribute['name'] = name
        schema['attributes'].append(attribute)
    attribute['description'] = description
    if attribute_type:
        attribute['type'] = attribute_type
    if optional:
        attribute['optional'] = True
    if default_value:
        attribute['default'] = _attribute_value(attribute_type, default_value)

def _update_attributes(schema, lines):
    i = 0
    while i < len(lines):
        line = lines[i]
        line = re.sub(r',\s+', ', ', line)
        if line.endswith('.'):
            line = line[0:-1]
        colon = line.find(':')
        if colon == -1:
            raise Exception("Expected ':' in parameter.")
        name = line[0:colon].strip(' ')
        line = line[colon + 1:].strip(' ')
        attribute_type = None
        type_map = {
            'float': 'float32',
            'boolean': 'boolean',
            'bool': 'boolean',
            'string': 'string',
            'int': 'int32',
            'integer': 'int32'
        }
        skip_map = {
            "'sigmoid' or 'isotonic'",
            'instance BaseEstimator',
            'callable or None (default)',
            'str or callable',
            "string {'english'}, list, or None (default)",
            'tuple (min_n, max_n)',
            "string, {'word', 'char', 'char_wb'} or callable",
            "{'word', 'char'} or callable",
            "string, {'word', 'char'} or callable",
            'int, float, None or string',
            "int, float, None or str",
            "int or None, optional (default=None)",
            "'l1', 'l2' or None, optional",
            "{'strict', 'ignore', 'replace'} (default='strict')",
            "{'ascii', 'unicode', None} (default=None)",
            "string {'english'}, list, or None (default=None)",
            "tuple (min_n, max_n) (default=(1, 1))",
            "float in range [0.0, 1.0] or int (default=1.0)",
            "float in range [0.0, 1.0] or int (default=1)",
            "'l1', 'l2' or None, optional (default='l2')",
            "str {'auto', 'full', 'arpack', 'randomized'}",
            "str {'filename', 'file', 'content'}",
            "str, {'word', 'char', 'char_wb'} or callable",
            "str {'english'}, list, or None (default=None)",
            "{'scale', 'auto'} or float, optional (default='scale')",
            "{'word', 'char', 'char_wb'} or callable, default='word'",
            "{'scale', 'auto'} or float, default='scale'",
            "{'uniform', 'distance'} or callable, default='uniform'",
            "int, RandomState instance or None (default)",
            "list of (string, transformer) tuples",
            "list of tuples",
            "{'drop', 'passthrough'} or estimator, default='drop'",
            "'auto' or a list of array-like, default='auto'",
            "callable",
            "int or \"all\", optional, default=10",
            "number, string, np.nan (default) or None",
            "estimator object",
            "dict or list of dictionaries",
            "int, or str, default=n_jobs",
            "'raise' or numeric, default=np.nan",
            "'auto' or float, default=None",
            "float, default=np.finfo(float).eps",
            "int, float, str, np.nan or None, default=np.nan",
            "list of (str, transformer) tuples",
            "int, float, str, np.nan, None or pandas.NA, default=np.nan",
            "{'first', 'if_binary'} or an array-like of shape (n_features,), default=None",
            "{'first', 'if_binary'} or a array-like of shape (n_features,), default=None",
            "{'linear', 'poly', 'rbf', 'sigmoid', 'precomputed'} or callable, default='rbf'",
            "estimator instance",
            "{'ascii', 'unicode'} or callable, default=None",
            "{'l1', 'l2'} or None, default='l2'"
        }
        if line == 'str':
            line = 'string'
        if line in skip_map:
            line = ''
        elif line.startswith('{'):
            if line.endswith('}'):
                line = ''
            else:
                end = line.find('},')
                if end == -1:
                    raise Exception("Expected '}' in parameter.")
                # attribute_type = line[0:end + 1]
                line = line[end + 2:].strip(' ')
        elif line.startswith("'"):
            while line.startswith("'"):
                end = line.find("',")
                if end == -1:
                    raise Exception("Expected \' in parameter.")
                line = line[end + 2:].strip(' ')
        elif line in type_map:
            attribute_type = line
            line = ''
        elif line.startswith('int, RandomState instance or None,'):
            line = line[len('int, RandomState instance or None,'):]
        elif line.startswith('int, or str, '):
            line = line[len('int, or str, '):]
        elif line.find('|') != -1:
            line = ''
        else:
            space = line.find(' {')
            if space != -1 and line[0:space] in type_map and line[space:].find('}') != -1:
                attribute_type = line[0:space]
                end = line[space:].find('}')
                line = line[space+end+1:]
            else:
                comma = line.find(',')
                if comma == -1:
                    comma = line.find(' (')
                    if comma == -1:
                        raise Exception("Expected ',' in parameter.")
                attribute_type = line[0:comma]
                line = line[comma + 1:].strip(' ')
        attribute_type = type_map.get(attribute_type, None)
        # elif type == "{dict, 'balanced'}":
        #    v = 'map'
        # else:
        #    raise Exception("Unknown attribute type '" + attribute_type + "'.")
        optional = False
        default = None
        while len(line.strip(' ')) > 0:
            line = line.strip(' ')
            if line.startswith('optional ') or line.startswith('optional,'):
                optional = True
                line = line[9:]
            elif line.startswith('optional'):
                optional = True
                line = ''
            elif line.startswith('('):
                close = line.index(')')
                if close == -1:
                    raise Exception("Expected ')' in parameter.")
                line = line[1:close]
            elif line.endswith(' by default'):
                default = line[0:-11]
                line = ''
            elif line.startswith('default =') or line.startswith('default :'):
                default = line[9:].strip(' ')
                line = ''
            elif line.startswith('default ') or \
                line.startswith('default=') or line.startswith('default:'):
                default = line[8:].strip(' ')
                line = ''
            else:
                comma = line.index(',')
                if comma == -1:
                    raise Exception("Expected ',' in parameter.")
                line = line[comma+1:]
        i = i + 1
        attribute_lines = []
        while i < len(lines) and (len(lines[i].strip(' ')) == 0 or lines[i].startswith('        ')):
            attribute_lines.append(lines[i].lstrip(' '))
            i = i + 1
        description = '\n'.join(attribute_lines)
        _update_attribute(schema, name, description, attribute_type, optional, default)

def _metadata():
    json_file = os.path.join(os.path.dirname(__file__), '../source/sklearn-metadata.json')
    with open(json_file, 'r', encoding='utf-8') as file:
        json_root = json.loads(file.read())

    for schema in json_root:
        name = schema['name']
        skip_modules = [
            'lightgbm.',
            'sklearn.svm.classes',
            'sklearn.ensemble.forest.',
            'sklearn.ensemble.weight_boosting.',
            'sklearn.neural_network.multilayer_perceptron.',
            'sklearn.tree.tree.'
        ]
        if not any(name.startswith(module) for module in skip_modules):
            class_definition = pydoc.locate(name)
            if not class_definition:
                raise Exception('\'' + name + '\' not found.')
            docstring = class_definition.__doc__
            if not docstring:
                raise Exception('\'' + name + '\' missing __doc__.')
            headers = _split_docstring(docstring)
            if '' in headers:
                _update_description(schema, headers[''])
            if 'Parameters' in headers:
                _update_attributes(schema, headers['Parameters'])

    with open(json_file, 'w', encoding='utf-8') as file:
        file.write(json.dumps(json_root, sort_keys=False, indent=2))

def main(): # pylint: disable=missing-function-docstring
    command_table = { 'metadata': _metadata }
    command = sys.argv[1]
    command_table[command]()

if __name__ == '__main__':
    main()
