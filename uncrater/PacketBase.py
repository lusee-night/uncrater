import os, sys
import ctypes

import hexdump
from .coreloop import pycoreloop,pycoreloop_203,pycoreloop_305,pycoreloop_307
from .decode_status import DecodeStatus, PacketDecodeError, source_label
from .schema_registry import SchemaConflictError, resolve_wire_version
pystruct = pycoreloop.pystruct
pystruct_203 = pycoreloop_203.pystruct
pystruct_305 = pycoreloop_305.pystruct
pystruct_307 = pycoreloop_307.pystruct


def cdi_rounded_size(size):
    """Include the four-byte CDI padding omitted from ctypes struct sizes."""
    return (size + 3) & ~3


# Resolve constructor inputs while preserving an explicitly selected binding
def _resolve_packet_schema(*, version, schema, reported_version,
                           schema_variant, evidence, diagnostic_override):
    if (reported_version is not None and version is not None
            and reported_version != version):
        raise SchemaConflictError("version and reported_version disagree")
    if reported_version is None:
        reported_version = version

    if schema is None:
        resolution = resolve_wire_version(
            reported_version,
            variant=schema_variant,
            evidence=evidence,
            diagnostic_override=diagnostic_override,
        )
        return resolution.binding, reported_version, resolution.schema_assumed

    has_evidence = evidence is not None or schema_variant is not None
    needs_resolution = (
        has_evidence
        or (
            reported_version is not None
            and reported_version not in schema.accepted_reported_versions
        )
    )
    if not needs_resolution:
        return schema, reported_version, reported_version is None

    resolution = resolve_wire_version(
        reported_version,
        variant=schema_variant,
        evidence=evidence,
        diagnostic_override=diagnostic_override,
    )
    if resolution.binding is not schema:
        if has_evidence:
            raise SchemaConflictError(
                f"Packet evidence selects {resolution.binding.binding_key}, "
                f"not {schema.binding_key}"
            )
        raise SchemaConflictError(
            f"Reported version 0x{reported_version:X} does not match "
            f"binding {schema.binding_key}"
        )
    return schema, reported_version, resolution.schema_assumed


