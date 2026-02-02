r"""Wrapper for core_loop.h

Generated with:
/home/anze/anaconda3/bin/ctypesgen ../coreloop/core_loop.h ../coreloop/calibrator.h

Do not modify this file.
"""

__docformat__ = "restructuredtext"

# Begin preamble for Python

import ctypes
import sys
from ctypes import *  # noqa: F401, F403

_int_types = (ctypes.c_int16, ctypes.c_int32)
if hasattr(ctypes, "c_int64"):
    # Some builds of ctypes apparently do not have ctypes.c_int64
    # defined; it's a pretty good bet that these builds do not
    # have 64-bit pointers.
    _int_types += (ctypes.c_int64,)
for t in _int_types:
    if ctypes.sizeof(t) == ctypes.sizeof(ctypes.c_size_t):
        c_ptrdiff_t = t
del t
del _int_types



class UserString:
    def __init__(self, seq):
        if isinstance(seq, bytes):
            self.data = seq
        elif isinstance(seq, UserString):
            self.data = seq.data[:]
        else:
            self.data = str(seq).encode()

    def __bytes__(self):
        return self.data

    def __str__(self):
        return self.data.decode()

    def __repr__(self):
        return repr(self.data)

    def __int__(self):
        return int(self.data.decode())

    def __long__(self):
        return int(self.data.decode())

    def __float__(self):
        return float(self.data.decode())

    def __complex__(self):
        return complex(self.data.decode())

    def __hash__(self):
        return hash(self.data)

    def __le__(self, string):
        if isinstance(string, UserString):
            return self.data <= string.data
        else:
            return self.data <= string

    def __lt__(self, string):
        if isinstance(string, UserString):
            return self.data < string.data
        else:
            return self.data < string

    def __ge__(self, string):
        if isinstance(string, UserString):
            return self.data >= string.data
        else:
            return self.data >= string

    def __gt__(self, string):
        if isinstance(string, UserString):
            return self.data > string.data
        else:
            return self.data > string

    def __eq__(self, string):
        if isinstance(string, UserString):
            return self.data == string.data
        else:
            return self.data == string

    def __ne__(self, string):
        if isinstance(string, UserString):
            return self.data != string.data
        else:
            return self.data != string

    def __contains__(self, char):
        return char in self.data

    def __len__(self):
        return len(self.data)

    def __getitem__(self, index):
        return self.__class__(self.data[index])

    def __getslice__(self, start, end):
        start = max(start, 0)
        end = max(end, 0)
        return self.__class__(self.data[start:end])

    def __add__(self, other):
        if isinstance(other, UserString):
            return self.__class__(self.data + other.data)
        elif isinstance(other, bytes):
            return self.__class__(self.data + other)
        else:
            return self.__class__(self.data + str(other).encode())

    def __radd__(self, other):
        if isinstance(other, bytes):
            return self.__class__(other + self.data)
        else:
            return self.__class__(str(other).encode() + self.data)

    def __mul__(self, n):
        return self.__class__(self.data * n)

    __rmul__ = __mul__

    def __mod__(self, args):
        return self.__class__(self.data % args)

    # the following methods are defined in alphabetical order:
    def capitalize(self):
        return self.__class__(self.data.capitalize())

    def center(self, width, *args):
        return self.__class__(self.data.center(width, *args))

    def count(self, sub, start=0, end=sys.maxsize):
        return self.data.count(sub, start, end)

    def decode(self, encoding=None, errors=None):  # XXX improve this?
        if encoding:
            if errors:
                return self.__class__(self.data.decode(encoding, errors))
            else:
                return self.__class__(self.data.decode(encoding))
        else:
            return self.__class__(self.data.decode())

    def encode(self, encoding=None, errors=None):  # XXX improve this?
        if encoding:
            if errors:
                return self.__class__(self.data.encode(encoding, errors))
            else:
                return self.__class__(self.data.encode(encoding))
        else:
            return self.__class__(self.data.encode())

    def endswith(self, suffix, start=0, end=sys.maxsize):
        return self.data.endswith(suffix, start, end)

    def expandtabs(self, tabsize=8):
        return self.__class__(self.data.expandtabs(tabsize))

    def find(self, sub, start=0, end=sys.maxsize):
        return self.data.find(sub, start, end)

    def index(self, sub, start=0, end=sys.maxsize):
        return self.data.index(sub, start, end)

    def isalpha(self):
        return self.data.isalpha()

    def isalnum(self):
        return self.data.isalnum()

    def isdecimal(self):
        return self.data.isdecimal()

    def isdigit(self):
        return self.data.isdigit()

    def islower(self):
        return self.data.islower()

    def isnumeric(self):
        return self.data.isnumeric()

    def isspace(self):
        return self.data.isspace()

    def istitle(self):
        return self.data.istitle()

    def isupper(self):
        return self.data.isupper()

    def join(self, seq):
        return self.data.join(seq)

    def ljust(self, width, *args):
        return self.__class__(self.data.ljust(width, *args))

    def lower(self):
        return self.__class__(self.data.lower())

    def lstrip(self, chars=None):
        return self.__class__(self.data.lstrip(chars))

    def partition(self, sep):
        return self.data.partition(sep)

    def replace(self, old, new, maxsplit=-1):
        return self.__class__(self.data.replace(old, new, maxsplit))

    def rfind(self, sub, start=0, end=sys.maxsize):
        return self.data.rfind(sub, start, end)

    def rindex(self, sub, start=0, end=sys.maxsize):
        return self.data.rindex(sub, start, end)

    def rjust(self, width, *args):
        return self.__class__(self.data.rjust(width, *args))

    def rpartition(self, sep):
        return self.data.rpartition(sep)

    def rstrip(self, chars=None):
        return self.__class__(self.data.rstrip(chars))

    def split(self, sep=None, maxsplit=-1):
        return self.data.split(sep, maxsplit)

    def rsplit(self, sep=None, maxsplit=-1):
        return self.data.rsplit(sep, maxsplit)

    def splitlines(self, keepends=0):
        return self.data.splitlines(keepends)

    def startswith(self, prefix, start=0, end=sys.maxsize):
        return self.data.startswith(prefix, start, end)

    def strip(self, chars=None):
        return self.__class__(self.data.strip(chars))

    def swapcase(self):
        return self.__class__(self.data.swapcase())

    def title(self):
        return self.__class__(self.data.title())

    def translate(self, *args):
        return self.__class__(self.data.translate(*args))

    def upper(self):
        return self.__class__(self.data.upper())

    def zfill(self, width):
        return self.__class__(self.data.zfill(width))


class MutableString(UserString):
    """mutable string objects

    Python strings are immutable objects.  This has the advantage, that
    strings may be used as dictionary keys.  If this property isn't needed
    and you insist on changing string values in place instead, you may cheat
    and use MutableString.

    But the purpose of this class is an educational one: to prevent
    people from inventing their own mutable string class derived
    from UserString and than forget thereby to remove (override) the
    __hash__ method inherited from UserString.  This would lead to
    errors that would be very hard to track down.

    A faster and better solution is to rewrite your program using lists."""

    def __init__(self, string=""):
        self.data = string

    def __hash__(self):
        raise TypeError("unhashable type (it is mutable)")

    def __setitem__(self, index, sub):
        if index < 0:
            index += len(self.data)
        if index < 0 or index >= len(self.data):
            raise IndexError
        self.data = self.data[:index] + sub + self.data[index + 1 :]

    def __delitem__(self, index):
        if index < 0:
            index += len(self.data)
        if index < 0 or index >= len(self.data):
            raise IndexError
        self.data = self.data[:index] + self.data[index + 1 :]

    def __setslice__(self, start, end, sub):
        start = max(start, 0)
        end = max(end, 0)
        if isinstance(sub, UserString):
            self.data = self.data[:start] + sub.data + self.data[end:]
        elif isinstance(sub, bytes):
            self.data = self.data[:start] + sub + self.data[end:]
        else:
            self.data = self.data[:start] + str(sub).encode() + self.data[end:]

    def __delslice__(self, start, end):
        start = max(start, 0)
        end = max(end, 0)
        self.data = self.data[:start] + self.data[end:]

    def immutable(self):
        return UserString(self.data)

    def __iadd__(self, other):
        if isinstance(other, UserString):
            self.data += other.data
        elif isinstance(other, bytes):
            self.data += other
        else:
            self.data += str(other).encode()
        return self

    def __imul__(self, n):
        self.data *= n
        return self


class String(MutableString, ctypes.Union):

    _fields_ = [("raw", ctypes.POINTER(ctypes.c_char)), ("data", ctypes.c_char_p)]

    def __init__(self, obj=b""):
        if isinstance(obj, (bytes, UserString)):
            self.data = bytes(obj)
        else:
            self.raw = obj

    def __len__(self):
        return self.data and len(self.data) or 0

    def from_param(cls, obj):
        # Convert None or 0
        if obj is None or obj == 0:
            return cls(ctypes.POINTER(ctypes.c_char)())

        # Convert from String
        elif isinstance(obj, String):
            return obj

        # Convert from bytes
        elif isinstance(obj, bytes):
            return cls(obj)

        # Convert from str
        elif isinstance(obj, str):
            return cls(obj.encode())

        # Convert from c_char_p
        elif isinstance(obj, ctypes.c_char_p):
            return obj

        # Convert from POINTER(ctypes.c_char)
        elif isinstance(obj, ctypes.POINTER(ctypes.c_char)):
            return obj

        # Convert from raw pointer
        elif isinstance(obj, int):
            return cls(ctypes.cast(obj, ctypes.POINTER(ctypes.c_char)))

        # Convert from ctypes.c_char array
        elif isinstance(obj, ctypes.c_char * len(obj)):
            return obj

        # Convert from object
        else:
            return String.from_param(obj._as_parameter_)

    from_param = classmethod(from_param)


