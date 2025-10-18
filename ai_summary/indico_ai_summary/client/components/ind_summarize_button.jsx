// This file is part of the Indico plugins.
// Copyright (C) 2002 - 2025 CERN
//
// The Indico plugins are free software; you can redistribute
// them and/or modify them under the terms of the MIT License;
// see the LICENSE file for more details.

// Main entry point of the summarization feature in the Indico plugin.
// This file defines the Summarize button, manages modal states,
// handles prompt selection, generates summaries, and integrates
// with Indico's API to fetch and save meeting notes.

// import getStoredPrompts from 'indico-url:plugin_ai_summary.stored_prompts';

import staticURL from 'indico-url:plugin_ai_summary.static';

import React, {useState, useEffect, useContext} from 'react';
import ReactDOM from 'react-dom';
import {Modal, Button, Form, Grid, GridRow, GridColumn, Header, Icon, Loader, Popup} from 'semantic-ui-react';
import {Translate} from 'indico/react/i18n';
import {handleAxiosError} from 'indico/utils/axios';
import {streamSummary, fetchSummary, fetchEventNote, saveSummaryToEvent} from '../services/summarize';
import {PromptControls, PromptEditor} from './PromptSelector';
import SummaryPreview from './SummaryPreview';
import '../styles/ind_summarize_button.module.scss';

