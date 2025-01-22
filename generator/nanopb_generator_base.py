#!/usr/bin/env python3
# kate: replace-tabs on; indent-width 4;

from __future__ import unicode_literals
from fnmatch import fnmatchcase
from optparse import OptionParser, OptionValueError
import importlib.util
import os.path
import time
from functools import reduce
import os
import itertools
import copy
import codecs
import re
import sys

'''Generate header file for nanopb from a ProtoBuf FileDescriptorSet.'''
nanopb_version = "nanopb-1.0.0-dev"


# Python-protobuf breaks easily with protoc version differences if
# using the cpp or upb implementation. Force it to use pure Python
# implementation. Performance is not very important in the generator.
if not os.getenv("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"):
    os.putenv("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")
    os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"

try:
    import google.protobuf.text_format as text_format
    import google.protobuf.descriptor_pb2 as descriptor
    import google.protobuf.compiler.plugin_pb2 as plugin_pb2
    import google.protobuf.descriptor
    import google.protobuf.message_factory as message_factory
except:
    sys.stderr.write('''
         **********************************************************************
         *** Could not import the Google protobuf Python libraries          ***
         ***                                                                ***
         *** Easiest solution is often to install the dependencies via pip: ***
         ***    pip install protobuf grpcio-tools                           ***
         **********************************************************************
    ''' + '\n')
    raise

# GetMessageClass() is used by modern python-protobuf (around 5.x onwards)
# Retain compatibility with older python-protobuf versions.
try:
    import google.protobuf.message_factory as message_factory
    GetMessageClass = message_factory.GetMessageClass
except AttributeError:
    import google.protobuf.reflection as reflection
    GetMessageClass = reflection.MakeClass

# Depending on how this script is run, we may or may not have PEP366 package name
# available for relative imports.
if not __package__:
    import proto
    from proto._utils import invoke_protoc
    from proto import TemporaryDirectory
else:
    from . import proto
    from .proto._utils import invoke_protoc
    from .proto import TemporaryDirectory

if getattr(sys, 'frozen', False):
    # Binary package, just import the file
    from proto import nanopb_pb2
else:
    # Import nanopb_pb2.py, rebuilds if necessary and not disabled
    # by env variable NANOPB_PB2_NO_REBUILD
    nanopb_pb2 = proto.load_nanopb_pb2()

# ---------------------------------------------------------------------------
#                     Generation of single fields
# ---------------------------------------------------------------------------


# Values are tuple (c type, pb type, encoded size, data_size)
FieldD = descriptor.FieldDescriptorProto
basetypes = {
    "int8":     ('int8_t',     'INT32',      1),
    "uint8":    ('uint8_t',    'INT32',      1),
    "int16":    ('int16_t',    'INT32',      2),
    "uint16":   ('uint16_t',   'INT32',      2),
    "bool":     ('bool',       'BOOL',       1),
    "double":   ('double',     'DOUBLE',     8),
    "float":    ('float',      'FLOAT',      4),
    "int32_t":  ('int32_t',    'INT32',      4),
    "int64_t":  ('int64_t',    'INT64',      8),
    "uint32_t": ('uint32_t',   'UINT32',     4),
    "uint64_t": ('uint64_t',   'UINT64',     8),
}

datatypes = {
    FieldD.TYPE_BOOL:       ('bool',     'BOOL',       1),
    FieldD.TYPE_DOUBLE:     ('double',   'DOUBLE',     8),
    FieldD.TYPE_FIXED32:    ('uint32_t', 'FIXED32',    4),
    FieldD.TYPE_FIXED64:    ('uint64_t', 'FIXED64',    8),
    FieldD.TYPE_FLOAT:      ('float',    'FLOAT',      4),
    FieldD.TYPE_INT32:      ('int32_t',  'INT32',      4),
    FieldD.TYPE_INT64:      ('int64_t',  'INT64',      8),
    FieldD.TYPE_SFIXED32:   ('int32_t',  'SFIXED32',   4),
    FieldD.TYPE_SFIXED64:   ('int64_t',  'SFIXED64',   8),
    FieldD.TYPE_SINT32:     ('int32_t',  'SINT32',     4),
    FieldD.TYPE_SINT64:     ('int64_t',  'SINT64',     8),
    FieldD.TYPE_UINT32:     ('uint32_t', 'UINT32',     4),
    FieldD.TYPE_UINT64:     ('uint64_t', 'UINT64',     8),
}


class NamingStyle:
    def enum_name(self, name):
        return "_%s" % (name)

    def struct_name(self, name):
        return "_%s" % (name)

    def union_name(self, name):
        return "_%s" % (name)

    def type_name(self, name):
        return "%s" % (name)

    def define_name(self, name):
        return "%s" % (name)

    def var_name(self, name):
        return "%s" % (name)

    def enum_entry(self, name):
        return "%s" % (name)

    def func_name(self, name):
        return "%s" % (name)

    def bytes_type(self, struct_name, name):
        return "%s_%s_t" % (struct_name, name)


class NamingStyleC(NamingStyle):
    def enum_name(self, name):
        return self.underscore(name)

    def struct_name(self, name):
        return self.underscore(name)

    def union_name(self, name):
        return self.underscore(name)

    def type_name(self, name):
        return "%s_t" % self.underscore(name)

    def define_name(self, name):
        return self.underscore(name).upper()

    def var_name(self, name):
        return self.underscore(name)

    def enum_entry(self, name):
        return self.underscore(name).upper()

    def func_name(self, name):
        return self.underscore(name)

    def bytes_type(self, struct_name, name):
        return "%s_%s_t" % (self.underscore(struct_name), self.underscore(name))

    def underscore(self, word):
        word = str(word)
        word = re.sub(r"([A-Z]+)([A-Z][a-z])", r'\1_\2', word)
        word = re.sub(r"([a-z\d])([A-Z])", r'\1_\2', word)
        word = word.replace("-", "_")
        return word.lower()


class Globals:
    '''Ugly global variables, should find a good way to pass these.'''
    verbose_options = False
    separate_options = []
    matched_namemasks = set()
    protoc_insertion_points = False
    naming_style = NamingStyle()