def ReturnString(obj, func=None, arguments=None):
    return String.from_param(obj)


# As of ctypes 1.0, ctypes does not support custom error-checking
# functions on callbacks, nor does it support custom datatypes on
# callbacks, so we must ensure that all callbacks return
# primitive datatypes.
#
# Non-primitive return values wrapped with UNCHECKED won't be
# typechecked, and will be converted to ctypes.c_void_p.
def UNCHECKED(type):
    if hasattr(type, "_type_") and isinstance(type._type_, str) and type._type_ != "P":
        return type
    else:
        return ctypes.c_void_p


# ctypes doesn't have direct support for variadic functions, so we have to write
# our own wrapper class
class _variadic_function(object):
    def __init__(self, func, restype, argtypes, errcheck):
        self.func = func
        self.func.restype = restype
        self.argtypes = argtypes
        if errcheck:
            self.func.errcheck = errcheck

    def _as_parameter_(self):
        # So we can pass this variadic function as a function pointer
        return self.func

    def __call__(self, *args):
        fixed_args = []
        i = 0
        for argtype in self.argtypes:
            # Typecheck what we can
            fixed_args.append(argtype.from_param(args[i]))
            i += 1
        return self.func(*fixed_args + list(args[i:]))


def ord_if_char(value):
    """
    Simple helper used for casts to simple builtin types:  if the argument is a
    string type, it will be converted to it's ordinal value.

    This function will raise an exception if the argument is string with more
    than one characters.
    """
    return ord(value) if (isinstance(value, bytes) or isinstance(value, str)) else value

# End preamble

_libs = {}
_libdirs = []

# Begin loader

"""
Load libraries - appropriately for all our supported platforms
"""
# ----------------------------------------------------------------------------
# Copyright (c) 2008 David James
# Copyright (c) 2006-2008 Alex Holkner
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in
#    the documentation and/or other materials provided with the
#    distribution.
#  * Neither the name of pyglet nor the names of its
#    contributors may be used to endorse or promote products
#    derived from this software without specific prior written
#    permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
# ----------------------------------------------------------------------------

import ctypes
import ctypes.util
import glob
import os.path
import platform
import re
import sys


def _environ_path(name):
    """Split an environment variable into a path-like list elements"""
    if name in os.environ:
        return os.environ[name].split(":")
    return []


class LibraryLoader:
    """
    A base class For loading of libraries ;-)
    Subclasses load libraries for specific platforms.
    """

    # library names formatted specifically for platforms
    name_formats = ["%s"]

    class Lookup:
        """Looking up calling conventions for a platform"""

        mode = ctypes.DEFAULT_MODE

        def __init__(self, path):
            super(LibraryLoader.Lookup, self).__init__()
            self.access = dict(cdecl=ctypes.CDLL(path, self.mode))

        def get(self, name, calling_convention="cdecl"):
            """Return the given name according to the selected calling convention"""
            if calling_convention not in self.access:
                raise LookupError(
                    "Unknown calling convention '{}' for function '{}'".format(
                        calling_convention, name
                    )
                )
            return getattr(self.access[calling_convention], name)

        def has(self, name, calling_convention="cdecl"):
            """Return True if this given calling convention finds the given 'name'"""
            if calling_convention not in self.access:
                return False
            return hasattr(self.access[calling_convention], name)

        def __getattr__(self, name):
            return getattr(self.access["cdecl"], name)

    def __init__(self):
        self.other_dirs = []

    def __call__(self, libname):
        """Given the name of a library, load it."""
        paths = self.getpaths(libname)

        for path in paths:
            # noinspection PyBroadException
            try:
                return self.Lookup(path)
            except Exception:  # pylint: disable=broad-except
                pass

        raise ImportError("Could not load %s." % libname)

    def getpaths(self, libname):
        """Return a list of paths where the library might be found."""
        if os.path.isabs(libname):
            yield libname
        else:
            # search through a prioritized series of locations for the library

            # we first search any specific directories identified by user
            for dir_i in self.other_dirs:
                for fmt in self.name_formats:
                    # dir_i should be absolute already
                    yield os.path.join(dir_i, fmt % libname)

            # check if this code is even stored in a physical file
            try:
                this_file = __file__
            except NameError:
                this_file = None

            # then we search the directory where the generated python interface is stored
            if this_file is not None:
                for fmt in self.name_formats:
                    yield os.path.abspath(os.path.join(os.path.dirname(__file__), fmt % libname))

            # now, use the ctypes tools to try to find the library
            for fmt in self.name_formats:
                path = ctypes.util.find_library(fmt % libname)
                if path:
                    yield path

            # then we search all paths identified as platform-specific lib paths
            for path in self.getplatformpaths(libname):
                yield path

            # Finally, we'll try the users current working directory
            for fmt in self.name_formats:
                yield os.path.abspath(os.path.join(os.path.curdir, fmt % libname))

    def getplatformpaths(self, _libname):  # pylint: disable=no-self-use
        """Return all the library paths available in this platform"""
        return []


# Darwin (Mac OS X)


class DarwinLibraryLoader(LibraryLoader):
    """Library loader for MacOS"""

    name_formats = [
        "lib%s.dylib",
        "lib%s.so",
        "lib%s.bundle",
        "%s.dylib",
        "%s.so",
        "%s.bundle",
        "%s",
    ]

    class Lookup(LibraryLoader.Lookup):
        """
        Looking up library files for this platform (Darwin aka MacOS)
        """

        # Darwin requires dlopen to be called with mode RTLD_GLOBAL instead
        # of the default RTLD_LOCAL.  Without this, you end up with
        # libraries not being loadable, resulting in "Symbol not found"
        # errors
        mode = ctypes.RTLD_GLOBAL

    def getplatformpaths(self, libname):
        if os.path.pathsep in libname:
            names = [libname]
        else:
            names = [fmt % libname for fmt in self.name_formats]

        for directory in self.getdirs(libname):
            for name in names:
                yield os.path.join(directory, name)

    @staticmethod
    def getdirs(libname):
        """Implements the dylib search as specified in Apple documentation:

        http://developer.apple.com/documentation/DeveloperTools/Conceptual/
            DynamicLibraries/Articles/DynamicLibraryUsageGuidelines.html

        Before commencing the standard search, the method first checks
        the bundle's ``Frameworks`` directory if the application is running
        within a bundle (OS X .app).
        """

        dyld_fallback_library_path = _environ_path("DYLD_FALLBACK_LIBRARY_PATH")
        if not dyld_fallback_library_path:
            dyld_fallback_library_path = [
                os.path.expanduser("~/lib"),
                "/usr/local/lib",
                "/usr/lib",
            ]

        dirs = []

        if "/" in libname:
            dirs.extend(_environ_path("DYLD_LIBRARY_PATH"))
        else:
            dirs.extend(_environ_path("LD_LIBRARY_PATH"))
            dirs.extend(_environ_path("DYLD_LIBRARY_PATH"))
            dirs.extend(_environ_path("LD_RUN_PATH"))

        if hasattr(sys, "frozen") and getattr(sys, "frozen") == "macosx_app":
            dirs.append(os.path.join(os.environ["RESOURCEPATH"], "..", "Frameworks"))

        dirs.extend(dyld_fallback_library_path)

        return dirs


# Posix


