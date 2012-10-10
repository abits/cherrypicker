from distutils.core import setup

setup(
    name='cherrypicker',
    version='0.1',
    packages=['cherrypicker', 'cherrypicker.test',
              'cherrypicker.test.cherrypicker'],
    url='https://bitbucket.org/cmartel/cherrypicker',
    license='LICENSE',
    author='Chris Martel',
    author_email='chris@codeways.org',
    description='Gather stuff from the interwebs.',
    long_description=open('README').read(),
    install_requires=[
        'BeautifulSoup' >= '3.2.1'
        'SQLAlchemy' >= '0.7.9'
        'pygtk' >= '2.24.0'
      ],
    package_data={
        'share/doc/': ['data/*.txt'],
        },
    )
