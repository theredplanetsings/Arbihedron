#!/usr/bin/env python3
"""Script to update imports after package reorganization."""
import re
from pathlib import Path

# Define import mappings
IMPORT_MAPPINGS = {
    # Base modules
    r'\bfrom models import\b': 'from arbihedron.models import',
    r'\bimport models\b': 'import arbihedron.models as models',
    r'\bfrom config import\b': 'from arbihedron.config import',
    r'\bimport config\b': 'import arbihedron.config as config',
    r'\bfrom utils import\b': 'from arbihedron.utils import',
    r'\bimport utils\b': 'import arbihedron.utils as utils',
    
    # Core modules
    r'\bfrom arbitrage_engine import\b': 'from arbihedron.core.arbitrage_engine import',
    r'\bfrom gnn_arbitrage_engine import\b': 'from arbihedron.core.gnn_arbitrage_engine import',
    r'\bfrom executor import\b': 'from arbihedron.core.executor import',
    r'\bfrom exchange_client import\b': 'from arbihedron.core.exchange_client import',
    
    # Infrastructure
    r'\bfrom cache import\b': 'from arbihedron.infrastructure.cache import',
    r'\bfrom database import\b': 'from arbihedron.infrastructure.database import',
    r'\bfrom error_handling import\b': 'from arbihedron.infrastructure.error_handling import',
    r'\bfrom performance import\b': 'from arbihedron.infrastructure.performance import',
    r'\bfrom health_monitor import\b': 'from arbihedron.infrastructure.health_monitor import',
    
    # Monitoring
    r'\bfrom monitor import\b': 'from arbihedron.monitoring.monitor import',
    r'\bfrom alerts import\b': 'from arbihedron.monitoring.alerts import',
    r'\bfrom analytics import\b': 'from arbihedron.monitoring.analytics import',
    
    # Tools
    r'\bfrom backtest import\b': 'from arbihedron.tools.backtest import',
    r'\bfrom compare_engines import\b': 'from arbihedron.tools.compare_engines import',
    r'\bfrom train_gnn_real import\b': 'from arbihedron.tools.train_gnn_real import',
    r'\bfrom view_data import\b': 'from arbihedron.tools.view_data import',
}

# Special case for within-package imports
WITHIN_PACKAGE_MAPPINGS = {
    'src/arbihedron/core': {
        r'\bfrom exchange_client import\b': 'from .exchange_client import',
        r'\bfrom arbitrage_engine import\b': 'from .arbitrage_engine import',
        r'\bfrom gnn_arbitrage_engine import\b': 'from .gnn_arbitrage_engine import',
        r'\bfrom executor import\b': 'from .executor import',
    },
    'src/arbihedron/infrastructure': {
        r'\bfrom cache import\b': 'from .cache import',
        r'\bfrom database import\b': 'from .database import',
        r'\bfrom error_handling import\b': 'from .error_handling import',
        r'\bfrom performance import\b': 'from .performance import',
        r'\bfrom health_monitor import\b': 'from .health_monitor import',
    },
    'src/arbihedron/monitoring': {
        r'\bfrom monitor import\b': 'from .monitor import',
        r'\bfrom alerts import\b': 'from .alerts import',
        r'\bfrom analytics import\b': 'from .analytics import',
    },
}

def update_file(filepath: Path):
    """Update imports in a file."""
    content = filepath.read_text()
    original = content
    
    # Determine if within-package replacements apply
    package_dir = None
    for pkg_path in WITHIN_PACKAGE_MAPPINGS:
        if pkg_path in str(filepath.parent):
            package_dir = pkg_path
            break
    
    # Apply within-package mappings first (higher priority)
    if package_dir:
        for pattern, replacement in WITHIN_PACKAGE_MAPPINGS[package_dir].items():
            content = re.sub(pattern, replacement, content)
    
    # Then apply general mappings
    for pattern, replacement in IMPORT_MAPPINGS.items():
        # Skip if it would create duplicate relative imports
        if package_dir and 'from .' in content and replacement.startswith('from arbihedron.'):
            module_name = replacement.split('.')[-2]  # Get module name
            if f'from .{module_name}' in content:
                continue
        content = re.sub(pattern, replacement, content)
    
    # Write back if changed
    if content != original:
        filepath.write_text(content)
        print(f"✓ Updated {filepath.relative_to(Path.cwd())}")
        return True
    return False

def main():
    """Update all files."""
    project_root = Path.cwd()
    
    # Update files in src/arbihedron
    updated_count = 0
    for filepath in project_root.glob('src/arbihedron/**/*.py'):
        if '__pycache__' not in str(filepath) and filepath.name != '__init__.py':
            if update_file(filepath):
                updated_count += 1
    
    # Update files in tests/
    for filepath in project_root.glob('tests/**/*.py'):
        if '__pycache__' not in str(filepath):
            if update_file(filepath):
                updated_count += 1
    
    # Update root files
    root_files = ['main.py', 'arbihedron_service.py', 'examples.py']
    for filename in root_files:
        filepath = project_root / filename
        if filepath.exists():
            if update_file(filepath):
                updated_count += 1
    
    print(f"\n✅ Updated {updated_count} files")

if __name__ == '__main__':
    main()
