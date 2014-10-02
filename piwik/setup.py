from setuptools import setup, find_packages


setup(
    name='indico_piwik',
    version='0.1',
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    platforms='any',
    install_requires=[
        'indico>=1.9.1'
    ],
    entry_points={'indico.plugins': {'piwik = indico_piwik:PiwikPlugin'}}
)
