// This file is part of the Indico plugins.
// Copyright (C) 2002 - 2025 CERN
//
// The Indico plugins are free software; you can redistribute
// them and/or modify them under the terms of the MIT License;
// see the LICENSE file for more details.

import staticURL from 'indico-url:plugin_ai_summary.static'

import React, {useRef, useEffect} from 'react';
import {Button, Segment, Header, HeaderSubheader, Icon, Dimmer, Image, Card} from 'semantic-ui-react';
import {Translate} from 'indico/react/i18n';

import './SummaryPreview.module.scss';
import './ActionButtons.module.scss';

import ActionButtons from './ActionButtons';

export default function SummaryPreview({loading, error, summaryHtml, saving, onSave, streamResponse, onRetry, llmInfo}) {

  const previewBottomRef = useRef();

  // Auto scroll if streaming is enabled
  useEffect(() => {
    // On new streamed content, scroll to bottom (only when not in error)
    if (streamResponse && previewBottomRef.current && !error) {
      previewBottomRef.current.scrollIntoView({behavior: 'smooth'});
    }
  }, [streamResponse, summaryHtml, error]);

  const scrollBarStyle = loading || error ? 'preview-card-wrapper scrollbar-hidden' : 'preview-card-wrapper';
  const displayedHtml = summaryHtml ? (error ? summaryHtml.substring(0, 800) : summaryHtml) : null;

  if (!loading && !error && !summaryHtml) {
    return (
      <Segment placeholder styleName="no-preview-placeholder" textAlign="center">
        <Header as="h3" textAlign="center" styleName="placeholder-message">
          <Image src={staticURL({filename: 'images/file-sparkle.svg'})} />
          <Translate as="span">Summarize your minutes</Translate>
          <HeaderSubheader styleName="subheader">
            <Translate as="span">Select a prompt, or create your own, from the panel on the left to get started.</Translate>
            <Translate as="span">AI responses may be inaccurate. Always verify important information.</Translate>
          </HeaderSubheader>
        </Header>
      </Segment>
    );
  }

  return (
    <>
      <Card raised fluid styleName={scrollBarStyle}>
        <Card.Content>
          {loading && !summaryHtml && (
            <h3 styleName="shimmer-text">
              <Translate>Generating summary...</Translate>
            </h3>
          )}
          {error && (
            <Dimmer active styleName="error-dimmer">
              <div styleName="error-content">
                <Header as="h2" icon>
                  <Icon name="times circle outline" color="red" />
                  <Header.Content color="white">
                    <Translate>Something went wrong</Translate>
                    <HeaderSubheader>{error}</HeaderSubheader>
                  </Header.Content>
                </Header>
                <Button primary onClick={onRetry}>
                  <Icon name="undo" />
                  <Translate>Try Again</Translate>
                </Button>
              </div>
            </Dimmer>
          )}

          {displayedHtml && (
            <div styleName="preview-card" dangerouslySetInnerHTML={{__html: displayedHtml}} />
          )}
          <div ref={previewBottomRef} />
        </Card.Content>
      </Card>
      <div styleName="action-buttons">
        <ActionButtons
          loading={loading}
          error={error}
          summaryHtml={summaryHtml}
          saving={saving}
          onSave={onSave}
          onRetry={onRetry}
        />
        {!loading && llmInfo && (
          <span styleName="llm-info">
            {llmInfo.model_name} ({llmInfo.provider_name})
          </span>
        )}
      </div>
    </>
  );
}
