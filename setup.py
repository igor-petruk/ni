from distutils.core import setup
setup(name='ni',
    version='1.0',
    url="https://github.com/igor-petruk/ni",
    author='Igor Petruk',
    author_email='igor.petrouk@gmail.com',
    packages=['nibt'],
    package_dir={'':'src'},
    package_data={
        'nibt': [
            'data/*.js',
            'data/*.html', 
            'data/*.css'
            ]
        },
    scripts=['src/ni','src/nid']
)
