// This file is part of the Indico plugins.
// Copyright (C) 2002 - 2022 CERN
//
// The Indico plugins are free software; you can redistribute
// them and/or modify them under the terms of the MIT License;
// see the LICENSE file for more details.

import generateCaptchaURL from 'indico-url:core.generate_captcha';

import PropTypes from 'prop-types';
import React, {useState, useEffect, useRef, useCallback} from 'react';
import {useFormState, useForm} from 'react-final-form';
import ReCAPTCHA from 'react-google-recaptcha';
import {Message, Button, Icon, Popup, Loader} from 'semantic-ui-react';

import {FinalField} from 'indico/react/forms';
import {Translate} from 'indico/react/i18n';
import {indicoAxios} from 'indico/utils/axios';

import './Captcha.module.scss';

function CaptchaField({onChange, siteKey, reCaptchaRef}) {
  return <ReCAPTCHA sitekey={siteKey} onChange={onChange} ref={reCaptchaRef} />;
}

CaptchaField.propTypes = {
  onChange: PropTypes.func.isRequired,
  siteKey: PropTypes.string.isRequired,
  reCaptchaRef: PropTypes.object.isRequired,
};

export default function Captcha({name}) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [siteKey, setSiteKey] = useState('');
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

  const fetchSiteKey = async () => {
    setLoading(true);
    setError(false);
    try {
      const {data} = await indicoAxios.get(generateCaptchaURL());
      setSiteKey(data.site_key);
    } catch (err) {
      setError(true);
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => fetchSiteKey(), []);

  useEffect(() => {
    // Reset the CAPTCHA if the validation fails
    if (submitErrors && submitErrors[name]) {
      resetCaptcha();
    }
  }, [submitErrors, name, resetCaptcha]);

  const reloadBtn = (
    <Popup
      content={Translate.string('Refresh CAPTCHA')}
      trigger={
        <Button icon type="button" onClick={() => fetchSiteKey().then(resetCaptcha)}>
          <Icon name="redo" />
        </Button>
      }
    />
  );

  return (
    <Message info style={{marginTop: 25}}>
      <Message.Header>
        <Translate>Confirm that you are not a robot</Translate> 🤖
      </Message.Header>
      <div>
        {loading && <Loader active inline="centered" />}
        {error && (
          <div styleName="error">
            <Message error>
              <Translate>Failed to load CAPTCHA, try refreshing it.</Translate>
            </Message>
            {reloadBtn}
          </div>
        )}
        {!error && !loading && !siteKey && (
          <div styleName="error">
            <Message error>
              <Translate>The Site key is not set. Please add it in the plugin settings.</Translate>
            </Message>
          </div>
        )}
        {!error && !loading && siteKey && (
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
};

Captcha.defaultProps = {
  name: 'captcha',
};
