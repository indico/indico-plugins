"""
++++++++++++++++++++++++++++++++++++++++++++++++++
``indico_sixpay`` - SIX EPayment Plugin for Indico
++++++++++++++++++++++++++++++++++++++++++++++++++

.. image:: https://readthedocs.org/projects/indico_sixpay/badge/?version=latest
    :target: http://indico-sixpay.readthedocs.io/en/latest/?badge=latest
    :alt: Documentation

.. image:: https://img.shields.io/pypi/v/indico_sixpay.svg
    :alt: Available on PyPI
    :target: https://pypi.python.org/pypi/indico_sixpay/

.. image:: https://img.shields.io/github/license/maxfischer2781/indico_sixpay.svg
    :alt: License
    :target: https://github.com/maxfischer2781/indico_sixpay/blob/master/LICENSE

.. image:: https://img.shields.io/github/commits-since/maxfischer2781/indico_sixpay/v2.0.0.svg
    :alt: Repository
    :target: https://github.com/maxfischer2781/indico_sixpay/tree/master

Plugin for the Indico event management system to use EPayment via SIX Payment services.

Quick Guide
-----------

To enable the plugin, it must be installed for the python version running ``indico``.

.. code:: bash

    python -m pip install indico_sixpay

Once installed, it can be enabled in the administrator and event settings.
Configuration uses the same options for global defaults and event specific overrides.

Disclaimer
----------

This plugin is in no way endorsed, supported or provided by SIX, Indico or any other service, provider or entity.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE
WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
DEALINGS IN THE SOFTWARE.
"""
__title__ = 'indico_sixpay'
__summary__ = 'Indico EPayment Plugin for SixPay services'
__url__ = 'https://github.com/maxfischer2781/indico_sixpay'

__version__ = '2.0.2'
__author__ = 'Max Fischer'
__email__ = 'maxfischer2781@gmail.com'
__copyright__ = '2017 - 2018 %s' % __author__
