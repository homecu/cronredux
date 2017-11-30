import os
from setuptools import setup, find_packages

README = 'README.md'
VERSION = os.environ.get('CRONREDUX_VERSION', 'dev-build')

with open('requirements.txt') as f:
    requirements = f.readlines()


def long_desc():
    try:
        import pypandoc
    except ImportError:
        with open(README) as f:
            return f.read()
    else:
        return pypandoc.convert(README, 'rst')


setup(
    name='cronredux',
    version=VERSION,
    description='A reimagined cron executor',
    author='HomeCU',
    author_email='developers@homecu.com',
    url='https://github.com/homecu/cronredux/',
    license='MIT',
    long_description=long_desc(),
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