class PosixLibraryLoader(LibraryLoader):
    """Library loader for POSIX-like systems (including Linux)"""

    _ld_so_cache = None

    _include = re.compile(r"^\s*include\s+(?P<pattern>.*)")

    name_formats = ["lib%s.so", "%s.so", "%s"]

    class _Directories(dict):
        """Deal with directories"""

        def __init__(self):
            dict.__init__(self)
            self.order = 0

        def add(self, directory):
            """Add a directory to our current set of directories"""
            if len(directory) > 1:
                directory = directory.rstrip(os.path.sep)
            # only adds and updates order if exists and not already in set
            if not os.path.exists(directory):
                return
            order = self.setdefault(directory, self.order)
            if order == self.order:
                self.order += 1

        def extend(self, directories):
            """Add a list of directories to our set"""
            for a_dir in directories:
                self.add(a_dir)

        def ordered(self):
            """Sort the list of directories"""
            return (i[0] for i in sorted(self.items(), key=lambda d: d[1]))

    def _get_ld_so_conf_dirs(self, conf, dirs):
        """
        Recursive function to help parse all ld.so.conf files, including proper
        handling of the `include` directive.
        """

        try:
            with open(conf) as fileobj:
                for dirname in fileobj:
                    dirname = dirname.strip()
                    if not dirname:
                        continue

                    match = self._include.match(dirname)
                    if not match:
                        dirs.add(dirname)
                    else:
                        for dir2 in glob.glob(match.group("pattern")):
                            self._get_ld_so_conf_dirs(dir2, dirs)
        except IOError:
            pass

    def _create_ld_so_cache(self):
        # Recreate search path followed by ld.so.  This is going to be
        # slow to build, and incorrect (ld.so uses ld.so.cache, which may
        # not be up-to-date).  Used only as fallback for distros without
        # /sbin/ldconfig.
        #
        # We assume the DT_RPATH and DT_RUNPATH binary sections are omitted.

        directories = self._Directories()
        for name in (
            "LD_LIBRARY_PATH",
            "SHLIB_PATH",  # HP-UX
            "LIBPATH",  # OS/2, AIX
            "LIBRARY_PATH",  # BE/OS
        ):
            if name in os.environ:
                directories.extend(os.environ[name].split(os.pathsep))

        self._get_ld_so_conf_dirs("/etc/ld.so.conf", directories)

        bitage = platform.architecture()[0]

        unix_lib_dirs_list = []
        if bitage.startswith("64"):
            # prefer 64 bit if that is our arch
            unix_lib_dirs_list += ["/lib64", "/usr/lib64"]

        # must include standard libs, since those paths are also used by 64 bit
        # installs
        unix_lib_dirs_list += ["/lib", "/usr/lib"]
        if sys.platform.startswith("linux"):
            # Try and support multiarch work in Ubuntu
            # https://wiki.ubuntu.com/MultiarchSpec
            if bitage.startswith("32"):
                # Assume Intel/AMD x86 compat
                unix_lib_dirs_list += ["/lib/i386-linux-gnu", "/usr/lib/i386-linux-gnu"]
            elif bitage.startswith("64"):
                # Assume Intel/AMD x86 compatible
                unix_lib_dirs_list += [
                    "/lib/x86_64-linux-gnu",
                    "/usr/lib/x86_64-linux-gnu",
                ]
            else:
                # guess...
                unix_lib_dirs_list += glob.glob("/lib/*linux-gnu")
        directories.extend(unix_lib_dirs_list)

        cache = {}
        lib_re = re.compile(r"lib(.*)\.s[ol]")
        # ext_re = re.compile(r"\.s[ol]$")
        for our_dir in directories.ordered():
            try:
                for path in glob.glob("%s/*.s[ol]*" % our_dir):
                    file = os.path.basename(path)

                    # Index by filename
                    cache_i = cache.setdefault(file, set())
                    cache_i.add(path)

                    # Index by library name
                    match = lib_re.match(file)
                    if match:
                        library = match.group(1)
                        cache_i = cache.setdefault(library, set())
                        cache_i.add(path)
            except OSError:
                pass

        self._ld_so_cache = cache

    def getplatformpaths(self, libname):
        if self._ld_so_cache is None:
            self._create_ld_so_cache()

        result = self._ld_so_cache.get(libname, set())
        for i in result:
            # we iterate through all found paths for library, since we may have
            # actually found multiple architectures or other library types that
            # may not load
            yield i


# Windows


class WindowsLibraryLoader(LibraryLoader):
    """Library loader for Microsoft Windows"""

    name_formats = ["%s.dll", "lib%s.dll", "%slib.dll", "%s"]

    class Lookup(LibraryLoader.Lookup):
        """Lookup class for Windows libraries..."""

        def __init__(self, path):
            super(WindowsLibraryLoader.Lookup, self).__init__(path)
            self.access["stdcall"] = ctypes.windll.LoadLibrary(path)


# Platform switching

# If your value of sys.platform does not appear in this dict, please contact
# the Ctypesgen maintainers.

loaderclass = {
    "darwin": DarwinLibraryLoader,
    "cygwin": WindowsLibraryLoader,
    "win32": WindowsLibraryLoader,
    "msys": WindowsLibraryLoader,
}

load_library = loaderclass.get(sys.platform, PosixLibraryLoader)()


def add_library_search_dirs(other_dirs):
    """
    Add libraries to search paths.
    If library paths are relative, convert them to absolute with respect to this
    file's directory
    """
    for path in other_dirs:
        if not os.path.isabs(path):
            path = os.path.abspath(path)
        load_library.other_dirs.append(path)


del loaderclass

# End loader

add_library_search_dirs([])

# No libraries

# No modules

__uint8_t = c_ubyte# /usr/include/x86_64-linux-gnu/bits/types.h: 38

__uint16_t = c_ushort# /usr/include/x86_64-linux-gnu/bits/types.h: 40

__uint32_t = c_uint# /usr/include/x86_64-linux-gnu/bits/types.h: 42

__uint64_t = c_ulong# /usr/include/x86_64-linux-gnu/bits/types.h: 45

uint8_t = __uint8_t# /usr/include/x86_64-linux-gnu/bits/stdint-uintn.h: 24

uint16_t = __uint16_t# /usr/include/x86_64-linux-gnu/bits/stdint-uintn.h: 25

uint32_t = __uint32_t# /usr/include/x86_64-linux-gnu/bits/stdint-uintn.h: 26

uint64_t = __uint64_t# /usr/include/x86_64-linux-gnu/bits/stdint-uintn.h: 27

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/spectrometer_interface.h: 49
class struct_ADC_stat(Structure):
    pass

struct_ADC_stat._pack_ = 1
struct_ADC_stat.__slots__ = [
    'min',
    'max',
    'valid_count',
    'invalid_count_max',
    'invalid_count_min',
    'sumv',
    'sumv2',
]
struct_ADC_stat._fields_ = [
    ('min', c_int16),
    ('max', c_int16),
    ('valid_count', uint32_t),
    ('invalid_count_max', uint32_t),
    ('invalid_count_min', uint32_t),
    ('sumv', uint64_t),
    ('sumv2', uint64_t),
]

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 181
class struct_core_state(Structure):
    pass

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/calibrator.h: 50
class struct_calibrator_state(Structure):
    pass

struct_calibrator_state._pack_ = 1
struct_calibrator_state.__slots__ = [
    'mode',
    'Navg2',
    'Navg3',
    'drift_guard',
    'drift_step',
    'antenna_mask',
    'notch_index',
    'SNRon',
    'SNRoff',
    'SNR_minratio',
    'Nsettle',
    'delta_drift_corA',
    'delta_drift_corB',
    'ddrift_guard',
    'gphase_guard',
    'pfb_index',
    'weight_ndx',
    'auto_slice',
    'powertop_slice',
    'delta_powerbot_slice',
    'sum1_slice',
    'sum2_slice',
    'fd_slice',
    'sd2_slice',
    'prod1_slice',
    'prod2_slice',
    'errors',
    'bitslicer_errors',
    'zoom_ch1',
    'zoom_ch2',
    'zoom_diff_1',
    'zoom_diff_2',
    'zoom_ch1_minus',
    'zoom_ch2_minus',
    'zoom_Navg',
    'zoom_avg_idx',
    'zoom_ndx_range',
    'zoom_ndx_current',
    'raw11_every',
    'raw11_counter',
    'settle_count',
]
struct_calibrator_state._fields_ = [
    ('mode', uint8_t),
    ('Navg2', uint8_t),
    ('Navg3', uint8_t),
    ('drift_guard', uint16_t),
    ('drift_step', uint16_t),
    ('antenna_mask', uint8_t),
    ('notch_index', uint8_t),
    ('SNRon', uint32_t),
    ('SNRoff', uint32_t),
    ('SNR_minratio', uint16_t),
    ('Nsettle', uint32_t),
    ('delta_drift_corA', uint32_t),
    ('delta_drift_corB', uint32_t),
    ('ddrift_guard', uint32_t),
    ('gphase_guard', uint32_t),
    ('pfb_index', uint16_t),
    ('weight_ndx', uint16_t),
    ('auto_slice', uint8_t),
    ('powertop_slice', uint8_t),
    ('delta_powerbot_slice', uint8_t),
    ('sum1_slice', uint8_t),
    ('sum2_slice', uint8_t),
    ('fd_slice', uint8_t),
    ('sd2_slice', uint8_t),
    ('prod1_slice', uint8_t),
    ('prod2_slice', uint8_t),
    ('errors', uint32_t),
    ('bitslicer_errors', uint32_t),
    ('zoom_ch1', uint8_t),
    ('zoom_ch2', uint8_t),
    ('zoom_diff_1', c_bool),
    ('zoom_diff_2', c_bool),
    ('zoom_ch1_minus', uint8_t),
    ('zoom_ch2_minus', uint8_t),
    ('zoom_Navg', c_int32),
    ('zoom_avg_idx', c_int32),
    ('zoom_ndx_range', c_int16),
    ('zoom_ndx_current', c_int16),
    ('raw11_every', uint8_t),
    ('raw11_counter', uint8_t),
    ('settle_count', uint8_t),
]

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/calibrator.h: 81
class struct_calibrator_stats(Structure):
    pass

struct_calibrator_stats._pack_ = 1
struct_calibrator_stats.__slots__ = [
    'SNR_max',
    'SNR_min',
    'ptop_max',
    'ptop_min',
    'pbot_max',
    'pbot_min',
    'FD_max',
    'FD_min',
    'SD_max',
    'SD_min',
    'SD_positive_count',
    'lock_count',
]
struct_calibrator_stats._fields_ = [
    ('SNR_max', uint32_t * int(4)),
    ('SNR_min', uint32_t * int(4)),
    ('ptop_max', uint32_t * int(4)),
    ('ptop_min', uint32_t * int(4)),
    ('pbot_max', uint32_t * int(4)),
    ('pbot_min', uint32_t * int(4)),
    ('FD_max', c_int32 * int(4)),
    ('FD_min', c_int32 * int(4)),
    ('SD_max', c_int32 * int(4)),
    ('SD_min', c_int32 * int(4)),
    ('SD_positive_count', uint16_t * int(4)),
    ('lock_count', c_int32),
]

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/calibrator.h: 91
class struct_calibrator_error_reg(Structure):
    pass

