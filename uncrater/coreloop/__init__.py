"""Expose bundled pycoreloop versions shipped with uncrater.

Historical bindings stay available as ``pycoreloop.pycoreloop_<ver>`` and are
importable as attributes on this package for convenience. We keep the newest
bundled bindings (307) as the default export for legacy callers of
``import pycoreloop``.
"""

import importlib, os, sys

# Import versioned bindings as submodules so their symbols (e.g. appId_from_value)
# are reachable via pycoreloop.pycoreloop_XXX
pycoreloop_203 = importlib.import_module('.pycoreloop_203', __name__)
pycoreloop_305 = importlib.import_module('.pycoreloop_305', __name__)
pycoreloop_307 = importlib.import_module('.pycoreloop_307', __name__)

if os.environ.get('CORELOOP_DIR') is not None:
    sys.path.append(os.environ.get('CORELOOP_DIR'))

# now try to import pycoreloop
try:
    import pycoreloop
except ImportError:
    print ("Can't import pycoreloop from CORELOOP_DIR. Will revert too 307.\n")
    pycoreloop = pycoreloop_307

__all__ = [
	'pycoreloop_203',
	'pycoreloop_305',
	'pycoreloop_307',
    'pycoreloop'
]
