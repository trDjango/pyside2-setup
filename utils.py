import sys
import os
import re
import stat
import errno
import time
import shutil
import subprocess
import fnmatch
import itertools
import popenasync
# There is no urllib.request in Python2
try:
    import urllib.request as urllib
except ImportError:
    import urllib

from distutils import log
from distutils.errors import DistutilsOptionError
from distutils.errors import DistutilsSetupError
from distutils.spawn import spawn
from distutils.spawn import DistutilsExecError

try:
    WindowsError
except NameError:
    WindowsError = None


def has_option(name):
    try:
        sys.argv.remove('--%s' % name)
        return True
    except ValueError:
        pass
    return False


def option_value(name):
    for index, option in enumerate(sys.argv):
        if option == '--' + name:
            if index+1 >= len(sys.argv):
                raise DistutilsOptionError(
                    'The option %s requires a value' % option)
            value = sys.argv[index+1]
            sys.argv[index:index+2] = []
            return value
        if option.startswith('--' + name + '='):
            value = option[len(name)+3:]
            sys.argv[index:index+1] = []
            return value
    env_val = os.getenv(name.upper().replace('-', '_'))
    return env_val


def filter_match(name, patterns):
    for pattern in patterns:
        if pattern is None:
            continue
        if fnmatch.fnmatch(name, pattern):
            return True
    return False


def update_env_path(newpaths):
    paths = os.environ['PATH'].lower().split(os.pathsep)
    for path in newpaths:
        if not path.lower() in paths:
            log.info("Inserting path \"%s\" to environment" % path)
            paths.insert(0, path)
            os.environ['PATH'] = path + os.pathsep + os.environ['PATH']


def winsdk_setenv(platform_arch, build_type):
    from distutils.msvc9compiler import VERSION as MSVC_VERSION
    from distutils.msvc9compiler import Reg
    from distutils.msvc9compiler import HKEYS
    from distutils.msvc9compiler import WINSDK_BASE

    sdk_version_map = {
        "v6.0a": 9.0,
        "v6.1": 9.0,
        "v7.0": 9.0,
        "v7.0a": 10.0,
        "v7.1": 10.0
    }

    log.info("Searching Windows SDK with MSVC compiler version %s" % MSVC_VERSION)
    setenv_paths = []
    for base in HKEYS:
        sdk_versions = Reg.read_keys(base, WINSDK_BASE)
        if sdk_versions:
            for sdk_version in sdk_versions:
                installationfolder = Reg.get_value(WINSDK_BASE + "\\" +
                    sdk_version, "installationfolder")
                productversion = Reg.get_value(WINSDK_BASE + "\\" +
                    sdk_version, "productversion")
                setenv_path = os.path.join(installationfolder, os.path.join(
                    'bin', 'SetEnv.cmd'))
                if not os.path.exists(setenv_path):
                    continue
                if not sdk_version in sdk_version_map:
                    continue
                if sdk_version_map[sdk_version] != MSVC_VERSION:
                    continue
                setenv_paths.append(setenv_path)
    if len(setenv_paths) == 0:
        raise DistutilsSetupError(
            "Failed to find the Windows SDK with MSVC compiler version %s"
                % MSVC_VERSION)
    for setenv_path in setenv_paths:
        log.info("Found %s" % setenv_path)

    # Get SDK env (use latest SDK version installed on system)
    setenv_path = setenv_paths[-1]
    log.info("Using %s " % setenv_path)
    build_arch = "/x86" if platform_arch.startswith("32") else "/x64"
    build_type = "/Debug" if build_type.lower() == "debug" else "/Release"
    setenv_cmd = [setenv_path, build_arch, build_type]
    setenv_env = get_environment_from_batch_command(setenv_cmd)
    setenv_env_paths = os.pathsep.join([setenv_env[k] for k in setenv_env if k.upper() == 'PATH']).split(os.pathsep)
    setenv_env_without_paths = dict([(k, setenv_env[k]) for k in setenv_env if k.upper() != 'PATH'])

    # Extend os.environ with SDK env
    log.info("Initializing Windows SDK env...")
    update_env_path(setenv_env_paths)
    for k in sorted(setenv_env_without_paths):
        v = setenv_env_without_paths[k]
        log.info("Inserting \"%s = %s\" to environment" % (k, v))
        os.environ[k] = v
    log.info("Done initializing Windows SDK env")


