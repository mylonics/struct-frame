#!/usr/bin/env python3
# kate: replace-tabs on; indent-width 4;

from nanopb_generator_base import *

tsTypes = {
    "int8_t":     ('Int8'),
    "uint8_t":    ('UInt8'),
    "int16_t":    ('Int16LE'),
    "uint16_t":   ('UInt16LE'),
    "bool":     ('Boolean8'),
    "double":   ('Float64LE'),
    "float":    ('Float32LE'),
    "int32_t":  ('Int32LE'),
    "uint32_t": ('UInt32LE'),
    "uint64_t": ('BigInt64LE'),
    "int64_t":  ('BigUInt64LE'),
}


class EnumTsGen():
    @staticmethod
    def generate(field):
        leading_comment, trailing_comment = field.get_comments()

        result = ''
        if leading_comment:
            result = '%s\n' % leading_comment

        result += 'export enum %s' % Globals.naming_style.type_name(field.names)

        result += ' {'

        if trailing_comment:
            result += " " + trailing_comment

        result += "\n"

        enum_length = len(field.values)
        enum_values = []
        for index, (name, value) in enumerate(field.values):
            leading_comment, trailing_comment = field.get_member_comments(
                index)

            if leading_comment:
                enum_values.append(leading_comment)

            comma = ","
            if index == enum_length - 1:
                # last enum member should not end with a comma
                comma = ""

            enum_value = "    %s = %d%s" % (
                Globals.naming_style.enum_entry(name), value, comma)
            if trailing_comment:
                enum_value += " " + trailing_comment

            enum_values.append(enum_value)

        result += '\n'.join(enum_values)
        result += '\n}'

        return result


class FieldTsGen():
    @staticmethod
    def generate(field):
        result = ''
        isEnum = field.pbtype in ('ENUM', 'UENUM')
        var_name = Globals.naming_style.var_name(field.name)
        type_name = Globals.naming_style.type_name(
            field.ctype) if isinstance(field.ctype, Names) else field.ctype

        if type_name in tsTypes:
            type_name = tsTypes[type_name]

        if isEnum:
            result += '    .UInt8(\'%s\', typed<%s>())' % (var_name, type_name)
        else:
            result += '    .%s(\'%s\')' % (type_name, var_name)

        leading_comment, trailing_comment = field.get_comments(
            leading_indent=True)
        if leading_comment:
            result = leading_comment + "\n" + result
        if trailing_comment:
            result = result + " " + trailing_comment

        return result

# ---------------------------------------------------------------------------
#                   Generation of oneofs (unions)
# ---------------------------------------------------------------------------


class OneOfTsGen():
    @staticmethod
    def generate(oneof):
        result = ''
        if oneof.fields:
            if oneof.has_msg_cb:
                result += '    pb_callback_t cb_' + \
                    Globals.naming_style.var_name(oneof.name) + ';\n'

            result += '    pb_size_t which_' + \
                Globals.naming_style.var_name(oneof.name) + ";\n"
            if oneof.anonymous:
                result += '    union {\n'
            else:
                result += '    union ' + \
                    Globals.naming_style.union_name(
                        oneof.struct_name + oneof.name) + ' {\n'
            for f in oneof.fields:
                result += '    ' + str(f).replace('\n', '\n    ') + '\n'
            if oneof.anonymous:
                result += '    };'
            else:
                result += '    } ' + \
                    Globals.naming_style.var_name(oneof.name) + ';'
        return result

    @staticmethod
    def get_initializer(oneof, null_init):
        if oneof.has_msg_cb:
            return '{{NULL}, NULL}, 0, {' + oneof.fields[0].get_initializer(null_init) + '}'
        else:
            return '0, {' + oneof.fields[0].get_initializer(null_init) + '}'


# ---------------------------------------------------------------------------
#                   Generation of messages (structures)
# ---------------------------------------------------------------------------