class Names:
    '''Keeps a set of nested names and formats them to C identifier.'''

    def __init__(self, parts=()):
        if isinstance(parts, Names):
            parts = parts.parts
        elif isinstance(parts, str):
            parts = (parts,)
        self.parts = tuple(parts)

        if self.parts == ('',):
            self.parts = ()

    def __str__(self):
        return '_'.join(self.parts)

    def __repr__(self):
        return 'Names(%s)' % ','.join("'%s'" % x for x in self.parts)

    def __add__(self, other):
        if isinstance(other, str):
            return Names(self.parts + (other,))
        elif isinstance(other, Names):
            return Names(self.parts + other.parts)
        elif isinstance(other, tuple):
            return Names(self.parts + other)
        else:
            raise ValueError("Name parts should be of type str")

    def __eq__(self, other):
        return isinstance(other, Names) and self.parts == other.parts

    def __lt__(self, other):
        if not isinstance(other, Names):
            return NotImplemented
        return str(self) < str(other)


def names_from_type_name(type_name):
    '''Parse Names() from FieldDescriptorProto type_name'''
    if type_name[0] != '.':
        raise NotImplementedError(
            "Lookup of non-absolute type names is not supported")
    return Names(type_name[1:].split('.'))


class ProtoElement(object):
    # Constants regarding path of proto elements in file descriptor.
    # They are used to connect proto elements with source code information (comments)
    # These values come from:
    # https://github.com/google/protobuf/blob/master/src/google/protobuf/descriptor.proto
    FIELD = 2
    MESSAGE = 4
    ENUM = 5
    NESTED_TYPE = 3
    NESTED_ENUM = 4

    def __init__(self, path, comments=None):
        '''
        path is a tuple containing integers (type, index, ...)
        comments is a dictionary mapping between element path & SourceCodeInfo.Location
            (contains information about source comments).
        '''
        assert (isinstance(path, tuple))
        self.element_path = path
        self.comments = comments or {}

    def get_member_comments(self, index):
        '''Get comments for a member of enum or message.'''
        return self.get_comments((ProtoElement.FIELD, index), leading_indent=True)

    def format_comment(self, comment):
        '''Put comment inside /* */ and sanitize comment contents'''
        comment = comment.strip()
        comment = comment.replace('/*', '/ *')
        comment = comment.replace('*/', '* /')
        return "/* %s */" % comment

    def get_comments(self, member_path=(), leading_indent=False):
        '''Get leading & trailing comments for a protobuf element.

        member_path is the proto path of an element or member (ex. [5 0] or [4 1 2 0])
        leading_indent is a flag that indicates if leading comments should be indented
        '''

        # Obtain SourceCodeInfo.Location object containing comment
        # information (based on the member path)
        path = self.element_path + member_path
        comment = self.comments.get(path)

        leading_comment = ""
        trailing_comment = ""

        if not comment:
            return leading_comment, trailing_comment

        if comment.leading_comments:
            leading_comment = "    " if leading_indent else ""
            leading_comment += self.format_comment(comment.leading_comments)

        if comment.trailing_comments:
            trailing_comment = self.format_comment(comment.trailing_comments)

        return leading_comment, trailing_comment


class Enum(ProtoElement):
    def __init__(self, names, desc, enum_options, element_path, comments):
        '''
        desc is EnumDescriptorProto
        index is the index of this enum element inside the file
        comments is a dictionary mapping between element path & SourceCodeInfo.Location
            (contains information about source comments)
        '''
        super(Enum, self).__init__(element_path, comments)

        self.options = enum_options
        self.names = names

        # by definition, `names` include this enum's name
        base_name = Names(names.parts[:-1])

        self.values = [(base_name + x.name, x.number) for x in desc.value]

        self.value_longnames = [self.names + x.name for x in desc.value]

    def has_negative(self):
        for n, v in self.values:
            if v < 0:
                return True
        return False

    def __repr__(self):
        return 'Enum(%s)' % self.names

    def __str__(self):
        return d

    def auxiliary_defines(self):
        # sort the enum by value
        sorted_values = sorted(self.values, key=lambda x: (x[1], x[0]))

        unmangledName = self.protofile.manglenames.unmangle(self.names)
        identifier = Globals.naming_style.define_name('_%s_MIN' % self.names)
        result = '#define %s %s\n' % (
            identifier,
            Globals.naming_style.enum_entry(sorted_values[0][0]))
        if unmangledName:
            unmangledIdentifier = Globals.naming_style.define_name(
                '_%s_MIN' % unmangledName)
            self.protofile.manglenames.reverse_name_mapping[identifier] = unmangledIdentifier

        identifier = Globals.naming_style.define_name('_%s_MAX' % self.names)
        result += '#define %s %s\n' % (
            identifier,
            Globals.naming_style.enum_entry(sorted_values[-1][0]))
        if unmangledName:
            unmangledIdentifier = Globals.naming_style.define_name(
                '_%s_MAX' % unmangledName)
            self.protofile.manglenames.reverse_name_mapping[identifier] = unmangledIdentifier

        identifier = Globals.naming_style.define_name(
            '_%s_ARRAYSIZE' % self.names)
        result += '#define %s ((%s)(%s+1))\n' % (
            identifier,
            Globals.naming_style.type_name(self.names),
            Globals.naming_style.enum_entry(sorted_values[-1][0]))
        if unmangledName:
            unmangledIdentifier = Globals.naming_style.define_name(
                '_%s_ARRAYSIZE' % unmangledName)
            self.protofile.manglenames.reverse_name_mapping[identifier] = unmangledIdentifier

        for i, x in enumerate(self.values):
            result += '#define %s %s\n' % (Globals.naming_style.define_name(
                self.value_longnames[i]), Globals.naming_style.enum_entry(x[0]))

        return result

    def enum_to_string_definition(self):
        if not self.options.enum_to_string:
            return ""

        result = 'const char *%s(%s v) {\n' % (
            Globals.naming_style.func_name('%s_name' % self.names),
            Globals.naming_style.type_name(self.names))

        result += '    switch (v) {\n'

        for ((enumname, _), strname) in zip(self.values, self.value_longnames):
            # Just use the last part of the string value.
            result += '        case %s: return "%s";\n' % (
                Globals.naming_style.enum_entry(enumname),
                Globals.naming_style.enum_entry(strname.parts[-1]))

        result += '    }\n'
        result += '    return "unknown";\n'
        result += '}\n'

        return result

    def enum_validate(self):
        if not self.options.enum_validate:
            return ""

        result = 'bool %s(%s v) {\n' % (
            Globals.naming_style.func_name('%s_valid' % self.names),
            Globals.naming_style.type_name(self.names))

        result += '    switch (v) {\n'

        for (enumname, _) in self.values:
            result += '        case %s: return true;\n' % (
                Globals.naming_style.enum_entry(enumname)
            )

        result += '    }\n'
        result += '    return false;\n'
        result += '}\n'

        return result


