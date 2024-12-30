from setuptools import setup, find_packages

def readme():
    with open('README.md', 'r') as f:
        return f.read()

def requirements():
    with open('requirements.txt', 'r') as f:
        return f.read().splitlines()


def version():
    loc = dict()
    with open('metacatalog_client/__version__.py', 'r') as f:
        exec(f.read(), loc)
    return loc['__version__']

setup(
    name='metacatalog_client',
    version=version(),
    packages=find_packages(),
    license='GPLv3',
    description='Python client for MetaCatalog server instances',
    long_description=readme(),
    long_description_content_type='text/markdown',
    author='Mirko Mälicke',
    author_email='mirko.malicke@kit.edu',
    install_requires=requirements(),
)