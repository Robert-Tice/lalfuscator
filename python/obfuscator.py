from abc import abstractmethod
import inspect
import libadalang as lal
import os
import shutil

class BaseProvider:

    @abstractmethod
    def log(self, msg, mode=None):
        pass

    @abstractmethod
    def get_source_list(self):
        pass

    @abstractmethod
    def get_proj_location(self):
        pass

    @abstractmethod
    def get_scenario_vars(self):
        pass


class Token:
    __counter = 0

    def __init__(self, prefix):
        self.__prefix = prefix

    def next(self):
        ret = self.__counter
        self.__counter += 1
        return "%s%d" % (self.__prefix, ret)


class Obfuscator:

    __units = []
    __file_map = {}

    def __init__(self, provider):
        self.__provider = provider

    def __create_obfuscated_project(self, dest, name):
        counter = 0

        if not os.path.isdir(dest):
            self.__provider.log("Destination path %s is invalid. Defaulting to current directory %s..." % (dest, os.getcwd()), mode="error")
            dest = os.getcwd()

        if name is None:
            name = "obdir_"

        # create obfuscated project from loaded project
        while True:
            wr_dirname = os.path.join(dest, "obdir_%s" % counter)
            if not os.path.isdir(wr_dirname):
                os.mkdir(wr_dirname)
                os.mkdir(os.path.join(wr_dirname, "src"))
                break
            else:
                counter += 1

        ro_sources = self.__provider.get_source_list()

        self.__wr_proj = os.path.join(wr_dirname, os.path.basename(self.__provider.get_proj_location()))

        shutil.copyfile(self.__provider.get_proj_location(), self.__wr_proj)

        dests = []
        for src in ro_sources:
            dest = os.path.join(wr_dirname, "src", os.path.basename(src))
            shutil.copyfile(src, dest)
            dests.append(dest)

        self.__unit_provider = lal.UnitProvider.for_project(self.__wr_proj, scenario_vars=self.__provider.get_scenario_vars(), target=self.__provider.get_target(), runtime=self.__provider.get_runtime())
        self.__ctx = lal.AnalysisContext(unit_provider=self.__unit_provider)

        for src in dests:
            self.__units.append(self.__ctx.get_from_file(src))

    def __edit_files(self, catalog):
        by_filename = {}

        for key, value in catalog.iteritems():
            for node in value["nodes"]:
            #    self.__provider.log("%s:%s %s -> %s" % (os.path.basename(node.unit.filename), node.sloc_range, node.text, value["token"]))
                if node.unit.filename in by_filename.keys():
                    if node.sloc_range.start.line in by_filename[node.unit.filename].keys():
                        by_filename[node.unit.filename][node.sloc_range.start.line].append({"node": node, "token": value["token"]})
                    else:
                        by_filename[node.unit.filename][node.sloc_range.start.line] = [{"node": node, "token": value["token"]}]
                else:
                    by_filename[node.unit.filename] = {node.sloc_range.start.line: [{"node": node, "token": value["token"]}]}

        for key, value in by_filename.iteritems():
            with open(key, 'r') as f:
                lines = f.readlines()

            for line, nodes in value.iteritems():
                nodes.sort(key=lambda x: x["node"].sloc_range.start.column, reverse=True)
                for node_dict in nodes:
                    node = node_dict["node"]
                    token = node_dict["token"]
                    lines[line - 1] = lines[line - 1][:node.sloc_range.start.column - 1] + token  + lines[line - 1][node.sloc_range.end.column - 1:]

            with open(key, 'w') as f:
                f.writelines(lines)

            if key in self.__file_map.keys():
                dest = os.path.join(os.path.dirname(os.path.abspath(key)), self.__file_map[key] + os.path.splitext(key)[1])
                #self.__provider.log("Move %s to %s" % (key, dest))
                if key != dest:
                    if os.path.isfile(dest):
                        self.__provider.log("Error: file %s already exists..." % dest, mode="error")
                    else:
                        shutil.move(key, dest)
            else:
                self.__provider.log("%s has no rename target. Maybe main?" % key)

    def __generate_token_map(self, catalog):
        lines = []
        for key, value in catalog.iteritems():
            lines.append("%s, %s\n" % (list(value["nodes"])[0].text, value["token"]))

        with open(os.path.join(os.path.dirname(self.__wr_proj), "token_map.txt"), "w") as f:
            f.writelines(lines)

    def do_obfuscate(self, dest, name, dump):
        if dest is None:
            dest = os.getcwd()
        self.__create_obfuscated_project(dest, name)
        node_catalog = self.__populate_catalog(dump)
        self.__generate_token_map(node_catalog)
        self.__edit_files(node_catalog)
        self.__provider.log("Obfuscated project located: %s" % self.__wr_proj)

    def __populate_catalog(self, dump):
        catalog = {}

        token_catalog = {"package": Token("pk"),
                         "subprogram": Token("sp"),
                         "constant": Token("c"),
                         "object": Token("ob"),
                         "type": Token("t"),
                         "parameter": Token("fp"),
                         "literal": Token("l")
                        }

        def add_node(key, node, token_type):
            key = key.lower()
            if key in catalog.keys():
                catalog[key]["nodes"].update(node)
            else:
                catalog[key] = {"nodes": set([node]), "token": token_type.next()}

        def file_location(node):
            return "%s:%s" % (os.path.basename(node.unit.filename), node.sloc_range)

        rt_prefix = ["ada", "gnat", "interfaces", "standard", "system"]
        def runtime_pkg(node):
            text = node.text.lower()
            if text in rt_prefix:
                return True
            return from_runtime(node)

        def from_runtime(node):
            text = node.text.lower()
            for prefix in rt_prefix:
                if text.startswith(prefix + "."):
                    return True
            return False

        def is_standard_type(node):
            return node.unit.filename.endswith('__standard')

        def dump_nodes(root, filename):
            with open(filename, "w") as f:
                root.dump(file=f)

        def print_frame():
            callerframerecord = inspect.stack()[1]

            frame = callerframerecord[0]
            info = inspect.getframeinfo(frame)

            return "%s:%s:%s" % (info.filename, info.function, info.lineno)


        for u in self.__units:
            if u.root is None:
                self.__console_msg("Could not parse %s\n" % f, mode="error")
                for diag in u.diagnostics:
                    self.__provider.log('  {}'.format(diag), mode="error")
                    return

            if dump:
                dump_nodes(u.root, "%s.dump" % u.root.unit.filename)

            self.__provider.log("Parsing file %s..." % u.root.unit.filename)
            for node in u.root.findall(lal.Identifier):
                parent = node.parent
                if parent and parent.is_a(lal.AttributeRef, lal.AspectAssoc, lal.PragmaNode, lal.PragmaArgumentAssoc):
                    continue

                if node.p_is_defining:
                    try:
                        ref = node.p_enclosing_defining_name.p_basic_decl#.p_canonical_part
                        #print "Defining ref canonical: %s for %s" % (ref, node)
                        loc_node = node
                    except Exception as ex:
                        self.__provider.log("%s: %s" % (print_frame(), node))
                        self.__provider.log("%s: %s" % (print_frame(), ex.args[0]), mode="error")
                        continue
                else:
                    try:
                    #    ref = node.p_referenced_decl()
                        ref = node.p_xref().p_basic_decl#.p_canonical_part
                        if ref is None:
                            self.__provider.log("%s has no referenced_decl..." % node, mode="error")
                            continue

                        loc_node = ref
                    except Exception as ex:
                        self.__provider.log("%s: %s" % (print_frame(), node), mode="error")
                        self.__provider.log("%s: %s" % (print_frame(), ex.args[0]), mode="error")
                        print node.p_xref()
                        print dir(node.p_xref())
                        continue

                if ref is not None:
                    loc = file_location(loc_node)
                    if ref.is_a(lal.BasePackageDecl, lal.GenericPackageInstantiation, lal.PackageBody, lal.GenericPackageDecl):
                        if not runtime_pkg(ref):
                            token_type = "package"
                    elif ref.is_a(lal.SubpBody, lal.SubpDecl, lal.ExprFunction, lal.ConcreteFormalSubpDecl):
                        if not from_runtime(ref):
                            token_type = "subprogram"
                    elif ref.is_a(lal.ObjectDecl, lal.ForLoopVarDecl, lal.ParamSpec, lal.ComponentDecl):
                        if not from_runtime(ref):
                            token_type = "object"
                    elif ref.is_a(lal.NumberDecl):
                        if not from_runtime(ref):
                            token_type = "constant"
                    elif ref.is_a(lal.TypeDecl, lal.SubtypeDecl):
                        if not is_standard_type(ref):
                            token_type = "type"
                    elif ref.is_a(lal.EnumLiteralDecl):
                        if not is_standard_type(ref):
                            token_type = "literal"
                    else:
                        self.__provider.log("Can't add %s is a %s - %s" % (ref, ref.kind_name, loc), mode="error")
                        continue

                    add_node(loc, node, token_catalog[token_type])
                else:
                    self.__provider.log("%s ref is None - Defining: %s..." % (node, node.p_is_defining), mode="error")

            for node in u.root.findall(lal.LibraryItem):
                if node.f_item.is_a(lal.SubpBody):
                    self.__file_map[node.unit.filename] = "main"
                elif node.f_item.is_a(lal.BasePackageDecl, lal.GenericPackageDecl, lal.GenericPackageInstantiation, lal.PackageBody):
                    loc = file_location(node.f_item.p_canonical_part)
                    if loc not in catalog.keys():
                        self.__provider.log("Package defintion not found in catalog - %s:%s" % (loc, catalog.keys()))
                        continue
                    token = catalog[loc]["token"]
                    self.__file_map[node.unit.filename] = token
                else:
                    self.__provider.log("This LibraryItem is not recognized - %s:%s" % (node.unit.filename, node.f_item))

        return catalog