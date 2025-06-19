
import re

version = "0.0.1"


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
        return name.upper()

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


def camelCase(st):
    output = ''.join(x for x in st.title() if x.isalnum())
    return output[0].lower() + output[1:]


def pascalCase(st):
    return ''.join(x for x in st.title() if x.isalnum())


pattern = re.compile(r'(?<!^)(?=[A-Z])')


def CamelToSnakeCase(data):
    return pattern.sub('_', data).lower()
