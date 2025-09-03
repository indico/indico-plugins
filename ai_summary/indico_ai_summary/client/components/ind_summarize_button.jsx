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

import React, {useState} from 'react';
import ReactDOM from 'react-dom';
import {Modal, Button, Form, Grid, GridRow, GridColumn, Header, Icon} from 'semantic-ui-react';
import {Translate} from 'indico/react/i18n';
import {handleAxiosError} from 'indico/utils/axios';
import {fetchSummary, fetchEventNote, saveSummaryToEvent} from '../services/summarize';
import {PromptControls, PromptEditor} from './prompt_selector';
import SummaryPreview from './summary_preview';
import '../styles/ind_summarize_button.module.scss';

function SummarizeButton({categoryId, eventId, storedPrompts}) {
  // React State Definitions
  const [selectedPromptIndex, setSelectedPromptIndex] = useState(0); // prompt selected for deletion
  const [prompts, setPrompts] = useState(storedPrompts); // all stored prompts
  const selectedPrompt = prompts[selectedPromptIndex];
  const [summaryHtml, setSummaryHtml] = useState(''); // generated summary HTML
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [saving, setSaving] = useState(false); // saving summary indicator

  // trigger summary generation by calling the backend API
  const runSummarize = async () => {
    setLoading(true);
    setError(null);
    setSummaryHtml('');

    let data;
    try {
      // call backend to fetch summary
      data = await fetchSummary(eventId, selectedPrompt.text);
    } catch (e) {
      setError(`Error during summarization: ${handleAxiosError(e)}`);
      setLoading(false);
      return;
    }
    // if response contains the summary display it
    if (data.summary_html) {
      setSummaryHtml(data.summary_html);
    } else {
      setError('No summary returned.');
    }
    setLoading(false);
  };

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
      setError(`Error during saving summary: ${handleAxiosError(e)}`);
    } finally {
      setSaving(false);
    }
  };

  return (
    <>
      <Modal
        closeIcon
        trigger={
          <li>
            <a>Summarize</a>
          </li>
        }
        style={{minWidth: '65vw'}}
      >
        <Modal.Header>Summarize Meeting</Modal.Header>
        <Modal.Content>
          <Grid celled="internally">
            <GridRow columns={2}>
              {/* left column : prompt selection */}
              <GridColumn>
                <Form>
                  <Header as="h3" content={Translate.string('Select a prompt')} />
                  <PromptControls
                    selectedPromptIndex={selectedPromptIndex}
                    setSelectedPromptIndex={setSelectedPromptIndex}
                    storedPrompts={storedPrompts}
                  />
                  <PromptEditor
                    selectedPromptIndex={selectedPromptIndex}
                    selectedPrompt={selectedPrompt}
                    setPrompts={setPrompts}
                  />
                  <Button
                    primary
                    type="button"
                    icon
                    labelPosition="right"
                    onClick={runSummarize}
                    disabled={loading}
                  >
                    {loading ? 'Summarizing…' : 'Generate meeting summary'}
                    <Icon name="magic" />
                  </Button>
                </Form>
              </GridColumn>

              {/* right column : summary preview */}
              <GridColumn styleName="column-divider">
                <Header as="h3" content="Preview" subheader="Summary" />
                <SummaryPreview
                  loading={loading}
                  error={error}
                  summaryHtml={summaryHtml}
                  saving={saving}
                  onSave={handleSaveSummary}
                />
              </GridColumn>
            </GridRow>
          </Grid>
        </Modal.Content>
      </Modal>
    </>
  );
}

// custom HTML element <ind-summarize-button>
customElements.define(
  'ind-summarize-button',
  class extends HTMLElement {
    connectedCallback() {
      const eventId = parseInt(this.getAttribute('event-id'), 10);
      const categoryId = parseInt(this.getAttribute('category-id'), 10);
      const storedPrompts = [
        ...JSON.parse(this.getAttribute('stored-prompts')),
        {name: 'Custom...', text: ''},
      ];
      ReactDOM.render(
        <SummarizeButton categoryId={categoryId} eventId={eventId} storedPrompts={storedPrompts} />,
        this
      );
    }
    disconnectedCallback() {
      ReactDOM.unmountComponentAtNode(this);
    }
  }
);
