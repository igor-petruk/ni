import logging
import os
import subprocess
import glob

def RunProcess(args):
    logging.info("Running %s", args)
    process = subprocess.Popen(
            args, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)
    out, err = process.communicate()
    if out:
        logging.info("Output '%s'", out.decode())
    if err:
        logging.info("Error '%s'", err.decode())
    result = process.wait()
    logging.info("Result %s", result)
    return result, out, err

def GetPkgConfigFlags(packages_list, cflags=False, libs=False):
    if packages_list:
        args = []
        args.extend(["pkg-config"])
        if cflags:
            args.extend(["--cflags"])
        if libs:
            args.extend(["--libs"])
        args.extend(list(packages_list))
        _, out, _ = RunProcess(args)
        return out.decode().strip().split(" ")
    else:
        return []

class CppStaticLibrary(object):
    def __init__(self, archive_path, lflags, pkg_deps):
        self.archive_path = archive_path
        self.lflags = lflags
        self.pkg_deps = pkg_deps

    def __repr__(self):
        return "lib(%s, %s, %s)" % (self.archive_path, self.lflags, self.pkg_deps)

class CppStaticBinary(object):
    def __init__(self, binary_path):
        self.binary_path = binary_path

    def __repr__(self):
        return "bin(%s)" % (self.binary_path,)

class CppStaticLibraryBuilder(object):
    def __init__(self, compilation_database):
        self.compilation_database = compilation_database
    
    def Build(self, context, target_name):
        target = context.targets[target_name]
        env = target.GetConfig().GetEnv()
        logging.info("Env %s", env)
        cflags = env["cflags"]

        pkg_config_deps = env["pkg_config"]
        pkg_config_cflags = GetPkgConfigFlags(pkg_config_deps, cflags=True)
        
        sources = self._ResolveSources(target)
        logging.info("Sources %s", sources)
        
        if not os.path.exists(target.GetTargetObjDir()):
            os.makedirs(target.GetTargetObjDir())
        
        output_files = []
        for source in sources:

            args = []
            args.extend(["clang++"])
            args.extend(cflags)
            args.extend(pkg_config_cflags)
            args.extend(["-I", target.GetRootDir()])
            args.extend(["-c"])
            args.extend([source])
            output_file = os.path.join(
                    target.GetTargetObjDir(),
                    os.path.basename(source)+".o")
            output_files.append(output_file)
            args.extend(["-o", output_file])
            self.compilation_database.SubmitCommand(source, " ".join(args))
            RunProcess(args)
        if output_files:
            module_parent_dir = os.path.dirname(
                    os.path.join(target.GetOutDir(), target.GetName()))
            if not os.path.exists(module_parent_dir):
                os.makedirs(module_parent_dir)
            output_archive = os.path.join(module_parent_dir,
                    "lib%s.a" % (os.path.basename(target.GetName())))
            args = []
            args.extend(["ar","rc"])
            args.extend([output_archive])
            args.extend(output_files)
            RunProcess(args)
            return [CppStaticLibrary(output_archive,
                    env["lflags"], set(pkg_config_deps))]
        else:
            return []


    def _ResolveSources(self, target):
        sources_dir = target.GetModuleDir()
        sources = glob.glob(os.path.join(sources_dir, "*.cc"))
        return sources

class CppBinaryBuilder(CppStaticLibraryBuilder):
    def Build(self, context, target_name):
        self_result = super(CppBinaryBuilder, self).Build(
                context, target_name)
        deps = self_result

        target = context.targets[target_name]
        env = target.GetConfig().GetEnv()
        for dep_name in env["deps"]:
            self._FillDependencies(context, dep_name, deps)
        logging.info("Collected deps for %s: %s", target_name, deps)
        binary_name = os.path.join(
                target.GetOutDir(), target.GetName())
        args = []
        args.extend(["clang++"])
        pkg_deps = set()
        for dep in deps:
            args.extend([dep.archive_path])
            args.extend(dep.lflags)
            pkg_deps.update(dep.pkg_deps)
        args.extend(GetPkgConfigFlags(pkg_deps, libs=True))
        args.extend(["-o", binary_name])
        RunProcess(args)
        return CppStaticBinary(binary_name)

    def _FillDependencies(self, context, target_name, deps):
        logging.info("Fill %r %r", context.build_results, deps)
        if target_name in context.build_results:
            target = context.targets[target_name]
            env = target.GetConfig().GetEnv()
            for dep_name in env["deps"]:
                self._FillDependencies(context, dep_name, deps)
            result = context.build_results[target_name]
            deps.extend(result) 

