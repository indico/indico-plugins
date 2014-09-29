from setuptools import setup, find_packages


setup(
    name='indico_statistics',
    version='0.1',
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    platforms='any',
    install_requires=[
        'indico>=1.9.1'
    ],
    entry_points={'indico.plugins': {'statistics = indico_statistics:StatisticsPlugin'}}
)
