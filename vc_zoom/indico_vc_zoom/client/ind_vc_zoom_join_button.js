// This file is part of the Indico plugins.
// Copyright (C) 2020 - 2024 CERN and ENEA
//
// The Indico plugins are free software; you can redistribute
// them and/or modify them under the terms of the MIT License;
// see the LICENSE file for more details.

import React from 'react';
import ReactDOM from 'react-dom';

import JoinButton from './JoinButton';

import './ind_vc_zoom_join_button.scss';

/** Custom element wrapper for a React-managed JoinButton */
customElements.define(
  'ind-vc-zoom-join-button',
  class extends HTMLElement {
    connectedCallback() {
      const classes = this.getAttribute('classes');
      const href = this.getAttribute('href');
      const target = this.getAttribute('target');
      const icon = this.getAttribute('icon');
      const caption = this.getAttribute('caption');
      const description = this.getAttribute('description');
      const altHostUrl = this.getAttribute('alt-host-url');
      const meetingTitle = this.getAttribute('meeting-title');
      const meetingDataHtml = this.getAttribute('meeting-data-html');

      ReactDOM.render(
        <JoinButton
          classes={classes}
          href={href}
          target={target}
          icon={icon}
          caption={caption}
          description={description}
          altHostUrl={altHostUrl}
          meetingTitle={meetingTitle}
          meetingDataHtml={meetingDataHtml}
        />,
        this
      );
    }
  }
);
