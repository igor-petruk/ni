import logging
import os
import subprocess
import glob
import utils
import common

class CppStaticLibrary(common.SuccessfulBuildResult):
    def __init__(self, archive_path, lflags, pkg_deps):
        self.archive_path = archive_path
        self.lflags = lflags
        self.pkg_deps = pkg_deps

    def __repr__(self):
        return "lib(%s, %s, %s)" % (self.archive_path, self.lflags, self.pkg_deps)

class CppStaticBinary(common.SuccessfulBuildResult, common.ExecutableBuildResult):
    def __init__(self, binary_path):
        self.binary_path = binary_path
    
    def GetExecutablePath(self):
        return self.binary_path

    def __repr__(self):
        return "bin(%s)" % (self.binary_path,)

class CppStaticLibraryBuilder(object):
    def __init__(self, compilation_database, pkg_config, threading_manager):
        self.threading_manager = threading_manager
        self.compilation_database = compilation_database
        self.pkg_config = pkg_config
    
    def Build(self, context, target_name):
        target = context.targets[target_name]
        env = target.GetModuleDefinition().GetEnv()
        logging.info("Env %s", env)
        cflags = env["cflags"]

        pkg_config_deps = env["pkg_config"]
        pkg_config_cflags = self.pkg_config.GetFlags(
                tuple(pkg_config_deps), cflags=True)
        
        sources = self._ResolveSources(target)
        logging.info("Sources %s", sources)
        
        if not os.path.exists(target.GetTargetObjDir()):
            os.makedirs(target.GetTargetObjDir())
        
        output_files = []
        executor = self.threading_manager.GetThreadPool("modules")
        futures = {}
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
            result = executor.submit(utils.RunProcess, args)
            futures[source] = result
        
        errors = []

        for source, future in futures.items():
            result, out, err = future.result()
            if result != 0:
                errors.append(common.FailedBuildResult(err.decode()))
        
        if errors:
            return [common.FailedBuildResult("Cannot build "+target.GetName(),
                    errors)]
        elif output_files:
            module_parent_dir = os.path.dirname(
                    os.path.join(target.GetOutDir(), target.GetName()))
            if not os.path.exists(module_parent_dir):
                os.makedirs(module_parent_dir)
            output_archive = os.path.join(module_parent_dir,
                    "lib%s.a" % (os.path.basename(target.GetName())))
            if os.path.exists(output_archive):
                os.remove(output_archive)
            args = []
            args.extend(["ar","rc"])
            args.extend([output_archive])
            args.extend(output_files)
            utils.RunProcess(args)
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
        env = target.GetModuleDefinition().GetEnv()
        for dep_name in env["deps"]:
            self._FillDependencies(context, dep_name, deps)
        logging.info("Collected deps for %s: %s", target_name, deps)
        binary_name = os.path.join(
                target.GetOutDir(), target.GetName())

        dep_errors = []
        for dep in deps:
            if not dep.ok():
                dep_errors.append(dep)

        if dep_errors:
            return [common.FailedBuildResult("Cannot build "+target.GetName(),
                    dep_errors)]

        args = []
        args.extend(["clang++"])
        pkg_deps = set()
        for dep in deps:
            args.extend([dep.archive_path])
            args.extend(dep.lflags)
            pkg_deps.update(dep.pkg_deps)
        args.extend(self.pkg_config.GetFlags(tuple(pkg_deps), libs=True))
        args.extend(["-o", binary_name])
        utils.RunProcess(args)
        return [CppStaticBinary(binary_name)]

    def _FillDependencies(self, context, target_name, deps):
        logging.info("Fill %r %r", context.build_results, deps)
        if target_name in context.build_results:
            target = context.targets[target_name]
            env = target.GetModuleDefinition().GetEnv()
            for dep_name in env["deps"]:
                self._FillDependencies(context, dep_name, deps)
            result = context.build_results[target_name]
            deps.extend(result) 

