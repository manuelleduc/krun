import subprocess
import os

from krun import ANSI_GREEN, ANSI_RESET

DIR = os.path.abspath(os.path.dirname(__file__))
ITERATIONS_RUNNER_DIR = os.path.abspath(os.path.join(DIR, "iteration_runners"))

class BaseVariant(object):

    def __init__(self, iterations_runner, entry_point):
        self.entry_point = entry_point
        self.iterations_runner = iterations_runner

    def run_exec(self, interpreter, benchmark, iterations, param):
        raise NotImplemented("abstract")

    def _run_exec(self, args, env=None):
        if os.environ.get("BENCH_DEBUG"):
            print("%s    DEBUG: cmdline='%s'%s" % (ANSI_GREEN, " ".join(args), ANSI_RESET))
            print("%s    DEBUG: env='%s'%s" % (ANSI_GREEN, env, ANSI_RESET))

        if os.environ.get("BENCH_DRYRUN") != None:
            print("%s    DEBUG: %s%s" % (ANSI_GREEN, "DRY RUN, SKIP", ANSI_RESET))
            return "[]"

        stdout, stderr = subprocess.Popen(
                args, stdout=subprocess.PIPE, env=env).communicate()
        return stdout

class GenericScriptingVariant(BaseVariant):
    def __init__(self, iterations_runner, entry_point):
        fp_iterations_runner = os.path.join(ITERATIONS_RUNNER_DIR, iterations_runner)
        BaseVariant.__init__(self, fp_iterations_runner, entry_point)

    def run_exec(self, interpreter, benchmark, iterations, param):
        script_path = os.path.join(benchmark, self.entry_point)
        args = [interpreter, self.iterations_runner, script_path, str(iterations), str(param)]
        return self._run_exec(args, env=None)

class JavaVariant(BaseVariant):
    def __init__(self, entry_point):
        BaseVariant.__init__(self, "IterationsRunner", entry_point)
        self.entry_point = entry_point

    def run_exec(self, interpreter, benchmark, iterations, param):
        args = [interpreter, self.iterations_runner, self.entry_point, str(iterations), str(param)]
        bench_dir = os.path.abspath(os.path.join(os.getcwd(), benchmark))

        # deal with CLASSPATH
        cur_classpath = os.environ.get("CLASSPATH", "")
        paths = cur_classpath.split(os.pathsep)
        paths.append(ITERATIONS_RUNNER_DIR)
        paths.append(bench_dir)

        new_env = os.environ.copy()
        new_env["CLASSPATH"] = os.pathsep.join(paths)

        return self._run_exec(args, new_env)


class PythonVariant(GenericScriptingVariant):
    def __init__(self, entrypoint):
        GenericScriptingVariant.__init__(self, "iterations_runner.py", entrypoint)

class LuaVariant(GenericScriptingVariant):
    def __init__(self, entrypoint):
        GenericScriptingVariant.__init__(self, "iterations_runner.lua", entrypoint)