// This file is part of the Indico plugins.
// Copyright (C) 2002 - 2022 CERN
//
// The Indico plugins are free software; you can redistribute
// them and/or modify them under the terms of the MIT License;
// see the LICENSE file for more details.

import PropTypes from 'prop-types';
import React, {useState, useEffect, useRef, useCallback} from 'react';
import {useFormState, useForm} from 'react-final-form';
import ReCAPTCHA from 'react-google-recaptcha';
import {Message, Form} from 'semantic-ui-react';

import {FinalField} from 'indico/react/forms';
import {Translate} from 'indico/react/i18n';

import './Captcha.module.scss';

export default function Captcha({name, settings: {siteKey}, wtf}) {
  return wtf ? (
    <WTFCaptcha name={name} siteKey={siteKey} />
  ) : (
    <FinalCaptcha name={name} siteKey={siteKey} />
  );
}

Captcha.propTypes = {
  name: PropTypes.string,
  wtf: PropTypes.bool,
  settings: PropTypes.shape({
    siteKey: PropTypes.string.isRequired,
  }).isRequired,
};

Captcha.defaultProps = {
  name: 'captcha',
  wtf: false,
};

function CaptchaField({onChange, siteKey, reCaptchaRef}) {
  return <ReCAPTCHA sitekey={siteKey} onChange={onChange} ref={reCaptchaRef} />;
}

CaptchaField.propTypes = {
  onChange: PropTypes.func.isRequired,
  siteKey: PropTypes.string.isRequired,
  reCaptchaRef: PropTypes.object,
};

CaptchaField.defaultProps = {
  reCaptchaRef: undefined,
};

function WTFCaptcha({name, siteKey}) {
  const [response, setResponse] = useState('');

  return (
    <Message info style={{marginTop: 0}}>
      <Message.Header>
        <Translate>Confirm that you are not a robot</Translate> 🤖
      </Message.Header>
      <div>
        <Form as="div" styleName="captcha">
          <input type="hidden" name={name} value={response} />
          <CaptchaField siteKey={siteKey} onChange={setResponse} />
        </Form>
      </div>
    </Message>
  );
}

WTFCaptcha.propTypes = {
  name: PropTypes.string.isRequired,
  siteKey: PropTypes.string.isRequired,
};

function FinalCaptcha({name, siteKey}) {
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
        <Form as="div" styleName="captcha">
          <FinalField
            name={name}
            required
            component={CaptchaField}
            siteKey={siteKey}
            reCaptchaRef={reCaptchaRef}
          />
        </Form>
      </div>
    </Message>
  );
}

FinalCaptcha.propTypes = {
  name: PropTypes.string.isRequired,
  siteKey: PropTypes.string.isRequired,
};
