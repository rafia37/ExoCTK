from distutils.extension import Extension
import glob

def get_extensions():
    cfiles = glob.glob('ExoCTK/pal/include/*.c')
    cfiles.remove('ExoCTK/pal/include/main_transmission.c')
    return [Extension(name='ExoCTK.pal._exotransmit_wrapper',
                      sources=['ExoCTK/pal/_exotransmit_wrapper.pyx']+cfiles,
                      include_dirs=['numpy', 'ExoCTK/pal/include'])]

def get_package_data():
    return {'ExoCTK.pal': ['include/*']}