struct_calibrator_error_reg._pack_ = 1
struct_calibrator_error_reg.__slots__ = [
    'cal_phaser_err',
    'averager_err',
    'process_err',
    'stage3_err',
    'check',
]
struct_calibrator_error_reg._fields_ = [
    ('cal_phaser_err', uint32_t * int(2)),
    ('averager_err', uint32_t * int(16)),
    ('process_err', uint32_t * int(8)),
    ('stage3_err', uint32_t * int(4)),
    ('check', uint32_t),
]

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/calibrator.h: 100
class struct_calibrator_metadata(Structure):
    pass

struct_calibrator_metadata._pack_ = 1
struct_calibrator_metadata.__slots__ = [
    'version',
    'unique_packet_id',
    'time_32',
    'time_16',
    'have_lock',
    'SNRon',
    'SNRoff',
    'mode',
    'powertop_slice',
    'sum1_slice',
    'sum2_slice',
    'fd_slice',
    'sd2_slice',
    'prod1_slice',
    'prod2_slice',
    'errors',
    'bitslicer_errors',
    'stats',
    'error_reg',
    'drift',
    'drift_shift',
]
struct_calibrator_metadata._fields_ = [
    ('version', uint16_t),
    ('unique_packet_id', uint32_t),
    ('time_32', uint32_t),
    ('time_16', uint16_t),
    ('have_lock', uint16_t * int(4)),
    ('SNRon', uint32_t),
    ('SNRoff', uint32_t),
    ('mode', uint8_t),
    ('powertop_slice', uint8_t),
    ('sum1_slice', uint8_t),
    ('sum2_slice', uint8_t),
    ('fd_slice', uint8_t),
    ('sd2_slice', uint8_t),
    ('prod1_slice', uint8_t),
    ('prod2_slice', uint8_t),
    ('errors', uint32_t),
    ('bitslicer_errors', uint32_t),
    ('stats', struct_calibrator_stats),
    ('error_reg', struct_calibrator_error_reg),
    ('drift', c_int16 * int(128)),
    ('drift_shift', uint8_t),
]

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/calibrator.h: 120
class struct_saved_calibrator_weights(Structure):
    pass

struct_saved_calibrator_weights._pack_ = 1
struct_saved_calibrator_weights.__slots__ = [
    'in_use',
    'CRC',
    'weights',
]
struct_saved_calibrator_weights._fields_ = [
    ('in_use', uint32_t),
    ('CRC', uint32_t),
    ('weights', uint16_t * int(512)),
]

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/calibrator.h: 129
for _lib in _libs.values():
    if not _lib.has("set_calibrator", "cdecl"):
        continue
    set_calibrator = _lib.get("set_calibrator", "cdecl")
    set_calibrator.argtypes = [POINTER(struct_calibrator_state)]
    set_calibrator.restype = None
    break

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/calibrator.h: 130
for _lib in _libs.values():
    if not _lib.has("calibrator_set_SNR", "cdecl"):
        continue
    calibrator_set_SNR = _lib.get("calibrator_set_SNR", "cdecl")
    calibrator_set_SNR.argtypes = [POINTER(struct_calibrator_state)]
    calibrator_set_SNR.restype = None
    break

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/calibrator.h: 131
for _lib in _libs.values():
    if not _lib.has("calibrator_slice_init", "cdecl"):
        continue
    calibrator_slice_init = _lib.get("calibrator_slice_init", "cdecl")
    calibrator_slice_init.argtypes = [POINTER(struct_calibrator_state)]
    calibrator_slice_init.restype = None
    break

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/calibrator.h: 132
for _lib in _libs.values():
    if not _lib.has("calibrator_set_slices", "cdecl"):
        continue
    calibrator_set_slices = _lib.get("calibrator_set_slices", "cdecl")
    calibrator_set_slices.argtypes = [POINTER(struct_calibrator_state)]
    calibrator_set_slices.restype = None
    break

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/calibrator.h: 133
for _lib in _libs.values():
    if not _lib.has("process_cal_zoom", "cdecl"):
        continue
    process_cal_zoom = _lib.get("process_cal_zoom", "cdecl")
    process_cal_zoom.argtypes = [POINTER(struct_core_state)]
    process_cal_zoom.restype = None
    break

enum_flash_copy_status = c_int# /home/anze/Dropbox/work/lusee/coreloop/coreloop/flash_interface.h: 7

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/flash_interface.h: 14
class struct_flash_copy_report_t(Structure):
    pass

struct_flash_copy_report_t._pack_ = 1
struct_flash_copy_report_t.__slots__ = [
    'region_1',
    'region_2',
    'size_1',
    'size_2',
    'checksum_1_meta',
    'checksum_1_data',
    'checksum_2_meta',
    'checksum_2_data',
    'status',
]
struct_flash_copy_report_t._fields_ = [
    ('region_1', c_int),
    ('region_2', c_int),
    ('size_1', uint32_t),
    ('size_2', uint32_t),
    ('checksum_1_meta', uint32_t),
    ('checksum_1_data', uint32_t),
    ('checksum_2_meta', uint32_t),
    ('checksum_2_data', uint32_t),
    ('status', enum_flash_copy_status),
]

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 53
for _lib in _libs.values():
    try:
        tap_counter = (uint64_t).in_dll(_lib, "tap_counter")
        break
    except:
        pass

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 55
for _lib in _libs.values():
    try:
        TVS_sensors_avg = (uint32_t * int(4)).in_dll(_lib, "TVS_sensors_avg")
        break
    except:
        pass

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 57
for _lib in _libs.values():
    try:
        loop_count_min_latch = (uint16_t).in_dll(_lib, "loop_count_min_latch")
        break
    except:
        pass

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 57
for _lib in _libs.values():
    try:
        loop_count_max_latch = (uint16_t).in_dll(_lib, "loop_count_max_latch")
        break
    except:
        pass

enum_gain_state = c_int# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 61

GAIN_LOW = 0# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 61

GAIN_MED = (GAIN_LOW + 1)# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 61

GAIN_HIGH = (GAIN_MED + 1)# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 61

GAIN_DISABLE = (GAIN_HIGH + 1)# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 61

GAIN_AUTO = (GAIN_DISABLE + 1)# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 61

enum_output_format = c_int# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 68

OUTPUT_32BIT = 0# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 68

OUTPUT_16BIT_UPDATES = (OUTPUT_32BIT + 1)# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 68

OUTPUT_16BIT_FLOAT1 = (OUTPUT_16BIT_UPDATES + 1)# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 68

OUTPUT_16BIT_10_PLUS_6 = (OUTPUT_16BIT_FLOAT1 + 1)# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 68

OUTPUT_16BIT_4_TO_5 = (OUTPUT_16BIT_10_PLUS_6 + 1)# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 68

OUTPUT_16BIT_SHARED_LZ = (OUTPUT_16BIT_4_TO_5 + 1)# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 68

enum_averaging_mode = c_int# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 77

AVG_INT32 = 0# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 77

AVG_INT_40_BITS = (AVG_INT32 + 1)# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 77

AVG_FLOAT = (AVG_INT_40_BITS + 1)# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 77

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 84
class struct_route_state(Structure):
    pass

struct_route_state._pack_ = 1
struct_route_state.__slots__ = [
    'plus',
    'minus',
]
struct_route_state._fields_ = [
    ('plus', uint8_t),
    ('minus', uint8_t),
]

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 88
class struct_time_counters(Structure):
    pass

struct_time_counters._pack_ = 1
struct_time_counters.__slots__ = [
    'heartbeat_counter',
    'resettle_counter',
    'cdi_wait_counter',
    'cdi_dispatch_counter',
]
struct_time_counters._fields_ = [
    ('heartbeat_counter', uint64_t),
    ('resettle_counter', uint64_t),
    ('cdi_wait_counter', uint64_t),
    ('cdi_dispatch_counter', uint64_t),
]

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 98
class struct_core_state_base(Structure):
    pass

