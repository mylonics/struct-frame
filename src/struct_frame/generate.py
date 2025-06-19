#!/usr/bin/env python3
# kate: replace-tabs on; indent-width 4;


import os
import shutil
from struct_frame import FileCGen
from struct_frame import FileTsGen
from proto_schema_parser.parser import Parser
from proto_schema_parser import ast

import argparse

recErrCurrentField = ""
recErrCurrentMessage = ""

default_types = {
    "uint8": {"size": 1},
    "int8": {"size": 1},
    "uint16": {"size": 2},
    "int16": {"size": 2},
    "uint32": {"size": 4},
    "int32": {"size": 4},
    "bool": {"size": 1},
    "float": {"size": 4},
    "double": {"size": 8}
}


class Enum:
    def __init__(self, package, comments):
        self.name = None
        self.data = {}
        self.size = 1
        self.comments = comments
        self.package = package
        self.isEnum = True

    def parse(self, enum):
        self.name = enum.name
        comments = []
        for e in enum.elements:
            if type(e) == ast.Comment:
                comments.append(e.text)
            else:
                if e.name in self.data:
                    print(f"Enum Field Redclaration")
                    return False
                self.data[e.name] = (e.number, comments)
                comments = []

        return True

    def validate(self, currentPackage, packages):
        return True

    def __str__(self):
        output = ""
        for c in self.comments:
            output = output + c + "\n"

        output = output + f"Enum: {self.name}\n"

        for key, value in self.data.items():
            output = output + f"Key: {key}, Value: {value}" + "\n"
        return output


class Field:
    def __init__(self, package, comments):
        self.name = None
        self.fieldType = None
        self.isDefaultType = False
        self.size = 0
        self.validated = False
        self.comments = comments
        self.package = package
        self.isEnum = False

    def parse(self, field):
        self.name = field.name
        self.fieldType = field.type
        if self.fieldType in default_types:
            self.isDefaultType = True
            self.size = default_types[self.fieldType]["size"]
            self.validated = True
        return True

    def validate(self, currentPackage, packages):

        global recErrCurrentField
        recErrCurrentField = self.name
        if not self.validated:
            ret = currentPackage.findFieldType(self.fieldType)

            if ret:
                if ret.validate(currentPackage, packages):
                    self.isEnum = ret.isEnum
                    self.validate = True
                    self.size = ret.size
                else:
                    print(
                        f"Failed to validate Field: {self.name} of Type: {self.fieldType} in Package: {currentPackage.name}")
                    return False
            else:
                print(
                    f"Failed to find Field: {self.name} of Type: {self.fieldType} in Package: {currentPackage.name}")
                return False

        return True

    def __str__(self):
        output = ""
        for c in self.comments:
            output = output + c + "\n"
        output = output + \
            f"Field: {self.name}, Type:{self.fieldType}, Size:{self.size}"
        return output


class Message:
    def __init__(self, package, comments):
        self.id = None
        self.size = 0
        self.name = None
        self.fields = {}
        self.validated = False
        self.comments = comments
        self.package = package
        self.isEnum = False

    def parse(self, msg):
        self.name = msg.name
        comments = []
        for e in msg.elements:
            if type(e) == ast.Option:
                if e.name == "msgid":
                    if self.id:
                        raise Exception(f"Redefinition of msg_id for {e.name}")
                    self.id = e.value
            elif type(e) == ast.Comment:
                comments.append(e.text)
            elif type(e) == ast.Field:
                if e.name in self.fields:
                    print(f"Field Redclaration")
                    return False
                self.fields[e.name] = Field(self.package, comments)
                comments = []
                if not self.fields[e.name].parse(e):
                    return False
        return True

    def validate(self, currentPackage, packages):
        if self.validated:
            return True

        global recErrCurrentMessage
        recErrCurrentMessage = self.name
        for key, value in self.fields.items():
            if not value.validate(currentPackage, packages):
                print(
                    f"Failed To validate Field: {key}, in Message {self.name}\n")
                return False
            self.size = self.size + value.size

        self.validated = True
        return True

    def __str__(self):
        output = ""
        for c in self.comments:
            output = output + c + "\n"
        output = output + \
            f"Message: {self.name}, Size: {self.size}, ID: {self.id}\n"

        for key, value in self.fields.items():
            output = output + value.__str__() + "\n"
        return output


