// This file is part of the Indico plugins.
// Copyright (C) 2002 - 2022 CERN
//
// The Indico plugins are free software; you can redistribute
// them and/or modify them under the terms of the MIT License;
// see the LICENSE file for more details.

import {registerPluginComponent} from 'indico/utils/plugins';

import Captcha from './Captcha';

registerPluginComponent('recaptcha', 'regformCaptcha', Captcha);