struct_core_state_base._pack_ = 1
struct_core_state_base.__slots__ = [
    'uC_time',
    'time_32',
    'time_16',
    'TVS_sensors',
    'loop_count_min',
    'loop_count_max',
    'gain',
    'gain_auto_min',
    'gain_auto_mult',
    'route',
    'Navg1_shift',
    'Navg2_shift',
    'notch',
    'Navgf',
    'hi_frac',
    'med_frac',
    'bitslice',
    'bitslice_keep_bits',
    'format',
    'reject_ratio',
    'reject_maxbad',
    'tr_start',
    'tr_stop',
    'tr_avg_shift',
    'grimm_enable',
    'averaging_mode',
    'errors',
    'corr_products_mask',
    'actual_gain',
    'actual_bitslice',
    'spec_overflow',
    'notch_overflow',
    'ADC_stat',
    'spectrometer_enable',
    'calibrator_enable',
    'rand_state',
    'weight',
    'weight_current',
    'num_bad_min_current',
    'num_bad_max_current',
    'num_bad_min',
    'num_bad_max',
]
struct_core_state_base._fields_ = [
    ('uC_time', uint64_t),
    ('time_32', uint32_t),
    ('time_16', uint16_t),
    ('TVS_sensors', uint16_t * int(4)),
    ('loop_count_min', uint16_t),
    ('loop_count_max', uint16_t),
    ('gain', uint8_t * int(4)),
    ('gain_auto_min', uint16_t * int(4)),
    ('gain_auto_mult', uint16_t * int(4)),
    ('route', struct_route_state * int(4)),
    ('Navg1_shift', uint8_t),
    ('Navg2_shift', uint8_t),
    ('notch', uint8_t),
    ('Navgf', uint8_t),
    ('hi_frac', uint8_t),
    ('med_frac', uint8_t),
    ('bitslice', uint8_t * int(16)),
    ('bitslice_keep_bits', uint8_t),
    ('format', uint8_t),
    ('reject_ratio', uint8_t),
    ('reject_maxbad', uint8_t),
    ('tr_start', uint16_t),
    ('tr_stop', uint16_t),
    ('tr_avg_shift', uint16_t),
    ('grimm_enable', uint8_t),
    ('averaging_mode', uint8_t),
    ('errors', uint32_t),
    ('corr_products_mask', uint16_t),
    ('actual_gain', uint8_t * int(4)),
    ('actual_bitslice', uint8_t * int(16)),
    ('spec_overflow', uint16_t),
    ('notch_overflow', uint16_t),
    ('ADC_stat', struct_ADC_stat * int(4)),
    ('spectrometer_enable', c_bool),
    ('calibrator_enable', c_bool),
    ('rand_state', uint32_t),
    ('weight', uint16_t),
    ('weight_current', uint16_t),
    ('num_bad_min_current', uint16_t),
    ('num_bad_max_current', uint16_t),
    ('num_bad_min', uint16_t),
    ('num_bad_max', uint16_t),
]

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 141
class struct_cdi_stats(Structure):
    pass

struct_cdi_stats._pack_ = 1
struct_cdi_stats.__slots__ = [
    'cdi_total_command_count',
    'cdi_packets_sent',
    'cdi_bytes_sent',
]
struct_cdi_stats._fields_ = [
    ('cdi_total_command_count', uint32_t),
    ('cdi_packets_sent', uint32_t),
    ('cdi_bytes_sent', uint64_t),
]

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 147
class struct_delayed_cdi_sending(Structure):
    pass

struct_delayed_cdi_sending._pack_ = 1
struct_delayed_cdi_sending.__slots__ = [
    'appId',
    'tr_appId',
    'int_counter',
    'format',
    'prod_count',
    'tr_count',
    'grimm_count',
    'cal_count',
    'Nfreq',
    'Navgf',
    'packet_id',
    'cal_packet_id',
    'cal_appId',
    'cal_size',
    'cal_packet_size',
]
struct_delayed_cdi_sending._fields_ = [
    ('appId', uint32_t),
    ('tr_appId', uint32_t),
    ('int_counter', uint16_t),
    ('format', uint8_t),
    ('prod_count', uint8_t),
    ('tr_count', uint8_t),
    ('grimm_count', uint8_t),
    ('cal_count', uint8_t),
    ('Nfreq', uint16_t),
    ('Navgf', uint16_t),
    ('packet_id', uint32_t),
    ('cal_packet_id', uint32_t),
    ('cal_appId', uint32_t),
    ('cal_size', uint32_t),
    ('cal_packet_size', uint32_t),
]

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 165
class struct_watchdog_state(Structure):
    pass

struct_watchdog_state._pack_ = 1
struct_watchdog_state.__slots__ = [
    'FPGA_max_temp',
    'watchdogs_enabled',
    'feed_uc',
    'tripped_mask',
]
struct_watchdog_state._fields_ = [
    ('FPGA_max_temp', uint8_t),
    ('watchdogs_enabled', uint8_t),
    ('feed_uc', c_bool),
    ('tripped_mask', uint8_t),
]

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 174
class struct_watchdog_packet(Structure):
    pass

struct_watchdog_packet._pack_ = 1
struct_watchdog_packet.__slots__ = [
    'unique_packet_id',
    'uC_time',
    'tripped',
]
struct_watchdog_packet._fields_ = [
    ('unique_packet_id', uint16_t),
    ('uC_time', uint64_t),
    ('tripped', uint8_t),
]

struct_core_state._pack_ = 1
struct_core_state.__slots__ = [
    'base',
    'cdi_stats',
    'cal',
    'cdi_dispatch',
    'timing',
    'watchdog',
    'clear_buffers',
    'soft_reset_flag',
    'cdi_wait_spectra',
    'avg_counter',
    'unique_packet_id',
    'leading_zeros_min',
    'leading_zeros_max',
    'housekeeping_request',
    'range_adc',
    'resettle',
    'request_waveform',
    'request_eos',
    'tick_tock',
    'drop_df',
    'heartbeat_packet_count',
    'flash_slot',
    'cmd_arg_high',
    'cmd_arg_low',
    'cmd_ptr',
    'cmd_end',
    'sequence_upload',
    'loop_depth',
    'loop_start',
    'loop_count',
    'cmd_counter',
    'dispatch_delay',
    'reg_address',
    'reg_value',
    'bitslicer_action_counter',
    'fft_time',
    'grimm_weights',
    'grimm_weight_ndx',
    'fft_computed',
    'region_have_lock',
]
struct_core_state._fields_ = [
    ('base', struct_core_state_base),
    ('cdi_stats', struct_cdi_stats),
    ('cal', struct_calibrator_state),
    ('cdi_dispatch', struct_delayed_cdi_sending),
    ('timing', struct_time_counters),
    ('watchdog', struct_watchdog_state),
    ('clear_buffers', c_bool),
    ('soft_reset_flag', c_bool),
    ('cdi_wait_spectra', uint16_t),
    ('avg_counter', uint16_t),
    ('unique_packet_id', uint32_t),
    ('leading_zeros_min', uint8_t * int(4)),
    ('leading_zeros_max', uint8_t * int(4)),
    ('housekeeping_request', uint8_t),
    ('range_adc', uint8_t),
    ('resettle', uint8_t),
    ('request_waveform', uint8_t),
    ('request_eos', uint8_t),
    ('tick_tock', c_bool),
    ('drop_df', c_bool),
    ('heartbeat_packet_count', uint32_t),
    ('flash_slot', c_int8),
    ('cmd_arg_high', uint8_t * int(1024)),
    ('cmd_arg_low', uint8_t * int(1024)),
    ('cmd_ptr', uint16_t),
    ('cmd_end', uint16_t),
    ('sequence_upload', c_bool),
    ('loop_depth', uint8_t),
    ('loop_start', uint16_t * int(4)),
    ('loop_count', uint8_t * int(4)),
    ('cmd_counter', uint32_t),
    ('dispatch_delay', uint16_t),
    ('reg_address', uint16_t),
    ('reg_value', c_int32),
    ('bitslicer_action_counter', c_int8),
    ('fft_time', uint32_t),
    ('grimm_weights', uint32_t * int((4 * 8))),
    ('grimm_weight_ndx', uint8_t),
    ('fft_computed', c_bool),
    ('region_have_lock', c_bool),
]

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 223
class struct_saved_state(Structure):
    pass

struct_saved_state._pack_ = 1
struct_saved_state.__slots__ = [
    'in_use',
    'cmd_arg_high',
    'cmd_arg_low',
    'cmd_ptr',
    'cmd_end',
    'CRC',
]
struct_saved_state._fields_ = [
    ('in_use', uint32_t),
    ('cmd_arg_high', uint8_t * int(1024)),
    ('cmd_arg_low', uint8_t * int(1024)),
    ('cmd_ptr', uint16_t),
    ('cmd_end', uint16_t),
    ('CRC', uint32_t),
]

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 230
class struct_state_recover_notification(Structure):
    pass

struct_state_recover_notification._pack_ = 1
struct_state_recover_notification.__slots__ = [
    'slot',
    'size',
]
struct_state_recover_notification._fields_ = [
    ('slot', uint32_t),
    ('size', uint32_t),
]

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 235
class struct_end_of_sequence(Structure):
    pass

struct_end_of_sequence._pack_ = 1
struct_end_of_sequence.__slots__ = [
    'unique_packet_id',
    'eos_arg',
]
struct_end_of_sequence._fields_ = [
    ('unique_packet_id', uint32_t),
    ('eos_arg', uint32_t),
]

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 240
class struct_startup_hello(Structure):
    pass

struct_startup_hello._pack_ = 1
struct_startup_hello.__slots__ = [
    'SW_version',
    'FW_Version',
    'FW_ID',
    'FW_Date',
    'FW_Time',
    'unique_packet_id',
    'time_32',
    'time_16',
]
struct_startup_hello._fields_ = [
    ('SW_version', uint32_t),
    ('FW_Version', uint32_t),
    ('FW_ID', uint32_t),
    ('FW_Date', uint32_t),
    ('FW_Time', uint32_t),
    ('unique_packet_id', uint32_t),
    ('time_32', uint32_t),
    ('time_16', uint16_t),
]

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 251
class struct_heartbeat(Structure):
    pass

