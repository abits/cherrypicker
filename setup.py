from setuptools import setup, find_packages

setup(
    name='cherrypicker',
    version='0.1',
    url='https://bitbucket.org/cmartel/cherrypicker',
    license='LICENSE.txt',
    author='Chris Martel',
    keywords='tv shows guide web',
    author_email='chris@codeways.org',
    description='Gather stuff from the interwebs.',
    long_description=open('README.txt').read(),
    install_requires=[
        'BeautifulSoup >= 3.2.1',
        'SQLAlchemy >= 0.7.9',
        'distribute'
      ],
    packages=find_packages(),
    zip_safe=False,
    entry_points={
        'console_scripts' : [
            'cherrypicker = cherrypicker.console.main'
        ]
    }
    )
