import os
from setuptools import setup, find_packages

README = 'README.md'

cronredux_version = os.path.join(
    os.path.abspath(os.path.dirname(__file__)), 'cronredux', '__init__.py')

exec(compile(open(cronredux_version, 'r').read(), cronredux_version, 'exec'))

with open('requirements.txt') as f:
    requirements = f.readlines()

long_description = None
with open('README.md', 'r') as fh:
    long_description = fh.read()

setup(
    name='cronredux',
    version=VERSION,
    description='A reimagined cron executor',
    author='HomeCU',
    author_email='developers@homecu.com',
    url='https://github.com/homecu/cronredux/',
    license='MIT',
    long_description=long_description,
    long_description_content_type='text/markdown',
    packages=find_packages(),
    test_suite='test',
    install_requires=requirements,
    entry_points={
        'console_scripts': ['cronredux=cronredux.main:main'],
    },
    include_package_data=True,
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
    ]
)
