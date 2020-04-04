from __future__ import unicode_literals

from setuptools import find_packages, setup


setup(
    name='indico-plugin-vc-zoom',
    version='0.2-dev',
    description='Zoom video-conferencing plugin for Indico',
    url='',
    license='MIT',
    author='Giovanni Mariano - ENEA',
    author_email='giovanni.mariano@enea.it',
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=[
        'indico>=2',
        'requests', 
        'PyJWT'
    ],
    classifiers=[
        'Environment :: Plugins',
        'Environment :: Web Environment',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2.7'
    ],
    entry_points={'indico.plugins': {'vc_zoom = indico_vc_zoom.plugin:ZoomPlugin'}}
)
