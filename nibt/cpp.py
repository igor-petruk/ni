import logging
import os
import subprocess
import glob

from nibt import common, utils

class CppStaticLibraryResult(common.SuccessfulBuildResult):
    def __init__(self, archive_path, lflags, pkg_deps):
        self.archive_path = archive_path
        self.lflags = lflags
        self.pkg_deps = pkg_deps

    def __repr__(self):
        return "lib(%s, %s, %s)" % (self.archive_path, self.lflags, self.pkg_deps)

class CppStaticBinaryResult(common.SuccessfulBuildResult, common.ExecutableBuildResult):
    def __init__(self, binary_path):
        self.binary_path = binary_path
    
    def GetExecutablePath(self):
        return self.binary_path

    def __repr__(self):
        return "bin(%s)" % (self.binary_path,)

class CppStaticLibraryBuilder(object):
    def __init__(self, compilation_database, pkg_config, threading_manager, configuration):
        self.threading_manager = threading_manager
        self.compilation_database = compilation_database
        self.pkg_config = pkg_config
        self.root_dir = configuration.GetExpandedDir("projects","root_dir")

    def Build(self, context, target_name):
        target = context.targets[target_name]
        definition = target.GetModuleDefinition()
        logging.info("Definition %s", definition)
        cflags = definition.cflags

        pkg_config_deps = definition.pkg_config
        pkg_config_cflags = self.pkg_config.GetFlags(
                tuple(pkg_config_deps), cflags=True)
        
        sources = self._ResolveSources(target)
        logging.info("Sources %s", sources)
        
        obj_dir = os.path.join(self.root_dir, "obj", os.path.dirname(target.GetName())) 

        if not os.path.exists(obj_dir):
            os.makedirs(obj_dir)
        
        output_files = []
        executor = self.threading_manager.GetThreadPool("modules")
        futures = {}
        for source in sources:
            args = []
            args.extend(["clang++"])
            args.extend(cflags)
            args.extend(pkg_config_cflags)
            args.extend(["-I", self.root_dir])
            args.extend(["-c"])
            args.extend([source])
            output_file = os.path.join(
                    obj_dir,
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
                    os.path.join(self.root_dir, "out", target.GetName()))
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
            return [CppStaticLibraryResult(output_archive,
                    definition.lflags, set(pkg_config_deps))]
        else:
            return []


    def _ResolveSources(self, target):
        module_definition = target.GetModuleDefinition()
        if module_definition.sources is None:
            logging.info("Sources is None for %s, using defailt convention", target)
            sources_prefix = os.path.join(self.root_dir, target.GetName())
            return [sources_prefix + ".cc"]
        else:
            module_dir = os.path.dirname(os.path.join(self.root_dir, target.GetName()))
            sources = []
            for pattern in module_definition.sources:
                full_pattern = os.path.join(module_dir, pattern)   
                expanded = glob.glob(full_pattern)
                logging.info("Sources pattern %s for %s expanded to %s", full_pattern, target, expanded) 
                sources.extend(expanded)
            return sources

class CppBinaryBuilder(CppStaticLibraryBuilder):
    def Build(self, context, target_name):
        deps = []
        target = context.targets[target_name]
        definition = target.GetModuleDefinition()
        for dep_name in definition.deps:
            self._FillDependencies(context, dep_name, deps)
        logging.info("Collected deps for %s: %s", target_name, deps)
        binary_name = os.path.join(
                self.root_dir, "out", target.GetName())

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

        if definition.binary_name:
            symlink_full_path = os.path.join(self.root_dir, "bin", definition.binary_name)
            logging.info("Symlinking %s to %s", binary_name, symlink_full_path)
            if not os.path.exists(os.path.dirname(symlink_full_path)):
                os.makedirs(os.path.dirname(symlink_full_path))
            if os.path.exists(symlink_full_path):
                os.remove(symlink_full_path)
            os.symlink(binary_name, symlink_full_path)

        return [CppStaticBinaryResult(binary_name)]

    def _FillDependencies(self, context, target_name, deps):
        logging.info("Fill %r %r", context.build_results, deps)
        if target_name in context.build_results:
            target = context.targets[target_name]
            definition = target.GetModuleDefinition()
            for dep_name in definition.deps:
                self._FillDependencies(context, dep_name, deps)
            result = context.build_results[target_name]
            deps.extend(result) 

