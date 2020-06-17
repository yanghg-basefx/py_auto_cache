from setuptools import setup

setup(
    install_requires=['redis'],
    name='py_auto_cache',
    version='1.1.2',
    packages=['py_auto_cache', 'py_auto_cache.caches'],
    package_dir={'': 'lib'},
    url='',
    license='',
    author='yanghg',
    author_email='',
    description=''
)