class Field(ProtoElement):
    macro_x_param = 'X'
    macro_a_param = 'a'

    def __init__(self, struct_name, desc, field_options, element_path=(), comments=None):
        '''desc is FieldDescriptorProto'''
        ProtoElement.__init__(self, element_path, comments)
        self.tag = desc.number
        self.struct_name = struct_name
        self.union_name = None
        self.name = desc.name
        self.default = None
        self.max_size = None
        self.max_count = None
        self.array_decl = ""
        self.data_item_size = 0
        self.ctype = None
        self.fixed_count = False
        self.math_include_required = False

        # Parse field options
        if field_options.HasField("max_size"):
            self.max_size = field_options.max_size

        self.initializer = None

        if desc.type == FieldD.TYPE_STRING and field_options.HasField("max_length"):
            # max_length overrides max_size for strings
            self.max_size = field_options.max_length + 1

        if desc.HasField('default_value'):
            self.default = desc.default_value

        # Check field rules, i.e. required/optional/repeated.
        if desc.label == FieldD.LABEL_REPEATED:
            self.rules = 'REPEATED'
            if self.max_count is None:
                can_be_static = False
            else:
                self.array_decl = '[%d]' % self.max_count
                if field_options.fixed_count:
                    self.rules = 'FIXARRAY'

        elif desc.label == FieldD.LABEL_REQUIRED:
            # We allow LABEL_REQUIRED using label_override even for proto3 (see #962)
            self.rules = 'REQUIRED'
        elif desc.label == FieldD.LABEL_OPTIONAL:
            self.rules = 'OPTIONAL'
        else:
            raise NotImplementedError(desc.label)

        # Check if the field can be implemented with static allocation
        # i.e. whether the data size is known.
        if desc.type == FieldD.TYPE_STRING and self.max_size is None:
            can_be_static = False

        if desc.type == FieldD.TYPE_BYTES and self.max_size is None:
            can_be_static = False

        # Decide how the field data will be allocated
        if field_options.fixed_count and self.max_count is None:
            raise Exception("Field '%s' is defined as fixed count, "
                            "but max_count is not given." % self.name)

        # Decide the C data type to use in the struct.
        if desc.type in datatypes:
            self.ctype, self.pbtype, self.data_item_size = datatypes[desc.type]
        elif desc.type == FieldD.TYPE_ENUM:
            self.pbtype = 'ENUM'
            self.data_item_size = 1
            self.ctype = names_from_type_name(desc.type_name)
            if self.default is not None:
                self.default = self.ctype + self.default
        elif desc.type == FieldD.TYPE_STRING:
            self.pbtype = 'STRING'
            self.ctype = 'char'
        elif desc.type == FieldD.TYPE_BYTES:
            if field_options.fixed_length:
                self.pbtype = 'FIXED_LENGTH_BYTES'

                if self.max_size is None:
                    raise Exception("Field '%s' is defined as fixed length, "
                                    "but max_size is not given." % self.name)

                self.ctype = 'pb_byte_t'
                self.array_decl += '[%d]' % self.max_size
            else:
                self.pbtype = 'BYTES'
                self.ctype = 'pb_bytes_array_t'
        elif desc.type == FieldD.TYPE_MESSAGE:
            self.pbtype = 'MESSAGE'
            self.ctype = self.submsgname = names_from_type_name(desc.type_name)
            
            if str(self.ctype) in basetypes:
                self.ctype, self.pbtype, self.data_item_size = basetypes[str(
                    names_from_type_name(desc.type_name))]
            elif desc.type_name in basetypes:
                self.ctype, self.pbtype, self.data_item_size = basetypes[str(
                    names_from_type_name(desc.type_name))]


        else:
            raise NotImplementedError(desc.type)

        if self.default and self.pbtype in ['FLOAT', 'DOUBLE']:
            if 'inf' in self.default or 'nan' in self.default:
                self.math_include_required = True

    def __lt__(self, other):
        return self.tag < other.tag

    def __repr__(self):
        return 'Field(%s)' % self.name

    def types(self):
        '''Return definitions for any special types this field might need.'''
        return ''

    def get_dependencies(self):
        '''Get list of type names used by this field.'''
        return [str(self.ctype)]

    def get_initializer(self, null_init, inner_init_only=False):
        '''Return literal expression for this field's default value.
        null_init: If True, initialize to a 0 value instead of default from .proto
        inner_init_only: If True, exclude initialization for any count/has fields
        '''

        inner_init = None
        if self.initializer is not None:
            inner_init = self.initializer
        elif self.pbtype in ['MESSAGE', 'MSG_W_CB']:
            if null_init:
                inner_init = Globals.naming_style.define_name(
                    '%s_init_zero' % self.ctype)
            else:
                inner_init = Globals.naming_style.define_name(
                    '%s_init_default' % self.ctype)
        elif self.default is None or null_init:
            if self.pbtype == 'STRING':
                inner_init = '""'
            elif self.pbtype == 'BYTES':
                inner_init = '{0, {0}}'
            elif self.pbtype == 'FIXED_LENGTH_BYTES':
                inner_init = '{0}'
            elif self.pbtype in ('ENUM', 'UENUM'):
                inner_init = '_%s_MIN' % Globals.naming_style.define_name(
                    self.ctype)
            else:
                inner_init = '0'
        else:
            if self.pbtype == 'STRING':
                data = codecs.escape_encode(self.default.encode('utf-8'))[0]
                inner_init = '"' + data.decode('ascii') + '"'
            elif self.pbtype == 'BYTES':
                data = codecs.escape_decode(self.default)[0]
                data = ["0x%02x" % c for c in bytearray(data)]
                if len(data) == 0:
                    inner_init = '{0, {0}}'
                else:
                    inner_init = '{%d, {%s}}' % (len(data), ','.join(data))
            elif self.pbtype == 'FIXED_LENGTH_BYTES':
                data = codecs.escape_decode(self.default)[0]
                data = ["0x%02x" % c for c in bytearray(data)]
                if len(data) == 0:
                    inner_init = '{0}'
                else:
                    inner_init = '{%s}' % ','.join(data)
            elif self.pbtype in ['FIXED32', 'UINT32']:
                inner_init = str(self.default) + 'u'
            elif self.pbtype in ['FIXED64', 'UINT64']:
                inner_init = str(self.default) + 'ull'
            elif self.pbtype in ['SFIXED64', 'INT64']:
                inner_init = str(self.default) + 'll'
            elif self.pbtype in ['FLOAT', 'DOUBLE']:
                inner_init = str(self.default)
                if 'inf' in inner_init:
                    inner_init = inner_init.replace('inf', 'INFINITY')
                elif 'nan' in inner_init:
                    inner_init = inner_init.replace('nan', 'NAN')
                elif (not '.' in inner_init) and self.pbtype == 'FLOAT':
                    inner_init += '.0f'
                elif self.pbtype == 'FLOAT':
                    inner_init += 'f'
            elif self.pbtype in ('ENUM', 'UENUM'):
                inner_init = Globals.naming_style.enum_entry(self.default)
            else:
                inner_init = str(self.default)

        if inner_init_only:
            return inner_init

        outer_init = ''

        if self.pbtype == 'MSG_W_CB' and self.rules in ['REPEATED', 'OPTIONAL']:
            outer_init = '{{NULL}, NULL}, ' + outer_init

        return outer_init

    def tags(self):
        '''Return the #define for the tag number of this field.'''
        identifier = Globals.naming_style.define_name(
            '%s_%s_tag' % (self.struct_name, self.name))
        return '#define %-40s %d\n' % (identifier, self.tag)

    def fieldlist(self):
        '''Return the FIELDLIST macro entry for this field.
        Format is: X(a, ATYPE, HTYPE, LTYPE, field_name, tag)
        '''
        name = Globals.naming_style.var_name(self.name)

        if self.rules == "ONEOF":
            # For oneofs, make a tuple of the union name, union member name,
            # and the name inside the parent struct.
            if not self.anonymous:
                name = '(%s,%s,%s)' % (
                    Globals.naming_style.var_name(self.union_name),
                    Globals.naming_style.var_name(self.name),
                    Globals.naming_style.var_name(self.union_name) + '.' +
                    Globals.naming_style.var_name(self.name))
            else:
                name = '(%s,%s,%s)' % (
                    Globals.naming_style.var_name(self.union_name),
                    Globals.naming_style.var_name(self.name),
                    Globals.naming_style.var_name(self.name))

        return '%s(%s, %-9s %-9s %-9s %-16s %3d)' % (self.macro_x_param,
                                                     self.macro_a_param,
                                                     False + ',',
                                                     self.rules + ',',
                                                     self.pbtype + ',',
                                                     name + ',',
                                                     self.tag)

    def data_size(self, dependencies):
        '''Return estimated size of this field in the C struct.
        This is used to try to automatically pick right descriptor size.
        If the estimate is wrong, it will result in compile time error and
        user having to specify descriptor_width option.
        '''
        if self.pbtype in ['MESSAGE', 'MSG_W_CB']:
            alignment = 8
            if str(self.submsgname) in dependencies:
                other_dependencies = dict(
                    x for x in dependencies.items() if x[0] != str(self.struct_name))
                size = dependencies[str(self.submsgname)].data_size(
                    other_dependencies)
            else:
                size = 256  # Message is in other file, this is reasonable guess for most cases
                sys.stderr.write('Could not determine size for submessage %s, using default %d\n' % (
                    self.submsgname, size))

            if self.pbtype == 'MSG_W_CB':
                size += 16
        elif self.pbtype in ['STRING', 'FIXED_LENGTH_BYTES']:
            size = self.max_size
            alignment = 4
        elif self.pbtype == 'BYTES':
            size = self.max_size + 4
            alignment = 4
        elif self.data_item_size is not None:
            size = self.data_item_size
            alignment = 4
            if self.data_item_size >= 8:
                alignment = 8
        else:
            raise Exception("Unhandled field type: %s" % self.pbtype)

        if self.rules not in ('REQUIRED', 'SINGULAR'):
            size += 4

        if size % alignment != 0:
            # Estimate how much alignment requirements will increase the size.
            size += alignment - (size % alignment)

        return size