function SummarizeButton({categoryId, eventId, storedPrompts, streamResponse, llmInfo}) {
  const [selectedPromptIndex, setSelectedPromptIndex] = useState(0);
  const [prompts, setPrompts] = useState(storedPrompts);
  const selectedPrompt = prompts[selectedPromptIndex];
  const [summaryHtml, setSummaryHtml] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [saving, setSaving] = useState(false);
  const [streamStopped, setStreamStopped] = useState(false);
  const [streamCtl, setStreamCtl] = useState(null);

  // trigger summary generation from the backend
  const runSummarize = () => {
    // Close any existing stream first
    if (streamCtl) {
      try {
        streamCtl.close();
      } catch {}
      setStreamCtl(null);
    }

    setLoading(true);
    setError(null);
    setSummaryHtml('');

    if (streamResponse) {
      setStreamStopped(false);
      // Streaming via SSE
      const ctl = streamSummary(eventId, selectedPrompt.text, {
        onChunk: html => {
          // Replace each time with server snapshot
          setSummaryHtml(html);
        },
        onDone: () => {
          setLoading(false);
          setStreamCtl(null);
        },
        onError: msg => {
          setError(typeof msg === 'string' ? msg : 'Error during summarization');
          setLoading(false);
          setStreamCtl(null);
        },
      });
      setStreamCtl(ctl);
      return;
    }

    // Non-streaming single request
    (async () => {
      try {
        const data = await fetchSummary(eventId, selectedPrompt.text);
        if (data?.summary_html) {
          setSummaryHtml(data.summary_html);
        } else {
          setError('No summary returned.');
        }
      } catch (e) {
        setError(`Error during summarization: ${handleAxiosError(e)}`);
      } finally {
        setLoading(false);
      }
    })();
  };

  // stop/cancel an in-progress stream
  const stopStreaming = () => {
    if (streamCtl) {
      try {
        streamCtl.close();
      } catch {}
      setStreamCtl(null);
    }
    setStreamStopped(true);
    setLoading(false);
  };

  // Ensure stream is closed when component unmounts
  useEffect(() => () => {
    if (streamCtl) {
      try {
        streamCtl.close();
      } catch {}
    }
  }, [streamCtl]);

  // save generated summary into Indico event notes
  const handleSaveSummary = async () => {
    try {
      setSaving(true);
      // fetch existing event notes
      const noteData = await fetchEventNote(eventId);
      const updatedHtml = `${noteData.html || ''}<hr><h2>Summary</h2>${summaryHtml}`;
      // save combined notes(or previous summary) + summary back to Indico
      await saveSummaryToEvent(eventId, updatedHtml, noteData.id);
    } catch (e) {
      setError(`Error during saving summary: ${handleAxiosError(e)}.`);
    } finally {
      setSaving(false);
    }
  };

  const renderSummarizeButton = (loading, streamResponse, error) => {
    if (error) {
      return (
        <Button
          primary
          attached="bottom"
          onClick={runSummarize}
          disabled={loading}
        >
          <Icon name="undo" />
          <Translate>Try Again</Translate>
        </Button>
      );
    }

    if (!loading) {
      return (
        <Button
          primary
          attached="bottom"
          onClick={runSummarize}
          disabled={loading}
        >
          <Icon name="play circle" />
          <Translate>Generate Summary</Translate>
        </Button>
      );
    }

    if (loading && streamResponse) {
      return (
        <Button
          negative
          attached="bottom"
          onClick={stopStreaming}
        >
          <Icon name="stop" />
          <Translate>Stop Generating</Translate>
        </Button>
      );
    }

    if (loading && !streamResponse) {
      return (
        <Button
          primary
          attached="bottom"
          disabled
        >
          <Translate>Generating Summary...</Translate>
        </Button>
      );
    }
    return null;
  };

  return (
    <>
      <Modal
        closeIcon
        onClose={() => {
          // Ensure any active stream is closed when modal is closed
          if (streamCtl) {
            try {
              streamCtl.close();
            } catch {}
            setStreamCtl(null);
          }
          setLoading(false);
        }}
        closeOnEscape={false}
        closeOnDimmerClick={false}
        trigger={
          <div styleName="summarize-button-menu">
            <img src={staticURL({filename:'images/sparkle.svg'})} />
            <Translate as="a">Summarize</Translate>
          </div>
        }
        style={{minWidth: '65vw'}}
      >
        <Modal.Header>
          <Translate>Summarize Meeting</Translate>
        </Modal.Header>
        <Modal.Content>
          <Grid celled="internally">
            <GridRow columns={2}>
              <GridColumn width={5}>
                <Form>
                  <Header as="h3" content={Translate.string('Select a prompt')} />
                  <PromptControls
                    selectedPromptIndex={selectedPromptIndex}
                    setSelectedPromptIndex={setSelectedPromptIndex}
                    storedPrompts={storedPrompts}
                    disabled={loading}
                  />
                  <PromptEditor
                    selectedPromptIndex={selectedPromptIndex}
                    selectedPrompt={selectedPrompt}
                    setPrompts={setPrompts}
                    disabled={loading}
                  />
                  {renderSummarizeButton(loading, streamResponse, error)}
                </Form>
              </GridColumn>
              <GridColumn width={11} styleName="column-divider">
                  <Header as="h3">
                    <Translate>Preview</Translate>
                    <span styleName="completion-status">
                      {loading && !error && (
                        <Loader active inline size="small" styleName="modal-spinner" />
                      )}
                      {streamStopped && summaryHtml && (
                        <Popup
                          trigger={<Icon name="stop circle outline" color="grey" />}
                          content={Translate.string('Response interrupted')}
                          position="top center"
                        />
                      )}
                      {!loading && !error && !streamStopped && summaryHtml && (
                        <Icon name="check circle outline" color="green" />
                      )}
                    </span>
                  </Header>
                  <SummaryPreview
                    loading={loading}
                    error={error}
                    summaryHtml={summaryHtml}
                    saving={saving}
                    onSave={handleSaveSummary}
                    streamResponse={streamResponse}
                    onRetry={runSummarize}
                    llmInfo={llmInfo}
                  />
              </GridColumn>
            </GridRow>
          </Grid>
        </Modal.Content>
      </Modal>
    </>
  );
}

customElements.define(
  'ind-summarize-button',
  class extends HTMLElement {
    connectedCallback() {
      const eventId = parseInt(this.getAttribute('event-id'), 10);
      const categoryId = parseInt(this.getAttribute('category-id'), 10);
      const streamResponse = JSON.parse(this.getAttribute('stream-response'));
      const llmInfo = JSON.parse(this.getAttribute('llm-info'));
      const storedPrompts = [
        ...JSON.parse(this.getAttribute('stored-prompts')),
        {name: 'Custom...', text: ''},
      ];
      ReactDOM.render(
        <SummarizeButton
          categoryId={categoryId}
          eventId={eventId}
          storedPrompts={storedPrompts}
          streamResponse={streamResponse}
          llmInfo={llmInfo}
        />,
        this
      );
    }
    disconnectedCallback() {
      ReactDOM.unmountComponentAtNode(this);
    }
  }
);
