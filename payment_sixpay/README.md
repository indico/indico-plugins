# Indico 2 EPayment plugin for SIX Payment Services

Plugin for the Indico 2 event/conference management system, enabling support for SIX Payment Service.
This enables EPayment for users via the SixPay Saferpay Payment Page in conferences and other events.

Please see the [documentation](http://indico-sixpay.readthedocs.io/en/latest/) for details on installation, usage and maintenance.

## Overview

If the plugin is enabled, event participants can select the ``SixPay`` payment method during the EPayment checkout.
Payment is performed via the **Saferpay Payment Page**, an external service provided by SIX Payment Services.
The plugin handles the user interaction inside Indico, and the secure, asynchronous transaction with SIX Payment Services.

*This is plugin supports Indico 2.0.*
*The legacy plugin for Indico 1.2 is [hosted on github](https://github.com/maxfischer2781/indico_sixpay/tree/indico-1.2).*

## Installation

The plugin can be installed using standard Python package managers.
Note that at least `indico` 2.0 is required, and will be installed if it is missing.

**Note**: The `indico_sixpay` plugin must be installed for the python version running `indico`.

### Release Version

The latest release version is available for the default python package managers.
You can directly install the module using `pip`:

    pip install indico_sixpay

This can also be used to upgrade to a newer version:

    pip install indico_sixpay --upgrade

### Latest Version

Download this repository to any host running indico.
Install it by running:

    python setup.py install

After reloading the EPayment plugin in the Indico Admin panel, you can enable the SixPay service.

## Contributing, Feedback and Bug Reports

This project is hosted on [github](https://github.com/maxfischer2781/indico_sixpay).
If you encounter any bugs or missing features, please use the [bug tracker](https://github.com/maxfischer2781/indico_sixpay/issues) or submit a [pull request](https://github.com/maxfischer2781/indico_sixpay/pulls).

## Disclaimer

This plugin is in no way endorsed, supported or provided by SIX, Indico, KIT or any other service, provider or entity.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