class OneOf(Field):
    def __init__(self, struct_name, oneof_desc, oneof_options):
        self.struct_name = struct_name
        self.name = oneof_desc.name
        self.ctype = 'union'
        self.pbtype = 'oneof'
        self.fields = []
        self.default = None
        self.rules = 'ONEOF'
        self.anonymous = oneof_options.anonymous_oneof
        self.sort_by_tag = oneof_options.sort_by_tag
        self.has_msg_cb = False

    def add_field(self, field):
        field.union_name = self.name
        field.rules = 'ONEOF'
        field.anonymous = self.anonymous
        self.fields.append(field)

        if self.sort_by_tag:
            self.fields.sort()

        if field.pbtype == 'MSG_W_CB':
            self.has_msg_cb = True

        # Sort by the lowest tag number inside union
        self.tag = min([f.tag for f in self.fields])

    def types(self):
        return ''.join([f.types() for f in self.fields])

    def get_dependencies(self):
        deps = []
        for f in self.fields:
            deps += f.get_dependencies()
        return deps

    def tags(self):
        return ''.join([f.tags() for f in self.fields])

    def data_size(self, dependencies):
        return max(f.data_size(dependencies) for f in self.fields)

    def __str__(self):
        return result + '\n'


class Message(ProtoElement):
    def __init__(self, names, desc, message_options, element_path, comments):
        super(Message, self).__init__(element_path, comments)
        self.name = names
        self.fields = []
        self.oneofs = {}
        self.desc = desc
        self.math_include_required = False

        if message_options.msgid:
            self.msgid = message_options.msgid

        if desc is not None:
            self.load_fields(desc, message_options)

        self.data_size = 0
        for f in self.fields:
            if hasattr(f, "data_item_size"):
                self.data_size = self.data_size + f.data_item_size
        basetype_name = Globals.naming_style.type_name(self.name)
        if basetype_name not in basetypes:
            basetypes[basetype_name] = (basetype_name,     basetype_name,      self.data_size)

    def load_fields(self, desc, message_options):
        '''Load field list from DescriptorProto'''

        no_unions = []

        if hasattr(desc, 'oneof_decl'):
            for i, f in enumerate(desc.oneof_decl):
                oneof_options = get_nanopb_suboptions(
                    desc, message_options, self.name + f.name)
                if oneof_options.no_unions:
                    no_unions.append(i)  # No union, but add fields normally
                elif oneof_options.type == nanopb_pb2.FT_IGNORE:
                    pass  # No union and skip fields also
                else:
                    oneof = OneOf(self.name, f, oneof_options)
                    self.oneofs[i] = oneof
        else:
            sys.stderr.write(
                'Note: This Python protobuf library has no OneOf support\n')

        for index, f in enumerate(desc.field):
            field_options = get_nanopb_suboptions(
                f, message_options, self.name + f.name)

            field = Field(self.name, f, field_options, self.element_path +
                          (ProtoElement.FIELD, index), self.comments)
            if hasattr(f, 'oneof_index') and f.HasField('oneof_index'):
                if hasattr(f, 'proto3_optional') and f.proto3_optional:
                    no_unions.append(f.oneof_index)

                if f.oneof_index in no_unions:
                    self.fields.append(field)
                elif f.oneof_index in self.oneofs:
                    self.oneofs[f.oneof_index].add_field(field)

                    if self.oneofs[f.oneof_index] not in self.fields:
                        self.fields.append(self.oneofs[f.oneof_index])
            else:
                self.fields.append(field)

            if field.math_include_required:
                self.math_include_required = True

    def get_dependencies(self):
        '''Get list of type names that this structure refers to.'''
        deps = []
        for f in self.fields:
            deps += f.get_dependencies()
        return deps

    def __repr__(self):
        return 'Message(%s)' % self.name

    def __str__(self):
        return result + '\n'

    def types(self):
        return ''.join([f.types() for f in self.fields])

    def get_initializer(self, null_init):
        if not self.fields:
            return '{0}'

        parts = []
        for field in self.fields:
            parts.append(field.get_initializer(null_init))
        return '{' + ', '.join(parts) + '}'

    def count_required_fields(self):
        '''Returns number of required fields inside this message'''
        count = 0
        for f in self.fields:
            if not isinstance(f, OneOf):
                if f.rules == 'REQUIRED':
                    count += 1
        return count

    def all_fields(self):
        '''Iterate over all fields in this message, including nested OneOfs.'''
        for f in self.fields:
            if isinstance(f, OneOf):
                for f2 in f.fields:
                    yield f2
            else:
                yield f

    def field_for_tag(self, tag):
        '''Given a tag number, return the Field instance.'''
        for field in self.all_fields():
            if field.tag == tag:
                return field
        return None

    def count_all_fields(self):
        '''Count the total number of fields in this message.'''
        count = 0
        for f in self.fields:
            if isinstance(f, OneOf):
                count += len(f.fields)
            else:
                count += 1
        return count

    def fields_declaration(self, dependencies):
        '''Return X-macro declaration of all fields in this message.'''
        Field.macro_x_param = 'X'
        Field.macro_a_param = 'a'
        while any(field.name == Field.macro_x_param for field in self.all_fields()):
            Field.macro_x_param += '_'
        while any(field.name == Field.macro_a_param for field in self.all_fields()):
            Field.macro_a_param += '_'

        # Field descriptor array must be sorted by tag number, pb_common.c relies on it.
        sorted_fields = list(self.all_fields())
        sorted_fields.sort(key=lambda x: x.tag)

        result = '#define %s_FIELDLIST(%s, %s) \\\n' % (
            Globals.naming_style.define_name(self.name),
            Field.macro_x_param,
            Field.macro_a_param)
        result += ' \\\n'.join(x.fieldlist() for x in sorted_fields)
        result += '\n'

        defval = self.default_value(dependencies)
        if defval:
            hexcoded = ''.join("\\x%02x" % ord(
                defval[i:i+1]) for i in range(len(defval)))
            result += '#define %s_DEFAULT (const pb_byte_t*)"%s\\x00"\n' % (
                Globals.naming_style.define_name(self.name),
                hexcoded)
        else:
            result += '#define %s_DEFAULT NULL\n' % Globals.naming_style.define_name(
                self.name)

        for field in sorted_fields:
            if field.pbtype in ['MESSAGE', 'MSG_W_CB']:
                if field.rules == 'ONEOF':
                    result += "#define %s_%s_%s_MSGTYPE %s\n" % (
                        Globals.naming_style.type_name(self.name),
                        Globals.naming_style.var_name(field.union_name),
                        Globals.naming_style.var_name(field.name),
                        Globals.naming_style.type_name(field.ctype)
                    )
                else:
                    result += "#define %s_%s_MSGTYPE %s\n" % (
                        Globals.naming_style.type_name(self.name),
                        Globals.naming_style.var_name(field.name),
                        Globals.naming_style.type_name(field.ctype)
                    )

        return result

    def enumtype_defines(self):
        '''Defines to allow user code to refer to enum type of a specific field'''
        result = ''
        for field in self.all_fields():
            if field.pbtype in ['ENUM', "UENUM"]:
                if field.rules == 'ONEOF':
                    result += "#define %s_%s_%s_ENUMTYPE %s\n" % (
                        Globals.naming_style.type_name(self.name),
                        Globals.naming_style.var_name(field.union_name),
                        Globals.naming_style.var_name(field.name),
                        Globals.naming_style.type_name(field.ctype)
                    )
                else:
                    result += "#define %s_%s_ENUMTYPE %s\n" % (
                        Globals.naming_style.type_name(self.name),
                        Globals.naming_style.var_name(field.name),
                        Globals.naming_style.type_name(field.ctype)
                    )

        return result

    def fields_definition(self, dependencies):
        '''Return the field descriptor definition that goes in .pb.c file.'''
        width = self.required_descriptor_width(dependencies)
        if width == 1:
            width = 'AUTO'

        result = 'PB_BIND(%s, %s, %s)\n' % (
            Globals.naming_style.define_name(self.name),
            Globals.naming_style.type_name(self.name),
            width)
        return result

    def required_descriptor_width(self, dependencies):
        '''Estimate how many words are necessary for each field descriptor.'''
        if self.descriptorsize != nanopb_pb2.DS_AUTO:
            return int(self.descriptorsize)

        if not self.fields:
            return 1

        max_tag = max(field.tag for field in self.all_fields())
        max_offset = self.data_size(dependencies)
        max_arraysize = max((field.max_count or 0)
                            for field in self.all_fields())
        max_datasize = max(field.data_size(dependencies)
                           for field in self.all_fields())

        if max_arraysize > 0xFFFF:
            return 8
        elif (max_tag > 0x3FF or max_offset > 0xFFFF or
              max_arraysize > 0x0FFF or max_datasize > 0x0FFF):
            return 4
        elif max_tag > 0x3F or max_offset > 0xFF:
            return 2
        else:
            # NOTE: Macro logic in pb.h ensures that width 1 will
            # be raised to 2 automatically for string/submsg fields
            # and repeated fields. Thus only tag and offset need to
            # be checked.
            return 1

    def data_size(self, dependencies):
        '''Return approximate sizeof(struct) in the compiled code.'''
        return sum(f.data_size(dependencies) for f in self.fields)


