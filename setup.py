from setuptools import setup, find_packages
# To use a consistent encoding
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

# Arguments marked as "Required" below must be included for upload to PyPI.

setup(
    name='i3-workscreen',  # Required

    # Versions should comply with PEP 440:
    # https://www.python.org/dev/peps/pep-0440/
    version='1.0.0',  # Required

    description='i3wm - assign workspaces to correct display outputs based on multi-scenario multi-monitor configuration',  # Required

    # This is an optional longer description of your project that represents
    # the body of text which users will see when they visit PyPI.
    # This field corresponds to the "Description" metadata field:
    # https://packaging.python.org/specifications/core-metadata/#description-optional
    long_description=long_description,  # Optional

    # This should be a valid link to your project's main homepage.
    #
    # This field corresponds to the "Home-Page" metadata field:
    # https://packaging.python.org/specifications/core-metadata/#home-page-optional
    url='https://github.com/fogine/i3-workscreen',  # Optional

    author='fogine',  # Optional
    license='MIT',
    python_requires='>=3.5.0',
    # Classifiers help users find your project by categorizing it.
    #
    # For a list of valid classifiers, see
    # https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[  # Optional
        # How mature is this project? Common values are
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        'Development Status :: 3 - Alpha',
        'Intended Audience :: End Users/Desktop',
        'Operating System :: POSIX :: Linux',
        'Topic :: Desktop Environment :: Window Managers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.6',
    ],

    keywords='i3 workspace monitor',  # Optional

    packages=find_packages(exclude=['contrib', 'docs', 'tests']),  # Required

    # This field lists other packages that your project depends on to run.
    # Any package you put here will be installed by pip when your project is
    # installed, so they must be valid existing projects.
    #
    # For an analysis of "install_requires" vs pip's requirements files see:
    # https://packaging.python.org/en/latest/requirements.html
    install_requires=['python-xlib', 'i3ipc', 'jsonschema'],

    # The following would provide a command called `i3-workscreen` which
    # executes the function `main` from this package when invoked:
   entry_points = {
        'console_scripts': ['i3-workscreen = i3workscreen.i3workscreen:main'],
    },
    project_urls={  # Optional
        'Bug Reports': 'https://github.com/pypa/sampleproject/issues',
        'Source': 'https://github.com/fogine/i3-workscreen',
    },
    download_url='https://github.com/fogine/i3-workscreen/archive/1.0.0.tar.gz'
)