def find_vcdir(version):
    """
    This is the customized version of distutils.msvc9compiler.find_vcvarsall method
    """
    from distutils.msvc9compiler import VS_BASE
    from distutils.msvc9compiler import Reg
    from distutils import log
    vsbase = VS_BASE % version
    try:
        productdir = Reg.get_value(r"%s\Setup\VC" % vsbase,
                                   "productdir")
    except KeyError:
        productdir = None

    # trying Express edition
    if productdir is None:
        try:
            from distutils.msvc9compiler import VSEXPRESS_BASE
        except ImportError:
            pass
        else:
            vsbase = VSEXPRESS_BASE % version
            try:
                productdir = Reg.get_value(r"%s\Setup\VC" % vsbase,
                                           "productdir")
            except KeyError:
                productdir = None
                log.debug("Unable to find productdir in registry")

    if not productdir or not os.path.isdir(productdir):
        toolskey = "VS%0.f0COMNTOOLS" % version
        toolsdir = os.environ.get(toolskey, None)

        if toolsdir and os.path.isdir(toolsdir):
            productdir = os.path.join(toolsdir, os.pardir, os.pardir, "VC")
            productdir = os.path.abspath(productdir)
            if not os.path.isdir(productdir):
                log.debug("%s is not a valid directory" % productdir)
                return None
        else:
            log.debug("Env var %s is not set or invalid" % toolskey)
    if not productdir:
        log.debug("No productdir found")
        return None
    return productdir


def init_msvc_env(platform_arch, build_type):
    from distutils.msvc9compiler import VERSION as MSVC_VERSION

    log.info("Searching MSVC compiler version %s" % MSVC_VERSION)
    vcdir_path = find_vcdir(MSVC_VERSION)
    if not vcdir_path:
        raise DistutilsSetupError(
            "Failed to find the MSVC compiler version %s on your system." % MSVC_VERSION)
    else:
        log.info("Found %s" % vcdir_path)

    log.info("Searching MSVC compiler %s environment init script" % MSVC_VERSION)
    if platform_arch.startswith("32"):
        vcvars_path = os.path.join(vcdir_path, "bin", "vcvars32.bat")
    else:
        vcvars_path = os.path.join(vcdir_path, "bin", "vcvars64.bat")
        if not os.path.exists(vcvars_path):
            vcvars_path = os.path.join(vcdir_path, "bin", "amd64", "vcvars64.bat")
            if not os.path.exists(vcvars_path):
                vcvars_path = os.path.join(vcdir_path, "bin", "amd64", "vcvarsamd64.bat")

    if not os.path.exists(vcvars_path):
        # MSVC init script not found, try to find and init Windows SDK env
        log.error(
            "Failed to find the MSVC compiler environment init script (vcvars.bat) on your system.")
        winsdk_setenv(platform_arch, build_type)
        return
    else:
        log.info("Found %s" % vcvars_path)

    # Get MSVC env
    log.info("Using MSVC %s in %s" % (MSVC_VERSION, vcvars_path))
    msvc_arch = "x86" if platform_arch.startswith("32") else "amd64"
    log.info("Getting MSVC env for %s architecture" % msvc_arch)
    vcvars_cmd = [vcvars_path, msvc_arch]
    msvc_env = get_environment_from_batch_command(vcvars_cmd)
    msvc_env_paths = os.pathsep.join([msvc_env[k] for k in msvc_env if k.upper() == 'PATH']).split(os.pathsep)
    msvc_env_without_paths = dict([(k, msvc_env[k]) for k in msvc_env if k.upper() != 'PATH'])

    # Extend os.environ with MSVC env
    log.info("Initializing MSVC env...")
    update_env_path(msvc_env_paths)
    for k in sorted(msvc_env_without_paths):
        v = msvc_env_without_paths[k]
        log.info("Inserting \"%s = %s\" to environment" % (k, v))
        os.environ[k] = v
    log.info("Done initializing MSVC env")


def copyfile(src, dst, force=True, vars=None, force_copy_symlink=False):
    if vars is not None:
        src = src.format(**vars)
        dst = dst.format(**vars)

    if not os.path.exists(src) and not force:
        log.info("**Skiping copy file %s to %s. Source does not exists." % (src, dst))
        return

    if not os.path.islink(src) or force_copy_symlink:
        log.info("Copying file %s to %s." % (src, dst))
        shutil.copy2(src, dst)
    else:
        linkTargetPath = os.path.realpath(src)
        if os.path.dirname(linkTargetPath) == os.path.dirname(src):
            linkTarget = os.path.basename(linkTargetPath)
            linkName = os.path.basename(src)
            currentDirectory = os.getcwd()
            try:
                targetDir = dst if os.path.isdir(dst) else os.path.dirname(dst)
                os.chdir(targetDir)
                if os.path.exists(linkName):
                    os.remove(linkName)
                log.info("Symlinking %s -> %s in %s." % (linkName, linkTarget, targetDir))
                os.symlink(linkTarget, linkName)
            except OSError:
                log.error("%s -> %s: Error creating symlink" % (linkName, linkTarget))
            finally:
                os.chdir(currentDirectory)
        else:
            log.error("%s -> %s: Can only create symlinks within the same directory" % (src, linkTargetPath))

    return dst


