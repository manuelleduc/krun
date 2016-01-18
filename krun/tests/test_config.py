from krun import LOGFILE_FILENAME_TIME_FORMAT
from krun.config import Config

import os
import pytest
import time
from distutils.spawn import find_executable


JAVA = find_executable("java")
from krun.tests import TEST_DIR

def touch(fname):
    with open(fname, 'a'):
        os.utime(fname, None)


def test_str():
    path = os.path.join(TEST_DIR, "example.krun")
    config = Config(path)
    assert config.text == str(config)

def test_eq():
    example_config = Config("krun/tests/example.krun")
    assert example_config == example_config
    assert not example_config == None
    assert not example_config == Config("krun/tests/quick.krun")


def test_log_filename(monkeypatch):
    example_config = Config("krun/tests/example.krun")
    tstamp = time.strftime(LOGFILE_FILENAME_TIME_FORMAT)
    assert example_config.log_filename(False) == "krun/tests/example" + "_" + tstamp + ".log"
    def mock_mtime(path):
        return 1445964109.9363003
    monkeypatch.setattr(os.path, 'getmtime', mock_mtime)
    tstamp = '20151027_164149'
    assert example_config.log_filename(True) == "krun/tests/example" + "_" + tstamp + ".log"


def test_read_config_from_file():
    path = "krun/tests/example.krun"
    config0 = Config(path)
    config1 = Config(None)
    config1.read_from_file(path)
    assert config0 == config1


def test_read_config_from_string():
    path = "krun/tests/example.krun"
    config0 = Config(path)
    config1 = Config(None)
    with open(path) as fp:
        config_string = fp.read()
        config1.read_from_string(config_string)
        assert config0 == config1


def test_read_corrupt_config_from_string():
    path = "krun/tests/corrupt.krun"
    config = Config(None)
    with pytest.raises(Exception):
        with open(path) as fp:
            config_string = fp.read()
            config.read_from_string(config_string)

@pytest.mark.skipif(JAVA is None, reason="No Java found")
def test_config_init():
    path = "examples/example.krun"
    config = Config(path)
    assert config is not None
    assert config.BENCHMARKS == {"dummy": 1000, "nbody": 1000}
    assert config.N_EXECUTIONS == 2
    assert config.SKIP == []
    assert config.MAIL_TO == []
    assert config.ITERATIONS_ALL_VMS == 5
    assert config.HEAP_LIMIT == 2097152


def test_read_corrupt_config():
    path = "krun/tests/corrupt.krun"
    with pytest.raises(Exception):
        Config(path)


def test_results_filename():
    example = os.path.join(TEST_DIR, "example.krun")
    touch(example)
    example_config = Config(example)
    # not exact match due to absolute path
    assert example_config.results_filename().endswith("example_results.json.bz2")


def test_skip0001():
    config = Config("krun/tests/skips.krun")
    expected = ["*:PyPy:*",
                "*:CPython:*",
                "*:Hotspot:*",
                "*:Graal:*",
                "*:LuaJIT:*",
                "*:HHVM:*",
                "*:JRubyTruffle:*",
                "*:V8:*",
    ]
    for triplet in expected:
        assert config.should_skip(triplet)
    assert config.should_skip("nbody:HHVM:default-php")
    assert not config.should_skip("nbody:MYVM:default-php")


def test_skip0002():
    config = Config()
    config.SKIP = ["mybench:CPython:default-python"]

    assert config.should_skip("mybench:CPython:default-python")
    assert not config.should_skip("myotherbench:CPython:default-python")
    assert not config.should_skip("mybench:PyPy:default-python")
    assert not config.should_skip("mybench:CPython:special-python")


def test_skip0003():
    config = Config()
    config.SKIP = ["*:CPython:default-python"]

    assert config.should_skip("mybench:CPython:default-python")
    assert config.should_skip("myotherbench:CPython:default-python")
    assert not config.should_skip("mybench:PyPy:default-python")
    assert not config.should_skip("mybench:CPython:special-python")


def test_skip0004():
    config = Config()
    config.SKIP = ["mybench:*:default-python"]

    assert config.should_skip("mybench:CPython:default-python")
    assert not config.should_skip("myotherbench:CPython:default-python")
    assert config.should_skip("mybench:PyPy:default-python")
    assert not config.should_skip("mybench:CPython:special-python")

def test_skip0005():
    config = Config()
    config.SKIP = ["mybench:CPython:*"]

    assert config.should_skip("mybench:CPython:default-python")
    assert not config.should_skip("myotherbench:CPython:default-python")
    assert not config.should_skip("mybench:PyPy:default-python")
    assert config.should_skip("mybench:CPython:special-python")


def test_skip0006():
    config = Config()
    config.SKIP = ["*:*:*"]

    assert config.should_skip("mybench:CPython:default-python")
    assert config.should_skip("myotherbench:CPython:default-python")
    assert config.should_skip("mybench:PyPy:default-python")
    assert config.should_skip("mybench:CPython:special-python")


def test_skip0007():
    config = Config()

    with pytest.raises(ValueError) as e:
        config.should_skip("wobble")

    assert e.value.message == "bad benchmark key: wobble"

def test_skip0008():
    config = Config()
    config.SKIP = ["*:SomeVM:*", "fasta:JRubyTruffle:default-ruby"]

    assert config.should_skip("fasta:JRubyTruffle:default-ruby")

def test_skip0009():
    config = Config()
    config.SKIP = ["*:SomeVM:*",
                   "fasta:JRubyTruffle:default-ruby",
                   "bench:*:*",
                   "bench:vm:skipvariant",
                   "*:*:skipvariant",
                   ]

    assert config.should_skip("fasta:JRubyTruffle:default-ruby")
    assert not config.should_skip("fasta:JRubyTruffle:default-ruby2")
    assert config.should_skip("bench:lala:hihi")
    assert config.should_skip("bench:lala:hihi2")
    assert not config.should_skip("bench1:lala:hihi")
    assert config.should_skip("bench1:lala:skipvariant")
    assert config.should_skip("bench1:lala2:skipvariant")

def test_skip0010():
    config = Config()
    config.SKIP = ["*:SomeVM:*",
                   "fasta:JRubyTruffle:default-ruby",
                   "bench:*:*",
                   "bench:vm:skipvariant",
                   "*:*:skipvariant",
                   "*:*:*",  # everything should be skipped due to this
                   ]

    import uuid
    def rand_str():
        return uuid.uuid4().hex

    for i in xrange(25):
        key = "%s:%s:%s" % tuple([rand_str() for x in xrange(3)])
        assert config.should_skip(key)

def test_temp_read_pause0001():
    config = Config()
    assert config.TEMP_READ_PAUSE == 60  # default

def test_temp_read_pause0002():
    config = Config(os.path.join(TEST_DIR, "example.krun"))
    assert config.TEMP_READ_PAUSE == 1