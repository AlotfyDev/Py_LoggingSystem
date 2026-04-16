import ast
import json
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any
from collections import defaultdict
import re

class BehavioralExtractor(ast.NodeVisitor):
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.lines = open(file_path, 'r', encoding='utf-8').readlines()
        self.current_class = None
        self.current_method = None
        self.current_method_line = None
        
        self.calls = []  # (caller_class, caller_method, target_class, target_method, line)
        self.instances = defaultdict(list)  # class_name -> [(var_name, line)]
        self.depends_on = defaultdict(set)  # entity -> set of imports
        self.implements = defaultdict(set)  # class -> set of protocols
        self.extends = defaultdict(set)  # class -> set of base classes
        self.self_vars = {}  # method -> var_name for self
        
    def extract(self) -> Dict:
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                tree = ast.parse(f.read(), filename=self.file_path)
            self.visit(tree)
        except Exception as e:
            print(f"Error parsing {self.file_path}: {e}")
        return {
            'calls': self.calls,
            'instances': dict(self.instances),
            'depends_on': {k: list(v) for k, v in self.depends_on.items()},
            'implements': {k: list(v) for k, v in self.implements.items()},
            'extends': {k: list(v) for k, v in self.extends.items()}
        }
    
    def visit_Import(self, node):
        for alias in node.names:
            name = alias.asname if alias.asname else alias.name
            self._add_dependency(name, node.lineno)
        return node
    
    def visit_ImportFrom(self, node):
        if node.module:
            for alias in node.names:
                name = alias.asname if alias.asname else alias.name
                full_name = f"{node.module}.{alias.name}" if alias.name != '*' else node.module
                self._add_dependency(full_name, node.lineno)
        return node
    
    def _add_dependency(self, name: str, line: int):
        if self.current_class:
            self.depends_on[self.current_class].add(name.split('.')[0])
        elif self.current_method:
            self.depends_on[self.current_method].add(name.split('.')[0])
    
    def visit_ClassDef(self, node):
        old_class = self.current_class
        self.current_class = node.name
        
        for base in node.bases:
            base_name = self._get_name(base)
            if base_name:
                self.extends[node.name].add(base_name)
                self.depends_on[node.name].add(base_name.split('.')[0])
        
        for item in node.body:
            if isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name):
                        value_name = self._get_name(item.value)
                        if value_name == node.name:
                            self.instances[node.name].append({
                                'var_name': target.id,
                                'line': item.lineno
                            })
        
        self.generic_visit(node)
        self.current_class = old_class
    
    def visit_FunctionDef(self, node):
        old_method = self.current_method
        old_line = self.current_method_line
        self.current_method = node.name
        self.current_method_line = node.lineno
        
        if node.args.args:
            first_arg = node.args.args[0]
            if first_arg.arg == 'self':
                self.self_vars[node.name] = 'self'
        
        self.generic_visit(node)
        self.current_method = old_method
        self.current_method_line = old_line
    
    def visit_AsyncFunctionDef(self, node):
        self.visit_FunctionDef(node)
    
    def visit_Call(self, node):
        target_class = None
        target_method = None
        
        if isinstance(node.func, ast.Attribute):
            attr_name = node.func.attr
            
            if isinstance(node.func.value, ast.Name):
                var_name = node.func.value.id
                if var_name in ('self', 'cls'):
                    target_class = self.current_class
                    target_method = attr_name
                else:
                    target_class = var_name
                    target_method = attr_name
            elif isinstance(node.func.value, ast.Attribute):
                target_class = self._get_name(node.func.value)
                target_method = attr_name
            else:
                target_class = self._get_name(node.func.value)
                target_method = attr_name
        elif isinstance(node.func, ast.Name):
            target_class = None
            target_method = node.func.id
        
        if target_method:
            self.calls.append({
                'caller': {
                    'class': self.current_class,
                    'method': self.current_method,
                    'line': self.current_method_line
                },
                'target': {
                    'class': target_class,
                    'method': target_method
                },
                'line': node.lineno
            })
        
        self.generic_visit(node)
    
    def _get_name(self, node) -> str:
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            value = self._get_name(node.value)
            return f"{value}.{node.attr}" if value else node.attr
        elif isinstance(node, ast.Subscript):
            value = self._get_name(node.value)
            return value
        elif isinstance(node, ast.Call):
            return self._get_name(node.func)
        return None


def is_test_file(path: Path) -> bool:
    name = path.name.lower()
    return (
        'test_' in name or
        name.endswith('_test.py') or
        '/tests/' in str(path).replace('\\', '/') or
        'obsolete' in str(path).lower()
    )


def extract_behavioral_data(source_dir: Path, exclude_dirs: Set[str]) -> Dict[str, Any]:
    results = {
        'calls': [],
        'instances': defaultdict(list),
        'depends_on': defaultdict(set),
        'implements': defaultdict(set),
        'extends': defaultdict(set)
    }
    
    for py_file in source_dir.rglob('*.py'):
        if is_test_file(py_file):
            continue
        
        rel_path = py_file.relative_to(source_dir)
        if any(excl in str(rel_path) for excl in exclude_dirs):
            continue
        
        extractor = BehavioralExtractor(str(py_file))
        data = extractor.extract()
        
        for call in data['calls']:
            call['file'] = str(rel_path)
            results['calls'].append(call)
        
        for cls, insts in data['instances'].items():
            for inst in insts:
                inst['file'] = str(rel_path)
            results['instances'][cls].extend(insts)
        
        for entity, deps in data['depends_on'].items():
            results['depends_on'][entity].update(deps)
        
        for cls, protos in data['implements'].items():
            results['implements'][cls].update(protos)
        
        for cls, bases in data['extends'].items():
            results['extends'][cls].update(bases)
    
    return results


