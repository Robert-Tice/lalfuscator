#!/usr/bin/env python

import argparse
import fnmatch
import json
import os

import obfuscator

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('project_file', help='The project file to obfuscate')
parser.add_argument('src_folder', help='The top level folder where all the source lives')
parser.add_argument("--scenario", type=json.loads, help="Scenario variables for the project in json form")
parser.add_argument("--target", help="Build target")
parser.add_argument("--runtime", help="Build runtime")
parser.add_argument("--dump", help="Dump lal tree of source files")
parser.add_argument("--dest", help="Destination folder for obfuscated project")
parser.add_argument("--name", help="The name of the obfuscated project and project directory")


class CLIProvider(obfuscator.BaseProvider):

    def __init__(self, proj_loc, src_dir):
        self.__proj_loc = proj_loc
        self.__src_dir = src_dir

    def log(self, msg, mode=None):
        print msg

    def get_source_list(self):
        matches = []
        for root, dirnames, filenames in os.walk(self.__src_dir):
            for filename in fnmatch.filter(filenames, "*.ad*"):
                matches.append(os.path.join(root, filename))
        return matches

    def get_proj_location(self):
        return self.__proj_loc

    def get_scenario_vars(self):
        args = parser.parse_args()
        return args.scenario

    def get_target(self):
        args = parser.parse_args()
        return args.target

    def get_runtime(self):
        args = parser.parse_args()
        return args.runtime


def main(args):
    provider =  CLIProvider(args.project_file, args.src_folder)
    obf = obfuscator.Obfuscator(provider)
    obf.do_obfuscate(args.dest, args.name, args.dump)

if __name__== "__main__":
    main(parser.parse_args())