# ---------------------------------------------------------------------------
#                    Processing of entire .proto files
# ---------------------------------------------------------------------------


class ProtoFile:
    def __init__(self, fdesc, file_options):
        '''Takes a FileDescriptorProto and parses it.'''
        self.fdesc = fdesc
        self.file_options = file_options
        self.dependencies = {}
        self.math_include_required = False
        self.parse()
        self.discard_unused_automatic_types()
        for message in self.messages:
            if message.math_include_required:
                self.math_include_required = True
                break

        # Some of types used in this file probably come from the file itself.
        # Thus it has implicit dependency on itself.
        self.add_dependency(self)

    def parse(self):
        self.enums = []
        self.messages = []
        self.extensions = []
        self.manglenames = MangleNames(self.fdesc, self.file_options)

        # process source code comment locations
        # ignores any locations that do not contain any comment information
        self.comment_locations = {
            tuple(location.path): location
            for location in self.fdesc.source_code_info.location
            if location.leading_comments or location.leading_detached_comments or location.trailing_comments
        }

        for index, enum in enumerate(self.fdesc.enum_type):
            name = self.manglenames.create_name(enum.name)
            enum_options = get_nanopb_suboptions(enum, self.file_options, name)
            enum_path = (ProtoElement.ENUM, index)
            self.enums.append(Enum(name, enum, enum_options,
                              enum_path, self.comment_locations))

        for names, message, comment_path in iterate_messages(self.fdesc, self.manglenames.flatten):
            name = self.manglenames.create_name(names)
            message_options = get_nanopb_suboptions(
                message, self.file_options, name)

            # Apply any configured typename mangling options
            message = copy.deepcopy(message)
            for field in message.field:
                if field.type in (FieldD.TYPE_MESSAGE, FieldD.TYPE_ENUM):
                    field.type_name = self.manglenames.mangle_field_typename(
                        field.type_name)

            # Check for circular dependencies
            msgobject = Message(name, message, message_options,
                                comment_path, self.comment_locations)
            if check_recursive_dependencies(msgobject, self.messages):
                sys.stderr.write('Breaking circular dependency at message %s by converting to %s\n'
                                 % (msgobject.name, "None"))
                msgobject = Message(
                    name, message, message_options, comment_path, self.comment_locations)
            self.messages.append(msgobject)

            # Process any nested enums
            for index, enum in enumerate(message.enum_type):
                name = self.manglenames.create_name(names + enum.name)
                enum_options = get_nanopb_suboptions(
                    enum, message_options, name)
                enum_path = comment_path + (ProtoElement.NESTED_ENUM, index)
                self.enums.append(
                    Enum(name, enum, enum_options, enum_path, self.comment_locations))

        for names, extension in iterate_extensions(self.fdesc, self.manglenames.flatten):
            name = self.manglenames.create_name(names + extension.name)
            field_options = get_nanopb_suboptions(
                extension, self.file_options, name)

            extension = copy.deepcopy(extension)
            if extension.type in (FieldD.TYPE_MESSAGE, FieldD.TYPE_ENUM):
                extension.type_name = self.manglenames.mangle_field_typename(
                    extension.type_name)


    def discard_unused_automatic_types(self):
        '''Discard unused types that are automatically generated by protoc if they are not actually
        needed. Currently this applies to map< > types when the field is ignored by options.
        '''
        map_entries = {}
        types_used = set()
        for msg in self.messages:
            if msg.desc.options.map_entry:
                map_entries[str(msg.name)] = msg

            for field in msg.all_fields():
                if field.pbtype == 'MESSAGE':
                    types_used.add(str(field.submsgname))

        for name, msg in map_entries.items():
            if name not in types_used:
                self.messages.remove(msg)

    def add_dependency(self, other):
        for enum in other.enums:
            self.dependencies[str(enum.names)] = enum
            self.dependencies[str(
                other.manglenames.unmangle(enum.names))] = enum
            enum.protofile = other

        for msg in other.messages:
            canonical_mangled_typename = str(
                other.manglenames.unmangle(msg.name))
            self.dependencies[str(msg.name)] = msg
            self.dependencies[canonical_mangled_typename] = msg
            msg.protofile = other

            # Fix references to submessages with different mangling rules
            for message in self.messages:
                for field in message.all_fields():
                    if field.ctype == canonical_mangled_typename:
                        field.ctype = msg.name

        # Fix field default values where enum short names are used.
        for enum in other.enums:
            for message in self.messages:
                for field in message.all_fields():
                    if field.default in enum.value_longnames:
                        idx = enum.value_longnames.index(field.default)
                        field.default = enum.values[idx][0]

        # Fix field data types where enums have negative values.
        for enum in other.enums:
            if not enum.has_negative():
                for message in self.messages:
                    for field in message.all_fields():
                        if field.pbtype == 'ENUM' and field.ctype == enum.names:
                            field.pbtype = 'UENUM'



