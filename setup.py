from setuptools import find_packages, setup

setup(
    name='glocklib',
    packages=find_packages(include=['glocklib']),
    version='0.1.0',
    description='A library for handy discord.py utilities.',
    author='DarkKronicle',
    license='MPLv2',
    install_requires=[
        'discord~=1.0.1',
        'discord.py~=1.7.2',
        'discord-ext-menus @ git+https://github.com/Rapptz/discord-ext-menus',
        'asyncpg~=0.23.0',
        'toml~=0.10.2',
    ],
)
