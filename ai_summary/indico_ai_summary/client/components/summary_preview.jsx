// This file is part of the Indico plugins.
// Copyright (C) 2002 - 2025 CERN
//
// The Indico plugins are free software; you can redistribute
// them and/or modify them under the terms of the MIT License;
// see the LICENSE file for more details.

import React from 'react';
import {Button, Loader, Dimmer, Segment, Message} from 'semantic-ui-react';
import '../styles/ind_summarize_button.module.scss';

export default function SummaryPreview({
  loading,
  error,
  summaryHtml,
  saving,
  onSave,
  onClear,
}) {
  return (
    <Segment basic style={{position: 'relative', minHeight: '250px'}}>
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
        <div styleName="placeholder-no-summary"
        >
          No summary yet
        </div>
      )}

      {/* render summary HTML */}
      {summaryHtml && (
        <div          
          styleName="preview-card"
          dangerouslySetInnerHTML={{__html: summaryHtml}}
        />
      )}

      {/* save and clear buttons */}
      {summaryHtml && (
        <div style={{display: 'flex', gap: '0.5em', marginTop: '1em'}}>
          <Button
            size="tiny"
            primary
            onClick={onSave}
            disabled={saving}
          >
            {saving ? 'Saving…' : 'Save summary'}
          </Button>
          <Button
            size="tiny"
            type="button"
            onClick={onClear}
          >
            Clear summary
          </Button>
        </div>
      )}
    </Segment>
  );
}
