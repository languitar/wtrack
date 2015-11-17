from setuptools import setup

setup(
    name='wtrack',
    version='0.1-dev',

    install_requires=['pandas', 'matplotlib', 'numpy', 'icalendar'],

    scripts=['wtrack'],

    author='Johannes Wienke',
    author_email='languitar@semipol.de',
    url='https://github.com/languitar/wtrack',
    description='A command-line based work time tracker with overtime '
                'calculation. A fixed amount of work peer weekday is the'
                'assumed model.',

    license='LGPLv3+',
    keywords=['work', 'timetracking', 'overtime'],
    classifiers=[
        'Programming Language :: Python :: 3',
        'Topic :: Utilities',
        'License :: OSI Approved :: GNU Lesser General Public License v3 or later (LGPLv3+)'
    ])
