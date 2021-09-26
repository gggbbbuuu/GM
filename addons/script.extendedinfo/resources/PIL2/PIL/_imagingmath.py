def __bootstrap__():
    global __bootstrap__, __loader__, __file__
    import os, sys , pkg_resources, imp
    __file__ = os.path.join(os.environ["KODI_ANDROID_LIBS"],  'lib_imagingmath.cpython-38-x86_64-linux-gnu.so')
    __loader__ = None; del __bootstrap__, __loader__
    imp.load_dynamic(__name__,__file__)
__bootstrap__()
