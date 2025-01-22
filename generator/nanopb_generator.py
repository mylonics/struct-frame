#!/usr/bin/env python3
# kate: replace-tabs on; indent-width 4;

from nanopb_generator_base import *
from ts_gen import *
from c_gen import *


# ---------------------------------------------------------------------------
#                         Command line interface
# ---------------------------------------------------------------------------


optparser = OptionParser(
    usage="Usage: nanopb_generator.py [options] file.pb ...",
    epilog="Compile file.pb from file.proto by: 'protoc -ofile.pb file.proto'. " +
    "Output will be written to file.sf.h and file.pb.c.")
optparser.add_option("-V", "--version", dest="version", action="store_true",
                     help="Show version info and exit (add -v for protoc version info)")
optparser.add_option("-x", dest="exclude", metavar="FILE", action="append", default=[],
                     help="Exclude file from generated #include list.")
optparser.add_option("-e", "--extension", dest="extension", metavar="EXTENSION", default=".sf",
                     help="Set extension to use instead of '.sf' for generated files. [default: %default]")
optparser.add_option("-H", "--header-extension", dest="header_extension", metavar="EXTENSION", default=".h",
                     help="Set extension to use for generated header files. [default: %default]")
optparser.add_option("-S", "--source-extension", dest="source_extension", metavar="EXTENSION", default=".c",
                     help="Set extension to use for generated source files. [default: %default]")
optparser.add_option("-f", "--options-file", dest="options_file", metavar="FILE", default="%s.options",
                     help="Set name of a separate generator options file.")
optparser.add_option("-I", "--options-path", "--proto-path", dest="options_path", metavar="DIR",
                     action="append", default=[],
                     help="Search path for .options and .proto files. Also determines relative paths for output directory structure.")
optparser.add_option("--error-on-unmatched", dest="error_on_unmatched", action="store_true", default=False,
                     help="Stop generation if there are unmatched fields in options file")
optparser.add_option("--no-error-on-unmatched", dest="error_on_unmatched", action="store_false", default=False,
                     help="Continue generation if there are unmatched fields in options file (default)")
optparser.add_option("-D", "--output-dir", dest="output_dir",
                     metavar="OUTPUTDIR", default=None,
                     help="Output directory of .pb.h and .pb.c files")
optparser.add_option("-Q", "--generated-include-format", dest="genformat",
                     metavar="FORMAT", default='#include "%s"',
                     help="Set format string to use for including other .pb.h files. Value can be 'quote', 'bracket' or a format string. [default: %default]")
optparser.add_option("-L", "--library-include-format", dest="libformat",
                     metavar="FORMAT", default='#include <%s>',
                     help="Set format string to use for including the nanopb pb.h header. Value can be 'quote', 'bracket' or a format string. [default: %default]")
optparser.add_option("--strip-path", dest="strip_path", action="store_true", default=False,
                     help="Strip directory path from #included .pb.h file name")
optparser.add_option("--no-strip-path", dest="strip_path", action="store_false",
                     help="Opposite of --strip-path (default since 0.4.0)")
optparser.add_option("--cpp-descriptors", action="store_true",
                     help="Generate C++ descriptors to lookup by type (e.g. pb_field_t for a message)")
optparser.add_option("-T", "--no-timestamp", dest="notimestamp", action="store_true", default=True,
                     help="Don't add timestamp to .pb.h and .pb.c preambles (default since 0.4.0)")
optparser.add_option("-t", "--timestamp", dest="notimestamp", action="store_false", default=True,
                     help="Add timestamp to .pb.h and .pb.c preambles")
optparser.add_option("-q", "--quiet", dest="quiet", action="store_true", default=False,
                     help="Don't print anything except errors.")
optparser.add_option("-v", "--verbose", dest="verbose", action="store_true", default=False,
                     help="Print more information.")
optparser.add_option("-s", dest="settings", metavar="OPTION:VALUE", action="append", default=[],
                     help="Set generator option (max_size, max_count etc.).")
optparser.add_option("--protoc-opt", dest="protoc_opts", action="append", default=[], metavar="OPTION",
                     help="Pass an option to protoc when compiling .proto files")
optparser.add_option("--protoc-insertion-points", dest="protoc_insertion_points", action="store_true", default=False,
                     help="Include insertion point comments in output for use by custom protoc plugins")
optparser.add_option("-C", "--c-style", dest="c_style", action="store_true", default=False,
                     help="Use C naming convention.")


def parse_custom_style(option, opt_str, value, parser):
    parts = value.rsplit(".", 1)
    if len(parts) != 2 or not all(len(part) > 0 for part in parts):
        raise OptionValueError("Invalid value for %s, must be in the form %s: %r" % (
            opt_str, option.metavar, value))
    setattr(parser.values, option.dest, parts)


optparser.add_option("--custom-style", dest="custom_style", type=str, metavar="MODULE.CLASS", action="callback", callback=parse_custom_style,
                     help="Use a custom naming convention from a module/class that defines the methods from the NamingStyle class to be overridden. When paired with the -C/--c-style option, the NamingStyleC class is the fallback, otherwise it's the NamingStyle class.")