def makefile(dst, content=None, vars=None):
    if vars is not None:
        if content is not None:
            content = content.format(**vars)
        dst = dst.format(**vars)

    log.info("Making file %s." % (dst))

    dstdir = os.path.dirname(dst)
    if not os.path.exists(dstdir):
        os.makedirs(dstdir)

    f = open(dst, "wt")
    if content is not None:
        f.write(content)
    f.close()


def copydir(src, dst, filter=None, ignore=None, force=True, recursive=True, vars=None,
            dir_filter_function=None, force_copy_symlinks=False):

    if vars is not None:
        src = src.format(**vars)
        dst = dst.format(**vars)
        if filter is not None:
            for i in range(len(filter)):
                filter[i] = filter[i].format(**vars)
        if ignore is not None:
            for i in range(len(ignore)):
                ignore[i] = ignore[i].format(**vars)

    if not os.path.exists(src) and not force:
        log.info("**Skiping copy tree %s to %s. Source does not exists. filter=%s. ignore=%s." % \
            (src, dst, filter, ignore))
        return []

    log.info("Copying tree %s to %s. filter=%s. ignore=%s." % \
        (src, dst, filter, ignore))

    names = os.listdir(src)

    results = []
    errors = []
    for name in names:
        srcname = os.path.join(src, name)
        dstname = os.path.join(dst, name)
        try:
            if os.path.isdir(srcname):
                if dir_filter_function and not dir_filter_function(name, src, srcname):
                    continue
                if recursive:
                    results.extend(
                        copydir(srcname, dstname, filter, ignore, force, recursive,
                                vars, dir_filter_function, force_copy_symlinks))
            else:
                if (filter is not None and not filter_match(name, filter)) or \
                    (ignore is not None and filter_match(name, ignore)):
                    continue
                if not os.path.exists(dst):
                    os.makedirs(dst)
                results.append(copyfile(srcname, dstname, True, vars, force_copy_symlinks))
        # catch the Error from the recursive copytree so that we can
        # continue with other files
        except shutil.Error as err:
            errors.extend(err.args[0])
        except EnvironmentError as why:
            errors.append((srcname, dstname, str(why)))
    try:
        if os.path.exists(dst):
            shutil.copystat(src, dst)
    except OSError as why:
        if WindowsError is not None and isinstance(why, WindowsError):
            # Copying file access times may fail on Windows
            pass
        else:
            errors.extend((src, dst, str(why)))
    if errors:
        raise EnvironmentError(errors)
    return results


def rmtree(dirname):
    def handleRemoveReadonly(func, path, exc):
        excvalue = exc[1]
        if func in (os.rmdir, os.remove) and excvalue.errno == errno.EACCES:
            os.chmod(path, stat.S_IRWXU| stat.S_IRWXG| stat.S_IRWXO) # 0777
            func(path)
        else:
            raise
    shutil.rmtree(dirname, ignore_errors=False, onerror=handleRemoveReadonly)

def run_process_output(args, initial_env=None):
    if initial_env is None:
        initial_env = os.environ
    stdOut = subprocess.Popen(args, env = initial_env, universal_newlines = 1,
                              stdout=subprocess.PIPE).stdout
    result = []
    for rawLine in stdOut.readlines():
        line = rawLine if sys.version_info >= (3,) else rawLine.decode('utf-8')
        result.append(line.rstrip())
    return result

def run_process(args, initial_env=None):
    def _log(buffer, checkNewLine=False):
        endsWithNewLine = False
        if buffer.endswith('\n'):
            endsWithNewLine = True
        if checkNewLine and buffer.find('\n') == -1:
            return buffer
        lines = buffer.splitlines()
        buffer = ''
        if checkNewLine and not endsWithNewLine:
            buffer = lines[-1]
            lines = lines[:-1]
        for line in lines:
            log.info(line.rstrip('\r'))
        return buffer
    _log("Running process in {0}: {1}".format(os.getcwd(), " ".join([(" " in x and '"{0}"'.format(x) or x) for x in args])))

    if sys.platform != "win32":
        try:
            spawn(args)
            return 0
        except DistutilsExecError:
            return -1

    shell = False
    if sys.platform == "win32":
        shell = True

    if initial_env is None:
        initial_env = os.environ

    proc = popenasync.Popen(args,
        stdin = subprocess.PIPE,
        stdout = subprocess.PIPE,
        stderr = subprocess.STDOUT,
        universal_newlines = 1,
        shell = shell,
        env = initial_env)

    log_buffer = None;
    while proc.poll() is None:
        log_buffer = _log(proc.read_async(wait=0.1, e=0))
    if log_buffer:
        _log(log_buffer)

    proc.wait()
    return proc.returncode