struct_heartbeat._pack_ = 1
struct_heartbeat.__slots__ = [
    'packet_count',
    'time_32',
    'time_16',
    'TVS_sensors',
    'cdi_stats',
    'errors',
    'magic',
]
struct_heartbeat._fields_ = [
    ('packet_count', uint32_t),
    ('time_32', uint32_t),
    ('time_16', uint16_t),
    ('TVS_sensors', uint16_t * int(4)),
    ('cdi_stats', struct_cdi_stats),
    ('errors', uint32_t),
    ('magic', c_char * int(6)),
]

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 261
class struct_waveform_metadata(Structure):
    pass

struct_waveform_metadata._pack_ = 1
struct_waveform_metadata.__slots__ = [
    'unique_packet_id',
    'time_32',
    'time_16',
    'timestamp',
]
struct_waveform_metadata._fields_ = [
    ('unique_packet_id', uint32_t),
    ('time_32', uint32_t),
    ('time_16', uint16_t),
    ('timestamp', uint64_t),
]

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 269
class struct_meta_data(Structure):
    pass

struct_meta_data._pack_ = 1
struct_meta_data.__slots__ = [
    'version',
    'unique_packet_id',
    'base',
]
struct_meta_data._fields_ = [
    ('version', uint16_t),
    ('unique_packet_id', uint32_t),
    ('base', struct_core_state_base),
]

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 275
class struct_housekeeping_data_base(Structure):
    pass

struct_housekeeping_data_base._pack_ = 1
struct_housekeeping_data_base.__slots__ = [
    'version',
    'unique_packet_id',
    'errors',
    'housekeeping_type',
]
struct_housekeeping_data_base._fields_ = [
    ('version', uint16_t),
    ('unique_packet_id', uint32_t),
    ('errors', uint32_t),
    ('housekeeping_type', uint16_t),
]

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 283
class struct_housekeeping_data_0(Structure):
    pass

struct_housekeeping_data_0._pack_ = 1
struct_housekeeping_data_0.__slots__ = [
    'base',
    'core_state',
]
struct_housekeeping_data_0._fields_ = [
    ('base', struct_housekeeping_data_base),
    ('core_state', struct_core_state),
]

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 289
class struct_housekeeping_data_1(Structure):
    pass

struct_housekeeping_data_1._pack_ = 1
struct_housekeeping_data_1.__slots__ = [
    'base',
    'ADC_stat',
    'actual_gain',
]
struct_housekeeping_data_1._fields_ = [
    ('base', struct_housekeeping_data_base),
    ('ADC_stat', struct_ADC_stat * int(4)),
    ('actual_gain', uint8_t * int(4)),
]

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 296
class struct_housekeeping_data_2(Structure):
    pass

struct_housekeeping_data_2._pack_ = 1
struct_housekeeping_data_2.__slots__ = [
    'base',
    'heartbeat',
]
struct_housekeeping_data_2._fields_ = [
    ('base', struct_housekeeping_data_base),
    ('heartbeat', struct_heartbeat),
]

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 303
class struct_housekeeping_data_3(Structure):
    pass

struct_housekeeping_data_3._pack_ = 1
struct_housekeeping_data_3.__slots__ = [
    'base',
    'checksum',
    'weight_ndx',
]
struct_housekeeping_data_3._fields_ = [
    ('base', struct_housekeeping_data_base),
    ('checksum', uint32_t),
    ('weight_ndx', uint16_t),
]

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 309
class struct_housekeeping_data_100(Structure):
    pass

struct_housekeeping_data_100._pack_ = 1
struct_housekeeping_data_100.__slots__ = [
    'base',
    'meta_valid',
    'size',
    'checksum_meta',
    'checksum_data',
]
struct_housekeeping_data_100._fields_ = [
    ('base', struct_housekeeping_data_base),
    ('meta_valid', uint8_t * int(6)),
    ('size', uint32_t * int(6)),
    ('checksum_meta', uint32_t * int(6)),
    ('checksum_data', uint32_t * int(6)),
]

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 318
class struct_housekeeping_data_101(Structure):
    pass

