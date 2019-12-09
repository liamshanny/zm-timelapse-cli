from setuptools import setup

setup(
    name='zm-timelapse',
    version='.1',
    py_modules=['timelapse_generator'],
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
        zm-timelapse=timelapse_generator:create_timelapse
    ''',
)
