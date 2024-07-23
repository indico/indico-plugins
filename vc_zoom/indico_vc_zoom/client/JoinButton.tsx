// This file is part of the Indico plugins.
// Copyright (C) 2020 - 2024 CERN

// The Indico plugins are free software; you can redistribute
// them and/or modify them under the terms of the MIT License;
// see the LICENSE file for more details.

import staticURL from 'indico-url:plugin_vc_zoom.static';

import React, {useState} from 'react';
import {Button, ButtonGroup, Confirm, Icon, Label, Popup, SemanticICONS} from 'semantic-ui-react';

import {Translate} from 'indico/react/i18n';
import {handleAxiosError, indicoAxios} from 'indico/utils/axios';

import './JoinButton.module.scss';

interface OptionsButtonProps {
  url: string;
  onMadeAltHost: () => void;
}

/** A dropdown button which shows additional actions, such as the possibility to take over as meeting co-host */
function OptionsButton({url, onMadeAltHost}: OptionsButtonProps) {
  const [isConfirmOpen, setConfirmOpen] = useState(false);
  const [state, setState] = useState('idle');

  async function makeAlternativeHost() {
    setConfirmOpen(false);
    try {
      setState('submitting');
      await indicoAxios.post(url);
      setState('success');
    } catch (error) {
      handleAxiosError(error);
    }
    window.setTimeout(() => {
      onMadeAltHost();
      setState('idle');
    }, 3000);
  }

  const trigger = (
    <Button
      disabled={state !== 'idle'}
      title={Translate.string('Actions you can perform on your Zoom meeting')}
      color={state === 'success' ? 'green' : undefined}
      loading={state === 'submitting'}
      size="mini"
      icon={state !== 'submitting'}
    >
      {
        {
          idle: <Icon fitted name="cog" />,
          submitting: null,
          success: <Icon fitted name="checkmark" />,
        }[state]
      }
    </Button>
  );

  return (
    <>
      <Popup trigger={trigger} hoverable on="click">
        <Button
          size="mini"
          title={Translate.string('You will become an alternative host of this Zoom meeting')}
          onClick={() => setConfirmOpen(true)}
        >
          <Icon name="star" />
          <Translate>Make me alternative host</Translate>
        </Button>
      </Popup>
      <Confirm
        header={Translate.string('Make me an alternative host')}
        content={Translate.string('Are you sure you want to be added as an alternative host?')}
        open={isConfirmOpen}
        onConfirm={makeAlternativeHost}
        onCancel={() => setConfirmOpen(false)}
      />
    </>
  );
}

interface JoinButtonProps {
  classes: string;
  href: string;
  target: string;
  icon: SemanticICONS;
  caption: string;
  description: string;
  altHostUrl: string;
  meetingTitle: string | undefined;
  meetingDataHtml: string | undefined;
}

/** The join button, which can optionally include an alternative host URL (creates menu) as well as a pop-up */
export default function JoinButton({
  classes,
  href,
  target,
  icon,
  caption,
  description,
  altHostUrl = '',
  meetingTitle,
  meetingDataHtml,
}: JoinButtonProps) {
  const [isAltHost, setAltHost] = useState(!altHostUrl);

  let buttons = (
    <>
      <Button size="mini" title={description} className={classes} href={href} target={target}>
        <Icon name={icon} />
        {caption}
      </Button>
      {!isAltHost ? (
        <OptionsButton
          url={altHostUrl}
          onMadeAltHost={() => {
            setAltHost(true);
          }}
        />
      ) : null}
    </>
  );

  const labeledButton = (
    <Button as="div" labelPosition="left" size="mini">
      <Label as="a" size="mini" image title="Zoom" pointing="right" styleName="button-label">
        <img src={staticURL({filename: 'images/zoom_icon.svg'})} />
      </Label>
    </Button>
  );

  buttons = meetingDataHtml ? (
    <>
      <Popup hoverable trigger={labeledButton}>
        <h4>{meetingTitle}</h4>
        {/* the HTML data is generated server-side from the Zoom API output and should be in a sanitized state */}
        <div dangerouslySetInnerHTML={{__html: meetingDataHtml}} />
      </Popup>
      {buttons}
    </>
  ) : (
    buttons
  );

  return <ButtonGroup size="mini">{buttons}</ButtonGroup>;
}
