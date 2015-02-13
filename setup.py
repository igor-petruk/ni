from setuptools import setup, find_packages
setup(name='ni',
    version='1.0',
    url="https://github.com/igor-petruk/ni",
    author='Igor Petruk',
    author_email='igor.petrouk@gmail.com',
    packages=find_packages(),
    include_package_data=True,
    entry_points={
        'console_scripts': [
            'ni = nibt.client:Main',
            'nid = nibt.server:Main',
        ]
    }
)