class Package:
    def __init__(self, name):
        self.name = name
        self.enums = {}
        self.messages = {}

    def addEnum(self, enum, comments):
        self.comments = comments
        if enum.name in self.enums:
            print(f"Enum Redclaration")
            return False
        self.enums[enum.name] = Enum(self.name, comments)
        return self.enums[enum.name].parse(enum)

    def addMessage(self, message, comments):
        if message.name in self.messages:
            print(f"Message Redclaration")
            return False
        self.messages[message.name] = Message(self.name, comments)
        return self.messages[message.name].parse(message)

    def validatePackage(self, allPackages):
        names = []
        for key, value in self.enums.items():
            if value.name in names:
                print(
                    f"Name collision with Enum and Message: {value.name} in Packaage {self.name}")
                return False
            names.append(value.name)
        for key, value in self.messages.items():
            if value.name in names:
                print(
                    f"Name collision with Enum and Message: {value.name} in Packaage {self.name}")
                return False
            names.append(value.name)

        for key, value in self.messages.items():
            if not value.validate(self, allPackages):
                print(
                    f"Failed To validate Message: {key}, in Package {self.name}\n")
                return False

        return True

    def findFieldType(self, name):
        for key, value in self.enums.items():
            if value.name == name:
                return value

        for key, value in self.messages.items():
            if value.name == name:
                return value

    def sortedMessages(self):
        # Need to sort messages to ensure no out of order dependencies.
        return self.messages

    def __str__(self):
        output = "Package: " + self.name + "\n"
        for key, value in self.enums.items():
            output = output + value.__str__() + "\n"
        for key, value in self.messages.items():
            output = output + value.__str__() + "\n"
        return output


packages = {}
processed_file = []
required_file = []

parser = argparse.ArgumentParser(
    prog='struct_frame',
    description='Message serialization and header generation program')

parser.add_argument('filename')
parser.add_argument('--debug', action='store_true')
parser.add_argument('--build_c', action='store_true')
parser.add_argument('--build_ts', action='store_true')
parser.add_argument('--c_path', nargs=1, type=str, default=['c/'])
parser.add_argument('--ts_path', nargs=1, type=str, default=['ts/'])


def parseFile(filename):
    processed_file.append(filename)
    with open(filename, "r") as f:
        result = Parser().parse(f.read())

        foundPackage = False
        package_name = ""
        comments = []

        for e in result.file_elements:
            if (type(e) == ast.Package):
                if foundPackage:
                    print(
                        f"Multiple Package declaration found in file {filename} - {package_name}")
                    return False
                foundPackage = True
                package_name = e.name
                if package_name not in packages:
                    packages[package_name] = Package(package_name)
                packages

            elif (type(e) == ast.Enum):
                if not packages[package_name].addEnum(e, comments):
                    print(
                        f"Enum Error in Package: {package_name}  FileName: {filename} EnumName: {e.name}")
                    return False
                comments = []

            elif (type(e) == ast.Message):
                if not packages[package_name].addMessage(e, comments):
                    print(
                        f"Message Error in Package: {package_name}  FileName: {filename} MessageName: {e.name}")
                    return False
                comments = []

            elif (type(e) == ast.Comment):
                comments.append(e.text)


def validatePackages():
    for key, value in packages.items():
        if not value.validatePackage(packages):
            print(f"Failed To Validate Package: {key}")
            return False

    return True


def printPackages():
    for key, value in packages.items():
        print(value)


def generateCFileStrings(path):
    out = {}
    for key, value in packages.items():
        name = os.path.join(path, value.name + ".sf.h")
        data = ''.join(FileCGen.generate(value))
        out[name] = data

    return out


def generateTsFileStrings(path):
    out = {}
    for key, value in packages.items():
        name = os.path.join(path, value.name + ".sf.ts")
        data = ''.join(FileTsGen.generate(value))
        out[name] = data
    return out


def main():
    args = parser.parse_args()
    parseFile(args.filename)

    if (not args.build_c and not args.build_ts):
        print("Select at least one build argument")
        return

    try:
        validatePackages()
    except RecursionError as err:
        print(
            f'Recursion Error. Messages most likely have a cyclical dependancy. Check Message: {recErrCurrentMessage} and Field: {recErrCurrentField}')

    if (args.build_c):
        files = generateCFileStrings(args.c_path[0])

    if (args.build_ts):
        files.update(generateTsFileStrings(args.ts_path[0]))

    for filename, filedata in files.items():
        dirname = os.path.dirname(filename)
        if dirname and not os.path.exists(dirname):
            os.makedirs(dirname)

        with open(filename, 'w', encoding='utf-8') as f:
            f.write(filedata)

    dir_path = os.path.dirname(os.path.realpath(__file__))

    if (args.build_c):
        shutil.copytree(os.path.join(dir_path, "boilerplate/c"),
                        args.c_path[0], dirs_exist_ok=True)

    if (args.build_ts):
        shutil.copytree(os.path.join(dir_path, "boilerplate/ts"),
                        args.ts_path[0], dirs_exist_ok=True)

    if args.debug:
        printPackages()
    print("Struct Frame successfully completed")


if __name__ == '__main__':
    main()
