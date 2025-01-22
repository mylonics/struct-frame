#!/usr/bin/env python3
# kate: replace-tabs on; indent-width 4;

from nanopb_generator_base import *

class EnumCGen():
    @staticmethod
    def generate(field):
        leading_comment, trailing_comment = field.get_comments()

        result = ''
        if leading_comment:
            result = '%s\n' % leading_comment

        result += 'typedef enum %s' % Globals.naming_style.enum_name(
            field.names)

        result += ' {'

        if trailing_comment:
            result += " " + trailing_comment

        result += "\n"

        enum_length = len(field.values)
        enum_values = []
        for index, (name, value) in enumerate(field.values):
            leading_comment, trailing_comment = field.get_member_comments(index)

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

        result += ' %sTy;\n' % Globals.naming_style.type_name(field.names)

        result += 'typedef uint8_t %s;' % Globals.naming_style.type_name(field.names)
        return result


class FieldCGen():
    @staticmethod
    def generate(field):
        result = ''

        var_name = Globals.naming_style.var_name(field.name)
        type_name = Globals.naming_style.type_name(field.ctype) if isinstance(field.ctype, Names) else field.ctype
        result += '    %s %s%s;' % (type_name, var_name, field.array_decl)

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

class OneOfCGen():
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



class MessageCGen():
    @staticmethod
    def generate(msg):
        leading_comment, trailing_comment = msg.get_comments()

        result = ''
        if leading_comment:
            result = '%s\n' % leading_comment

        result += 'typedef struct %s {' % Globals.naming_style.struct_name(
            msg.name)
        if trailing_comment:
            result += " " + trailing_comment

        result += '\n'

        size = 1
        if not msg.fields:
            # Empty structs are not allowed in C standard.
            # Therefore add a dummy field if an empty message occurs.
            result += '    char dummy_field;'
        else:
            size = msg.data_size
        
        result += '\n'.join([FieldCGen.generate(f) for f in msg.fields])
        result += '\n}'
        struct_name = Globals.naming_style.type_name(msg.name)
        result += ' %s;\n\n' % struct_name

        result += '#define %s_max_size %d;\n' % (struct_name, size)

        if hasattr(msg, 'msgid'):
            result += '#define %s_msgid %d\n' % (msg.name, msg.msgid)

        result += 'MESSAGE_HELPER(%s, %d, %d);\n\n' % (struct_name,
                                                       size, msg.msgid)

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

class FileCGen():
    @staticmethod
    def generate(file, includes, headername, options):
        '''Generate content for a header file.
        Generates strings, which should be concatenated and stored to file.
        '''

        yield '/* Automatically generated nanopb header */\n'
        if options.notimestamp:
            yield '/* Generated by %s */\n\n' % (nanopb_version)
        else:
            yield '/* Generated by %s at %s. */\n\n' % (nanopb_version, time.asctime())

        if file.fdesc.package:
            symbol = make_identifier(file.fdesc.package + '_' + headername)
        else:
            symbol = make_identifier(headername)
        yield '#pragma once\n'
        yield '#pragma pack(1)\n'

        if file.math_include_required:
            yield '#include <math.h>\n'

        yield '#include "serial_frame.h"\n'

        for incfile in includes:
            noext = os.path.splitext(incfile)[0]
            yield options.genformat % (noext + options.extension + options.header_extension)
            yield '\n'

        if file.enums:
            yield '/* Enum definitions */\n'
            for enum in file.enums:
                yield EnumCGen.generate(enum) + '\n\n'

        if file.messages:
            yield '/* Struct definitions */\n'
            for msg in sort_dependencies(file.messages):
                yield msg.types()
                yield MessageCGen.generate(msg) + '\n'
            yield '\n'

        if file.extensions:
            yield '/* Extensions */\n'
            for extension in file.extensions:
                yield extension.extension_decl()
            yield '\n'

        if file.enums:
            yield '/* Helper constants for enums */\n'
            for enum in file.enums:
                yield enum.auxiliary_defines() + '\n'

            for msg in file.messages:
                yield msg.enumtype_defines() + '\n'
            yield '\n'

        if file.messages:
            yield '/* Initializer values for message structs */\n'
            for msg in file.messages:
                identifier = Globals.naming_style.define_name(
                    '%s_init_default' % msg.name)
                yield '#define %-40s %s\n' % (identifier, msg.get_initializer(False))
                unmangledName = file.manglenames.unmangle(msg.name)
                if unmangledName:
                    unmangledIdentifier = Globals.naming_style.define_name(
                        '%s_init_default' % unmangledName)
                    file.manglenames.reverse_name_mapping[identifier] = unmangledIdentifier
            for msg in file.messages:
                identifier = Globals.naming_style.define_name(
                    '%s_init_zero' % msg.name)
                yield '#define %-40s %s\n' % (identifier, msg.get_initializer(True))
                unmangledName = file.manglenames.unmangle(msg.name)
                if unmangledName:
                    unmangledIdentifier = Globals.naming_style.define_name(
                        '%s_init_zero' % unmangledName)
                    file.manglenames.reverse_name_mapping[identifier] = unmangledIdentifier
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
            yield 'uint8_t get_message_length(uint8_t msg_id){\n switch (msg_id)\n {\n'
            for msg in sort_dependencies(file.messages):
                name = Globals.naming_style.type_name(msg.name)
                yield '  case %s_msgid: return %s_max_size;\n' % (name, name)

            yield '  default: break;\n } return 0;\n}'
            yield '\n'




