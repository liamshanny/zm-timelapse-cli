from setuptools import setup

setup(
    name='zm-timelapse',
    version='.1',
    py_modules=['main'],
    install_requires=[
        'Click',
    ],
    url='',
    license='MIT',
    author='lshanny',
    author_email='shanny.liam@gmail.com',
    description='',
    entry_points='''
        [console_scripts]
        zm-timelapse=main:create_timelapse
    ''',
)