struct_housekeeping_data_101._pack_ = 1
struct_housekeeping_data_101.__slots__ = [
    'base',
    'report',
]
struct_housekeeping_data_101._fields_ = [
    ('base', struct_housekeeping_data_base),
    ('report', struct_flash_copy_report_t),
]

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 325
for _lib in _libs.values():
    if not _lib.has("core_loop", "cdecl"):
        continue
    core_loop = _lib.get("core_loop", "cdecl")
    core_loop.argtypes = [POINTER(struct_core_state)]
    core_loop.restype = None
    break

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 328
for _lib in _libs.values():
    if not _lib.has("process_cdi", "cdecl"):
        continue
    process_cdi = _lib.get("process_cdi", "cdecl")
    process_cdi.argtypes = [POINTER(struct_core_state)]
    process_cdi.restype = c_bool
    break

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 332
for _lib in _libs.values():
    if not _lib.has("process_watchdogs", "cdecl"):
        continue
    process_watchdogs = _lib.get("process_watchdogs", "cdecl")
    process_watchdogs.argtypes = [POINTER(struct_core_state)]
    process_watchdogs.restype = c_bool
    break

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 333
for _lib in _libs.values():
    if not _lib.has("cmd_soft_reset", "cdecl"):
        continue
    cmd_soft_reset = _lib.get("cmd_soft_reset", "cdecl")
    cmd_soft_reset.argtypes = [uint8_t, POINTER(struct_core_state)]
    cmd_soft_reset.restype = None
    break

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 336
for _lib in _libs.values():
    if not _lib.has("RFS_stop", "cdecl"):
        continue
    RFS_stop = _lib.get("RFS_stop", "cdecl")
    RFS_stop.argtypes = [POINTER(struct_core_state)]
    RFS_stop.restype = None
    break

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 337
for _lib in _libs.values():
    if not _lib.has("RFS_start", "cdecl"):
        continue
    RFS_start = _lib.get("RFS_start", "cdecl")
    RFS_start.argtypes = [POINTER(struct_core_state)]
    RFS_start.restype = None
    break

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 338
for _lib in _libs.values():
    if not _lib.has("restart_spectrometer", "cdecl"):
        continue
    restart_spectrometer = _lib.get("restart_spectrometer", "cdecl")
    restart_spectrometer.argtypes = [POINTER(struct_core_state)]
    restart_spectrometer.restype = None
    break

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 341
for _lib in _libs.values():
    if not _lib.has("get_Navg1", "cdecl"):
        continue
    get_Navg1 = _lib.get("get_Navg1", "cdecl")
    get_Navg1.argtypes = [POINTER(struct_core_state)]
    get_Navg1.restype = uint16_t
    break

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 342
for _lib in _libs.values():
    if not _lib.has("get_Navg2", "cdecl"):
        continue
    get_Navg2 = _lib.get("get_Navg2", "cdecl")
    get_Navg2.argtypes = [POINTER(struct_core_state)]
    get_Navg2.restype = uint16_t
    break

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 343
for _lib in _libs.values():
    if not _lib.has("get_Nfreq", "cdecl"):
        continue
    get_Nfreq = _lib.get("get_Nfreq", "cdecl")
    get_Nfreq.argtypes = [POINTER(struct_core_state)]
    get_Nfreq.restype = uint16_t
    break

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 344
for _lib in _libs.values():
    if not _lib.has("get_tr_avg", "cdecl"):
        continue
    get_tr_avg = _lib.get("get_tr_avg", "cdecl")
    get_tr_avg.argtypes = [POINTER(struct_core_state)]
    get_tr_avg.restype = uint16_t
    break

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 345
for _lib in _libs.values():
    if not _lib.has("get_gain_auto_max", "cdecl"):
        continue
    get_gain_auto_max = _lib.get("get_gain_auto_max", "cdecl")
    get_gain_auto_max.argtypes = [POINTER(struct_core_state), c_int]
    get_gain_auto_max.restype = uint16_t
    break

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 346
for _lib in _libs.values():
    if not _lib.has("get_tr_length", "cdecl"):
        continue
    get_tr_length = _lib.get("get_tr_length", "cdecl")
    get_tr_length.argtypes = [POINTER(struct_core_state)]
    get_tr_length.restype = uint32_t
    break

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 350
for _lib in _libs.values():
    if not _lib.has("set_route", "cdecl"):
        continue
    set_route = _lib.get("set_route", "cdecl")
    set_route.argtypes = [POINTER(struct_core_state), uint8_t, uint8_t]
    set_route.restype = None
    break

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 353
for _lib in _libs.values():
    if not _lib.has("update_spec_gains", "cdecl"):
        continue
    update_spec_gains = _lib.get("update_spec_gains", "cdecl")
    update_spec_gains.argtypes = [POINTER(struct_core_state)]
    update_spec_gains.restype = None
    break

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 356
for _lib in _libs.values():
    if not _lib.has("trigger_ADC_stat", "cdecl"):
        continue
    trigger_ADC_stat = _lib.get("trigger_ADC_stat", "cdecl")
    trigger_ADC_stat.argtypes = []
    trigger_ADC_stat.restype = None
    break

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 359
for _lib in _libs.values():
    if not _lib.has("reset_errormasks", "cdecl"):
        continue
    reset_errormasks = _lib.get("reset_errormasks", "cdecl")
    reset_errormasks.argtypes = [POINTER(struct_core_state)]
    reset_errormasks.restype = None
    break

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 362
for _lib in _libs.values():
    if not _lib.has("update_time", "cdecl"):
        continue
    update_time = _lib.get("update_time", "cdecl")
    update_time.argtypes = [POINTER(struct_core_state)]
    update_time.restype = None
    break

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 365
for _lib in _libs.values():
    if not _lib.has("process_spectrometer", "cdecl"):
        continue
    process_spectrometer = _lib.get("process_spectrometer", "cdecl")
    process_spectrometer.argtypes = [POINTER(struct_core_state)]
    process_spectrometer.restype = None
    break

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 368
for _lib in _libs.values():
    if not _lib.has("transfer_to_cdi", "cdecl"):
        continue
    transfer_to_cdi = _lib.get("transfer_to_cdi", "cdecl")
    transfer_to_cdi.argtypes = [POINTER(struct_core_state)]
    transfer_to_cdi.restype = None
    break

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 370
for _lib in _libs.values():
    if not _lib.has("process_delayed_cdi_dispatch", "cdecl"):
        continue
    process_delayed_cdi_dispatch = _lib.get("process_delayed_cdi_dispatch", "cdecl")
    process_delayed_cdi_dispatch.argtypes = [POINTER(struct_core_state)]
    process_delayed_cdi_dispatch.restype = c_bool
    break

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 373
for _lib in _libs.values():
    if not _lib.has("process_gain_range", "cdecl"):
        continue
    process_gain_range = _lib.get("process_gain_range", "cdecl")
    process_gain_range.argtypes = [POINTER(struct_core_state)]
    process_gain_range.restype = None
    break

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 374
for _lib in _libs.values():
    if not _lib.has("bitslice_control", "cdecl"):
        continue
    bitslice_control = _lib.get("bitslice_control", "cdecl")
    bitslice_control.argtypes = [POINTER(struct_core_state)]
    bitslice_control.restype = c_bool
    break

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 377
for _lib in _libs.values():
    if not _lib.has("set_spectrometer", "cdecl"):
        continue
    set_spectrometer = _lib.get("set_spectrometer", "cdecl")
    set_spectrometer.argtypes = [POINTER(struct_core_state)]
    set_spectrometer.restype = None
    break

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 378
for _lib in _libs.values():
    if not _lib.has("default_state", "cdecl"):
        continue
    default_state = _lib.get("default_state", "cdecl")
    default_state.argtypes = [POINTER(struct_core_state_base)]
    default_state.restype = None
    break

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 381
for _lib in _libs.values():
    if not _lib.has("debug_helper", "cdecl"):
        continue
    debug_helper = _lib.get("debug_helper", "cdecl")
    debug_helper.argtypes = [uint8_t, POINTER(struct_core_state)]
    debug_helper.restype = None
    break

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 382
for _lib in _libs.values():
    if not _lib.has("cdi_not_implemented", "cdecl"):
        continue
    cdi_not_implemented = _lib.get("cdi_not_implemented", "cdecl")
    cdi_not_implemented.argtypes = [String]
    cdi_not_implemented.restype = None
    break

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 386
for _lib in _libs.values():
    if not _lib.has("send_hello_packet", "cdecl"):
        continue
    send_hello_packet = _lib.get("send_hello_packet", "cdecl")
    send_hello_packet.argtypes = [POINTER(struct_core_state)]
    send_hello_packet.restype = None
    break

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 387
for _lib in _libs.values():
    if not _lib.has("process_hearbeat", "cdecl"):
        continue
    process_hearbeat = _lib.get("process_hearbeat", "cdecl")
    process_hearbeat.argtypes = [POINTER(struct_core_state)]
    process_hearbeat.restype = c_bool
    break

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 388
for _lib in _libs.values():
    if not _lib.has("process_housekeeping", "cdecl"):
        continue
    process_housekeeping = _lib.get("process_housekeeping", "cdecl")
    process_housekeeping.argtypes = [POINTER(struct_core_state)]
    process_housekeeping.restype = c_bool
    break

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 391
for _lib in _libs.values():
    if not _lib.has("process_eos", "cdecl"):
        continue
    process_eos = _lib.get("process_eos", "cdecl")
    process_eos.argtypes = [POINTER(struct_core_state)]
    process_eos.restype = c_bool
    break

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 394
for _lib in _libs.values():
    if not _lib.has("cdi_dispatch_uC", "cdecl"):
        continue
    cdi_dispatch_uC = _lib.get("cdi_dispatch_uC", "cdecl")
    cdi_dispatch_uC.argtypes = [POINTER(struct_cdi_stats), uint16_t, uint32_t]
    cdi_dispatch_uC.restype = None
    break

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 397
for _lib in _libs.values():
    if not _lib.has("delayed_cdi_dispatch_done", "cdecl"):
        continue
    delayed_cdi_dispatch_done = _lib.get("delayed_cdi_dispatch_done", "cdecl")
    delayed_cdi_dispatch_done.argtypes = [POINTER(struct_core_state)]
    delayed_cdi_dispatch_done.restype = c_bool
    break

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 400
for _lib in _libs.values():
    if not _lib.has("calibrator_default_state", "cdecl"):
        continue
    calibrator_default_state = _lib.get("calibrator_default_state", "cdecl")
    calibrator_default_state.argtypes = [POINTER(struct_calibrator_state)]
    calibrator_default_state.restype = None
    break

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 401
for _lib in _libs.values():
    if not _lib.has("calib_set_mode", "cdecl"):
        continue
    calib_set_mode = _lib.get("calib_set_mode", "cdecl")
    calib_set_mode.argtypes = [POINTER(struct_core_state), uint8_t]
    calib_set_mode.restype = None
    break

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 402
for _lib in _libs.values():
    if not _lib.has("process_calibrator", "cdecl"):
        continue
    process_calibrator = _lib.get("process_calibrator", "cdecl")
    process_calibrator.argtypes = [POINTER(struct_core_state)]
    process_calibrator.restype = None
    break

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 403
for _lib in _libs.values():
    if not _lib.has("dispatch_calibrator_data", "cdecl"):
        continue
    dispatch_calibrator_data = _lib.get("dispatch_calibrator_data", "cdecl")
    dispatch_calibrator_data.argtypes = [POINTER(struct_core_state)]
    dispatch_calibrator_data.restype = None
    break

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 411
for _lib in _libs.values():
    if not _lib.has("flash_send_region_info", "cdecl"):
        continue
    flash_send_region_info = _lib.get("flash_send_region_info", "cdecl")
    flash_send_region_info.argtypes = [POINTER(struct_core_state)]
    flash_send_region_info.restype = None
    break

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 412
for _lib in _libs.values():
    if not _lib.has("flash_copy_region_cmd", "cdecl"):
        continue
    flash_copy_region_cmd = _lib.get("flash_copy_region_cmd", "cdecl")
    flash_copy_region_cmd.argtypes = [POINTER(struct_core_state), c_int, c_int]
    flash_copy_region_cmd.restype = None
    break

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 413
for _lib in _libs.values():
    if not _lib.has("flash_region_enable", "cdecl"):
        continue
    flash_region_enable = _lib.get("flash_region_enable", "cdecl")
    flash_region_enable.argtypes = [c_int, c_bool]
    flash_region_enable.restype = None
    break

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 419
for _lib in _libs.values():
    if not _lib.has("mini_wait", "cdecl"):
        continue
    mini_wait = _lib.get("mini_wait", "cdecl")
    mini_wait.argtypes = [uint32_t]
    mini_wait.restype = None
    break

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 423
for _lib in _libs.values():
    if not _lib.has("timer_start", "cdecl"):
        continue
    timer_start = _lib.get("timer_start", "cdecl")
    timer_start.argtypes = []
    timer_start.restype = None
    break

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 426
for _lib in _libs.values():
    if not _lib.has("timer_stop", "cdecl"):
        continue
    timer_stop = _lib.get("timer_stop", "cdecl")
    timer_stop.argtypes = []
    timer_stop.restype = uint32_t
    break

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 430
for _lib in _libs.values():
    if not _lib.has("encode_12plus4", "cdecl"):
        continue
    encode_12plus4 = _lib.get("encode_12plus4", "cdecl")
    encode_12plus4.argtypes = [c_int32]
    encode_12plus4.restype = uint16_t
    break

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 431
for _lib in _libs.values():
    if not _lib.has("decode_12plus4", "cdecl"):
        continue
    decode_12plus4 = _lib.get("decode_12plus4", "cdecl")
    decode_12plus4.argtypes = [uint16_t]
    decode_12plus4.restype = c_int32
    break

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 434
for _lib in _libs.values():
    if not _lib.has("encode_10plus6", "cdecl"):
        continue
    encode_10plus6 = _lib.get("encode_10plus6", "cdecl")
    encode_10plus6.argtypes = [c_int32]
    encode_10plus6.restype = uint16_t
    break

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 435
for _lib in _libs.values():
    if not _lib.has("decode_10plus6", "cdecl"):
        continue
    decode_10plus6 = _lib.get("decode_10plus6", "cdecl")
    decode_10plus6.argtypes = [uint16_t]
    decode_10plus6.restype = c_int32
    break

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 441
for _lib in _libs.values():
    if not _lib.has("encode_shared_lz_positive", "cdecl"):
        continue
    encode_shared_lz_positive = _lib.get("encode_shared_lz_positive", "cdecl")
    encode_shared_lz_positive.argtypes = [POINTER(uint32_t), POINTER(c_ubyte), c_int]
    encode_shared_lz_positive.restype = c_int
    break

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 442
for _lib in _libs.values():
    if not _lib.has("decode_shared_lz_positive", "cdecl"):
        continue
    decode_shared_lz_positive = _lib.get("decode_shared_lz_positive", "cdecl")
    decode_shared_lz_positive.argtypes = [POINTER(c_ubyte), POINTER(uint32_t), c_int]
    decode_shared_lz_positive.restype = None
    break

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 448
for _lib in _libs.values():
    if not _lib.has("encode_shared_lz_signed", "cdecl"):
        continue
    encode_shared_lz_signed = _lib.get("encode_shared_lz_signed", "cdecl")
    encode_shared_lz_signed.argtypes = [POINTER(c_int32), POINTER(c_ubyte), c_int]
    encode_shared_lz_signed.restype = c_int
    break

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 449
for _lib in _libs.values():
    if not _lib.has("decode_shared_lz_signed", "cdecl"):
        continue
    decode_shared_lz_signed = _lib.get("decode_shared_lz_signed", "cdecl")
    decode_shared_lz_signed.argtypes = [POINTER(c_ubyte), POINTER(c_int32), c_int]
    decode_shared_lz_signed.restype = None
    break

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 452
for _lib in _libs.values():
    if not _lib.has("encode_4_into_5", "cdecl"):
        continue
    encode_4_into_5 = _lib.get("encode_4_into_5", "cdecl")
    encode_4_into_5.argtypes = [POINTER(c_int32), POINTER(uint16_t)]
    encode_4_into_5.restype = None
    break

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 453
for _lib in _libs.values():
    if not _lib.has("decode_5_into_4", "cdecl"):
        continue
    decode_5_into_4 = _lib.get("decode_5_into_4", "cdecl")
    decode_5_into_4.argtypes = [POINTER(uint16_t), POINTER(c_int32)]
    decode_5_into_4.restype = None
    break

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 456
for _lib in _libs.values():
    if not _lib.has("rle_encode", "cdecl"):
        continue
    rle_encode = _lib.get("rle_encode", "cdecl")
    rle_encode.argtypes = [POINTER(None), POINTER(None), c_size_t]
    rle_encode.restype = c_size_t
    break

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 459
for _lib in _libs.values():
    if not _lib.has("CRC", "cdecl"):
        continue
    CRC = _lib.get("CRC", "cdecl")
    CRC.argtypes = [POINTER(None), c_size_t]
    CRC.restype = uint32_t
    break

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 462
for _lib in _libs.values():
    if not _lib.has("fft_precompute_tables", "cdecl"):
        continue
    fft_precompute_tables = _lib.get("fft_precompute_tables", "cdecl")
    fft_precompute_tables.argtypes = []
    fft_precompute_tables.restype = None
    break

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 463
for _lib in _libs.values():
    if not _lib.has("fft", "cdecl"):
        continue
    fft = _lib.get("fft", "cdecl")
    fft.argtypes = [POINTER(uint32_t), POINTER(uint32_t)]
    fft.restype = None
    break

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 467
for _lib in _libs.values():
    if not _lib.has("get_free_stack", "cdecl"):
        continue
    get_free_stack = _lib.get("get_free_stack", "cdecl")
    get_free_stack.argtypes = []
    get_free_stack.restype = c_size_t
    break

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 7
try:
    VERSION_ID = 0x307