def process_cmdline(args, is_plugin):
    '''Process command line options. Returns list of options, filenames.'''

    options, filenames = optparser.parse_args(args)

    if options.version:
        if is_plugin:
            sys.stderr.write('%s\n' % (nanopb_version))
        else:
            print(nanopb_version)

        if options.verbose:
            proto.print_versions()

        sys.exit(0)

    if not filenames and not is_plugin:
        optparser.print_help()
        sys.exit(1)

    if options.quiet:
        options.verbose = False

    include_formats = {'quote': '#include "%s"', 'bracket': '#include <%s>'}
    options.libformat = include_formats.get(
        options.libformat, options.libformat)
    options.genformat = include_formats.get(
        options.genformat, options.genformat)

    if options.custom_style:
        module_path, class_name = options.custom_style
        module_name = os.path.splitext(os.path.basename(module_path))[0]
        if not module_path.endswith(".py"):
            module_path = module_path + ".py"

        spec = importlib.util.spec_from_file_location(module_name, module_path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)

        custom_class = getattr(module, class_name)

        class InheritNamingStyle(custom_class, NamingStyleC if options.c_style else NamingStyle):
            """Class to inherit from the custom class and then NamingStyle or NamingCStyle, in case it doesn't implement all methods."""
            pass

        Globals.naming_style = InheritNamingStyle()
    elif options.c_style:
        Globals.naming_style = NamingStyleC()

    Globals.verbose_options = options.verbose

    if options.verbose:
        sys.stderr.write("Nanopb version %s\n" % nanopb_version)
        sys.stderr.write('Google Python protobuf library imported from %s, version %s\n'
                         % (google.protobuf.__file__, google.protobuf.__version__))

    return options, filenames


def generate_files(filename, fdesc, options, other_files={}):
    '''Process a single file.
    filename: The full path to the .proto or .pb source file, as string.
    fdesc: The loaded FileDescriptorSet, or None to read from the input file.
    options: Command line options as they come from OptionsParser.

    Returns a dict:
        {'headername': Name of header file,
         'headerdata': Data for the .h header file,
        }
    '''
    f = parse_file(filename, fdesc, options)

    # Check the list of dependencies, and if they are available in other_files,
    # add them to be considered for import resolving. Recursively add any files
    # imported by the dependencies.
    deps = list(f.fdesc.dependency)
    while deps:
        dep = deps.pop(0)
        if dep in other_files:
            f.add_dependency(other_files[dep])
            deps += list(other_files[dep].fdesc.dependency)

    # Decide the file names
    noext = os.path.splitext(filename)[0]
    headername = noext + ".sf"
    
    if options.strip_path:
        headerbasename = os.path.basename(headername)
    else:
        headerbasename = headername
    
    # List of .proto files that should not be included in the C header file
    # even if they are mentioned in the source .proto.
    excludes = ['nanopb.proto', 'google/protobuf/descriptor.proto']
    includes = [d for d in f.fdesc.dependency if d not in excludes]

    c_name = "c/" + headername + ".h"
    c_data = ''.join(FileCGen.generate(f, includes, headerbasename, options))
    
    ts_name = "ts/" + headername + ".ts"
    ts_data = ''.join(FileTsGen.generate(f, includes, headerbasename, options))
    
    print(headername)
    return [{'headername': c_name, 'headerdata': c_data},{'headername': ts_name, 'headerdata': ts_data}]


def main():
    '''Main function when invoked directly from the command line.'''

    options, filenames = process_cmdline(sys.argv[1:], is_plugin=False)

    if options.output_dir and not os.path.exists(options.output_dir):
        optparser.print_help()
        sys.stderr.write("\noutput_dir does not exist: %s\n" %
                         options.output_dir)
        sys.exit(1)

    # Load .pb files into memory and compile any .proto files.
    include_path = ['-I%s' % p for p in options.options_path]
    all_fdescs = {}
    out_fdescs = {}
    for filename in filenames:
        if filename.endswith(".proto"):
            with TemporaryDirectory() as tmpdir:
                tmpname = os.path.join(
                    tmpdir, os.path.basename(filename) + ".pb")
                args = ["protoc"] + include_path
                args += options.protoc_opts
                args += ['--include_imports',
                         '--include_source_info', '-o' + tmpname, filename]
                status = invoke_protoc(args)
                if status != 0:
                    sys.exit(status)
                data = open(tmpname, 'rb').read()
        else:
            data = open(filename, 'rb').read()

        fdescs = descriptor.FileDescriptorSet.FromString(data).file
        last_fdesc = fdescs[-1]

        for fdesc in fdescs:
            all_fdescs[fdesc.name] = fdesc

        out_fdescs[last_fdesc.name] = last_fdesc

    # Process any include files first, in order to have them
    # available as dependencies
    other_files = {}
    for fdesc in all_fdescs.values():
        print("printing other files")
        print(fdesc.name)
        other_files[fdesc.name] = parse_file(fdesc.name, fdesc, options)

    # Then generate the headers / sources
    for fdesc in out_fdescs.values():
        results = generate_files(fdesc.name, fdesc, options, other_files)
        for res in results:

            base_dir = options.output_dir or ''
            to_write = [
                (os.path.join(base_dir,
                 res['headername']), res['headerdata']),
            ]

            if not options.quiet:
                paths = " and ".join([x[0] for x in to_write])
                sys.stderr.write("Writing to %s\n" % paths)

            for path, data in to_write:
                dirname = os.path.dirname(path)
                if dirname and not os.path.exists(dirname):
                    os.makedirs(dirname)

                with open(path, 'w', encoding='utf-8') as f:
                    f.write(data)


if __name__ == '__main__':
    main()
