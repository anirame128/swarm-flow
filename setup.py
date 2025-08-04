from setuptools import setup, find_packages

# Read the README file
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name='swarmflow',
    version='0.3.4',
    description='SwarmFlow: A distributed multi-agent orchestration framework',
    long_description=long_description,
    long_description_content_type="text/markdown",
    author='Anirudh Ramesh',
    author_email='anirudhramesh2021@gmail.com',
    maintainer='Anirudh Ramesh',
    maintainer_email='anirudhramesh2021@gmail.com',
    url='https://github.com/anirame128/swarmflow',
    download_url='https://github.com/anirame128/swarmflow/archive/refs/tags/v0.3.4.tar.gz',
    packages=find_packages(),
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Programming Language :: Python :: 3.13',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Scientific/Engineering :: Artificial Intelligence',
        'Topic :: System :: Distributed Computing',
    ],
    install_requires=[
        'requests>=2.25.0',
        'opentelemetry-api>=1.20.0',
        'opentelemetry-sdk>=1.20.0',
    ],
    python_requires='>=3.8',
    keywords='ai, agents, orchestration, workflow, llm, multi-agent, distributed, observability',
    project_urls={
        'Bug Reports': 'https://github.com/anirame128/swarmflow/issues',
        'Source': 'https://github.com/anirame128/swarmflow',
        'Documentation': 'https://github.com/anirame128/swarmflow#readme',
        'Changelog': 'https://github.com/anirame128/swarmflow/blob/main/CHANGELOG.md',
    },
    include_package_data=True,
    zip_safe=False,
) 