class MessageTsGen():
    @staticmethod
    def generate(msg):
        leading_comment, trailing_comment = msg.get_comments()

        result = ''
        if leading_comment:
            result = '%s\n' % leading_comment

        struct_name = Globals.naming_style.type_name(msg.name)
        result += 'export const %s = new typed_struct.Struct(\'%s\') ' % (
            struct_name, struct_name)
        if trailing_comment:
            result += " " + trailing_comment

        result += '\n'

        size = 1
        if not msg.fields:
            # Empty structs are not allowed in C standard.
            # Therefore add a dummy field if an empty message occurs.
            result += '    .UInt8(\'dummy_field\');'
        else:
            size = msg.data_size

        result += '\n'.join([FieldTsGen.generate(f) for f in msg.fields])
        result += '\n    .compile();\n\n'

        result += 'export const %s_max_size = %d;\n' % (struct_name, size)

        if hasattr(msg, 'msgid'):
            result += 'export const %s_msgid = %d\n' % (msg.name, msg.msgid)

            result += 'export function %s_encode(buffer: struct_frame_buffer, msg: any) {\n' % (
                msg.name, msg.name)
            result += '    msg_encode(buffer, msg, %s_msgid)\n}\n' % (msg.name)

            result += 'export function %s_reserve(buffer: struct_frame_buffer) {\n' % (
                msg.name)
            result += '    const msg_buffer = msg_reserve(buffer, %s_msgid, %s_max_size);\n' % (
                msg.name, msg.name)
            result += '    if (msg_buffer){\n'
            result += '        return new %s(msg_buffer)\n    }\n    return;\n}\n' % (
                msg.name)

            result += 'export function %s_finish(buffer: struct_frame_buffer) {\n' % (
                msg.name)
            result += '    msg_finish(buffer);\n}\n'
        return result + '\n'

    @staticmethod
    def get_initializer(msg, null_init):
        if not msg.fields:
            return '{0}'

        parts = []
        for field in msg.fields:
            parts.append(field.get_initializer(null_init))
        return '{' + ', '.join(parts) + '}'

    @staticmethod
    def default_value(msg, dependencies):
        '''Generate serialized protobuf message that contains the
        default values for optional fields.'''

        if not msg.desc:
            return b''

        optional_only = copy.deepcopy(msg.desc)

        # Remove fields without default values
        # The iteration is done in reverse order to avoid remove() messing up iteration.
        for field in reversed(list(optional_only.field)):
            field.ClearField(str('extendee'))
            parsed_field = msg.field_for_tag(field.number)
            if parsed_field is None or parsed_field.allocation != 'STATIC':
                optional_only.field.remove(field)
            elif (field.label == FieldD.LABEL_REPEATED or
                  field.type == FieldD.TYPE_MESSAGE):
                optional_only.field.remove(field)
            elif hasattr(field, 'oneof_index') and field.HasField('oneof_index'):
                optional_only.field.remove(field)
            elif field.type == FieldD.TYPE_ENUM:
                # The partial descriptor doesn't include the enum type
                # so we fake it with int64.
                enumname = names_from_type_name(field.type_name)
                try:
                    enumtype = dependencies[str(enumname)]
                except KeyError:
                    raise Exception("Could not find enum type %s while generating default values for %s.\n" % (enumname, msg.name)
                                    + "Try passing all source files to generator at once, or use -I option.")

                if not isinstance(enumtype, Enum):
                    raise Exception("Expected enum type as %s, got %s" % (
                        enumname, repr(enumtype)))

                if field.HasField('default_value'):
                    defvals = [
                        v for n, v in enumtype.values if n.parts[-1] == field.default_value]
                else:
                    # If no default is specified, the default is the first value.
                    defvals = [v for n, v in enumtype.values]
                if defvals and defvals[0] != 0:
                    field.type = FieldD.TYPE_INT64
                    field.default_value = str(defvals[0])
                    field.ClearField(str('type_name'))
                else:
                    optional_only.field.remove(field)
            elif not field.HasField('default_value'):
                optional_only.field.remove(field)

        if len(optional_only.field) == 0:
            return b''

        optional_only.ClearField(str('oneof_decl'))
        optional_only.ClearField(str('nested_type'))
        optional_only.ClearField(str('extension'))
        optional_only.ClearField(str('enum_type'))
        optional_only.name += str(id(msg))

        desc = google.protobuf.descriptor.MakeDescriptor(optional_only)
        msg = GetMessageClass(desc)()

        for field in optional_only.field:
            if field.type == FieldD.TYPE_STRING:
                setattr(msg, field.name, field.default_value)
            elif field.type == FieldD.TYPE_BYTES:
                setattr(msg, field.name, codecs.escape_decode(
                    field.default_value)[0])
            elif field.type in [FieldD.TYPE_FLOAT, FieldD.TYPE_DOUBLE]:
                setattr(msg, field.name, float(field.default_value))
            elif field.type == FieldD.TYPE_BOOL:
                setattr(msg, field.name, field.default_value == 'true')
            else:
                setattr(msg, field.name, int(field.default_value))

        return msg.SerializeToString()


class FileTsGen():
    @staticmethod
    def generate(file, includes, headername, options):
        '''Generate content for a header file.
        Generates strings, which should be concatenated and stored to file.
        '''

        yield '/* Automatically generated struct frame header */\n'
        if options.notimestamp:
            yield '/* Generated by %s */\n\n' % (nanopb_version)
        else:
            yield '/* Generated by %s at %s. */\n\n' % (nanopb_version, time.asctime())

        if file.fdesc.package:
            symbol = make_identifier(file.fdesc.package + '_' + headername)
        else:
            symbol = make_identifier(headername)

        yield 'const typed_struct = require(\'typed-struct\')\n'
        yield 'const ExtractType = typeof typed_struct.ExtractType;\n'
        yield 'const type = typeof typed_struct.ExtractType;\n\n'



        yield "import { struct_frame_buffer } from './struct_frame_types';\n"

        yield "import { msg_encode, msg_reserve, msg_finish } from './struct_frame';\n\n"

        for incfile in includes:
            noext = os.path.splitext(incfile)[0]
            yield options.genformat % (noext + options.extension + options.header_extension)
            yield '\n'

        if file.enums:
            yield '/* Enum definitions */\n'
            for enum in file.enums:
                yield EnumTsGen.generate(enum) + '\n\n'

        if file.messages:
            yield '/* Struct definitions */\n'
            for msg in sort_dependencies(file.messages):
                yield msg.types()
                yield MessageTsGen.generate(msg) + '\n'
            yield '\n'

        # Check if there is any name mangling active
        pairs = [x for x in file.manglenames.reverse_name_mapping.items()
                 if str(x[0]) != str(x[1])]
        if pairs:
            yield '/* Mapping from canonical names (mangle_names or overridden package name) */\n'
            for shortname, longname in pairs:
                yield '#define %s %s\n' % (longname, shortname)
            yield '\n'
        if file.messages:
            yield 'export function get_message_length(msg_id : number){\n switch (msg_id)\n {\n'
            for msg in sort_dependencies(file.messages):
                name = Globals.naming_style.type_name(msg.name)
                yield '  case %s_msgid: return %s_max_size;\n' % (name, name)

            yield '  default: break;\n } return 0;\n}'
            yield '\n'
