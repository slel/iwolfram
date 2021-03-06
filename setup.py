from __future__ import print_function

import os
import sys
from distutils.core import setup
from setuptools.command.install import install
from distutils import log
# from IPython.utils.tempdir import TemporaryDirectory


import platform
import json
import os
import sys
import subprocess
import setuptools


def subdirs(root, file='*.*', depth=10):
    for k in range(depth):
        yield root + '*/' * k + file


# Reads the specific command line arguments

if "--help" in sys.argv:
    print('setup install|build --mma-exec <path to mathematica executable> --iwolfram-mathkernel-path <path to store the caller>')



def get_start_text(cmd):
    if not os.access(cmd, os.X_OK):
        return ""
    else:
        print("    command valid. Trying....")
    with subprocess.Popen(cmd,
                              bufsize=1,
                              stdout=subprocess.PIPE,
                              stdin=subprocess.PIPE) as pr:
        starttext = pr.communicate(timeout=5)[0].decode()
    return starttext

# As default, look first if wolfram mma is installed. Otherwise, use mathics.
wmmexec = None
if "--mma-exec" in sys.argv:
    idx = sys.argv.index("--mma-exec")
    sys.argv.pop(idx)
    candidate = sys.argv.pop(idx)
    print("trying ", candidate)
    try:
        starttext = get_start_text(candidate)
        if starttext[:11] == "Mathematica":
            print("Using Wolfram Mathematica")
            wmmexec = candidate
        if starttext[:7] == "Wolfram":
            print("Using Wolfram Script")
            wmmexec = candidate
        elif starttext[:8] == "\nMathics":
            print("Using Mathics")
            wmmexec = candidate
        elif starttext[:21] == "Welcome to Expreduce!":
            print("Using Expreduce")
            wmmexec = candidate
    except Exception:
        print(wmmexec  + " is not a valid interpreter. Looking for a valid one.")

if wmmexec is None:
    print("trying with MathKernel")
    candidates =  [os.path.join(path, 'MathKernel') for path in os.environ["PATH"].split(os.pathsep)]
    for candidate in candidates:
        try:
            starttext = get_start_text(candidate)
            if starttext[:11] == "Mathematica":
                print("MathKernel (Wolfram version) found at " + candidate)
                wmmexec = candidate
                break
        except Exception:
            continue

if wmmexec is None:
    print("trying with wolframscript")
    candidates =  [os.path.join(path, 'wolframscript') for path in os.environ["PATH"].split(os.pathsep)]
    for candidate in candidates:
        try:
            starttext = get_start_text(candidate)
            if starttext[:7] == "Wolfram":
                print("MathKernel (Wolfram version) found at " + candidate)
                wmmexec = candidate
                break
        except Exception:
            continue

if wmmexec is None:
    print("trying with Mathics")
    candidates =  [os.path.join(path, 'mathics') for path in os.environ["PATH"].split(os.pathsep)]
    for candidate in candidates:
        try:
            starttext = get_start_text(candidate)
            if starttext[:8] == "\nMathics":
                print("Mathics version found at " + candidate)
                wmmexec = candidate
                break
        except Exception:
            continue

if wmmexec is None:
    print("Couldn't find a Mathics/Mathematica interpreter.")
    sys.exit(-1)


def _is_root():
    try:
        return os.geteuid() == 0
    except AttributeError:
        return False  # assume not an admin on non-Unix platforms


class install_with_kernelspec(install):
    def run(self):
        import os
        global wmmexec
        if wmmexec[-13:] == "wolframscript":
            with open("wolfram_kernel/wmath.in") as f:
                script = f.read()

            with open("wolfram_kernel/wmath","w") as f:
                f.write("#!"+wmmexec+" -c\n")
                f.write(script)
            if platform.system() == "Linux":
                os.chmod("wolfram_kernel/wmath", 0o755)

            wmmexec = (setuptools.__path__)[0][:-10]  + "wolfram_kernel/wmath"


        user = '--user' in sys.argv or not _is_root()
        configfilestr = "# iwolfram configuration file\nmathexec = '{wolfram-caller-script-path}'\n\n"
        configfilestr = configfilestr.replace('{wolfram-caller-script-path}', wmmexec)
        with open('wolfram_kernel/config.py','w') as f:
            f.write(configfilestr)

        #Run the standard intallation
        install.run(self)

        def install_kernelspec(self):

            try:
                from jupyter_client.kernelspec import install_kernel_spec
            except ImportError:
                from IPython.kernel.kernelspec import install_kernel_spec


            from ipykernel.kernelspec import write_kernel_spec
            from jupyter_client.kernelspec import KernelSpecManager
            from wolfram_kernel.wolfram_kernel import WolframKernel
            kernel_json = WolframKernel.kernel_json
            kernel_js = WolframKernel.kernel_js
            kernel_spec_manager = KernelSpecManager()
            log.info('Writing kernel spec')
            kernel_spec_path = write_kernel_spec(overrides=kernel_json)
            with open(kernel_spec_path+"/kernel.js","w") as jsfile:
                 jsfile.write(kernel_js)

            log.info('Installing kernel spec')
            try:
                kernel_spec_manager.install_kernel_spec(
                    kernel_spec_path,
                    kernel_name=kernel_json['name'],
                        user=user)
            except:
                log.error('Failed to install kernel spec in ' + kernel_spec_path)
                kernel_spec_manager.install_kernel_spec(
                    kernel_spec_path,
                    kernel_name=kernel_json['name'],
                        user=not user)


        print("Installing kernel spec")
        #Build and Install the kernelspec
        install_kernelspec(self)
        log.info("Installing nbextension")
        from notebook.nbextensions import install_nbextension
        import os.path
        try:
            install_nbextension(os.path.join(os.path.dirname(__file__), 'nbmathics'),overwrite=True,)
            jup_nbex_exec = os.path.dirname(sys.executable) + "/" + "jupyter-nbextension"
            os.system(jup_nbex_exec + " install --system  nbmathics")
            os.system(jup_nbex_exec + "  enable --system --py  nbmathics")
        except:
            log.info("nbextension can not be installed")


setup(name='wolfram_kernel',
      version='0.11.3',
      description='A Wolfram Mathematica/mathics kernel for Jupyter/IPython',
      long_description='A Wolfram Mathematica/mathics kernel for Jupyter/IPython, based on MetaKernel',
      url='https://github.com/matera/iwolfram/tree/master/iwolfram',
      author='Juan Mauricio Matera',
      author_email='matera@fisica.unlp.edu.ar',
      packages=['wolfram_kernel','nbmathics'],
      cmdclass={'install': install_with_kernelspec},
      install_requires=['metakernel', 'mathics',],
      package_data={
          'wolfram_kernel': ['init.m','wmath',],
          'nbmathics': ['nbmathics/static/img/*.gif',
                        'nbmathics/static/css/*.css',
                        'nbmathics/static/*.js',
                        'nbmathics/static/js/*.js',
                        'nbmathics/static/js/innerdom/*.js',
                        'nbmathics/static/js/prototype/*.js',
                        'nbmathics/static/js/scriptaculous/*.js',
                        'nbmathics/static/js/tree/Three.js',
                        'nbmathics/static/js/tree/Detector.js',
                         ] + list(subdirs('media/js/mathjax/')),
      },
      classifiers = [
          'Framework :: IPython',
          'License :: OSI Approved :: BSD License',
          'Programming Language :: Python :: 3',
          'Programming Language :: Python :: 2',
          'Topic :: System :: Shells',
      ]
)