def get_environment_from_batch_command(env_cmd, initial=None):
    """
    Take a command (either a single command or list of arguments)
    and return the environment created after running that command.
    Note that if the command must be a batch file or .cmd file, or the
    changes to the environment will not be captured.

    If initial is supplied, it is used as the initial environment passed
    to the child process.
    """

    def validate_pair(ob):
        try:
            if not (len(ob) == 2):
                print("Unexpected result: %s" % ob)
                raise ValueError
        except:
            return False
        return True

    def consume(iter):
        try:
            while True: next(iter)
        except StopIteration:
            pass

    if not isinstance(env_cmd, (list, tuple)):
        env_cmd = [env_cmd]
    # construct the command that will alter the environment
    env_cmd = subprocess.list2cmdline(env_cmd)
    # create a tag so we can tell in the output when the proc is done
    tag = 'Done running command'
    # construct a cmd.exe command to do accomplish this
    cmd = 'cmd.exe /E:ON /V:ON /s /c "{env_cmd} && echo "{tag}" && set"'.format(**vars())
    # launch the process
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, env=initial)
    # parse the output sent to stdout
    lines = proc.stdout
    if sys.version_info[0] > 2:
        # make sure the lines are strings
        make_str = lambda s: s.decode()
        lines = map(make_str, lines)
    # consume whatever output occurs until the tag is reached
    consume(itertools.takewhile(lambda l: tag not in l, lines))
    # define a way to handle each KEY=VALUE line
    handle_line = lambda l: l.rstrip().split('=',1)
    # parse key/values into pairs
    pairs = map(handle_line, lines)
    # make sure the pairs are valid
    valid_pairs = filter(validate_pair, pairs)
    # construct a dictionary of the pairs
    result = dict(valid_pairs)
    # let the process finish
    proc.communicate()
    return result


def regenerate_qt_resources(src, pyside_rcc_path, pyside_rcc_options):
    names = os.listdir(src)
    for name in names:
        srcname = os.path.join(src, name)
        if os.path.isdir(srcname):
            regenerate_qt_resources(srcname,
                                    pyside_rcc_path,
                                    pyside_rcc_options)
        elif srcname.endswith('.qrc'):
            # Replace last occurence of '.qrc' in srcname
            srcname_split = srcname.rsplit('.qrc', 1)
            dstname = '_rc.py'.join(srcname_split)
            if os.path.exists(dstname):
                log.info('Regenerating %s from %s' % \
                    (dstname, os.path.basename(srcname)))
                run_process([pyside_rcc_path,
                             pyside_rcc_options,
                             srcname, '-o', dstname])


def back_tick(cmd, ret_err=False):
    """ Run command `cmd`, return stdout, or stdout, stderr if `ret_err`

    Roughly equivalent to ``check_output`` in Python 2.7

    Parameters
    ----------
    cmd : str
        command to execute
    ret_err : bool, optional
        If True, return stderr in addition to stdout.  If False, just return
        stdout

    Returns
    -------
    out : str or tuple
        If `ret_err` is False, return stripped string containing stdout from
        `cmd`.  If `ret_err` is True, return tuple of (stdout, stderr) where
        ``stdout`` is the stripped stdout, and ``stderr`` is the stripped
        stderr.

    Raises
    ------
    Raises RuntimeError if command returns non-zero exit code
    """
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = proc.communicate()
    if not isinstance(out, str):
        # python 3
        out = out.decode()
        err = err.decode()
    retcode = proc.returncode
    if retcode is None:
        proc.terminate()
        raise RuntimeError(cmd + ' process did not terminate')
    if retcode != 0:
        raise RuntimeError(cmd + ' process returned code %d\n*** %s' %
                           (retcode, err))
    out = out.strip()
    if not ret_err:
        return out
    return out, err.strip()


OSX_OUTNAME_RE = re.compile(r'\(compatibility version [\d.]+, current version '
                        '[\d.]+\)')