def get_nanopb_suboptions(subdesc, options, name):
    '''Get copy of options, and merge information from subdesc.'''
    new_options = nanopb_pb2.NanoPBOptions()
    new_options.CopyFrom(options)

    # Handle options defined in a separate file
    dotname = '.'.join(name.parts)
    for namemask, options in Globals.separate_options:
        if fnmatchcase(dotname, namemask):
            Globals.matched_namemasks.add(namemask)
            new_options.MergeFrom(options)

    # Handle options defined in .proto
    if isinstance(subdesc.options, descriptor.FieldOptions):
        ext_type = nanopb_pb2.nanopb
    elif isinstance(subdesc.options, descriptor.FileOptions):
        ext_type = nanopb_pb2.nanopb_fileopt
    elif isinstance(subdesc.options, descriptor.MessageOptions):
        ext_type = nanopb_pb2.nanopb_msgopt
    elif isinstance(subdesc.options, descriptor.EnumOptions):
        ext_type = nanopb_pb2.nanopb_enumopt
    else:
        raise Exception("Unknown options type")

    if subdesc.options.HasExtension(ext_type):
        ext = subdesc.options.Extensions[ext_type]
        new_options.MergeFrom(ext)

    if Globals.verbose_options:
        sys.stderr.write("Options for " + dotname + ": ")
        sys.stderr.write(text_format.MessageToString(new_options) + "\n")

    return new_options


