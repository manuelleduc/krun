# Various CPU related abstrations

import time
import os
import sys
import difflib
from collections import OrderedDict
from krun.util import fatal, collect_cmd_output


class BasePlatform(object):
    CPU_TEMP_MANDATORY_WAIT = 1
    CPU_TEMP_POLL_FREQ = 5
    CPU_TEMP_POLLS_BEFORE_MELTDOWN = 12  #  * 5 = one minute

    def __init__(self):
        self.audit = OrderedDict()

        # We will be looking for changes in the dmesg output.
        # In the past we have seen benchmarks trigger performance-related
        # errors and warnings in the Linux dmesg. If that happens, we
        # really want to know about it!
        self.current_dmesg = self._collect_dmesg_lines()

    def _collect_dmesg_lines(self):
        return collect_cmd_output("dmesg").split("\n")

    def check_dmesg_for_changes(self):
        new_dmesg = self._collect_dmesg_lines()
        lines = [x for x in difflib.unified_diff(
            self.current_dmesg, new_dmesg, "old", "new", lineterm="")]

        if lines:
            # dmesg changed!
            print("dmesg seems to have changed! Diff follows:\n")
            print("\n".join(lines))
            print("")
            self.current_dmesg = new_dmesg

    def wait_until_cpu_cool(self):
        time.sleep(BasePlatform.CPU_TEMP_MANDATORY_WAIT)
        msg_shown = False
        trys = 0
        while True:
            cool, reason = self.has_cpu_cooled()
            if cool:
                break

            # if we get here, CPU is too hot!
            if not msg_shown:
                print("CPU is running hot.")
                print(reason)
                sys.stdout.write("Waiting to cool")
                sys.stdout.flush()
                msg_shown = True

            trys += 1
            if trys >= BasePlatform.CPU_TEMP_POLLS_BEFORE_MELTDOWN:
                print("")
                fatal("CPU didn't cool down")

            time.sleep(BasePlatform.CPU_TEMP_POLL_FREQ)
            sys.stdout.write(".")
            sys.stdout.flush()
        print("")

    # When porting to a new platform, implement the following:
    def take_cpu_temp_readings(self):
        raise NotImplementedError("abstract")

    def set_base_cpu_temps(self):
        raise NotImplementedError("abstract")

    def has_cpu_cooled(self):
        raise NotImplementedError("abstract")

    def check_cpu_throttled(self):
        raise NotImplementedError("abstract")

    # And you may want to extend this
    def collect_audit(self):
        self.audit["uname"] = collect_cmd_output("uname")
        self.audit["dmesg"] = collect_cmd_output("dmesg")

class LinuxPlatform(BasePlatform):
    THERMAL_BASE = "/sys/class/thermal/"
    CPU_GOV_FILE = "/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor"

    # Temperature files under /sys measure in millidegrees
    # https://www.kernel.org/doc/Documentation/thermal/sysfs-api.txt
    THRESHOLD = 1000  # therefore one degree

    def __init__(self):
        self.base_cpu_temps = None
        self.zones = self._find_thermal_zones()
        BasePlatform.__init__(self)

    def _find_thermal_zones(self):
        return [x for x in os.listdir(LinuxPlatform.THERMAL_BASE) if
                x.startswith("thermal_zone")]

    def set_base_cpu_temps(self):
        self.base_cpu_temps = self.take_cpu_temp_readings()

    def _read_zone(self, zone):
        fn = os.path.join(LinuxPlatform.THERMAL_BASE, zone, "temp")
        with open(fn, "r") as fh:
            return int(fh.read())

    def take_cpu_temp_readings(self):
        return [self._read_zone(z) for z in self.zones]

    def has_cpu_cooled(self):
        """returns tuple: bool_cool * str_reason_if_false

        bool_cool is True if the CPU has cooled (or was never hot).
        """

        if self.base_cpu_temps is None:
            fatal("Base CPU temperature was not set")

        readings = self.take_cpu_temp_readings()
        for i in range(len(self.base_cpu_temps)):
            if readings[i] - self.base_cpu_temps[i] - self.THRESHOLD > 0:
                reason = "Zone 1 started at %d but is now %d" % \
                    (self.base_cpu_temps[i], readings[i])
                return (False, reason)  # one or more sensor too hot
        return (True, None)

    def check_cpu_throttled(self):
        with open(LinuxPlatform.CPU_GOV_FILE, "r") as fh:
            v = fh.read().strip()

        if v != "performance":
            fatal("Expected 'performance' got '%s'. "
                   "Use cpufreq-set from the cpufrequtils package" % v)

    def collect_audit(self):
        BasePlatform.collect_audit(self)

        # Extra CPU info, some not in dmesg. E.g. CPU cache size.
        self.audit["cpuinfo"] = collect_cmd_output("cat /proc/cpuinfo")

class DebianLinuxPlatform(LinuxPlatform):
    def collect_audit(self):
        LinuxPlatform.collect_audit(self)
        self.audit["packages"] = collect_cmd_output("dpkg-query -l")
        self.audit["debian_version"] = collect_cmd_output("cat /etc/debian_version")

def platform():
    if os.path.exists("/etc/debian_version"):
        return DebianLinuxPlatform()
    else:
        fatal("I don't have support for your platform")
