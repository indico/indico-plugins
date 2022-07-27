// This file is part of the Indico plugins.
// Copyright (C) 2002 - 2022 CERN
//
// The Indico plugins are free software; you can redistribute
// them and/or modify them under the terms of the MIT License;
// see the LICENSE file for more details.

import PropTypes from 'prop-types';
import React, {useEffect, useRef, useCallback} from 'react';
import {useFormState, useForm} from 'react-final-form';
import ReCAPTCHA from 'react-google-recaptcha';
import {Message} from 'semantic-ui-react';

import {FinalField} from 'indico/react/forms';
import {Translate} from 'indico/react/i18n';

import './Captcha.module.scss';

function CaptchaField({onChange, siteKey, reCaptchaRef}) {
  return <ReCAPTCHA sitekey={siteKey} onChange={onChange} ref={reCaptchaRef} />;
}

CaptchaField.propTypes = {
  onChange: PropTypes.func.isRequired,
  siteKey: PropTypes.string.isRequired,
  reCaptchaRef: PropTypes.object.isRequired,
};

export default function Captcha({name, settings}) {
  const {siteKey} = settings;
  const reCaptchaRef = useRef(null);
  const form = useForm();
  const {submitErrors} = useFormState({
    subscription: {
      submitErrors: true,
    },
  });

  const resetCaptcha = useCallback(() => {
    form.change(name, '');
    reCaptchaRef.current.reset();
  }, [form, name, reCaptchaRef]);

  useEffect(() => {
    // Reset the CAPTCHA if validation fails
    if (submitErrors && submitErrors[name]) {
      resetCaptcha();
    }
  }, [submitErrors, name, resetCaptcha]);

  return (
    <Message info style={{marginTop: 25}}>
      <Message.Header>
        <Translate>Confirm that you are not a robot</Translate> 🤖
      </Message.Header>
      <div>
        {!siteKey && (
          <div styleName="error">
            <Message error>
              <Translate>The Site key is not set. Please add it in the plugin settings.</Translate>
            </Message>
          </div>
        )}
        {siteKey && (
          <div className="ui form" styleName="captcha">
            <FinalField
              name={name}
              required
              component={CaptchaField}
              siteKey={siteKey}
              reCaptchaRef={reCaptchaRef}
            />
          </div>
        )}
      </div>
    </Message>
  );
}

Captcha.propTypes = {
  name: PropTypes.string,
  settings: PropTypes.object.isRequired,
};

Captcha.defaultProps = {
  name: 'captcha',
};
