#!/usr/bin/env python

import argparse
import fnmatch
import json
import os

import obfuscator

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('-P', '--project',
                    help='The project file to obfuscate',
                    required=True)
parser.add_argument('--src',
                    nargs='+',
                    help='The top level folder where all the source lives',
                    required=True)
parser.add_argument('--obj',
                    nargs='+',
                    help='The obj folder specified in the project file.',
                    required=True)
parser.add_argument("--scenario",
                    type=json.loads,
                    default=None,
                    help="Scenario variables for the project in json form")
parser.add_argument("--target",
                    default=None,
                    help="Build target")
parser.add_argument("--runtime",
                    default=None,
                    help="Build runtime")
parser.add_argument("--dump",
                    action='store_true',
                    help="Dump lal tree of source files")
parser.add_argument("--dest",
                    default=None,
                    help="Destination folder for obfuscated project. If this option is not provided, the dest directory will be the first parameter passed with the --obj argument.")
parser.add_argument("--name",
                    default="my_obfuscated_proj",
                    help="The name of the obfuscated project and project directory")
parser.add_argument("-f", "--force",
                    default=False,
                    help="Force creation of the obfuscated project. This will delete any obfuscated project with the same specified name in the destination directory.")
parser.add_argument("-q", "--quiet",
                    default=False,
                    help="Forces quiet execution.")
parser.add_argument("-rc",
                    action='store_true',
                    help="Removes all comments from the obfuscated source code.")


class CLIProvider(obfuscator.BaseProvider):

    def __init__(self, args):
        self.__args = args

    def log(self, msg, mode=None):
        if not self.__args.quiet:
            print msg

    def get_source_list(self):
        matches = []
        for src in self.__args.src:
            for root, dirnames, filenames in os.walk(src):
                for filename in fnmatch.filter(filenames, "*.ad*"):
                    matches.append(os.path.join(root, filename))
        return matches

    def get_dest_location(self):
        if self.__args.dest is None:
            dest = self.get_obj_locations()[0]
        else:
            dest = self.__args.dest

        if not os.path.isdir(dest):
            self.log("Destination path %s is invalid. Defaulting to current directory %s..." % (dest, os.getcwd()), mode="error")
            dest = os.getcwd()

        return dest

    def get_src_locations(self):
        return self.__args.src

    def get_obj_locations(self):
        return self.__args.obj

    def get_proj_location(self):
        return self.__args.project

    def get_scenario_vars(self):
        return self.__args.scenario

    def get_target(self):
        return self.__args.target

    def get_runtime(self):
        return self.__args.runtime


def main(args):
    provider =  CLIProvider(args)
    obf = obfuscator.Obfuscator(provider)
    obf.do_obfuscate(args.name, args.dump, args.rc)


if __name__== "__main__":
    main(parser.parse_args())