def osx_get_install_names(libpath):
    """ Get OSX library install names from library `libpath` using ``otool``

    Parameters
    ----------
    libpath : str
        path to library

    Returns
    -------
    install_names : list of str
        install names in library `libpath`
    """
    out = back_tick('otool -L ' + libpath)
    libs = [line for line in out.split('\n')][1:]
    return [OSX_OUTNAME_RE.sub('', lib).strip() for lib in libs]


OSX_RPATH_RE = re.compile(r"path (.+) \(offset \d+\)")

def osx_get_rpaths(libpath):
    """ Get rpath load commands from library `libpath` using ``otool``

    Parameters
    ----------
    libpath : str
        path to library

    Returns
    -------
    rpaths : list of str
        rpath values stored in ``libpath``

    Notes
    -----
    See ``man dyld`` for more information on rpaths in libraries
    """
    lines = back_tick('otool -l ' + libpath).split('\n')
    ctr = 0
    rpaths = []
    while ctr < len(lines):
        line = lines[ctr].strip()
        if line != 'cmd LC_RPATH':
            ctr += 1
            continue
        assert lines[ctr + 1].strip().startswith('cmdsize')
        rpath_line = lines[ctr + 2].strip()
        match = OSX_RPATH_RE.match(rpath_line)
        if match is None:
            raise RuntimeError('Unexpected path line: ' + rpath_line)
        rpaths.append(match.groups()[0])
        ctr += 3
    return rpaths


def osx_fix_rpaths_for_library(library_path, qt_lib_dir):
    """ Adds required rpath load commands to given library.

    This is a necessary post-installation step, to allow loading PySide modules without setting
    DYLD_LIBRARY_PATH or DYLD_FRAMEWORK_PATH.
    The CMake rpath commands which are added at build time  are used only for testing (make check),
    and they are stripped once the equivalent of make install is executed (except for shiboken,
    which currently uses CMAKE_INSTALL_RPATH_USE_LINK_PATH, which might be necessary to remove in
    the future).

    Parameters
    ----------
    library_path : str
        path to library for which to set rpaths.
    qt_lib_dir : str
        rpath to installed Qt lib directory.
    """

    install_names = osx_get_install_names(library_path)
    existing_rpath_commands = osx_get_rpaths(library_path)

    needs_loader_path = False
    for install_name in install_names:
        # Absolute path, skip it.
        if install_name[0] == '/':
            continue

        # If there are dynamic library install names that contain @rpath tokens, we will
        # provide an rpath load command with the value of "@loader_path". This will allow loading
        # dependent libraries from within the same directory as 'library_path'.
        if install_name[0] == '@':
            needs_loader_path = True
            break

    if needs_loader_path and "@loader_path" not in existing_rpath_commands:
        back_tick('install_name_tool -add_rpath {rpath} {library_path}'.format(
                  rpath="@loader_path", library_path=library_path))

    # If the library depends on a Qt library, add an rpath load comment pointing to the Qt lib
    # directory.
    osx_add_qt_rpath(library_path, qt_lib_dir, existing_rpath_commands, install_names)

def osx_add_qt_rpath(library_path, qt_lib_dir,
                     existing_rpath_commands = [], library_dependencies = []):
    """ Adds an rpath load command to the Qt lib directory if necessary

    Checks if library pointed to by 'library_path' has Qt dependencies, and adds an rpath load
    command that points to the Qt lib directory (qt_lib_dir).
    """
    if not existing_rpath_commands:
        existing_rpath_commands = osx_get_rpaths(library_path)

    # Return early if qt rpath is already present.
    if qt_lib_dir in existing_rpath_commands:
        return

    # Check if any library dependencies are Qt libraries (hacky).
    if not library_dependencies:
        library_dependencies = osx_get_install_names(library_path)

    needs_qt_rpath = False
    for library in library_dependencies:
        if 'Qt' in library:
            needs_qt_rpath = True
            break

    if needs_qt_rpath:
        back_tick('install_name_tool -add_rpath {rpath} {library_path}'.format(
                  rpath=qt_lib_dir, library_path=library_path))

def download_and_extract_7z(fileurl, target):
    """ Downloads 7z file from fileurl and extract to target  """

    print("Downloading fileUrl %s " % fileurl)
    info = ""
    try:
        localfile, info = urllib.urlretrieve(fileurl)
    except:
        print("Error downloading %r : %r" % (fileurl, info))
        raise RuntimeError(' Error downloading ' + fileurl)

    try:
        outputDir = "-o" + target
        print("calling 7z x %s %s" % (localfile, outputDir))
        subprocess.call(["7z", "x", "-y", localfile, outputDir])
    except:
        raise RuntimeError(' Error extracting ' + localfile)
