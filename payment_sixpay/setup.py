import os
from setuptools import setup, find_packages

repo_base_dir = os.path.abspath(os.path.dirname(__file__))
# pull in the packages metadata
package_about = {}
with open(os.path.join(repo_base_dir, "indico_sixpay", "__about__.py")) as about_file:
    exec(about_file.read(), package_about)

setup(
    name=package_about['__title__'],
    version=package_about['__version__'],
    description=package_about['__summary__'],
    long_description=package_about['__doc__'].strip(),
    author=package_about['__author__'],
    author_email=package_about['__email__'],
    url=package_about['__url__'],
    entry_points={
        'indico.plugins': {
            'payment_sixpay = indico_sixpay.plugin:SixpayPaymentPlugin'
        }
    },
    packages=find_packages(),
    package_data={'indico_sixpay': ['templates/*.html']},
    install_requires=['requests', 'indico>=2.0', 'iso4217'],
    license='GPLv3+',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Plugins',
        'Environment :: Web Environment',
        'Intended Audience :: Science/Research',
        'Intended Audience :: System Administrators',
        'Intended Audience :: Other Audience',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2.7',
        'Topic :: Communications :: Conferencing',
        'Topic :: Internet :: WWW/HTTP :: WSGI :: Application',
    ],
    zip_safe=False,
    keywords='indico epayment six sixpay plugin',
)