class MangleNames:
    '''Handles conversion of type names according to mangle_names option:
    M_NONE = 0; // Default, no typename mangling
    M_STRIP_PACKAGE = 1; // Strip current package name
    M_FLATTEN = 2; // Only use last path component
    M_PACKAGE_INITIALS = 3; // Replace the package name by the initials
    '''

    def __init__(self, fdesc, file_options):
        self.file_options = file_options
        self.mangle_names = file_options.mangle_names
        self.flatten = (self.mangle_names == nanopb_pb2.M_FLATTEN)
        self.strip_prefix = None
        self.replacement_prefix = None
        self.name_mapping = {}
        self.reverse_name_mapping = {}
        self.canonical_base = Names(fdesc.package.split('.'))

        if self.mangle_names == nanopb_pb2.M_STRIP_PACKAGE:
            self.strip_prefix = "." + fdesc.package
        elif self.mangle_names == nanopb_pb2.M_PACKAGE_INITIALS:
            self.strip_prefix = "." + fdesc.package
            self.replacement_prefix = ""
            for part in fdesc.package.split("."):
                self.replacement_prefix += part[0]

        if self.strip_prefix == '.':
            self.strip_prefix = ''

        if self.replacement_prefix is not None:
            self.base_name = Names(self.replacement_prefix.split('.'))
        elif fdesc.package:
            self.base_name = Names(fdesc.package.split('.'))
        else:
            self.base_name = Names()

    def create_name(self, names):
        '''Create name for a new message / enum.
        Argument can be either string or Names instance.
        '''
        if str(names) not in self.name_mapping:
            if self.mangle_names in (nanopb_pb2.M_NONE, nanopb_pb2.M_PACKAGE_INITIALS):
                new_name = self.base_name + names
            elif self.mangle_names == nanopb_pb2.M_STRIP_PACKAGE:
                new_name = Names(names)
            elif isinstance(names, Names):
                new_name = Names(names.parts[-1])
            else:
                new_name = Names(names)

            if str(new_name) in self.reverse_name_mapping:
                sys.stderr.write("Warning: Duplicate name with mangle_names=%s: %s and %s map to %s\n" %
                                 (self.mangle_names, self.reverse_name_mapping[str(new_name)], names, new_name))

            self.name_mapping[str(names)] = new_name
            self.reverse_name_mapping[str(
                new_name)] = self.canonical_base + names

            styled_name = Globals.naming_style.type_name(new_name)
            unmangled_styled_name = Globals.naming_style.type_name(
                self.canonical_base + names)

            if styled_name != unmangled_styled_name:
                # The styled name is mangled and needs extra mapping from unmangled to mangled. We just need to figure out whether
                # it requires one or two extra mappings to get from the unmangled to the mangled name, depending on how they differ.
                # This is required because enum dependencies are looked up from the reverse_name_mapping using names_from_type_name.

                # The type name (new_name) doesn't match either of the styled names, so we'll have to add an extra mapping to it.
                if str(new_name) != unmangled_styled_name and str(new_name) != styled_name:
                    self.reverse_name_mapping[unmangled_styled_name] = new_name

                # We need to be careful not to redefine the type name (new_name), use unmangled canonical name in this case.
                if styled_name == str(new_name):
                    self.reverse_name_mapping[str(
                        self.canonical_base + names)] = unmangled_styled_name
                else:
                    self.reverse_name_mapping[styled_name] = unmangled_styled_name

        return self.name_mapping[str(names)]

    def mangle_field_typename(self, typename):
        '''Mangle type name for a submessage / enum crossreference.
        Argument is a string.
        '''
        if self.mangle_names == nanopb_pb2.M_FLATTEN:
            return "." + typename.split(".")[-1]

        canonical_mangled_typename = str(Names(typename.strip(".").split(".")))
        if not canonical_mangled_typename.startswith(str(self.canonical_base) + "_"):
            return typename

        if self.strip_prefix is not None and typename.startswith(self.strip_prefix):
            if self.replacement_prefix is not None:
                return "." + self.replacement_prefix + typename[len(self.strip_prefix):]
            else:
                return typename[len(self.strip_prefix):]

        return typename

    def unmangle(self, names):
        return self.reverse_name_mapping.get(str(names), names)


