// This file is part of the Indico plugins.
// Copyright (C) 2002 - 2025 CERN
//
// The Indico plugins are free software; you can redistribute
// them and/or modify them under the terms of the MIT License;
// see the LICENSE file for more details.

import React from 'react';
import {Button, Loader, Dimmer, Message, Card} from 'semantic-ui-react';
import '../styles/ind_summarize_button.module.scss';

export default function SummaryPreview({loading, error, summaryHtml, saving, onSave}) {
  return (
    <>
      <Card raised fluid styleName="preview-card-wrapper">
        <Card.Content>
          {loading && (
            <Dimmer active inverted>
              <Loader>Loading summary...</Loader>
            </Dimmer>
          )}
          {error && (
            <Message negative>
              <Message.Header>Couldn't get a summary</Message.Header>
              <p>{error}</p>
            </Message>
          )}

          {/* show placeholder when no summary yet */}
          {!loading && !error && !summaryHtml && (
            <div styleName="placeholder-no-summary">No summary yet</div>
          )}

          {/* render summary HTML */}
          {summaryHtml && (
            <div styleName="preview-card" dangerouslySetInnerHTML={{__html: summaryHtml}} />
          )}
        </Card.Content>
      </Card>
      {summaryHtml && (
        <div style={{display: 'flex', gap: '0.5em', marginTop: '1em'}}>
          <Button primary onClick={onSave} disabled={saving}>
            {saving ? 'Saving…' : 'Save summary'}
          </Button>
        </div>
      )}
    </>
  );
}