def enrich_taxonomy(taxonomy: Dict, behavior_data: Dict) -> Dict:
    entity_names = {e['identity']['name'] for e in taxonomy['entities']}
    called_by_map = defaultdict(list)
    
    for call in behavior_data['calls']:
        caller = call['caller']
        target = call['target']
        
        if target['class'] in entity_names or target['method'] in entity_names:
            target_name = target['class'] if target['class'] in entity_names else target['method']
            
            for entity in taxonomy['entities']:
                if entity['identity']['name'] == target_name:
                    entity['behavior']['calls'].append({
                        'target': target_name,
                        'method': target.get('method', ''),
                        'count': 1,
                        'logical_container': {
                            'class': caller.get('class', ''),
                            'method': caller.get('method', '')
                        },
                        'physical_container': {
                            'file': call.get('file', ''),
                            'lines': [call.get('line', 0)]
                        },
                        'invocations': [{
                            'method': caller.get('method', ''),
                            'line': call.get('line', 0)
                        }]
                    })
                    
                    caller_name = caller.get('class', caller.get('method', ''))
                    if caller_name:
                        called_by_map[(target_name, caller_name)].append({
                            'method': caller.get('method', ''),
                            'line': call.get('line', 0)
                        })
                    break
    
    for call_list in behavior_data['calls']:
        target = call_list['target']
        caller = call_list['caller']
        target_name = target['class'] if target['class'] in entity_names else target.get('method', '')
        caller_name = caller.get('class', caller.get('method', ''))
        
        if caller_name in entity_names:
            for entity in taxonomy['entities']:
                if entity['identity']['name'] == caller_name:
                    key = (caller_name, target_name)
                    if key in called_by_map:
                        invocations = called_by_map[key]
                        entity['behavior']['called_by'].append({
                            'source': target_name,
                            'method': target.get('method', ''),
                            'count': len(invocations),
                            'logical_container': {
                                'class': target.get('class', ''),
                                'method': ''
                            },
                            'physical_container': {
                                'file': call_list.get('file', ''),
                                'lines': [inv['line'] for inv in invocations]
                            },
                            'invocations': invocations
                        })
                    break
    
    for entity in taxonomy['entities']:
        name = entity['identity']['name']
        
        for dep in behavior_data['depends_on'].get(name, []):
            if dep in entity_names:
                entity['behavior']['depends_on'].append(dep)
        
        for proto in behavior_data['implements'].get(name, []):
            if proto in entity_names:
                entity['behavior']['implements'].append(proto)
        
        for base in behavior_data['extends'].get(name, []):
            if base in entity_names:
                entity['behavior']['extends'].append(base)
    
    return taxonomy


def aggregate_counts(taxonomy: Dict) -> Dict:
    for entity in taxonomy['entities']:
        entity['behavior']['calls_count'] = sum(c['count'] for c in entity['behavior']['calls'])
        entity['behavior']['called_by_count'] = sum(c['count'] for c in entity['behavior']['called_by'])
    
    return taxonomy


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Extract behavioral data from Python codebase')
    parser.add_argument('--source', required=True, help='Source directory to analyze')
    parser.add_argument('--taxonomy', required=True, help='Existing taxonomy JSON file')
    parser.add_argument('--output', required=True, help='Output file path')
    parser.add_argument('--exclude', nargs='*', default=['tests', 'Obsolete', '.venv', 'venv', '__pycache__'],
                        help='Directories to exclude')
    
    args = parser.parse_args()
    
    source_dir = Path(args.source)
    taxonomy_path = Path(args.taxonomy)
    
    print(f"Extracting behavioral data from: {source_dir}")
    print(f"Using taxonomy: {taxonomy_path}")
    print(f"Excluding: {args.exclude}")
    
    behavior_data = extract_behavioral_data(source_dir, set(args.exclude))
    
    print(f"\nExtracted:")
    print(f"  - {len(behavior_data['calls'])} calls")
    print(f"  - {sum(len(v) for v in behavior_data['instances'].values())} named instances")
    print(f"  - {len(behavior_data['depends_on'])} dependencies")
    
    with open(taxonomy_path, 'r', encoding='utf-8') as f:
        taxonomy = json.load(f)
    
    taxonomy = enrich_taxonomy(taxonomy, behavior_data)
    taxonomy = aggregate_counts(taxonomy)
    
    output_path = Path(args.output)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(taxonomy, f, indent=2)
    
    print(f"\nEnriched taxonomy saved to: {output_path}")
    
    calls_with_targets = [c for c in taxonomy['entities'] if c['behavior']['calls_count'] > 0]
    print(f"\nEntities with CALLS: {len(calls_with_targets)}")
    for e in calls_with_targets[:10]:
        print(f"  - {e['identity']['name']}: {e['behavior']['calls_count']} calls")


if __name__ == '__main__':
    main()