class PacketBase:
    def __init__ (self, appid, blob = None, blob_fn = None, version=None,
                  schema=None, reported_version=None, schema_variant=None,
                  evidence=None, diagnostic_override=False, strict=True,
                  original_appid=None, **kwargs):
        if (blob is None) and (blob_fn is None):
            raise ValueError
        self.appid = appid
        self.original_appid = appid if original_appid is None else original_appid
        self._blob = blob
        self._blob_fn = blob_fn
        self.strict = strict
        self.decode_status = DecodeStatus()
        self._diagnostic_override = diagnostic_override

        schema, reported_version, resolved_schema_assumed = _resolve_packet_schema(
            version=version,
            schema=schema,
            reported_version=reported_version,
            schema_variant=schema_variant,
            evidence=evidence,
            diagnostic_override=diagnostic_override,
        )

        # Keep the on-wire report separate from the frozen decoder selected for it
        self.schema = schema
        self.schema_id = schema.canonical_schema_id
        self.reported_version = reported_version
        self.binding_provenance = schema.binding_provenance
        self._version = reported_version
        self._is_read = False
        for key, value in kwargs.items():
            setattr(self, key, value)
        self.schema_assumed = resolved_schema_assumed
        if self.schema_assumed and reported_version is not None:
            self._issue(
                "unknown_schema",
                f"reported schema 0x{reported_version:X} decoded with "
                f"diagnostic binding {schema.binding_key}",
                details={"selected_binding": schema.binding_key},
            )
        if blob is not None:
            self._read()
        

        
    @property
    def blob(self):
        self._load_blob()
        return self._blob

    @property
    def is_read(self):
        return self._is_read

    @property
    def error_crc_mismatch(self):
        return self.decode_status.has("crc_mismatch")

    @property
    def error_packed_id_mismatch(self):
        return self.decode_status.has("unique_packet_id_mismatch")

    @property
    def packed_id_mismatch(self):
        return self.error_packed_id_mismatch

    @property
    def error_data_read(self):
        return self.decode_status.has("payload_decode_failed")

    def _context(self):
        return {
            "appid": self.appid,
            "source": source_label(self._blob_fn),
        }

    def _issue(self, code, message, *, fatal=False, details=None):
        # Parsers call this for findings that should stay attached to the packet;
        # unlike _fail, recording an issue never stops decoding by itself.
        return self.decode_status.add(
            code,
            message,
            fatal=fatal,
            details=details,
            **self._context(),
        )

    def _fail(self, code, message, *, details=None):
        # Structural validators call this when publishing decoded fields is unsafe.
        # Strict mode raises; diagnostic mode records the failure and returns.
        issue = self._issue(code, message, fatal=True, details=details)
        self._is_read = True
        if self.strict:
            raise PacketDecodeError(issue, self.decode_status)

    def _load_blob(self):
        if self._blob is None:
            with open(self._blob_fn, "rb") as source:
                self._blob = source.read()

    def _read(self):
        if self._is_read:
            return
        self._load_blob()
        self._is_read = True

    def read(self):
        self._read()

    def _accepted_lengths(self, raw_size, *, allow_cdi_padding=True):
        accepted = {raw_size}
        if allow_cdi_padding:
            accepted.add(cdi_rounded_size(raw_size))
        return tuple(sorted(accepted))

    def _validate_length(self, raw_size, *, allow_cdi_padding=True):
        self._load_blob()
        accepted = self._accepted_lengths(raw_size,
                                          allow_cdi_padding=allow_cdi_padding)
        if len(self._blob) in accepted:
            return True
        self._fail(
            "bad_blob_length",
            f"expected payload length in {accepted}, got {len(self._blob)}",
            details={"actual": len(self._blob), "expected": list(accepted)},
        )
        return False

    def _validate_min_length(self, minimum):
        self._load_blob()
        if len(self._blob) >= minimum:
            return True
        self._fail(
            "bad_blob_length",
            f"expected at least {minimum} bytes, got {len(self._blob)}",
            details={"actual": len(self._blob), "minimum": minimum},
        )
        return False

    def _decode_prefix_struct(self, struct_type):
        raw_size = ctypes.sizeof(struct_type)
        if not self._validate_min_length(raw_size):
            return None
        return struct_type.from_buffer_copy(self._blob[:raw_size])

    def _decode_struct(self, struct_type):
        raw_size = ctypes.sizeof(struct_type)
        if not self._validate_length(raw_size):
            return None
        return struct_type.from_buffer_copy(self._blob[:raw_size])

    def _check_declared_version(self, declared_version):
        if declared_version in self.schema.accepted_reported_versions:
            return True
        if (self._diagnostic_override and self.schema_assumed
                and declared_version == self.reported_version):
            return True
        self._fail(
            "declared_version_mismatch",
            f"payload declares 0x{declared_version:X}, selected binding is "
            f"{self.schema.binding_key}",
            details={
                "declared_version": declared_version,
                "selected_binding": self.schema.binding_key,
            },
        )
        return False

    def _analyze_attr(self, attr_name: str, obj: object, full_attr_name: str) -> None:
        attr = getattr(obj, attr_name)
        full_attr_name += f'{attr_name}.'
        if isinstance(attr, object) and type(attr).__module__ != 'builtins':
            self._analyze_hk(attr, full_attr_name)
        else:
            self.attr_dict[full_attr_name.strip('.')].append(attr)

    def _analyze_hk(self, obj: object, full_attr_name='') -> None:
        # slotted classes generated in core_loop.py
        print (obj,full_attr_name)
        if hasattr(obj, '__slots__'):
            for slot in obj.__slots__:
                if slot[0] == '_':
                    continue
                self._analyze_attr(slot, obj, full_attr_name)
        # top level Packet class
        elif obj.__class__.__module__ != 'builtins':
            for attr_name in vars(obj):
                if attr_name[0] == '_':
                    continue
                self._analyze_attr(attr_name, obj, full_attr_name)


    def keys(self):
        def it_keys(d):
            l = []
            klist = getattr(d,"__slots__") if hasattr(d,"__slots__") else dir(d)
            for k in klist:
                if k[0]=='_':
                    continue        
                a = getattr(d,k)
                if not hasattr(a, "__slots__"):
                    if not (callable(a)):
                        l.append(k)
                else:
                    for sk in it_keys(a):
                        l.append(k+'.'+sk)
            return l 
        return it_keys(self)
    
    def __getitem__(self,name):
        def get_dotted(obj,name):
            if '.' in name:
                i = name.find('.')
                first,second = name[:i], name[i+1:]
                if hasattr(obj,first):
                    return get_dotted(getattr(obj,first),second)
                else:
                    return None
            else:
                return getattr(obj,name)
        return get_dotted(self,name)

    def xxd(self):
        """ xxd style dump of the contents"""
        self._read()
        return hexdump.hexdump(self.blob,result='return')

    @property
    def desc(self):
        return  "generic"


    def info(self):
        """ ASCII readable description.
        To be specialized
        """
        return self.xxd()

    def copy_attrs (self,src):
        for attr in dir(src): 
            if attr[0] == '_':
                continue
            setattr(self, attr, getattr(src, attr))


class Packet_Unsupported(PacketBase):
    @property
    def desc(self):
        return "Unsupported packet"

    def _read(self):
        if self._is_read:
            return
        self._fail(
            "unsupported_format",
            f"decoding for AppID 0x{self.appid:03X} is not implemented",
        )