def iterate_messages(desc, flatten=False, names=Names(), comment_path=()):
    '''Recursively find all messages. For each, yield name, DescriptorProto, comment_path.'''
    if hasattr(desc, 'message_type'):
        submsgs = desc.message_type
        comment_path += (ProtoElement.MESSAGE,)
    else:
        submsgs = desc.nested_type
        comment_path += (ProtoElement.NESTED_TYPE,)

    for idx, submsg in enumerate(submsgs):
        sub_names = names + submsg.name
        sub_path = comment_path + (idx,)
        if flatten:
            yield Names(submsg.name), submsg, sub_path
        else:
            yield sub_names, submsg, sub_path

        for x in iterate_messages(submsg, flatten, sub_names, sub_path):
            yield x


def iterate_extensions(desc, flatten=False, names=Names()):
    '''Recursively find all extensions.
    For each, yield name, FieldDescriptorProto.
    '''
    for extension in desc.extension:
        yield names, extension

    for subname, subdesc, comment_path in iterate_messages(desc, flatten, names):
        for extension in subdesc.extension:
            yield subname, extension


def check_recursive_dependencies(message, all_messages, root=None):
    '''Returns True if message has a recursive dependency on root (or itself if root is None).'''

    if not isinstance(all_messages, dict):
        all_messages = dict((str(m.name), m) for m in all_messages)

    if not root:
        root = message

    for dep in message.get_dependencies():
        if dep == str(root.name):
            return True
        elif dep in all_messages:
            if check_recursive_dependencies(all_messages[dep], all_messages, root):
                return True

    return False


def sort_dependencies(messages):
    '''Sort a list of Messages based on dependencies.'''

    # Construct first level list of dependencies
    dependencies = {}
    for message in messages:
        dependencies[str(message.name)] = set(message.get_dependencies())

    # Emit messages after all their dependencies have been processed
    remaining = list(messages)
    remainset = set(str(m.name) for m in remaining)
    while remaining:
        for candidate in remaining:
            if not remainset.intersection(dependencies[str(candidate.name)]):
                remaining.remove(candidate)
                remainset.remove(str(candidate.name))
                yield candidate
                break
        else:
            sys.stderr.write("Circular dependency in messages: " + ', '.join(
                remainset) + " (consider changing to FT_POINTER or FT_CALLBACK)\n")
            candidate = remaining.pop(0)
            remainset.remove(str(candidate.name))
            yield candidate


def make_identifier(headername):
    '''Make #ifndef identifier that contains uppercase A-Z and digits 0-9'''
    result = ""
    for c in headername.upper():
        if c.isalnum():
            result += c
        else:
            result += '_'
    return result


# ---------------------------------------------------------------------------
#                    Options parsing for the .proto files
# ---------------------------------------------------------------------------

def read_options_file(infile):
    '''Parse a separate options file to list:
        [(namemask, options), ...]
    '''
    results = []
    data = infile.read()
    data = re.sub(r'/\*.*?\*/', '', data, flags=re.MULTILINE)
    data = re.sub(r'//.*?$', '', data, flags=re.MULTILINE)
    data = re.sub(r'#.*?$', '', data, flags=re.MULTILINE)
    for i, line in enumerate(data.split('\n')):
        line = line.strip()
        if not line:
            continue

        parts = line.split(None, 1)

        if len(parts) < 2:
            sys.stderr.write("%s:%d: " % (infile.name, i + 1) +
                             "Option lines should have space between field name and options. " +
                             "Skipping line: '%s'\n" % line)
            sys.exit(1)

        opts = nanopb_pb2.NanoPBOptions()

        try:
            text_format.Merge(parts[1], opts)
        except Exception as e:
            sys.stderr.write("%s:%d: " % (infile.name, i + 1) +
                             "Unparsable option line: '%s'. " % line +
                             "Error: %s\n" % str(e))
            sys.exit(1)
        results.append((parts[0], opts))

    return results



def parse_file(filename, fdesc, options):
    '''Parse a single file. Returns a ProtoFile instance.'''
    toplevel_options = nanopb_pb2.NanoPBOptions()
    for s in options.settings:
        if ':' not in s and '=' in s:
            s = s.replace('=', ':')
        text_format.Merge(s, toplevel_options)

    if not fdesc:
        data = open(filename, 'rb').read()
        fdesc = descriptor.FileDescriptorSet.FromString(data).file[0]

    # Check if there is a separate .options file
    had_abspath = False
    try:
        optfilename = options.options_file % os.path.splitext(filename)[0]
    except TypeError:
        # No %s specified, use the filename as-is
        optfilename = options.options_file
        had_abspath = True

    paths = ['.'] + options.options_path
    for p in paths:
        if os.path.isfile(os.path.join(p, optfilename)):
            optfilename = os.path.join(p, optfilename)
            if options.verbose:
                sys.stderr.write('Reading options from ' + optfilename + '\n')
            Globals.separate_options = read_options_file(
                open(optfilename, 'r', encoding='utf-8'))
            break
    else:
        # If we are given a full filename and it does not exist, give an error.
        # However, don't give error when we automatically look for .options file
        # with the same name as .proto.
        if options.verbose or had_abspath:
            sys.stderr.write('Options file not found: ' + optfilename + '\n')
        Globals.separate_options = []

    Globals.matched_namemasks = set()
    Globals.protoc_insertion_points = options.protoc_insertion_points

    # Parse the file
    file_options = get_nanopb_suboptions(
        fdesc, toplevel_options, Names([filename]))
    f = ProtoFile(fdesc, file_options)
    f.optfilename = optfilename

    return f
