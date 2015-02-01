import utils


class PkgConfig(object):

    @utils.memoize(log=True)
    def GetFlags(self, packages_list, cflags=False, libs=False):
        if packages_list:
            args = []
            args.extend(["pkg-config"])
            if cflags:
                args.extend(["--cflags"])
            if libs:
                args.extend(["--libs"])
            args.extend(list(packages_list))
            _, out, _ = utils.RunProcess(args)
            return out.decode().strip().split(" ")
        else:
            return []
