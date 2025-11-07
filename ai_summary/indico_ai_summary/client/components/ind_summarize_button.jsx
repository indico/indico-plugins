// This file is part of the Indico plugins.
// Copyright (C) 2002 - 2025 CERN
//
// The Indico plugins are free software; you can redistribute
// them and/or modify them under the terms of the MIT License;
// see the LICENSE file for more details.

import staticURL from 'indico-url:plugin_ai_summary.static';
import getStoredPrompts from 'indico-url:plugin_ai_summary.llm_prompts';

import React, {useState, useEffect} from 'react';
import ReactDOM from 'react-dom';
import {Modal, Button, Form, Grid, GridRow, GridColumn, Header, Icon, Loader, Popup, Message} from 'semantic-ui-react';
import {Translate} from 'indico/react/i18n';
import {indicoAxios} from 'indico/utils/axios';
import {handleAxiosError} from 'indico/utils/axios';
import {streamSummary, fetchSummary, fetchEventNote, saveSummaryToEvent} from '../utils/summarize';
import {PromptControls, PromptEditor} from './PromptSelector';
import SummaryPreview from './SummaryPreview';
import './ind_summarize_button.module.scss';

function SummarizeButton({eventId, streamResponse, llmInfo}) {
  const [selectedPromptIndex, setSelectedPromptIndex] = useState(0);
  const [prompts, setPrompts] = useState([selectedPromptIndex]);
  const selectedPrompt = prompts[selectedPromptIndex];
  const [summaryHtml, setSummaryHtml] = useState('');
  const [summaryMarkdown, setSummaryMarkdown] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [saving, setSaving] = useState(false);
  const [isSaved, setIsSaved] = useState(false);
  const [streamStopped, setStreamStopped] = useState(false);
  const [streamCtl, setStreamCtl] = useState(null);
  const [isFeedbackDismissed, setIsFeedbackDismissed] = useState(
    localStorage.getItem('ai_summary_feedback_dismissed') === 'true' || false
  );

  // trigger summary generation from the backend
  const runSummarize = () => {
    // Close any existing stream first
    if (streamCtl) {
      try {
        streamCtl.abort();
      } catch {}
      setStreamCtl(null);
    }

    setLoading(true);
    setError(null);
    setSummaryHtml('');
    setSummaryMarkdown('');

    if (streamResponse) {
      setStreamStopped(false);
      // Streaming via fetch
      const ctl = streamSummary(eventId, selectedPrompt.text, {
        onChunk: data => {
          setSummaryHtml(data['html']);
          setSummaryMarkdown(data['markdown']);
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
        if (data?.summary_html && data?.summary_markdown) {
          setSummaryHtml(data.summary_html);
          setSummaryMarkdown(data.summary_markdown);
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
        streamCtl.abort();
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
        streamCtl.abort();
      } catch {}
    }
  }, [streamCtl]);

  // save generated summary into Indico event notes
  const handleSaveSummary = async () => {
    try {
      setSaving(true);
      const summaryMarker = `<hr>
        <h2>
          <img src="${staticURL({filename: 'images/sparkle.svg'})}" width="18px" height="18px" />
          <span style="color: #0099C9">Summary</span>
        </h2>`;
      // fetch existing event notes
      const noteData = await fetchEventNote(eventId);
      const updatedHtml = `${summaryMarker}${summaryHtml}${noteData.html || ''}`;

      // save combined notes(or previous summary) + summary back to Indico
      await saveSummaryToEvent(eventId, updatedHtml, noteData.id);
      setIsSaved(true);
    } catch (e) {
      setError(`Error during saving summary: ${handleAxiosError(e)}.`);
    } finally {
      setSaving(false);
    }
  };

  const getPrompts = async () => {
    try {
      const prompts =  await indicoAxios.get(getStoredPrompts({event_id: eventId}));
      setPrompts(prompts.data);
    } catch (e) {
      handleAxiosError(e);
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

  const handleFeedbackDismiss = () => {
    setIsFeedbackDismissed(true);
    localStorage.setItem('ai_summary_feedback_dismissed', 'true');
  };

  return (
    <>
      <Modal
        closeIcon
        onClose={() => {
          // Ensure any active stream is closed when modal is closed
          if (streamCtl) {
            try {
              streamCtl.abort();
            } catch {}
            setStreamCtl(null);
          }
          setLoading(false);
          if (isSaved) {
            location.reload();
          }
        }}
        onOpen={() => {
          getPrompts();
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
          <div styleName="modal-header-section">
            <Translate as="span">Summarize Meeting</Translate>
            <Popup
              trigger={
                <div styleName="badge">
                  <Icon name="flask" />
                  <Translate as="span">Experimental</Translate>
                </div>
              }
              content={Translate.string('This is an experimental feature. Functionality may change or be withdrawn in future releases.')}
              position="right center"
            />
          </div>
        </Modal.Header>
        <Modal.Content>
          <Grid celled="internally">
            <GridRow columns={2}>
              <GridColumn width={5} style={{display: 'flex', flexDirection: 'column'}}>
                <div style={{flex: 1}}>
                  <Form>
                    <Header as="h3" content={Translate.string('Select a prompt')} />
                    <PromptControls
                      selectedPromptIndex={selectedPromptIndex}
                      setSelectedPromptIndex={setSelectedPromptIndex}
                      storedPrompts={prompts}
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
                </div>

                {!isFeedbackDismissed && !loading && summaryHtml && (
                  <Message icon info style={{marginTop: '10px'}} onDismiss={handleFeedbackDismiss}>
                    <Icon name="comments outline" />
                    <Message.Content>
                      <Message.Header>
                        <Translate>We want your feedback</Translate>
                      </Message.Header>
                      <Translate as="p">Share your feedback on this feature with us on our Mattermost channel</Translate>
                      <Button as="a" href="https://mattermost.web.cern.ch/it-dep/channels/indico" target="_blank" primary>
                        <Translate>Mattermost: Open #indico</Translate>
                      </Button>
                    </Message.Content>
                  </Message>
                )}
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
                        <Popup
                          trigger={<Icon name="check circle outline" color="green" />}
                          content={Translate.string('Response complete')}
                          position="top center"
                        />
                      )}
                    </span>
                  </Header>
                  <SummaryPreview
                    loading={loading}
                    error={error}
                    summaryHtml={summaryHtml}
                    summaryMarkdown={summaryMarkdown}
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
      ReactDOM.render(
        <SummarizeButton
          categoryId={categoryId}
          eventId={eventId}
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
