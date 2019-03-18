import os
import sys

import GPS
import gps_utils


def initialize_project_plugin():
    """
    Entry point hook to GPS
    """
    global menu_item
    try:
        d = GPS.Project.root().file().path
        sys.path.append(os.path.dirname(os.path.realpath(d)))

        import obfuscator

        class GPSProvider(obfuscator.BaseProvider):

            def log(self, msg, mode=None):
                if mode is not None:
                    GPS.Console("Messages").write(msg + "\n", mode=mode)
                else:
                    GPS.Console("Messages").write(msg + "\n")

            def get_source_list(self):
                ro_proj = GPS.Project.root()
                return [src.path for src in ro_proj.sources()]

            def get_dest_location(self):
                dest = self.get_obj_locations()[0]

                if not os.path.isdir(dest):
                    self.log("Destination path %s is invalid. Defaulting to current directory %s..." % (dest, os.getcwd()), mode="error")
                    dest = os.getcwd()

                return dest

            def get_src_locations(self):
                return GPS.Project.root().sources()

            def get_obj_locations(self):
                return GPS.Project.root().object_dirs()

            def get_proj_location(self):
                return GPS.Project.root().file().name()

            def get_scenario_vars(self):
                return GPS.Project.root().scenario_variables()

            def get_target(self):
                return GPS.get_target()

            def get_runtime(self):
                return GPS.get_runtime()

        provider = GPSProvider()
        obf = obfuscator.Obfuscator(provider)
        menu_item = gps_utils.make_interactive(
                        callback=lambda: obf.do_obfuscate(),
                        name="Obfuscate",
                        toolbar='main',
                        menu='/Code/Obfuscate',
                        description='Create obfuscated project')
    except Exception as inst:
        GPS.Console("Messages").write(inst.args[0] + "\n", mode="error")

def finalize_project_plugin():
    global menu_item

    menu_item[0].destroy_ui()
    del globals()[pluginRef, menu_item]