except:
    pass

# /usr/lib/gcc/x86_64-linux-gnu/13/include/stdbool.h: 37
try:
    true = 1
except:
    pass

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/calibrator.h: 14
try:
    CAL_MODE_RAW0 = 0b00
except:
    pass

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/calibrator.h: 16
try:
    CAL_MODE_RAW1 = 0b01
except:
    pass

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/calibrator.h: 18
try:
    CAL_MODE_RAW2 = 0b10
except:
    pass

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/calibrator.h: 20
try:
    CAL_MODE_RAW3 = 0b11
except:
    pass

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/calibrator.h: 24
try:
    CAL_MODE_BIT_SLICER_SETTLE = 0x10
except:
    pass

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/calibrator.h: 26
try:
    CAL_MODE_SNR_SETTLE = 0x20
except:
    pass

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/calibrator.h: 28
try:
    CAL_MODE_RUN = 0x30
except:
    pass

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/calibrator.h: 30
try:
    CAL_MODE_BLIND = 0x40
except:
    pass

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/calibrator.h: 32
try:
    CAL_MODE_ZOOM = 0x50
except:
    pass

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/calibrator.h: 36
try:
    AUTO_SLICE_SETTLE = 0b0001
except:
    pass

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/calibrator.h: 37
try:
    AUTO_SLICE_SNR = 0b0010
except:
    pass

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/calibrator.h: 38
try:
    AUTO_SLICE_RUN = 0b0100
except:
    pass

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/calibrator.h: 39
try:
    AUTO_SLICE_PROD = 0b1000
except:
    pass

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/calibrator.h: 41
try:
    USE_FLOAT_FFT = true
except:
    pass

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/calibrator.h: 43
try:
    NPFB = 2048
except:
    pass

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/calibrator.h: 44
try:
    MAX_SETTLE_COUNT = 6
except:
    pass

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 19
try:
    DISPATCH_DELAY = 6
except:
    pass

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 20
try:
    RESETTLE_DELAY = 5
except:
    pass

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 21
try:
    HEARTBEAT_DELAY = 1024
except:
    pass

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 22
try:
    CMD_BUFFER_SIZE = 1024
except:
    pass

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 23
try:
    MAX_LOOPS = 4
except:
    pass

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 24
try:
    ADC_STAT_SAMPLES = 16000
except:
    pass

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 25
try:
    MAX_STATE_SLOTS = 16
except:
    pass

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 26
try:
    BITSLICER_MAX_ACTION = 5
except:
    pass

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 28
try:
    TVS_AVG = 128
except:
    pass

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 29
try:
    TVS_AVG_VSHIFT = 6
except:
    pass

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 30
try:
    TVS_AVG_TSHIFT = 4
except:
    pass

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 32
try:
    LOOP_COUNT_RST = 1024
except:
    pass

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 34
try:
    GRIMM_BINS = 4
except:
    pass

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 35
try:
    NGRIMM_WEIGHTS = (GRIMM_BINS * 8)
except:
    pass

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 38
try:
    GRIMM_NDX0 = 574
except:
    pass

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 39
try:
    GRIMM_NDX1 = 835
except:
    pass

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 40
try:
    GRIMM_NDX2 = 1182
except:
    pass

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 41
try:
    GRIMM_NDX3 = 1672
except:
    pass

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 46
try:
    HK_REQUEST_STATE = 0
except:
    pass

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 47
try:
    HK_REQUEST_ADC = 1
except:
    pass

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 48
try:
    HK_REQUEST_HEALTH = 2
except:
    pass

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 49
try:
    HK_REQUEST_CAL_WEIGHT_CHECKSUM = 3
except:
    pass

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 416
def MAX(x, y):
    return (x > y) and x or y

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 417
def MIN(x, y):
    return (x < y) and x or y

# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 418
def IS_NEG(x):
    return (x < 0) and 1 or 0

core_state = struct_core_state# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 181

calibrator_state = struct_calibrator_state# /home/anze/Dropbox/work/lusee/coreloop/coreloop/calibrator.h: 50

calibrator_stats = struct_calibrator_stats# /home/anze/Dropbox/work/lusee/coreloop/coreloop/calibrator.h: 81

calibrator_error_reg = struct_calibrator_error_reg# /home/anze/Dropbox/work/lusee/coreloop/coreloop/calibrator.h: 91

calibrator_metadata = struct_calibrator_metadata# /home/anze/Dropbox/work/lusee/coreloop/coreloop/calibrator.h: 100

saved_calibrator_weights = struct_saved_calibrator_weights# /home/anze/Dropbox/work/lusee/coreloop/coreloop/calibrator.h: 120

route_state = struct_route_state# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 84

time_counters = struct_time_counters# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 88

core_state_base = struct_core_state_base# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 98

cdi_stats = struct_cdi_stats# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 141

delayed_cdi_sending = struct_delayed_cdi_sending# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 147

watchdog_state = struct_watchdog_state# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 165

watchdog_packet = struct_watchdog_packet# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 174

saved_state = struct_saved_state# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 223

state_recover_notification = struct_state_recover_notification# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 230

end_of_sequence = struct_end_of_sequence# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 235

startup_hello = struct_startup_hello# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 240

heartbeat = struct_heartbeat# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 251

waveform_metadata = struct_waveform_metadata# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 261

meta_data = struct_meta_data# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 269

housekeeping_data_base = struct_housekeeping_data_base# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 275

housekeeping_data_0 = struct_housekeeping_data_0# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 283

housekeeping_data_1 = struct_housekeeping_data_1# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 289

housekeeping_data_2 = struct_housekeeping_data_2# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 296

housekeeping_data_3 = struct_housekeeping_data_3# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 303

housekeeping_data_100 = struct_housekeeping_data_100# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 309

housekeeping_data_101 = struct_housekeeping_data_101# /home/anze/Dropbox/work/lusee/coreloop/coreloop/core_loop.h: 318

# No inserted files

# No prefix-stripping

